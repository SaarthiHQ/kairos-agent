# Grant One-Pager: Toward Expert AI Systems Through Structured Latent Intelligence

**Ramanan Sivasubramanian**
PhD Candidate, Computational Linguistics & Heritage Science, IIT Hyderabad
Co-Founder, Saarthi (saarthihealth.com)

---

## The Problem

Large Language Models generate confident output regardless of whether they have sufficient evidence. The softmax function forces a probability distribution on every prediction — there is no mechanism for "I don't know." In high-stakes domains, this produces outputs that are statistically plausible but potentially dangerous.

This is not a training problem. It is an architectural one.

Chollet (2019) argued that LLMs cannot reason — they memorize patterns and replay them. When the memorized program doesn't apply, they fail. The ARC-AGI benchmark confirms this: frontier models achieve only 24% on tasks humans find trivial. AbstentionBench (2025) reveals a deeper issue: **reasoning-trained models are 24% worse at abstaining** than their non-reasoning counterparts. Making models smarter makes them worse at knowing their limits.

Current mitigations (RLHF, prompt engineering, output filtering) operate outside the model's representational core. Safety is corrected after the fact, not enforced by construction. The model may internally represent and prefer unsafe states even when filtered at inference time.

## The Hypothesis

**Structured Latent Intelligence (SLI):** If symbolic domain constraints are embedded directly into a model's latent representation — factorizing the latent state into surface form, domain semantics, and invariant constraints — then:

1. Invalid outputs become probabilistically suppressed (and potentially structurally unreachable with sufficient constraint density)
2. Models require fewer parameters for equivalent domain accuracy (representational capacity focused on valid regions)
3. Calibration improves natively (the model's epistemic state is explicit, not entangled)

This is consistent with the emerging evidence that **structure beats scale**: the ARC Prize 2025 CompressARC system achieved 20% on ARC-AGI-1 with 76K parameters — no pretraining, using Minimum Description Length optimization. The 7M-parameter TRM achieved 45% through recursive latent refinement. Both outperform models 1,000-10,000x their size on novel reasoning tasks.

SLI applies this principle to domain expertise: constrained latent spaces that prevent invalid outputs rather than general reasoning over arbitrary tasks.

## Intellectual Heritage

SLI draws on Pāṇini's Aṣṭādhyāyī — the classical Sanskrit grammar that separates surface form (śabda) from deeper semantic roles (artha, kāraka) and enforces constraints prior to generation. The principle that generation must be constrained at the level of structure, not corrected after the fact, is 2,500 years old. Its application to neural language models is new.

The connection to Chollet's program synthesis thesis is direct: Chollet proposes hybrid architectures where neural components suggest candidates and symbolic components verify structure. SLI embeds the verification INTO the latent space, maintaining end-to-end differentiability while achieving structural enforcement.

## Preliminary Evidence

We have built and deployed a context engineering framework (kairos-agent, open source at github.com/SaarthiHQ/kairos-agent) that applies SLI principles externally — engineering the input context and constraining the output, rather than modifying the latent space:

**Domain compression:** Multi-source log assembly with dependency-aware selection and alert-type-specific scoring. 173 raw lines → 61 after compression (65% reduction) with zero signal loss.

**Quality assessment:** The system reports what data it lacks. When quality metadata is included in the prompt, the model's expressed confidence becomes meaningfully correlated with actual data availability.

**Model tier arbitrage:** On structured tasks, engineered context + a small model (Haiku, $0.006/triage) approaches the quality of raw context + a large model (Opus, $0.14/triage). 24x cost reduction. This is the external analogue of SLI's prediction that constrained representations need fewer parameters.

**Behavioral calibration alignment:** The Rewarding Doubt paper (December 2025) demonstrates that smaller models trained with calibration-aware RL surpass frontier models on uncertainty quantification. Calibration is a transferable meta-skill, decoupled from raw accuracy. SLI proposes making this structural rather than training-dependent.

These results demonstrate that constraining the information space the model reasons over significantly improves output quality. SLI proposes doing this at the representational level for stronger guarantees.

## The Research Program

**Phase 1 (6 months): Constraint projection layer**

A lightweight trainable layer (~1M parameters) between input encoding and transformer attention that projects embeddings into a constraint-aware subspace:

```
e' = e + W_domain · d + W_constraint · c
```

No base model modification. Testable hypothesis: does latent-space projection reduce hallucination compared to prompt-only constraints?

Domains: healthcare (clinical decision support) and incident management (SRE triage). Both have well-defined invariants, existing deployed systems, and evaluation data.

Evaluation: hallucination rate, calibration (Brier score, ECE), abstention accuracy on unanswerable questions, comparison against prompt-only baseline, semantic entropy, and behavioral calibration.

**Phase 2 (12 months): Factorized latent representation**

Full SLI implementation: h = [h_text, h_domain, h_constraints]. Constraints participate in attention and transformation. Training on the valid manifold. Evaluation against standard models + external constraints on domain-specific benchmarks.

**Phase 3 (18-24 months): Cross-domain validation and abstention**

Evaluate whether SLI-trained models exhibit native principled refusal (abstain when evidence is insufficient without explicit training to do so). Test on AbstentionBench-style tasks within domain contexts. Validate cross-domain transfer: does a constraint projection trained on healthcare transfer to incident management?

**Optional: ARC-AGI adaptation.** Adapt the constraint projection layer to the grid transformation domain (h = [h_visual, h_transformation, h_constraints]). Submit to ARC Prize 2026 as a proof of concept for the "structure beats scale" thesis.

## Why This Matters

- **Healthcare:** A model that structurally cannot recommend a contraindicated drug is categorically safer than one trained to avoid it.
- **Incident management:** A triage system that structurally cannot produce a root cause claim without cited evidence prevents misdiagnosis of production incidents.
- **General AI safety:** SLI offers a path to reliability by construction, not correction. The AbstentionBench finding that reasoning models are worse at abstention suggests external training approaches have hit a ceiling. Architectural change may be necessary.
- **Efficiency:** If SLI achieves comparable accuracy with smaller models (following the CompressARC precedent), it enables deployment in resource-constrained settings — edge devices, low-connectivity environments, cost-sensitive applications.

## What We Need

- **Compute:** GPU access for training constraint projection layers across two domains. Estimated: $30-50K over 12 months (A100 equivalent).
- **Collaboration:** Domain experts for invariant definition and evaluation (we have healthcare through Saarthi's clinical partnerships). Connection to AI safety and calibration researchers.
- **Publication support:** Positioning SLI within the abstention, calibration, and neuro-symbolic landscape for top-tier venues (NeurIPS, ICML, ICLR).

## About the Team

**Ramanan Sivasubramanian** — PhD candidate (IIT Hyderabad, Computational Linguistics & Heritage Science), MTech (IIT Hyderabad, Indic Language Processing), MTech (BITS Pilani, Computer Software Engineering). Former SRE at TikTok, Vortexa, WhatsApp, Amazon. Co-founder of Saarthi. The SLI concept emerged from the intersection of classical Indian grammatical theory, production AI system design, and the observation that domain expertise is a constraint problem, not a scale problem.

**Rohan Jahagirdar** — Co-founder, Saarthi. Operations, strategy, and domain partnerships.

---

*Saarthi — saarthihealth.com | GitHub: SaarthiHQ | ramanan93@gmail.com*
