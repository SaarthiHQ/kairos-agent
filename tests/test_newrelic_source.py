"""Tests for New Relic log source connector."""

from datetime import datetime, timezone

import httpx

from kairos_agent.sources.newrelic_source import NewRelicSource


def _make_response(status_code: int, json_data: dict) -> httpx.Response:
    return httpx.Response(
        status_code,
        json=json_data,
        request=httpx.Request("POST", "https://api.newrelic.com/graphql"),
    )


def test_newrelic_source_success(monkeypatch) -> None:
    canned = {
        "data": {
            "actor": {
                "account": {
                    "nrql": {
                        "results": [
                            {
                                "timestamp": 1711457460000,
                                "message": "Stripe API timeout after 30s",
                                "level": "error",
                                "service": "payment-service",
                            },
                            {
                                "timestamp": 1711457520000,
                                "message": "Circuit breaker opened",
                                "level": "warn",
                                "service": "payment-service",
                            },
                        ]
                    }
                }
            }
        }
    }
    monkeypatch.setattr(
        httpx.Client, "post",
        lambda self, url, **kw: _make_response(200, canned),
    )

    source = NewRelicSource(api_key="NRAK-test", account_id="1234567")
    result = source.fetch(
        "payment-service",
        datetime(2026, 3, 26, 13, 50, tzinfo=timezone.utc),
        datetime(2026, 3, 26, 14, 5, tzinfo=timezone.utc),
    )
    assert result.error is None
    assert result.line_count == 2
    assert "[newrelic]" in result.lines[0]
    assert "[ERROR]" in result.lines[0]
    assert "Stripe API timeout" in result.lines[0]
    assert "Circuit breaker" in result.lines[1]


def test_newrelic_source_graphql_error(monkeypatch) -> None:
    canned = {
        "errors": [{"message": "Invalid NRQL query syntax"}],
        "data": None,
    }
    monkeypatch.setattr(
        httpx.Client, "post",
        lambda self, url, **kw: _make_response(200, canned),
    )

    source = NewRelicSource(api_key="NRAK-test", account_id="1234567")
    result = source.fetch(
        "svc",
        datetime(2026, 3, 26, 13, 50, tzinfo=timezone.utc),
        datetime(2026, 3, 26, 14, 5, tzinfo=timezone.utc),
    )
    assert result.error is not None
    assert "Invalid NRQL" in result.error


def test_newrelic_source_http_error(monkeypatch) -> None:
    def raise_403(self, url, **kw):
        resp = httpx.Response(403, request=httpx.Request("POST", url))
        raise httpx.HTTPStatusError("Forbidden", request=resp.request, response=resp)

    monkeypatch.setattr(httpx.Client, "post", raise_403)

    source = NewRelicSource(api_key="bad-key", account_id="1234567")
    result = source.fetch(
        "svc",
        datetime(2026, 3, 26, 13, 50, tzinfo=timezone.utc),
        datetime(2026, 3, 26, 14, 5, tzinfo=timezone.utc),
    )
    assert result.error is not None
    assert "403" in result.error


def test_newrelic_source_empty_results(monkeypatch) -> None:
    canned = {
        "data": {
            "actor": {"account": {"nrql": {"results": []}}}
        }
    }
    monkeypatch.setattr(
        httpx.Client, "post",
        lambda self, url, **kw: _make_response(200, canned),
    )

    source = NewRelicSource(api_key="key", account_id="123")
    result = source.fetch(
        "svc",
        datetime(2026, 3, 26, 13, 50, tzinfo=timezone.utc),
        datetime(2026, 3, 26, 14, 5, tzinfo=timezone.utc),
    )
    assert result.error is None
    assert result.line_count == 0


def test_newrelic_source_custom_query(monkeypatch) -> None:
    captured_body = {}

    def capture_post(self, url, **kw):
        captured_body.update(kw.get("json", {}))
        return _make_response(200, {
            "data": {"actor": {"account": {"nrql": {"results": []}}}}
        })

    monkeypatch.setattr(httpx.Client, "post", capture_post)

    source = NewRelicSource(
        api_key="key",
        account_id="999",
        query_template="SELECT * FROM Log WHERE service = '{service_name}' AND level = 'ERROR'",
    )
    source.fetch(
        "payment-service",
        datetime(2026, 3, 26, 13, 50, tzinfo=timezone.utc),
        datetime(2026, 3, 26, 14, 5, tzinfo=timezone.utc),
    )
    query_str = captured_body.get("query", "")
    assert "payment-service" in query_str
    assert "ERROR" in query_str
    assert "SINCE" in query_str
    assert "UNTIL" in query_str
    assert "LIMIT MAX" in query_str


def test_newrelic_source_eu_region() -> None:
    source = NewRelicSource(api_key="k", account_id="123", region="eu")
    assert source._endpoint == "https://api.eu.newrelic.com/graphql"


def test_newrelic_source_us_region() -> None:
    source = NewRelicSource(api_key="k", account_id="123", region="us")
    assert source._endpoint == "https://api.newrelic.com/graphql"


def test_newrelic_source_name() -> None:
    source = NewRelicSource(api_key="k", account_id="1234567")
    assert source.name == "newrelic:1234567"


def test_newrelic_source_api_key_header(monkeypatch) -> None:
    captured_headers = {}

    def capture_post(self, url, **kw):
        captured_headers.update(kw.get("headers", {}))
        return _make_response(200, {
            "data": {"actor": {"account": {"nrql": {"results": []}}}}
        })

    monkeypatch.setattr(httpx.Client, "post", capture_post)

    source = NewRelicSource(api_key="NRAK-my-secret-key", account_id="123")
    source.fetch(
        "svc",
        datetime(2026, 3, 26, 13, 50, tzinfo=timezone.utc),
        datetime(2026, 3, 26, 14, 5, tzinfo=timezone.utc),
    )
    assert captured_headers.get("API-Key") == "NRAK-my-secret-key"
