"""Tests for config loading."""

import os
import tempfile
from pathlib import Path

import pytest

from kairos_agent.config import load_config


def _write_config(tmp_path: Path, content: str) -> Path:
    config_path = tmp_path / "kairos.yaml"
    config_path.write_text(content)
    return config_path


def test_load_valid_config(tmp_path):
    path = _write_config(
        tmp_path,
        """
slack:
  webhook_url: "https://hooks.slack.com/test"
pagerduty:
  webhook_secret: "secret123"
log_sources:
  - type: file
    path: "/var/log/app/*.log"
llm:
  provider: anthropic
  model: claude-sonnet-4-20250514
context:
  time_window_minutes: 10
  max_log_lines: 200
""",
    )
    config = load_config(path)
    assert config.slack.webhook_url == "https://hooks.slack.com/test"
    assert config.pagerduty.webhook_secret == "secret123"
    assert len(config.log_sources) == 1
    assert config.log_sources[0].type == "file"
    assert config.context.time_window_minutes == 10
    assert config.context.max_log_lines == 200


def test_load_config_defaults(tmp_path):
    path = _write_config(
        tmp_path,
        """
slack:
  webhook_url: "https://hooks.slack.com/test"
pagerduty:
  webhook_secret: "secret123"
log_sources:
  - path: "/var/log/*.log"
""",
    )
    config = load_config(path)
    assert config.llm.model == "claude-sonnet-4-20250514"
    assert config.context.time_window_minutes == 15
    assert config.context.max_log_lines == 500
    assert config.log_sources[0].type == "file"


def test_load_config_missing_file():
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/kairos.yaml")


def test_load_config_missing_slack(tmp_path):
    path = _write_config(
        tmp_path,
        """
pagerduty:
  webhook_secret: "secret123"
log_sources:
  - path: "/var/log/*.log"
""",
    )
    with pytest.raises(ValueError, match="slack.webhook_url"):
        load_config(path)


def test_load_config_missing_log_sources(tmp_path):
    path = _write_config(
        tmp_path,
        """
slack:
  webhook_url: "https://hooks.slack.com/test"
pagerduty:
  webhook_secret: "secret123"
""",
    )
    with pytest.raises(ValueError, match="log_source"):
        load_config(path)


def test_env_var_interpolation(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_SLACK_URL", "https://hooks.slack.com/from-env")
    path = _write_config(
        tmp_path,
        """
slack:
  webhook_url: "${TEST_SLACK_URL}"
pagerduty:
  webhook_secret: "secret123"
log_sources:
  - path: "/var/log/*.log"
""",
    )
    config = load_config(path)
    assert config.slack.webhook_url == "https://hooks.slack.com/from-env"
