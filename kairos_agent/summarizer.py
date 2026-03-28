"""Send assembled context to Claude and get a triage summary.

Prompt design follows context engineering best practices:
- Structured system prompt with clear sections (Anthropic guide)
- Situation-first user prompt with evidence and question at end
- Prompt repetition of key context (Leviathan et al., 2025)
- Quality assessment surfaced so the model can express confidence
"""

from __future__ import annotations

import logging

import anthropic

from kairos_agent.config import LLMConfig
from kairos_agent.context_assembler import LogContext

logger = logging.getLogger("kairos_agent")

# System prompt structured with clear sections per Anthropic's
# context engineering guide: "extremely clear, simple, direct language"
# at "the right altitude" — specific enough to guide, flexible enough
# for strong heuristics.
SYSTEM_PROMPT = """\
<role>
You are an expert incident triage assistant. You receive incident context \
(alert details and relevant log lines) and produce a concise triage summary \
for the on-call engineer.
</role>

<output_format>
Your summary must be actionable and scannable in under 30 seconds. Structure it as:

1. **What's happening**: One-sentence description of the incident.
2. **Affected service**: Which service/component is impacted.
3. **Key evidence**: The 3-5 most important log lines or patterns (quote them).
4. **Likely root cause**: Your best assessment based on the evidence.
5. **Suggested next steps**: 2-3 concrete actions the on-call should take first.
</output_format>

<guidelines>
- Be direct. No filler.
- If the logs are insufficient, say so explicitly and suggest where to look next.
- If context quality is low (failed sources, gaps, or low coverage), explicitly \
state your confidence level and recommend where to look for missing data.
- When multiple sources are available, note correlations across sources.
- If no ERROR-level lines are found despite an error-related alert, flag this \
as a potential logging or configuration issue.
</guidelines>\
"""


def build_user_prompt(alert_info: dict, context: LogContext) -> str:
    """Build the user prompt from alert info and assembled context.

    Prompt structure follows research-backed practices:
    - Alert details first (situation — primacy position)
    - Quality assessment next (so the model calibrates confidence early)
    - Log lines in the middle (evidence)
    - Key context repeated at the end (prompt repetition — recency position)
    """
    log_block = "\n".join(context.log_lines) if context.log_lines else "(no matching logs found)"

    quality_section = ""
    if context.quality:
        q = context.quality
        gaps_block = "\n".join(f"  - {g}" for g in q.gaps) if q.gaps else "  (none)"
        quality_section = f"""
## Context Quality
- **Sources attempted**: {q.sources_attempted} | **succeeded**: {q.sources_succeeded} | **failed**: {q.sources_failed}
- **Coverage**: {q.coverage_ratio:.0%}
- **Gaps**:
{gaps_block}
"""

    # Prompt repetition: repeat the key identifiers (service, title) after the
    # log block so the model has them in its attention window when generating.
    # Research shows this improves accuracy in 47/70 benchmarks with 0 regressions.
    title = alert_info.get('title', 'N/A')
    service = context.service_name
    urgency = alert_info.get('urgency', 'N/A')

    return f"""\
## Incident Alert
- **Title**: {title}
- **Service**: {service}
- **Urgency**: {urgency}
- **Triggered at**: {alert_info.get('triggered_at', 'N/A')}
- **PagerDuty URL**: {alert_info.get('html_url', 'N/A')}

## Log Context
- **Time window**: {context.time_window_start} to {context.time_window_end}
- **Lines scanned**: {context.total_lines_scanned}
- **Error lines found**: {context.error_count}
- **Sources**: {', '.join(context.sources_checked)}
{quality_section}
## Relevant Log Lines
```
{log_block}
```

## Task
Produce a triage summary for the incident "{title}" affecting **{service}** (urgency: {urgency}). \
Focus on the evidence above and assess root cause.\
"""


async def summarize(
    alert_info: dict,
    context: LogContext,
    llm_config: LLMConfig,
) -> str:
    """Call Claude to produce a triage summary from incident context."""
    client = anthropic.AsyncAnthropic()  # Uses ANTHROPIC_API_KEY env var

    user_prompt = build_user_prompt(alert_info, context)

    logger.info(
        "Requesting summary from %s (context: %d lines)",
        llm_config.model,
        len(context.log_lines),
    )

    message = await client.messages.create(
        model=llm_config.model,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    summary = message.content[0].text
    logger.info("Summary generated (%d chars)", len(summary))
    return summary
