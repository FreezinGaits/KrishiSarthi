"""
Crop Disease Classifier Service — PyTorch EfficientNet / MobileNet

Classifies crop leaf images into disease categories using a pretrained
image classification model. Supports 38 classes from the PlantVillage dataset.

Pipeline:
1. Load model (lazy, once on first call)
2. Preprocess image (resize, normalize, tensor conversion)
3. Run inference
4. Map class index → disease name + treatment + pesticide
5. Return top-k predictions

Falls back to intelligent demo classification when model file is unavailable
or DEMO_MODE is enabled.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.config import get_settings
from app.models.schemas import DiagnoseImageResponse, DiagnosisPrediction
from app.utils.logger import get_logger

logger = get_logger("service.classifier")
settings = get_settings()

# ── Lazy-loaded globals ───────────────────────────
_model = None
_class_labels: Optional[Dict] = None
_device = None
_transforms = None

# ── Disease knowledge base for demo + label mapping ─
DISEASE_DATABASE: Dict[str, Dict] = {
    "Tomato___Early_blight": {
        "display_name": "Tomato Early Blight",
        "crop": "Tomato",
        "treatment": "Apply Mancozeb 75% WP at 2.5g/L water. Remove and destroy affected leaves. "
                     "Ensure adequate spacing between plants for air circulation. Water at the base, "
                     "avoid wetting foliage. Rotate crops yearly.",
        "pesticide": "Mancozeb 75% WP",
        "prevention": "Use certified disease-free seeds. Apply preventive fungicide spray before monsoon.",
    },
    "Tomato___Late_blight": {
        "display_name": "Tomato Late Blight",
        "crop": "Tomato",
        "treatment": "Apply Copper Oxychloride 50% WP at 3g/L immediately. Remove and burn infected plants. "
                     "Avoid overhead irrigation. Stake plants for better air flow.",
        "pesticide": "Copper Oxychloride 50% WP",
        "prevention": "Plant resistant varieties. Avoid planting near potato fields.",
    },
    "Tomato___Leaf_Mold": {
        "display_name": "Tomato Leaf Mold",
        "crop": "Tomato",
        "treatment": "Improve ventilation in greenhouse. Apply Chlorothalonil fungicide at 2g/L. "
                     "Reduce humidity below 85%. Remove lower leaves for better air flow.",
        "pesticide": "Chlorothalonil 75% WP",
        "prevention": "Maintain good ventilation. Use resistant varieties.",
    },
    "Tomato___Septoria_leaf_spot": {
        "display_name": "Tomato Septoria Leaf Spot",
        "crop": "Tomato",
        "treatment": "Apply Mancozeb or Chlorothalonil fungicide. Remove infected lower leaves. "
                     "Mulch around plants to prevent soil splash. Water at soil level.",
        "pesticide": "Mancozeb 75% WP",
        "prevention": "Rotate crops every 3 years. Destroy crop debris after harvest.",
    },
    "Tomato___Bacterial_spot": {
        "display_name": "Tomato Bacterial Spot",
        "crop": "Tomato",
        "treatment": "Apply Copper-based bactericide. Remove severely infected plants. "
                     "Avoid working with wet plants. Use drip irrigation.",
        "pesticide": "Copper Hydroxide 77% WP",
        "prevention": "Use disease-free transplants. Treat seeds with hot water (50°C for 25 min).",
    },
    "Tomato___healthy": {
        "display_name": "Healthy Tomato Plant",
        "crop": "Tomato",
        "treatment": "No treatment needed. Plant appears healthy. Continue regular care, "
                     "proper watering, and balanced fertilization.",
        "pesticide": "None required",
        "prevention": "Maintain good agricultural practices.",
    },
    "Wheat___Brown_Rust": {
        "display_name": "Wheat Brown/Leaf Rust",
        "crop": "Wheat",
        "treatment": "Apply Propiconazole 25% EC at 1ml/L at first sign of orange-brown pustules. "
                     "Spray in evening for best absorption. Repeat after 15 days if needed.",
        "pesticide": "Propiconazole 25% EC",
        "prevention": "Use resistant varieties (PBW 343, HD 2967). Early sowing reduces risk.",
    },
    "Wheat___Yellow_Rust": {
        "display_name": "Wheat Yellow/Stripe Rust",
        "crop": "Wheat",
        "treatment": "Apply Propiconazole 25% EC immediately at 1ml/L. This is the most damaging "
                     "wheat rust — early treatment is critical. Spray entire field.",
        "pesticide": "Propiconazole 25% EC",
        "prevention": "Plant resistant varieties. Monitor from January onwards.",
    },
    "Wheat___healthy": {
        "display_name": "Healthy Wheat Plant",
        "crop": "Wheat",
        "treatment": "No treatment needed. Continue balanced NPK fertilization and proper irrigation.",
        "pesticide": "None required",
        "prevention": "Follow recommended agronomic practices.",
    },
    "Rice___Leaf_Blast": {
        "display_name": "Rice Leaf Blast",
        "crop": "Rice",
        "treatment": "Apply Tricyclazole 75% WP at 0.6g/L. Reduce nitrogen fertilization. "
                     "Maintain 2-3 cm water in paddy. Drain field and reapply if symptoms persist.",
        "pesticide": "Tricyclazole 75% WP",
        "prevention": "Use resistant varieties (Pusa Basmati-1). Balanced nitrogen use.",
    },
    "Rice___Brown_Spot": {
        "display_name": "Rice Brown Spot",
        "crop": "Rice",
        "treatment": "Apply Mancozeb 75% WP at 2.5g/L. Ensure balanced fertilization especially "
                     "potassium. This disease often indicates nutrient-deficient soil.",
        "pesticide": "Mancozeb 75% WP",
        "prevention": "Soil testing and balanced fertilization. Use healthy seeds.",
    },
    "Rice___Bacterial_Blight": {
        "display_name": "Rice Bacterial Leaf Blight",
        "crop": "Rice",
        "treatment": "Drain the field for 3-4 days. Apply Streptocycline at 0.5g + Copper Oxychloride "
                     "at 2.5g per liter. Reduce nitrogen application.",
        "pesticide": "Streptocycline + Copper Oxychloride",
        "prevention": "Use resistant varieties. Avoid excess nitrogen. Proper drainage.",
    },
    "Rice___healthy": {
        "display_name": "Healthy Rice Plant",
        "crop": "Rice",
        "treatment": "No treatment needed. Plant appears healthy.",
        "pesticide": "None required",
        "prevention": "Continue good water management and balanced fertilization.",
    },
    "Potato___Early_blight": {
        "display_name": "Potato Early Blight",
        "crop": "Potato",
        "treatment": "Apply Mancozeb 75% WP at 2.5g/L. Remove lower affected leaves. "
                     "Hill up soil around plant base. Ensure proper tuber coverage.",
        "pesticide": "Mancozeb 75% WP",
        "prevention": "Use certified disease-free seed tubers. Rotate crops.",
    },
    "Potato___Late_blight": {
        "display_name": "Potato Late Blight",
        "crop": "Potato",
        "treatment": "Apply Cymoxanil + Mancozeb at 3g/L urgently. This spreads rapidly — "
                     "treat entire field immediately. Destroy volunteer potato plants.",
        "pesticide": "Cymoxanil 8% + Mancozeb 64% WP",
        "prevention": "Plant resistant varieties. Monitor weather — high humidity triggers outbreaks.",
    },
    "Potato___healthy": {
        "display_name": "Healthy Potato Plant",
        "crop": "Potato",
        "treatment": "No treatment needed. Continue proper hilling and irrigation.",
        "pesticide": "None required",
        "prevention": "Regular monitoring and good field hygiene.",
    },
    "Corn___Common_rust": {
        "display_name": "Corn/Maize Common Rust",
        "crop": "Corn",
        "treatment": "Apply Mancozeb 75% WP at 2.5g/L if infection is early. For severe cases, "
                     "use Propiconazole 25% EC at 1ml/L.",
        "pesticide": "Mancozeb 75% WP or Propiconazole 25% EC",
        "prevention": "Plant rust-resistant hybrids. Early planting reduces risk.",
    },
    "Corn___Northern_Leaf_Blight": {
        "display_name": "Corn Northern Leaf Blight",
        "crop": "Corn",
        "treatment": "Apply Propiconazole 25% EC at 1ml/L. Spray when lesions first appear on lower leaves.",
        "pesticide": "Propiconazole 25% EC",
        "prevention": "Crop rotation. Bury crop residue. Use resistant hybrids.",
    },
    "Corn___healthy": {
        "display_name": "Healthy Corn Plant",
        "crop": "Corn",
        "treatment": "No treatment needed. Plant is healthy.",
        "pesticide": "None required",
        "prevention": "Continue standard practices.",
    },
}

# Map keywords to diseases for intelligent demo classification
KEYWORD_DISEASE_MAP = {
    "tomato": ["Tomato___Early_blight", "Tomato___Late_blight", "Tomato___Septoria_leaf_spot", "Tomato___healthy"],
    "tamatar": ["Tomato___Early_blight", "Tomato___Late_blight", "Tomato___Septoria_leaf_spot", "Tomato___healthy"],
    "wheat": ["Wheat___Brown_Rust", "Wheat___Yellow_Rust", "Wheat___healthy"],
    "gehu": ["Wheat___Brown_Rust", "Wheat___Yellow_Rust", "Wheat___healthy"],
    "rice": ["Rice___Leaf_Blast", "Rice___Brown_Spot", "Rice___Bacterial_Blight", "Rice___healthy"],
    "chawal": ["Rice___Leaf_Blast", "Rice___Brown_Spot", "Rice___Bacterial_Blight", "Rice___healthy"],
    "dhaan": ["Rice___Leaf_Blast", "Rice___Brown_Spot", "Rice___Bacterial_Blight", "Rice___healthy"],
    "potato": ["Potato___Early_blight", "Potato___Late_blight", "Potato___healthy"],
    "aloo": ["Potato___Early_blight", "Potato___Late_blight", "Potato___healthy"],
    "corn": ["Corn___Common_rust", "Corn___Northern_Leaf_Blight", "Corn___healthy"],
    "maize": ["Corn___Common_rust", "Corn___Northern_Leaf_Blight", "Corn___healthy"],
    "makka": ["Corn___Common_rust", "Corn___Northern_Leaf_Blight", "Corn___healthy"],
}


def _load_class_labels() -> Dict:
    """Load class label mappings from JSON file."""
    global _class_labels
    if _class_labels is not None:
        return _class_labels

    labels_path = Path(settings.class_labels_path)
    if labels_path.exists():
        with open(labels_path, "r", encoding="utf-8") as f:
            _class_labels = json.load(f)
        logger.info("Loaded %d class labels from %s", len(_class_labels), labels_path)
    else:
        # Build from DISEASE_DATABASE
        _class_labels = {
            str(i): key for i, key in enumerate(DISEASE_DATABASE.keys())
        }
        logger.info("Using built-in class labels (%d classes)", len(_class_labels))

    return _class_labels


def _load_model():
    """Lazy-load the PyTorch model. Returns None if model file doesn't exist."""
    global _model, _device, _transforms

    if _model is not None:
        return _model

    model_path = Path(settings.classifier_model_path)

    if not model_path.exists():
        logger.warning("Model file not found at %s — will use demo classifier", model_path)
        return None

    try:
        import torch
        import torchvision.transforms as T
        from torchvision import models

        _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info("Loading classifier model on device: %s", _device)

        # Load EfficientNet-B0 with custom classification head
        num_classes = len(DISEASE_DATABASE)
        model = models.efficientnet_b0(weights=None)
        model.classifier[1] = torch.nn.Linear(model.classifier[1].in_features, num_classes)

        # Load saved weights
        state_dict = torch.load(str(model_path), map_location=_device, weights_only=True)
        model.load_state_dict(state_dict)
        model.to(_device)
        model.eval()

        # Setup transforms
        _transforms = T.Compose([
            T.Resize((224, 224)),
            T.ToTensor(),
            T.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ])

        _model = model
        logger.info("Classifier model loaded successfully (%d classes)", num_classes)
        return _model

    except Exception as e:
        logger.error("Failed to load classifier model: %s", str(e))
        return None


def _build_prediction(class_key: str, confidence: float) -> DiagnosisPrediction:
    """Build a DiagnosisPrediction from a disease database entry."""
    disease_info = DISEASE_DATABASE.get(class_key, {})
    return DiagnosisPrediction(
        disease_name=disease_info.get("display_name", class_key.replace("___", " — ").replace("_", " ")),
        confidence=round(confidence, 3),
        treatment=disease_info.get("treatment", "Consult a local agronomist for treatment advice."),
        pesticide=disease_info.get("pesticide", "Consult local agricultural supply shop"),
    )


async def classify_image(
    image_data: bytes,
    filename: str = "image.jpg",
    request_id: str = "",
) -> DiagnoseImageResponse:
    """
    Classify a crop image for disease detection.

    Pipeline:
    1. If DEMO_MODE with mock enabled → intelligent demo classification
    2. Try loading PyTorch model
    3. If model available → real inference
    4. If model unavailable → intelligent demo fallback

    Args:
        image_data: Raw image bytes (JPEG/PNG/WebP)
        filename: Original filename (used for keyword-based demo classification)
        request_id: Request tracking ID

    Returns:
        DiagnoseImageResponse with top predictions, treatments, pesticides
    """
    logger.info("[%s] Classification request: filename=%s, size=%.1fKB", request_id, filename, len(image_data) / 1024)

    # ── Demo mode shortcut ────────────────────────
    if settings.is_demo and settings.mock_ai_responses:
        logger.info("[%s] DEMO_MODE: using intelligent demo classifier", request_id)
        return _demo_classify(filename, request_id)

    # ── Try real model inference ──────────────────
    model = _load_model()

    if model is not None:
        try:
            return await _real_inference(image_data, request_id)
        except Exception as e:
            logger.error("[%s] Model inference failed: %s", request_id, str(e))
            if settings.is_demo:
                return _demo_classify(filename, request_id)
            raise

    # ── No model available ────────────────────────
    logger.warning("[%s] No classifier model available", request_id)
    if settings.is_demo:
        return _demo_classify(filename, request_id)

    raise FileNotFoundError(f"Classifier model not found at {settings.classifier_model_path}")


async def _real_inference(image_data: bytes, request_id: str) -> DiagnoseImageResponse:
    """Run actual PyTorch model inference on the image."""
    import torch
    from PIL import Image

    # Decode image
    image = Image.open(io.BytesIO(image_data)).convert("RGB")
    logger.info("[%s] Image decoded: %dx%d", request_id, image.width, image.height)

    # Preprocess
    input_tensor = _transforms(image).unsqueeze(0).to(_device)

    # Inference
    with torch.no_grad():
        outputs = _model(input_tensor)
        probabilities = torch.nn.functional.softmax(outputs[0], dim=0)

    # Get top-k predictions
    labels = _load_class_labels()
    top_k = min(3, len(labels))
    top_probs, top_indices = torch.topk(probabilities, top_k)

    predictions = []
    for prob, idx in zip(top_probs.cpu().numpy(), top_indices.cpu().numpy()):
        class_key = labels.get(str(idx), f"Unknown_class_{idx}")
        predictions.append(_build_prediction(class_key, float(prob)))

    top = predictions[0]
    logger.info("[%s] Inference result: %s (%.1f%%)", request_id, top.disease_name, top.confidence * 100)

    return DiagnoseImageResponse(
        predictions=predictions,
        top_disease=top.disease_name,
        top_confidence=top.confidence,
        treatment=top.treatment,
        pesticide=top.pesticide,
        model_version="v1.0-efficientnet",
    )


def _demo_classify(filename: str, request_id: str) -> DiagnoseImageResponse:
    """
    Intelligent demo classification based on filename keywords.
    If no keyword match, returns a random disease from the database.
    """
    import random

    filename_lower = filename.lower()

    # Try to match filename to a crop type
    matched_classes = None
    for keyword, classes in KEYWORD_DISEASE_MAP.items():
        if keyword in filename_lower:
            matched_classes = classes
            logger.info("[%s] DEMO: filename matched keyword '%s'", request_id, keyword)
            break

    if matched_classes is None:
        # No keyword match — pick random crop diseases (not healthy)
        disease_keys = [k for k in DISEASE_DATABASE.keys() if "healthy" not in k.lower()]
        matched_classes = random.sample(disease_keys, min(3, len(disease_keys)))

    # Select primary disease (prefer non-healthy for interesting demos)
    non_healthy = [c for c in matched_classes if "healthy" not in c.lower()]
    primary_key = random.choice(non_healthy) if non_healthy else matched_classes[0]

    # Build top-3 predictions with descending confidence
    primary_conf = round(random.uniform(0.82, 0.96), 3)
    predictions = [_build_prediction(primary_key, primary_conf)]

    remaining = [c for c in matched_classes if c != primary_key]
    for i, class_key in enumerate(remaining[:2]):
        conf = round(primary_conf - random.uniform(0.15 + i * 0.1, 0.25 + i * 0.1), 3)
        predictions.append(_build_prediction(class_key, max(conf, 0.05)))

    top = predictions[0]
    logger.info("[%s] DEMO classification: %s (%.1f%%)", request_id, top.disease_name, top.confidence * 100)

    return DiagnoseImageResponse(
        predictions=predictions,
        top_disease=top.disease_name,
        top_confidence=top.confidence,
        treatment=top.treatment,
        pesticide=top.pesticide,
        model_version="v1.0-demo",
    )
