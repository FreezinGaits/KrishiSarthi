"""
n8n Workflow Integration Service

Triggers n8n automation workflows via webhook URLs for:
- Vendor enrichment (enrich vendor data with pricing, reviews)
- Notifications (SMS/WhatsApp via Twilio)
- Model retraining (collect corrections, trigger retrain)
- Price aggregation
- Low confidence escalation

All webhook URLs are configured via environment variables.
Falls back to mock responses in DEMO_MODE.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

from app.config import get_settings
from app.models.schemas import NotifyVendorResponse
from app.utils.logger import get_logger

logger = get_logger("service.n8n")
settings = get_settings()

# ── Constants ─────────────────────────────────────
HTTP_TIMEOUT = 10.0  # seconds
MAX_RETRIES = 2


async def _trigger_webhook(
    webhook_path: str,
    payload: Dict[str, Any],
    request_id: str = "",
    retry_count: int = MAX_RETRIES,
) -> Dict[str, Any]:
    """
    Generic webhook trigger with retry logic.

    Args:
        webhook_path: Relative path from n8n base URL (e.g. /webhook/send-notification)
        payload: JSON payload to send
        request_id: Request tracking ID
        retry_count: Number of retry attempts

    Returns:
        Response JSON from n8n, or a mock response in demo mode
    """
    url = f"{settings.n8n_base_url.rstrip('/')}{webhook_path}"

    for attempt in range(1, retry_count + 1):
        try:
            logger.info(
                "[%s] Triggering n8n webhook: %s (attempt %d/%d)",
                request_id, webhook_path, attempt, retry_count,
            )

            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "KrishiSarthi/1.0",
                        "X-Request-ID": request_id,
                    },
                )
                response.raise_for_status()

            result = response.json() if response.headers.get("content-type", "").startswith("application/json") else {"status": "ok", "raw": response.text}
            logger.info("[%s] n8n webhook success: %s → %s", request_id, webhook_path, result.get("status", "ok"))
            return result

        except httpx.TimeoutException:
            logger.warning("[%s] n8n webhook timeout: %s (attempt %d/%d)", request_id, webhook_path, attempt, retry_count)
        except httpx.ConnectError:
            logger.warning("[%s] n8n not reachable: %s (attempt %d/%d)", request_id, url, attempt, retry_count)
            break  # Don't retry if n8n is down
        except httpx.HTTPStatusError as e:
            logger.error("[%s] n8n HTTP error %d: %s", request_id, e.response.status_code, webhook_path)
            if e.response.status_code >= 500:
                continue  # Retry on server errors
            break  # Don't retry on client errors (4xx)
        except Exception as e:
            logger.error("[%s] n8n webhook error: %s — %s", request_id, webhook_path, str(e))

    # All retries exhausted
    raise ConnectionError(f"Failed to trigger n8n webhook: {webhook_path} after {retry_count} attempts")


# ─────────────────────────────────────────────────
# Vendor Enrichment Workflow
# ─────────────────────────────────────────────────

async def trigger_vendor_enrichment(
    vendor_data: Dict[str, Any],
    request_id: str = "",
) -> Dict[str, Any]:
    """
    Trigger vendor enrichment workflow.
    n8n will: fetch pricing data, check reviews, update database.

    Args:
        vendor_data: Dict with vendor name, lat, lng, etc.
        request_id: Tracking ID
    """
    logger.info("[%s] Triggering vendor enrichment for: %s", request_id, vendor_data.get("name", "unknown"))

    if settings.is_demo:
        logger.info("[%s] DEMO: Vendor enrichment skipped", request_id)
        return {
            "status": "demo_skipped",
            "message": "Vendor enrichment not executed in demo mode",
            "vendor": vendor_data.get("name", ""),
            "timestamp": datetime.utcnow().isoformat(),
        }

    payload = {
        "event": "vendor_enrichment",
        "vendor": vendor_data,
        "request_id": request_id,
        "timestamp": datetime.utcnow().isoformat(),
    }

    return await _trigger_webhook(
        settings.n8n_vendor_enrichment_webhook,
        payload,
        request_id,
    )


# ─────────────────────────────────────────────────
# Notification Workflow (SMS / WhatsApp)
# ─────────────────────────────────────────────────

async def trigger_notification(
    phone: str,
    message: str,
    channel: str = "sms",
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    notification_id: Optional[str] = None,
    request_id: str = "",
) -> NotifyVendorResponse:
    """
    Trigger notification workflow via n8n.
    n8n will: send SMS/WhatsApp via Twilio, log to database.

    Args:
        phone: Recipient phone number
        message: Notification content
        channel: "sms" or "whatsapp"
        session_id: Related session
        metadata: Extra context
        notification_id: Pre-generated tracking ID
        request_id: Request tracking ID

    Returns:
        NotifyVendorResponse with status and tracking ID
    """
    nid = notification_id or str(uuid.uuid4())

    logger.info(
        "[%s] Triggering %s notification to %s (nid=%s)",
        request_id, channel, phone[:6] + "****", nid[:8],
    )

    if settings.is_demo:
        logger.info("[%s] DEMO: Notification simulated (not sent)", request_id)
        return NotifyVendorResponse(
            status="sent_demo",
            notification_id=nid,
            channel=channel,
            message=f"[DEMO] {channel.upper()} notification would be sent to {phone}: {message[:80]}...",
        )

    payload = {
        "event": "send_notification",
        "notification_id": nid,
        "phone": phone,
        "message": message,
        "channel": channel,
        "session_id": session_id,
        "metadata": metadata or {},
        "request_id": request_id,
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        result = await _trigger_webhook(
            settings.n8n_notification_webhook,
            payload,
            request_id,
        )
        return NotifyVendorResponse(
            status=result.get("status", "sent"),
            notification_id=nid,
            channel=channel,
            message=f"Notification sent via {channel}",
        )
    except ConnectionError:
        logger.warning("[%s] n8n unreachable, notification not sent", request_id)
        if settings.is_demo:
            return NotifyVendorResponse(
                status="sent_demo",
                notification_id=nid,
                channel=channel,
                message=f"[DEMO FALLBACK] n8n unreachable — notification simulated",
            )
        return NotifyVendorResponse(
            status="failed",
            notification_id=nid,
            channel=channel,
            message="Notification service unavailable",
        )


# ─────────────────────────────────────────────────
# Retraining Trigger Workflow
# ─────────────────────────────────────────────────

async def trigger_retraining(
    correction_data: Dict[str, Any],
    request_id: str = "",
) -> Dict[str, Any]:
    """
    Trigger model retraining workflow when a farmer corrects a diagnosis.
    n8n will: store correction, check if threshold met, trigger retrain job.

    Args:
        correction_data: Dict with image_id, correct_label, original_prediction, etc.
        request_id: Tracking ID
    """
    logger.info(
        "[%s] Triggering retraining: original=%s → corrected=%s",
        request_id,
        correction_data.get("original_prediction", "?"),
        correction_data.get("correct_label", "?"),
    )

    if settings.is_demo:
        logger.info("[%s] DEMO: Retraining trigger skipped", request_id)
        return {
            "status": "demo_skipped",
            "message": "Retraining trigger not executed in demo mode",
            "correction": correction_data,
            "timestamp": datetime.utcnow().isoformat(),
        }

    payload = {
        "event": "retraining_trigger",
        "correction": correction_data,
        "request_id": request_id,
        "timestamp": datetime.utcnow().isoformat(),
    }

    return await _trigger_webhook(
        settings.n8n_retraining_webhook,
        payload,
        request_id,
    )


# ─────────────────────────────────────────────────
# Low Confidence Escalation
# ─────────────────────────────────────────────────

async def trigger_escalation(
    diagnosis_data: Dict[str, Any],
    confidence: float,
    request_id: str = "",
) -> Dict[str, Any]:
    """
    Escalate low-confidence diagnoses to a human agronomist.
    Triggered when confidence < 0.6.

    Args:
        diagnosis_data: Full diagnosis result
        confidence: Model confidence score
        request_id: Tracking ID
    """
    logger.info("[%s] Low confidence escalation: confidence=%.2f", request_id, confidence)

    if settings.is_demo:
        logger.info("[%s] DEMO: Escalation skipped", request_id)
        return {
            "status": "demo_skipped",
            "message": f"Low confidence ({confidence:.0%}) escalation not sent in demo mode",
            "timestamp": datetime.utcnow().isoformat(),
        }

    payload = {
        "event": "low_confidence_escalation",
        "diagnosis": diagnosis_data,
        "confidence": confidence,
        "request_id": request_id,
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Use dedicated escalation webhook (falls back to notification webhook if not configured)
    webhook = getattr(settings, 'n8n_escalation_webhook', settings.n8n_notification_webhook)
    return await _trigger_webhook(
        webhook,
        payload,
        request_id,
    )
