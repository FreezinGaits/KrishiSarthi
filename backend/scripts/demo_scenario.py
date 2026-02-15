"""
Demo Scenario Runner — Simulate a complete farmer interaction flow.

Demonstrates the full pipeline:
  Voice → Whisper → Agent → Classifier + RAG + Vendors → n8n Notification

Run with: python -m scripts.demo_scenario
"""

import asyncio
import base64
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")


def print_section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_json(data, indent=2):
    if hasattr(data, "model_dump"):
        data = data.model_dump()
    elif hasattr(data, "dict"):
        data = data.dict()
    print(json.dumps(data, indent=indent, ensure_ascii=False, default=str))


async def run_scenario():
    from app.config import get_settings
    settings = get_settings()

    print(r"""
    ╔══════════════════════════════════════════════════╗
    ║   🎬  KRISHI-SARTHI DEMO SCENARIO RUNNER        ║
    ║       Full Pipeline Simulation                   ║
    ╚══════════════════════════════════════════════════╝
    """)
    print(f"  Demo Mode: {'✅ ON' if settings.is_demo else '❌ OFF'}")
    print(f"  Mock AI:   {'✅ ON' if settings.mock_ai_responses else '❌ OFF'}")

    # ─────────────────────────────────────────────
    # STEP 1: Farmer Voice Input → Whisper STT
    # ─────────────────────────────────────────────
    print_section("STEP 1: 🎤 Voice Input → Whisper STT")
    try:
        from app.services.whisper_service import transcribe_audio

        # Simulate audio data (demo will return mock transcript)
        result = await transcribe_audio(
            audio_data=b"mock_audio_data_for_demo",
            filename="farmer_query.wav",
            request_id="demo-001",
        )
        transcript = result.get("transcript", result.get("text", ""))
        language = result.get("detected_language", "hi")
        confidence = result.get("confidence", 0.9)

        print(f"  📝 Transcript: \"{transcript}\"")
        print(f"  🌐 Language:   {language}")
        print(f"  📊 Confidence: {confidence:.0%}")

    except Exception as e:
        print(f"  ⚠️  Whisper fallback: {e}")
        transcript = "Mere tamatar ki patti par kale dhabbe hain, kya karu?"
        language = "hi"
        print(f"  📝 Using default: \"{transcript}\"")

    # ─────────────────────────────────────────────
    # STEP 2: Image Diagnosis → Classifier
    # ─────────────────────────────────────────────
    print_section("STEP 2: 📷 Image Diagnosis → Classifier")
    try:
        from app.services.classifier_service import classify_image

        result = await classify_image(
            image_data=b"demo_image_bytes",
            filename="tomato_leaf_disease.jpg",
            request_id="demo-002",
        )

        print(f"  🔬 Disease:    {result.top_disease}")
        print(f"  📊 Confidence: {result.top_confidence:.0%}")
        print(f"  💊 Treatment:  {result.treatment[:80]}...")
        print(f"  🧪 Pesticide:  {result.pesticide}")

        if result.predictions:
            print(f"\n  Top predictions:")
            for i, p in enumerate(result.predictions[:3], 1):
                print(f"    {i}. {p.disease_name} ({p.confidence:.0%})")

        diagnosis_result = result

    except Exception as e:
        print(f"  ⚠️  Classifier error: {e}")
        diagnosis_result = None

    # ─────────────────────────────────────────────
    # STEP 3: RAG Knowledge Retrieval
    # ─────────────────────────────────────────────
    print_section("STEP 3: 📚 RAG Knowledge Retrieval")
    try:
        from app.services.rag_service import search_knowledge

        results = await search_knowledge(
            query=transcript,
            top_k=3,
            request_id="demo-003",
        )

        for i, r in enumerate(results, 1):
            print(f"\n  📖 Result {i}: {r.title}")
            print(f"     Relevance: {r.relevance_score:.2f} | Source: {r.source}")
            content_preview = r.content[:120].replace("\n", " ")
            print(f"     Preview: {content_preview}...")

    except Exception as e:
        print(f"  ⚠️  RAG error: {e}")

    # ─────────────────────────────────────────────
    # STEP 4: Vendor Search (Ludhiana)
    # ─────────────────────────────────────────────
    print_section("STEP 4: 📍 Vendor Search (Ludhiana)")
    try:
        from app.services.vendor_service import search_vendors

        vendor_result = await search_vendors(
            latitude=30.9,
            longitude=75.85,
            query="pesticide agricultural supply",
            radius_km=10.0,
            request_id="demo-004",
        )

        print(f"  Found {vendor_result.total} vendors within 10km:\n")
        for i, v in enumerate(vendor_result.vendors[:5], 1):
            print(f"  {i}. {v.name}")
            print(f"     📫 {v.address}")
            print(f"     📞 {v.phone or 'N/A'} | ⭐ {v.rating or 'N/A'} | 📍 {v.distance_km} km")

    except Exception as e:
        print(f"  ⚠️  Vendor search error: {e}")

    # ─────────────────────────────────────────────
    # STEP 5: Full Agent Orchestration
    # ─────────────────────────────────────────────
    print_section("STEP 5: 🤖 Full Agent Orchestration")
    try:
        from app.services.agent_service import run_agent

        start_t = time.time()
        agent_response = await run_agent(
            message=transcript,
            session_id="demo-session-001",
            image_base64=base64.b64encode(b"demo_image").decode(),
            latitude=30.9,
            longitude=75.85,
            language=language,
            request_id="demo-005",
        )
        elapsed = time.time() - start_t

        print(f"  ⏱️  Response time: {elapsed:.1f}s")
        print(f"  🗣️  Language: {agent_response.language}")
        print(f"\n  📬 Agent Reply:")
        print(f"  {'─'*50}")
        for line in agent_response.reply.split("\n"):
            print(f"  {line}")
        print(f"  {'─'*50}")

        if agent_response.diagnosis:
            print(f"\n  🔬 Diagnosis attached: {agent_response.diagnosis.top_disease}")

        if agent_response.vendors:
            print(f"  📍 Vendors attached: {agent_response.vendors.total} found")

        if agent_response.sources:
            print(f"  📚 Sources: {', '.join(agent_response.sources)}")

    except Exception as e:
        print(f"  ⚠️  Agent error: {e}")

    # ─────────────────────────────────────────────
    # STEP 6: n8n Notification Trigger
    # ─────────────────────────────────────────────
    print_section("STEP 6: 🔔 n8n Notification Trigger")
    try:
        from app.services.n8n_service import trigger_notification

        notif_result = await trigger_notification(
            phone="+91 98765 43210",
            message="आपकी फसल में टमाटर अगेती झुलसा रोग पाया गया। Mancozeb 75% WP से छिड़काव करें।",
            channel="sms",
            metadata={
                "disease": diagnosis_result.top_disease if diagnosis_result else "Unknown",
                "confidence": diagnosis_result.top_confidence if diagnosis_result else 0,
                "farmer_location": {"lat": 30.9, "lng": 75.85},
            },
        )

        print(f"  📤 Notification triggered:")
        print(f"     Status: {notif_result.get('status', 'unknown')}")
        print(f"     Channel: sms")
        print(f"     To: +91 98765 43210")

    except Exception as e:
        print(f"  ⚠️  n8n notification error: {e}")

    # ─────────────────────────────────────────────
    # Summary
    # ─────────────────────────────────────────────
    print_section("🏆 DEMO SCENARIO COMPLETE")
    print("""
  Complete farmer journey simulated:

    🎤  Voice Input  →  Whisper STT  →  Hindi transcript
    📷  Crop Image   →  Classifier   →  Disease diagnosis
    📚  Knowledge    →  RAG Search   →  Treatment details
    📍  Location     →  Vendor API   →  Nearby shops
    🤖  Agent        →  Orchestrator →  Structured response
    🔔  Notification →  n8n Webhook  →  SMS to farmer

  ✅ System is hackathon-ready!
    """)


if __name__ == "__main__":
    asyncio.run(run_scenario())
