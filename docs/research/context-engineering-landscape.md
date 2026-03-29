# Context Engineering Landscape — Deep Dive (March 2026)

## What Exists Today

The context engineering space has matured rapidly. Here's what's out there, what each does, and where Saarthi's framework fits.

---

## 1. Frameworks and Orchestrators

### LangChain / LangGraph
- **What:** The dominant LLM application framework. Chains of calls, memory modules, RAG pipelines, agent workflows.
- **Context engineering:** ConversationBufferWindowMemory, summarization memory, vector store retrieval. LangGraph adds stateful agent orchestration with checkpointing.
- **Strength:** Broad ecosystem, 75K+ GitHub stars, most tutorials target it.
- **Weakness:** Higher latency (~10ms overhead vs ~6ms for LlamaIndex). Generic — no domain-specific intelligence. You build context engineering on top of it, not with it.
- **Relevance to Saarthi:** LangChain is a tool, not a competitor. Saarthi's framework could use LangChain components internally, but the intelligence (scoring, compression, quality assessment) is what LangChain doesn't provide.

### LlamaIndex
- **What:** Data-first framework — ingestion, chunking, indexing, retrieval. Designed for connecting LLMs to your data.
- **Context engineering:** Hierarchical indexing, semantic chunking, re-ranking, context window assembly. Explicit `Context` object for state management.
- **Strength:** Best-in-class retrieval quality. Lower latency. Handles messy, unstructured documents well.
- **Weakness:** Stateless by default — less mature for long-running agents. Retrieval-focused, not orchestration-focused.
- **Relevance to Saarthi:** LlamaIndex's retrieval capabilities (especially for medical documents) could be a source connector in the Saarthi framework. The indexing + re-ranking pipeline is complementary, not competitive.

### Google ADK (Agent Development Kit)
- **What:** Open-source, multi-agent-native framework from Google. Treats context as a compiled view over tiered state.
- **Context engineering:** Three-tier storage: Session (conversation), Memory (long-term), Artifacts (files/data). Named, ordered "processors" transform context. Strict scoping — each agent/sub-agent sees minimum required context.
- **Strength:** The most architecturally mature approach to context isolation. Multi-agent by design. Scope enforcement is built in, not bolted on.
- **Weakness:** Google ecosystem bias. Less adoption than LangChain. Newer, less battle-tested.
- **Relevance to Saarthi:** Google ADK's tiered context architecture (Session/Memory/Artifacts) is the closest to what Saarthi's framework needs. The "processors" concept maps to our compression/scoring pipeline. Worth studying deeply.

### Model Context Protocol (MCP)
- **What:** Universal standard (now under Linux Foundation) for connecting AI agents to tools and data sources. 97M+ monthly SDK downloads.
- **Context engineering:** Standardizes how tools are defined, invoked, and how results flow into context. Just-in-time instruction injection for scaling beyond 50+ tools.
- **Strength:** Universal adoption (Anthropic, OpenAI, Google, Microsoft). 75+ official connectors. The de facto standard for tool integration.
- **Weakness:** Protocol, not a framework. Handles tool connectivity but not scoring, compression, or quality assessment.
- **Relevance to Saarthi:** MCP is how kairos and Saarthi Health would expose their tools. The Source protocol we built is a simpler version of MCP's resource model. Future: make kairos sources MCP-compatible.

---

## 2. Memory and Persistence

### Mem0
- **What:** Universal memory layer for AI agents. Extracts, consolidates, and retrieves salient information from conversations.
- **Context engineering:** Intelligent compression (extracts meaning, discards noise). Semantic search + recency weighting + relevance scoring for retrieval. Graph memory for relationships.
- **Strength:** 91% lower p95 latency, 90% token cost reduction. 26% improvement in LLM-as-a-Judge metric. Production-grade with a published paper (arXiv:2504.19413).
- **Weakness:** Conversation-centric — designed for chatbots and assistants, not incident management or clinical decision support. Memory is about user interactions, not system data.
- **Relevance to Saarthi:** Mem0's memory architecture (semantic extraction + graph relationships) is directly applicable to the "State & Memory" component of our framework. Incident history, patient history, learned patterns — all could use Mem0's approach. Consider using Mem0 as a dependency for the Write operation in WSCI.

---

## 3. Research: Self-Improving Context

### ACE — Agentic Context Engineering (arXiv:2510.04618, ICLR 2026)
- **What:** Academic framework that treats contexts as evolving playbooks. Three components: Generator (produces output), Reflector (analyzes success/failure, extracts lessons), Curator (integrates lessons as incremental updates).
- **Context engineering:** "Grow-and-refine" mechanism — expansion then pruning based on semantic similarity. Prevents context collapse (where iterative rewriting erodes details) and brevity bias (where summarization drops domain insights).
- **Strength:** +10.6% on agent benchmarks, +8.6% on finance tasks. Matches top-ranked production agents on AppWorld leaderboard with a smaller open-source model.
- **Weakness:** Academic — not production-ready. The three-component architecture adds complexity.
- **Relevance to Saarthi:** The Reflector concept is exactly what kairos needs for v0.4+ (incident history/learning). After each triage, a Reflector extracts "what worked" and "what was missing" and the Curator updates the scoring rules. This is how the framework gets smarter over time. Highly relevant for the "Write" operation.

---

## 4. Production Lessons: Manus AI

### Manus — Context Engineering for Production Agents
- **What:** General-purpose AI agent (consumer product). Rebuilt their framework four times. Most mature production context engineering documented publicly.
- **Key strategies:**
  1. **KV-cache is king** — cache hit rate is the #1 metric. Append-only context, stable prefixes, deterministic serialization. Cached tokens cost 10x less ($0.30 vs $3.00/MTok on Claude).
  2. **Mask, don't remove** — don't dynamically add/remove tools (breaks cache). Use logit masking to constrain which tools are available.
  3. **Filesystem as extended memory** — treat files as unlimited context. Write data to files, read back on demand. Restorable compression (drop content if URL/path is preserved).
  4. **Recitation via todo.md** — agent rewrites a todo file at each step, pushing goals into the recency attention span. Mitigates lost-in-the-middle across ~50 tool calls per task.
  5. **Preserve errors** — don't hide failures. Seeing its own mistakes helps the model avoid repeating them.
  6. **Break patterns** — introduce structured variation in serialization to prevent the model from falling into repetitive rhythms.
- **Metrics:** 100:1 input-to-output token ratio. ~50 tool calls per task.
- **Relevance to Saarthi:** Manus's KV-cache optimization is critical for the managed service (cost reduction). The todo.md recitation maps to our triple prompt repetition (keeping the model focused). The "preserve errors" strategy validates our quality assessment approach (showing gaps, not hiding them). Most actionable production lessons available.

---

## 5. Comparison: Where Saarthi's Framework Fits

| Capability | LangChain | LlamaIndex | Google ADK | Mem0 | ACE | Manus | **Saarthi** |
|---|---|---|---|---|---|---|---|
| Multi-source fetch | Via tools | Via connectors | Via tools | No | No | Via tools | **Native — Source protocol** |
| Domain-aware scoring | No | Relevance ranking | No | Relevance scoring | Task-specific | No | **Alert-type / Clinical scoring** |
| Compression | No built-in | Summarization | Processors | Intelligent extraction | Grow-and-refine | Restorable compression | **Rule-based L1 + future L2/L3** |
| Quality assessment | No | No | No | No | Reflection step | Error preservation | **Native — gap detection** |
| Entity graph / catalog | No | Knowledge graph (add-on) | Session state | Graph memory | No | No | **Service catalog / Patient catalog** |
| Token budgeting | Manual | Via retrieval limits | Scope enforcement | Cost optimization | No | KV-cache optimization | **Explicit budget + prompt repetition** |
| Self-improvement | No | No | No | Learns from interactions | **Core feature** | Learns from errors | **v0.4+ via ACE-style reflection** |
| Domain-agnostic | Yes | Yes | Yes | Yes | Yes | Yes | **Yes — framework layer** |
| Domain-specific intelligence | No | No | No | No | No | No | **Yes — scoring, compression, catalog** |

### The gap Saarthi fills

Every existing framework is either:
- **Generic orchestration** (LangChain, LangGraph) — you build context engineering on top
- **Retrieval-focused** (LlamaIndex) — great at finding documents, doesn't score or compress
- **Memory-focused** (Mem0) — great for conversation history, not for system data or clinical records
- **Research** (ACE) — great ideas, not production-ready
- **Single-product** (Manus) — deeply optimized for one product, not a reusable framework

Saarthi's framework combines:
1. **Multi-source fetch** (like LangChain tools but with quality assessment)
2. **Domain-specific scoring** (no one else does this)
3. **Domain-specific compression** (no one else does this)
4. **Entity graph awareness** (service deps, patient comorbidities)
5. **Reusable across domains** (the framework layer is generic, implementations are domain-specific)

This is the moat: **domain-intelligent context engineering as a reusable framework**.

---

## 6. What to Learn From Each

| Source | Lesson for Saarthi |
|---|---|
| **Google ADK** | Tiered context (Session/Memory/Artifacts) is the right architecture. Adopt this for v0.4. |
| **Manus** | KV-cache optimization is critical for the SaaS. Append-only context, stable serialization. Recitation (todo.md) validates our prompt repetition. |
| **ACE (ICLR 2026)** | Generator → Reflector → Curator is the self-improvement loop. Implement for incident history learning. |
| **Mem0** | Memory extraction + graph relationships. Use for patient history and incident history persistence. |
| **MCP** | Make kairos Sources MCP-compatible for universal tool integration. |
| **LlamaIndex** | Use as a retrieval engine inside Saarthi Health's Source implementation (medical document retrieval). |

---

## Sources

- [Manus: Context Engineering for AI Agents](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus)
- [ACE: Agentic Context Engineering (arXiv:2510.04618)](https://arxiv.org/abs/2510.04618)
- [Mem0: Production-Ready AI Agents with Scalable Memory (arXiv:2504.19413)](https://arxiv.org/abs/2504.19413)
- [Google ADK: Architecting Efficient Context-Aware Multi-Agent Framework](https://developers.googleblog.com/architecting-efficient-context-aware-multi-agent-framework-for-production/)
- [Anthropic: Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Awesome Context Engineering (comprehensive repo)](https://github.com/Meirtz/Awesome-Context-Engineering)
- [Weaviate: Context Engineering — LLM Memory and Retrieval](https://weaviate.io/blog/context-engineering)
- [LangChain: State of Agent Engineering](https://www.langchain.com/state-of-agent-engineering)
