"""
Notification Router — POST /api/notify-vendor

Triggers notification workflows via n8n webhooks to send SMS/WhatsApp
messages to farmers with diagnosis results and vendor information.
Falls back to mock response in DEMO_MODE.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from app.config import get_settings
from app.models.schemas import NotifyVendorRequest, NotifyVendorResponse
from app.utils.logger import get_logger

logger = get_logger("router.notifications")
settings = get_settings()

router = APIRouter(prefix="/api", tags=["Notifications"])


@router.post(
    "/notify-vendor",
    response_model=NotifyVendorResponse,
    summary="Send notification to farmer",
    description="Triggers notification workflow (SMS/WhatsApp) via n8n to send diagnosis results or vendor info.",
)
async def notify_vendor(request: NotifyVendorRequest):
    """
    Notification endpoint.

    1. Validates phone number and message
    2. Triggers n8n notification webhook (or demo fallback)
    3. Returns notification status with tracking ID
    """
    request_id = str(uuid.uuid4())[:8]
    notification_id = str(uuid.uuid4())

    logger.info(
        "[%s] Notification request: phone=%s, channel=%s, message_len=%d",
        request_id,
        request.user_phone[:6] + "****",
        request.channel,
        len(request.message),
    )

    # ── Validate phone number format ──────────────
    phone = request.user_phone.strip()
    if not phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number is required",
        )

    # ── Validate channel ──────────────────────────
    valid_channels = {"sms", "whatsapp", "email"}
    if request.channel not in valid_channels:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid channel '{request.channel}'. Allowed: {', '.join(valid_channels)}",
        )

    # ── Validate message ──────────────────────────
    if not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message body cannot be empty",
        )

    # ── Send notification ─────────────────────────
    try:
        from app.services.n8n_service import trigger_notification
        result = await trigger_notification(
            phone=phone,
            message=request.message,
            channel=request.channel,
            session_id=request.session_id,
            metadata=request.metadata,
            notification_id=notification_id,
            request_id=request_id,
        )
        logger.info("[%s] Notification sent: id=%s, status=%s", request_id, notification_id, result.status)
        return result

    except ImportError:
        if settings.is_demo:
            logger.warning("[%s] n8n service not available, using demo fallback", request_id)
            return _demo_notification(request, notification_id, request_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Notification service is not available",
        )
    except Exception as e:
        logger.error("[%s] Notification failed: %s", request_id, str(e))
        if settings.is_demo:
            logger.warning("[%s] Falling back to demo notification", request_id)
            return _demo_notification(request, notification_id, request_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Notification delivery failed: {str(e)}",
        )


def _demo_notification(
    request: NotifyVendorRequest,
    notification_id: str,
    request_id: str,
) -> NotifyVendorResponse:
    """Return a mock notification response for demo mode."""
    logger.info(
        "[%s] DEMO notification: channel=%s, phone=%s",
        request_id,
        request.channel,
        request.user_phone[:6] + "****",
    )

    return NotifyVendorResponse(
        status="sent_demo",
        notification_id=notification_id,
        channel=request.channel,
        message=f"[DEMO] Notification would be sent via {request.channel} to {request.user_phone}",
    )
