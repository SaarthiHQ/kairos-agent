"""Tests for Datadog log source connector."""

from datetime import datetime, timezone

import httpx

from kairos_agent.sources.datadog_source import DatadogSource


def _make_response(status_code: int, json_data: dict) -> httpx.Response:
    return httpx.Response(
        status_code,
        json=json_data,
        request=httpx.Request("POST", "https://test"),
    )


def test_datadog_source_success(monkeypatch) -> None:
    canned = {
        "data": [
            {
                "attributes": {
                    "timestamp": "2026-03-26T14:01:00Z",
                    "message": "Stripe API timeout after 30s",
                    "service": "payment-service",
                    "status": "error",
                }
            },
            {
                "attributes": {
                    "timestamp": "2026-03-26T14:02:00Z",
                    "message": "Circuit breaker opened",
                    "service": "payment-service",
                    "status": "warn",
                }
            },
        ],
        "meta": {"page": {}},
    }
    monkeypatch.setattr(
        httpx.Client, "post",
        lambda self, url, **kw: _make_response(200, canned),
    )

    source = DatadogSource(api_key="test-key", app_key="test-app")
    result = source.fetch(
        "payment-service",
        datetime(2026, 3, 26, 13, 50, tzinfo=timezone.utc),
        datetime(2026, 3, 26, 14, 5, tzinfo=timezone.utc),
    )
    assert result.error is None
    assert result.line_count == 2
    assert "[datadog]" in result.lines[0]
    assert "Stripe API timeout" in result.lines[0]
    assert "[ERROR]" in result.lines[0]
    assert "Circuit breaker" in result.lines[1]


def test_datadog_source_auth_failure(monkeypatch) -> None:
    def raise_403(self, url, **kw):
        resp = httpx.Response(403, json={"errors": ["Forbidden"]})
        resp.request = httpx.Request("POST", url)
        raise httpx.HTTPStatusError("Forbidden", request=resp.request, response=resp)

    monkeypatch.setattr(httpx.Client, "post", raise_403)

    source = DatadogSource(api_key="bad-key", app_key="bad-app")
    result = source.fetch(
        "svc",
        datetime(2026, 3, 26, 13, 50, tzinfo=timezone.utc),
        datetime(2026, 3, 26, 14, 5, tzinfo=timezone.utc),
    )
    assert result.error is not None
    assert "403" in result.error


def test_datadog_source_empty_response(monkeypatch) -> None:
    canned = {"data": [], "meta": {"page": {}}}
    monkeypatch.setattr(
        httpx.Client, "post",
        lambda self, url, **kw: _make_response(200, canned),
    )

    source = DatadogSource(api_key="key", app_key="app")
    result = source.fetch(
        "svc",
        datetime(2026, 3, 26, 13, 50, tzinfo=timezone.utc),
        datetime(2026, 3, 26, 14, 5, tzinfo=timezone.utc),
    )
    assert result.error is None
    assert result.line_count == 0


def test_datadog_source_custom_query(monkeypatch) -> None:
    """Verify the query template substitution works."""
    captured_body = {}

    def capture_post(self, url, **kw):
        captured_body.update(kw.get("json", {}))
        return _make_response(200, {"data": [], "meta": {"page": {}}})

    monkeypatch.setattr(httpx.Client, "post", capture_post)

    source = DatadogSource(
        api_key="key",
        app_key="app",
        query_template="service:{service_name} status:error",
    )
    source.fetch(
        "payment-service",
        datetime(2026, 3, 26, 13, 50, tzinfo=timezone.utc),
        datetime(2026, 3, 26, 14, 5, tzinfo=timezone.utc),
    )
    assert captured_body["filter"]["query"] == "service:payment-service status:error"


def test_datadog_source_name() -> None:
    source = DatadogSource(api_key="k", app_key="a", site="us5.datadoghq.com")
    assert source.name == "datadog:us5.datadoghq.com"
