"""Generic HTTP log source — configurable REST connector with template substitution."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from functools import reduce
from typing import Any

import httpx

from kairos_agent.sources import FetchedLines

logger = logging.getLogger("kairos_agent")


class GenericHTTPSource:
    """Fetch logs from any REST API that returns log lines.

    Supports template substitution in URL, headers, and body:
    - {service_name} — the alerting service
    - {start_iso} — time window start in ISO 8601
    - {end_iso} — time window end in ISO 8601
    - {start_epoch} — time window start as unix epoch seconds
    - {end_epoch} — time window end as unix epoch seconds
    """

    def __init__(
        self,
        url: str,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body_template: str | None = None,
        response_lines_path: str = "lines",
    ) -> None:
        self._url = url
        self._method = method.upper()
        self._headers = headers or {}
        self._body_template = body_template
        self._response_lines_path = response_lines_path

    @property
    def name(self) -> str:
        return f"http:{self._url}"

    def _substitute(self, template: str, vars: dict[str, str]) -> str:
        result = template
        for key, value in vars.items():
            result = result.replace(f"{{{key}}}", value)
        return result

    def _extract_lines(self, data: Any, path: str) -> list[str]:
        """Extract lines from response JSON using dot-notation path."""
        try:
            value = reduce(lambda d, k: d[k], path.split("."), data)
        except (KeyError, TypeError, IndexError):
            return []
        if isinstance(value, list):
            return [str(item) for item in value]
        return [str(value)]

    def fetch(
        self,
        service_name: str,
        start: datetime,
        end: datetime,
    ) -> FetchedLines:
        t0 = time.monotonic()

        template_vars = {
            "service_name": service_name,
            "start_iso": start.isoformat(),
            "end_iso": end.isoformat(),
            "start_epoch": str(int(start.timestamp())),
            "end_epoch": str(int(end.timestamp())),
        }

        url = self._substitute(self._url, template_vars)
        headers = {
            k: self._substitute(v, template_vars)
            for k, v in self._headers.items()
        }

        try:
            with httpx.Client(timeout=30) as client:
                if self._method == "GET":
                    resp = client.get(url, headers=headers)
                else:
                    body = None
                    if self._body_template:
                        body = self._substitute(self._body_template, template_vars)
                    resp = client.post(
                        url,
                        headers={**headers, "Content-Type": "application/json"},
                        content=body,
                    )

                resp.raise_for_status()
                data = resp.json()
                lines = self._extract_lines(data, self._response_lines_path)
                tagged = [f"[http:{url}] {line}" for line in lines]

        except httpx.HTTPStatusError as e:
            elapsed = (time.monotonic() - t0) * 1000
            error_msg = f"HTTP source returned {e.response.status_code}"
            logger.warning("%s for URL: %s", error_msg, url)
            return FetchedLines(
                lines=[],
                source_name=self.name,
                line_count=0,
                fetch_duration_ms=elapsed,
                error=error_msg,
            )
        except httpx.RequestError as e:
            elapsed = (time.monotonic() - t0) * 1000
            error_msg = f"HTTP request failed: {e}"
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
            "HTTP source returned %d lines from %s in %.0fms",
            len(tagged), url, elapsed,
        )
        return FetchedLines(
            lines=tagged,
            source_name=self.name,
            line_count=len(tagged),
            fetch_duration_ms=elapsed,
        )
