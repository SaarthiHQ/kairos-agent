DRAFT — LinkedIn post introducing kairos-agent

---

Two posts ago: context engineering is reshaping SRE.
Last post: why it's engineering, not stuffing — the research behind it.

Today: we built the thing. And it's open source.

𝐤𝐚𝐢𝐫𝐨𝐬-𝐚𝐠𝐞𝐧𝐭 — an AI-powered incident context assembler.

Alert fires → agent pulls relevant logs → filters and ranks by severity → Claude summarizes → Slack delivers a triage brief.

30 seconds instead of 20 minutes.

What makes this context engineering, not just "LLM on logs":

• 𝐒𝐞𝐥𝐞𝐜𝐭𝐢𝐨𝐧 — only logs from the relevant time window and service. 10-100x noise reduction before the model sees anything.
• 𝐒𝐜𝐨𝐫𝐢𝐧𝐠 — ERROR/FATAL/CRITICAL lines ranked highest. Service mentions boosted. Stack traces kept together.
• 𝐎𝐫𝐝𝐞𝐫𝐢𝐧𝐠 — re-sorted chronologically so the model reads a timeline, not a jumbled ranking.
• 𝐒𝐭𝐫𝐮𝐜𝐭𝐮𝐫𝐢𝐧𝐠 — prompt designed for a triage brief, not a generic "summarize these logs."

The principles from "Lost in the Middle" and "Needle in the Haystack" — applied to a real system.

Where we are today (v0.1):
→ File-based log sources with glob patterns
→ PagerDuty webhooks with signature validation
→ Claude summarization
→ Slack notification
→ Docker Compose or pip install
→ Five-minute setup

Where we're going:
→ Datadog and Grafana Loki integrations
→ Deploy correlation from GitHub/GitLab
→ Context-aware runbook suggestions

We built kairos at Saarthi because we needed it — same context engineering discipline we apply in healthcare, now applied to incident response.

It's open source because context engineering for on-call shouldn't be locked behind a vendor.

GitHub link in comments.

#SRE #OpenSource #AI #ContextEngineering #IncidentResponse #DevOps #Reliability
