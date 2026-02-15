"""
Image Diagnosis Router — POST /api/diagnose-image

Accepts crop images, runs EfficientNet disease classifier.
Falls back to mock diagnosis in DEMO_MODE.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.config import get_settings
from app.models.schemas import DiagnoseImageResponse, DiagnosisPrediction
from app.utils.logger import get_logger

logger = get_logger("router.diagnosis")
settings = get_settings()

router = APIRouter(prefix="/api", tags=["Diagnosis"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# ── Demo fallback data ────────────────────────────
DEMO_DIAGNOSES = [
    {
        "disease_name": "Tomato Early Blight",
        "confidence": 0.92,
        "treatment": "Apply chlorothalonil-based fungicide. Remove affected leaves. Ensure proper spacing for air circulation. Water at base of plant, avoid wetting leaves.",
        "pesticide": "Mancozeb 75% WP",
    },
    {
        "disease_name": "Tomato Late Blight",
        "confidence": 0.88,
        "treatment": "Apply copper-based fungicide immediately. Remove and destroy infected plants. Avoid overhead irrigation. Rotate crops next season.",
        "pesticide": "Copper Oxychloride 50% WP",
    },
    {
        "disease_name": "Wheat Leaf Rust",
        "confidence": 0.85,
        "treatment": "Apply propiconazole fungicide at first sign of pustules. Use resistant varieties in next season. Monitor regularly during humid weather.",
        "pesticide": "Propiconazole 25% EC",
    },
    {
        "disease_name": "Rice Blast",
        "confidence": 0.90,
        "treatment": "Apply tricyclazole fungicide. Reduce nitrogen fertilization. Maintain shallow water in paddy. Use resistant varieties.",
        "pesticide": "Tricyclazole 75% WP",
    },
    {
        "disease_name": "Healthy Plant",
        "confidence": 0.96,
        "treatment": "No treatment needed. Plant appears healthy. Continue regular care and monitoring.",
        "pesticide": "None required",
    },
]


@router.post(
    "/diagnose-image",
    response_model=DiagnoseImageResponse,
    summary="Diagnose crop disease from image",
    description="Accepts a crop image and returns disease classification with treatment recommendations.",
)
async def diagnose_image(
    image: UploadFile = File(..., description="Crop leaf/plant image (jpg, png, webp)"),
):
    """
    Image diagnosis endpoint.

    1. Validates image file type and size
    2. Runs through EfficientNet classifier (or demo fallback)
    3. Returns top predictions with treatment and pesticide recommendations
    """
    request_id = str(uuid.uuid4())[:8]
    logger.info("[%s] Diagnosis request: filename=%s, content_type=%s", request_id, image.filename, image.content_type)

    # ── Validate file extension ───────────────────
    ext = Path(image.filename or "image.jpg").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image format '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # ── Read image data ───────────────────────────
    image_bytes = await image.read()
    if len(image_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty image file received",
        )
    if len(image_bytes) > settings.max_upload_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {settings.max_upload_size // 1_048_576}MB",
        )

    logger.info("[%s] Image size: %.1f KB", request_id, len(image_bytes) / 1024)

    # ── Run classifier ────────────────────────────
    try:
        from app.services.classifier_service import classify_image
        result = await classify_image(
            image_data=image_bytes,
            filename=image.filename or "crop_image.jpg",
            request_id=request_id,
        )
        logger.info("[%s] Classification success: disease=%s, confidence=%.2f", request_id, result.top_disease, result.top_confidence)
        return result

    except ImportError:
        if settings.is_demo:
            logger.warning("[%s] Classifier service not available, using demo fallback", request_id)
            return _demo_diagnosis(request_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Image classification service is not available",
        )
    except Exception as e:
        logger.error("[%s] Classification failed: %s", request_id, str(e))
        if settings.is_demo:
            logger.warning("[%s] Falling back to demo diagnosis", request_id)
            return _demo_diagnosis(request_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Image classification failed: {str(e)}",
        )


def _demo_diagnosis(request_id: str) -> DiagnoseImageResponse:
    """Return a mock diagnosis for demo mode."""
    import random
    primary = random.choice(DEMO_DIAGNOSES)

    # Create top-3 predictions
    others = [d for d in DEMO_DIAGNOSES if d["disease_name"] != primary["disease_name"]]
    secondary = random.sample(others, min(2, len(others)))

    predictions = [
        DiagnosisPrediction(**primary),
        *[
            DiagnosisPrediction(
                disease_name=d["disease_name"],
                confidence=round(primary["confidence"] - random.uniform(0.15, 0.35), 2),
                treatment=d["treatment"],
                pesticide=d["pesticide"],
            )
            for d in secondary
        ],
    ]

    logger.info("[%s] DEMO diagnosis: %s (%.0f%%)", request_id, primary["disease_name"], primary["confidence"] * 100)

    return DiagnoseImageResponse(
        predictions=predictions,
        top_disease=primary["disease_name"],
        top_confidence=primary["confidence"],
        treatment=primary["treatment"],
        pesticide=primary["pesticide"],
        model_version="v1.0-demo",
    )
