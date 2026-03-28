"""Tests for Generic HTTP log source connector."""

from datetime import datetime, timezone

import httpx

from kairos_agent.sources.http_source import GenericHTTPSource


def _make_response(status_code: int, json_data: dict) -> httpx.Response:
    return httpx.Response(
        status_code,
        json=json_data,
        request=httpx.Request("GET", "https://test"),
    )


def test_http_source_get_success(monkeypatch) -> None:
    canned = {"lines": ["error: timeout on payment", "warn: retry attempt 3"]}
    monkeypatch.setattr(
        httpx.Client, "get",
        lambda self, url, **kw: _make_response(200, canned),
    )

    source = GenericHTTPSource(url="https://logs.internal/api/search")
    result = source.fetch(
        "payment-service",
        datetime(2026, 3, 26, 13, 50, tzinfo=timezone.utc),
        datetime(2026, 3, 26, 14, 5, tzinfo=timezone.utc),
    )
    assert result.error is None
    assert result.line_count == 2
    assert "timeout on payment" in result.lines[0]


def test_http_source_post_success(monkeypatch) -> None:
    canned = {"data": {"hits": {"lines": ["log line 1", "log line 2"]}}}
    monkeypatch.setattr(
        httpx.Client, "post",
        lambda self, url, **kw: _make_response(200, canned),
    )

    source = GenericHTTPSource(
        url="https://logs.internal/search",
        method="POST",
        body_template='{"query": "{service_name}", "from": "{start_epoch}"}',
        response_lines_path="data.hits.lines",
    )
    result = source.fetch(
        "svc",
        datetime(2026, 3, 26, 13, 50, tzinfo=timezone.utc),
        datetime(2026, 3, 26, 14, 5, tzinfo=timezone.utc),
    )
    assert result.error is None
    assert result.line_count == 2


def test_http_source_template_substitution(monkeypatch) -> None:
    captured_url = {}

    def capture_get(self, url, **kw):
        captured_url["url"] = url
        return _make_response(200, {"lines": []})

    monkeypatch.setattr(httpx.Client, "get", capture_get)

    source = GenericHTTPSource(
        url="https://logs.internal/search?service={service_name}&from={start_epoch}&to={end_epoch}",
    )
    source.fetch(
        "payment-service",
        datetime(2026, 3, 26, 13, 50, tzinfo=timezone.utc),
        datetime(2026, 3, 26, 14, 5, tzinfo=timezone.utc),
    )
    assert "payment-service" in captured_url["url"]
    assert "start_epoch" not in captured_url["url"]  # should be replaced


def test_http_source_nested_response_path(monkeypatch) -> None:
    canned = {"data": {"results": ["line a", "line b", "line c"]}}
    monkeypatch.setattr(
        httpx.Client, "get",
        lambda self, url, **kw: _make_response(200, canned),
    )

    source = GenericHTTPSource(
        url="https://logs.internal/api",
        response_lines_path="data.results",
    )
    result = source.fetch(
        "svc",
        datetime(2026, 3, 26, 13, 50, tzinfo=timezone.utc),
        datetime(2026, 3, 26, 14, 5, tzinfo=timezone.utc),
    )
    assert result.line_count == 3


def test_http_source_bad_response_path(monkeypatch) -> None:
    canned = {"something": "else"}
    monkeypatch.setattr(
        httpx.Client, "get",
        lambda self, url, **kw: _make_response(200, canned),
    )

    source = GenericHTTPSource(
        url="https://logs.internal/api",
        response_lines_path="nonexistent.path",
    )
    result = source.fetch(
        "svc",
        datetime(2026, 3, 26, 13, 50, tzinfo=timezone.utc),
        datetime(2026, 3, 26, 14, 5, tzinfo=timezone.utc),
    )
    assert result.line_count == 0
    assert result.error is None  # not an error, just no data at that path


def test_http_source_server_error(monkeypatch) -> None:
    def raise_500(self, url, **kw):
        resp = httpx.Response(500, request=httpx.Request("GET", url))
        raise httpx.HTTPStatusError("Server Error", request=resp.request, response=resp)

    monkeypatch.setattr(httpx.Client, "get", raise_500)

    source = GenericHTTPSource(url="https://logs.internal/api")
    result = source.fetch(
        "svc",
        datetime(2026, 3, 26, 13, 50, tzinfo=timezone.utc),
        datetime(2026, 3, 26, 14, 5, tzinfo=timezone.utc),
    )
    assert result.error is not None
    assert "500" in result.error


def test_http_source_name() -> None:
    source = GenericHTTPSource(url="https://logs.internal/api/search")
    assert source.name == "http:https://logs.internal/api/search"
