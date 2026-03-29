# Context Engineering Is Not Context Stuffing

In my previous post, I argued that context engineering is reshaping on-call. A few people asked the obvious question: why can't you just give the LLM all the logs and let it figure it out?

Because that makes things worse, not better. And we have the research to prove it.

## The Reality of Incident Triage in 2026

A friend described his team's setup recently. About ten systems involved in any given incident. Logs in one tool, metrics in another, dashboards that are outdated or misconfigured, alerts that fire on the wrong thresholds, limited access to the code that's actually failing. Their average MTTR is about four hours — and the majority of that time isn't spent fixing the problem. It's spent finding it.

This is normal. I've seen the same pattern at every company I've worked at, from Amazon to TikTok to Vortexa. The tools keep getting better. The cognitive load doesn't shrink.

Current AI-powered incident tools are making progress — Datadog's Bits AI, incident.io, Rootly are all embedding intelligence into their workflows. But most of them are platform-native. Datadog's AI summarizes Datadog data. That works if all your signal is in Datadog. It doesn't work when the root cause spans a deploy log in GitHub, a config change in your CD pipeline, and an error trace in a completely different system.

## Why "Just Use AI" Fails

There's a common assumption: models have 200K token context windows now, so just send everything and let the model figure it out. The research says this is the wrong approach.

**Lost in the Middle** (Liu et al., Stanford, 2023) showed that LLMs exhibit a U-shaped attention curve. They attend well to information at the beginning and end of the context but significantly degrade in the middle. With 20+ documents in the context, model performance dropped *below* the no-context baseline. More data made the model less accurate than giving it nothing at all.

**Needle in the Haystack** (Nelson et al., IBM Research, 2024) demonstrated that even the simplest retrieval task — finding a single planted sentence in a long context — breaks down as context length increases. Longer window, more noise, worse recall.

**Prompt Repetition** (Leviathan et al., Google Research, 2025) found that the *order* and *structure* of information in the prompt materially changes output quality. Simply repeating the query alongside the context improved accuracy in 47 out of 70 benchmark tests with zero regressions. The implication: how you arrange information matters as much as what information you include.

LLM reasoning starts degrading around 3,000 tokens — roughly 50 to 60 log lines. That's not a lot of context when your systems generate thousands of lines per minute.

## It's Not Just Models — It's AI Output in General

This isn't unique to incident triage. CodeRabbit's recent study on AI-generated code (2026) found that AI-authored pull requests contain **1.7x more issues** than human-authored ones. The issues aren't random — they're systematic:

- 75% more logic and correctness errors
- Nearly 2x more error handling gaps
- Up to 2.74x more security issues
- Roughly 8x more performance regressions

The root cause: AI models "infer patterns statistically, not semantically." They miss business logic, local conventions, and context that experienced practitioners internalize. The code *looks right* but skips the guardrails that matter.

Their conclusion: **"Input quality directly correlates with output reliability. Insufficient context amplifies mistakes."**

Replace "code" with "triage summary" or "clinical brief" and the same dynamics apply. A model summarizing 5,000 raw log lines will produce a confident, plausible-sounding summary that misses the actual root cause — because the signal was buried at position 2,500 where the model's attention is weakest.

## What Context Engineering Actually Is

Anthropic's engineering team defines it precisely: finding "the smallest possible set of high-signal tokens that maximize the likelihood of a desired outcome." Intelligence isn't the bottleneck. Context is.

This is an engineering discipline, not a prompt trick. It means:

**Selecting what matters** — not everything is relevant. When a payment service alerts, you don't need the health check logs from your CDN. You need the error logs from the payment service, its upstream dependencies, and the most recent deploy. Knowing which sources to query — based on the service, its dependency graph, and the type of alert — is the first and most important decision.

**Compressing noise** — raw data is noisy. The same retry error appears 47 times. Health checks flood the output. Systematic deduplication and pattern normalization can reduce 5,000 lines to 500 without losing signal. The research shows that models reason better with less, higher-quality input.

**Scoring by relevance** — not all evidence is equally useful. An error-rate alert needs stack traces. A latency alert needs timeout patterns. Scoring needs to understand what kind of question is being asked and weight the evidence accordingly.

**Assessing quality** — knowing what you don't know. If a data source is unreachable, or returns nothing for a service that should have logs, that's critical information. The model needs to see its own blind spots so it can express appropriate confidence.

**Structuring for attention** — arranging the prompt so the model attends to what matters. This isn't formatting — it's aligned with how transformer attention actually works, and the research on prompt repetition confirms it.

These aren't novel concepts individually. What's missing is a systematic approach that applies all of them together, adapts to the specific domain, and works across the disparate systems that real teams actually use.

## The Uncomfortable Implication

Here's what the research implies but rarely gets said: **with disciplined context engineering, a smaller model can approach the output quality of a larger model on structured tasks.**

If the context is 5,000 raw lines with no filtering, you need the most powerful model available, and it still might produce garbage. But if the context is the right 50 lines, correctly scored and structured, a mid-tier model produces an actionable output.

The ACE framework (ICLR 2026) demonstrated this directly: a smaller open-source model with engineered context matched the top-ranked production agent on the AppWorld leaderboard — an agent using a significantly larger model.

This changes the economics. If context engineering is good enough, the model tier becomes a cost lever, not a quality lever.

## What This Doesn't Solve

Context engineering makes the model's output better when the evidence exists and can be retrieved. It doesn't help when:

- **The data doesn't exist.** If your service doesn't log the information needed to diagnose the issue, no amount of engineering will conjure it.
- **The problem requires novel reasoning.** A cascading failure across six services with a non-obvious trigger needs human judgment. The model can surface the evidence; the engineer makes the call.
- **The context is inherently ambiguous.** When logs and metrics tell different stories, a human needs to resolve the contradiction.

The CodeRabbit study confirms: even with good context, AI output needs human review. The goal is to make that review faster — not to eliminate it.

## Where This Goes

The teams that get this right will have measurably lower MTTR — not because they use a fancier model, but because they engineer the context that feeds it. The discipline applies beyond incident management: clinical decision support, legal analysis, customer support — anywhere a decision-maker needs the right information from scattered sources, structured for fast comprehension.

At Saarthi, we've been applying this across healthcare and incident management. The same principles work in both domains. The domain changes. The discipline doesn't.

More on that in a future post.

---

### Further Reading

- [Liu et al.: Lost in the Middle](https://arxiv.org/abs/2307.03172) — Stanford, 2023
- [Nelson et al.: Needle in the Haystack](https://arxiv.org/abs/2407.01437) — IBM Research, 2024
- [Leviathan et al.: Prompt Repetition](https://arxiv.org/abs/2512.14982) — Google Research, 2025
- [CodeRabbit: State of AI vs Human Code Generation](https://www.coderabbit.ai/blog/state-of-ai-vs-human-code-generation-report) — 2026
- [ACE: Agentic Context Engineering](https://arxiv.org/abs/2510.04618) — ICLR 2026
- [Anthropic: Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

---

*This is the second in a series on context engineering in practice. Previously: [The On-Call Engineer's New Partner](#). Reach out on [LinkedIn](https://www.linkedin.com/in/ramanansiva).*
