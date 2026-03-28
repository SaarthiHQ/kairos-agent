"""Orchestrate the triage pipeline: assemble context -> summarize -> notify."""

from __future__ import annotations

import logging
from typing import Any

from kairos_agent.config import KairosConfig
from kairos_agent.context_assembler import assemble_context, infer_alert_type
from kairos_agent.notifier import notify_slack
from kairos_agent.service_catalog import resolve_sources_for_alert
from kairos_agent.summarizer import summarize

logger = logging.getLogger("kairos_agent")


async def run_triage_pipeline(
    config: KairosConfig, alert_info: dict[str, Any]
) -> None:
    """Run the full triage pipeline for an incident.

    Steps:
    1. Infer alert type and resolve sources from service catalog
    2. Assemble log context with dependency awareness
    3. Summarize with Claude
    4. Post to Slack
    """
    incident_id = alert_info.get("incident_id", "unknown")
    service_name = alert_info.get("service_name", "unknown")
    logger.info("Starting triage pipeline for incident %s", incident_id)

    # Step 1: Classify alert and resolve sources
    alert_type = infer_alert_type(alert_info)
    logger.info("Alert type: %s", alert_type.value)

    resolved = resolve_sources_for_alert(service_name, config)
    service_metadata = config.services.get(service_name)

    if service_metadata:
        logger.info(
            "Service catalog: %s (tier=%s, deps=%s)",
            service_name, service_metadata.tier,
            ", ".join(service_metadata.depends_on) or "none",
        )

    # Step 2: Assemble context
    context = assemble_context(
        alert_info=alert_info,
        log_sources=config.log_sources,
        config=config.context,
        resolved_sources=resolved if config.services else None,
        alert_type=alert_type,
        service_metadata=service_metadata,
    )
    logger.info(
        "Context assembled: %d lines + %d dep lines from %d scanned (%d errors)",
        len(context.log_lines),
        len(context.dependency_log_lines),
        context.total_lines_scanned,
        context.error_count,
    )

    # Step 3: Summarize with LLM
    summary = await summarize(
        alert_info=alert_info,
        context=context,
        llm_config=config.llm,
    )

    # Step 4: Post to Slack
    await notify_slack(
        alert_info=alert_info,
        summary=summary,
        slack_config=config.slack,
    )

    logger.info("Triage pipeline complete for incident %s", incident_id)
