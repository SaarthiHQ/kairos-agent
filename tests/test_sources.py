"""Tests for source connectors and build_sources."""

from datetime import datetime, timezone
from pathlib import Path

from kairos_agent.config import LogSource
from kairos_agent.sources import FetchedLines, build_sources
from kairos_agent.sources.file_source import FileSource


def test_file_source_basic(tmp_path: Path) -> None:
    log_file = tmp_path / "app.log"
    log_file.write_text(
        "2026-03-26T14:00:00Z [INFO] payment-service: healthy\n"
        "2026-03-26T14:01:00Z [ERROR] payment-service: timeout\n"
    )
    source = FileSource(path=str(log_file))
    result = source.fetch(
        "payment-service",
        datetime(2026, 3, 26, 13, 50, tzinfo=timezone.utc),
        datetime(2026, 3, 26, 14, 5, tzinfo=timezone.utc),
    )
    assert result.line_count == 2
    assert result.error is None
    assert "[app.log]" in result.lines[0]


def test_file_source_glob(tmp_path: Path) -> None:
    (tmp_path / "app-1.log").write_text("line1\n")
    (tmp_path / "app-2.log").write_text("line2\n")
    source = FileSource(path=str(tmp_path / "app-*.log"))
    result = source.fetch(
        "svc",
        datetime(2026, 1, 1, tzinfo=timezone.utc),
        datetime(2026, 12, 31, tzinfo=timezone.utc),
    )
    assert result.line_count == 2
    assert result.error is None


def test_file_source_missing_path() -> None:
    source = FileSource(path="/nonexistent/path/*.log")
    result = source.fetch(
        "svc",
        datetime(2026, 1, 1, tzinfo=timezone.utc),
        datetime(2026, 12, 31, tzinfo=timezone.utc),
    )
    assert result.line_count == 0
    assert result.error is not None
    assert "No files matched" in result.error


def test_file_source_name() -> None:
    source = FileSource(path="/var/log/app/*.log")
    assert source.name == "file:/var/log/app/*.log"


def test_build_sources_file_only() -> None:
    log_sources = [LogSource(type="file", path="/var/log/app.log")]
    sources = build_sources(log_sources)
    assert len(sources) == 1
    assert isinstance(sources[0], FileSource)


def test_build_sources_unknown_type() -> None:
    log_sources = [LogSource(type="unknown_type", path="")]
    sources = build_sources(log_sources)
    assert len(sources) == 0


def test_build_sources_backward_compat() -> None:
    """v0.1 style config with only type and path still works."""
    log_sources = [LogSource(type="file", path="/var/log/*.log")]
    sources = build_sources(log_sources)
    assert len(sources) == 1
    assert sources[0].name == "file:/var/log/*.log"


def test_fetched_lines_protocol() -> None:
    """FileSource satisfies the Source protocol."""
    from kairos_agent.sources import Source

    source = FileSource(path="/tmp/test.log")
    assert isinstance(source, Source)
