"""Orchestrate the triage pipeline: assemble context -> summarize -> notify."""

from __future__ import annotations

import logging
from typing import Any

from kairos_agent.config import KairosConfig
from kairos_agent.context_assembler import assemble_context
from kairos_agent.notifier import notify_slack
from kairos_agent.summarizer import summarize

logger = logging.getLogger("kairos_agent")


async def run_triage_pipeline(
    config: KairosConfig, alert_info: dict[str, Any]
) -> None:
    """Run the full triage pipeline for an incident.

    Steps:
    1. Assemble log context from configured sources
    2. Summarize with Claude
    3. Post to Slack
    """
    incident_id = alert_info.get("incident_id", "unknown")
    logger.info("Starting triage pipeline for incident %s", incident_id)

    # Step 1: Assemble context
    context = assemble_context(
        alert_info=alert_info,
        log_sources=config.log_sources,
        config=config.context,
    )
    logger.info(
        "Context assembled: %d relevant lines from %d scanned (%d errors)",
        len(context.log_lines),
        context.total_lines_scanned,
        context.error_count,
    )

    # Step 2: Summarize with LLM
    summary = await summarize(
        alert_info=alert_info,
        context=context,
        llm_config=config.llm,
    )

    # Step 3: Post to Slack
    await notify_slack(
        alert_info=alert_info,
        summary=summary,
        slack_config=config.slack,
    )

    logger.info("Triage pipeline complete for incident %s", incident_id)
