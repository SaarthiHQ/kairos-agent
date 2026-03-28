"""Simulated Saarthi incident — test kairos end-to-end.

Runs the context assembly + summarization pipeline against sample logs.
Requires ANTHROPIC_API_KEY to be set. Does NOT post to Slack.

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python test_saarthi.py
"""

import asyncio
import json
import sys

from kairos_agent.config import load_config
from kairos_agent.context_assembler import assemble_context, infer_alert_type
from kairos_agent.service_catalog import resolve_sources_for_alert
from kairos_agent.summarizer import build_user_prompt, summarize


# Simulated PagerDuty alert for Saarthi
SIMULATED_ALERT = {
    "incident_id": "SIM-001",
    "title": "High error rate on saarthi-clinical — document processing pipeline stalled",
    "service_name": "saarthi-clinical",
    "urgency": "high",
    "triggered_at": "2026-03-29T10:02:00Z",
    "html_url": "https://alerts.newrelic.com/accounts/7688224/incidents/SIM-001",
}


async def main():
    print("=" * 60)
    print("KAIROS TEST: Saarthi incident simulation")
    print("=" * 60)

    # Load config
    config = load_config("kairos-test.yaml")
    print(f"\nConfig loaded: {len(config.log_sources)} sources, {len(config.services)} services")

    # Classify alert
    alert_type = infer_alert_type(SIMULATED_ALERT)
    print(f"Alert type inferred: {alert_type.value}")

    # Resolve sources
    resolved = resolve_sources_for_alert(SIMULATED_ALERT["service_name"], config)
    print(f"Sources resolved: {len(resolved)}")
    for r in resolved:
        print(f"  - {r.log_source.name or r.log_source.path} ({r.relationship} via {r.origin_service})")

    # Assemble context
    service_metadata = config.services.get(SIMULATED_ALERT["service_name"])
    context = assemble_context(
        alert_info=SIMULATED_ALERT,
        log_sources=config.log_sources,
        config=config.context,
        resolved_sources=resolved if config.services else None,
        alert_type=alert_type,
        service_metadata=service_metadata,
    )

    print(f"\nContext assembled:")
    print(f"  Direct log lines: {len(context.log_lines)}")
    print(f"  Dependency log lines: {len(context.dependency_log_lines)}")
    print(f"  Total scanned: {context.total_lines_scanned}")
    print(f"  Error count: {context.error_count}")
    print(f"  Alert type: {context.alert_type}")
    print(f"  Service tier: {context.service_tier}")
    print(f"  Dependencies: {context.dependency_services}")

    if context.quality:
        q = context.quality
        print(f"\n  Quality:")
        print(f"    Sources: {q.sources_attempted} attempted, {q.sources_succeeded} succeeded")
        print(f"    Coverage: {q.coverage_ratio:.0%}")
        if q.gaps:
            print(f"    Gaps:")
            for gap in q.gaps:
                print(f"      - {gap}")

    # Show the prompt that would be sent to Claude
    prompt = build_user_prompt(SIMULATED_ALERT, context)
    print(f"\n{'=' * 60}")
    print("PROMPT PREVIEW (what Claude will see):")
    print("=" * 60)
    print(prompt)

    # Call Claude for summarization (requires ANTHROPIC_API_KEY)
    import os
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(f"\n{'=' * 60}")
        print("SKIPPING SUMMARIZATION: Set ANTHROPIC_API_KEY to test Claude integration")
        print("=" * 60)
        return

    print(f"\n{'=' * 60}")
    print("CALLING CLAUDE FOR TRIAGE SUMMARY...")
    print("=" * 60)

    summary = await summarize(
        alert_info=SIMULATED_ALERT,
        context=context,
        llm_config=config.llm,
    )

    print(f"\n{'=' * 60}")
    print("TRIAGE SUMMARY:")
    print("=" * 60)
    print(summary)


if __name__ == "__main__":
    asyncio.run(main())
