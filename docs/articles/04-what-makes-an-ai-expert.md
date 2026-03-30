# What Makes an AI Expert? (And Why Current Models Aren't One)

There's a word we keep reaching for in AI: "expert." Expert systems. Expert-level performance. Expert reasoning. We use it loosely — usually meaning "scores well on a benchmark" or "passes a professional exam."

But ask anyone who's worked with a real domain expert — a senior oncologist, a veteran SRE, a seasoned trial lawyer — and they'll tell you: expertise isn't about knowing the right answer. It's about knowing when you don't have enough to answer at all.

That distinction matters. And it's exactly where current AI models fall short.

## The Five Properties of Expertise

After spending the last several months building AI systems for healthcare and incident management at Saarthi, I've come to a working definition of what makes a system behave like an expert. It has five properties.

### 1. Calibrated self-knowledge

An expert knows the boundary of their competence — not vaguely, but precisely.

A junior doctor says: "I think this could be serious."
An expert says: "I can't differentiate between X and Y without a creatinine level. Order that first. Until then, I'm not going to speculate."

A junior SRE says: "Looks like a database issue."
An expert says: "The logs show timeouts but the metrics show normal latency. That means the instrumentation is broken, not the database. I need to see the metrics pipeline before I can say more."

Self-knowledge has two sides: knowing what you have, and knowing what you lack. The second is harder and more valuable. A system that confidently reports findings from available data is useful. A system that also tells you "I cannot rule out X because I don't have access to Y" is trustworthy.

### 2. Domain compression

An expert doesn't look at more data. They look at the right data. Faced with 5,000 log lines, their attention goes to the 5 that matter. Reading a 50-page patient history, they extract the 3 findings relevant to the current complaint.

Information theory has a term for this: low entropy prediction within a domain. An expert has learned which distinctions matter and which don't. They don't treat all evidence equally — they know that a creatinine of 2.8 in a diabetic patient is urgent, while the same value post-surgery might be expected.

This is actually the property that current AI systems can approximate most effectively — with the right engineering. If you give a model only the evidence that matters, scored by relevance, it reasons well over it. The challenge is knowing what matters before the model sees it.

### 3. Judgment under ambiguity

When evidence contradicts itself, an expert doesn't average the signals. They reason about *why* the signals contradict.

"The logs show no errors, but the error rate metric is 50%. A novice says 'conflicting data.' An expert recognizes: the logging system is broken, not the service. Fix the observability before triaging the incident."

"The patient's symptoms suggest diagnosis A, but their age and history make B far more likely. A novice picks A. An expert orders a specific test that would distinguish A from B before committing to either."

This is meta-reasoning — thinking about the structure of the evidence, not just its content. Why am I seeing what I'm seeing? What would I expect to see if hypothesis A were true versus hypothesis B? Which single data point, if different, would change my conclusion?

Current AI models can do this when explicitly prompted. But they don't do it natively. Their default is to pattern-match to the most statistically likely conclusion from training data — not to reason from first principles about the specific evidence in front of them.

### 4. Principled refusal

This is the defining property. An expert is defined as much by what they refuse to do as by what they do.

A good doctor doesn't guess when the data is insufficient. They say: "I need an MRI before I can tell you what this is. Acting without it risks misdiagnosis."

A good SRE doesn't deploy a speculative fix at 3am. They say: "I don't have enough information to act safely. Let me gather more data before we make this worse."

This isn't caution. It's competence. The willingness to not-act when the cost of being wrong exceeds the cost of waiting is the clearest signal of expertise. Novices act to demonstrate competence. Experts refuse to demonstrate it.

Current language models cannot do this. The architecture forces output. The training objective rewards fluency. There is no native mechanism for "I have insufficient basis for this prediction." The model generates a confident, plausible-sounding answer regardless of whether it has evidence to support it — because that's what it's mathematically optimized to do.

CodeRabbit's recent study on AI-generated code (2026) quantified this: AI-authored work contained 1.7x more issues than human work. Not because the model was less capable, but because it "infers patterns statistically, not semantically" — it doesn't know when to stop.

### 5. Knowledge that persists and compounds

An expert doesn't start from zero each time. They carry structured knowledge across interactions:

- Episodic: "Last time I saw this pattern in this patient, it was X"
- Semantic: "This class of drugs always interacts with that class"
- Procedural: "When I see A and B together, I check C before drawing conclusions"

An expert oncologist on their patient's 5th visit doesn't re-read the full history. They know the context. "Last time we adjusted the dosing. Let me check if it worked."

Current AI models have parametric knowledge (from training) and in-context knowledge (from the current prompt). But they have no persistent structured knowledge that compounds over interactions. Every conversation starts from zero. Every triage starts without memory of the last.

## State or Process?

Is an expert a fixed configuration of knowledge, or an evolving process that improves through experience?

The answer is both, in sequence.

An expert starts as a state: a configuration of rules, relationships, and procedures learned through training. A medical student memorizes drug interactions. A junior SRE learns which dashboards to check first. This is competence — the ability to follow the right process given the right inputs.

An expert becomes a process: a system that refines itself through experience. The oncologist who has seen 1,000 patients with this condition develops an intuition — a fast pattern-matching ability that fires before conscious reasoning. The veteran SRE hears "latency spike" and their mind immediately goes to yesterday's deploy, not because a rule told them to, but because accumulated experience has wired that connection.

The Dreyfus model of skill acquisition captures this progression: novice → advanced beginner → competent → proficient → expert. Current AI systems are somewhere between advanced beginner and competent. They recognize patterns and follow complex instructions. But they lack the "something doesn't fit" sense of the proficient practitioner — the ability to notice that the data is telling a different story than the one the model is constructing.

## The Mathematical Root

Why can't current models reach full expertise? The answer is architectural, not just about training data or prompting.

The transformer architecture represents all knowledge — linguistic patterns, factual information, domain constraints, ethical boundaries — in a single, undifferentiated latent space. Everything is entangled. The model cannot distinguish between a linguistically valid continuation ("the patient should take...") and a medically valid one.

More fundamentally, the softmax function that governs output forces a probability distribution that sums to 1. The model must always commit probability mass to some prediction. There is no mathematical representation of "I have no basis for this prediction." Even maximum uncertainty (a flat distribution) produces tokens — just random ones rather than confident ones.

This means hallucination is not a failure mode. It's a feature of the architecture. The model will always produce fluent output, regardless of whether it has evidence for that output. And it will produce that output with no structural indication of how grounded it is.

## What This Means for Building AI Systems

If we accept that expertise requires principled refusal, calibrated self-knowledge, and structured persistence — and that current architectures lack these natively — then the question becomes: how close can we get with engineering?

The answer, based on our experience: surprisingly close on structured tasks. With disciplined context engineering — careful selection of what the model sees, compression of noise, domain-aware scoring, quality assessment, and structured prompting — a mid-tier model can produce expert-like output for well-defined tasks like incident triage or clinical summary.

But "surprisingly close" is not "there." The gap manifests in exactly the ways the five properties predict:
- The model gives a confident answer when it should say "insufficient data"
- It pattern-matches to the most common cause when the evidence points to an uncommon one
- It can't tell you what it would need in order to change its conclusion
- It starts from zero every time, with no memory of what worked before

The 85-90% is commercially valuable. The remaining 10-15% is the research frontier. And the distinction matters most in exactly the domains where AI is needed most — where a wrong answer isn't just unhelpful, it's harmful.

## Where This Goes

The path to expert AI systems isn't bigger models or better prompts. It's architectural change — models that natively represent what they know and what they don't, that carry structured knowledge across interactions, and that can refuse to act when the cost of being wrong exceeds the cost of waiting.

The classical Indian grammarian Pāṇini understood this 2,500 years ago: his Aṣṭādhyāyī separates surface form from deeper structure and enforces constraints prior to generation — not after. The principle that generation must be constrained at the level of structure, not corrected after the fact, is ancient. Its application to neural language models is the work ahead.

At Saarthi, we're approaching this from both ends — engineering the context that feeds current models to approximate expertise today, while researching the architectural changes that would make expertise native. The domain changes. The definition of expertise doesn't.

---

*This is the third in a series on context engineering and expert AI systems. Previously: [The On-Call Engineer's New Partner](#) and [Context Engineering Is Not Context Stuffing](#). Reach out on [LinkedIn](https://www.linkedin.com/in/ramanansiva).*
