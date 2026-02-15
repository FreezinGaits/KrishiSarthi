"""
Whisper Speech-to-Text Service

Transcribes audio files using the OpenAI Whisper API.
Supports Hindi and other Indian vernacular languages.
Includes language detection, confidence scoring, and demo fallback.
"""

from __future__ import annotations

import io
import random
from pathlib import Path
from typing import Optional

import httpx

from app.config import get_settings
from app.models.schemas import SpeechToTextResponse
from app.utils.logger import get_logger

logger = get_logger("service.whisper")
settings = get_settings()

# ── Constants ─────────────────────────────────────
WHISPER_API_URL = "https://api.openai.com/v1/audio/transcriptions"
HTTP_TIMEOUT = 30.0  # Whisper can be slow on long audio
MAX_AUDIO_SIZE = 25 * 1024 * 1024  # 25MB (OpenAI limit)

SUPPORTED_FORMATS = {".wav", ".mp3", ".webm", ".ogg", ".m4a", ".mp4", ".flac"}

# MIME type mapping for the API multipart upload
MIME_MAP = {
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".webm": "audio/webm",
    ".ogg": "audio/ogg",
    ".m4a": "audio/mp4",
    ".mp4": "audio/mp4",
    ".flac": "audio/flac",
}

# ── Demo fallback transcripts ────────────────────
DEMO_TRANSCRIPTS = [
    {
        "transcript": "Meri tamatar ki fasal mein kale dhabbe hain, kya karu?",
        "language": "hi",
        "confidence": 0.94,
        "duration": 3.8,
    },
    {
        "transcript": "Mere gehu ki patti peeli ho rahi hai aur sukh rahi hai",
        "language": "hi",
        "confidence": 0.91,
        "duration": 4.2,
    },
    {
        "transcript": "Chawal ki fasal mein keedon ka hamla ho raha hai, koi dawai batao",
        "language": "hi",
        "confidence": 0.89,
        "duration": 5.1,
    },
    {
        "transcript": "Mujhe sabse nazdiki keetnashak ki dukaan chahiye",
        "language": "hi",
        "confidence": 0.96,
        "duration": 2.9,
    },
    {
        "transcript": "Aloo ki fasal mein safed makdi lagi hai, uska ilaaj batao",
        "language": "hi",
        "confidence": 0.92,
        "duration": 4.5,
    },
    {
        "transcript": "Sarson ki fasal mein phool aane se pehle rog lag gaya hai",
        "language": "hi",
        "confidence": 0.88,
        "duration": 4.0,
    },
]


async def transcribe_audio(
    audio_data: bytes,
    filename: str = "audio.webm",
    request_id: str = "",
    language: Optional[str] = "hi",
) -> SpeechToTextResponse:
    """
    Transcribe audio using OpenAI Whisper API.

    Pipeline:
    1. Validate audio data (size, format)
    2. If DEMO_MODE → return mock transcript
    3. Send to Whisper API with Hindi language hint
    4. Return structured response with transcript + language + confidence

    Args:
        audio_data: Raw audio bytes
        filename: Original filename (used for format detection)
        request_id: Request tracking ID
        language: Language hint for Whisper (default: "hi" for Hindi)

    Returns:
        SpeechToTextResponse with transcript, language, confidence
    """
    logger.info(
        "[%s] Transcription request: filename=%s, size=%.1fKB",
        request_id, filename, len(audio_data) / 1024,
    )

    # ── Validate ──────────────────────────────────
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported audio format: {ext}. Supported: {', '.join(SUPPORTED_FORMATS)}")

    if len(audio_data) > MAX_AUDIO_SIZE:
        raise ValueError(f"Audio file too large: {len(audio_data)} bytes. Maximum: {MAX_AUDIO_SIZE} bytes")

    if len(audio_data) < 100:
        raise ValueError("Audio file too small — likely empty or corrupt")

    # ── Demo mode ─────────────────────────────────
    if settings.is_demo and settings.mock_ai_responses:
        logger.info("[%s] DEMO_MODE: returning mock transcript", request_id)
        return _demo_response(request_id)

    # ── Call Whisper API ──────────────────────────
    if not settings.openai_api_key:
        logger.warning("[%s] No OpenAI API key configured", request_id)
        if settings.is_demo:
            return _demo_response(request_id)
        raise ConnectionError("OpenAI API key not configured")

    try:
        result = await _call_whisper_api(
            audio_data=audio_data,
            filename=filename,
            ext=ext,
            language=language,
            request_id=request_id,
        )
        return result

    except Exception as e:
        logger.error("[%s] Whisper API call failed: %s", request_id, str(e))
        if settings.is_demo:
            logger.warning("[%s] Falling back to demo transcript", request_id)
            return _demo_response(request_id)
        raise


async def _call_whisper_api(
    audio_data: bytes,
    filename: str,
    ext: str,
    language: Optional[str],
    request_id: str,
) -> SpeechToTextResponse:
    """
    Make the actual HTTP call to OpenAI Whisper API.

    Uses verbose_json response format to get word-level timestamps
    and language detection.
    """
    mime = MIME_MAP.get(ext, "audio/mpeg")

    logger.info("[%s] Calling Whisper API: model=%s, lang=%s", request_id, settings.whisper_model, language)

    # Build multipart form data
    files = {
        "file": (filename, audio_data, mime),
    }
    data = {
        "model": settings.whisper_model,
        "response_format": "verbose_json",
    }

    # Add language hint (helps with Hindi accuracy)
    if language:
        data["language"] = language

    # Optional: add prompt to guide transcription for agricultural context
    data["prompt"] = (
        "This is a farmer speaking in Hindi about crop diseases, pesticides, "
        "and agricultural problems. Common topics: tamatar, gehu, chawal, "
        "keetnashak, rog, bimari, fasal, khet."
    )

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        response = await client.post(
            WHISPER_API_URL,
            files=files,
            data=data,
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
            },
        )
        response.raise_for_status()

    result = response.json()

    transcript = result.get("text", "").strip()
    detected_language = result.get("language", language or "hi")
    duration = result.get("duration", 0.0)

    # Calculate confidence from segment-level data if available
    confidence = _calculate_confidence(result)

    logger.info(
        "[%s] Whisper result: lang=%s, duration=%.1fs, confidence=%.2f, transcript='%s'",
        request_id, detected_language, duration, confidence, transcript[:60],
    )

    return SpeechToTextResponse(
        transcript=transcript,
        language=detected_language,
        confidence=confidence,
        duration_seconds=round(duration, 2),
    )


def _calculate_confidence(whisper_result: dict) -> float:
    """
    Calculate overall confidence from Whisper's segment-level data.
    Whisper verbose_json returns segments with avg_logprob and no_speech_prob.
    """
    segments = whisper_result.get("segments", [])
    if not segments:
        return 0.85  # Reasonable default

    # Average the exponential of avg_logprob across segments
    # avg_logprob is typically between -1 and 0 (higher = more confident)
    avg_logprobs = [seg.get("avg_logprob", -0.3) for seg in segments]
    no_speech_probs = [seg.get("no_speech_prob", 0.0) for seg in segments]

    # Convert log probability to a 0-1 confidence score
    import math
    avg_logprob = sum(avg_logprobs) / len(avg_logprobs)

    # Map from typical range [-1.0, 0.0] to [0.5, 1.0]
    raw_confidence = math.exp(avg_logprob)
    confidence = max(0.0, min(1.0, raw_confidence))

    # Penalize if there's high no-speech probability
    avg_no_speech = sum(no_speech_probs) / len(no_speech_probs)
    if avg_no_speech > 0.5:
        confidence *= (1.0 - avg_no_speech * 0.5)

    return round(confidence, 3)


def _demo_response(request_id: str) -> SpeechToTextResponse:
    """Return a realistic mock transcript for demo mode."""
    demo = random.choice(DEMO_TRANSCRIPTS)
    logger.info("[%s] DEMO transcript: '%s'", request_id, demo["transcript"][:50])

    return SpeechToTextResponse(
        transcript=demo["transcript"],
        language=demo["language"],
        confidence=demo["confidence"],
        duration_seconds=demo["duration"],
    )
