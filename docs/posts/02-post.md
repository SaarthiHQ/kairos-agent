We've been building AI systems for doctors and on-call engineers. Two completely different domains. Same core problem.

The bottleneck is never the answer. It's assembling the right context to arrive at one.

A nephrologist getting a referral from a cardiologist doesn't need the patient's full history. They need creatinine trends, nephrotoxic medications, and the specific question being asked. An SRE getting paged at 3am doesn't need every log line from every service. They need the error logs from the affected service and its dependencies.

In both cases, the human is the expert reasoner. The system's job is expert-level assembly.

Here's what the research says about why this matters:

→ AI-generated code has 1.7x more issues than human code. Root cause: "input quality directly correlates with output reliability" (CodeRabbit, 2026)
→ More context often means worse model performance — drops below no-context baseline with 20+ documents (Liu et al., Stanford)
→ Reasoning-trained models are 24% worse at saying "I don't know" (AbstentionBench, 2025). Making models smarter makes them worse at knowing their limits.
→ But: smaller models with better context match larger models on structured tasks (ACE, ICLR 2026). Structure beats scale.

This led us to a working definition of expertise that splits into two layers:

Assembly — knowing what to gather, for whom, when. 3 of 5 expert properties live here.
Reasoning — drawing conclusions from assembled context. Often done by the human, not the model.

The higher-value problem isn't "how do we make AI reason better." It's "how do we make AI assemble context like an expert would."

We're building this at Saarthi. More on what we've learned — link in comments.

#ContextEngineering #AI #ExpertSystems #IncidentResponse #HealthcareAI
