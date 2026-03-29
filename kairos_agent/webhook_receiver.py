"""FastAPI app that receives alert webhooks and triggers the triage pipeline.

Supported triggers:
- POST /webhook/pagerduty  — PagerDuty V3 webhooks
- POST /webhook/newrelic   — New Relic alert notifications
- POST /slack/command       — Slack slash commands (/kairos investigate <service>)
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Form, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from kairos_agent import __version__
from kairos_agent.config import KairosConfig, load_config
from kairos_agent.context_assembler import assemble_context, infer_alert_type
from kairos_agent.pipeline import run_triage_pipeline
from kairos_agent.service_catalog import resolve_sources_for_alert
from kairos_agent.summarizer import summarize

logger = logging.getLogger("kairos_agent")

app = FastAPI(title="kairos-agent", version=__version__)

_config: KairosConfig | None = None


def get_config() -> KairosConfig:
    global _config
    if _config is None:
        _config = load_config()
    return _config


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


# ---------------------------------------------------------------------------
# PagerDuty V3 webhook
# ---------------------------------------------------------------------------

def verify_pagerduty_signature(
    body: bytes, signature: str, secret: str
) -> bool:
    """Validate PagerDuty V3 webhook signature (HMAC-SHA256)."""
    expected = hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()

    for sig_part in signature.split(","):
        sig_part = sig_part.strip()
        if sig_part.startswith("v1="):
            provided = sig_part[3:]
            if hmac.compare_digest(expected, provided):
                return True
    return False


def extract_alert_info(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Extract relevant alert fields from a PagerDuty V3 webhook event."""
    event = payload.get("event", {})
    event_type = event.get("event_type", "")

    if event_type != "incident.triggered":
        return None

    data = event.get("data", {})
    service = data.get("service", {})

    return {
        "incident_id": data.get("id", "unknown"),
        "title": data.get("title", "No title"),
        "service_name": service.get("name", "unknown"),
        "urgency": data.get("urgency", "high"),
        "triggered_at": data.get("created_at", datetime.now(timezone.utc).isoformat()),
        "html_url": data.get("html_url", ""),
    }


@app.post("/webhook/pagerduty")
async def pagerduty_webhook(
    request: Request,
    x_pagerduty_signature: str = Header(default=""),
) -> dict[str, str]:
    config = get_config()
    body = await request.body()

    if not x_pagerduty_signature:
        raise HTTPException(status_code=401, detail="Missing signature header")

    if not verify_pagerduty_signature(
        body, x_pagerduty_signature, config.pagerduty.webhook_secret
    ):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = json.loads(body)
    alert_info = extract_alert_info(payload)

    if alert_info is None:
        return {"status": "ignored", "reason": "not an incident.triggered event"}

    logger.info(
        "PagerDuty alert: %s (service=%s)",
        alert_info["title"],
        alert_info["service_name"],
    )

    asyncio.create_task(_run_pipeline(config, alert_info))
    return {"status": "accepted", "incident_id": alert_info["incident_id"]}


# ---------------------------------------------------------------------------
# New Relic webhook
# ---------------------------------------------------------------------------

def extract_newrelic_alert_info(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract alert fields from a New Relic webhook notification.

    New Relic webhook payloads vary based on configuration. We handle:
    - Default workflow webhook format
    - Custom webhook with standard field names
    """
    # Try standard workflow fields first
    title = (
        payload.get("issueTitle")
        or payload.get("title")
        or payload.get("condition_name")
        or payload.get("details", "Alert triggered")
    )

    # Service name: try multiple fields
    service_name = (
        payload.get("service_name")
        or payload.get("targetName")
        or payload.get("targets", [{}])[0].get("name", "")
        if isinstance(payload.get("targets"), list) and payload.get("targets")
        else payload.get("entity_name", "")
    ) or "unknown"

    # Severity mapping
    severity = payload.get("severity", payload.get("priority", "")).lower()
    urgency = "high" if severity in ("critical", "high", "1", "2") else "low"

    # Incident ID
    incident_id = str(
        payload.get("issueId")
        or payload.get("incident_id")
        or payload.get("id")
        or f"nr-{int(time.time())}"
    )

    # Timestamp
    triggered_at = (
        payload.get("timestamp")
        or payload.get("createdAt")
        or payload.get("openedAt")
        or datetime.now(timezone.utc).isoformat()
    )
    # Convert epoch ms to ISO if numeric
    if isinstance(triggered_at, (int, float)):
        triggered_at = datetime.fromtimestamp(
            triggered_at / 1000, tz=timezone.utc
        ).isoformat()

    # URL
    html_url = (
        payload.get("issueUrl")
        or payload.get("issuePageUrl")
        or payload.get("violationChartUrl")
        or ""
    )

    return {
        "incident_id": incident_id,
        "title": title,
        "service_name": service_name,
        "urgency": urgency,
        "triggered_at": triggered_at,
        "html_url": html_url,
        "source": "newrelic",
    }


@app.post("/webhook/newrelic")
async def newrelic_webhook(request: Request) -> dict[str, str]:
    """Receive New Relic alert webhook and trigger triage.

    New Relic workflow webhooks don't use HMAC signatures by default.
    For production, validate using a shared secret header or IP allowlisting.
    """
    config = get_config()
    body = await request.body()

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Skip if this is a "closed" or "acknowledged" state
    state = payload.get("state", payload.get("current_state", "")).lower()
    if state in ("closed", "acknowledged", "resolved"):
        return {"status": "ignored", "reason": f"alert state is {state}"}

    alert_info = extract_newrelic_alert_info(payload)

    logger.info(
        "New Relic alert: %s (service=%s)",
        alert_info["title"],
        alert_info["service_name"],
    )

    asyncio.create_task(_run_pipeline(config, alert_info))
    return {"status": "accepted", "incident_id": alert_info["incident_id"]}


# ---------------------------------------------------------------------------
# Slack slash command: /kairos investigate <service>
# ---------------------------------------------------------------------------

def verify_slack_signature(
    body: bytes, timestamp: str, signature: str, signing_secret: str
) -> bool:
    """Verify Slack request signature (HMAC-SHA256)."""
    basestring = f"v0:{timestamp}:{body.decode()}".encode()
    expected = "v0=" + hmac.new(
        signing_secret.encode(), basestring, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@app.post("/slack/command")
async def slack_command(
    request: Request,
    command: str = Form(default=""),
    text: str = Form(default=""),
    user_name: str = Form(default=""),
    channel_name: str = Form(default=""),
    response_url: str = Form(default=""),
    x_slack_request_timestamp: str = Header(default=""),
    x_slack_signature: str = Header(default=""),
) -> JSONResponse:
    """Handle Slack slash command: /kairos investigate <service>

    Usage in Slack:
        /kairos investigate saarthi-clinical
        /kairos investigate saarthi-flask --title "latency spike"
        /kairos status
    """
    config = get_config()

    # Parse the command text
    parts = text.strip().split()
    if not parts:
        return JSONResponse({
            "response_type": "ephemeral",
            "text": (
                "Usage:\n"
                "  `/kairos investigate <service>` — run triage for a service\n"
                "  `/kairos investigate <service> --title \"alert description\"` — with custom title\n"
                "  `/kairos status` — check kairos health"
            ),
        })

    subcommand = parts[0].lower()

    if subcommand == "status":
        service_count = len(config.services)
        source_count = len(config.log_sources)
        return JSONResponse({
            "response_type": "ephemeral",
            "text": f"kairos-agent v{__version__} — {source_count} sources, {service_count} services configured",
        })

    if subcommand != "investigate":
        return JSONResponse({
            "response_type": "ephemeral",
            "text": f"Unknown command: `{subcommand}`. Try `/kairos investigate <service>`",
        })

    if len(parts) < 2:
        return JSONResponse({
            "response_type": "ephemeral",
            "text": "Please specify a service: `/kairos investigate <service>`",
        })

    service_name = parts[1]

    # Parse optional --title
    title = f"Manual investigation requested for {service_name}"
    if "--title" in parts:
        title_idx = parts.index("--title")
        title_parts = parts[title_idx + 1:]
        if title_parts:
            title = " ".join(title_parts).strip('"').strip("'")

    alert_info = {
        "incident_id": f"slack-{user_name}-{int(time.time())}",
        "title": title,
        "service_name": service_name,
        "urgency": "high",
        "triggered_at": datetime.now(timezone.utc).isoformat(),
        "html_url": "",
        "source": "slack",
        "requested_by": user_name,
        "channel": channel_name,
    }

    logger.info(
        "Slack command from @%s in #%s: investigate %s",
        user_name, channel_name, service_name,
    )

    # Respond immediately (Slack requires <3s response)
    asyncio.create_task(_run_slack_triage(config, alert_info, response_url))

    return JSONResponse({
        "response_type": "in_channel",
        "text": f"Investigating *{service_name}*... triage summary incoming.",
    })


async def _run_slack_triage(
    config: KairosConfig,
    alert_info: dict[str, Any],
    response_url: str,
) -> None:
    """Run triage and post result back to Slack via response_url."""
    try:
        # Assemble and summarize (same as pipeline, but post result to response_url)
        alert_type = infer_alert_type(alert_info)
        resolved = resolve_sources_for_alert(alert_info["service_name"], config)
        service_metadata = config.services.get(alert_info["service_name"])

        context = assemble_context(
            alert_info=alert_info,
            log_sources=config.log_sources,
            config=config.context,
            resolved_sources=resolved if config.services else None,
            alert_type=alert_type,
            service_metadata=service_metadata,
        )

        summary = await summarize(
            alert_info=alert_info,
            context=context,
            llm_config=config.llm,
        )

        # Post summary back to Slack via response_url
        import httpx
        quality_note = ""
        if context.quality and context.quality.gaps:
            quality_note = "\n\n_Gaps: " + "; ".join(context.quality.gaps[:2]) + "_"

        async with httpx.AsyncClient() as client:
            await client.post(response_url, json={
                "response_type": "in_channel",
                "text": (
                    f"*Triage: {alert_info['title']}*\n"
                    f"Service: {alert_info['service_name']} | "
                    f"Alert type: {alert_type.value} | "
                    f"Sources: {len(context.sources_checked)}\n\n"
                    f"{summary}"
                    f"{quality_note}"
                ),
            })

        logger.info("Slack triage posted for %s", alert_info["service_name"])

    except Exception:
        logger.exception("Slack triage failed for %s", alert_info["service_name"])
        # Try to post error back to Slack
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                await client.post(response_url, json={
                    "response_type": "ephemeral",
                    "text": f"Triage failed for {alert_info['service_name']}. Check kairos-agent logs.",
                })
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Pipeline runner (shared)
# ---------------------------------------------------------------------------

async def _run_pipeline(config: KairosConfig, alert_info: dict[str, Any]) -> None:
    """Run the triage pipeline in the background, logging errors."""
    try:
        await run_triage_pipeline(config, alert_info)
    except Exception:
        logger.exception("Triage pipeline failed for incident %s", alert_info["incident_id"])
