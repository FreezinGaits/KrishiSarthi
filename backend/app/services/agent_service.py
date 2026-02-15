"""
Agentic AI Orchestration Service — LangChain Agent

The central intelligence of Krishi-Sarthi. Orchestrates all services into
a unified conversational agent that:

1. Detects farmer intent (disease diagnosis, vendor search, knowledge query)
2. Calls appropriate tools (classifier, vendor finder, RAG, whisper)
3. Synthesizes structured responses in Hindi or English
4. Maintains session context

Uses LangChain with OpenAI GPT-4 when available.
Falls back to a rule-based orchestrator in DEMO_MODE.
"""

from __future__ import annotations

import base64
import json
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.config import get_settings
from app.models.schemas import (
    ChatResponse,
    DiagnoseImageResponse,
    VendorSearchResponse,
)
from app.utils.logger import get_logger

logger = get_logger("service.agent")
settings = get_settings()

# ── Intent detection keywords ─────────────────────
INTENT_KEYWORDS = {
    "disease_diagnosis": {
        "hi": ["rog", "bimari", "dhabbe", "spots", "kale", "peeli", "safed", "jhulsa",
               "geeli", "sadi", "keede", "keet", "pest", "makdi", "spider", "patti",
               "leaf", "phool", "flower", "phal", "fruit", "sukh", "dry", "murg", "wilt",
               "diagnos", "jaanch", "pahchan", "identify", "kya hua", "kya bimari"],
        "en": ["disease", "blight", "rust", "mold", "spots", "fungus", "wilt", "rot",
               "lesion", "infection", "pest", "insect", "diagnose", "identify", "what is wrong"],
    },
    "vendor_search": {
        "hi": ["dukaan", "shop", "kharidna", "buy", "price", "keemat", "nazdiki", "nearest",
               "store", "kendra", "vendor", "dealer", "dawai", "medicine", "keetnashak",
               "pesticide", "khaad", "fertilizer", "beej", "seed"],
        "en": ["shop", "store", "buy", "purchase", "vendor", "dealer", "nearest", "nearby",
               "price", "cost", "where to buy", "pesticide shop", "fertilizer"],
    },
    "treatment_advice": {
        "hi": ["ilaaj", "upay", "treatment", "dawai", "spray", "chidkav", "kaise",
               "kya karu", "solution", "remedy", "bachav", "prevention", "rokne"],
        "en": ["treatment", "cure", "remedy", "how to", "what to do", "spray", "apply",
               "solution", "prevent", "manage", "control"],
    },
    "greeting": {
        "hi": ["namaste", "namaskar", "hello", "hi", "kaise", "madad", "sahayata",
               "help", "shuruaat", "start"],
        "en": ["hello", "hi", "hey", "namaste", "help", "start", "begin"],
    },
}


def _detect_intent(message: str, has_image: bool = False) -> str:
    """
    Detect the farmer's intent from their message.
    Priority: image → disease, then keyword matching.
    """
    if has_image:
        return "disease_diagnosis"

    msg_lower = message.lower()

    scores = {}
    for intent, lang_keywords in INTENT_KEYWORDS.items():
        score = 0
        for lang, keywords in lang_keywords.items():
            for kw in keywords:
                if kw in msg_lower:
                    score += 1
        scores[intent] = score

    if not any(scores.values()):
        return "general_question"

    return max(scores, key=scores.get)


def _detect_crop_from_text(message: str) -> Optional[str]:
    """Extract crop name from the message for context-aware responses."""
    msg_lower = message.lower()
    crop_map = {
        "tomato": "tomato", "tamatar": "tomato", "टमाटर": "tomato",
        "wheat": "wheat", "gehu": "wheat", "गेहूं": "wheat", "gehun": "wheat",
        "rice": "rice", "chawal": "rice", "dhaan": "rice", "चावल": "rice",
        "potato": "potato", "aloo": "potato", "आलू": "potato",
        "corn": "corn", "maize": "corn", "makka": "corn", "मक्का": "corn",
        "sarson": "mustard", "mustard": "mustard", "सरसों": "mustard",
        "cotton": "cotton", "kapas": "cotton", "कपास": "cotton",
        "sugarcane": "sugarcane", "ganna": "sugarcane", "गन्ना": "sugarcane",
    }
    for keyword, crop in crop_map.items():
        if keyword in msg_lower:
            return crop
    return None


async def _run_langchain_agent(
    message: str,
    session_id: str,
    image_base64: Optional[str],
    latitude: Optional[float],
    longitude: Optional[float],
    language: str,
    request_id: str,
) -> ChatResponse:
    """
    Run the LangChain agent with tools for disease diagnosis,
    vendor search, and knowledge retrieval.
    """
    from langchain_openai import ChatOpenAI
    from langchain.agents import AgentExecutor, create_openai_tools_agent
    from langchain.tools import Tool
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

    # ── Define tools ──────────────────────────────
    tools = []

    # Tool: Diagnose crop disease
    async def _tool_diagnose(query: str) -> str:
        """Diagnose a crop disease from the uploaded image."""
        if not image_base64:
            return "No image was uploaded. Ask the farmer to upload a photo of the affected plant."
        try:
            from app.services.classifier_service import classify_image
            img_bytes = base64.b64decode(image_base64)
            result = await classify_image(img_bytes, filename="upload.jpg", request_id=request_id)
            return json.dumps({
                "disease": result.top_disease,
                "confidence": result.top_confidence,
                "treatment": result.treatment,
                "pesticide": result.pesticide,
            }, ensure_ascii=False)
        except Exception as e:
            return f"Diagnosis error: {str(e)}"

    tools.append(Tool(
        name="diagnose_crop",
        func=lambda q: None,  # Sync placeholder
        coroutine=_tool_diagnose,
        description="Diagnose crop disease from an uploaded image. Returns disease name, confidence, treatment, and pesticide.",
    ))

    # Tool: Find vendors
    async def _tool_vendors(query: str) -> str:
        """Find nearby agricultural supply vendors."""
        if not latitude or not longitude:
            return "Location not provided. Ask the farmer to share their location."
        try:
            from app.services.vendor_service import search_vendors
            result = await search_vendors(
                latitude=latitude, longitude=longitude,
                query=query or "pesticide shop", radius_km=10.0,
                request_id=request_id,
            )
            vendors_list = [
                {"name": v.name, "distance_km": v.distance_km, "phone": v.phone, "address": v.address}
                for v in result.vendors[:5]
            ]
            return json.dumps(vendors_list, ensure_ascii=False)
        except Exception as e:
            return f"Vendor search error: {str(e)}"

    tools.append(Tool(
        name="find_vendors",
        func=lambda q: None,
        coroutine=_tool_vendors,
        description="Find nearby pesticide shops and agricultural supply vendors. Input: search query (e.g., 'pesticide shop', 'fertilizer').",
    ))

    # Tool: Search knowledge
    async def _tool_knowledge(query: str) -> str:
        """Search agricultural knowledge base."""
        try:
            from app.services.rag_service import search_knowledge
            results = await search_knowledge(query=query, top_k=3, request_id=request_id)
            docs = [{"title": r.title, "content": r.content[:500]} for r in results]
            return json.dumps(docs, ensure_ascii=False)
        except Exception as e:
            return f"Knowledge search error: {str(e)}"

    tools.append(Tool(
        name="search_knowledge",
        func=lambda q: None,
        coroutine=_tool_knowledge,
        description="Search the agricultural knowledge base for disease info, treatments, pesticide guidance, and agronomic advice.",
    ))

    # ── Build agent prompt ────────────────────────
    system_prompt = """You are Krishi-Sarthi (कृषि-सारथी), an AI agricultural assistant for Indian farmers.

YOUR ROLE:
- Help farmers diagnose crop diseases from images
- Recommend treatments and pesticides with exact dosages
- Find nearby agricultural supply vendors
- Answer farming questions about soil, water, and crop management

CRITICAL RULES:
1. If the farmer sends an image, ALWAYS use the diagnose_crop tool first
2. If the farmer asks about nearby shops/vendors, ALWAYS use find_vendors tool
3. For disease and treatment questions, use search_knowledge tool
4. NEVER hallucinate vendor data — only use find_vendors tool results
5. Always provide specific, actionable advice with dosages
6. Mention the specific pesticide product name and application rate

LANGUAGE:
- If the farmer speaks in Hindi/Hinglish, respond in Hindi (Devanagari + Roman)
- If in English, respond in English
- Current farmer language: {language}

RESPONSE FORMAT:
- Use bullet points for treatments
- Include pesticide name, dosage, and application method
- If you found vendors, include their name, distance, and phone number
- Add a brief prevention tip at the end

Be empathetic, supportive, and practical. Remember: many farmers have limited formal education."""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])

    # ── Create agent ──────────────────────────────
    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.3,
        max_tokens=1500,
    )

    agent = create_openai_tools_agent(llm, tools, prompt)
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=settings.debug,
        max_iterations=5,
        return_intermediate_steps=True,
        handle_parsing_errors=True,
    )

    # ── Run agent ─────────────────────────────────
    result = await executor.ainvoke({
        "input": message,
        "language": language,
        "chat_history": [],
    })

    reply = result.get("output", "I could not process your request. Please try again.")

    # ── Extract structured data from intermediate steps ─
    diagnosis_data = None
    vendor_data = None
    sources = []

    for step in result.get("intermediate_steps", []):
        action, output = step
        tool_name = action.tool if hasattr(action, 'tool') else ""

        if tool_name == "diagnose_crop" and output:
            try:
                parsed = json.loads(output) if isinstance(output, str) else output
                from app.services.classifier_service import DISEASE_DATABASE
                diagnosis_data = DiagnoseImageResponse(
                    predictions=[],
                    top_disease=parsed.get("disease", "Unknown"),
                    top_confidence=parsed.get("confidence", 0.0),
                    treatment=parsed.get("treatment", ""),
                    pesticide=parsed.get("pesticide", ""),
                    model_version="v1.0",
                )
            except Exception:
                pass

        elif tool_name == "find_vendors" and output:
            try:
                parsed = json.loads(output) if isinstance(output, str) else output
                from app.models.schemas import VendorResult
                vendor_results = [VendorResult(**v) for v in parsed] if isinstance(parsed, list) else []
                vendor_data = VendorSearchResponse(
                    vendors=vendor_results,
                    total=len(vendor_results),
                    search_radius_km=10.0,
                    source="agent",
                )
            except Exception:
                pass

        elif tool_name == "search_knowledge" and output:
            try:
                parsed = json.loads(output) if isinstance(output, str) else output
                if isinstance(parsed, list):
                    sources.extend(d.get("title", "") for d in parsed)
            except Exception:
                pass

    # ── Trigger n8n automation based on diagnosis confidence ─
    await _trigger_n8n_automations(diagnosis_data, latitude, longitude, request_id)

    return ChatResponse(
        reply=reply,
        session_id=session_id,
        diagnosis=diagnosis_data,
        vendors=vendor_data,
        sources=sources,
        language=language,
    )


async def _run_rule_based_agent(
    message: str,
    session_id: str,
    image_base64: Optional[str],
    latitude: Optional[float],
    longitude: Optional[float],
    language: str,
    request_id: str,
) -> ChatResponse:
    """
    Rule-based orchestrator for DEMO_MODE.
    Detects intent, calls services, and assembles a structured response
    without requiring OpenAI API.
    """
    intent = _detect_intent(message, has_image=bool(image_base64))
    crop = _detect_crop_from_text(message)
    logger.info("[%s] DEMO agent: intent=%s, crop=%s", request_id, intent, crop)

    diagnosis_data = None
    vendor_data = None
    sources: List[str] = []
    reply_parts: List[str] = []

    # ── Handle disease diagnosis ──────────────────
    if intent == "disease_diagnosis":
        try:
            from app.services.classifier_service import classify_image

            if image_base64:
                img_bytes = base64.b64decode(image_base64)
                diagnosis_data = await classify_image(img_bytes, filename=f"{crop or 'crop'}_leaf.jpg", request_id=request_id)
            else:
                # No image but disease-related query — use crop hint
                diagnosis_data = await classify_image(b"demo", filename=f"{crop or 'tomato'}_leaf.jpg", request_id=request_id)

            reply_parts.append(
                f"🌿 **जांच परिणाम / Diagnosis Result:**\n"
                f"• **रोग / Disease:** {diagnosis_data.top_disease}\n"
                f"• **विश्वास / Confidence:** {diagnosis_data.top_confidence:.0%}\n\n"
                f"**उपचार / Treatment:**\n{diagnosis_data.treatment}\n\n"
                f"**अनुशंसित कीटनाशक / Recommended Pesticide:** {diagnosis_data.pesticide}"
            )
        except Exception as e:
            logger.error("[%s] Classifier failed: %s", request_id, str(e))
            reply_parts.append("❌ रोग की पहचान में समस्या हुई। कृपया फिर से कोशिश करें।")

    # ── Handle treatment queries ──────────────────
    if intent in ("disease_diagnosis", "treatment_advice"):
        try:
            from app.services.rag_service import search_knowledge
            knowledge_results = await search_knowledge(query=message, top_k=2, request_id=request_id)

            if knowledge_results and knowledge_results[0].relevance_score > 0.1:
                top_result = knowledge_results[0]
                sources.append(top_result.title)

                if intent != "disease_diagnosis":  # Avoid duplicate info
                    reply_parts.append(
                        f"\n📚 **{top_result.title}:**\n{top_result.content}"
                    )
                elif len(knowledge_results) > 1:
                    second = knowledge_results[1]
                    sources.append(second.title)
                    reply_parts.append(
                        f"\n📚 **अतिरिक्त जानकारी / Additional Info:**\n"
                        f"*{second.title}*\n{second.content[:300]}..."
                    )
        except Exception as e:
            logger.error("[%s] RAG search failed: %s", request_id, str(e))

    # ── Handle vendor search ──────────────────────
    if intent == "vendor_search" or (intent == "disease_diagnosis" and latitude and longitude):
        try:
            from app.services.vendor_service import search_vendors
            lat = latitude or 30.9  # Default to Ludhiana if no location
            lng = longitude or 75.85

            vendor_data = await search_vendors(
                latitude=lat, longitude=lng,
                query="pesticide agricultural supply",
                radius_km=10.0, request_id=request_id,
            )

            if vendor_data.vendors:
                vendor_text = "\n📍 **नज़दीकी दुकानें / Nearby Shops:**\n"
                for i, v in enumerate(vendor_data.vendors[:3], 1):
                    vendor_text += (
                        f"\n{i}. **{v.name}** — {v.distance_km} km\n"
                        f"   📞 {v.phone or 'N/A'} | ⭐ {v.rating or 'N/A'}\n"
                        f"   📫 {v.address}\n"
                    )
                reply_parts.append(vendor_text)
        except Exception as e:
            logger.error("[%s] Vendor search failed: %s", request_id, str(e))

    # ── Handle greeting ───────────────────────────
    if intent == "greeting" or not reply_parts:
        greeting = (
            "🙏 **नमस्ते! मैं कृषि-सारथी हूँ — आपका AI कृषि सहायक।**\n\n"
            "मैं आपकी मदद कर सकता हूँ:\n"
            "🌱 **फसल रोग पहचान** — फसल की फोटो भेजें\n"
            "🗣️ **आवाज़ में बात करें** — माइक बटन दबाएं\n"
            "💊 **उपचार सलाह** — बताएं कौन सी बीमारी है\n"
            "📍 **नज़दीकी दुकान** — कीटनाशक दुकान ढूंढें\n\n"
            "आप हिंदी या अंग्रेज़ी में बात कर सकते हैं! 🌾"
        )
        if intent == "greeting":
            reply_parts = [greeting]
        else:
            reply_parts.insert(0, greeting)

    reply = "\n\n---\n\n".join(reply_parts)

    # ── Trigger n8n automation based on diagnosis confidence ─
    await _trigger_n8n_automations(diagnosis_data, latitude, longitude, request_id)

    return ChatResponse(
        reply=reply,
        session_id=session_id,
        diagnosis=diagnosis_data,
        vendors=vendor_data,
        sources=sources,
        language=language,
    )


async def _trigger_n8n_automations(
    diagnosis: Optional[DiagnoseImageResponse],
    latitude: Optional[float],
    longitude: Optional[float],
    request_id: str,
) -> None:
    """
    Fire-and-forget n8n automation triggers based on diagnosis confidence.
    - confidence >= 0.65 → notification workflow
    - confidence <  0.65 → escalation workflow
    Never raises — failures are logged and silently ignored.
    """
    if diagnosis is None:
        return

    try:
        from app.services.n8n_service import trigger_notification, trigger_escalation

        payload_meta = {
            "disease_name": diagnosis.top_disease,
            "confidence": diagnosis.top_confidence,
            "treatment": diagnosis.treatment,
            "pesticide": diagnosis.pesticide,
            "location": {"lat": latitude, "lng": longitude},
            "timestamp": datetime.utcnow().isoformat(),
        }

        if diagnosis.top_confidence >= 0.65:
            logger.info("[%s] Confidence %.0f%% >= 65%% → triggering notification workflow",
                        request_id, diagnosis.top_confidence * 100)
            await trigger_notification(
                phone="farmer-phone",  # Populated from session in production
                message=(
                    f"Diagnosis: {diagnosis.top_disease} ({diagnosis.top_confidence:.0%}).\n"
                    f"Treatment: {diagnosis.treatment}\n"
                    f"Pesticide: {diagnosis.pesticide}"
                ),
                channel="sms",
                metadata=payload_meta,
                request_id=request_id,
            )
        else:
            logger.info("[%s] Confidence %.0f%% < 65%% → triggering escalation workflow",
                        request_id, diagnosis.top_confidence * 100)
            await trigger_escalation(
                diagnosis_data=payload_meta,
                confidence=diagnosis.top_confidence,
                request_id=request_id,
            )
    except Exception as e:
        # Never let n8n failures break the main agent flow
        logger.warning("[%s] n8n automation trigger failed (non-fatal): %s", request_id, str(e))


async def run_agent(
    message: str,
    session_id: str = "",
    image_base64: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    language: str = "hi",
    request_id: str = "",
) -> ChatResponse:
    """
    Main entry point for the agentic AI.

    Strategy:
    1. If OpenAI available and not DEMO_MODE → full LangChain agent
    2. Otherwise → rule-based orchestrator with service calls

    Both paths call the same underlying services (classifier, vendor, RAG).

    Args:
        message: Farmer's text message
        session_id: Conversation session ID (for context)
        image_base64: Optional base64-encoded crop image
        latitude: User's latitude for vendor search
        longitude: User's longitude for vendor search
        language: User's language ("hi" or "en")
        request_id: Request tracking ID

    Returns:
        ChatResponse with reply, optional diagnosis, vendors, sources
    """
    if not session_id:
        session_id = str(uuid.uuid4())

    logger.info(
        "[%s] Agent invoked: session=%s, msg='%s', image=%s, loc=(%s,%s), lang=%s",
        request_id, session_id[:8], message[:60],
        "yes" if image_base64 else "no",
        latitude, longitude, language,
    )

    # ── Try LangChain agent ───────────────────────
    if not settings.is_demo and settings.openai_api_key:
        try:
            logger.info("[%s] Using LangChain agent (GPT-4)", request_id)
            return await _run_langchain_agent(
                message=message,
                session_id=session_id,
                image_base64=image_base64,
                latitude=latitude,
                longitude=longitude,
                language=language,
                request_id=request_id,
            )
        except Exception as e:
            logger.error("[%s] LangChain agent failed: %s — falling back to rule-based", request_id, str(e))

    # ── Rule-based orchestrator ───────────────────
    logger.info("[%s] Using rule-based agent (DEMO_MODE=%s)", request_id, settings.is_demo)
    return await _run_rule_based_agent(
        message=message,
        session_id=session_id,
        image_base64=image_base64,
        latitude=latitude,
        longitude=longitude,
        language=language,
        request_id=request_id,
    )
