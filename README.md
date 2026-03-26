# kairos-agent

AI-powered incident context assembler for SRE teams.

When an alert fires, kairos-agent pulls relevant logs, assembles context, uses Claude to generate a triage summary, and posts it to Slack. The on-call engineer gets a 30-second read instead of 20 minutes of digging.

```
PagerDuty Alert → kairos-agent → Logs + Context → Claude Summary → Slack
```

## 5-Minute Quickstart

### Prerequisites

- Docker and Docker Compose
- An [Anthropic API key](https://console.anthropic.com/)
- A [Slack incoming webhook URL](https://api.slack.com/messaging/webhooks)
- A [PagerDuty webhook](https://support.pagerduty.com/docs/webhooks) pointed at your kairos-agent instance

### 1. Clone and configure

```bash
git clone https://github.com/yourorg/kairos-agent.git
cd kairos-agent
cp kairos.yaml.example kairos.yaml
```

Edit `kairos.yaml` with your values:

```yaml
slack:
  webhook_url: "${SLACK_WEBHOOK_URL}"

pagerduty:
  webhook_secret: "your-pagerduty-webhook-secret"

log_sources:
  - type: file
    path: "/var/log/app/*.log"

llm:
  provider: anthropic
  model: claude-sonnet-4-20250514

context:
  time_window_minutes: 15
  max_log_lines: 500
```

### 2. Set your API key

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### 3. Start the agent

```bash
docker compose up --build
```

The webhook receiver starts on `http://localhost:8000`.

### 4. Point PagerDuty at it

In PagerDuty, add a Generic V3 Webhook pointing to:

```
https://your-host:8000/webhook/pagerduty
```

Set the webhook secret in `kairos.yaml` to match.

### 5. Test it

```bash
curl -X POST http://localhost:8000/webhook/pagerduty \
  -H "Content-Type: application/json" \
  -H "X-PagerDuty-Signature: v1=$(echo -n '{"event":{"event_type":"incident.triggered","data":{"id":"P123","title":"High error rate on payment-service","service":{"name":"payment-service"},"urgency":"high","created_at":"2026-03-26T14:03:00Z","html_url":"https://app.pagerduty.com/incidents/P123"}}}' | openssl dgst -sha256 -hmac 'your-pagerduty-webhook-secret' | awk '{print $2}')" \
  -d '{"event":{"event_type":"incident.triggered","data":{"id":"P123","title":"High error rate on payment-service","service":{"name":"payment-service"},"urgency":"high","created_at":"2026-03-26T14:03:00Z","html_url":"https://app.pagerduty.com/incidents/P123"}}}'
```

## Running without Docker

```bash
pip install .
kairos-agent --config kairos.yaml --port 8000
```

## Architecture

```
┌──────────────┐     ┌───────────────────┐     ┌─────────────────┐
│  PagerDuty   │────▶│  webhook_receiver  │────▶│ context_assembler│
│  Webhook     │     │  (FastAPI)         │     │ (log filtering)  │
└──────────────┘     └───────────────────┘     └────────┬────────┘
                                                        │
                                                        ▼
                     ┌───────────────────┐     ┌─────────────────┐
                     │     notifier      │◀────│   summarizer    │
                     │  (Slack Block Kit)│     │  (Claude API)   │
                     └───────────────────┘     └─────────────────┘
```

| Module                | Responsibility                                          |
|-----------------------|---------------------------------------------------------|
| `webhook_receiver.py` | FastAPI app, PagerDuty signature validation, routing    |
| `context_assembler.py`| Read logs, filter by time window + service, rank lines  |
| `summarizer.py`       | Build prompt, call Claude, return triage summary        |
| `notifier.py`         | Format Slack Block Kit message, post via webhook        |
| `pipeline.py`         | Orchestrate the full triage flow                        |
| `config.py`           | Load and validate `kairos.yaml`                         |
| `cli.py`              | CLI entry point with argument parsing                   |

## How Log Context Works

kairos reads log files matching your `log_sources[].path` glob patterns (e.g., `/var/log/app/*.log`). It recognizes these timestamp formats:

- **ISO 8601** — `2026-03-26T14:03:00Z`
- **Common log format** — `26/Mar/2026:14:03:00 +0000`
- **Syslog** — `Mar 26 14:03:00`
- **Simple datetime** — `2026-03-26 14:03:00`

Lines without a recognized timestamp are included but ranked lower.

**Filtering:** Only log lines within the configured time window (default: 15 minutes before the alert) are kept.

**Ranking:** Lines are scored by relevance — keywords like `ERROR`, `FATAL`, `CRITICAL`, `PANIC`, `EXCEPTION` score highest, followed by lines mentioning the alerting service name. The top lines (default: 500) are sent to Claude for summarization.

Tune these in `kairos.yaml`:

```yaml
context:
  time_window_minutes: 15   # how far back to look
  max_log_lines: 500         # max lines sent to the LLM
```

## Configuration Reference

| Key                        | Required | Default                    | Description                          |
|----------------------------|----------|----------------------------|--------------------------------------|
| `slack.webhook_url`        | Yes      | —                          | Slack incoming webhook URL           |
| `pagerduty.webhook_secret` | Yes      | —                          | HMAC secret for signature validation |
| `log_sources[].type`       | No       | `file`                     | Log source type (only `file` in v0.1)|
| `log_sources[].path`       | Yes      | —                          | Glob pattern for log files           |
| `llm.provider`             | No       | `anthropic`                | LLM provider                         |
| `llm.model`                | No       | `claude-sonnet-4-20250514` | Model to use for summarization       |
| `context.time_window_minutes` | No    | `15`                       | How far back to look for logs        |
| `context.max_log_lines`    | No       | `500`                      | Max log lines to send to LLM         |

Config values support `${ENV_VAR}` interpolation (e.g., `webhook_url: "${SLACK_URL}"`).

## Endpoints

| Method | Path                  | Description                    |
|--------|-----------------------|--------------------------------|
| GET    | `/health`             | Health check                   |
| POST   | `/webhook/pagerduty`  | PagerDuty V3 webhook receiver  |

## Roadmap

- **v0.2**: Datadog and Grafana Loki log source integrations
- **v0.3**: Recent deploy correlation (GitHub/GitLab)
- **v0.4**: Runbook attachment and auto-remediation suggestions

## License

Apache 2.0 — see [LICENSE](LICENSE).
