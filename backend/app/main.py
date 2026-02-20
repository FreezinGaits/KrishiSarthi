"""
Krishi-Sarthi FastAPI Application Entry Point.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.middleware import register_middleware
from app.models.database import close_db, init_db
from app.models.schemas import HealthResponse
from app.utils.logger import get_logger

logger = get_logger("main")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("Starting %s (env=%s, demo=%s)", settings.app_name, settings.environment, settings.is_demo)

    # Ensure upload directory exists
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)

    # Initialize database tables
    await init_db()
    logger.info("Database initialized")

    yield

    # Shutdown
    await close_db()
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.app_name,
    description="Vernacular Agentic AI Assistant for Farmers",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Custom Middleware ─────────────────────────────
register_middleware(app)

# ── Routers ───────────────────────────────────────
from app.routers import speech, diagnosis, vendors, chat, notifications, health, marketplace  # noqa: E402

app.include_router(speech.router)
app.include_router(diagnosis.router)
app.include_router(vendors.router)
app.include_router(chat.router)
app.include_router(notifications.router)
app.include_router(health.router)
app.include_router(marketplace.router)


# ── Health Check ──────────────────────────────────
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    return HealthResponse(
        status="healthy",
        app_name=settings.app_name,
        demo_mode=settings.is_demo,
    )


@app.get("/", tags=["Health"])
async def root():
    return {
        "app": settings.app_name,
        "status": "running",
        "docs": "/docs",
        "demo_mode": settings.is_demo,
    }
