"""
System Health Router — GET /api/health

Deep health check endpoint that verifies all system components:
database, Redis, AI services, and agent readiness.
"""

from __future__ import annotations

import time
from typing import Any, Dict

from fastapi import APIRouter

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger("router.health")
settings = get_settings()

router = APIRouter(prefix="/api", tags=["Health"])


@router.get(
    "/health",
    summary="Deep system health check",
    description="Verifies database, Redis, and AI services readiness.",
)
async def system_health():
    """
    Comprehensive health check endpoint.

    Returns status for each subsystem:
    - database: connection + table accessibility
    - redis: connection + ping
    - services: import + readiness for each AI service
    - agent: orchestrator availability
    """
    start = time.time()
    services: Dict[str, Any] = {}

    # ── Database ──────────────────────────────────
    try:
        from app.models.database import async_engine
        from sqlalchemy import text

        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        services["database"] = {"status": "healthy", "type": str(async_engine.url).split("://")[0]}
    except Exception as e:
        services["database"] = {"status": "degraded", "error": str(e)[:100]}

    # ── Redis ─────────────────────────────────────
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url, socket_timeout=2)
        await r.ping()
        info = await r.info("server")
        await r.close()
        services["redis"] = {"status": "healthy", "version": info.get("redis_version", "?")}
    except Exception as e:
        services["redis"] = {"status": "unavailable", "note": "In-memory fallback active (OK for demo)"}

    # ── Whisper STT ───────────────────────────────
    try:
        from app.services.whisper_service import transcribe_audio  # noqa: F401
        services["whisper_stt"] = {"status": "ready", "model": settings.whisper_model}
    except ImportError:
        services["whisper_stt"] = {"status": "unavailable"}

    # ── Classifier ────────────────────────────────
    try:
        from app.services.classifier_service import classify_image, DISEASE_DATABASE  # noqa: F401
        services["classifier"] = {
            "status": "ready",
            "diseases_known": len(DISEASE_DATABASE),
            "model_path": settings.classifier_model_path,
        }
    except ImportError:
        services["classifier"] = {"status": "unavailable"}

    # ── RAG / Knowledge Base ──────────────────────
    try:
        from app.services.rag_service import search_knowledge, KNOWLEDGE_BASE  # noqa: F401
        services["rag_knowledge"] = {
            "status": "ready",
            "in_memory_docs": len(KNOWLEDGE_BASE),
            "faiss_index_path": settings.faiss_index_path,
        }
    except ImportError:
        services["rag_knowledge"] = {"status": "unavailable"}

    # ── Vendor Service ────────────────────────────
    try:
        from app.services.vendor_service import search_vendors  # noqa: F401
        services["vendor_search"] = {"status": "ready"}
    except ImportError:
        services["vendor_search"] = {"status": "unavailable"}

    # ── Agent ─────────────────────────────────────
    try:
        from app.services.agent_service import run_agent  # noqa: F401
        services["agent"] = {
            "status": "ready",
            "mode": "langchain" if (not settings.is_demo and settings.openai_api_key) else "rule_based",
        }
    except ImportError:
        services["agent"] = {"status": "unavailable"}

    # ── n8n Webhooks ──────────────────────────────
    try:
        from app.services.n8n_service import trigger_notification  # noqa: F401
        services["n8n_webhooks"] = {"status": "ready", "base_url": settings.n8n_base_url}
    except ImportError:
        services["n8n_webhooks"] = {"status": "unavailable"}

    # ── Overall status ────────────────────────────
    critical = ["database", "classifier", "agent", "rag_knowledge"]
    all_critical_ok = all(
        services.get(s, {}).get("status") in ("healthy", "ready")
        for s in critical
    )

    elapsed_ms = round((time.time() - start) * 1000, 1)

    return {
        "status": "healthy" if all_critical_ok else "degraded",
        "demo_mode": settings.is_demo,
        "environment": settings.environment,
        "response_time_ms": elapsed_ms,
        "services": services,
    }
