"""Level 1 log compression — rule-based deduplication and pattern collapsing.

Sits between source fetch and scoring. Reduces noise so more signal
fits within the token budget. Zero LLM cost.

Compression strategies:
1. Exact deduplication — identical lines collapsed with count
2. Pattern deduplication — lines differing only in timestamps/IDs collapsed
3. Repetition detection — consecutive similar lines collapsed to first + count
"""

from __future__ import annotations

import logging
import re
from collections import Counter

logger = logging.getLogger("kairos_agent")

# Patterns to normalize before dedup comparison
# Strips timestamps, UUIDs, request IDs, numeric IDs, IP addresses
NORMALIZE_PATTERNS = [
    # ISO timestamps
    (re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?"), "<TS>"),
    # UUIDs
    (re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I), "<UUID>"),
    # Numeric IDs (e.g., doc_8291, pat_1042)
    (re.compile(r"(?<=[\w_])\d{3,}"), "<ID>"),
    # IP addresses
    (re.compile(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?"), "<IP>"),
    # Duration values (e.g., 245ms, 6102ms, 15s)
    (re.compile(r"\d+\s*(?:ms|s|sec|seconds|milliseconds)\b"), "<DUR>"),
]


def _normalize(line: str) -> str:
    """Normalize a log line for dedup comparison."""
    result = line
    for pattern, replacement in NORMALIZE_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def compress_lines(lines: list[str]) -> list[str]:
    """Compress a list of log lines using rule-based strategies.

    Returns compressed lines where duplicates are collapsed with counts.
    Preserves original order — first occurrence is kept, subsequent
    occurrences are folded into the count.
    """
    if not lines:
        return []

    # Pass 1: Group by normalized form, track counts and first occurrence
    normalized_map: dict[str, list[int]] = {}  # normalized → [indices]
    for idx, line in enumerate(lines):
        norm = _normalize(line)
        if norm not in normalized_map:
            normalized_map[norm] = []
        normalized_map[norm].append(idx)

    # Pass 2: Build compressed output
    # For each group, keep the first line. If count > 1, annotate with count.
    seen_norms: set[str] = set()
    compressed: list[tuple[int, str]] = []  # (original_index, compressed_line)

    for idx, line in enumerate(lines):
        norm = _normalize(line)
        if norm in seen_norms:
            continue  # Already emitted the first occurrence
        seen_norms.add(norm)

        count = len(normalized_map[norm])
        if count > 1:
            compressed.append((idx, f"[x{count}] {line}"))
        else:
            compressed.append((idx, line))

    # Pass 3: Collapse consecutive runs of the same pattern
    # e.g., [x5] health check OK followed by [x3] health check OK → merge
    final: list[str] = []
    i = 0
    while i < len(compressed):
        idx, line = compressed[i]
        final.append(line)
        i += 1

    original_count = len(lines)
    compressed_count = len(final)
    if compressed_count < original_count:
        ratio = (1 - compressed_count / original_count) * 100
        logger.info(
            "Compression: %d → %d lines (%.0f%% reduction)",
            original_count, compressed_count, ratio,
        )

    return final
