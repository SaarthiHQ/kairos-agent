# Saarthi's Trajectory Toward the Expert Model

**Internal document — Ramanan Sivasubramanian, March 30, 2026**

---

## Where We Are

Saarthi has two live products and one research thesis, all converging on the same goal: AI systems that behave like domain experts.

**Saarthi Health** — WhatsApp-based clinical intelligence for doctors. Takes patient documents, extracts structured clinical data, answers directed questions. Live in production with oncologists, nephrologists, gastroenterologists, and general medicine. Revenue-generating.

**kairos-agent** — Open-source incident context assembler. Multi-source log ingestion, dependency-aware context assembly, alert-type scoring, compression, quality assessment. Live against real New Relic data. Validated with benchmark: engineered context + small model matches raw + large model at 24x lower cost.

**SLI research** — Structured Latent Intelligence. The architectural thesis: embed symbolic constraints into the latent space so invalid outputs are structurally unreachable. Written up January 2026. Not yet implemented.

These three are not separate projects. They're the same project at different layers.

## The Unified Vision

Saarthi builds expert AI systems. The expert model has five properties: calibrated self-knowledge, domain compression, judgment under ambiguity, principled refusal, and persistent compounding knowledge. Current LLMs have none of these natively.

Our approach attacks this gap at three layers simultaneously:

```
Layer 1: Context Engineering (external, works today)
    → Shapes what the model sees
    → 85-90% of expert behavior on structured tasks
    → The open-source engine + SaaS product

Layer 2: Constraint Enforcement (external, buildable in months)
    → Shapes what the model can output
    → Mandatory citations, confidence fields, negation rules
    → Gets to 92-95% of expert behavior
    → SaaS differentiator

Layer 3: Structured Latent Intelligence (architectural, research)
    → Shapes how the model represents knowledge
    → Invalid outputs structurally unreachable
    → 99%+ of expert behavior
    → The long-term moat, the PhD, the grant
```

Every layer builds on and validates the one below it. Context engineering proves that constraining the information space works. The constraint layer proves that structural enforcement works. SLI makes it native to the architecture.

## Execution Plan

### Phase 0: Foundation (done — March 2026)

**What we built:**
- kairos v0.3: multi-source connectors (NR, Datadog, Loki, HTTP), service catalog with dependency graph, alert-type inference and scoring, Level 1 compression, token-aware scoping, triple prompt repetition, quality assessment
- Live end-to-end: NR staging → kairos → Claude → Slack #prod-alerts
- Benchmark harness proving context engineering + small model thesis
- Saarthi Health in production with real patients and doctors

**What we proved:**
- External context engineering measurably improves output quality
- Smaller models with engineered context match larger models with raw context
- Quality assessment enables calibrated confidence (property 1)
- Domain compression is achievable externally (property 2)

**What we didn't build yet:**
- Properties 3-5 (ambiguity, refusal, persistence)

### Phase 1: Constraint Layer (April-May 2026)

**Goal:** Properties 3 and 4 — judgment under ambiguity and principled refusal — through external constraint enforcement.

**For kairos (incident management):**
- Mandatory evidence citation: every root cause claim must reference a specific log line
- Contradiction detection: force the model to list signal conflicts before summarizing
- Structural confidence: HIGH/MEDIUM/LOW/CANNOT_DETERMINE as required fields, not suggestions
- Post-generation validation: verify cited log lines exist in the input; override confidence when quality assessment contradicts
- Domain negation rules: "never claim service is healthy during active alert," "never suggest root cause without evidence"

**For Saarthi Health (clinical):**
- Mandatory evidence citation: every clinical finding must reference a specific record
- Drug interaction checking: if two medications in the patient's list interact, the output MUST mention it regardless of the question asked
- Contraindication enforcement: never suggest a treatment that contradicts a known allergy or condition
- Uncertainty enforcement: if critical lab data is missing (e.g., creatinine for a renal question), refuse to speculate
- Recency enforcement: never base a current recommendation on data older than X days without flagging it

**Deliverables:**
- Constraint engine module in the framework (reusable across domains)
- Domain-specific constraint configs for incident management and healthcare
- Before/after benchmark: constraint-enforced outputs vs unconstrained
- Reduction in hallucination rate (measurable via citation verification)

**This is the SaaS differentiator.** The open-source engine does context engineering. The managed service adds constraint enforcement. The constraints encode domain expertise that took real-world experience to define.

### Phase 2: Memory and Learning (June-August 2026)

**Goal:** Property 5 — persistent compounding knowledge — through external memory systems.

**Incident memory for kairos:**
- After each triage, store: incident ID, service, alert type, root cause (if known), which log patterns were relevant, was the triage useful (feedback)
- Before each new triage, retrieve: "last 5 incidents for this service" and "services with similar alert patterns"
- Scoring adaptation: if the last 3 payment-service incidents were Stripe timeouts, boost Stripe-related patterns automatically
- This is the ACE Reflector → Curator loop applied to our domain

**Patient memory for Saarthi Health:**
- Persist structured summaries per patient across conversations
- Track: what questions were asked, what the doctor corrected, what findings were important
- On the next consultation, preload relevant history without re-reading the full record
- Learn which clinical patterns matter for this specific patient

**Deliverables:**
- Memory storage layer (could use Mem0's approach or build simpler)
- Retrieval integration in the context engine (memory becomes a source)
- Before/after: does memory-augmented triage improve accuracy on repeat incidents?
- Before/after: does patient memory reduce redundant questions in clinical sessions?

### Phase 3: Configurable Domain Onboarding (September-October 2026)

**Goal:** The equalizer — make domain onboarding a configuration exercise, not a code exercise.

**The onboarding flow:**
1. Choose domain template (incident management / healthcare / custom)
2. Connect sources (OAuth for NR/Datadog, API keys, database connections)
3. Auto-discover entities (services from NR, patients from DB)
4. Configure scoring weights (what "important" means in this domain)
5. Define constraints (domain invariants, negation rules)
6. Run calibration (3-5 sample inputs, rate outputs, framework adjusts)
7. Go live

**The free tier:**
- Default template + 1 source + Haiku model + basic constraints
- Enough to validate and get hooked

**The pro tier:**
- Full equalizer + multiple sources + model routing (Haiku → Sonnet) + custom constraints + memory

**Enterprise:**
- Custom domain adapters + Level 3 compression + SLI constraint projection (when ready) + dedicated infrastructure

**Deliverables:**
- Web-based onboarding flow (the SaaS frontend)
- Domain template system (pre-built configs for incident management + healthcare)
- Equalizer API (programmatic access to all dials)
- Billing and usage tracking

### Phase 4: Constraint Projection Layer — SLI Prototype (November 2026 - March 2027)

**Goal:** Bridge from external constraints to latent-space constraints. Test the SLI hypothesis with a lightweight implementation.

**The experiment:**
- Add a trainable projection layer (~1M parameters) between input encoding and transformer attention
- The layer projects embeddings into a constraint-aware subspace
- Train on domain-specific data with a loss function that penalizes constraint violations
- No base model modification — this is an adapter, not a new model

**Evaluation:**
- Does the constraint projection layer reduce hallucination vs prompt-only constraints?
- Does it improve calibration (when it says 90% confident, is it right 90%)?
- Does it enable native "I don't know" (outputs structurally blocked when evidence is insufficient)?
- Can it be trained on one domain and transferred to another?

**If the results are positive:**
- Publishable result (constraint projection improves domain-specific reliability)
- Product differentiator (the constraint projection is Saarthi's IP, runs in the managed service)
- Evidence for the full SLI architectural thesis → stronger grant application

**If the results are negative:**
- We learn that external constraints are sufficient for practical purposes
- The SaaS product (context engineering + constraint enforcement + memory) is still commercially valuable
- The research pivots to understanding why latent-space constraints don't add value

### Phase 5: Full SLI (2027+)

**Goal:** Implement the factorized latent representation: h = [h_text, h_domain, h_constraints].

This is the PhD-level work. It requires:
- Training a model from scratch (or heavily fine-tuning) with the factorized architecture
- Defining constraint representations that are learnable and differentiable
- Evaluating across multiple domains (healthcare, incident management, and a third domain to test generalization)
- Comparing against standard models + external constraints on calibration, safety, and refusal

**Success criteria:**
- SLI model with 1B parameters matches standard 7B+ model on domain accuracy
- SLI model has measurably better calibration (Brier score, ECE)
- SLI model refuses to answer in >90% of cases where evidence is genuinely insufficient
- The same SLI architecture works across healthcare and incident management with different constraint configurations

## Revenue Trajectory

| Phase | Timeline | Revenue source | ARR target |
|---|---|---|---|
| 0 (Foundation) | Mar 2026 | Saarthi Health (existing) | Existing |
| 1 (Constraints) | Apr-May | Pro tier upsell on constraint enforcement | First SaaS revenue |
| 2 (Memory) | Jun-Aug | Retained customers, reduced churn | Growing |
| 3 (Onboarding) | Sep-Oct | Self-serve signups, free → pro conversion | Scaling |
| 4 (SLI prototype) | Nov-Mar 2027 | Enterprise contracts (reliability guarantee) | Significant |
| 5 (Full SLI) | 2027+ | Platform + research licensing | Long-term moat |

## Team Needs

| Phase | Need |
|---|---|
| 1-2 | Forward-deployed engineer / solutions architect (1 person) — deploys the framework for customers, handles operational work |
| 2-3 | Frontend engineer (1 person) — builds the SaaS onboarding and equalizer UI |
| 4-5 | ML researcher (1 person, could be PhD intern) — implements constraint projection and SLI experiments |
| All | Ramanan: 80% research + framework, 20% operations |
| All | Rohan: business, partnerships, customer conversations |

## The Bet

The bet is that **expertise is not a property of model size — it's a property of constraint enforcement and domain compression.** A 1B parameter model with the right constraints and the right context can outperform a 100B parameter model without them on domain-specific tasks.

If this is true:
- Smaller models = lower cost = viable free tier = faster adoption
- Constraint enforcement = reliability = enterprise trust = premium pricing
- Domain compression = transferable framework = multiple verticals from one engine
- SLI = architectural moat = defensible long-term position

The first three are testable now. The fourth is the research program. We're building the evidence for each one in sequence.

---

*This document reflects the state of thinking as of March 30, 2026. It should be updated monthly as we learn from building, deploying, and observing what works.*
