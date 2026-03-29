# Saarthi Intelligent Context Engineering Framework — Design

## Architecture: Three Layers

### Pre-Engine: Domain Adapter (pluggable)
- Entity graph (services / patients / cases)
- Source connectors (NR / D1+R2 / Splunk)
- Question classifier (alert type / clinical question type)

### Engine: Domain-Agnostic (ships as-is)
1. Resolve — entity graph → which sources
2. Fetch — parallel, with quality tracking
3. Compress — dedup, normalize, collapse
4. Score — keyword + semantic + configurable weights
5. Budget — token-aware selection
6. Prompt — structured, with repetition
7. Call — model routing (tier selection)
8. Assess — did the output use the evidence?

### Post-Engine: Domain Formatter (pluggable)
- Output format (Slack / WhatsApp / API)
- Delivery channel
- Feedback capture
- Memory write

## The Equalizer (SaaS config surface)

| Dial | Controls |
|------|----------|
| Entity schema | Graph structure |
| Source registry | Data connections |
| Question classifier | Input categorization |
| Scoring weights | What "important" means |
| Scoring boosts | Per question-type emphasis |
| Compression rules | Noise reduction strategy |
| Token budget | Context size |
| Model tier | Which model (Haiku/Sonnet/Opus) |
| Output template | Formatting |
| Feedback mechanism | Learning loop |

## Saarthi Health Mapping

Entity: Patient (conditions, medications, allergies, documents, providers)
Sources: D1 (records), R2 (documents), Vectorize (semantic search)
Question types: diagnosis, medication_review, lab_interpretation, imaging, follow_up
Scoring: abnormal values +12, critical labs +15, recency bias, routine findings -3
Compression: full detail 30 days, summarize beyond 1 year
Model: Sonnet (clinical accuracy tier)
Output: WhatsApp clinical brief
Feedback: Doctor correction in chat
