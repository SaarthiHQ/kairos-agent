# kairos-agent

AI-powered incident context assembler. When an alert fires, kairos pulls logs from your observability tools, assembles context with dependency awareness, uses Claude to generate a triage summary, and posts it to Slack.

The on-call engineer gets a 30-second read instead of 20 minutes of digging.

```
Alert fires → kairos → Logs + Dependencies + Context → Claude → Slack triage brief
```

## 5-Minute Quickstart

### Prerequisites

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/)
- A [Slack incoming webhook URL](https://api.slack.com/messaging/webhooks)
- [ngrok](https://ngrok.com/download) (for receiving webhooks from alert tools)

### 1. Install and setup

```bash
git clone https://github.com/SaarthiHQ/kairos-agent.git
cd kairos-agent
pip install .
kairos-agent setup
```

The interactive setup walks you through connecting your observability tools, discovering services, and generating `kairos.yaml`.

### 2. Test locally

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
kairos-agent test --config kairos.yaml --service your-service
```

### 3. Start with a public tunnel

```bash
kairos-agent --config kairos.yaml --tunnel
```

This starts the server and an ngrok tunnel, then prints the webhook URLs:

```
  kairos-agent v0.3.0
  Public URL: https://your-tunnel.ngrok-free.dev

  Webhook endpoints (use these in your alert tools):
    New Relic:  https://your-tunnel.ngrok-free.dev/webhook/newrelic
    PagerDuty: https://your-tunnel.ngrok-free.dev/webhook/pagerduty
    Slack cmd: https://your-tunnel.ngrok-free.dev/slack/command

  Quick setup:
    1. New Relic → Alerts → Workflows → Add destination → Webhook
    2. Slack → App settings → Slash Commands → Request URL
```

Copy the URLs into your alert tools. Done — alerts now trigger automatic triage.

### 4. Slack slash command (on-demand triage)

Once the Slack slash command is configured, any engineer can type:

```
/kairos investigate payment-service
/kairos investigate api-gateway --title "latency spike"
/kairos status
```

## Source Connectors

kairos pulls logs from multiple backends simultaneously:

| Source | Config type | What it connects to |
|--------|-----------|-------------------|
| **File** | `file` | Local log files via glob patterns |
| **New Relic** | `newrelic` | NerdGraph API (NRQL queries) |
| **Datadog** | `datadog` | Logs Search API v2 |
| **Grafana Loki** | `loki` | query_range HTTP API |
| **Generic HTTP** | `http` | Any REST API that returns logs |

Configure multiple sources per service — kairos queries all of them and merges the results.

## Service Catalog

Declare your services, dependencies, and source mappings:

```yaml
services:
  payment-service:
    depends_on: [stripe-gateway, postgres-primary]
    owners: [payments-team]
    sources: [newrelic-prod, payment-logs]
    tier: critical

  stripe-gateway:
    depends_on: []
    sources: [newrelic-prod]
    tier: critical

log_sources:
  - name: newrelic-prod
    type: newrelic
    credentials:
      api_key: "${NEW_RELIC_API_KEY}"
    options:
      account_id: "1234567"
      query: "SELECT timestamp, message, level, service FROM Log WHERE service = '{service_name}'"
```

When `payment-service` alerts, kairos automatically:
- Pulls logs for payment-service (direct)
- Pulls logs for stripe-gateway and postgres-primary (dependencies)
- Tags dependency logs separately so the model knows the provenance
- Boosts scoring for dependency lines that correlate with the direct service errors

## Context Engineering

kairos doesn't just dump logs into an LLM. It applies context engineering principles:

**Alert-type inference** — Classifies alerts as error_rate, latency, or availability. Boosts relevant log patterns (timeouts for latency alerts, stack traces for error alerts).

**Level 1 compression** — Deduplicates log lines, collapses repetitive patterns (`[x47] connection refused`), normalizes timestamps/IDs/IPs before comparison.

**Token-aware scoping** — Enforces a 10,000-token budget for log context. Every token earns its place.

**Triple prompt repetition** — Key context (service name, alert title) repeated at beginning, middle, and end of the prompt. Based on Leviathan et al. (2025): 47/70 accuracy wins, 0 losses.

**Quality assessment** — Reports which sources succeeded, failed, or returned empty. Flags gaps like "no ERROR lines found despite error-rate alert." Claude factors data quality into its confidence level.

## Architecture

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  New Relic   │  │  PagerDuty   │  │    Slack     │
│  Webhook     │  │  Webhook     │  │  /kairos cmd │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       ▼                 ▼                 ▼
┌─────────────────────────────────────────────────┐
│              webhook_receiver (FastAPI)           │
└──────────────────────┬──────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────┐
│  service_catalog: resolve sources + dependencies  │
│  alert type inference: error_rate/latency/avail   │
└──────────────────────┬───────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────┐
│  sources: File | Datadog | Loki | NewRelic | HTTP │
│  → compressor: dedup, pattern collapse            │
│  → context_assembler: score, filter, token budget │
│  → quality assessment: gaps, confidence            │
└──────────────────────┬───────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────┐
│  summarizer: Claude API with structured prompt    │
│  → triple prompt repetition                       │
│  → alert-type-specific guidance                   │
│  → quality-aware confidence                       │
└──────────────────────┬───────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────┐
│  notifier: Slack Block Kit message                │
└──────────────────────────────────────────────────┘
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/webhook/newrelic` | New Relic alert notifications |
| POST | `/webhook/pagerduty` | PagerDuty V3 webhooks |
| POST | `/slack/command` | Slack slash commands (`/kairos`) |

## CLI Commands

```bash
kairos-agent setup              # Interactive setup — generates kairos.yaml
kairos-agent test               # Simulate a triage against your config
kairos-agent --tunnel           # Start server with ngrok tunnel
kairos-agent                    # Start server (local only)
```

## Configuration Reference

| Key | Required | Default | Description |
|-----|----------|---------|-------------|
| `slack.webhook_url` | Yes | — | Slack incoming webhook URL |
| `pagerduty.webhook_secret` | No | — | HMAC secret for PagerDuty signature validation |
| `log_sources[].type` | No | `file` | Source type: file, newrelic, datadog, loki, http |
| `log_sources[].name` | No | — | Name for service catalog references |
| `log_sources[].credentials` | No | `{}` | API keys, tokens (supports `${ENV_VAR}`) |
| `log_sources[].options` | No | `{}` | Source-specific config (query templates, URLs) |
| `services.<name>.depends_on` | No | `[]` | Service dependencies |
| `services.<name>.sources` | No | `[]` | Source references for this service |
| `services.<name>.tier` | No | `standard` | Service tier: critical, standard, best-effort |
| `services.<name>.owners` | No | `[]` | Team or individual owners |
| `llm.model` | No | `claude-sonnet-4-20250514` | Claude model for summarization |
| `context.time_window_minutes` | No | `15` | How far back to look for logs |
| `context.max_log_lines` | No | `500` | Max log lines before token budget |
| `context.max_context_tokens` | No | `10000` | Token budget for log context |

## License

Apache 2.0 — see [LICENSE](LICENSE).
