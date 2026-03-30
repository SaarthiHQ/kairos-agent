# Grant One-Pager: Toward Expert AI Systems Through Structured Latent Intelligence

**Ramanan Sivasubramanian**, **Rohan Jahagirdhar**
Founders, Saarthi (saarthihealth.com)

---

## The Problem

Large Language Models generate confident output regardless of whether they have sufficient evidence. The softmax function forces a probability distribution on every prediction — there is no mechanism for "I don't know." In high-stakes domains, this produces outputs that are statistically plausible but potentially dangerous.

This is not a training problem. It is an architectural one.

Chollet (2019) argued that LLMs cannot reason — they memorize patterns and replay them. When the memorized program doesn't apply, they fail. The ARC-AGI benchmark confirms this: frontier models achieve only 24% on tasks humans find trivial. AbstentionBench (2025) reveals a deeper issue: **reasoning-trained models are 24% worse at abstaining** than their non-reasoning counterparts. Making models smarter makes them worse at knowing their limits.

Current mitigations (RLHF, prompt engineering, output filtering) operate outside the model's representational core. Safety is corrected after the fact, not enforced by construction.

## The Key Insight: Assembly vs Reasoning

Our field experience across healthcare and incident management reveals that expertise has two distinct components:

**Intelligent assembly** — knowing what context to gather, for whom, at what moment. When a cardiologist refers a patient to a nephrologist, an expert system surfaces creatinine trends and nephrotoxic medications, not the dermatology visit from six months ago. When a payment service alerts, it pulls logs from the payment service AND its upstream dependency, not every service in the cluster.

**Domain reasoning** — given assembled context, drawing conclusions, weighing competing hypotheses, and arriving at actionable decisions.

Critically: **in most high-stakes domains, the human is the reasoner.** Doctors rejected AI reasoning in routine clinical settings — they want to reason themselves. They want the right context at the right time. The system's expertise is in assembly.

This means the higher-value, more tractable problem is not "how do we make LLMs reason better" but **"how do we make LLMs assemble context like an expert would."** Three of the five properties we define as expertise — domain compression, self-knowledge, and persistent knowledge — live in the assembly layer, not the reasoning layer.

## The Hypothesis

**Structured Latent Intelligence (SLI):** If symbolic domain constraints are embedded directly into a model's latent representation — factorizing the latent state into query understanding, domain topology, and relevance constraints — then:

1. Context assembly becomes domain-aware by construction (the model knows what to include and exclude)
2. Invalid assemblies are probabilistically suppressed (irrelevant context doesn't enter the reasoning space)
3. Smaller models achieve expert-level assembly (representational capacity focused on valid regions)
4. When reasoning IS needed, it operates over pre-constrained context, reducing hallucination

This applies to both assembly and reasoning, but the assembly application is more tractable and immediately testable.

The evidence for structure over scale is emerging: the ARC Prize 2025 CompressARC system achieved 20% on ARC-AGI-1 with 76K parameters using Minimum Description Length optimization. The 7M-parameter TRM achieved 45% through recursive latent refinement. Both outperform models 1,000-10,000x their size.

## Intellectual Heritage

SLI draws on Pāṇini's Aṣṭādhyāyī — the classical Sanskrit grammar that separates surface form (śabda) from deeper semantic roles (artha, kāraka) and enforces constraints prior to generation. Generation must be constrained at the level of structure, not corrected after the fact.

The connection to Chollet's program synthesis thesis is direct: neural components suggest candidates, symbolic components verify structure. SLI embeds the verification into the latent space, maintaining end-to-end differentiability.

## Preliminary Evidence

We have built and deployed systems that apply SLI principles externally across two domains:

**Saarthi Health** (production): WhatsApp-based clinical intelligence for doctors. Context assembly for patient records — specialty-aware selection, medication interaction flagging, chronological compression. Live with oncologists, nephrologists, gastroenterologists. Doctors use the assembled context; they provide the reasoning. No reasoning model needed.

**kairos-agent** (open source, github.com/SaarthiHQ/kairos-agent): Incident triage for engineering teams. Multi-source log assembly with dependency-aware selection, alert-type scoring, compression. Here, reasoning IS part of the product (Claude summarizes and triages). Key result: engineered context + small model (Haiku, $0.006) approaches raw context + large model (Opus, $0.14). 24x cost reduction.

**Cross-domain validation:** The same five-layer assembly pipeline (discover → fetch → compress → score → structure) works in both healthcare and incident management. The domain-specific parts (what to include, how to score, what constraints to enforce) are configuration, not code. This suggests the assembly problem is domain-agnostic at the framework level.

## The Research Program

**Phase 1 (6 months): Constraint projection for assembly**

A trainable layer (~1M parameters) that projects embeddings into a relevance-constrained subspace before attention:

```
e' = e + W_domain · d + W_relevance · r
```

Testable hypothesis: does latent-space relevance projection improve context assembly quality (measured by downstream task accuracy, coverage, and absence of irrelevant context) compared to prompt-engineered assembly?

**Phase 2 (12 months): Factorized latent representation**

Full SLI: h = [h_query, h_domain_topology, h_constraints]. The model natively represents what's relevant and what's not for a given query type in a given domain.

**Phase 3 (18-24 months): Reasoning under constraints + cross-domain transfer**

For domains where reasoning IS needed (incident management, ER triage): does constraining the latent space improve reasoning quality? Does a constraint projection trained on healthcare transfer to incident management?

**Optional: ARC-AGI adaptation.** Submit to ARC Prize 2026 as a proof of concept for the "structure beats scale" thesis.

## Why This Matters

- **Healthcare:** A system that structurally surfaces nephrotoxic medications for a nephrology referral — without being told to — is expert-level assembly. A system that structurally cannot recommend a contraindicated drug is expert-level reasoning. Both require constraint-aware representations.
- **Incident management:** A system that knows "payment-service depends on stripe-gateway, so check both" without configuration is expert-level assembly. A system that structurally cannot claim root cause without evidence is expert-level reasoning.
- **General AI safety:** If the assembly layer is constrained, the reasoning layer operates over safer input. Safety compounds across layers.
- **Efficiency:** Constrained representations need fewer parameters. Expert assembly with a small model beats generic assembly with a large model.

## What We Need

- **Compute:** GPU access for training constraint projection layers across two domains. Estimated: $30-50K over 12 months (A100 equivalent).
- **Collaboration:** Domain experts for invariant definition and evaluation (we have healthcare through Saarthi's clinical partnerships). Connection to AI safety and calibration researchers.
- **Publication support:** Positioning SLI within the abstention, calibration, and neuro-symbolic landscape for top-tier venues (NeurIPS, ICML, ICLR).

---

*Saarthi — saarthihealth.com | GitHub: SaarthiHQ | ramanan,rohan@saarthihq.com*
