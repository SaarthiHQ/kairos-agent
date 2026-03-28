"""Datadog log source — fetches logs via the Datadog Logs Search API."""

from __future__ import annotations

import logging
import time
from datetime import datetime

import httpx

from kairos_agent.sources import FetchedLines

logger = logging.getLogger("kairos_agent")


class DatadogSource:
    """Fetch logs from Datadog using the Logs List API (v2)."""

    def __init__(
        self,
        api_key: str,
        app_key: str,
        site: str = "datadoghq.com",
        query_template: str = "service:{service_name}",
    ) -> None:
        self._api_key = api_key
        self._app_key = app_key
        self._site = site
        self._query_template = query_template

    @property
    def name(self) -> str:
        return f"datadog:{self._site}"

    def fetch(
        self,
        service_name: str,
        start: datetime,
        end: datetime,
    ) -> FetchedLines:
        t0 = time.monotonic()
        query = self._query_template.replace("{service_name}", service_name)

        url = f"https://api.{self._site}/api/v2/logs/events/search"
        headers = {
            "DD-API-KEY": self._api_key,
            "DD-APPLICATION-KEY": self._app_key,
            "Content-Type": "application/json",
        }
        body = {
            "filter": {
                "query": query,
                "from": start.isoformat(),
                "to": end.isoformat(),
            },
            "sort": "timestamp",
            "page": {"limit": 1000},
        }

        all_lines: list[str] = []
        cursor: str | None = None

        try:
            with httpx.Client(timeout=30) as client:
                while True:
                    if cursor:
                        body["page"]["cursor"] = cursor

                    resp = client.post(url, headers=headers, json=body)
                    resp.raise_for_status()
                    data = resp.json()

                    for log_entry in data.get("data", []):
                        attrs = log_entry.get("attributes", {})
                        ts = attrs.get("timestamp", "")
                        msg = attrs.get("message", "")
                        svc = attrs.get("service", "")
                        status = attrs.get("status", "")
                        line = f"[datadog] {ts} [{status.upper()}] {svc}: {msg}"
                        all_lines.append(line)

                    # Pagination
                    next_cursor = (
                        data.get("meta", {})
                        .get("page", {})
                        .get("after")
                    )
                    if not next_cursor or not data.get("data"):
                        break
                    cursor = next_cursor

        except httpx.HTTPStatusError as e:
            elapsed = (time.monotonic() - t0) * 1000
            error_msg = f"Datadog API returned {e.response.status_code}"
            logger.warning("%s for query: %s", error_msg, query)
            return FetchedLines(
                lines=all_lines,
                source_name=self.name,
                line_count=len(all_lines),
                fetch_duration_ms=elapsed,
                error=error_msg,
            )
        except httpx.RequestError as e:
            elapsed = (time.monotonic() - t0) * 1000
            error_msg = f"Datadog request failed: {e}"
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
            "Datadog returned %d lines for query '%s' in %.0fms",
            len(all_lines), query, elapsed,
        )
        return FetchedLines(
            lines=all_lines,
            source_name=self.name,
            line_count=len(all_lines),
            fetch_duration_ms=elapsed,
        )
