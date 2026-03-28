"""CLI entry point for kairos-agent."""

from __future__ import annotations

import argparse
import logging
import sys

from kairos_agent import __version__


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="kairos-agent",
        description="AI-powered incident context assembler",
    )
    subparsers = parser.add_subparsers(dest="command")

    # Default: run the server (backward compat — also works without subcommand)
    parser.add_argument(
        "--config",
        default="kairos.yaml",
        help="Path to kairos.yaml config file (default: kairos.yaml)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on (default: 8000)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (default: INFO)",
    )

    # setup subcommand
    setup_parser = subparsers.add_parser(
        "setup",
        help="Interactive setup — generates kairos.yaml",
    )
    setup_parser.add_argument(
        "--output",
        default="kairos.yaml",
        help="Output config file path (default: kairos.yaml)",
    )

    # test subcommand
    test_parser = subparsers.add_parser(
        "test",
        help="Run a simulated triage against your config",
    )
    test_parser.add_argument(
        "--config",
        default="kairos.yaml",
        help="Path to kairos.yaml config file",
    )
    test_parser.add_argument(
        "--service",
        default="",
        help="Service name to simulate alert for",
    )
    test_parser.add_argument(
        "--title",
        default="High error rate",
        help="Simulated alert title",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level if hasattr(args, "log_level") else "INFO"),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.command == "setup":
        from kairos_agent.setup import run_setup
        run_setup(output_path=args.output)
        return

    if args.command == "test":
        _run_test(args)
        return

    # Default: run the webhook server
    _run_server(args)


def _run_test(args) -> None:
    """Run a simulated triage against the config."""
    import asyncio

    from kairos_agent.config import load_config
    from kairos_agent.context_assembler import assemble_context, infer_alert_type
    from kairos_agent.service_catalog import resolve_sources_for_alert
    from kairos_agent.summarizer import build_user_prompt, summarize

    try:
        config = load_config(args.config)
    except (FileNotFoundError, ValueError) as e:
        print(f"Config error: {e}", file=sys.stderr)
        sys.exit(1)

    service = args.service
    if not service and config.services:
        service = next(iter(config.services))
        print(f"No --service specified, using first from catalog: {service}")
    elif not service:
        service = "test-service"

    # For test mode, use a triggered_at that matches sample log timestamps.
    # If --at is provided, use that; otherwise try to detect from log content.
    triggered_at = getattr(args, "at", "") or ""
    if not triggered_at:
        # Auto-detect: use the latest timestamp from the configured sources
        from kairos_agent.sources import build_sources
        from kairos_agent.context_assembler import parse_timestamp
        from datetime import datetime as dt, timezone as tz

        all_sources = build_sources(config.log_sources)
        latest_ts = None
        for source in all_sources:
            fetched = source.fetch(service, dt.min.replace(tzinfo=tz.utc), dt.max.replace(tzinfo=tz.utc))
            for line in fetched.lines:
                ts = parse_timestamp(line)
                if ts and (latest_ts is None or ts > latest_ts):
                    latest_ts = ts
        if latest_ts:
            triggered_at = latest_ts.isoformat()
            print(f"Auto-detected trigger time from logs: {triggered_at}")

    if not triggered_at:
        triggered_at = __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat()

    alert_info = {
        "incident_id": "TEST-001",
        "title": args.title,
        "service_name": service,
        "urgency": "high",
        "triggered_at": triggered_at,
        "html_url": "https://test/incidents/TEST-001",
    }

    print(f"\nSimulating alert: '{args.title}' on {service}")
    print("-" * 50)

    alert_type = infer_alert_type(alert_info)
    print(f"Alert type: {alert_type.value}")

    resolved = resolve_sources_for_alert(service, config)
    print(f"Sources resolved: {len(resolved)}")
    for r in resolved:
        label = r.log_source.name or r.log_source.path or r.log_source.type
        print(f"  {r.relationship}: {label} (via {r.origin_service})")

    context = assemble_context(
        alert_info=alert_info,
        log_sources=config.log_sources,
        config=config.context,
        resolved_sources=resolved if config.services else None,
        alert_type=alert_type,
        service_metadata=config.services.get(service),
    )

    print(f"\nContext: {len(context.log_lines)} lines + {len(context.dependency_log_lines)} dep lines")
    print(f"Scanned: {context.total_lines_scanned} | Errors: {context.error_count}")

    if context.quality:
        q = context.quality
        print(f"Quality: {q.coverage_ratio:.0%} coverage, {len(q.gaps)} gaps")
        for gap in q.gaps:
            print(f"  - {gap}")

    import os
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(f"\nPrompt preview ({len(build_user_prompt(alert_info, context))} chars):")
        print(build_user_prompt(alert_info, context)[:500] + "...")
        print("\nSet ANTHROPIC_API_KEY to get a Claude-generated summary.")
        return

    print("\nCalling Claude...")
    summary = asyncio.run(summarize(alert_info, context, config.llm))
    print(f"\n{'=' * 50}")
    print("TRIAGE SUMMARY:")
    print("=" * 50)
    print(summary)


def _run_server(args) -> None:
    """Start the webhook server."""
    from kairos_agent.config import load_config

    try:
        config = load_config(args.config)
    except (FileNotFoundError, ValueError) as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    import os
    os.environ["KAIROS_CONFIG_PATH"] = args.config

    import uvicorn
    import kairos_agent.webhook_receiver as wr
    from kairos_agent.webhook_receiver import app

    wr._config = config

    print(f"kairos-agent v{__version__} starting on {args.host}:{args.port}")
    print(f"Config: {args.config}")
    print(f"Sources: {len(config.log_sources)} | Services: {len(config.services)}")
    print(f"LLM: {config.llm.provider}/{config.llm.model}")
    print(f"Webhook: POST http://{args.host}:{args.port}/webhook/pagerduty")

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
