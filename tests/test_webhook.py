"""Tests for webhook receiver."""

import hashlib
import hmac
import json

import pytest

from kairos_agent.webhook_receiver import (
    extract_alert_info,
    verify_pagerduty_signature,
)


def test_verify_valid_signature():
    secret = "test-secret"
    body = b'{"event": "test"}'
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    signature = f"v1={digest}"

    assert verify_pagerduty_signature(body, signature, secret) is True


def test_verify_invalid_signature():
    secret = "test-secret"
    body = b'{"event": "test"}'
    signature = "v1=0000000000000000000000000000000000000000000000000000000000000000"

    assert verify_pagerduty_signature(body, signature, secret) is False


def test_verify_multiple_signatures():
    secret = "test-secret"
    body = b'{"event": "test"}'
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    # PagerDuty may send multiple versioned signatures
    signature = f"v0=fakedigest, v1={digest}"

    assert verify_pagerduty_signature(body, signature, secret) is True


def test_extract_triggered_incident():
    payload = {
        "event": {
            "event_type": "incident.triggered",
            "data": {
                "id": "P123ABC",
                "title": "High error rate on payment-service",
                "service": {"name": "payment-service"},
                "urgency": "high",
                "created_at": "2026-03-26T14:03:00Z",
                "html_url": "https://app.pagerduty.com/incidents/P123ABC",
            },
        }
    }

    result = extract_alert_info(payload)
    assert result is not None
    assert result["incident_id"] == "P123ABC"
    assert result["title"] == "High error rate on payment-service"
    assert result["service_name"] == "payment-service"
    assert result["urgency"] == "high"


def test_extract_non_triggered_event():
    payload = {
        "event": {
            "event_type": "incident.resolved",
            "data": {"id": "P123ABC"},
        }
    }

    result = extract_alert_info(payload)
    assert result is None


def test_extract_empty_payload():
    result = extract_alert_info({})
    assert result is None
