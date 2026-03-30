# What Is an Expert? A Working Definition for Saarthi

**Ramanan Sivasubramanian — March 30, 2026**
**Internal document — shared definition for Saarthi research direction**

---

## The Question

We want to build AI systems that behave like domain experts — in healthcare, in incident management, and eventually in other domains. Current LLMs don't qualify. They're fluent but not expert. The question is: what exactly is the gap, and what would it take to close it?

## Five Properties of an Expert

### 1. Calibrated self-knowledge

An expert knows the boundary of their competence — not vaguely, but precisely.

A junior doctor says: "I think this could be serious."
An expert says: "I can't differentiate between X and Y without a creatinine level. Order that first. Until then, I will not speculate."

A junior SRE says: "Looks like a database issue."
An expert says: "The logs show timeouts but the metrics show normal latency. That means the instrumentation is broken, not the database. I need to see the metrics pipeline before I can triage the service."

Self-knowledge has two components:
- **Knowing what you have** — "I have these 5 data points, they point to this conclusion"
- **Knowing what you lack** — "I don't have deploy data, so I cannot rule out a deploy regression"

The second component is what current LLMs fundamentally cannot do. The softmax function forces a probability distribution that always sums to 1. There is no "I don't know" in the output space. The model must always commit to a prediction, even when it has no basis for one.

### 2. Domain compression

An expert doesn't process more data than a novice. They process the *right* data. They look at 5,000 log lines and their attention goes to the 5 that matter. They read a 50-page patient history and extract the 3 findings relevant to the current complaint.

From information theory: experts have **lower entropy in their predictions within their domain**. They've learned which distinctions matter and which don't. A novice treats all lab values equally. An expert knows that a creatinine of 2.8 in a diabetic patient is urgent, while the same value post-surgery might be expected and transient.

This is the property that context engineering addresses most directly. Selection, compression, scoring — these are external implementations of the compression that an expert does internally. The framework is, in effect, a domain compression layer.

### 3. Judgment under ambiguity

When evidence contradicts, an expert doesn't average the signals or pick the loudest one. They reason about *why* the signals contradict.

"The logs say no errors but the error rate metric is at 50%. A novice says 'conflicting data.' An expert recognizes: the logging system is broken, not the service."

"The patient's symptoms suggest diagnosis A, but their age and history make B more likely. A novice picks A (matches symptoms). An expert orders a specific test that distinguishes A from B before committing."

This requires **meta-reasoning** — thinking about the structure of the evidence, not just its content. Why am I seeing what I'm seeing? What would I expect to see if hypothesis A were true vs hypothesis B? Which data point, if different, would change my conclusion?

Current LLMs can do this when explicitly prompted ("consider alternative hypotheses"). But they don't do it natively. They pattern-match to the most statistically likely conclusion from training data, not from first-principles reasoning about the specific evidence at hand.

### 4. Principled refusal

This is the defining property. **An expert is defined as much by what they refuse to do as by what they do.**

A good doctor doesn't guess when they don't have enough data. They say: "I need an MRI before I can tell you what's wrong. Acting without it risks misdiagnosis."

A good SRE doesn't deploy a speculative fix at 3am. They say: "I don't have enough information to act safely. Let me gather more data before we make this worse."

This isn't caution — it's competence. The willingness to not-act when the cost of being wrong exceeds the cost of waiting is a hallmark of expertise. Novices act to demonstrate competence. Experts refuse to demonstrate it.

**The mathematical problem:** The transformer architecture makes principled refusal structurally impossible. The softmax function forces output. The training objective (next-token prediction) rewards fluency over abstention. There is no mechanism for "I have insufficient basis for this prediction."

This is not a prompting problem. It's a representation problem. The model's latent space does not distinguish between "I know this from evidence" and "I'm pattern-completing because I must produce something." Both produce equally fluent output.

### 5. Structured knowledge that persists and compounds

An expert doesn't start from zero each time. They carry structured knowledge:
- **Episodic**: "Last time I saw this pattern in this patient, it was X"
- **Semantic**: "This class of drugs interacts with that class"
- **Procedural**: "When I see A + B, I always check C before concluding"

Current LLMs have parametric knowledge (from training) and in-context knowledge (from the prompt). But they have no **session-persistent structured knowledge** that compounds over interactions. Every conversation starts fresh. Every triage starts without memory of the previous one.

An expert oncologist seeing a patient for the 5th time doesn't re-read the entire history. They know: "Last visit we adjusted the dosing. Let me check if it worked." That's structured, persistent, compounding knowledge. Current architectures don't have it.

## Is an Expert a State or a Process?

**Both, in sequence.**

An expert starts as a state — a configuration of knowledge and constraints:
- Domain rules (what's important, what's dangerous, what's irrelevant)
- Entity relationships (service dependencies, drug interactions, legal precedents)
- Procedures (when I see X, do Y before Z)

This is the "competent" level of the Dreyfus skill acquisition model. It's achievable through configuration.

An expert becomes a process — a system that improves through experience:
- Notices patterns across cases ("this service always fails because of X")
- Learns from corrections ("my last triage missed the root cause, I need to weight deploy data higher")
- Develops calibrated intuition ("this *feels* like a Stripe issue" — based on accumulated pattern matching, not explicit rules)

This is the "proficient" and "expert" levels of Dreyfus. It requires learning loops, memory, and the ability to modify one's own behavior.

The trajectory: **Configuration → Calibration → Learning → Expertise.**

## What Current LLMs Get Right

It's worth acknowledging what current models do well:

- **Pattern recognition across vast domains** — they've seen more medical literature, more code, more incident reports than any human expert
- **Flexible reasoning** — they can follow complex instructions and reason over novel combinations of evidence
- **Language generation** — they communicate findings in natural, accessible language
- **Speed** — they produce a triage brief in seconds, not minutes

These are not trivial. A model with the right context, the right constraints, and the right domain configuration can produce output that is useful to an expert, even if it is not itself an expert. This is the practical opportunity.

## The Gap: What's Missing

| Property | Current LLMs | With context engineering | Full expert |
|---|---|---|---|
| Domain compression | Poor (attends to everything) | Strong (external selection + scoring) | Native (internal attention allocation) |
| Self-knowledge (what it has) | None | Strong (quality assessment) | Native (epistemic state tracking) |
| Self-knowledge (what it lacks) | None | Good (explicit gap detection) | Native (imprecise probabilities) |
| Principled refusal | Cannot (softmax forces output) | Partial (prompt instruction + constraints) | Native (abstention mechanism) |
| Judgment under ambiguity | Weak (pattern-matches most likely) | Moderate (contradiction detection) | Strong (meta-reasoning over evidence structure) |
| Persistent knowledge | None (stateless) | Designed (memory layer, v0.4+) | Native (episodic + semantic memory) |
| Calibrated confidence | Poor (confident when wrong) | Moderate (post-generation override) | Native (evidential deep learning) |

**Context engineering + constraints gets 85-90% of expert behavior on structured tasks.** The remaining 10-15% requires architectural innovation.

## Implications

1. **The 85-90% is buildable now** — and it's commercially valuable. A system that compresses domain data, assesses quality, enforces constraints, and delivers structured analysis is better than what any team has today for incident triage or clinical decision support.

2. **The 10-15% is the research frontier** — principled refusal, meta-reasoning under ambiguity, and calibrated confidence require models that natively represent what they know and don't know. This is where architectural innovation matters.

3. **The bridge between them is the constraint layer** — structured output requirements, mandatory citation, domain invariant checking, and negation rules that bound the model's behavior within safe limits. Not guaranteed, but significantly safer than unconstrained generation.

4. **Writing is a way of clarifying this for ourselves more than for the public.** But what we clarify can be shared — the problem definition, the gap analysis, the properties of expertise. The solutions are where the IP lives.

---

*Working document. To be compared with Rohan's independent definition and iterated.*
