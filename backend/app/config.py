"""
Krishi-Sarthi Configuration
Loads all settings from environment variables with sensible defaults.
"""

from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    # ── Core ──────────────────────────────────────────────
    app_name: str = "Krishi-Sarthi"
    environment: str = "development"
    debug: bool = True
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    secret_key: str = "change-me"
    api_key: str = "krishi-sarthi-api-key-change-this"
    log_level: str = "INFO"

    # ── Database ──────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./krishi.db"

    # ── Redis ─────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── OpenAI ────────────────────────────────────────────
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"
    whisper_model: str = "whisper-1"

    # ── Grok (xAI) ────────────────────────────────────────
    grok_api_key: str = ""
    grok_base_url: str = "https://api.x.ai/v1"
    grok_model: str = "grok-2-latest"

    # ── Google Maps ───────────────────────────────────────
    google_maps_api_key: str = ""
    google_maps_base_url: str = "https://maps.googleapis.com/maps/api"

    # ── Twilio ────────────────────────────────────────────
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    # ── n8n ───────────────────────────────────────────────
    n8n_base_url: str = "http://localhost:5678"
    n8n_vendor_enrichment_webhook: str = "/webhook/vendor-enrichment"
    n8n_notification_webhook: str = "/webhook/send-notification"
    n8n_escalation_webhook: str = "/webhook/escalation"
    n8n_retraining_webhook: str = "/webhook/retraining-trigger"

    # ── AI Models ─────────────────────────────────────────
    # ── AI Models ─────────────────────────────────────────
    classifier_model_path: str = str(Path(__file__).parent.parent.parent / "ai-service/models/classifier.pth")
    faiss_index_path: str = str(Path(__file__).parent.parent.parent / "ai-service/models/faiss_index")
    class_labels_path: str = str(Path(__file__).parent.parent.parent / "ai-service/class_labels.json")

    # ── Uploads ───────────────────────────────────────────
    upload_dir: str = "uploads"
    max_upload_size: int = 10_485_760  # 10 MB

    # ── Security ──────────────────────────────────────────
    rate_limit_per_minute: int = 100
    allowed_origins: str = "http://localhost:3000,http://localhost:5173"

    # ── Demo Mode ─────────────────────────────────────────
    demo_mode: bool = True
    mock_ai_responses: bool = True
    mock_vendor_data: bool = True

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def is_demo(self) -> bool:
        return self.demo_mode

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
