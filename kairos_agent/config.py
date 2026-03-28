"""Load and validate kairos.yaml configuration."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger("kairos_agent")


@dataclass
class SlackConfig:
    webhook_url: str


@dataclass
class PagerDutyConfig:
    webhook_secret: str


@dataclass
class LogSource:
    type: str  # "file", "datadog", "loki", "newrelic", "http"
    name: str = ""  # Optional name for service catalog references
    path: str = ""
    credentials: dict[str, str] = field(default_factory=dict)
    options: dict[str, str] = field(default_factory=dict)


@dataclass
class ServiceConfig:
    """Declaration of a service in the catalog."""

    name: str
    depends_on: list[str] = field(default_factory=list)
    owners: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)  # Source references
    tier: str = "standard"  # "critical", "standard", "best-effort"


@dataclass
class LLMConfig:
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-20250514"


@dataclass
class ContextConfig:
    time_window_minutes: int = 15
    max_log_lines: int = 500
    max_context_tokens: int = 10000  # Token budget for log lines in the prompt


@dataclass
class KairosConfig:
    slack: SlackConfig
    pagerduty: PagerDutyConfig
    log_sources: list[LogSource]
    llm: LLMConfig = field(default_factory=LLMConfig)
    context: ContextConfig = field(default_factory=ContextConfig)
    services: dict[str, ServiceConfig] = field(default_factory=dict)


def _resolve_env_vars(value: str) -> str:
    """Replace ${ENV_VAR} references in string values."""
    if not isinstance(value, str):
        return value
    import re
    def replacer(match: re.Match) -> str:
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))
    return re.sub(r"\$\{(\w+)}", replacer, value)


def _walk_and_resolve(data: Any) -> Any:
    """Recursively resolve environment variables in config values."""
    if isinstance(data, str):
        return _resolve_env_vars(data)
    if isinstance(data, dict):
        return {k: _walk_and_resolve(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_walk_and_resolve(item) for item in data]
    return data


def load_config(path: str | Path = "kairos.yaml") -> KairosConfig:
    """Load configuration from a YAML file.

    Supports ${ENV_VAR} interpolation in string values.
    """
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_path}. "
            "Copy kairos.yaml.example to kairos.yaml and fill in your values."
        )

    raw = yaml.safe_load(config_path.read_text())
    raw = _walk_and_resolve(raw)

    slack_raw = raw.get("slack", {})
    if not slack_raw.get("webhook_url"):
        raise ValueError("slack.webhook_url is required in kairos.yaml")

    pd_raw = raw.get("pagerduty", {})
    if not pd_raw.get("webhook_secret"):
        raise ValueError("pagerduty.webhook_secret is required in kairos.yaml")

    log_sources_raw = raw.get("log_sources", [])
    if not log_sources_raw:
        raise ValueError("At least one log_source is required in kairos.yaml")

    log_sources = [
        LogSource(
            type=ls.get("type", "file"),
            name=ls.get("name", ""),
            path=ls.get("path", ""),
            credentials=ls.get("credentials", {}),
            options=ls.get("options", {}),
        )
        for ls in log_sources_raw
    ]

    llm_raw = raw.get("llm", {})
    llm = LLMConfig(
        provider=llm_raw.get("provider", "anthropic"),
        model=llm_raw.get("model", "claude-sonnet-4-20250514"),
    )

    ctx_raw = raw.get("context", {})
    context = ContextConfig(
        time_window_minutes=ctx_raw.get("time_window_minutes", 15),
        max_log_lines=ctx_raw.get("max_log_lines", 500),
        max_context_tokens=ctx_raw.get("max_context_tokens", 3000),
    )

    # Parse optional service catalog
    services_raw = raw.get("services", {})
    services: dict[str, ServiceConfig] = {}
    for svc_name, svc_data in services_raw.items():
        services[svc_name] = ServiceConfig(
            name=svc_name,
            depends_on=svc_data.get("depends_on", []),
            owners=svc_data.get("owners", []),
            sources=svc_data.get("sources", []),
            tier=svc_data.get("tier", "standard"),
        )
        # Warn about unresolvable dependency references
        for dep in services[svc_name].depends_on:
            if dep not in services_raw:
                logger.warning(
                    "Service '%s' depends on '%s' which is not in the catalog",
                    svc_name, dep,
                )

    return KairosConfig(
        slack=SlackConfig(webhook_url=slack_raw["webhook_url"]),
        pagerduty=PagerDutyConfig(webhook_secret=pd_raw["webhook_secret"]),
        log_sources=log_sources,
        llm=llm,
        context=context,
        services=services,
    )
