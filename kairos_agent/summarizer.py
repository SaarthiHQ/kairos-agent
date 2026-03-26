"""Send assembled context to Claude and get a triage summary."""

from __future__ import annotations

import logging

import anthropic

from kairos_agent.config import LLMConfig
from kairos_agent.context_assembler import LogContext

logger = logging.getLogger("kairos_agent")

SYSTEM_PROMPT = """\
You are an expert SRE triage assistant. You receive incident context (alert details \
and relevant log lines) and produce a concise triage summary for the on-call engineer.

Your summary must be actionable and scannable in under 30 seconds. Structure it as:

1. **What's happening**: One-sentence description of the incident.
2. **Affected service**: Which service/component is impacted.
3. **Key evidence**: The 3-5 most important log lines or patterns (quote them).
4. **Likely root cause**: Your best assessment based on the evidence.
5. **Suggested next steps**: 2-3 concrete actions the on-call should take first.

Be direct. No filler. If the logs are insufficient, say so explicitly and suggest \
where to look next.\
"""


def build_user_prompt(alert_info: dict, context: LogContext) -> str:
    """Build the user prompt from alert info and assembled context."""
    log_block = "\n".join(context.log_lines) if context.log_lines else "(no matching logs found)"

    return f"""\
## Incident Alert
- **Title**: {alert_info.get('title', 'N/A')}
- **Service**: {context.service_name}
- **Urgency**: {alert_info.get('urgency', 'N/A')}
- **Triggered at**: {alert_info.get('triggered_at', 'N/A')}
- **PagerDuty URL**: {alert_info.get('html_url', 'N/A')}

## Log Context
- **Time window**: {context.time_window_start} to {context.time_window_end}
- **Lines scanned**: {context.total_lines_scanned}
- **Error lines found**: {context.error_count}
- **Sources**: {', '.join(context.sources_checked)}

## Relevant Log Lines
```
{log_block}
```

Produce your triage summary now.\
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
