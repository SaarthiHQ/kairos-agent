"""Assemble relevant log context for an incident.

This module is the core intelligence of kairos-agent. It pulls logs from
configured sources, filters by time window and service name, and returns
the most relevant lines with a quality assessment.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum

from kairos_agent.compressor import compress_lines
from kairos_agent.config import ContextConfig, LogSource, ServiceConfig
from kairos_agent.sources import (
    QualityAssessment,
    SourceResult,
    build_sources,
)
from kairos_agent.service_catalog import ResolvedSource

logger = logging.getLogger("kairos_agent")

# Common log timestamp patterns (ISO 8601, syslog-style, etc.)
TIMESTAMP_PATTERNS = [
    # ISO 8601: 2024-01-15T10:30:45Z or 2024-01-15T10:30:45.123+00:00
    (
        r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)",
        "%Y-%m-%dT%H:%M:%S",
    ),
    # Common log format: 15/Jan/2024:10:30:45 +0000
    (
        r"(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2})",
        "%d/%b/%Y:%H:%M:%S",
    ),
    # Syslog-like: Jan 15 10:30:45
    (
        r"(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})",
        None,  # handled specially since no year
    ),
    # Simple datetime: 2024-01-15 10:30:45
    (
        r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})",
        "%Y-%m-%d %H:%M:%S",
    ),
]

# Patterns that indicate error-level severity
ERROR_INDICATORS = re.compile(
    r"\b(ERROR|FATAL|CRITICAL|PANIC|EXCEPTION|Traceback|"
    r"OOMKilled|segfault|SIGSEGV|SIGKILL|"
    r"timeout|refused|unreachable|failed|crash)\b",
    re.IGNORECASE,
)


class AlertType(str, Enum):
    ERROR_RATE = "error_rate"
    LATENCY = "latency"
    AVAILABILITY = "availability"
    UNKNOWN = "unknown"


ALERT_TYPE_KEYWORDS: dict[AlertType, list[str]] = {
    AlertType.ERROR_RATE: ["error", "exception", "fatal", "5xx", "4xx", "failure rate"],
    AlertType.LATENCY: ["latency", "slow", "timeout", "p99", "p95", "p50", "duration", "response time", "apdex"],
    AlertType.AVAILABILITY: ["down", "unreachable", "health check", "oom", "connection refused", "unavailable", "uptime"],
}

ALERT_TYPE_BOOST_PATTERNS: dict[AlertType, list[tuple[re.Pattern, int]]] = {
    AlertType.ERROR_RATE: [
        (re.compile(r"\b(Traceback|caused\s*by|RuntimeError|ValueError|NullPointer)\b", re.I), 8),
        (re.compile(r"\b(stack\s*trace|EXCEPTION)\b", re.I), 5),
    ],
    AlertType.LATENCY: [
        (re.compile(r"\b(timeout|timed?\s*out|slow|latency|duration)\b", re.I), 8),
        (re.compile(r"\b(p99|p95|p50|response.time|elapsed|took\s+\d+\s*m?s)\b", re.I), 5),
        (re.compile(r"\b(deadline.exceeded|context.deadline|read.timeout)\b", re.I), 6),
    ],
    AlertType.AVAILABILITY: [
        (re.compile(r"\b(connection.refused|unreachable|ECONNREFUSED)\b", re.I), 8),
        (re.compile(r"\b(health.check|readiness|liveness|OOM|OOMKilled)\b", re.I), 7),
        (re.compile(r"\b(SIGKILL|SIGSEGV|segfault|crash|restarting)\b", re.I), 6),
    ],
}


def infer_alert_type(alert_info: dict) -> AlertType:
    """Infer alert type from title keywords or explicit field."""
    explicit = alert_info.get("alert_type")
    if explicit:
        try:
            return AlertType(explicit)
        except ValueError:
            pass

    title = alert_info.get("title", "").lower()
    scores: dict[AlertType, int] = {t: 0 for t in AlertType}
    for alert_type, keywords in ALERT_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in title:
                scores[alert_type] += 1

    best = max(scores, key=lambda t: scores[t])
    return best if scores[best] > 0 else AlertType.UNKNOWN


@dataclass
class LogContext:
    """Assembled log context ready for summarization."""
    service_name: str
    time_window_start: str
    time_window_end: str
    log_lines: list[str]
    total_lines_scanned: int
    sources_checked: list[str]
    error_count: int
    quality: QualityAssessment | None = None
    alert_type: str = "unknown"
    service_tier: str = "standard"
    service_owners: list[str] = field(default_factory=list)
    dependency_services: list[str] = field(default_factory=list)
    dependency_log_lines: list[str] = field(default_factory=list)


def parse_timestamp(line: str) -> datetime | None:
    """Try to extract a timestamp from a log line."""
    for pattern, fmt in TIMESTAMP_PATTERNS:
        match = re.search(pattern, line)
        if match:
            ts_str = match.group(1)
            try:
                if fmt is None:
                    # Syslog without year — assume current year
                    ts_str_with_year = f"{datetime.now().year} {ts_str}"
                    return datetime.strptime(
                        ts_str_with_year, "%Y %b %d %H:%M:%S"
                    ).replace(tzinfo=timezone.utc)

                # Strip fractional seconds and timezone for parsing
                clean = re.sub(r"\.\d+", "", ts_str)
                clean = re.sub(r"Z$", "", clean)
                clean = re.sub(r"[+-]\d{2}:?\d{2}$", "", clean)
                dt = datetime.strptime(clean, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return None


def _score_line(
    line: str,
    service_name: str,
    alert_type: AlertType = AlertType.UNKNOWN,
) -> int:
    """Score a log line by relevance. Higher = more relevant."""
    score = 0
    if ERROR_INDICATORS.search(line):
        score += 10
    if service_name.lower() in line.lower():
        score += 5
    # Stack trace continuations are valuable context
    if line.strip().startswith("at ") or line.strip().startswith("File "):
        score += 3
    # Alert-type-specific boosts
    for pattern, boost in ALERT_TYPE_BOOST_PATTERNS.get(alert_type, []):
        if pattern.search(line):
            score += boost
    return score


def _assess_quality(
    results: list[SourceResult],
    alert_info: dict,
    error_count: int,
) -> QualityAssessment:
    """Assess the quality and completeness of assembled context."""
    succeeded = sum(1 for r in results if r.status == "ok")
    failed = sum(1 for r in results if r.status == "error")
    empty = sum(1 for r in results if r.status == "empty")
    total_lines = sum(r.lines_fetched for r in results)

    gaps: list[str] = []

    if succeeded == 0 and len(results) > 0:
        gaps.append("CRITICAL: No log sources returned data — check source configuration and credentials")

    for r in results:
        if r.status == "error":
            gaps.append(f"{r.source_name}: {r.error_message}")
        elif r.status == "empty":
            gaps.append(f"{r.source_name}: returned 0 lines — verify query template or check if the service logs to this source")

    title = alert_info.get("title", "").lower()
    if error_count == 0 and any(
        kw in title for kw in ("error", "fatal", "critical", "exception")
    ):
        gaps.append(
            "No ERROR-level lines found despite error-related alert — check if log levels are set correctly or if errors are logged to a different source"
        )

    # Progressive disclosure: suggest what to add based on what's missing
    source_types = {r.source_name.split(":")[0] for r in results}
    has_logs = "file" in source_types or "datadog" in source_types or "loki" in source_types
    has_metrics = any("metric" in r.source_name.lower() for r in results)

    if len(source_types) == 1:
        only_type = next(iter(source_types))
        suggestions = []
        if only_type == "file":
            suggestions.append("a centralized log platform (Datadog, Loki) for richer querying")
        if not has_metrics:
            suggestions.append("a metrics source for CPU/memory/latency correlation")
        suggest_str = " and ".join(suggestions) if suggestions else "other sources"
        gaps.append(
            f"Only {only_type} sources configured — consider adding {suggest_str}"
        )

    return QualityAssessment(
        sources_attempted=len(results),
        sources_succeeded=succeeded,
        sources_failed=failed,
        sources_empty=empty,
        total_lines_fetched=total_lines,
        results=results,
        gaps=gaps,
    )


def _fetch_and_score(
    sources_to_fetch: list[tuple[str, list]],  # (relationship, list of Source objects)
    service_name: str,
    window_start: datetime,
    window_end: datetime,
    alert_type: AlertType,
    config: ContextConfig,
) -> tuple[list[str], list[str], list[SourceResult], list[str], int]:
    """Fetch from sources, score and select lines within token budget.

    Returns: (direct_lines, dep_lines, source_results, sources_checked, total_scanned)
    """
    source_results: list[SourceResult] = []
    direct_scored: list[tuple[int, int, str]] = []
    dep_scored: list[tuple[int, int, str]] = []
    sources_checked: list[str] = []
    global_idx = 0

    for relationship, source_list in sources_to_fetch:
        for source in source_list:
            fetched = source.fetch(service_name, window_start, window_end)
            status = "error" if fetched.error else ("empty" if not fetched.lines else "ok")
            source_results.append(SourceResult(
                source_name=fetched.source_name,
                lines_fetched=fetched.line_count,
                fetch_duration_ms=fetched.fetch_duration_ms,
                status=status,
                error_message=fetched.error,
            ))
            sources_checked.append(fetched.source_name)

            # Level 1 compression: dedup and collapse before scoring
            compressed = compress_lines(fetched.lines)

            for line in compressed:
                ts = parse_timestamp(line)
                in_window = ts is None or (window_start <= ts <= window_end)
                if in_window:
                    score = _score_line(line, service_name, alert_type)
                    if relationship == "dependency":
                        # Penalty: dep lines compete at 70% score
                        score = int(score * 0.7)
                    target = direct_scored if relationship == "direct" else dep_scored
                    target.append((score, global_idx, line))
                global_idx += 1

    total_scanned = global_idx

    # Select top lines within token budget — direct lines first, then deps
    all_scored = sorted(direct_scored, key=lambda x: (-x[0], x[1]))
    dep_sorted = sorted(dep_scored, key=lambda x: (-x[0], x[1]))

    top_direct: list[tuple[int, int, str]] = []
    token_count = 0
    for entry in all_scored[: config.max_log_lines]:
        line_tokens = len(entry[2]) // 4 + 1
        if token_count + line_tokens > config.max_context_tokens:
            break
        top_direct.append(entry)
        token_count += line_tokens

    # Use remaining token budget for dependency lines
    dep_budget = config.max_context_tokens - token_count
    top_dep: list[tuple[int, int, str]] = []
    dep_tokens = 0
    for entry in dep_sorted:
        line_tokens = len(entry[2]) // 4 + 1
        if dep_tokens + line_tokens > dep_budget:
            break
        top_dep.append(entry)
        dep_tokens += line_tokens

    # Re-sort by original order for readability
    top_direct.sort(key=lambda x: x[1])
    top_dep.sort(key=lambda x: x[1])

    direct_lines = [line for _, _, line in top_direct]
    dep_lines = [line for _, _, line in top_dep]

    return direct_lines, dep_lines, source_results, sources_checked, total_scanned


def assemble_context(
    alert_info: dict,
    log_sources: list[LogSource],
    config: ContextConfig,
    *,
    resolved_sources: list[ResolvedSource] | None = None,
    alert_type: AlertType = AlertType.UNKNOWN,
    service_metadata: ServiceConfig | None = None,
) -> LogContext:
    """Pull and filter logs relevant to an incident.

    When resolved_sources is provided (from the service catalog),
    uses those instead of all log_sources. Dependency lines are
    kept separate and scored with a penalty.
    """
    service_name = alert_info.get("service_name", "unknown")
    triggered_at_str = alert_info.get("triggered_at", "")

    try:
        triggered_at = datetime.fromisoformat(
            triggered_at_str.replace("Z", "+00:00")
        )
    except (ValueError, TypeError):
        triggered_at = datetime.now(timezone.utc)

    window_start = triggered_at - timedelta(minutes=config.time_window_minutes)
    window_end = triggered_at

    # Build source list — either from catalog or fallback to all
    if resolved_sources is not None:
        direct_ls = [rs.log_source for rs in resolved_sources if rs.relationship == "direct"]
        dep_ls = [rs.log_source for rs in resolved_sources if rs.relationship == "dependency"]
        direct_sources = build_sources(direct_ls)
        dep_sources = build_sources(dep_ls)
        sources_to_fetch = [("direct", direct_sources), ("dependency", dep_sources)]
        dep_service_names = list({
            rs.origin_service for rs in resolved_sources if rs.relationship == "dependency"
        })
    else:
        all_sources = build_sources(log_sources)
        sources_to_fetch = [("direct", all_sources)]
        dep_service_names = []

    direct_lines, dep_lines, source_results, sources_checked, total_scanned = _fetch_and_score(
        sources_to_fetch, service_name, window_start, window_end, alert_type, config,
    )

    error_count = sum(
        1 for line in direct_lines if ERROR_INDICATORS.search(line)
    )

    quality = _assess_quality(source_results, alert_info, error_count)

    return LogContext(
        service_name=service_name,
        time_window_start=window_start.isoformat(),
        time_window_end=window_end.isoformat(),
        log_lines=direct_lines,
        total_lines_scanned=total_scanned,
        sources_checked=sources_checked,
        error_count=error_count,
        quality=quality,
        alert_type=alert_type.value,
        service_tier=service_metadata.tier if service_metadata else "standard",
        service_owners=service_metadata.owners if service_metadata else [],
        dependency_services=dep_service_names,
        dependency_log_lines=dep_lines,
    )
