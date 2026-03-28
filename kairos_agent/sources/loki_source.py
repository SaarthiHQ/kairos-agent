"""Grafana Loki log source — fetches logs via the Loki HTTP API."""

from __future__ import annotations

import logging
import time
from datetime import datetime

import httpx

from kairos_agent.sources import FetchedLines

logger = logging.getLogger("kairos_agent")


class LokiSource:
    """Fetch logs from Grafana Loki using the query_range API."""

    def __init__(
        self,
        url: str,
        query_template: str = '{app="{service_name}"}',
        auth_header: str | None = None,
    ) -> None:
        self._url = url.rstrip("/")
        self._query_template = query_template
        self._auth_header = auth_header

    @property
    def name(self) -> str:
        return f"loki:{self._url}"

    def fetch(
        self,
        service_name: str,
        start: datetime,
        end: datetime,
    ) -> FetchedLines:
        t0 = time.monotonic()
        query = self._query_template.replace("{service_name}", service_name)

        # Loki expects nanosecond epoch timestamps
        start_ns = str(int(start.timestamp() * 1_000_000_000))
        end_ns = str(int(end.timestamp() * 1_000_000_000))

        endpoint = f"{self._url}/loki/api/v1/query_range"
        params = {
            "query": query,
            "start": start_ns,
            "end": end_ns,
            "limit": 5000,
            "direction": "forward",
        }
        headers: dict[str, str] = {}
        if self._auth_header:
            headers["Authorization"] = self._auth_header

        all_lines: list[str] = []

        try:
            with httpx.Client(timeout=30) as client:
                resp = client.get(endpoint, params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()

                for stream in data.get("data", {}).get("result", []):
                    stream_labels = stream.get("stream", {})
                    label_str = ",".join(
                        f"{k}={v}" for k, v in stream_labels.items()
                    )
                    for ts_ns, line in stream.get("values", []):
                        # Convert nanosecond timestamp to ISO
                        ts_sec = int(ts_ns) / 1_000_000_000
                        ts = datetime.fromtimestamp(ts_sec).strftime(
                            "%Y-%m-%dT%H:%M:%S"
                        )
                        all_lines.append(f"[loki:{label_str}] {ts} {line}")

        except httpx.HTTPStatusError as e:
            elapsed = (time.monotonic() - t0) * 1000
            error_msg = f"Loki API returned {e.response.status_code}"
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
            error_msg = f"Loki request failed: {e}"
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
            "Loki returned %d lines for query '%s' in %.0fms",
            len(all_lines), query, elapsed,
        )
        return FetchedLines(
            lines=all_lines,
            source_name=self.name,
            line_count=len(all_lines),
            fetch_duration_ms=elapsed,
        )
