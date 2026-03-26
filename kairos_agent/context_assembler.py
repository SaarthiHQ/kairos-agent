"""Assemble relevant log context for an incident.

This module is the core intelligence of kairos-agent. It reads log sources,
filters by time window and service name, and returns the most relevant lines.

Designed to be swappable — v0.2 will add Datadog/Grafana sources.
"""

from __future__ import annotations

import glob
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from kairos_agent.config import ContextConfig, LogSource

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


def _score_line(line: str, service_name: str) -> int:
    """Score a log line by relevance. Higher = more relevant."""
    score = 0
    if ERROR_INDICATORS.search(line):
        score += 10
    if service_name.lower() in line.lower():
        score += 5
    # Stack trace continuations are valuable context
    if line.strip().startswith("at ") or line.strip().startswith("File "):
        score += 3
    return score


def _read_file_source(source: LogSource) -> list[str]:
    """Read all lines from a file-based log source (supports globs)."""
    all_lines: list[str] = []
    matched_paths = sorted(glob.glob(source.path))

    if not matched_paths:
        logger.warning("No files matched log source pattern: %s", source.path)
        return all_lines

    for file_path in matched_paths:
        path = Path(file_path)
        if not path.is_file():
            continue
        try:
            lines = path.read_text(errors="replace").splitlines()
            # Tag each line with its source file for context
            all_lines.extend(
                f"[{path.name}] {line}" for line in lines
            )
        except OSError as e:
            logger.warning("Could not read %s: %s", file_path, e)

    return all_lines


def assemble_context(
    alert_info: dict,
    log_sources: list[LogSource],
    config: ContextConfig,
) -> LogContext:
    """Pull and filter logs relevant to an incident.

    Strategy:
    1. Read all lines from configured log sources
    2. Filter to the time window (if timestamps are parseable)
    3. Boost lines mentioning the affected service or error keywords
    4. Return top N lines sorted by relevance, preserving order
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

    all_lines: list[str] = []
    sources_checked: list[str] = []

    for source in log_sources:
        if source.type == "file":
            lines = _read_file_source(source)
            all_lines.extend(lines)
            sources_checked.append(source.path)
        else:
            logger.warning("Unsupported log source type: %s", source.type)

    total_scanned = len(all_lines)

    # Filter by time window and score by relevance
    scored_lines: list[tuple[int, int, str]] = []  # (score, original_index, line)

    for idx, line in enumerate(all_lines):
        ts = parse_timestamp(line)
        in_window = True

        if ts is not None:
            in_window = window_start <= ts <= window_end

        if in_window:
            score = _score_line(line, service_name)
            scored_lines.append((score, idx, line))

    # Sort by score descending, then by original order for ties
    scored_lines.sort(key=lambda x: (-x[0], x[1]))

    # Take top N lines, then re-sort by original order for readability
    top_lines = scored_lines[: config.max_log_lines]
    top_lines.sort(key=lambda x: x[1])

    error_count = sum(
        1 for score, _, _ in top_lines if score >= 10
    )

    return LogContext(
        service_name=service_name,
        time_window_start=window_start.isoformat(),
        time_window_end=window_end.isoformat(),
        log_lines=[line for _, _, line in top_lines],
        total_lines_scanned=total_scanned,
        sources_checked=sources_checked,
        error_count=error_count,
    )
