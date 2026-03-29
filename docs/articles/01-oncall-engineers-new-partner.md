# The On-Call Engineer's New Partner: How AI Is Changing Incident Response

When a PagerDuty alert fires at 3am, the on-call engineer's first 20 minutes look the same everywhere: open the dashboard, grep through logs, check recent deploys, scan for patterns, form a hypothesis. It's detective work under pressure, repeated thousands of times a day across the industry.

And it's not just SRE teams. On-call rotations span support engineers, backend developers, platform teams, and dev teams — anyone who owns a service in production. The 3am page doesn't check your job title.

That ritual is about to change fundamentally. Not because AI will replace the engineer — but because the *investigative grunt work* that precedes every decision is exactly the kind of task AI is built to absorb.

## The Incident Response Tax

Here's the dirty secret of modern incident response: the tools got better, but the cognitive load didn't shrink. We went from monoliths to microservices, from one log file to a hundred, from one dashboard to Datadog plus Grafana plus CloudWatch plus whatever your platform team chose last quarter.

Ask any on-call engineer: the time-to-understand for a production incident hasn't meaningfully improved in a decade. We added observability. We added runbooks. We added war rooms. But the engineer still starts every incident staring at a wall of data, trying to figure out which 15 lines out of 50,000 actually matter.

That's not an engineering problem. That's a *context assembly* problem.

## Context Engineering: Not Just a Buzzword

I've been thinking about context assembly across two very different domains.

At Saarthi, we build AI assistants for doctors — oncologists, nephrologists, gastroenterologists working in ERs and ICUs where decisions are time-critical and information is scattered across charts, lab results, imaging reports, and clinical guidelines. Incident response is the same problem wearing a different hat. The "patient" is a production system. The "charts" are log files. The "clinical guidelines" are runbooks. And the decision-maker — the on-call engineer — is trying to separate signal from noise before things get worse.

In both cases, the bottleneck isn't skill. It's the time spent *loading context into the decision-maker's brain*.

One important caveat: context engineering is not context *stuffing*. You can't dump 50,000 log lines into an LLM and expect a useful answer. Models degrade with longer contexts — they lose information in the middle, struggle with retrieval as noise increases, and are sensitive to how information is ordered. More context often means *worse* results.

The "engineering" is the deliberate work of filtering, ranking, and structuring information so the model can actually use it. The LLM is the reasoning engine. The real work is everything that happens before the prompt. (More on the science behind this in a future post.)

## Three Shifts

The industry is already moving. Datadog's Bits AI SRE performs autonomous, multi-step investigations across telemetry data. Platforms like incident.io and Rootly are embedding AI directly into incident workflows. These tools validate that the core idea is sound — and raise a question worth asking: what should an engineer actually be spending their time on during an incident?

Collecting logs isn't it. Correlating timestamps isn't it. Those are tasks that require attention but not judgment. An engineer's time during an incident belongs to the things only a human can do: deciding the right course of action, coordinating across teams, communicating with stakeholders.

I see three shifts reshaping on-call:

- **Context assembly becomes AI's job.** Alert fires, an agent pulls logs from the relevant time window, filters and ranks by severity, sends the context to an LLM, and posts a triage brief to Slack. The on-call gets a 30-second read — what's happening, key evidence, likely root cause, what to do first. The engineer still makes every decision. They just make it in minute two instead of minute twenty.

- **RCA becomes context assembly too.** During the incident, you need to know *what's happening*. After, you need to know *why*. Both are context assembly — pulling logs, correlating events, tracing the chain of failures. The same approach that generates a triage brief in 30 seconds can draft an RCA in minutes, while the timeline is still fresh.

- **Runbooks become dynamic.** Static runbooks are written once, updated never, and discovered to be outdated at the worst possible moment. Instead of "follow step 3," the AI reads the runbook *and* the current state, and gives context-aware next steps for *this* incident — not the generic playbook written six months ago.

## What This Won't Solve

Let's be honest about the boundaries.

**AI won't replace judgment.** A model can tell you the circuit breaker tripped because of upstream timeouts. It can't tell you whether to failover to an untested backup or wait 10 minutes for the primary to recover. That's a business decision wrapped in a technical one.

**AI won't fix bad observability.** Garbage in, garbage out — just faster and with more confidence, which is arguably worse.

**AI won't eliminate incidents.** Complex systems fail in emergent ways. AI can help you respond faster. It cannot prevent the network partition that takes down your payment pipeline.

## Where This Goes

The real promise isn't faster incident response. It's what happens when the reactive work stops consuming all the oxygen. Engineers get to spend time on what actually matters — building resilient systems, improving observability, eliminating failure modes.

The starting point is simpler than you think — a webhook receiver, a context assembler, an LLM call, and a Slack message. We've been building exactly this at Saarthi, applying the same context engineering approach we use in healthcare to incident management. More on that in a future post.

The interesting question isn't whether AI will transform on-call. It's what the on-call role becomes when the reactive work is compressed — when it looks less like firefighting and more like engineering. That's what on-call was always supposed to enable.

---

### Further Reading

- [Datadog: Introducing Bits AI SRE](https://www.datadoghq.com/blog/bits-ai-sre/) — Autonomous multi-step incident investigation
- [Datadog: How we built an AI SRE agent](https://www.datadoghq.com/blog/building-bits-ai-sre/) — Multi-agent architecture for incident response
- [InfoQ: Human-Centred AI for SRE](https://www.infoq.com/news/2026/01/opsworker-ai-sre/) — Multi-agent systems that assist rather than replace engineers
- [Anthropic: Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) — Context engineering principles and best practices

---

*If you're interested in context engineering — whether for incident response, healthcare, or something else entirely — I'd love to hear what you're building. Reach out on [LinkedIn](https://www.linkedin.com/in/ramanansiva).*
