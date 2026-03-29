AI-generated code has 1.7x more issues than human code. Not because the models are bad — but because "input quality directly correlates with output reliability."

That's from CodeRabbit's study of 470 GitHub PRs. And the same principle applies to every AI system consuming real-world data.

In incident management: ~10 systems, ~4hr average MTTR. Most of that time is spent finding the problem, not fixing it. Current AI tools help, but they're platform-native — Datadog's AI summarizes Datadog data. Not useful when the root cause spans three different systems.

The research is clear on why "just send everything to the model" fails:

- More context often means worse results — performance drops below the no-context baseline with 20+ documents (Liu et al., Stanford)
- LLM reasoning degrades around 3,000 tokens — about 50 log lines (Nelson et al., IBM Research)
- Prompt structure materially changes output — 47/70 accuracy wins just from reordering (Leviathan et al., Google Research)

Anthropic defines context engineering as finding "the smallest possible set of high-signal tokens that maximize the likelihood of a desired outcome." Intelligence isn't the bottleneck. Context is.

The uncomfortable implication: with disciplined context engineering, a smaller model can approach the output quality of a larger model on structured tasks. The ACE framework (ICLR 2026) demonstrated this — a smaller model matched the top-ranked agent by engineering better context.

This isn't about prompt tricks. It's an engineering discipline: what to select, how to compress, how to score by relevance, how to assess quality gaps, and how to structure for attention.

We've been applying this at Saarthi across healthcare and incident management. Same discipline, different domains. More on that soon.

I wrote a deeper piece — link in comments.

#ContextEngineering #AI #IncidentResponse #OnCall #SoftwareEngineering
