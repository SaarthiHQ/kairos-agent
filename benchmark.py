"""Benchmark: Context engineering + model tier experiment.

Runs the same incident through 6 configurations:
  A. Raw dump + Opus         D. Engineered + Opus
  B. Raw dump + Sonnet       E. Engineered + Sonnet
  C. Raw dump + Haiku        F. Engineered + Haiku

Uses realistic log volume (~130 lines across 2 services) to stress-test
the context engineering pipeline vs raw dump approach.

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python benchmark.py
"""

import asyncio
import json
import os
import time
from pathlib import Path

import anthropic

from kairos_agent.config import load_config
from kairos_agent.context_assembler import assemble_context, infer_alert_type
from kairos_agent.service_catalog import resolve_sources_for_alert
from kairos_agent.sources import build_sources


MODELS = {
    "opus": "claude-opus-4-20250514",
    "sonnet": "claude-sonnet-4-20250514",
    "haiku": "claude-haiku-4-5-20251001",
}

ALERT = {
    "incident_id": "BENCH-002",
    "title": "High error rate on saarthi-clinical — document processing pipeline stalled, auth failures",
    "service_name": "saarthi-clinical",
    "urgency": "high",
    "triggered_at": "2026-03-28T20:33:18Z",
    "html_url": "https://one.eu.newrelic.com/alerts-ai/accounts/7688224",
}

# Known ground truth for evaluation
GROUND_TRUTH = """\
The actual incident chain:
1. Gemini API quota exhausted (RESOURCE_EXHAUSTED) → extraction failures
2. Claude API overloaded (529) → fallback failures
3. OpenAI rate limited → all providers exhausted
4. D1 database locked under queue pressure → 500 errors on status checks
5. R2 upload timeouts → extraction results not persisting
6. Firebase token expiration → auth middleware errors (separate issue, concurrent)
7. Vectorize timeout → search degradation
8. Queue backlog: 31 pending, 23 stuck documents
9. Service error rate >50%, patients receiving fallback messages
10. saarthi-flask seeing cascading failures from saarthi-clinical degradation
"""

RAW_SYSTEM = "You are an incident triage assistant. Analyze the logs and summarize what's happening."

EVAL_PROMPT = """\
You are a strict evaluator of incident triage summaries. Score on 5 dimensions (1-5 each):

1. *Accuracy*: Does it identify the actual root cause chain? (1=misses root cause, 5=identifies full cascade)
2. *Evidence*: Does it cite specific log lines or patterns? (1=no evidence, 5=precise citations)
3. *Actionability*: Are next steps specific to THIS incident? (1=generic "check logs", 5=exact actions)
4. *Hallucination*: Does it claim things NOT in the logs? (1=significant hallucination, 5=strictly evidence-based)
5. *Confidence*: When data is missing, does it say so? Does it express appropriate certainty? (1=overconfident, 5=well-calibrated)

Ground truth for this incident:
{ground_truth}

Triage summary to evaluate:
---
{summary}
---

Respond ONLY with JSON:
{{"accuracy": N, "evidence": N, "actionability": N, "hallucination": N, "confidence": N, "total": N, "notes": "key observation in one sentence"}}
"""


async def get_raw_logs() -> str:
    """Read all log files without any engineering — raw dump."""
    files = [
        "sample_logs/stress-test.log",
        "sample_logs/stress-test-flask.log",
    ]
    lines = []
    for f in files:
        lines.extend(Path(f).read_text().splitlines())
    return "\n".join(lines)


async def get_engineered_context() -> tuple:
    """Build context through the full kairos pipeline."""
    config = load_config("kairos-benchmark.yaml")
    alert_type = infer_alert_type(ALERT)
    resolved = resolve_sources_for_alert("saarthi-clinical", config)
    service_metadata = config.services.get("saarthi-clinical")

    context = assemble_context(
        alert_info=ALERT,
        log_sources=config.log_sources,
        config=config.context,
        resolved_sources=resolved if config.services else None,
        alert_type=alert_type,
        service_metadata=service_metadata,
    )

    from kairos_agent.summarizer import build_user_prompt, SYSTEM_PROMPT
    user_prompt = build_user_prompt(ALERT, context)
    return SYSTEM_PROMPT, user_prompt, context


async def call_model(system: str, user: str, model: str) -> tuple:
    """Call Claude, return (summary, latency_ms, in_tokens, out_tokens, cost_estimate)."""
    client = anthropic.AsyncAnthropic()
    t0 = time.monotonic()

    msg = await client.messages.create(
        model=model,
        max_tokens=1500,
        system=system,
        messages=[{"role": "user", "content": user}],
    )

    latency = (time.monotonic() - t0) * 1000
    summary = msg.content[0].text
    in_tok = msg.usage.input_tokens
    out_tok = msg.usage.output_tokens

    # Cost estimation (per MTok pricing March 2026)
    costs = {
        MODELS["haiku"]: (0.80, 4.00),
        MODELS["sonnet"]: (3.00, 15.00),
        MODELS["opus"]: (15.00, 75.00),
    }
    in_rate, out_rate = costs.get(model, (3.00, 15.00))
    cost = (in_tok * in_rate + out_tok * out_rate) / 1_000_000

    return summary, latency, in_tok, out_tok, cost


async def evaluate(summary: str) -> dict:
    """Use Sonnet to evaluate a triage summary against ground truth."""
    client = anthropic.AsyncAnthropic()
    msg = await client.messages.create(
        model=MODELS["sonnet"],
        max_tokens=300,
        messages=[{"role": "user", "content": EVAL_PROMPT.format(
            ground_truth=GROUND_TRUTH, summary=summary
        )}],
    )
    text = msg.content[0].text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        import re
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {"error": text, "total": 0}


async def main():
    print("=" * 80)
    print("  BENCHMARK: Context Engineering vs Raw Dump × Model Tier")
    print("=" * 80)
    print()

    # Prepare data
    print("Preparing data...")
    raw_logs = await get_raw_logs()
    raw_lines = len(raw_logs.split("\n"))
    eng_system, eng_user, eng_ctx = await get_engineered_context()
    eng_lines = len(eng_ctx.log_lines)
    eng_dep = len(eng_ctx.dependency_log_lines)
    print(f"  Raw: {raw_lines} lines ({len(raw_logs)} chars)")
    print(f"  Engineered: {eng_lines} direct + {eng_dep} dep lines")
    print(f"  Compression ratio: {raw_lines} → {eng_lines + eng_dep} ({100 - (eng_lines + eng_dep) / raw_lines * 100:.0f}% reduction)")
    if eng_ctx.quality:
        print(f"  Quality: {eng_ctx.quality.coverage_ratio:.0%} coverage, {len(eng_ctx.quality.gaps)} gaps")
    print()

    raw_user = f"""Alert: "{ALERT['title']}"
Service: {ALERT['service_name']}
Urgency: {ALERT['urgency']}
Time: {ALERT['triggered_at']}

Logs:
{raw_logs}

What's happening and what should the on-call do?"""

    configs = [
        ("A", "Raw + Opus",    RAW_SYSTEM, raw_user, MODELS["opus"]),
        ("B", "Raw + Sonnet",  RAW_SYSTEM, raw_user, MODELS["sonnet"]),
        ("C", "Raw + Haiku",   RAW_SYSTEM, raw_user, MODELS["haiku"]),
        ("D", "Eng + Opus",    eng_system, eng_user,  MODELS["opus"]),
        ("E", "Eng + Sonnet",  eng_system, eng_user,  MODELS["sonnet"]),
        ("F", "Eng + Haiku",   eng_system, eng_user,  MODELS["haiku"]),
    ]

    results = []
    for label, name, sys_p, usr_p, model in configs:
        print(f"  {label}. {name}...", end=" ", flush=True)
        try:
            summary, lat, in_t, out_t, cost = await call_model(sys_p, usr_p, model)
            print(f"{lat:.0f}ms | {in_t}→{out_t} tok | ${cost:.4f}")

            scores = await evaluate(summary)
            scores.update({
                "label": label, "name": name,
                "latency_ms": round(lat),
                "input_tokens": in_t, "output_tokens": out_t,
                "cost_usd": round(cost, 5),
                "summary": summary,
            })
            results.append(scores)
        except Exception as e:
            print(f"FAILED: {e}")
            results.append({"label": label, "name": name, "error": str(e), "total": 0})

    # Results table
    print()
    print("=" * 80)
    print(f"{'Config':<18} {'Acc':>4} {'Evid':>4} {'Act':>4} {'Hall':>4} {'Conf':>4} {'TOTAL':>6} {'Cost':>8} {'Latency':>8}")
    print("-" * 80)
    for r in results:
        if r.get("total", 0) == 0 and "error" in r:
            print(f"{r['name']:<18} {'ERROR':>50}")
            continue
        print(
            f"{r['name']:<18} "
            f"{r.get('accuracy', '?'):>4} "
            f"{r.get('evidence', '?'):>4} "
            f"{r.get('actionability', '?'):>4} "
            f"{r.get('hallucination', '?'):>4} "
            f"{r.get('confidence', '?'):>4} "
            f"{r.get('total', '?'):>6} "
            f"${r.get('cost_usd', 0):.4f} "
            f"{r.get('latency_ms', 0):>7}ms"
        )

    # Key comparisons
    print()
    print("KEY FINDINGS:")
    def t(i): return results[i].get("total", 0) if i < len(results) else 0
    def c(i): return results[i].get("cost_usd", 0) if i < len(results) else 0

    if t(5) and t(0):
        print(f"  Eng+Haiku ({t(5)}/25) vs Raw+Opus ({t(0)}/25) — context engineering + cheapest model vs raw + most expensive")
        print(f"  Cost: ${c(5):.4f} vs ${c(0):.4f} — {c(0)/c(5) if c(5) > 0 else 0:.0f}x cheaper")
    if t(4) and t(1):
        print(f"  Eng+Sonnet ({t(4)}/25) vs Raw+Sonnet ({t(1)}/25) — same model, engineered vs raw")
    if t(5) and t(3):
        print(f"  Eng+Haiku ({t(5)}/25) vs Eng+Opus ({t(3)}/25) — same engineering, cheapest vs most expensive model")

    # Evaluator notes
    print()
    print("EVALUATOR NOTES:")
    for r in results:
        notes = r.get("notes", "")
        if notes:
            print(f"  {r.get('name', '?')}: {notes}")

    # Save
    output = "docs/research/benchmark-results.json"
    os.makedirs(os.path.dirname(output), exist_ok=True)
    with open(output, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nFull results (with summaries) saved to {output}")


if __name__ == "__main__":
    asyncio.run(main())
