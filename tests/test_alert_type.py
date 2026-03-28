"""Tests for alert type inference and alert-type-aware scoring."""

from kairos_agent.context_assembler import AlertType, _score_line, infer_alert_type


def test_infer_error_rate() -> None:
    alert = {"title": "High error rate on payment-service"}
    assert infer_alert_type(alert) == AlertType.ERROR_RATE


def test_infer_latency() -> None:
    alert = {"title": "p99 latency spike on api-gateway"}
    assert infer_alert_type(alert) == AlertType.LATENCY


def test_infer_availability() -> None:
    alert = {"title": "Health check failing on postgres"}
    assert infer_alert_type(alert) == AlertType.AVAILABILITY


def test_infer_unknown() -> None:
    alert = {"title": "Something weird happened"}
    assert infer_alert_type(alert) == AlertType.UNKNOWN


def test_infer_explicit_override() -> None:
    alert = {"title": "Some alert", "alert_type": "latency"}
    assert infer_alert_type(alert) == AlertType.LATENCY


def test_infer_explicit_override_invalid_falls_back() -> None:
    alert = {"title": "High error rate", "alert_type": "bogus"}
    assert infer_alert_type(alert) == AlertType.ERROR_RATE


def test_score_line_error_rate_boost() -> None:
    line = "2026-03-26T14:01:00Z Traceback (most recent call last):"
    score_unknown = _score_line(line, "svc", AlertType.UNKNOWN)
    score_error = _score_line(line, "svc", AlertType.ERROR_RATE)
    assert score_error > score_unknown


def test_score_line_latency_boost() -> None:
    line = "2026-03-26T14:01:00Z [WARN] request timeout after 30s"
    score_unknown = _score_line(line, "svc", AlertType.UNKNOWN)
    score_latency = _score_line(line, "svc", AlertType.LATENCY)
    assert score_latency > score_unknown


def test_score_line_availability_boost() -> None:
    line = "2026-03-26T14:01:00Z connection refused to postgres:5432"
    score_unknown = _score_line(line, "svc", AlertType.UNKNOWN)
    score_avail = _score_line(line, "svc", AlertType.AVAILABILITY)
    assert score_avail > score_unknown


def test_score_line_unknown_unchanged() -> None:
    """With UNKNOWN alert type, scoring is identical to v0.2 base scoring."""
    line = "2026-03-26T14:01:00Z [ERROR] payment-service: failed"
    score = _score_line(line, "payment-service", AlertType.UNKNOWN)
    # Base: ERROR +10, service name +5 = 15
    assert score == 15
