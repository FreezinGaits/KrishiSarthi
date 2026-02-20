"""
SQLAlchemy ORM models for Krishi-Sarthi.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.database import Base


def _default_jsonb():
    """Fallback for non-Postgres databases (SQLite)."""
    try:
        return JSONB
    except Exception:
        return Text


# Use Text as a universal JSON column (works on SQLite too)
JSONColumn = Text


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    phone = Column(String(20), unique=True, nullable=True)
    name = Column(String(100), nullable=True)
    email = Column(String(200), nullable=True)
    role = Column(String(20), default="farmer")  # farmer / vendor
    location_lat = Column(Float, nullable=True)
    location_lng = Column(Float, nullable=True)
    language = Column(String(10), default="hi")
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    sessions = relationship("Session", back_populates="user", lazy="selectin")
    notifications = relationship("Notification", back_populates="user", lazy="selectin")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    ended_at = Column(DateTime, nullable=True)
    metadata_json = Column(JSONColumn, nullable=True)

    user = relationship("User", back_populates="sessions")
    diagnoses = relationship("DiagnosisResult", back_populates="session", lazy="selectin")


class DiagnosisResult(Base):
    __tablename__ = "diagnosis_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=True)
    image_url = Column(String(500), nullable=True)
    disease_name = Column(String(200), nullable=False)
    confidence = Column(Float, nullable=False)
    treatment = Column(Text, nullable=True)
    pesticide = Column(String(200), nullable=True)
    model_version = Column(String(50), default="v1.0")
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    session = relationship("Session", back_populates="diagnoses")


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    address = Column(Text, nullable=True)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    phone = Column(String(20), nullable=True)
    rating = Column(Float, nullable=True)
    pesticides_json = Column(JSONColumn, nullable=True)
    source = Column(String(50), default="manual")
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    session_id = Column(String(36), nullable=True)
    channel = Column(String(20), default="sms")  # sms | whatsapp | email
    status = Column(String(20), default="pending")  # pending | sent | failed
    payload_json = Column(JSONColumn, nullable=True)
    sent_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="notifications")


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(300), nullable=False)
    category = Column(String(100), nullable=True)
    content = Column(Text, nullable=False)
    embedding_status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())


# ─────────────────────────────────────────────────
# Marketplace Models
# ─────────────────────────────────────────────────

class MarketConversation(Base):
    """Farmer ↔ Vendor chat conversation."""
    __tablename__ = "market_conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    farmer_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    vendor_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    messages = relationship("MarketMessage", back_populates="conversation", lazy="selectin")


class MarketMessage(Base):
    """Individual message inside a marketplace conversation."""
    __tablename__ = "market_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("market_conversations.id"), nullable=False)
    sender_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    conversation = relationship("MarketConversation", back_populates="messages")


class MedicineRequest(Base):
    """Medicine availability request from farmer to vendor."""
    __tablename__ = "medicine_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    farmer_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    vendor_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    disease_name = Column(String(200), nullable=False)
    medicine_name = Column(String(200), nullable=False)
    status = Column(String(20), default="pending")  # pending / confirmed / rejected
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
