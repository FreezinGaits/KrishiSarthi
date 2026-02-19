# D:\Code Playground\KrishiSarthi\backend\app\services\agent_service.py
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
from app.services.llm_service import generate_llm_response, _build_llm

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
        "hi": ["namaste", "namaskar", "hello", "hi", "madad", "sahayata",
               "shuruaat", "start"],
        "en": ["hello", "hi", "hey", "namaste", "start", "begin"],
    },
    "identity": {
        "hi": ["kaun ho", "tumhara naam", "kya karte ho", "krishi sarthi", "antigravity"],
        "en": ["who are you", "your name", "what do you do", "krishi sarthi", "antigravity"],
    },
    "small_talk": {
        "hi": ["kaise ho", "kaisa hai", "thik ho", "good morning", "shubh prabhat", "dhanyavad", "shukriya"],
        "en": ["how are you", "doing well", "good morning", "good evening", "thank", "thanks"],
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

    # If crop mentioned + disease-like words, treat as disease
    msg_lower = message.lower()

    disease_words = [
        "yellow", "curl", "curling", "spots", "lesions",
        "wilt", "rot", "blight", "rust", "mold",
        "dry", "dying", "infection"
    ]

    if any(word in msg_lower for word in disease_words):
        return "disease_diagnosis"

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
        "strawberry": "strawberry",
        "berries": "strawberry",
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
    chat_history: Optional[List[Dict[str, str]]] = None,
) -> ChatResponse:
    """
    Run the LangChain agent with tools for disease diagnosis,
    vendor search, and knowledge retrieval.
    """
    if chat_history is None:
        chat_history = []
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

    async def _tool_knowledge(query: str) -> str:
        """Search agricultural knowledge base using RAG."""
        try:
            from app.services.rag_service import query_rag
            # Format history for RAG (role: content strings)
            history_strs = [f"{m.get('role')}: {m.get('content')}" for m in chat_history] if chat_history else []
            return await query_rag(query, request_id=request_id, chat_history=history_strs)
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
    # ── Create agent ──────────────────────────────
    # Use our llm_service to pick Groq or OpenAI
    from app.services.llm_service import _build_llm
    llm = _build_llm()


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
    # ── Run agent ─────────────────────────────────
    # Convert history to LangChain format
    from langchain_core.messages import HumanMessage, AIMessage
    lc_history = []
    for msg in chat_history:
        if msg.get("role") == "user":
            lc_history.append(HumanMessage(content=msg.get("content", "")))
        elif msg.get("role") == "assistant":
            lc_history.append(AIMessage(content=msg.get("content", "")))

    result = await executor.ainvoke({
        "input": message,
        "language": language,
        "chat_history": lc_history,
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
    chat_history: Optional[List[Dict[str, str]]] = None,
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
    # ── Handle disease diagnosis ONLY if image exists ──────────────────
    if intent == "disease_diagnosis" and image_base64:

        try:

            from app.services.classifier_service import classify_image

            img_bytes = base64.b64decode(image_base64)

            # Call classifier service for real (do not fabricate demo data)
            try:
                diagnosis_data = await classify_image(
                    img_bytes,
                    filename=f"{crop or 'crop'}_leaf.jpg",
                    request_id=request_id
                )
            except Exception as e:
                logger.error("[%s] classify_image failed: %s", request_id, str(e))
                diagnosis_data = None

            if diagnosis_data:
                reply_parts.append(
                    f"🌿 **जांच परिणाम / Diagnosis Result:**\n"
                    f"• **रोग / Disease:** {diagnosis_data.top_disease}\n"
                    f"• **विश्वास / Confidence:** {diagnosis_data.top_confidence:.0%}\n\n"
                    f"**उपचार / Treatment:**\n{diagnosis_data.treatment}\n\n"
                    f"**अनुशंसित कीटनाशक / Recommended Pesticide:** {diagnosis_data.pesticide}"
                )
            else:
                reply_parts.append("❌ रोग की पहचान में समस्या हुई। कृपया फिर से फोटो भेजें।")


        except Exception as e:

            logger.error("[%s] Classifier failed: %s", request_id, str(e))

            reply_parts.append("❌ रोग की पहचान में समस्या हुई। कृपया फिर से कोशिश करें।")


    # ── Handle general questions (fallback to RAG) ──
    # ── Handle ALL text questions using RAG ──
    if diagnosis_data is None and intent not in ["greeting", "identity", "small_talk"]:


        try:
            from app.services.rag_service import query_rag
            # Use the full message as query
            query = message
            if crop and crop not in query.lower():
                query = f"{crop} {query}"
            
            # Use RAG Chain to get grounded answer
            # Format history for RAG
            history_strs = [f"{m.get('role')}: {m.get('content')}" for m in chat_history] if chat_history else []
            rag_response = await query_rag(query, request_id=request_id, chat_history=history_strs)
            reply_parts.append(f"📚 **जानकारी / Information:**\n{rag_response}")

        except Exception as e:
            logger.error("[%s] RAG search failed: %s", request_id, str(e))

    # ── Handle vendor search ──────────────────────
    if intent == "vendor_search":
        if not latitude or not longitude:
            reply_parts.append(
                "📍 कृपया अपनी लोकेशन शेयर करें ताकि मैं नज़दीकी दुकानें खोज सकूँ।\n"
                "Please share your location to find nearby shops."
            )
        else:
            try:
                from app.services.vendor_service import search_vendors
                v_result = await search_vendors(
                    latitude=latitude, longitude=longitude,
                    query="pesticide shop", radius_km=10.0,
                    request_id=request_id
                )
                if v_result.vendors:
                    from app.models.schemas import VendorResult
                    vendor_data = VendorSearchResponse(
                        vendors=[VendorResult(**v.dict()) for v in v_result.vendors[:5]],
                        total=len(v_result.vendors),
                        search_radius_km=10.0,
                        source="rule_based"
                    )
                    reply_parts.append(f"📍 मुझे {len(v_result.vendors)} नज़दीकी दुकानें मिली हैं:")
                    for idx, v in enumerate(v_result.vendors[:3], 1):
                        reply_parts.append(f"{idx}. **{v.name}** ({v.distance_km:.1f} km)\n   📞 {v.phone}")
                else:
                    reply_parts.append("📍 आस-पास कोई दुकान नहीं मिली।")
            except Exception as e:
                logger.error("Vendor search failed: %s", str(e))
                reply_parts.append("Vendor search error.")

    # ── Handle general questions (fallback to RAG) ──
    if intent == "greeting":
        greeting = (
            "🙏 **नमस्ते! मैं कृषि-सारथी हूँ — आपका AI कृषि सहायक।**\n\n"
            "मैं आपकी मदद कर सकता हूँ:\n"
            "🌱 **फसल रोग पहचान** — फसल की फोटो भेजें\n"
            "🗣️ **आवाज़ में बात करें** — माइक बटन दबाएं\n"
            "💊 **उपचार सलाह** — बताएं कौन सी बीमारी है\n"
            "📍 **नज़दीकी दुकान** — कीटनाशक दुकान ढूंढें\n\n"
            "आप हिंदी या अंग्रेज़ी में बात कर सकते हैं! 🌾"
        )
        reply_parts.insert(0, greeting)
    
    # ── Handle identity ───────────────────────────
    if intent == "identity":
        reply_parts.append(
            "मैं **कृषि-सारथी टीम** और **Google DeepMind** द्वारा विकसित एक AI सहायक हूँ।\n"
            "मेरा उद्देश्य आपकी खेती को आसान और लाभदायक बनाना है। 🚜\n\n"
            "I am an AI assistant developed by **Krishi-Sarthi Team** and **Google DeepMind**."
        )

    # ── Handle small talk ─────────────────────────
    if intent == "small_talk":
        reply_parts.append(
            "मैं बिल्कुल ठीक हूँ! पूछने के लिए धन्यवाद। 😊\n"
            "बताइये, आज मैं आपकी खेती में कैसे मदद कर सकता हूँ?\n\n"
            "I am doing great, thanks for asking! How can I help with your crops today?"
        )
    
    # ── Final Fallback ────────────────────────────
    if not reply_parts:
        reply_parts.append(
            "क्षमा करें, मैं समझ नहीं पाया। कृपया फसल की बीमारी, इलाज, या दुकान के बारे में पूछें।\n"
            "Sorry, I didn't understand. Please ask about crop diseases, remedies, or nearby shops."
        )

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
    chat_history: Optional[List[Dict[str, str]]] = None,
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
    
    if chat_history is None:
        chat_history = []

    logger.info(
        "[%s] Agent invoked: session=%s, msg='%s', image=%s, loc=(%s,%s), lang=%s",
        request_id, session_id[:8], message[:60],
        "yes" if image_base64 else "no",
        latitude, longitude, language,
    )

    # ── Try LangChain agent ───────────────────────
    # ── Try LangChain agent ───────────────────────
    if not settings.is_demo and (settings.openai_api_key or settings.grok_api_key):
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
                chat_history=chat_history,
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
        chat_history=chat_history,
    )
