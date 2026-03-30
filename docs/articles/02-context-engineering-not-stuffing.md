# Context Engineering Is Not Context Stuffing

In my previous post, I argued that context engineering is reshaping on-call. A few people asked the obvious question: why can't you just give the LLM all the logs and let it figure it out?

Because that doesn't work. And the reality of production systems makes it even harder than the research suggests.

## The Real Problem: 10 Systems, 4 Hours

Before we get to the research, let's talk about what incident triage actually looks like.

A friend recently described his team's setup: ~10 systems involved in any given incident. Logs in one tool, metrics in another, dashboards that are outdated or misconfigured, alerts that fire on the wrong thresholds, limited access to the code that's actually failing. Their average MTTR is about 4 hours — and most of that time is spent not fixing the problem, but finding it.

This is the norm. I've seen the same pattern at every company I've worked at, from Amazon to TikTok to Vortexa. The tools keep getting better. The cognitive load doesn't shrink.

Current AI-powered incident tools are making progress — Datadog's Bits AI, incident.io, Rootly are all embedding intelligence into their workflows. But most of them are platform-native. Datadog's AI summarizes Datadog data. That works if all your signal is in Datadog. It doesn't work when the root cause spans a deploy log in GitHub, a config change in your CD pipeline, and an error trace in a completely different system.

Context engineering starts before the LLM sees anything. It starts with knowing where to look.

## Two Domains, Same Problem

At Saarthi, we build AI systems for two very different users: doctors in ERs and ICUs, and on-call engineers during production incidents. Different domains. Same bottleneck.

A nephrologist receiving a referral from a cardiologist doesn't need the patient's full history. They need creatinine trends, current medications (especially nephrotoxic ones), and the specific question the cardiologist is asking. A 50-page record is noise. Five relevant data points are signal.

An SRE getting paged about a payment service failure doesn't need every log line from every service. They need error logs from the payment service, logs from its upstream dependencies, and the most recent deploy. 5,000 lines of health checks is noise. The 5 lines showing the cascade is signal.

In both cases, the human is the expert reasoner. The doctor makes the clinical judgment. The engineer makes the triage call. But before they can reason, someone — or something — needs to assemble the right context.

That assembly step is where most of the time is spent. And it's where current AI tools fall short.

## What the Research Says

Even when you have the data, throwing it all at a model doesn't work.

**Lost in the Middle** (Liu et al., Stanford, 2023) showed that LLMs exhibit a U-shaped attention curve — strong at the beginning and end of the context, significant degradation in the middle. With 20+ documents, performance dropped *below* the no-context baseline. More data made the model less accurate than giving it nothing.

**Needle in the Haystack** (Nelson et al., IBM Research, 2024) demonstrated that even simple fact retrieval — finding a single planted sentence — breaks down as context length increases. Longer window, more noise, worse recall.

**Prompt Repetition** (Leviathan et al., Google Research, 2025) revealed that the *order* of information in the prompt materially changes output quality. Repeating the query after the context improved accuracy in 47 out of 70 tests with zero regressions — because causal models process left-to-right and can't attend backwards.

LLM reasoning starts degrading around 3,000 tokens — roughly 2,000 words, about 50-60 log lines. That's not a lot of context when your systems generate thousands of lines per minute.

Anthropic's engineering team frames it precisely: context engineering is about finding "the smallest possible set of high-signal tokens that maximize the likelihood of a desired outcome." Intelligence isn't the bottleneck. Context is.

## It's Not Just Models — It's AI Output in General

CodeRabbit's study of 470 GitHub PRs (2026) found that AI-authored work contains **1.7x more issues** than human work — 75% more logic errors, nearly 2x more error handling gaps, up to 2.74x more security issues.

The root cause: AI models "infer patterns statistically, not semantically." They miss business logic, local conventions, and context that experienced practitioners internalize.

Their conclusion: **"Input quality directly correlates with output reliability."**

Replace "code" with "triage summary" or "clinical brief" and the same dynamics apply. A model summarizing 5,000 raw log lines will produce a confident, plausible-sounding summary that misses the actual root cause — because the signal was buried at position 2,500 where the model's attention is weakest.

## The Abstention Problem

Here's where it gets uncomfortable.

AbstentionBench (June 2025) evaluated 20 frontier models on their ability to say "I don't know" across diverse question types — unanswerable questions, false premises, underspecified problems, subjective topics.

Two findings that matter:

First: **scaling doesn't help.** Larger models are not better at abstaining. The ability to know your limits is not a capability that improves with more parameters.

Second: **reasoning fine-tuning makes it worse.** Reasoning-trained models like DeepSeek R1 showed a **24% drop** in abstention compared to their non-reasoning counterparts. Teaching a model to reason harder makes it *less* likely to admit it doesn't know.

This is a fundamental observation. The path to expert-level AI is not "make the model smarter." Smarter models are worse at knowing their limits.

## What an Intelligent Context-Engineered Workflow Looks Like

Most tools jump straight to "send logs to the model." An intelligent workflow has five layers before the LLM sees a single token.

### Layer 1: Discovery — where to look

When payment-service alerts, which of your 10 systems has the signal? Application logs might be in New Relic, infrastructure metrics in CloudWatch, recent deploys in GitHub Actions, the runbook in Confluence.

An intelligent engine maintains a *service catalog* — a map of services to their log sources, dependencies, and owners. When an alert fires, it already knows: payment-service logs are in New Relic, it depends on stripe-gateway (also in New Relic) and postgres-primary (in Datadog). Query those three, not all ten.

This is the *Selection* principle from the WSCI framework (Write, Select, Compress, Isolate) — choosing what goes in and what stays out. The most important decision happens before any data is fetched.

### Layer 2: Multi-source fetch with quality assessment

The engine queries each source, but it also assesses what came back. Did New Relic return a 403? Flag it. Did Loki return zero lines for a service that should have logs? That's a signal too — maybe the service crashed, maybe logging is broken.

Report what's *missing*, not just what's there. The model needs to know its own blind spots.

### Layer 3: Compression — making every token count

Raw logs are noisy. The same retry error appears 47 times. Health checks flood the output. A 15-minute window might produce 5,000 lines, but only 50 carry real signal.

Rule-based compression handles this without an LLM:
- **Deduplication** — identical lines collapsed: `[x47] connection refused to postgres:5432`
- **Pattern normalization** — lines differing only in timestamps, request IDs, or durations are recognized as the same event
- **Repetition collapse** — the first occurrence is kept with a count annotation

500 compressed lines carry more signal than 5,000 raw lines. This is the *Compress* principle — making every token earn its place.

### Layer 4: Alert-aware scoring and token budgeting

Not all log lines are equally relevant, and the scoring should reflect the type of alert:
- Error rate alert → boost ERROR, FATAL, EXCEPTION, stack traces
- Latency alert → boost timeout, slow, p99, duration, deadline exceeded
- Availability alert → boost connection refused, health check, OOM, SIGKILL

The scored lines compete for a token budget — not just a line count. With a 10,000-token budget, the highest-signal lines win. Dependency lines compete at a discount so direct-service evidence is preferred when the budget is tight.

This is *Scoping* — right-sizing the context for the task.

### Layer 5: Structured prompt with repetition

The prompt isn't just "here are some logs, summarize them." It's engineered:
- **Situation first** (alert details, service metadata, dependencies) — primacy position
- **Quality report next** (so the model calibrates confidence before reading evidence)
- **Evidence in the middle** (the scored, compressed, budget-constrained log lines)
- **Key context repeated at the end** (service name, alert title) — recency position

Triple prompt repetition: the key identifiers appear at the beginning, as an anchor in the middle of the log block, and in the closing task instruction. Leviathan et al. showed that repeating the query three times substantially outperforms single repetition. The cost is only in the parallelizable prefill stage — latency barely changes.

This is *Ordering* — placing information where the model attends best.

## The Assembly-Reasoning Split

Working across healthcare and incident management led us to a realization: expertise has two distinct components, and they're often performed by different actors.

**Intelligent assembly** — knowing what context to gather, for whom, at what moment. This is pattern matching on what-context-helps-when. It's what a senior nephrologist does before they start reasoning about the case — they know which data points to look at.

**Domain reasoning** — given assembled context, drawing conclusions and deciding actions.

The critical finding from our field work: **in most high-stakes domains, the human is the reasoner.** Doctors in routine clinical settings didn't want AI reasoning. They wanted the right context at the right time so they could reason faster. SREs in some cases want AI reasoning (triage brief, RCA), but the foundation is always the same: the context must be assembled first.

This means the higher-value, more tractable problem is not "how do we make AI reason better" but "how do we make AI assemble context like an expert would."

## The Uncomfortable Implication

With disciplined context engineering, a smaller model can approach the output quality of a larger model on structured tasks.

The ACE framework (ICLR 2026) demonstrated this: a smaller open-source model with engineered context matched the top-ranked production agent — which used a significantly larger model. At the ARC Prize 2025, a 76K-parameter system outperformed models 1,000x its size through structured representation rather than scale.

This changes the economics. If context engineering is good enough, the model tier becomes a cost lever, not a quality lever.

## The Levers

Context engineering isn't a black box. The levers are split between the system and the user:

**What the engine controls:**
- Scoring algorithm and alert-type boosts
- Compression (dedup, pattern normalization)
- Token budget enforcement
- Prompt structure and repetition
- Quality assessment and gap detection

**What the user configures:**
- Which sources to connect (New Relic, Datadog, Loki, any REST API)
- Service catalog — services, dependencies, owners, tiers
- Query templates — per-source filters that express domain knowledge
- Time window and token budget — tunable per team

The engine knows how LLMs work. The user knows how their system works. Both are necessary.

## What This Doesn't Solve

Context engineering makes the model's output better when evidence exists and can be retrieved. It doesn't help when:

- **The data doesn't exist.** No amount of engineering conjures data that was never logged.
- **The problem requires novel reasoning.** A cascading failure with a non-obvious trigger needs human judgment. The model can surface the evidence; the engineer makes the call.
- **The context is inherently ambiguous.** When logs and metrics tell different stories, a human needs to resolve the contradiction.

And the AbstentionBench finding is a reminder: even with perfect context, the model may still overclaim. External constraints help, but the architecture's bias toward fluent output remains.

The goal is to make expert-level decisions faster — not to eliminate the expert.

## Where This Goes

The teams that get this right will have measurably better outcomes — lower MTTR for incidents, faster clinical decisions, more accurate triage — not because they use a fancier model, but because they engineer the context that feeds it.

At Saarthi, we've been applying this across healthcare and incident management. The same principles work in both domains. The domain changes. The discipline doesn't.

More on that in a future post.

---

### Further Reading

- [Liu et al.: Lost in the Middle](https://arxiv.org/abs/2307.03172) — Stanford, 2023
- [Nelson et al.: Needle in the Haystack](https://arxiv.org/abs/2407.01437) — IBM Research, 2024
- [Leviathan et al.: Prompt Repetition](https://arxiv.org/abs/2512.14982) — Google Research, 2025
- [CodeRabbit: State of AI vs Human Code Generation](https://www.coderabbit.ai/blog/state-of-ai-vs-human-code-generation-report) — 2026
- [AbstentionBench: Reasoning LLMs Fail on Unanswerable Questions](https://arxiv.org/abs/2506.09038) — 2025
- [ACE: Agentic Context Engineering](https://arxiv.org/abs/2510.04618) — ICLR 2026
- [Anthropic: Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Vizuara: Context Engineering Workshop](https://context-engineering.vizuara.ai/)

---

*This is the second in a series on context engineering and expert AI systems. Previously: [The On-Call Engineer's New Partner](#). Reach out on [LinkedIn](https://www.linkedin.com/company/saarthihq/).*
