"""Interactive setup for kairos-agent — generates kairos.yaml from team inputs.

Usage:
    kairos-agent setup
    kairos-agent setup --output kairos.yaml

Walks the team through:
1. Observability tool selection and credential testing
2. Service discovery (auto from New Relic, or manual)
3. Service catalog with dependencies
4. Notification setup (Slack)
5. LLM configuration
6. Validation test
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

import yaml

logger = logging.getLogger("kairos_agent")


def _prompt(question: str, default: str = "") -> str:
    """Prompt user with optional default."""
    suffix = f" [{default}]" if default else ""
    answer = input(f"  {question}{suffix}: ").strip()
    return answer or default


def _prompt_choice(question: str, options: list[str]) -> str:
    """Prompt user to select from options."""
    print(f"  {question}")
    for i, opt in enumerate(options, 1):
        print(f"    {i}. {opt}")
    while True:
        answer = input(f"  Select (1-{len(options)}): ").strip()
        try:
            idx = int(answer) - 1
            if 0 <= idx < len(options):
                return options[idx]
        except ValueError:
            pass
        print(f"  Please enter a number between 1 and {len(options)}")


def _prompt_multi(question: str, options: list[str]) -> list[str]:
    """Prompt user to select multiple options."""
    print(f"  {question}")
    for i, opt in enumerate(options, 1):
        print(f"    {i}. {opt}")
    while True:
        answer = input(f"  Select (comma-separated, e.g. 1,2): ").strip()
        try:
            indices = [int(x.strip()) - 1 for x in answer.split(",")]
            if all(0 <= i < len(options) for i in indices):
                return [options[i] for i in indices]
        except ValueError:
            pass
        print(f"  Please enter valid numbers separated by commas")


def _prompt_yn(question: str, default: bool = True) -> bool:
    """Yes/no prompt."""
    suffix = " [Y/n]" if default else " [y/N]"
    answer = input(f"  {question}{suffix}: ").strip().lower()
    if not answer:
        return default
    return answer in ("y", "yes")


def _test_newrelic(api_key: str, account_id: str, region: str) -> list[str] | None:
    """Test New Relic connection and discover services."""
    import httpx

    endpoint = (
        "https://api.eu.newrelic.com/graphql"
        if region == "eu"
        else "https://api.newrelic.com/graphql"
    )
    query = f"""{{
        actor {{
            account(id: {account_id}) {{
                nrql(query: "SELECT uniques(service.name) FROM Log SINCE 1 day ago") {{
                    results
                }}
            }}
        }}
    }}"""

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                endpoint,
                headers={"API-Key": api_key, "Content-Type": "application/json"},
                json={"query": query},
            )
            resp.raise_for_status()
            data = resp.json()

            errors = data.get("errors")
            if errors:
                print(f"  ✗ NerdGraph error: {errors[0].get('message', errors)}")
                return None

            results = (
                data.get("data", {})
                .get("actor", {})
                .get("account", {})
                .get("nrql", {})
                .get("results", [])
            )

            services = []
            for row in results:
                members = row.get("uniques.service.name", row.get("members", []))
                if isinstance(members, list):
                    services.extend(members)
                elif isinstance(members, str):
                    services.append(members)

            return sorted(set(s for s in services if s))

    except httpx.RequestError as e:
        print(f"  ✗ Connection failed: {e}")
        return None
    except httpx.HTTPStatusError as e:
        print(f"  ✗ HTTP {e.response.status_code}")
        return None


def _test_slack(webhook_url: str) -> bool:
    """Test Slack webhook with a test message."""
    import httpx

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(
                webhook_url,
                json={"text": "kairos-agent setup test — connection successful"},
            )
            return resp.status_code == 200
    except Exception:
        return False


def run_setup(output_path: str = "kairos.yaml") -> None:
    """Interactive setup flow."""
    print()
    print("=" * 50)
    print("  kairos-agent setup")
    print("=" * 50)
    print()

    config: dict = {}
    log_sources: list[dict] = []
    services: dict = {}

    # Step 1: Observability tools
    print("Step 1/5: Observability tools")
    print()
    tools = _prompt_multi(
        "Which tools does your team use?",
        ["New Relic", "Datadog", "Grafana Loki", "File-based logs", "Other (HTTP API)"],
    )
    print()

    # Step 2: Configure each tool
    print("Step 2/5: Source connections")
    print()

    discovered_services: list[str] = []

    if "New Relic" in tools:
        print("  -- New Relic --")
        nr_key = _prompt("API Key (NRAK-...)")
        nr_account = _prompt("Account ID")
        nr_region = _prompt("Region", "us")
        nr_query = _prompt(
            "NRQL query template",
            "SELECT timestamp, message, level, service.name FROM Log WHERE service.name = '{service_name}'",
        )

        print("  Testing connection...", end=" ", flush=True)
        found = _test_newrelic(nr_key, nr_account, nr_region)
        if found is not None:
            print(f"✓ Connected (found {len(found)} services)")
            discovered_services = found
        else:
            print("✗ Failed — check credentials")
            if not _prompt_yn("Continue anyway?", default=False):
                sys.exit(1)

        log_sources.append({
            "name": "newrelic",
            "type": "newrelic",
            "credentials": {
                "api_key": nr_key,
            },
            "options": {
                "account_id": nr_account,
                "region": nr_region,
                "query": nr_query,
            },
        })
        print()

    if "Datadog" in tools:
        print("  -- Datadog --")
        dd_api = _prompt("API Key")
        dd_app = _prompt("Application Key")
        dd_site = _prompt("Site", "datadoghq.com")
        dd_query = _prompt("Query template", "service:{service_name}")

        log_sources.append({
            "name": "datadog",
            "type": "datadog",
            "credentials": {"api_key": dd_api, "app_key": dd_app},
            "options": {"site": dd_site, "query": dd_query},
        })
        print()

    if "Grafana Loki" in tools:
        print("  -- Grafana Loki --")
        loki_url = _prompt("Loki URL (e.g. http://loki:3100)")
        loki_query = _prompt("LogQL template", '{app="{service_name}"}')
        loki_auth = _prompt("Auth header (or empty)", "")

        source = {
            "name": "loki",
            "type": "loki",
            "options": {"url": loki_url, "query": loki_query},
        }
        if loki_auth:
            source["credentials"] = {"auth_header": loki_auth}
        log_sources.append(source)
        print()

    if "File-based logs" in tools:
        print("  -- File logs --")
        file_path = _prompt("Log file glob pattern", "/var/log/app/*.log")
        log_sources.append({
            "name": "file-logs",
            "type": "file",
            "path": file_path,
        })
        print()

    if "Other (HTTP API)" in tools:
        print("  -- HTTP API --")
        http_url = _prompt("API URL (supports {service_name}, {start_epoch}, {end_epoch})")
        http_method = _prompt("Method", "GET")
        http_lines_path = _prompt("Response JSON path to lines", "lines")
        http_auth = _prompt("Authorization header (or empty)", "")

        source = {
            "name": "http-api",
            "type": "http",
            "options": {
                "url": http_url,
                "method": http_method,
                "response_lines_path": http_lines_path,
            },
        }
        if http_auth:
            source["credentials"] = {"auth_header": http_auth}
        log_sources.append(source)
        print()

    # Step 3: Services
    print("Step 3/5: Service catalog")
    print()

    if discovered_services:
        print(f"  Found {len(discovered_services)} services in New Relic:")
        for i, svc in enumerate(discovered_services, 1):
            print(f"    {i}. {svc}")
        print()

        selected = _prompt(
            "Which services to monitor? (comma-separated numbers, or 'all')"
        )
        if selected.lower() == "all":
            service_names = discovered_services
        else:
            indices = [int(x.strip()) - 1 for x in selected.split(",")]
            service_names = [discovered_services[i] for i in indices if 0 <= i < len(discovered_services)]
    else:
        svc_input = _prompt("Service names (comma-separated)")
        service_names = [s.strip() for s in svc_input.split(",") if s.strip()]

    source_names = [s.get("name", s.get("type", "unknown")) for s in log_sources]

    for svc_name in service_names:
        print(f"\n  Configuring {svc_name}:")
        tier = _prompt_choice("Tier?", ["critical", "standard", "best-effort"])
        deps_input = _prompt("Dependencies (comma-separated, or empty)", "")
        deps = [d.strip() for d in deps_input.split(",") if d.strip()]
        owners_input = _prompt("Owners (comma-separated)", "")
        owners = [o.strip() for o in owners_input.split(",") if o.strip()]

        services[svc_name] = {
            "depends_on": deps,
            "owners": owners,
            "sources": source_names,
            "tier": tier,
        }
    print()

    # Step 4: Slack
    print("Step 4/5: Notifications")
    print()
    slack_url = _prompt("Slack incoming webhook URL")
    if slack_url:
        print("  Testing Slack...", end=" ", flush=True)
        if _test_slack(slack_url):
            print("✓ Message posted")
        else:
            print("✗ Failed — check webhook URL")
    config["slack"] = {"webhook_url": slack_url}
    print()

    # Step 5: LLM
    print("Step 5/5: LLM configuration")
    print()
    anthropic_key = _prompt("Anthropic API key (sk-ant-...)")
    model = _prompt("Model", "claude-sonnet-4-20250514")
    config["llm"] = {"provider": "anthropic", "model": model}
    print()

    # PagerDuty (optional)
    pd_secret = _prompt("PagerDuty webhook secret (or press enter to skip)", "")
    config["pagerduty"] = {"webhook_secret": pd_secret or "configure-me"}

    # Assemble config
    config["log_sources"] = log_sources
    if services:
        config["services"] = services
    config["context"] = {
        "time_window_minutes": 15,
        "max_log_lines": 500,
        "max_context_tokens": 10000,
    }

    # Write config
    output = Path(output_path)
    output.write_text(yaml.dump(config, default_flow_style=False, sort_keys=False))

    print("=" * 50)
    print(f"  ✓ Configuration written to {output_path}")
    print("=" * 50)

    # Set env var for Anthropic
    if anthropic_key:
        print(f"\n  To start kairos, run:")
        print(f"    export ANTHROPIC_API_KEY='{anthropic_key}'")
        print(f"    kairos-agent --config {output_path}")
    else:
        print(f"\n  To start kairos, run:")
        print(f"    export ANTHROPIC_API_KEY='your-key'")
        print(f"    kairos-agent --config {output_path}")

    # Offer validation test
    print()
    if _prompt_yn("Run a validation test now?"):
        _run_validation(output_path, anthropic_key)


def _run_validation(config_path: str, api_key: str = "") -> None:
    """Quick validation: load config, test each source, report."""
    from kairos_agent.config import load_config

    if api_key:
        os.environ["ANTHROPIC_API_KEY"] = api_key

    try:
        config = load_config(config_path)
    except Exception as e:
        print(f"\n  ✗ Config error: {e}")
        return

    print(f"\n  Validating {config_path}...")
    print(f"  Sources: {len(config.log_sources)}")
    print(f"  Services: {len(config.services)}")
    print(f"  LLM: {config.llm.provider}/{config.llm.model}")

    from kairos_agent.sources import build_sources
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=config.context.time_window_minutes)
    sources = build_sources(config.log_sources)

    total_lines = 0
    for source in sources:
        print(f"\n  Testing {source.name}...", end=" ", flush=True)
        result = source.fetch("test-service", start, now)
        if result.error:
            print(f"✗ {result.error}")
        elif result.line_count == 0:
            print(f"⚠ Connected but 0 lines (this may be normal for 'test-service')")
        else:
            print(f"✓ {result.line_count} lines in {result.fetch_duration_ms:.0f}ms")
            total_lines += result.line_count

    print(f"\n  Total lines across all sources: {total_lines}")
    print(f"  ✓ Validation complete")
