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

*What's happening*: One-sentence description of the incident.
*Affected service*: Which service/component is impacted.
*Key evidence*: The 3-5 most important log lines or patterns (quote them in backticks).
*Likely root cause*: Your best assessment based on the evidence.
*Suggested next steps*: 2-3 concrete actions the on-call should take first.

IMPORTANT formatting rules — your output will be posted to Slack:
- Use *asterisks* for bold (NOT **double asterisks**)
- Use _underscores_ for italic
- Use `backticks` for code/log lines
- Use plain numbered lists (1. 2. 3.) not markdown headers
- Do NOT use ## headers or **markdown bold** — they don't render in Slack
- Keep it compact — no blank lines between sections
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
    - Triple prompt repetition (Leviathan et al., 2025): key context
      repeated at beginning, mid-log anchor, and end. ×3 repetition
      "often substantially outperforms" single repetition.
    """
    # Triple prompt repetition: inject an anchor in the middle of the log block
    # so the model's attention stays connected to the task throughout.
    anchor = f"[CONTEXT: investigating {context.service_name} — {alert_info.get('title', '')}]"
    lines = context.log_lines if context.log_lines else []
    if len(lines) > 10:
        mid = len(lines) // 2
        lines = lines[:mid] + [anchor] + lines[mid:]
    log_block = "\n".join(lines) if lines else "(no matching logs found)"

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

    title = alert_info.get('title', 'N/A')
    service = context.service_name
    urgency = alert_info.get('urgency', 'N/A')

    # Service context section (if catalog data is available)
    service_section = ""
    if context.service_tier != "standard" or context.service_owners or context.dependency_services:
        deps_str = ", ".join(context.dependency_services) if context.dependency_services else "(none)"
        owners_str = ", ".join(context.service_owners) if context.service_owners else "(unspecified)"
        service_section = f"""
## Service Context
- **Tier**: {context.service_tier}
- **Owners**: {owners_str}
- **Dependencies**: {deps_str}
- **Alert type**: {context.alert_type}
"""

    # Dependency log section (separate from direct logs for clear provenance)
    dep_section = ""
    if context.dependency_log_lines:
        dep_block = "\n".join(context.dependency_log_lines)
        dep_section = f"""
## Dependency Log Lines
These lines are from upstream/downstream dependencies, not the alerting service itself:
```
{dep_block}
```
"""

    # Alert-type-specific guidance for the task instruction
    alert_guidance = ""
    if context.alert_type == "latency":
        alert_guidance = " Focus on latency patterns, timeouts, and slow operations."
    elif context.alert_type == "availability":
        alert_guidance = " Focus on connectivity, health checks, and resource exhaustion."
    elif context.alert_type == "error_rate":
        alert_guidance = " Focus on error patterns, exceptions, and stack traces."

    # Prompt repetition: repeat key identifiers after the log block so the model
    # has them in its attention window when generating (Leviathan et al., 2025).
    return f"""\
## Incident Alert
- **Title**: {title}
- **Service**: {service}
- **Urgency**: {urgency}
- **Triggered at**: {alert_info.get('triggered_at', 'N/A')}
- **PagerDuty URL**: {alert_info.get('html_url', 'N/A')}
{service_section}
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
{dep_section}
## Task
Produce a triage summary for the incident "{title}" affecting **{service}** (urgency: {urgency}).{alert_guidance} \
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
