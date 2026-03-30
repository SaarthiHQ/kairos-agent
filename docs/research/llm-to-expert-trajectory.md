# From LLM to Expert: The Trajectory and What's Being Tried

**Ramanan Sivasubramanian — March 30, 2026**
**Internal research survey**

---

## The Question Through the LLM Lens

An LLM is a next-token predictor trained on internet-scale text. An expert is a system with calibrated self-knowledge, domain compression, judgment under ambiguity, principled refusal, and persistent knowledge. How do you get from one to the other?

Chollet (2019) argued the gap is fundamental: LLMs memorize patterns and replay them, but cannot reason about novel situations. The ARC-AGI benchmark confirms this — frontier models achieve 24% on tasks humans find easy. More troublingly, AbstentionBench (2025) shows that making models better at reasoning makes them 24% worse at knowing when to stop. The gap isn't closing with scale. It may be widening.

There are seven active approaches in the industry and academia. Each addresses a different part of the gap. None of them, alone, closes it.

---

## Approach 1: Fine-Tuning (Change How the Model Behaves)

**What it does:** Adjusts model weights on domain-specific data so the model's default behavior matches the domain.

**Methods:** LoRA, QLoRA, DPO (Direct Preference Optimization), RLHF, instruction tuning.

**What it addresses:**
- Tone and format consistency ("always respond as a clinical brief")
- Domain-specific vocabulary and patterns
- Behavioral alignment (prefer cautious responses over confident ones)

**What it doesn't address:**
- The model still hallucinates — fine-tuning reduces frequency but doesn't eliminate it
- No epistemic awareness — the model doesn't know what it knows vs. what it learned to say
- No principled refusal — fine-tuned models can be trained to say "I'm not sure" but this is mimicry, not genuine uncertainty estimation
- Knowledge is frozen at training time

**The 2025-2026 consensus:** Fine-tune for behavior, not knowledge. Use it to make the model follow the right format, tone, and safety patterns. Don't rely on it for factual accuracy.

**Expert property coverage:** Partial on domain compression (the model learns what patterns matter). None on self-knowledge, refusal, or persistence.

---

## Approach 2: RAG (Change What the Model Sees)

**What it does:** Retrieves relevant documents at inference time and injects them into the context.

**Methods:** Vector similarity search, BM25, hybrid retrieval, GraphRAG, re-ranking.

**What it addresses:**
- Current, up-to-date knowledge without retraining
- Citable sources — the model can point to where its answer came from
- Reduced hallucination (when the answer IS in the retrieved context)

**What it doesn't address:**
- Retrieval quality ceiling — if the retriever doesn't find the right documents, the model hallucinates anyway
- No scoring by relevance — RAG retrieves "semantically similar," not "important for this specific question"
- No compression — retrieved documents are often verbose and noisy
- No quality assessment — the model doesn't know if the retrieval was complete or missed critical sources

**Expert property coverage:** Partial on domain compression (retrieval narrows the scope). None on self-knowledge, ambiguity judgment, or refusal.

**Our position:** Context engineering is what RAG becomes when you take it seriously. Selection, compression, scoring, quality assessment — these are the layers that RAG misses. RAG gives you the documents. Context engineering gives you the right 50 lines from those documents, scored and structured for the specific question being asked.

---

## Approach 3: Context Engineering (Change What the Model Sees, Systematically)

**What it does:** Engineers the entire context window — not just retrieved documents, but their selection, compression, scoring, ordering, and quality metadata.

**Methods:** Multi-source fetch, domain-aware scoring, deduplication/compression, token budgeting, prompt structure optimization (prompt repetition), quality assessment.

**What it addresses:**
- Domain compression — the 5 signals that matter from 5,000 data points
- Partial self-knowledge — quality assessment tells the model what it's missing
- Partial refusal — when prompted with gaps, models express appropriate uncertainty
- Model tier arbitrage — engineered context + small model matches raw context + large model

**What it doesn't address:**
- Refusal is behavioral, not structural — the model CAN still hallucinate if it chooses to
- Ambiguity judgment is prompt-dependent — the model doesn't natively reason about contradictions
- No persistent memory across sessions

**Expert property coverage:** Strong on compression. Moderate on self-knowledge and refusal. Weak on ambiguity and persistence.

**This is where Saarthi is today.** kairos is a context engineering system. It covers approximately 85-90% of expert behavior on structured tasks.

---

## Approach 4: Uncertainty Quantification (Measure How Much the Model Knows)

**What it does:** Estimates how confident the model actually is in its output, independent of how confident it *sounds*.

**Methods:**

**Semantic entropy** (Farquhar et al., Nature 2024): Generate multiple responses, cluster by meaning, measure entropy across clusters. High entropy = model is uncertain about the meaning, not just the wording. Validated as a statistically significant hallucination detection signal.

*Limitation:* 5-10x computational cost (multiple generations). Semantic Entropy Probes (SEPs) reduce this by approximating from hidden states of a single generation.

*Critical limitation:* Fails on "high-confidence hallucinations" — when the model consistently produces the same wrong answer with high certainty. The model doesn't know it's wrong, so entropy is low.

**Evidential deep learning** (Sensoy et al., NeurIPS 2018; F-EDL 2025): Instead of predicting a class, predict the parameters of a Dirichlet distribution over classes. The concentration parameter represents evidence strength. Low evidence = "I don't know" is a first-class output.

*Limitation:* Implemented for classification, not yet scaled to generative models. The gap between classifying "this is uncertain" and generating "I don't know how to answer this" is non-trivial.

**Behavioral calibration / Rewarding Doubt** (December 2025): Train the model via RL to admit uncertainty when not confident. Custom reward functions based on proper scoring rules. Key finding: **smaller models trained with calibration-aware RL surpass frontier models on uncertainty quantification.** Calibration is a transferable meta-skill, decoupled from raw predictive accuracy.

**Expert property coverage:** Directly addresses self-knowledge and calibration. Does not address compression, ambiguity judgment, or persistence.

**Critical insight for Saarthi:** The Rewarding Doubt result validates our thesis — smaller models with better calibration can outperform larger models. If we combine context engineering (our external compression) with behavioral calibration (internal uncertainty awareness), the combination should be powerful.

---

## Approach 5: Abstention Training (Teach the Model to Refuse)

**What it does:** Trains or prompts models to abstain from answering when they shouldn't.

**Key research:**

**AbstentionBench** (June 2025): Large-scale benchmark across 20 datasets including unanswerable questions, false premises, underspecified questions, subjective topics, and outdated information.

Key findings:
- **Abstention is an unsolved problem.** No model reliably abstains.
- **Scaling doesn't help.** Larger models are not better at abstaining.
- **Reasoning fine-tuning HURTS abstention.** Reasoning models like DeepSeek R1 show a **24% drop** in abstention compared to their non-reasoning counterparts. Teaching models to reason harder makes them LESS likely to say "I don't know."

This is a critical finding for our thesis: **the path to expert behavior is not "make the model smarter." Smarter models are worse at knowing their limits.**

**Know Your Limits** (TACL 2025): Comprehensive survey organizing abstention from three perspectives — the query (is this answerable?), the model (can I answer this?), and values (should I answer this?).

**Expert property coverage:** Directly addresses principled refusal. But the AbstentionBench result shows that current approaches don't work reliably. This is the hardest unsolved problem.

**Critical insight for Saarthi:** If training the model to abstain doesn't work (AbstentionBench), and making it smarter makes it worse (reasoning models), then external constraint enforcement is not just a practical shortcut — it may be the ONLY reliable approach with current architectures. This validates our constraint layer strategy.

---

## Approach 6: Neuro-Symbolic AI (Add Structure to the Model)

**What it does:** Combines neural pattern recognition with symbolic reasoning and constraint enforcement.

**Methods:**
- Neural perception → symbolic representation → symbolic reasoning → constrained output
- Knowledge graphs as structured memory
- Formal verification (TLA+, deontic logic) for safety guarantees
- Explicit constraint engines alongside neural generation

**2026 state:** No longer research-only. Neuro-symbolic is becoming "the backbone of trustworthy AI systems" for regulated industries. Dedicated hardware accelerators exist. The approach delivers explicit reasoning traces, human-auditable outputs, and formal safety guarantees.

**What it addresses:**
- Constraint enforcement by construction (not correction)
- Explainable reasoning (symbolic traces)
- Domain invariant preservation

**What it doesn't address:**
- Brittle interfaces between neural and symbolic components
- Scaling challenges — symbolic reasoning is computationally expensive
- The neural component can still hallucinate; the symbolic component catches it, but this is still post-hoc

**Expert property coverage:** Strong on refusal (symbolic constraints block invalid outputs) and ambiguity (symbolic reasoning can identify contradictions). Weak on compression and persistence (these remain neural problems).

**Saarthi's position (SLI):** Our Structured Latent Intelligence proposal goes further than standard neuro-symbolic — instead of running symbolic reasoning alongside the neural model, we propose embedding symbolic constraints INTO the latent space. This avoids the brittle interface problem and maintains end-to-end differentiability. The constraint projection layer (Phase 4 in our trajectory) is the first step toward testing this.

---

## Approach 7: Program Synthesis / Chollet's Thesis (Build New Solutions, Don't Replay Memorized Ones)

**What it does:** Instead of pattern-matching from training data, generate a *program* (a transformation rule) that solves a new problem from a few examples. Verify the program symbolically. Iterate.

**Key figure:** François Chollet (creator of Keras, founder of Ndea). His "On the Measure of Intelligence" (2019) redefines intelligence as skill-acquisition efficiency — how quickly you learn from limited examples, not how well you perform after seeing billions.

**Architecture (Ndea):** Hybrid neural + discrete program search. The neural component suggests promising candidates. The symbolic component assembles them into programs and verifies them. The key challenge is combinatorial explosion, managed by neural intuition over program space.

**ARC Prize 2025 results that validate this:**
- CompressARC: **76K parameters**, no pretraining, 20% on ARC-AGI-1 using Minimum Description Length optimization
- TRM: **7M parameters**, recursive latent refinement, 45% on ARC-AGI-1
- Both outperform models 1,000-10,000x larger

**What it addresses:**
- Novel reasoning from few examples (genuine intelligence, not interpolation)
- Smaller models beating larger ones through structure
- Verifiable outputs (programs can be checked symbolically)

**What it doesn't address:**
- Domain expertise (ARC tests general reasoning, not domain knowledge)
- Principled refusal (program synthesis either finds a program or doesn't — binary, not calibrated)
- Persistent knowledge across problems

**Expert property coverage:** Strong on ambiguity (generates and verifies multiple hypotheses). Moderate on compression (MDL principle). Weak on self-knowledge, refusal, and persistence.

**Connection to SLI:** Chollet proposes neural + symbolic as separate components. SLI proposes embedding the symbolic into the neural's latent space. Same insight (structure beats scale), different mechanism. Chollet verifies externally; SLI constrains internally.

---

## The Landscape Map

| Approach | Compression | Self-knowledge | Ambiguity | Refusal | Persistence |
|---|---|---|---|---|---|
| Fine-tuning | Partial | None | None | Mimicry only | Frozen |
| RAG | Partial | None | None | None | None |
| Context engineering | **Strong** | **Moderate** | Weak | Moderate | None |
| Uncertainty quantification | None | **Strong** | None | Moderate | None |
| Abstention training | None | Moderate | None | **Unsolved** | None |
| Neuro-symbolic | Weak | Moderate | **Moderate** | **Strong** | Weak |
| Program synthesis (Chollet) | Moderate | Weak | **Strong** | Weak | Weak |

No single approach covers all five expert properties. The trajectory to expertise requires combining them.

---

## The Trajectory: How to Make an LLM an Expert

Based on the research landscape, the path from LLM to expert has four stages:

### Stage 1: External Intelligence (where we are)

**Combine context engineering + constraints.**
- Context engineering provides compression, partial self-knowledge, and partial refusal
- Structural constraints (mandatory citations, contradiction detection, negation rules) enforce refusal and ambiguity judgment externally
- Works with any model, no training required
- Gets 85-95% of expert behavior on structured tasks

**This is commercially viable today.** It's what kairos does for incident management and what Saarthi Health does for clinical intelligence.

### Stage 2: Calibrated Intelligence (next 6-12 months)

**Add behavioral calibration + memory.**
- Fine-tune (or use RL) to improve the model's internal uncertainty calibration (Rewarding Doubt approach)
- Add persistent memory across sessions (incident history, patient history)
- The model's expressed confidence becomes meaningfully correlated with actual accuracy
- Memory enables pattern accumulation and scoring adaptation

**Key research to watch:** Behavioral calibration via proper scoring rules. The finding that smaller models trained for calibration outperform larger models on UQ is directly actionable.

### Stage 3: Structurally Constrained Intelligence (12-24 months)

**Embed constraints into the model's computation.**
- Constraint projection layer: trainable adapter that projects embeddings into a constraint-aware subspace before attention
- Domain invariants participate in the forward pass, not just in post-processing
- Invalid outputs become harder to generate (not impossible, but probabilistically suppressed)
- This is SLI Phase 1 — testable with a small trainable layer on top of existing models

**Key research to watch:** Evidential deep learning scaling from classification to generation. Neuro-symbolic hardware accelerators enabling real-time constraint checking.

### Stage 4: Architecturally Expert Intelligence (2+ years)

**Factorized latent representation: h = [h_text, h_domain, h_constraints].**
- Constraints are first-class citizens in the model's representation
- Epistemic state is tracked natively (the model knows what it knows)
- Abstention is a structural capability, not a trained behavior
- Smaller models with focused capacity outperform larger unconstrained models

**This is the SLI thesis.** It requires training from scratch or very deep architectural modification. It's the PhD-level work. But every stage before it builds evidence that constraining the model's representational space improves output quality — making the full thesis more credible.

---

## What No One Else Is Doing

Looking across the landscape, the gap that Saarthi uniquely fills:

1. **No one combines context engineering + constraints + domain specificity in a reusable framework.** LangChain does orchestration. LlamaIndex does retrieval. Mem0 does memory. Nobody does domain-aware scoring + compression + quality assessment + constraint enforcement as a unified pipeline.

2. **No one applies this across multiple high-stakes domains (healthcare + incident management) to extract common patterns.** Everyone is vertical. We're extracting the horizontal framework.

3. **No one has proposed embedding domain constraints into the latent space for generative models.** Evidential deep learning does it for classification. Neuro-symbolic does it with external symbolic components. SLI proposes doing it natively, in the latent space, end-to-end differentiable.

4. **The AbstentionBench finding — that reasoning models are WORSE at abstention — validates our architectural thesis.** If making models smarter makes them worse at knowing their limits, then the solution must be structural, not just scaling. That's SLI.

5. **The ARC Prize results show structure beats scale.** CompressARC (76K params) and TRM (7M params) outperform models 1000x larger through MDL optimization and recursive refinement. This is the same thesis as SLI: constrained representations need fewer parameters.

---

## Sources

- [Chollet: On the Measure of Intelligence](https://arxiv.org/abs/1911.01547) — 2019
- [ARC-AGI-2: A New Challenge for Frontier AI Reasoning](https://arxiv.org/abs/2505.11831) — May 2025
- [ARC Prize 2025 Results and Analysis](https://arcprize.org/blog/arc-prize-2025-results-analysis) — 2025
- [AbstentionBench: Reasoning LLMs Fail on Unanswerable Questions](https://arxiv.org/abs/2506.09038) — June 2025
- [Know Your Limits: A Survey of Abstention in LLMs](https://arxiv.org/abs/2407.18418) — TACL 2025
- [Rewarding Doubt: Behaviorally Calibrated RL for Hallucination](https://arxiv.org/abs/2512.19920) — December 2025
- [Semantic Entropy for Hallucination Detection](https://www.nature.com/articles/s41586-024-07421-0) — Nature 2024
- [Evidential Deep Learning to Quantify Classification Uncertainty](https://arxiv.org/abs/1806.01768) — NeurIPS 2018
- [Flexible Evidential Deep Learning](https://arxiv.org/abs/2510.18322) — October 2025
- [Semantic Entropy Probes](https://arxiv.org/abs/2406.15927) — 2024
- [Uncertainty Quantification for Hallucination Detection](https://arxiv.org/abs/2510.12040) — October 2025
- [Unlocking Generative AI through Neuro-Symbolic Architectures](https://arxiv.org/abs/2502.11269) — February 2025
- [Hallucination Detection and Mitigation Survey](https://arxiv.org/abs/2601.09929) — January 2026
- [ACE: Agentic Context Engineering](https://arxiv.org/abs/2510.04618) — ICLR 2026
- [RAG vs Fine-Tuning: Production Guide 2026](https://dev.to/umesh_malik/rag-vs-fine-tuning-for-llms-2026-what-actually-works-in-production-10if)
