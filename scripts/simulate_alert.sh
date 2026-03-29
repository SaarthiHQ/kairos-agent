#!/bin/bash
# Simulate a PagerDuty alert webhook against a running kairos-agent.
#
# Usage:
#   ./scripts/simulate_alert.sh [host:port] [webhook_secret]
#
# Defaults:
#   host:port = localhost:8000
#   webhook_secret = test-secret (matches kairos-test.yaml)

set -e

HOST="${1:-localhost:8000}"
SECRET="${2:-test-secret}"

# Simulated PagerDuty V3 webhook payload — Saarthi document processing incident
PAYLOAD='{
  "event": {
    "event_type": "incident.triggered",
    "data": {
      "id": "SIM-001",
      "title": "High error rate on saarthi-clinical — document processing pipeline stalled",
      "service": {
        "name": "saarthi-clinical"
      },
      "urgency": "high",
      "created_at": "2026-03-29T10:02:00Z",
      "html_url": "https://alerts.newrelic.com/accounts/7688224/incidents/SIM-001"
    }
  }
}'

# Compute HMAC-SHA256 signature (PagerDuty V3 format)
SIGNATURE="v1=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $2}')"

echo "============================================"
echo "  Simulating PagerDuty alert to kairos-agent"
echo "============================================"
echo ""
echo "Target:    http://${HOST}/webhook/pagerduty"
echo "Service:   saarthi-clinical"
echo "Alert:     High error rate — document processing pipeline stalled"
echo "Signature: ${SIGNATURE:0:20}..."
echo ""

# Send the webhook
RESPONSE=$(curl -s -w "\n%{http_code}" \
  -X POST "http://${HOST}/webhook/pagerduty" \
  -H "Content-Type: application/json" \
  -H "X-PagerDuty-Signature: ${SIGNATURE}" \
  -d "$PAYLOAD")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -1)

echo "Response: HTTP ${HTTP_CODE}"
echo "Body:     ${BODY}"
echo ""

if [ "$HTTP_CODE" = "200" ]; then
    echo "✓ Alert accepted! Check kairos-agent logs for triage pipeline output."
    echo "  (If ANTHROPIC_API_KEY is set, the summary will post to Slack)"
else
    echo "✗ Alert rejected. Check the server logs."
fi
