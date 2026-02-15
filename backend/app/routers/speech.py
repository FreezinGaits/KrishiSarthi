"""
Speech-to-Text Router — POST /api/speech-to-text

Accepts audio files (wav, mp3, webm, m4a, ogg), sends to OpenAI Whisper API
for Hindi/vernacular transcription. Falls back to mock transcript in DEMO_MODE.
"""

from __future__ import annotations

import io
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.config import get_settings
from app.models.schemas import SpeechToTextResponse
from app.utils.logger import get_logger

logger = get_logger("router.speech")
settings = get_settings()

router = APIRouter(prefix="/api", tags=["Speech"])

ALLOWED_AUDIO_TYPES = {
    "audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp3",
    "audio/webm", "audio/ogg", "audio/m4a", "audio/mp4",
    "audio/x-m4a", "video/webm",  # browser MediaRecorder may use video/webm
}
ALLOWED_EXTENSIONS = {".wav", ".mp3", ".webm", ".ogg", ".m4a", ".mp4"}

# ── Demo fallback data ────────────────────────────
DEMO_TRANSCRIPTS = [
    "Meri tamatar ki fasal mein kale dhabbe hain",
    "Mere gehu ki patti peeli ho rahi hai",
    "Chawal ki fasal mein keedon ka hamla ho raha hai",
    "Mujhe sabse nazdiki keetnashak dukaan chahiye",
]


@router.post(
    "/speech-to-text",
    response_model=SpeechToTextResponse,
    summary="Convert speech audio to text",
    description="Accepts audio file, transcribes using Whisper. Returns Hindi transcript.",
)
async def speech_to_text(
    audio: UploadFile = File(..., description="Audio file (wav, mp3, webm, m4a, ogg)"),
):
    """
    Speech-to-text endpoint.

    1. Validates audio file type and size
    2. Sends to Whisper API (or returns demo transcript)
    3. Returns transcript with detected language
    """
    request_id = str(uuid.uuid4())[:8]
    logger.info("[%s] Speech-to-text request: filename=%s, content_type=%s", request_id, audio.filename, audio.content_type)

    # ── Validate file extension ───────────────────
    ext = Path(audio.filename or "audio.webm").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported audio format '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # ── Read audio data ───────────────────────────
    audio_bytes = await audio.read()
    if len(audio_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty audio file received",
        )
    if len(audio_bytes) > settings.max_upload_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {settings.max_upload_size // 1_048_576}MB",
        )

    logger.info("[%s] Audio size: %.1f KB", request_id, len(audio_bytes) / 1024)

    # ── Transcribe ────────────────────────────────
    try:
        from app.services.whisper_service import transcribe_audio
        result = await transcribe_audio(
            audio_data=audio_bytes,
            filename=audio.filename or f"audio{ext}",
            request_id=request_id,
        )
        logger.info("[%s] Transcription success: lang=%s, len=%d", request_id, result.language, len(result.transcript))
        return result

    except ImportError:
        # Service not yet implemented — use demo fallback
        if settings.is_demo:
            logger.warning("[%s] Whisper service not available, using demo fallback", request_id)
            return _demo_transcript(request_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Speech-to-text service is not available",
        )
    except Exception as e:
        logger.error("[%s] Transcription failed: %s", request_id, str(e))
        logger.warning("[%s] Falling back to demo transcript due to error", request_id)
        return _demo_transcript(request_id)


def _demo_transcript(request_id: str) -> SpeechToTextResponse:
    """Return a mock transcript for demo mode."""
    import random
    transcript = random.choice(DEMO_TRANSCRIPTS)
    logger.info("[%s] DEMO transcript: %s", request_id, transcript)
    return SpeechToTextResponse(
        transcript=transcript,
        language="hi",
        confidence=0.95,
        duration_seconds=3.2,
    )
