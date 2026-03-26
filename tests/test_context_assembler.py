"""Tests for context assembly."""

import tempfile
from pathlib import Path

import pytest

from kairos_agent.config import ContextConfig, LogSource
from kairos_agent.context_assembler import (
    LogContext,
    assemble_context,
    parse_timestamp,
)


def test_parse_iso_timestamp():
    ts = parse_timestamp("2026-03-26T14:01:45Z [ERROR] something failed")
    assert ts is not None
    assert ts.year == 2026
    assert ts.month == 3
    assert ts.hour == 14
    assert ts.minute == 1


def test_parse_simple_datetime():
    ts = parse_timestamp("2026-03-26 14:01:45 ERROR something failed")
    assert ts is not None
    assert ts.year == 2026


def test_parse_no_timestamp():
    ts = parse_timestamp("  at PaymentProcessor.charge (payment_processor.py:142)")
    assert ts is None


def test_assemble_context_from_file(tmp_path):
    log_file = tmp_path / "test.log"
    log_file.write_text(
        "2026-03-26T14:00:00Z [INFO] payment-service: all good\n"
        "2026-03-26T14:01:00Z [ERROR] payment-service: Stripe timeout\n"
        "2026-03-26T14:02:00Z [ERROR] payment-service: Circuit breaker OPEN\n"
        "2026-03-26T13:00:00Z [INFO] payment-service: old log line outside window\n"
    )

    alert_info = {
        "service_name": "payment-service",
        "triggered_at": "2026-03-26T14:03:00Z",
    }
    log_sources = [LogSource(type="file", path=str(log_file))]
    config = ContextConfig(time_window_minutes=5, max_log_lines=100)

    context = assemble_context(alert_info, log_sources, config)

    assert context.service_name == "payment-service"
    assert context.total_lines_scanned == 4
    # The old log line should be filtered out (outside 5-min window)
    assert len(context.log_lines) == 3
    assert context.error_count == 2


def test_assemble_context_empty_logs(tmp_path):
    log_file = tmp_path / "empty.log"
    log_file.write_text("")

    alert_info = {
        "service_name": "api",
        "triggered_at": "2026-03-26T14:00:00Z",
    }
    log_sources = [LogSource(type="file", path=str(log_file))]
    config = ContextConfig(time_window_minutes=15, max_log_lines=100)

    context = assemble_context(alert_info, log_sources, config)
    assert context.log_lines == []
    assert context.total_lines_scanned == 0


def test_assemble_context_respects_max_lines(tmp_path):
    log_file = tmp_path / "big.log"
    lines = [
        f"2026-03-26T14:0{i % 5}:00Z [ERROR] svc: error line {i}\n"
        for i in range(50)
    ]
    log_file.write_text("".join(lines))

    alert_info = {
        "service_name": "svc",
        "triggered_at": "2026-03-26T14:05:00Z",
    }
    log_sources = [LogSource(type="file", path=str(log_file))]
    config = ContextConfig(time_window_minutes=10, max_log_lines=10)

    context = assemble_context(alert_info, log_sources, config)
    assert len(context.log_lines) <= 10
