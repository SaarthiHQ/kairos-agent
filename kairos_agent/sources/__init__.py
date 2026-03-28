"""Source connectors for kairos-agent.

Each source fetches log lines from a specific backend (files, Datadog, Loki, etc.)
and returns them in a uniform format for the context assembler.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable

from kairos_agent.config import LogSource

logger = logging.getLogger("kairos_agent")


@dataclass
class FetchedLines:
    """Result from a single source fetch."""

    lines: list[str]
    source_name: str
    line_count: int
    fetch_duration_ms: float
    error: str | None = None


@runtime_checkable
class Source(Protocol):
    """Any log source that kairos can pull from."""

    @property
    def name(self) -> str: ...

    def fetch(
        self,
        service_name: str,
        start: datetime,
        end: datetime,
    ) -> FetchedLines: ...


@dataclass
class SourceResult:
    """What happened when we tried to fetch from one source."""

    source_name: str
    lines_fetched: int
    fetch_duration_ms: float
    status: str  # "ok", "empty", "error"
    error_message: str | None = None


@dataclass
class QualityAssessment:
    """Overall assessment of context quality for this incident."""

    sources_attempted: int
    sources_succeeded: int
    sources_failed: int
    sources_empty: int
    total_lines_fetched: int
    results: list[SourceResult] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)

    @property
    def coverage_ratio(self) -> float:
        if self.sources_attempted == 0:
            return 0.0
        return self.sources_succeeded / self.sources_attempted


def build_sources(log_sources: list[LogSource]) -> list[Source]:
    """Convert config LogSource entries into concrete Source instances."""
    from kairos_agent.sources.file_source import FileSource

    sources: list[Source] = []
    for ls in log_sources:
        if ls.type == "file":
            sources.append(FileSource(path=ls.path))
        elif ls.type == "datadog":
            from kairos_agent.sources.datadog_source import DatadogSource

            sources.append(DatadogSource(
                api_key=ls.credentials.get("api_key", ""),
                app_key=ls.credentials.get("app_key", ""),
                site=ls.options.get("site", "datadoghq.com"),
                query_template=ls.options.get("query", "service:{service_name}"),
            ))
        elif ls.type == "loki":
            from kairos_agent.sources.loki_source import LokiSource

            sources.append(LokiSource(
                url=ls.options.get("url", ""),
                query_template=ls.options.get("query", '{app="{service_name}"}'),
                auth_header=ls.credentials.get("auth_header"),
            ))
        elif ls.type == "newrelic":
            from kairos_agent.sources.newrelic_source import NewRelicSource

            sources.append(NewRelicSource(
                api_key=ls.credentials.get("api_key", ""),
                account_id=ls.options.get("account_id", ""),
                query_template=ls.options.get("query", "SELECT timestamp, message, level, service FROM Log WHERE service = '{service_name}'"),
                region=ls.options.get("region", "us"),
            ))
        elif ls.type == "http":
            from kairos_agent.sources.http_source import GenericHTTPSource

            sources.append(GenericHTTPSource(
                url=ls.options.get("url", ""),
                method=ls.options.get("method", "GET"),
                headers=ls.options.get("headers"),
                body_template=ls.options.get("body_template"),
                response_lines_path=ls.options.get("response_lines_path", "lines"),
            ))
        else:
            logger.warning("Unknown source type: %s — skipping", ls.type)
    return sources
