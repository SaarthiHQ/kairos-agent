"""CLI entry point for kairos-agent."""

from __future__ import annotations

import argparse
import logging
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="kairos-agent",
        description="AI-powered incident context assembler for SRE teams",
    )
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
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Validate config at startup
    from kairos_agent.config import load_config
    try:
        config = load_config(args.config)
    except (FileNotFoundError, ValueError) as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    # Inject config path so the app can reload it
    import os
    os.environ["KAIROS_CONFIG_PATH"] = args.config

    import uvicorn
    from kairos_agent.webhook_receiver import app, _config

    # Pre-load config into the app
    import kairos_agent.webhook_receiver as wr
    wr._config = config

    print(f"kairos-agent v0.1.0 starting on {args.host}:{args.port}")
    print(f"Config: {args.config}")
    print(f"Log sources: {[s.path for s in config.log_sources]}")
    print(f"LLM: {config.llm.provider}/{config.llm.model}")
    print(f"Webhook endpoint: POST http://{args.host}:{args.port}/webhook/pagerduty")

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
