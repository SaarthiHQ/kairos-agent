# Introducing kairos-agent: Context Engineering for Incident Response, Open Source

DRAFT — third in the series, follows "Context Engineering Is Not Context Stuffing"

---

## The Hook

In my first post, I argued that AI is reshaping SRE by compressing the time between alert and informed action. In the second, I broke down why context engineering — not context stuffing — is the discipline that makes this work.

This post is the "show, don't tell." We built kairos-agent, and we're open-sourcing it.

## The Problem (Recap — Keep Brief)

Quick re-anchor for anyone who missed the earlier posts:
- On-call engineer gets paged
- Spends 15-20 minutes grepping logs, checking dashboards, forming a hypothesis
- The bottleneck isn't the fix — it's understanding what's happening
- That understanding requires assembling context from scattered sources under time pressure

## What kairos Does

kairos-agent intercepts the alert and does the context assembly before the engineer opens their laptop.

The pipeline:
1. **PagerDuty webhook fires** — kairos receives the alert with incident details
2. **Context assembler pulls logs** — filters by time window, scores by relevance (ERROR/FATAL keywords, service name mentions, stack traces), keeps the top N lines
3. **Claude summarizes** — structured triage brief: what's happening, key evidence, likely root cause, suggested next steps
4. **Slack delivers** — the on-call engineer gets a 30-second read instead of a 20-minute dig

The engineer still makes every decision. kairos just front-loads the context.

## Context Engineering in Practice

This is where the earlier posts come to life. kairos doesn't dump logs into Claude and hope for the best. Each step is deliberate:

**Selection** — Only logs from the configured time window (default: 15 minutes before the alert). Only from sources matching the affected service. Already a 10-100x noise reduction before the model sees anything.

**Scoring** — Lines are ranked: ERROR/FATAL/CRITICAL/PANIC/EXCEPTION get highest weight. Service name mentions get a boost. Stack trace continuations are kept together. The top 500 lines (configurable) survive.

**Ordering** — Scored lines are re-sorted chronologically so the model sees a coherent timeline, not a jumbled ranking. The alert details (what fired, which service, urgency) come first in the prompt. The question comes last.

**Structuring** — The prompt explicitly requests a structured output: situation, evidence, root cause hypothesis, next steps. The model isn't asked to "summarize these logs" — it's asked to produce a triage brief.

These are the principles from "Lost in the Middle," "Needle in the Haystack," and "Prompt Repetition" — applied to a real system, not a benchmark.

## What It Supports Today (v0.1)

Being honest about where we are:
- **Log sources:** File-based logs with glob patterns (e.g., `/var/log/app/*.log`)
- **Timestamp formats:** ISO 8601, common log format, syslog, simple datetime
- **Alerts:** PagerDuty V3 webhooks with HMAC signature validation
- **Summarization:** Claude (configurable model)
- **Notification:** Slack via incoming webhooks
- **Deployment:** Docker Compose or pip install

It's an MVP. It works. It's not production-hardened yet.

## What's Coming

- **v0.2:** Datadog and Grafana Loki log source integrations — because most teams don't have logs on disk anymore
- **v0.3:** Recent deploy correlation from GitHub/GitLab — "was anything deployed in the last hour?" is the first question every on-call engineer asks
- **v0.4:** Runbook attachment and context-aware remediation suggestions — the "living runbooks" idea from post 1

## Try It

[TODO: Link to SaarthiHQ/kairos-agent on GitHub once ready]

```
cp kairos.yaml.example kairos.yaml
# Add your Slack webhook URL and PagerDuty secret
export ANTHROPIC_API_KEY="sk-ant-..."
docker compose up --build
```

Five minutes to a working triage pipeline. The README has a curl command to simulate a PagerDuty alert and see it end-to-end.

## Why Open Source

Context engineering for incident response shouldn't be locked behind a vendor. Every SRE team's logs, services, and escalation patterns are different. The tool needs to be something you can read, modify, and extend.

We built kairos at Saarthi because we needed it — the same context engineering principles we use in healthcare apply to reliability engineering. We're open-sourcing it because the SRE community has given us tools for years, and this is how we give back.

If you're building on top of kairos or applying context engineering in your own domain, I want to hear about it.

---

*This is the third in a series on context engineering in practice. [Post 1: how AI is reshaping SRE](#). [Post 2: why context engineering, not context stuffing](#). Next: lessons from applying context engineering across healthcare and SRE — what transfers and what doesn't.*

*GitHub: [SaarthiHQ/kairos-agent](https://github.com/SaarthiHQ/kairos-agent)*
*Reach out on [LinkedIn](https://www.linkedin.com/in/ramanansiva)*
