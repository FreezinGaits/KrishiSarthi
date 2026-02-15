"""
Crop Disease Classifier Service — GPT-4o Vision + PyTorch EfficientNet

Classifies crop leaf images into disease categories using:
1. Local PyTorch model (if trained model weights exist)
2. OpenAI GPT-4o Vision API (real-time image analysis)
3. Demo fallback (keyword-based mock classification)

Pipeline: PyTorch model → GPT-4o Vision → Demo fallback
"""

from __future__ import annotations

import base64
import io
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx

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

# ── OpenAI Vision API ────────────────────────────
OPENAI_VISION_URL = "https://api.openai.com/v1/chat/completions"
VISION_TIMEOUT = 30.0

VISION_SYSTEM_PROMPT = """You are an expert agricultural scientist specializing in crop disease identification.
You are part of the Krishi-Sarthi system that helps Indian farmers identify crop diseases.

When given a crop leaf image, you MUST respond with ONLY a valid JSON object (no markdown, no explanation) in this exact format:
{
  "predictions": [
    {
      "disease_name": "Human readable disease name",
      "disease_key": "Crop___Disease_Name",
      "confidence": 0.92,
      "crop": "Crop name"
    }
  ],
  "is_healthy": false,
  "analysis": "Brief 1-2 sentence description of what you see"
}

Rules:
- Return exactly 1-3 predictions, ranked by confidence (highest first)
- Confidence should be realistic (0.5-0.99)
- disease_key format: "CropName___Disease_Name" (e.g., "Tomato___Early_blight")
- If the leaf looks healthy, set is_healthy to true and disease_name to "Healthy [Crop] Plant"
- If you cannot identify the crop/disease, still provide your best guess with lower confidence
- Focus on diseases common in India: rice blast, brown spot, wheat rust, tomato blight, etc.
- Consider the following crops: Tomato, Wheat, Rice, Potato, Corn/Maize, Pepper, Mustard, Cotton"""


# ── Disease knowledge base for treatments ────────
DISEASE_DATABASE: Dict[str, Dict] = {
    "Tomato___Early_blight": {
        "display_name": "Tomato Early Blight",
        "crop": "Tomato",
        "scientific_name": "Alternaria solani",
        "treatment": "Apply Mancozeb 75% WP at 2.5g/L water. Remove and destroy affected leaves. "
                     "Ensure adequate spacing between plants for air circulation. Water at the base, "
                     "avoid wetting foliage. Rotate crops yearly.",
        "pesticide": "Mancozeb 75% WP (Dithane M-45)",
        "prevention": "Use certified disease-free seeds. Apply preventive fungicide spray before monsoon. "
                      "Avoid overhead irrigation. Maintain proper plant spacing (60×45 cm).",
    },
    "Tomato___Late_blight": {
        "display_name": "Tomato Late Blight",
        "crop": "Tomato",
        "scientific_name": "Phytophthora infestans",
        "treatment": "Apply Copper Oxychloride 50% WP at 3g/L immediately. Remove and burn infected plants. "
                     "Avoid overhead irrigation. Stake plants for better air flow.",
        "pesticide": "Copper Oxychloride 50% WP (Blitox-50)",
        "prevention": "Plant resistant varieties. Avoid planting near potato fields. Use raised beds.",
    },
    "Tomato___Leaf_Mold": {
        "display_name": "Tomato Leaf Mold",
        "crop": "Tomato",
        "scientific_name": "Passalora fulva",
        "treatment": "Improve ventilation in greenhouse. Apply Chlorothalonil fungicide at 2g/L. "
                     "Reduce humidity below 85%. Remove lower leaves for better air flow.",
        "pesticide": "Chlorothalonil 75% WP (Kavach)",
        "prevention": "Maintain good ventilation. Use resistant varieties. Avoid leaf wetness.",
    },
    "Tomato___Septoria_leaf_spot": {
        "display_name": "Tomato Septoria Leaf Spot",
        "crop": "Tomato",
        "scientific_name": "Septoria lycopersici",
        "treatment": "Apply Mancozeb or Chlorothalonil fungicide at 2.5g/L. Remove infected lower leaves. "
                     "Mulch around plants to prevent soil splash. Water at soil level.",
        "pesticide": "Mancozeb 75% WP (Dithane M-45)",
        "prevention": "Rotate crops every 3 years. Destroy crop debris after harvest.",
    },
    "Tomato___Bacterial_spot": {
        "display_name": "Tomato Bacterial Spot",
        "crop": "Tomato",
        "scientific_name": "Xanthomonas vesicatoria",
        "treatment": "Apply Copper-based bactericide (Copper hydroxide 77% WP at 2g/L). Remove severely "
                     "infected plants. Avoid working with wet plants. Use drip irrigation.",
        "pesticide": "Copper Hydroxide 77% WP (Kocide 3000)",
        "prevention": "Use disease-free transplants. Treat seeds with hot water (50°C for 25 min).",
    },
    "Tomato___Spider_mites": {
        "display_name": "Tomato Spider Mites (Two-spotted)",
        "crop": "Tomato",
        "scientific_name": "Tetranychus urticae",
        "treatment": "Spray Abamectin 1.9% EC at 0.5ml/L. Spray undersides of leaves. "
                     "Increase humidity to discourage mites.",
        "pesticide": "Abamectin 1.9% EC (Abacin)",
        "prevention": "Regular monitoring. Avoid dusty conditions. Encourage natural predators.",
    },
    "Tomato___Target_Spot": {
        "display_name": "Tomato Target Spot",
        "crop": "Tomato",
        "scientific_name": "Corynespora cassiicola",
        "treatment": "Apply Azoxystrobin 23% SC at 1ml/L. Remove lower infected leaves. "
                     "Improve air circulation.",
        "pesticide": "Azoxystrobin 23% SC (Amistar)",
        "prevention": "Crop rotation. Proper plant spacing. Destroy crop residues.",
    },
    "Tomato___YellowLeaf_Curl_Virus": {
        "display_name": "Tomato Yellow Leaf Curl Virus",
        "crop": "Tomato",
        "scientific_name": "TYLCV (Geminiviridae)",
        "treatment": "No direct cure. Control whitefly vectors with Imidacloprid 17.8% SL "
                     "at 0.3ml/L. Remove and destroy infected plants immediately.",
        "pesticide": "Imidacloprid 17.8% SL (Confidor)",
        "prevention": "Use resistant varieties. Install yellow sticky traps. Use nylon net screens.",
    },
    "Tomato___Mosaic_Virus": {
        "display_name": "Tomato Mosaic Virus",
        "crop": "Tomato",
        "scientific_name": "ToMV",
        "treatment": "No chemical cure. Remove and burn infected plants. Disinfect tools with "
                     "10% sodium hypochlorite. Wash hands before handling healthy plants.",
        "pesticide": "None (control via sanitation)",
        "prevention": "Use virus-free seeds. Resistant varieties. No tobacco near plants.",
    },
    "Tomato___healthy": {
        "display_name": "Healthy Tomato Plant",
        "crop": "Tomato",
        "treatment": "No treatment needed. Continue regular care and balanced fertilization (NPK 19:19:19).",
        "pesticide": "None required",
        "prevention": "Maintain good agricultural practices.",
    },
    "Wheat___Brown_Rust": {
        "display_name": "Wheat Brown/Leaf Rust",
        "crop": "Wheat",
        "scientific_name": "Puccinia triticina",
        "treatment": "Apply Propiconazole 25% EC at 1ml/L at first sign of orange-brown pustules. "
                     "Spray in evening for best absorption. Repeat after 15 days. 500ml/acre.",
        "pesticide": "Propiconazole 25% EC (Tilt 25 EC)",
        "prevention": "Use resistant varieties: PBW 725, HD 3086, WH 1270. Early sowing reduces risk.",
    },
    "Wheat___Yellow_Rust": {
        "display_name": "Wheat Yellow/Stripe Rust",
        "crop": "Wheat",
        "scientific_name": "Puccinia striiformis f. sp. tritici",
        "treatment": "IMMEDIATE spray of Propiconazole 25% EC at 1ml/L. Most damaging wheat rust — "
                     "early treatment critical. Spray entire field. Second spray after 15 days.",
        "pesticide": "Propiconazole 25% EC (Tilt 25 EC)",
        "prevention": "Plant resistant varieties (HD 3086, PBW 725). Monitor from January.",
    },
    "Wheat___Loose_Smut": {
        "display_name": "Wheat Loose Smut",
        "crop": "Wheat",
        "scientific_name": "Ustilago tritici",
        "treatment": "Seed treatment: Carboxin 75% WP (Vitavax) at 2g/kg seed before sowing. "
                     "Rogue out infected earheads before spore dispersal.",
        "pesticide": "Carboxin 75% WP (Vitavax Power)",
        "prevention": "Always use treated seeds. Use certified disease-free seed.",
    },
    "Wheat___Karnal_Bunt": {
        "display_name": "Wheat Karnal Bunt",
        "crop": "Wheat",
        "scientific_name": "Tilletia indica",
        "treatment": "Spray Propiconazole 25% EC at boot leaf/flag leaf stage. "
                     "Seed treatment: Thiram 75% WP at 2.5g/kg seed.",
        "pesticide": "Propiconazole 25% EC (Tilt 25 EC)",
        "prevention": "Use certified Karnal bunt-free seed. Avoid late sowing.",
    },
    "Wheat___healthy": {
        "display_name": "Healthy Wheat Plant",
        "crop": "Wheat",
        "treatment": "No treatment needed. Continue balanced NPK fertilization (120:60:40 kg/ha).",
        "pesticide": "None required",
        "prevention": "Follow recommended agronomic practices.",
    },
    "Rice___Leaf_Blast": {
        "display_name": "Rice Leaf Blast",
        "crop": "Rice",
        "scientific_name": "Magnaporthe oryzae",
        "treatment": "Apply Tricyclazole 75% WP at 0.6g/L. Reduce nitrogen. "
                     "Maintain 2-3 cm water in paddy. 300g/acre.",
        "pesticide": "Tricyclazole 75% WP (Beam 75 WP)",
        "prevention": "Use resistant varieties (Pusa Basmati-1, PR-121). Balanced nitrogen.",
    },
    "Rice___Brown_Spot": {
        "display_name": "Rice Brown Spot",
        "crop": "Rice",
        "scientific_name": "Bipolaris oryzae",
        "treatment": "Apply Mancozeb 75% WP at 2.5g/L. Ensure balanced fertilization "
                     "especially potassium (60 kg/ha K2O). Indicates nutrient-deficient soil.",
        "pesticide": "Mancozeb 75% WP (Dithane M-45)",
        "prevention": "Soil testing and balanced fertilization. Treat seed with Carbendazim.",
    },
    "Rice___Bacterial_Blight": {
        "display_name": "Rice Bacterial Leaf Blight",
        "crop": "Rice",
        "scientific_name": "Xanthomonas oryzae pv. oryzae",
        "treatment": "Drain field 3-4 days. Apply Streptocycline 0.5g + Copper Oxychloride "
                     "2.5g per liter. Reduce nitrogen.",
        "pesticide": "Streptocycline + Copper Oxychloride (COC 50% WP)",
        "prevention": "Use resistant varieties (PR-126, Pusa-44). Proper drainage.",
    },
    "Rice___Leaf_Smut": {
        "display_name": "Rice Leaf Smut",
        "crop": "Rice",
        "scientific_name": "Entyloma oryzae",
        "treatment": "Spray Carbendazim 50% WP at 1g/L or Propiconazole 25% EC at 1ml/L.",
        "pesticide": "Carbendazim 50% WP (Bavistin)",
        "prevention": "Use disease-free seeds. Field sanitation.",
    },
    "Rice___Hispa": {
        "display_name": "Rice Hispa (Blue Beetle)",
        "crop": "Rice",
        "scientific_name": "Dicladispa armigera",
        "treatment": "Spray Chlorpyriphos 20% EC at 2.5ml/L or Cartap Hydrochloride 4G "
                     "at 18-20 kg/ha in standing water.",
        "pesticide": "Chlorpyriphos 20% EC (Dursban)",
        "prevention": "Avoid close planting. Remove weedy hosts.",
    },
    "Rice___Sheath_Blight": {
        "display_name": "Rice Sheath Blight",
        "crop": "Rice",
        "scientific_name": "Rhizoctonia solani",
        "treatment": "Spray Hexaconazole 5% EC at 2ml/L or Validamycin 3% SL at 2ml/L. "
                     "Direct spray to lower sheaths.",
        "pesticide": "Hexaconazole 5% EC (Contaf 5 EC)",
        "prevention": "Avoid excess nitrogen. Proper spacing (20×15 cm).",
    },
    "Rice___healthy": {
        "display_name": "Healthy Rice Plant",
        "crop": "Rice",
        "treatment": "No treatment needed. Continue balanced fertilization (120:60:40 NPK kg/ha).",
        "pesticide": "None required",
        "prevention": "Maintain standing water (5cm). Follow PAU practices.",
    },
    "Potato___Early_blight": {
        "display_name": "Potato Early Blight",
        "crop": "Potato",
        "scientific_name": "Alternaria solani",
        "treatment": "Apply Mancozeb 75% WP at 2.5g/L. Remove lower affected leaves. Hill up soil.",
        "pesticide": "Mancozeb 75% WP (Dithane M-45)",
        "prevention": "Use certified disease-free seed tubers. Rotate crops.",
    },
    "Potato___Late_blight": {
        "display_name": "Potato Late Blight",
        "crop": "Potato",
        "scientific_name": "Phytophthora infestans",
        "treatment": "Apply Cymoxanil + Mancozeb at 3g/L urgently. Treat entire field immediately.",
        "pesticide": "Cymoxanil 8% + Mancozeb 64% WP (Curzate M-8)",
        "prevention": "Plant resistant varieties (Kufri Badshah, Kufri Giriraj). Monitor humidity.",
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
        "scientific_name": "Puccinia sorghi",
        "treatment": "Apply Mancozeb 75% WP at 2.5g/L for early infection. "
                     "Severe cases: Propiconazole 25% EC at 1ml/L.",
        "pesticide": "Mancozeb 75% WP or Propiconazole 25% EC",
        "prevention": "Plant rust-resistant hybrids. Early planting.",
    },
    "Corn___Northern_Leaf_Blight": {
        "display_name": "Corn Northern Leaf Blight",
        "crop": "Corn",
        "scientific_name": "Exserohilum turcicum",
        "treatment": "Apply Propiconazole 25% EC at 1ml/L when lesions first appear.",
        "pesticide": "Propiconazole 25% EC (Tilt 25 EC)",
        "prevention": "Crop rotation. Bury crop residue. Use resistant hybrids.",
    },
    "Corn___healthy": {
        "display_name": "Healthy Corn Plant",
        "crop": "Corn",
        "treatment": "No treatment needed.",
        "pesticide": "None required",
        "prevention": "Continue standard practices.",
    },
    "Pepper___Bacterial_spot": {
        "display_name": "Pepper Bacterial Spot",
        "crop": "Pepper",
        "scientific_name": "Xanthomonas campestris pv. vesicatoria",
        "treatment": "Spray Copper Hydroxide 77% WP at 2g/L. Avoid overhead irrigation.",
        "pesticide": "Copper Hydroxide 77% WP (Kocide 3000)",
        "prevention": "Use certified disease-free seeds.",
    },
    "Pepper___healthy": {
        "display_name": "Healthy Pepper Plant",
        "crop": "Pepper",
        "treatment": "No treatment needed.",
        "pesticide": "None required",
        "prevention": "Regular monitoring.",
    },
}

# Map keywords to diseases for demo classification fallback
KEYWORD_DISEASE_MAP = {
    "tomato": [k for k in DISEASE_DATABASE if k.startswith("Tomato")],
    "tamatar": [k for k in DISEASE_DATABASE if k.startswith("Tomato")],
    "wheat": [k for k in DISEASE_DATABASE if k.startswith("Wheat")],
    "gehu": [k for k in DISEASE_DATABASE if k.startswith("Wheat")],
    "rice": [k for k in DISEASE_DATABASE if k.startswith("Rice")],
    "chawal": [k for k in DISEASE_DATABASE if k.startswith("Rice")],
    "dhaan": [k for k in DISEASE_DATABASE if k.startswith("Rice")],
    "potato": [k for k in DISEASE_DATABASE if k.startswith("Potato")],
    "aloo": [k for k in DISEASE_DATABASE if k.startswith("Potato")],
    "corn": [k for k in DISEASE_DATABASE if k.startswith("Corn")],
    "maize": [k for k in DISEASE_DATABASE if k.startswith("Corn")],
    "makka": [k for k in DISEASE_DATABASE if k.startswith("Corn")],
    "pepper": [k for k in DISEASE_DATABASE if k.startswith("Pepper")],
    "shimla": [k for k in DISEASE_DATABASE if k.startswith("Pepper")],
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
        _class_labels = {str(i): key for i, key in enumerate(DISEASE_DATABASE.keys())}
        logger.info("Using built-in class labels (%d classes)", len(_class_labels))
    return _class_labels


def _load_model():
    """Lazy-load the PyTorch model. Returns None if model file doesn't exist."""
    global _model, _device, _transforms
    if _model is not None:
        return _model

    model_path = Path(settings.classifier_model_path)
    if not model_path.exists():
        logger.warning("Model file not found at %s — will use GPT-4o Vision", model_path)
        return None

    try:
        import torch
        import torchvision.transforms as T
        from torchvision import models

        _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        num_classes = len(DISEASE_DATABASE)
        model = models.efficientnet_b0(weights=None)
        model.classifier[1] = torch.nn.Linear(model.classifier[1].in_features, num_classes)
        state_dict = torch.load(str(model_path), map_location=_device, weights_only=True)
        model.load_state_dict(state_dict)
        model.to(_device)
        model.eval()
        _transforms = T.Compose([
            T.Resize((224, 224)), T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        _model = model
        logger.info("Classifier model loaded (%d classes)", num_classes)
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


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  GPT-4o Vision Classification (REAL)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def _openai_vision_classify(image_data: bytes, request_id: str) -> DiagnoseImageResponse:
    """Classify a crop image using GPT-4o Vision API."""
    logger.info("[%s] Using GPT-4o Vision API for classification", request_id)

    img_b64 = base64.b64encode(image_data).decode("utf-8")
    mime = "image/jpeg"
    if image_data[:4] == b'\x89PNG':
        mime = "image/png"
    elif image_data[:4] == b'RIFF':
        mime = "image/webp"

    payload = {
        "model": settings.openai_model,
        "messages": [
            {"role": "system", "content": VISION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Identify the crop disease in this leaf image. Provide your analysis as JSON."},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b64}", "detail": "high"}},
                ],
            },
        ],
        "max_tokens": 500,
        "temperature": 0.2,
    }

    async with httpx.AsyncClient(timeout=VISION_TIMEOUT) as client:
        response = await client.post(
            OPENAI_VISION_URL, json=payload,
            headers={"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"},
        )
        response.raise_for_status()

    result = response.json()
    content = result["choices"][0]["message"]["content"].strip()

    # Parse JSON (handle markdown code blocks)
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    vision_result = json.loads(content)
    logger.info("[%s] GPT-4o Vision result: %s", request_id, json.dumps(vision_result, indent=2)[:300])

    predictions: List[DiagnosisPrediction] = []
    for pred in vision_result.get("predictions", [])[:3]:
        disease_key = pred.get("disease_key", "")
        confidence = float(pred.get("confidence", 0.5))
        display_name = pred.get("disease_name", "Unknown Disease")

        matched_key = _fuzzy_match_disease(disease_key, display_name)
        if matched_key:
            predictions.append(_build_prediction(matched_key, confidence))
        else:
            predictions.append(DiagnosisPrediction(
                disease_name=display_name, confidence=confidence,
                treatment=f"Identified by AI: {display_name}. Consult a local agronomist.",
                pesticide="Consult local agricultural supply shop",
            ))

    if not predictions:
        analysis = vision_result.get("analysis", "Unable to identify disease")
        predictions.append(DiagnosisPrediction(
            disease_name="Unidentified", confidence=0.3,
            treatment=f"AI Analysis: {analysis}. Consult a local agronomist.",
            pesticide="Consult agricultural expert",
        ))

    top = predictions[0]
    logger.info("[%s] Vision classification: %s (%.1f%%)", request_id, top.disease_name, top.confidence * 100)

    return DiagnoseImageResponse(
        predictions=predictions, top_disease=top.disease_name,
        top_confidence=top.confidence, treatment=top.treatment,
        pesticide=top.pesticide, model_version="gpt-4o-vision",
    )


def _fuzzy_match_disease(disease_key: str, display_name: str) -> Optional[str]:
    """Try to match a GPT-given disease key to our local database."""
    if disease_key in DISEASE_DATABASE:
        return disease_key
    normalized = disease_key.replace(" ", "_").replace("-", "_")
    if normalized in DISEASE_DATABASE:
        return normalized
    display_lower = display_name.lower()
    for key, info in DISEASE_DATABASE.items():
        db_display = info.get("display_name", "").lower()
        if any(word in display_lower for word in db_display.split() if len(word) > 4):
            return key
    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Main Classification Entry Point
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def classify_image(
    image_data: bytes, filename: str = "image.jpg", request_id: str = "",
) -> DiagnoseImageResponse:
    """
    Classify a crop image for disease detection.
    Pipeline: Demo mock → PyTorch model → GPT-4o Vision → Demo fallback
    """
    logger.info("[%s] Classification request: filename=%s, size=%.1fKB", request_id, filename, len(image_data) / 1024)

    if settings.is_demo and settings.mock_ai_responses:
        return _demo_classify(filename, request_id)

    model = _load_model()
    if model is not None:
        try:
            return await _real_inference(image_data, request_id)
        except Exception as e:
            logger.error("[%s] Model inference failed: %s", request_id, str(e))

    if settings.openai_api_key and not settings.mock_ai_responses:
        try:
            return await _openai_vision_classify(image_data, request_id)
        except Exception as e:
            logger.error("[%s] GPT-4o Vision failed: %s", request_id, str(e))

    logger.warning("[%s] All classifiers failed, using demo fallback", request_id)
    return _demo_classify(filename, request_id)


async def _real_inference(image_data: bytes, request_id: str) -> DiagnoseImageResponse:
    """Run actual PyTorch model inference."""
    import torch
    from PIL import Image

    image = Image.open(io.BytesIO(image_data)).convert("RGB")
    input_tensor = _transforms(image).unsqueeze(0).to(_device)

    with torch.no_grad():
        outputs = _model(input_tensor)
        probabilities = torch.nn.functional.softmax(outputs[0], dim=0)

    labels = _load_class_labels()
    top_k = min(3, len(labels))
    top_probs, top_indices = torch.topk(probabilities, top_k)

    predictions = []
    for prob, idx in zip(top_probs.cpu().numpy(), top_indices.cpu().numpy()):
        class_key = labels.get(str(idx), f"Unknown_class_{idx}")
        predictions.append(_build_prediction(class_key, float(prob)))

    top = predictions[0]
    return DiagnoseImageResponse(
        predictions=predictions, top_disease=top.disease_name,
        top_confidence=top.confidence, treatment=top.treatment,
        pesticide=top.pesticide, model_version="v1.0-efficientnet",
    )


def _demo_classify(filename: str, request_id: str) -> DiagnoseImageResponse:
    """Intelligent demo classification based on filename keywords."""
    import random
    filename_lower = filename.lower()

    matched_classes = None
    for keyword, classes in KEYWORD_DISEASE_MAP.items():
        if keyword in filename_lower:
            matched_classes = classes
            break

    if matched_classes is None:
        disease_keys = [k for k in DISEASE_DATABASE.keys() if "healthy" not in k.lower()]
        matched_classes = random.sample(disease_keys, min(3, len(disease_keys)))

    non_healthy = [c for c in matched_classes if "healthy" not in c.lower()]
    primary_key = random.choice(non_healthy) if non_healthy else matched_classes[0]
    primary_conf = round(random.uniform(0.82, 0.96), 3)
    predictions = [_build_prediction(primary_key, primary_conf)]

    remaining = [c for c in matched_classes if c != primary_key]
    for i, class_key in enumerate(remaining[:2]):
        conf = round(primary_conf - random.uniform(0.15 + i * 0.1, 0.25 + i * 0.1), 3)
        predictions.append(_build_prediction(class_key, max(conf, 0.05)))

    top = predictions[0]
    return DiagnoseImageResponse(
        predictions=predictions, top_disease=top.disease_name,
        top_confidence=top.confidence, treatment=top.treatment,
        pesticide=top.pesticide, model_version="v1.0-demo",
    )
