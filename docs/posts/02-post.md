100K tokens. 200K. 1M. We keep increasing context windows like it solves the problem.

It doesn't. And in production, it's worse than the research suggests.

A friend described his reality: ~10 systems, ~4hr MTTR. Logs in one tool, metrics in another, dashboards outdated, alerts misconfigured. Most of those 4 hours aren't spent fixing — they're spent finding.

Current AI tools do a partial job because they're platform-native. Datadog's AI summarizes Datadog data. Not useful when the root cause spans three different systems.

An intelligent context-engineered workflow has five layers before the LLM sees a single token:

1. Discovery — which of your 10 systems has the signal for this incident?
2. Multi-source fetch with quality assessment — can you trust what you got? Report what's missing.
3. Compression — 5,000 raw lines → 500 deduplicated, pattern-collapsed lines. Every token earns its place.
4. Alert-aware scoring — error rate alerts boost stack traces. Latency alerts boost timeouts. Not all evidence is equally relevant.
5. Structured prompt with repetition — situation first, evidence in the middle, key context repeated at the end. Research shows 3x repetition substantially outperforms single (47/70 wins, 0 losses).

The WSCI framework (Write, Select, Compress, Isolate) governs how context flows into an LLM. The discipline is the same whether you're building for incident response, healthcare, or legal.

We've been building this at Saarthi — applying context engineering across healthcare and on-call. More on that in a future post.

I wrote a deeper piece on the five layers and the research behind them — link in comments.

#ContextEngineering #AI #IncidentResponse #OnCall #LLMs #Reliability
