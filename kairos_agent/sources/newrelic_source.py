"""New Relic log source — fetches logs via the NerdGraph GraphQL API using NRQL."""

from __future__ import annotations

import logging
import time
from datetime import datetime

import httpx

from kairos_agent.sources import FetchedLines

logger = logging.getLogger("kairos_agent")

# NerdGraph endpoint — same for all accounts
NERDGRAPH_URL = "https://api.newrelic.com/graphql"

# EU datacenter uses a different endpoint
NERDGRAPH_EU_URL = "https://api.eu.newrelic.com/graphql"

# GraphQL query template for NRQL log queries
NRQL_QUERY_TEMPLATE = """\
{{
  actor {{
    account(id: {account_id}) {{
      nrql(query: "{nrql}") {{
        results
      }}
    }}
  }}
}}"""


class NewRelicSource:
    """Fetch logs from New Relic using NRQL queries via the NerdGraph API.

    Uses the NerdGraph GraphQL endpoint to run NRQL queries against
    the Log data type. Requires a User API key or Ingest License key.

    Config example:
        - type: newrelic
          credentials:
            api_key: "${NEW_RELIC_API_KEY}"
          options:
            account_id: "1234567"
            query: "SELECT timestamp, message, level FROM Log WHERE service = '{service_name}'"
            region: "us"  # or "eu"
    """

    def __init__(
        self,
        api_key: str,
        account_id: str,
        query_template: str = "SELECT timestamp, message, level, service FROM Log WHERE service = '{service_name}'",
        region: str = "us",
    ) -> None:
        self._api_key = api_key
        self._account_id = account_id
        self._query_template = query_template
        self._region = region.lower()

    @property
    def name(self) -> str:
        return f"newrelic:{self._account_id}"

    @property
    def _endpoint(self) -> str:
        return NERDGRAPH_EU_URL if self._region == "eu" else NERDGRAPH_URL

    def fetch(
        self,
        service_name: str,
        start: datetime,
        end: datetime,
    ) -> FetchedLines:
        t0 = time.monotonic()

        # Build NRQL query with time range via SINCE/UNTIL
        base_query = self._query_template.replace("{service_name}", service_name)
        # Add time bounds using epoch milliseconds
        since_ms = int(start.timestamp() * 1000)
        until_ms = int(end.timestamp() * 1000)
        nrql = f"{base_query} SINCE {since_ms} UNTIL {until_ms} LIMIT MAX"

        # Build GraphQL payload
        graphql_query = NRQL_QUERY_TEMPLATE.format(
            account_id=self._account_id,
            nrql=nrql.replace('"', '\\"'),
        )

        headers = {
            "Content-Type": "application/json",
            "API-Key": self._api_key,
        }

        all_lines: list[str] = []

        try:
            with httpx.Client(timeout=30) as client:
                resp = client.post(
                    self._endpoint,
                    headers=headers,
                    json={"query": graphql_query},
                )
                resp.raise_for_status()
                data = resp.json()

                # Check for GraphQL-level errors
                errors = data.get("errors")
                if errors:
                    error_msgs = "; ".join(e.get("message", str(e)) for e in errors)
                    elapsed = (time.monotonic() - t0) * 1000
                    logger.warning("NerdGraph returned errors: %s", error_msgs)
                    return FetchedLines(
                        lines=[],
                        source_name=self.name,
                        line_count=0,
                        fetch_duration_ms=elapsed,
                        error=f"NerdGraph errors: {error_msgs}",
                    )

                # Extract results from the nested GraphQL response
                results = (
                    data.get("data", {})
                    .get("actor", {})
                    .get("account", {})
                    .get("nrql", {})
                    .get("results", [])
                )

                for row in results:
                    ts = row.get("timestamp", "")
                    msg = row.get("message", "")
                    level = row.get("level", "INFO")
                    svc = row.get("service", service_name)
                    # Format timestamp if it's epoch ms
                    if isinstance(ts, (int, float)):
                        ts = datetime.fromtimestamp(ts / 1000).strftime(
                            "%Y-%m-%dT%H:%M:%S"
                        )
                    line = f"[newrelic] {ts} [{level.upper()}] {svc}: {msg}"
                    all_lines.append(line)

        except httpx.HTTPStatusError as e:
            elapsed = (time.monotonic() - t0) * 1000
            error_msg = f"New Relic API returned {e.response.status_code}"
            logger.warning("%s", error_msg)
            return FetchedLines(
                lines=[],
                source_name=self.name,
                line_count=0,
                fetch_duration_ms=elapsed,
                error=error_msg,
            )
        except httpx.RequestError as e:
            elapsed = (time.monotonic() - t0) * 1000
            error_msg = f"New Relic request failed: {e}"
            logger.warning(error_msg)
            return FetchedLines(
                lines=[],
                source_name=self.name,
                line_count=0,
                fetch_duration_ms=elapsed,
                error=error_msg,
            )

        elapsed = (time.monotonic() - t0) * 1000
        logger.info(
            "New Relic returned %d lines for account %s in %.0fms",
            len(all_lines), self._account_id, elapsed,
        )
        return FetchedLines(
            lines=all_lines,
            source_name=self.name,
            line_count=len(all_lines),
            fetch_duration_ms=elapsed,
        )
