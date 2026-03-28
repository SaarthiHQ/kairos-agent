"""Tests for service catalog and source resolution."""

from kairos_agent.config import (
    ContextConfig,
    KairosConfig,
    LLMConfig,
    LogSource,
    PagerDutyConfig,
    ServiceConfig,
    SlackConfig,
)
from kairos_agent.service_catalog import (
    ResolvedSource,
    _resolve_source_ref,
    resolve_sources_for_alert,
)


def _make_config(
    log_sources: list[LogSource],
    services: dict[str, ServiceConfig] | None = None,
) -> KairosConfig:
    return KairosConfig(
        slack=SlackConfig(webhook_url="https://test"),
        pagerduty=PagerDutyConfig(webhook_secret="secret"),
        log_sources=log_sources,
        services=services or {},
    )


def test_resolve_source_ref_by_name() -> None:
    sources = [
        LogSource(type="newrelic", name="nr-prod"),
        LogSource(type="file", name="app-logs", path="/var/log/app.log"),
    ]
    result = _resolve_source_ref("nr-prod", sources)
    assert result is not None
    assert result.type == "newrelic"


def test_resolve_source_ref_inline_file() -> None:
    result = _resolve_source_ref("file:/var/log/payment/*.log", [])
    assert result is not None
    assert result.type == "file"
    assert result.path == "/var/log/payment/*.log"


def test_resolve_source_ref_by_type() -> None:
    sources = [LogSource(type="datadog", credentials={"api_key": "k"})]
    result = _resolve_source_ref("datadog", sources)
    assert result is not None
    assert result.type == "datadog"


def test_resolve_source_ref_unresolved() -> None:
    result = _resolve_source_ref("nonexistent", [])
    assert result is None


def test_resolve_known_service() -> None:
    log_sources = [
        LogSource(type="newrelic", name="nr-prod"),
        LogSource(type="file", name="payment-logs", path="/var/log/pay.log"),
    ]
    services = {
        "payment-service": ServiceConfig(
            name="payment-service",
            sources=["nr-prod", "payment-logs"],
            tier="critical",
        ),
    }
    config = _make_config(log_sources, services)
    resolved = resolve_sources_for_alert("payment-service", config)
    assert len(resolved) == 2
    assert all(r.relationship == "direct" for r in resolved)
    assert all(r.origin_service == "payment-service" for r in resolved)


def test_resolve_with_dependencies() -> None:
    log_sources = [
        LogSource(type="newrelic", name="nr-prod"),
        LogSource(type="datadog", name="dd-prod"),
    ]
    services = {
        "payment-service": ServiceConfig(
            name="payment-service",
            depends_on=["stripe-gateway"],
            sources=["nr-prod"],
        ),
        "stripe-gateway": ServiceConfig(
            name="stripe-gateway",
            sources=["dd-prod"],
        ),
    }
    config = _make_config(log_sources, services)
    resolved = resolve_sources_for_alert("payment-service", config)

    direct = [r for r in resolved if r.relationship == "direct"]
    deps = [r for r in resolved if r.relationship == "dependency"]
    assert len(direct) == 1
    assert direct[0].origin_service == "payment-service"
    assert len(deps) == 1
    assert deps[0].origin_service == "stripe-gateway"


def test_resolve_unknown_service_fallback() -> None:
    log_sources = [
        LogSource(type="file", path="/var/log/app.log"),
        LogSource(type="newrelic", name="nr"),
    ]
    services = {
        "other-service": ServiceConfig(name="other-service", sources=["nr"]),
    }
    config = _make_config(log_sources, services)
    resolved = resolve_sources_for_alert("unknown-service", config)
    # Falls back to all log_sources
    assert len(resolved) == 2
    assert all(r.relationship == "direct" for r in resolved)


def test_circular_dependency_guard() -> None:
    log_sources = [LogSource(type="file", name="logs", path="/var/log/a.log")]
    services = {
        "svc-a": ServiceConfig(
            name="svc-a",
            depends_on=["svc-b"],
            sources=["logs"],
        ),
        "svc-b": ServiceConfig(
            name="svc-b",
            depends_on=["svc-a"],
            sources=["logs"],
        ),
    }
    config = _make_config(log_sources, services)
    resolved = resolve_sources_for_alert("svc-a", config)
    # Should not infinite loop, svc-b's dep on svc-a is skipped
    service_names = {r.origin_service for r in resolved}
    assert "svc-a" in service_names
    assert "svc-b" in service_names


def test_dependency_depth_one_only() -> None:
    """Only direct dependencies are resolved, not transitive."""
    log_sources = [
        LogSource(type="file", name="a-logs", path="/a.log"),
        LogSource(type="file", name="b-logs", path="/b.log"),
        LogSource(type="file", name="c-logs", path="/c.log"),
    ]
    services = {
        "svc-a": ServiceConfig(name="svc-a", depends_on=["svc-b"], sources=["a-logs"]),
        "svc-b": ServiceConfig(name="svc-b", depends_on=["svc-c"], sources=["b-logs"]),
        "svc-c": ServiceConfig(name="svc-c", sources=["c-logs"]),
    }
    config = _make_config(log_sources, services)
    resolved = resolve_sources_for_alert("svc-a", config)
    origins = {r.origin_service for r in resolved}
    assert "svc-a" in origins
    assert "svc-b" in origins
    assert "svc-c" not in origins  # transitive, not included


def test_missing_dependency_skipped() -> None:
    log_sources = [LogSource(type="file", name="logs", path="/a.log")]
    services = {
        "svc-a": ServiceConfig(
            name="svc-a",
            depends_on=["nonexistent-service"],
            sources=["logs"],
        ),
    }
    config = _make_config(log_sources, services)
    resolved = resolve_sources_for_alert("svc-a", config)
    assert len(resolved) == 1  # only direct, dep skipped
    assert resolved[0].origin_service == "svc-a"


def test_no_catalog_uses_all_sources() -> None:
    log_sources = [
        LogSource(type="file", path="/a.log"),
        LogSource(type="newrelic"),
    ]
    config = _make_config(log_sources, services={})
    resolved = resolve_sources_for_alert("any-service", config)
    assert len(resolved) == 2
