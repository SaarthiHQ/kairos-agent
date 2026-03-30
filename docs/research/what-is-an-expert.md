# What Is an Expert? A Working Definition for Saarthi

**Ramanan Sivasubramanian — March 30, 2026**

---

## The Question

We want to build AI systems that behave like domain experts — in healthcare, in incident management, and eventually in other domains. Current LLMs don't qualify. They're fluent but not expert. The question is: what exactly is the gap, and what would it take to close it?

## Four Properties of an Expert

### 1. Calibrated self-knowledge

An expert knows the boundary of their competence. Not just "low confidence" — but precisely what they need to make a call and what happens without it.

A junior doctor says: "I think this could be serious."
An expert says: "I can't differentiate between X and Y without a creatinine level. Order that first."

A junior SRE says: "Looks like a database issue."
An expert says: "The logs show timeouts but the metrics show normal latency. That means the instrumentation is broken, not the database. Check the metrics pipeline."

**The mathematical problem:** Current transformers have no epistemic state. They can't distinguish "I have strong evidence for this" from "I'm pattern-completing because I have to produce something." The softmax function forces a probability distribution that always sums to 1 — there is no "I don't know" in the output space.

### 2. Domain compression

An expert doesn't process more data. They process the right data. They look at 5,000 log lines and their attention goes to the 5 that matter. They read a 50-page patient history and extract the 3 findings relevant to the current complaint.

This is an information-theoretic property: experts have lower entropy in their predictions within their domain. They've learned which distinctions matter and which don't.

**This is what context engineering does.** Selection, compression, scoring — these are external implementations of the compression that an expert does internally. The framework IS the domain compression layer.

### 3. Judgment under ambiguity

When evidence contradicts, an expert doesn't average the signals or pick the loudest one. They reason about *why* the signals contradict.

"The logs say no errors but the error rate metric is at 50%. A novice would say 'conflicting data.' An expert recognizes: the logging system is broken, not the service. Fix the observability before triaging the incident."

"The patient's symptoms suggest diagnosis A, but their age and history make B more likely. A novice picks A (matches symptoms). An expert orders a specific test that distinguishes A from B."

**This requires reasoning over the structure of evidence, not just the content.** It's meta-reasoning — thinking about why you're seeing what you're seeing.

### 4. Principled refusal

This is the defining property. **An expert is defined as much by what they refuse to do as by what they do.**

A good doctor doesn't guess when they don't have enough data. They say: "I need an MRI before I can tell you what's wrong." A good SRE doesn't deploy a speculative fix at 3am. They say: "I don't have enough information to act. Let me gather more data before we make this worse."

Current LLMs cannot do this. They always produce an output. The architecture forces it.

## Is an Expert a State or a Process?

**Both.** An expert starts as a state (configured knowledge) and becomes a process (learning system).

**Expert as state** — the Dreyfus "competent" level:
- Configured with domain rules (scoring, compression, catalog)
- Knows the domain topology (service dependencies, patient comorbidities)
- Applies the right framework to the right question type
- This is what our context engine does today

**Expert as process** — the Dreyfus "proficient" and "expert" levels:
- Learns from each interaction (which triages were useful, which missed the mark)
- Notices patterns across interactions (this service always fails because of X)
- Adapts its own behavior (adjusts scoring weights, changes source priority)
- Develops "intuition" — fast pattern matching based on accumulated experience
- This is the ACE Reflector → Curator loop, the intelligence layer we've designed

The trajectory: Configuration → Calibration → Learning → Expertise.

## The Constraint-Based Approach to "I Don't Know"

Since we can't change the transformer architecture (it will always produce output), we need **external constraints that negate invalid response paths.** This is the engineering solution while the architecture catches up.

### What constraints can enforce

Constraints are rules that evaluate the model's output (or intermediate state) and block or modify it when it violates domain invariants. Think of them as guardrails that are mathematically rigorous, not just prompt instructions.

### Three layers of constraints

**Layer 1: Pre-generation constraints (what the model sees)**

These constrain the *input* to reduce the surface for hallucination:

- **Evidence-grounded context only.** If a claim isn't supported by the input evidence, the model shouldn't have a basis to make it. Our context engine does this — we only feed scored, compressed, quality-assessed evidence.
- **Explicit negative context.** Tell the model what it DOESN'T have: "No deployment data available. No metrics source configured. saarthi-flask returned 0 lines." This gives the model the information it needs to refuse.
- **Closed-world assumption in the prompt.** "Base your analysis ONLY on the evidence provided. If the evidence is insufficient to make a determination, say so explicitly. Do NOT infer information not present in the logs."

**Layer 2: Structural output constraints (what the model produces)**

These constrain the *output format* to force the model through checkpoints:

- **Mandatory evidence citation.** For every claim in the triage, the model must cite a specific log line. Claims without citations are structurally invalid.

```
Required format:
  Claim: [statement]
  Evidence: [quoted log line or "INSUFFICIENT — cannot determine"]
```

If the model can't fill the Evidence field for a claim, the constraint forces it to write "INSUFFICIENT" — which IS the "I don't know."

- **Confidence as a required field, not optional.**

```
For each finding, state:
  Confidence: HIGH (multiple corroborating evidence lines)
            | MEDIUM (single evidence line, consistent with context)
            | LOW (inferred, no direct evidence)
            | CANNOT_DETERMINE (insufficient data)
```

The model MUST classify each finding. This is a structural constraint — not a suggestion.

- **Contradiction detection as a required step.**

```
Before your final summary, list any contradictions:
  - Signal A says X, but Signal B says Y
  - If no contradictions: "No contradictions detected"

For each contradiction, state which signal you trust and why.
```

This forces the model to explicitly reason about conflicting evidence rather than silently averaging.

**Layer 3: Post-generation validation (what gets through)**

These are checks AFTER the model generates, before delivery:

- **Citation verification.** Parse the output, extract cited log lines, verify they exist in the input context. If a citation is fabricated, flag or remove the claim.

- **Confidence calibration check.** If the model says "HIGH confidence" but the quality assessment shows 0% source coverage, override to "LOW — quality assessment indicates missing data."

- **Domain invariant checks.** Rules that are always true in the domain:
  - Incident management: "If error_count is 0 and alert type is error_rate, the triage MUST flag this as a logging issue, not confirm no errors"
  - Healthcare: "If a drug interaction exists between two medications in the patient's list, the summary MUST mention it, regardless of whether it's relevant to the current complaint"

- **Negation rules.** Explicit rules that block certain response paths:

```python
NEGATION_RULES = [
    # Never suggest a root cause without evidence
    {
        "if": "root_cause is stated",
        "require": "at least one cited log line supports it",
        "else": "rewrite as 'Possible root cause (unconfirmed): ...' "
    },
    # Never claim the system is healthy during an active alert
    {
        "if": "alert is active AND urgency is high",
        "block": "claims that the service is operating normally",
    },
    # Never recommend an action that contradicts a known constraint
    {
        "if": "action suggested",
        "check": "action does not conflict with domain rules",
        "example": "don't suggest restarting production DB without explicit approval"
    },
]
```

### How constraints compose with context engineering

```
Input → Context Engine (Select, Compress, Score, Quality)
    → Pre-generation constraints (closed world, explicit negatives)
    → LLM generation
    → Structural output constraints (citations, confidence, contradictions)
    → Post-generation validation (verify citations, check invariants, apply negation rules)
    → Validated output OR rejection ("I cannot produce a reliable triage")
```

The constraints don't replace the LLM's reasoning. They **bound it.** The model reasons freely within the bounds. When it tries to step outside (hallucinate, overclaim, skip uncertainty), the constraints catch it.

This is analogous to how type systems work in programming: the programmer writes the logic, the type system catches the errors. The LLM writes the triage, the constraint system catches the hallucinations.

## The Delta: What's Left

| Capability | Context engineering | + Constraints | + Architecture change |
|---|---|---|---|
| Domain compression | ✓ Fully solved | | |
| Self-knowledge (what it has) | ✓ Quality assessment | | |
| Self-knowledge (what it lacks) | ✓ Gap detection | ✓ Explicit negatives | |
| Principled refusal | Partial (prompt instruction) | ✓ Structural enforcement | ✓ Native epistemic state |
| Judgment under ambiguity | Partial (prompt instruction) | ✓ Contradiction detection | ✓ Imprecise probabilities |
| Calibrated confidence | Partial (prompt instruction) | ✓ Post-generation override | ✓ Evidential deep learning |
| Learning from feedback | Not yet (v0.4+) | | |
| Pattern accumulation | Not yet (v0.4+) | | |

**Context engineering + constraints gets us 85-90% of expert behavior.** The remaining 10-15% requires architectural innovation — models that natively represent epistemic uncertainty.

The 85-90% is buildable now. The 10-15% is the research frontier.

## Implications for Saarthi

1. **Short-term (now):** Build the constraint layer into the framework. Mandatory citations, structural confidence, contradiction detection, post-generation validation. This is the highest-impact improvement for the least effort.

2. **Medium-term (6-12 months):** Add the learning loop (ACE Reflector → Curator). The system learns which constraints fire most often (indicating systematic model weaknesses) and adjusts the context engineering to preempt them.

3. **Long-term (research):** Investigate evidential deep learning and energy-based models for generative tasks. Can we build a model that natively produces calibrated uncertainty? This is the PhD-level question.

4. **The product insight:** The constraint layer is a SaaS differentiator. Open-source gets the context engine. The managed service gets the constraints (domain-specific invariants, citation verification, negation rules). This is hard to replicate because the constraints encode domain expertise.

---

*This document is a working definition, not a final answer. It should evolve as we build, test, and learn what works.*
