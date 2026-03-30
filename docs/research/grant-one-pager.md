# Grant One-Pager: Toward Expert AI Systems Through Structured Latent Intelligence

**Ramanan Sivasubramanian**
PhD Candidate, Computational Linguistics & Heritage Science, IIT Hyderabad
Co-Founder, Saarthi (saarthihealth.com)

---

## The Problem

Large Language Models generate confident, fluent output regardless of whether they have sufficient evidence. The softmax function forces a probability distribution on every prediction — there is no mechanism for "I don't know." In high-stakes domains like healthcare, incident management, and legal reasoning, this architectural limitation produces outputs that are statistically plausible but potentially dangerous.

Current mitigations (RLHF, prompt engineering, output filtering) operate outside the model's representational core. The model may internally represent and prefer unsafe states even when those states are filtered at inference time. Safety is corrected after the fact, not enforced by construction.

## The Hypothesis

**Structured Latent Intelligence (SLI):** If symbolic domain constraints are embedded directly into a model's latent representation — factorizing the latent state into surface form, domain semantics, and invariant constraints — then invalid outputs become structurally unreachable, not merely probabilistically unlikely.

This produces models that are smaller (representational capacity focused on valid regions), safer (constraint violations are unrepresentable), and more sample-efficient (invariants need not be learned from data).

## Preliminary Evidence

We have built and deployed a context engineering framework (kairos-agent, open source) that applies SLI principles externally — engineering the input context rather than the latent space:

- **Domain compression:** Multi-source log assembly with dependency-aware selection and alert-type-specific scoring. 173 raw lines → 61 after compression (65% reduction) with zero signal loss.
- **Quality assessment:** The system reports what data it lacks, enabling the LLM to express calibrated uncertainty. Claude's confidence ratings become meaningfully correlated with actual data availability.
- **Constraint enforcement:** Mandatory evidence citation, structural confidence fields, and domain invariant checking reduce uncalibrated claims.
- **Model tier arbitrage:** On structured tasks, engineered context + a small model (Haiku, $0.006/triage) matches raw context + a large model (Opus, $0.14/triage) in triage quality. 24x cost reduction, comparable accuracy.

These results demonstrate that constraining the information space the model reasons over significantly improves output quality. SLI proposes doing this at the representational level for stronger guarantees.

## The Research Program

**Phase 1 (6 months): Constraint projection layer**
A lightweight trainable layer (~1M parameters) between input encoding and transformer attention that projects embeddings into a constraint-aware subspace. No base model modification. Testable hypothesis: does latent-space projection reduce hallucination compared to prompt-only constraints?

Domains: healthcare (clinical decision support) and incident management (SRE triage). Both have well-defined invariants and existing deployed systems for evaluation.

**Phase 2 (12 months): Factorized latent representation**
Full SLI implementation: h = [h_text, h_domain, h_constraints]. Constraints participate in attention and transformation. Training on the valid manifold only. Evaluation against standard models on domain-specific benchmarks.

**Phase 3 (18-24 months): Principled refusal and epistemic calibration**
Extending SLI with evidential deep learning (Dirichlet output distributions) to enable native "I don't know." Evaluating calibration: when the model says 90% confident, is it right 90% of the time?

## Why This Matters

- **Healthcare:** A model that refuses to speculate without sufficient evidence is categorically safer than one that produces plausible-sounding but unsupported recommendations.
- **Incident management:** A triage system that says "I need deploy data before I can determine root cause" prevents misdiagnosis of production incidents.
- **General AI safety:** SLI offers a principled path to models that are reliable by construction, not by correction.

## The Intellectual Heritage

SLI draws on the architectural insight of Pāṇini's Aṣṭādhyāyī — the classical Sanskrit grammar that separates surface form (śabda) from deeper semantic roles (artha, kāraka) and enforces constraints prior to generation. The principle that generation must be constrained at the level of structure, not corrected after the fact, is ancient. Its application to neural language models is new.

## What We Need

- **Funding:** Compute for training constraint projection layers across two domains (healthcare + incident management). Estimated: GPU access equivalent to $30-50K over 12 months.
- **Collaboration:** Access to medical domain experts for invariant definition and evaluation. Connection to AI safety researchers working on calibration and epistemic uncertainty.
- **Publication support:** Guidance on positioning SLI within the broader AI safety and neuro-symbolic landscape for top-tier venues.

## About the Team

**Ramanan Sivasubramanian** — PhD (IIT Hyderabad, Computational Linguistics), MTech (IIT Hyderabad, Indic Language Processing), MTech (BITS Pilani, Computer Software Engineering). Former SRE at TikTok, Vortexa, WhatsApp, Amazon. Co-founder of Saarthi, building context-engineered AI for healthcare and incident management. The SLI concept emerged from the intersection of classical Indian grammatical theory and production AI system design.

**Rohan Jahagirdar** — Co-founder, Saarthi. Operations, strategy, and domain partnerships.

---

*Saarthi — saarthihealth.com | GitHub: SaarthiHQ | ramanan93@gmail.com*
