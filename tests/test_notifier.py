"""Tests for Slack notifier."""

from kairos_agent.notifier import build_slack_blocks


def test_build_slack_blocks_structure():
    alert_info = {
        "title": "High error rate on payment-service",
        "service_name": "payment-service",
        "urgency": "high",
        "triggered_at": "2026-03-26T14:03:00Z",
        "html_url": "https://app.pagerduty.com/incidents/P123",
    }
    summary = "The payment service is experiencing Stripe API timeouts."

    blocks = build_slack_blocks(alert_info, summary)

    assert len(blocks) == 6
    assert blocks[0]["type"] == "header"
    assert "payment-service" in blocks[0]["text"]["text"]
    assert blocks[1]["type"] == "section"
    assert blocks[2]["type"] == "divider"
    assert blocks[3]["type"] == "section"
    assert summary in blocks[3]["text"]["text"]
    assert blocks[5]["type"] == "context"


def test_build_slack_blocks_low_urgency():
    alert_info = {
        "title": "Minor issue",
        "service_name": "frontend",
        "urgency": "low",
        "triggered_at": "2026-03-26T14:03:00Z",
        "html_url": "",
    }
    summary = "Low severity issue detected."

    blocks = build_slack_blocks(alert_info, summary)
    # Check urgency field uses yellow circle for low
    fields = blocks[1]["fields"]
    urgency_field = [f for f in fields if "Urgency" in f["text"]][0]
    assert "large_yellow_circle" in urgency_field["text"]
