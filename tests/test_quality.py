"""Tests for quality assessment logic."""

from pathlib import Path

from kairos_agent.config import ContextConfig, LogSource
from kairos_agent.context_assembler import assemble_context


def test_quality_all_sources_ok(tmp_path: Path) -> None:
    log1 = tmp_path / "app.log"
    log1.write_text("2026-03-26T14:01:00Z [ERROR] payment-service: timeout\n")
    log2 = tmp_path / "sys.log"
    log2.write_text("2026-03-26T14:01:00Z [INFO] payment-service: healthy\n")

    alert_info = {
        "service_name": "payment-service",
        "triggered_at": "2026-03-26T14:03:00Z",
        "title": "High error rate",
    }
    log_sources = [
        LogSource(type="file", path=str(log1)),
        LogSource(type="file", path=str(log2)),
    ]
    config = ContextConfig(time_window_minutes=5, max_log_lines=100)

    context = assemble_context(alert_info, log_sources, config)
    assert context.quality is not None
    assert context.quality.sources_attempted == 2
    assert context.quality.sources_succeeded == 2
    assert context.quality.sources_failed == 0
    assert context.quality.coverage_ratio == 1.0


def test_quality_partial_failure(tmp_path: Path) -> None:
    log1 = tmp_path / "app.log"
    log1.write_text("2026-03-26T14:01:00Z [ERROR] svc: timeout\n")

    alert_info = {
        "service_name": "svc",
        "triggered_at": "2026-03-26T14:03:00Z",
        "title": "Issue",
    }
    log_sources = [
        LogSource(type="file", path=str(log1)),
        LogSource(type="file", path="/nonexistent/*.log"),
    ]
    config = ContextConfig(time_window_minutes=5, max_log_lines=100)

    context = assemble_context(alert_info, log_sources, config)
    assert context.quality is not None
    assert context.quality.sources_attempted == 2
    assert context.quality.sources_succeeded == 1
    assert context.quality.sources_failed == 1
    assert len(context.quality.gaps) >= 1
    assert any("No files matched" in g for g in context.quality.gaps)


def test_quality_empty_source(tmp_path: Path) -> None:
    empty_log = tmp_path / "empty.log"
    empty_log.write_text("")

    alert_info = {
        "service_name": "svc",
        "triggered_at": "2026-03-26T14:03:00Z",
        "title": "Issue",
    }
    log_sources = [LogSource(type="file", path=str(empty_log))]
    config = ContextConfig(time_window_minutes=5, max_log_lines=100)

    context = assemble_context(alert_info, log_sources, config)
    assert context.quality is not None
    assert context.quality.sources_empty == 1
    assert any("returned 0 lines" in g for g in context.quality.gaps)


def test_quality_no_errors_on_error_alert(tmp_path: Path) -> None:
    log = tmp_path / "app.log"
    log.write_text("2026-03-26T14:01:00Z [INFO] svc: all good\n")

    alert_info = {
        "service_name": "svc",
        "triggered_at": "2026-03-26T14:03:00Z",
        "title": "High error rate on svc",
    }
    log_sources = [LogSource(type="file", path=str(log))]
    config = ContextConfig(time_window_minutes=5, max_log_lines=100)

    context = assemble_context(alert_info, log_sources, config)
    assert context.quality is not None
    assert any("No ERROR-level lines found" in g for g in context.quality.gaps)


def test_quality_single_source_type_gap(tmp_path: Path) -> None:
    log = tmp_path / "app.log"
    log.write_text("2026-03-26T14:01:00Z [ERROR] svc: timeout\n")

    alert_info = {
        "service_name": "svc",
        "triggered_at": "2026-03-26T14:03:00Z",
        "title": "Issue",
    }
    log_sources = [LogSource(type="file", path=str(log))]
    config = ContextConfig(time_window_minutes=5, max_log_lines=100)

    context = assemble_context(alert_info, log_sources, config)
    assert context.quality is not None
    assert any("Only file sources configured" in g for g in context.quality.gaps)


def test_context_includes_quality(tmp_path: Path) -> None:
    log = tmp_path / "app.log"
    log.write_text("2026-03-26T14:01:00Z [INFO] svc: ok\n")

    alert_info = {
        "service_name": "svc",
        "triggered_at": "2026-03-26T14:03:00Z",
        "title": "Test",
    }
    log_sources = [LogSource(type="file", path=str(log))]
    config = ContextConfig(time_window_minutes=5, max_log_lines=100)

    context = assemble_context(alert_info, log_sources, config)
    assert context.quality is not None
    assert context.quality.sources_attempted == 1
    assert context.quality.total_lines_fetched == 1
