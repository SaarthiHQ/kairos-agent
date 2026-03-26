"""FastAPI app that receives PagerDuty webhooks and triggers the triage pipeline."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request

from kairos_agent.config import KairosConfig, load_config
from kairos_agent.pipeline import run_triage_pipeline

logger = logging.getLogger("kairos_agent")

app = FastAPI(title="kairos-agent", version="0.1.0")

_config: KairosConfig | None = None


def get_config() -> KairosConfig:
    global _config
    if _config is None:
        _config = load_config()
    return _config


def verify_pagerduty_signature(
    body: bytes, signature: str, secret: str
) -> bool:
    """Validate PagerDuty V3 webhook signature (HMAC-SHA256).

    PagerDuty sends the signature in the X-PagerDuty-Signature header
    as a list of versioned signatures: "v1=<hex_digest>".
    """
    expected = hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()

    # PagerDuty may send multiple signatures; accept any v1 match
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

    # We only care about triggered incidents
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


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhook/pagerduty")
async def pagerduty_webhook(
    request: Request,
    x_pagerduty_signature: str = Header(default=""),
) -> dict[str, str]:
    config = get_config()
    body = await request.body()

    # Validate signature
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
        "Received alert: %s (service=%s)",
        alert_info["title"],
        alert_info["service_name"],
    )

    # Run the triage pipeline asynchronously
    import asyncio
    asyncio.create_task(_run_pipeline(config, alert_info))

    return {"status": "accepted", "incident_id": alert_info["incident_id"]}


async def _run_pipeline(config: KairosConfig, alert_info: dict[str, Any]) -> None:
    """Run the triage pipeline in the background, logging errors."""
    try:
        await run_triage_pipeline(config, alert_info)
    except Exception:
        logger.exception("Triage pipeline failed for incident %s", alert_info["incident_id"])
