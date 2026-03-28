"""Tests for Level 1 log compression."""

from kairos_agent.compressor import compress_lines, _normalize


def test_exact_dedup() -> None:
    lines = [
        "2026-03-29T10:00:00Z [INFO] svc: health check OK",
        "2026-03-29T10:00:01Z [INFO] svc: health check OK",
        "2026-03-29T10:00:02Z [INFO] svc: health check OK",
    ]
    result = compress_lines(lines)
    assert len(result) == 1
    assert "[x3]" in result[0]


def test_pattern_dedup_different_ids() -> None:
    lines = [
        "2026-03-29T10:00:00Z [ERROR] svc: Extraction failed doc_id=doc_8291",
        "2026-03-29T10:00:01Z [ERROR] svc: Extraction failed doc_id=doc_8292",
        "2026-03-29T10:00:02Z [ERROR] svc: Extraction failed doc_id=doc_8293",
    ]
    result = compress_lines(lines)
    assert len(result) == 1
    assert "[x3]" in result[0]


def test_pattern_dedup_different_durations() -> None:
    lines = [
        "Request completed in 245ms",
        "Request completed in 312ms",
        "Request completed in 189ms",
    ]
    result = compress_lines(lines)
    assert len(result) == 1
    assert "[x3]" in result[0]


def test_unique_lines_preserved() -> None:
    lines = [
        "2026-03-29T10:00:00Z [ERROR] svc: Stripe timeout",
        "2026-03-29T10:00:01Z [CRITICAL] svc: Pipeline stalled",
        "2026-03-29T10:00:02Z [ERROR] svc: D1 database locked",
    ]
    result = compress_lines(lines)
    assert len(result) == 3
    assert all("[x" not in line for line in result)


def test_mixed_dedup_and_unique() -> None:
    lines = [
        "2026-03-29T10:00:00Z [INFO] svc: health check OK",
        "2026-03-29T10:00:01Z [INFO] svc: health check OK",
        "2026-03-29T10:00:02Z [ERROR] svc: Stripe timeout",
        "2026-03-29T10:00:03Z [INFO] svc: health check OK",
    ]
    result = compress_lines(lines)
    assert len(result) == 2  # health check (x3) + Stripe timeout
    health_line = [l for l in result if "health check" in l][0]
    assert "[x3]" in health_line


def test_empty_input() -> None:
    assert compress_lines([]) == []


def test_single_line() -> None:
    lines = ["one line only"]
    result = compress_lines(lines)
    assert result == ["one line only"]


def test_normalize_strips_timestamps() -> None:
    norm = _normalize("2026-03-29T10:00:00Z [ERROR] svc: failed")
    assert "2026-03-29" not in norm
    assert "<TS>" in norm


def test_normalize_strips_uuids() -> None:
    norm = _normalize("Request failed for id=550e8400-e29b-41d4-a716-446655440000")
    assert "550e8400" not in norm
    assert "<UUID>" in norm


def test_normalize_strips_ips() -> None:
    norm = _normalize("Connection refused to 10.0.1.42:5432")
    assert "10.0.1.42" not in norm
    assert "<IP>" in norm


def test_preserves_first_occurrence() -> None:
    """The first occurrence (with original timestamp) is kept."""
    lines = [
        "2026-03-29T10:00:00Z [INFO] first occurrence",
        "2026-03-29T10:00:05Z [INFO] first occurrence",
    ]
    result = compress_lines(lines)
    assert "10:00:00" in result[0]  # first timestamp preserved
