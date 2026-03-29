#!/bin/bash
# Simulate a New Relic alert webhook against a running kairos-agent.
#
# Usage:
#   ./scripts/simulate_newrelic_alert.sh [host:port]

set -e

HOST="${1:-localhost:8000}"

PAYLOAD='{
  "issueId": "NR-SIM-001",
  "issueTitle": "High error rate on saarthi-clinical — document processing failures",
  "state": "open",
  "severity": "CRITICAL",
  "priority": "CRITICAL",
  "targetName": "saarthi-clinical",
  "targets": [{"name": "saarthi-clinical", "type": "APPLICATION"}],
  "timestamp": 1743235320000,
  "issueUrl": "https://one.eu.newrelic.com/alerts-ai/accounts/7688224/issues/NR-SIM-001",
  "condition_name": "5xx Server Errors",
  "policy_name": "Saarthi Production Alerts"
}'

echo "============================================"
echo "  Simulating New Relic alert to kairos-agent"
echo "============================================"
echo ""
echo "Target:    http://${HOST}/webhook/newrelic"
echo "Service:   saarthi-clinical"
echo "Severity:  CRITICAL"
echo "Condition: 5xx Server Errors"
echo ""

RESPONSE=$(curl -s -w "\n%{http_code}" \
  -X POST "http://${HOST}/webhook/newrelic" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -1)

echo "Response: HTTP ${HTTP_CODE}"
echo "Body:     ${BODY}"
echo ""

if [ "$HTTP_CODE" = "200" ]; then
    echo "✓ Alert accepted! Check kairos-agent logs."
else
    echo "✗ Alert rejected."
fi
