"""Tests for Grafana Loki log source connector."""

from datetime import datetime, timezone

import httpx

from kairos_agent.sources.loki_source import LokiSource


def _make_response(status_code: int, json_data: dict) -> httpx.Response:
    return httpx.Response(
        status_code,
        json=json_data,
        request=httpx.Request("GET", "https://test"),
    )


def test_loki_source_success(monkeypatch) -> None:
    canned = {
        "data": {
            "result": [
                {
                    "stream": {"app": "payment-service", "env": "prod"},
                    "values": [
                        ["1711457460000000000", "ERROR: Stripe timeout after 30s"],
                        ["1711457520000000000", "WARN: Circuit breaker opened"],
                    ],
                }
            ]
        }
    }
    monkeypatch.setattr(
        httpx.Client, "get",
        lambda self, url, **kw: _make_response(200, canned),
    )

    source = LokiSource(url="http://loki.internal:3100")
    result = source.fetch(
        "payment-service",
        datetime(2026, 3, 26, 13, 50, tzinfo=timezone.utc),
        datetime(2026, 3, 26, 14, 5, tzinfo=timezone.utc),
    )
    assert result.error is None
    assert result.line_count == 2
    assert "[loki:" in result.lines[0]
    assert "Stripe timeout" in result.lines[0]


def test_loki_source_auth_failure(monkeypatch) -> None:
    def raise_401(self, url, **kw):
        resp = httpx.Response(401, json={"message": "Unauthorized"})
        resp.request = httpx.Request("GET", url)
        raise httpx.HTTPStatusError("Unauthorized", request=resp.request, response=resp)

    monkeypatch.setattr(httpx.Client, "get", raise_401)

    source = LokiSource(url="http://loki:3100", auth_header="Bearer bad-token")
    result = source.fetch(
        "svc",
        datetime(2026, 3, 26, 13, 50, tzinfo=timezone.utc),
        datetime(2026, 3, 26, 14, 5, tzinfo=timezone.utc),
    )
    assert result.error is not None
    assert "401" in result.error


def test_loki_source_empty_response(monkeypatch) -> None:
    canned = {"data": {"result": []}}
    monkeypatch.setattr(
        httpx.Client, "get",
        lambda self, url, **kw: _make_response(200, canned),
    )

    source = LokiSource(url="http://loki:3100")
    result = source.fetch(
        "svc",
        datetime(2026, 3, 26, 13, 50, tzinfo=timezone.utc),
        datetime(2026, 3, 26, 14, 5, tzinfo=timezone.utc),
    )
    assert result.error is None
    assert result.line_count == 0


def test_loki_source_custom_query(monkeypatch) -> None:
    captured_params = {}

    def capture_get(self, url, **kw):
        captured_params.update(kw.get("params", {}))
        return _make_response(200, {"data": {"result": []}})

    monkeypatch.setattr(httpx.Client, "get", capture_get)

    source = LokiSource(
        url="http://loki:3100",
        query_template='{app="{service_name}"} |= "error"',
    )
    source.fetch(
        "payment-service",
        datetime(2026, 3, 26, 13, 50, tzinfo=timezone.utc),
        datetime(2026, 3, 26, 14, 5, tzinfo=timezone.utc),
    )
    assert captured_params["query"] == '{app="payment-service"} |= "error"'


def test_loki_source_auth_header(monkeypatch) -> None:
    captured_headers = {}

    def capture_get(self, url, **kw):
        captured_headers.update(kw.get("headers", {}))
        return _make_response(200, {"data": {"result": []}})

    monkeypatch.setattr(httpx.Client, "get", capture_get)

    source = LokiSource(
        url="http://loki:3100",
        auth_header="Bearer my-token",
    )
    source.fetch(
        "svc",
        datetime(2026, 3, 26, 13, 50, tzinfo=timezone.utc),
        datetime(2026, 3, 26, 14, 5, tzinfo=timezone.utc),
    )
    assert captured_headers.get("Authorization") == "Bearer my-token"


def test_loki_source_name() -> None:
    source = LokiSource(url="http://loki.internal:3100")
    assert source.name == "loki:http://loki.internal:3100"


def test_loki_source_multiple_streams(monkeypatch) -> None:
    canned = {
        "data": {
            "result": [
                {
                    "stream": {"app": "svc-a"},
                    "values": [["1711457460000000000", "line from a"]],
                },
                {
                    "stream": {"app": "svc-b"},
                    "values": [["1711457520000000000", "line from b"]],
                },
            ]
        }
    }
    monkeypatch.setattr(
        httpx.Client, "get",
        lambda self, url, **kw: _make_response(200, canned),
    )

    source = LokiSource(url="http://loki:3100")
    result = source.fetch(
        "svc",
        datetime(2026, 3, 26, 13, 50, tzinfo=timezone.utc),
        datetime(2026, 3, 26, 14, 5, tzinfo=timezone.utc),
    )
    assert result.line_count == 2
    assert "line from a" in result.lines[0]
    assert "line from b" in result.lines[1]
