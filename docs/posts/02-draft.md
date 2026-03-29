DRAFT — follow-up LinkedIn post on context engineering

---

Last week I wrote about how context engineering is reshaping SRE. Several people asked: why not just give the LLM all the logs?

Because more context often means worse results. Here's what the research says:

𝐋𝐨𝐬𝐭 𝐢𝐧 𝐭𝐡𝐞 𝐌𝐢𝐝𝐝𝐥𝐞 (Stanford, 2023)
LLMs show a U-shaped attention curve. They use information at the start and end of the context well, but significantly degrade in the middle. With 20+ documents, performance dropped *below* the no-context baseline. More data made the model dumber.

𝐍𝐞𝐞𝐝𝐥𝐞 𝐢𝐧 𝐭𝐡𝐞 𝐇𝐚𝐲𝐬𝐭𝐚𝐜𝐤 (IBM Research, 2024)
Even simple fact retrieval breaks down in long contexts. A bigger context window doesn't mean better retrieval. It means more noise.

𝐏𝐫𝐨𝐦𝐩𝐭 𝐑𝐞𝐩𝐞𝐭𝐢𝐭𝐢𝐨𝐧 (Google Research, 2025)
The order of information in your prompt changes the output. Repeating the query after the context improved accuracy in 47/70 tests with 0 regressions. Prompt structure isn't cosmetic — it's functional.

What this means in practice:

1. 𝐅𝐢𝐥𝐭𝐞𝐫 𝐛𝐞𝐟𝐨𝐫𝐞 𝐲𝐨𝐮 𝐩𝐫𝐨𝐦𝐩𝐭. Don't send the model everything. 500 filtered lines beat 5000 raw lines.

2. 𝐎𝐫𝐝𝐞𝐫 𝐦𝐚𝐭𝐭𝐞𝐫𝐬. Put high-signal information at the start and end. The middle is where information goes to die.

3. 𝐒𝐭𝐫𝐮𝐜𝐭𝐮𝐫𝐞 𝐥𝐢𝐤𝐞 𝐚 𝐛𝐫𝐢𝐞𝐟𝐢𝐧𝐠. Situation first, evidence next, question last. This isn't just good UX — it's how causal attention works.

This applies whether you're building for SRE, healthcare, legal, or customer support. At Saarthi, we apply context engineering across healthcare and incident management — the discipline is the same even when the domain changes.

The LLM is the reasoning engine. Context engineering is everything else.

Full article with more detail — link in comments.

#ContextEngineering #AI #LLMs #SRE #MachineLearning #Reliability
