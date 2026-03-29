# Context Engineering Is Not Context Stuffing: What LLM Research Tells Us About Building Useful AI

DRAFT — follow-up to "The On-Call Engineer's New Partner"

---

## The Hook

In a previous post, I argued that context engineering — the deliberate assembly of the right information for a decision-maker — is reshaping SRE. Several people asked: why can't you just give the LLM all the logs and let it figure it out?

Because that doesn't work. And the research explains exactly why.

## The Core Problem: LLMs Are Bad at Long Contexts

We talk about models with 100K, 200K, even 1M token context windows as if "can accept" means "can use." It doesn't.

### Lost in the Middle (Liu et al., Stanford, 2023)

- LLMs show a U-shaped attention curve: strong performance on information at the beginning (primacy bias) and end (recency bias) of the context, significant degradation in the middle
- With 20+ documents in the context, model performance can drop below the *no-context baseline* — feeding the model more information made it less accurate than giving it nothing
- This held across models (GPT-3.5-Turbo, Claude 1.3, open-source models) and wasn't fixed by simply having a longer context window
- The implication: if your critical ERROR log line is buried at position 250 out of 500, it's in the exact zone where the model pays the least attention

### Needle in the Haystack (Nelson et al., IBM Research, 2024)

- Even on the simplest possible task — retrieving a single planted fact from a long context — standard LLMs struggle as context length increases
- Longer context window ≠ better retrieval. It means more noise, more distraction, more opportunity for the model to attend to the wrong thing
- External memory mechanisms can help, but they add architectural complexity. The simpler solution: don't put the needle in a haystack in the first place. Reduce the haystack.

### Prompt Repetition (Leviathan et al., Google Research, 2025)

- The *order* of information in the prompt materially affects output quality
- Repeating the query alongside the context improved accuracy in 47 out of 70 benchmark tests, with zero regressions
- Why? Causal language models (which most LLMs are) process tokens left-to-right. They can't "look back" — each token only attends to what came before it. Repeating the question after the context ensures the model has the query in its attention window when generating the answer
- The implication: prompt structure is not cosmetic. It's functional. How you arrange information changes what the model can do with it.

## What This Means for Building Real Systems

These aren't academic curiosities. They have direct implications for anyone building AI systems that consume real-world data:

### 1. Pre-filtering is non-negotiable

Don't send the model everything. Send it what matters. In incident response, that means:
- Filter by time window (only logs from the relevant period)
- Filter by service (only logs from the affected component and its dependencies)
- Score by relevance (ERROR/FATAL/CRITICAL lines first, service name mentions second, everything else last)

The model doesn't do this well on its own. That's your job — before the prompt.

### 2. Ordering matters

Put your highest-signal information at the beginning and end of the context. The middle is where information goes to die.

In practice: lead with the alert details and the most relevant log lines. Put supporting context (lower-severity logs, recent deploy info) after. End with the question/instruction.

### 3. Less is more (until it isn't)

There's a sweet spot between "not enough context" and "too much noise." In our experience building context-engineered systems for both healthcare and SRE:
- Too few lines and the model hallucinates connections that aren't there
- Too many lines and the model misses the connections that are
- The right number depends on signal density — 500 highly filtered lines > 5000 raw lines

### 4. Structure your prompt like a briefing, not a dump

The model performs best when the prompt mirrors how a human expert would want to receive information:
- Situation first (what triggered this)
- Key evidence next (the filtered, ranked data)
- Question last (what do you need from the model)

This isn't just good UX — it's aligned with how causal attention actually works.

## Context Engineering as a Discipline

The pattern across all three papers is the same: **the model's ability to reason is constrained by how you present information to it.** A 200K context window is a capacity limit, not a quality guarantee.

Context engineering is the discipline of working within these constraints:
- **Selection**: choosing what goes in (and what stays out)
- **Ordering**: placing information where the model attends best
- **Structuring**: formatting context so the model can parse it efficiently
- **Scoping**: right-sizing the context for the task

This applies whether you're building an SRE triage tool, a medical AI assistant, a legal document analyzer, or a customer support bot. The domain changes. The discipline doesn't.

At Saarthi, we apply this across healthcare and incident management. The doctor in an ER and the engineer on-call at 3am have the same need: the right information, structured for fast decisions, delivered before the situation gets worse.

## The Takeaway

Next time someone says "just increase the context window" or "just send it all the data," remember:

- More context often means worse results (Lost in the Middle)
- Long-context retrieval is unreliable (Needle in the Haystack)
- Prompt structure changes model behavior (Prompt Repetition)

The LLM is the reasoning engine. Context engineering is everything else — and it's where the real work happens.

---

*This is the second in a series on context engineering in practice. The first post covered how AI is reshaping SRE incident response. Next: how we apply these principles at Saarthi across healthcare and reliability engineering.*

*Reach out on [LinkedIn](https://www.linkedin.com/in/ramanansiva) — I'd love to hear how you're handling context in your AI systems.*
