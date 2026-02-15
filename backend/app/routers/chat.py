"""
Chat / Agent Router — POST /api/chat

Orchestrates the full agentic pipeline: speech transcript + image diagnosis +
vendor search + RAG knowledge lookup via LangChain agent.
Falls back to a structured demo response in DEMO_MODE.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from app.config import get_settings
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    DiagnoseImageResponse,
    DiagnosisPrediction,
    VendorResult,
    VendorSearchResponse,
)
from app.utils.logger import get_logger

logger = get_logger("router.chat")
settings = get_settings()

router = APIRouter(prefix="/api", tags=["Chat"])

# ── Demo fallback responses (Hindi + English mix) ─
DEMO_RESPONSES = {
    "disease": {
        "reply": (
            "🌿 आपकी फसल की जांच के अनुसार, यह **टमाटर का अगेती झुलसा रोग (Early Blight)** "
            "लग रहा है।\n\n"
            "**उपचार:**\n"
            "• मैंकोज़ेब 75% WP — 2.5 ग्राम प्रति लीटर पानी में मिलाकर छिड़काव करें\n"
            "• प्रभावित पत्तियों को तोड़कर नष्ट करें\n"
            "• पौधों के बीच उचित दूरी रखें\n"
            "• जड़ में पानी दें, पत्तियों पर पानी न डालें\n\n"
            "**सबसे नज़दीकी कीटनाशक दुकान:** शर्मा कृषि केंद्र (2.3 km दूर)\n"
            "📞 +91 98765 43210"
        ),
        "diagnosis": DiagnoseImageResponse(
            predictions=[
                DiagnosisPrediction(
                    disease_name="Tomato Early Blight",
                    confidence=0.92,
                    treatment="Apply Mancozeb 75% WP at 2.5g/L. Remove affected leaves.",
                    pesticide="Mancozeb 75% WP",
                ),
                DiagnosisPrediction(
                    disease_name="Tomato Septoria Leaf Spot",
                    confidence=0.65,
                    treatment="Apply chlorothalonil fungicide spray.",
                    pesticide="Chlorothalonil",
                ),
            ],
            top_disease="Tomato Early Blight",
            top_confidence=0.92,
            treatment="Apply Mancozeb 75% WP at 2.5g/L. Remove affected leaves.",
            pesticide="Mancozeb 75% WP",
            model_version="v1.0-demo",
        ),
        "vendors": VendorSearchResponse(
            vendors=[
                VendorResult(name="Sharma Krishi Kendra", address="Main Market, Ludhiana", distance_km=2.3, phone="+91 98765 43210", rating=4.5, lat=30.9010, lng=75.8573),
                VendorResult(name="Punjab Agro Store", address="GT Road, Ludhiana", distance_km=3.8, phone="+91 98123 45678", rating=4.2, lat=30.9110, lng=75.8673),
            ],
            total=2,
            search_radius_km=10.0,
            source="demo",
        ),
        "sources": ["PlantVillage Disease Database", "ICAR Treatment Guidelines"],
    },
    "greeting": {
        "reply": (
            "🙏 नमस्ते! मैं **कृषि-सारथी** हूँ — आपका कृषि सहायक।\n\n"
            "मैं आपकी मदद कर सकता हूँ:\n"
            "🌱 **फसल रोग पहचान** — फसल की फोटो भेजें\n"
            "🗣️ **आवाज़ में बात करें** — माइक बटन दबाएं\n"
            "📍 **नज़दीकी दुकान खोजें** — कीटनाशक दुकान ढूंढें\n\n"
            "आप हिंदी या अंग्रेज़ी में बात कर सकते हैं।"
        ),
    },
    "vendor": {
        "reply": (
            "📍 आपके नज़दीक कीटनाशक दुकानें:\n\n"
            "1. **शर्मा कृषि केंद्र** — 2.3 km\n"
            "   📞 +91 98765 43210 | ⭐ 4.5\n\n"
            "2. **पंजाब एग्रो स्टोर** — 3.8 km\n"
            "   📞 +91 98123 45678 | ⭐ 4.2\n\n"
            "3. **किसान सेवा केंद्र** — 5.1 km\n"
            "   📞 +91 94170 12345 | ⭐ 4.7"
        ),
        "vendors": VendorSearchResponse(
            vendors=[
                VendorResult(name="Sharma Krishi Kendra", address="Main Market, Ludhiana", distance_km=2.3, phone="+91 98765 43210", rating=4.5, lat=30.9010, lng=75.8573),
                VendorResult(name="Punjab Agro Store", address="GT Road, Ludhiana", distance_km=3.8, phone="+91 98123 45678", rating=4.2, lat=30.9110, lng=75.8673),
                VendorResult(name="Kisan Sewa Kendra", address="Gill Road, Ludhiana", distance_km=5.1, phone="+91 94170 12345", rating=4.7, lat=30.8810, lng=75.8373),
            ],
            total=3,
            search_radius_km=10.0,
            source="demo",
        ),
    },
}

# Keywords for intent detection in demo mode
DISEASE_KEYWORDS = ["rog", "bimari", "disease", "dhabbe", "spots", "peeli", "yellow", "kale", "black", "keede", "keet", "pest", "diagnos", "fasal", "crop", "patti", "leaf"]
VENDOR_KEYWORDS = ["dukaan", "shop", "vendor", "kharidna", "buy", "price", "keemat", "nazdiki", "near", "store", "kendra"]
GREETING_KEYWORDS = ["namaste", "hello", "hi", "namaskar", "kaise", "how", "help", "madad", "sahayata"]


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Chat with Krishi-Sarthi AI agent",
    description="Send a message (with optional image) to the agentic AI. Returns structured advice.",
)
async def chat(request: ChatRequest):
    """
    Main chat endpoint — the agentic orchestrator.

    1. Assigns/reuses session ID
    2. Detects intent from message
    3. Orchestrates tools (diagnosis, vendor search, RAG)
    4. Returns structured response with optional diagnosis/vendor data
    """
    session_id = request.session_id or str(uuid.uuid4())
    request_id = str(uuid.uuid4())[:8]

    logger.info(
        "[%s] Chat request: session=%s, message='%s', has_image=%s, lang=%s",
        request_id,
        session_id[:8],
        request.message[:80],
        bool(request.image_base64),
        request.language,
    )

    # ── Run agent ─────────────────────────────────
    try:
        from app.services.agent_service import run_agent
        result = await run_agent(
            message=request.message,
            session_id=session_id,
            image_base64=request.image_base64,
            latitude=request.latitude,
            longitude=request.longitude,
            language=request.language,
            request_id=request_id,
        )
        logger.info("[%s] Agent response generated", request_id)
        return result

    except ImportError:
        if settings.is_demo:
            logger.warning("[%s] Agent service not available, using demo fallback", request_id)
            return _demo_chat(request, session_id, request_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI agent service is not available",
        )
    except Exception as e:
        logger.error("[%s] Agent failed: %s", request_id, str(e))
        if settings.is_demo:
            logger.warning("[%s] Falling back to demo chat", request_id)
            return _demo_chat(request, session_id, request_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent processing failed: {str(e)}",
        )


def _detect_intent(message: str, has_image: bool) -> str:
    """Simple keyword-based intent detection for demo mode."""
    msg_lower = message.lower()

    if has_image or any(kw in msg_lower for kw in DISEASE_KEYWORDS):
        return "disease"
    if any(kw in msg_lower for kw in VENDOR_KEYWORDS):
        return "vendor"
    if any(kw in msg_lower for kw in GREETING_KEYWORDS):
        return "greeting"

    # Default to disease advice (most likely farmer query)
    return "disease"


def _demo_chat(request: ChatRequest, session_id: str, request_id: str) -> ChatResponse:
    """Generate a demo chat response based on intent detection."""
    intent = _detect_intent(request.message, bool(request.image_base64))
    demo = DEMO_RESPONSES.get(intent, DEMO_RESPONSES["greeting"])

    logger.info("[%s] DEMO chat: intent=%s", request_id, intent)

    return ChatResponse(
        reply=demo.get("reply", DEMO_RESPONSES["greeting"]["reply"]),
        session_id=session_id,
        diagnosis=demo.get("diagnosis"),
        vendors=demo.get("vendors"),
        sources=demo.get("sources", []),
        language=request.language,
    )
