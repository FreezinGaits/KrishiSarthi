"""
Pydantic request/response schemas for all Krishi-Sarthi API endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ───────────────────────────────────────────────
# Speech-to-Text
# ───────────────────────────────────────────────

class SpeechToTextResponse(BaseModel):
    transcript: str = Field(..., description="Transcribed text from audio")
    language: str = Field("hi", description="Detected language code")
    confidence: float = Field(1.0, description="Transcription confidence 0-1")
    duration_seconds: Optional[float] = Field(None, description="Audio duration")


# ───────────────────────────────────────────────
# Image Diagnosis
# ───────────────────────────────────────────────

class DiagnosisPrediction(BaseModel):
    disease_name: str = Field(..., description="Name of the detected disease")
    confidence: float = Field(..., description="Prediction confidence 0-1")
    treatment: str = Field("", description="Recommended treatment")
    pesticide: str = Field("", description="Recommended pesticide")


class DiagnoseImageResponse(BaseModel):
    predictions: List[DiagnosisPrediction] = Field(..., description="Top predictions")
    top_disease: str = Field(..., description="Most likely disease")
    top_confidence: float = Field(..., description="Confidence of top prediction")
    treatment: str = Field("", description="Treatment for top disease")
    pesticide: str = Field("", description="Recommended pesticide for top disease")
    model_version: str = Field("v1.0-demo", description="Model version used")


# ───────────────────────────────────────────────
# Vendor Finder
# ───────────────────────────────────────────────

class VendorSearchRequest(BaseModel):
    latitude: float = Field(..., description="User latitude", ge=-90, le=90)
    longitude: float = Field(..., description="User longitude", ge=-180, le=180)
    query: Optional[str] = Field("pesticide shop", description="Search query")
    radius_km: float = Field(10.0, description="Search radius in km", ge=0.5, le=50)


class VendorResult(BaseModel):
    name: str
    address: str = ""
    distance_km: float = 0.0
    phone: str = ""
    rating: Optional[float] = None
    lat: float = 0.0
    lng: float = 0.0


class VendorSearchResponse(BaseModel):
    vendors: List[VendorResult] = Field(default_factory=list)
    total: int = 0
    search_radius_km: float = 10.0
    source: str = "google_maps"


# ───────────────────────────────────────────────
# Chat / Agent
# ───────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., description="User message text", min_length=1)
    session_id: Optional[str] = Field(None, description="Session ID for context")
    image_base64: Optional[str] = Field(None, description="Optional base64-encoded image")
    latitude: Optional[float] = Field(None, description="User latitude")
    longitude: Optional[float] = Field(None, description="User longitude")
    language: str = Field("hi", description="User language code")


class ChatResponse(BaseModel):
    reply: str = Field(..., description="Agent reply text")
    session_id: str = Field(..., description="Session ID")
    diagnosis: Optional[DiagnoseImageResponse] = Field(None, description="Diagnosis if image was analyzed")
    vendors: Optional[VendorSearchResponse] = Field(None, description="Vendors if searched")
    sources: List[str] = Field(default_factory=list, description="Knowledge sources used")
    language: str = Field("hi", description="Response language")


# ───────────────────────────────────────────────
# Notifications
# ───────────────────────────────────────────────

class NotifyVendorRequest(BaseModel):
    user_phone: str = Field(..., description="Farmer phone number")
    message: str = Field(..., description="Notification message")
    channel: str = Field("sms", description="Channel: sms | whatsapp")
    session_id: Optional[str] = Field(None, description="Related session ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Extra context")


class NotifyVendorResponse(BaseModel):
    status: str = Field(..., description="Notification status")
    notification_id: str = Field(..., description="Tracking ID")
    channel: str = Field("sms")
    message: str = Field("")


# ───────────────────────────────────────────────
# General
# ───────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = "healthy"
    app_name: str = "Krishi-Sarthi"
    version: str = "1.0.0"
    demo_mode: bool = True
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
