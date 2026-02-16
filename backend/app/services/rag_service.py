"""
RAG (Retrieval-Augmented Generation) Service

Provides agricultural knowledge retrieval using FAISS vector store.
When FAISS index is unavailable, falls back to an in-memory keyword-based
knowledge base covering crop diseases, treatments, and agronomic practices.

Pipeline:
1. Load FAISS index + embeddings (lazy, on first call)
2. Embed user query
3. Retrieve top-k relevant documents
4. Return with relevance scores

Demo mode uses TF-IDF-style keyword matching over the built-in knowledge base.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger("service.rag")
settings = get_settings()

# ── Lazy-loaded globals ───────────────────────────
# ── Lazy-loaded globals ───────────────────────────
_faiss_index = None
_embeddings_model = None
_documents: Optional[List[Dict]] = None

STOPWORDS = {
    "why", "are", "my", "is", "the", "in", "at", "on", "to", "for", "of", "with",
    "a", "an", "and", "or", "but", "if", "then", "else", "when", "how", "do", "does",
    "did", "can", "could", "should", "would", "will", "what", "where", "who", "whom",
    "kya", "kyon", "kaise", "kab", "kahan", "hai", "hain", "ho", "hu", "mera", "meri",
    "mere", "ke", "ki", "ka", "se", "me", "mein", "par", "ko", "ne", "bhi", "hi",
}


@dataclass
class KnowledgeResult:
    """A single knowledge retrieval result."""
    title: str
    content: str
    relevance_score: float
    category: str = ""
    source: str = "knowledge_base"


# ─────────────────────────────────────────────────
# In-Memory Agricultural Knowledge Base
# ─────────────────────────────────────────────────

KNOWLEDGE_BASE: List[Dict[str, str]] = [
    # ── Tomato Diseases ───────────────────────────
    {
        "title": "Tomato Early Blight (Alternaria solani)",
        "category": "disease",
        "keywords": "tomato tamatar early blight ageti jhulsa dark spots concentric rings lower leaves alternaria",
        "content": (
            "**Tomato Early Blight** is caused by the fungus Alternaria solani. "
            "Symptoms: Dark brown to black spots with concentric rings (target-like pattern) "
            "appearing first on older lower leaves. Spots may have yellow halos.\n\n"
            "**Treatment:**\n"
            "• Apply Mancozeb 75% WP at 2.5g/litre of water\n"
            "• Alternatively, use Chlorothalonil at 2g/litre\n"
            "• Spray at 10-14 day intervals during humid weather\n"
            "• Remove and destroy affected leaves\n\n"
            "**Prevention:**\n"
            "• Use certified disease-free seeds\n"
            "• Maintain adequate spacing (60cm between plants)\n"
            "• Avoid overhead irrigation\n"
            "• Rotate crops — do not plant tomatoes in same field for 3 years\n"
            "• Mulch around plants to prevent soil splash"
        ),
    },
    {
        "title": "Tomato Late Blight (Phytophthora infestans)",
        "category": "disease",
        "keywords": "tomato tamatar late blight picheti jhulsa water soaked lesions white mold phytophthora rapid",
        "content": (
            "**Tomato Late Blight** is caused by Phytophthora infestans — the same pathogen "
            "that caused the Irish Potato Famine. It is highly destructive and spreads rapidly.\n\n"
            "Symptoms: Large, irregular, water-soaked greenish-black lesions on leaves. "
            "White fuzzy mold on leaf undersides in humid conditions. Fruit develops firm, "
            "dark, greasy-looking spots.\n\n"
            "**Treatment (URGENT — treat immediately):**\n"
            "• Apply Copper Oxychloride 50% WP at 3g/litre\n"
            "• Or Metalaxyl + Mancozeb (Ridomil Gold) at 2.5g/litre\n"
            "• Spray entire field including unaffected plants\n"
            "• Remove and BURN infected plants (do not compost)\n\n"
            "**Prevention:**\n"
            "• Plant resistant varieties\n"
            "• Avoid planting near potato fields\n"
            "• Ensure good airflow — stake and prune plants\n"
            "• Do not irrigate from above"
        ),
    },
    # ── Wheat Diseases ────────────────────────────
    {
        "title": "Wheat Leaf Rust / Brown Rust (Puccinia triticina)",
        "category": "disease",
        "keywords": "wheat gehu rust brown leaf puccinia orange pustules geru rog",
        "content": (
            "**Wheat Leaf Rust (Brown Rust)** is caused by Puccinia triticina. "
            "It is the most common wheat rust in Punjab and Haryana.\n\n"
            "Symptoms: Small, round, orange-brown pustules scattered on upper leaf surface. "
            "Pustules are lighter in color than stem rust.\n\n"
            "**Treatment:**\n"
            "• Apply Propiconazole 25% EC at 1ml/litre of water\n"
            "• Spray at first sign of pustules\n"
            "• Repeat after 15 days if symptoms persist\n"
            "• Best time to spray: evening (4-6 PM)\n\n"
            "**PAU Recommendations:**\n"
            "• Resistant varieties: PBW 343, HD 2967, WH 1105\n"
            "• Monitor fields from mid-January\n"
            "• Early sowing (late October) reduces risk\n"
            "• Do not over-apply nitrogen fertilizer"
        ),
    },
    {
        "title": "Wheat Yellow Rust / Stripe Rust (Puccinia striiformis)",
        "category": "disease",
        "keywords": "wheat gehu yellow stripe rust puccinia striiformis peeli dhariyan geru",
        "content": (
            "**Wheat Yellow Rust (Stripe Rust)** is the most damaging wheat rust. "
            "Caused by Puccinia striiformis f. sp. tritici.\n\n"
            "Symptoms: Yellow-orange pustules arranged in stripes along leaf veins. "
            "More prominent on young upper leaves. Favored by cool temperatures (10-15°C).\n\n"
            "**Treatment (VERY URGENT):**\n"
            "• Apply Propiconazole 25% EC at 1ml/litre IMMEDIATELY\n"
            "• This is a yield-devastating disease — delay = major crop loss\n"
            "• Spray entire field\n"
            "• Contact your nearest Krishi Vigyan Kendra (KVK) for guidance\n\n"
            "**Prevention:**\n"
            "• Plant resistant varieties recommended by PAU\n"
            "• Early sowing helps avoid peak infection period"
        ),
    },
    # ── Rice Diseases ─────────────────────────────
    {
        "title": "Rice Blast (Magnaporthe oryzae)",
        "category": "disease",
        "keywords": "rice chawal dhaan blast magnaporthe diamond spots leaf neck",
        "content": (
            "**Rice Blast** is caused by the fungus Magnaporthe oryzae. "
            "It is the most destructive rice disease worldwide.\n\n"
            "Symptoms: Diamond-shaped spots with grey centers and dark borders on leaves. "
            "Can also affect neck (neck blast), causing panicle to break.\n\n"
            "**Treatment:**\n"
            "• Apply Tricyclazole 75% WP at 0.6g/litre\n"
            "• Or Isoprothiolane 40% EC at 1.5ml/litre\n"
            "• Spray at tillering and panicle emergence stages\n\n"
            "**Prevention:**\n"
            "• Use resistant varieties: Pusa Basmati-1, PR-114\n"
            "• Balanced nitrogen — excess N increases susceptibility\n"
            "• Maintain 2-3 cm standing water in paddy\n"
            "• Remove weed hosts from field bunds"
        ),
    },
    {
        "title": "Green Potatoes (Solanine Toxicity)",
        "category": "safety",
        "keywords": "potato aloo green hari solanine sun light poison toxic zelene",
        "content": (
            "**Why are potatoes turning green?**\n"
            "This is caused by exposure to **sunlight**, which produces chlorophyll (green color) "
            "and a toxic compound called **Solanine**.\n\n"
            "**Is it safe to eat?**\n"
            "• **NO**, solanine is toxic and can cause nausea, headaches, and stomach pain.\n"
            "• If greening is slight, peel away the green part deeply.\n"
            "• If the potato is mostly green, **throw it away**.\n\n"
            "**Prevention:**\n"
            "• Store potatoes in a cool, dark place (not on the balcony!)\n"
            "• Hill up soil around potato plants to cover tubers completely\n"
            "• Do not wash potatoes until you are ready to use them"
        ),
    },
    # ── Potato Diseases ───────────────────────────
    {
        "title": "Potato Late Blight (Phytophthora infestans)",
        "category": "disease",
        "keywords": "potato aloo late blight phytophthora water soaked dark brown",
        "content": (
            "**Potato Late Blight** is the most devastating potato disease, caused by "
            "Phytophthora infestans. Can destroy entire crop within days.\n\n"
            "Symptoms: Water-soaked dark lesions on leaves, starting from tips and margins. "
            "White mold on undersides. Tubers develop firm, brownish rot.\n\n"
            "**Treatment:**\n"
            "• Apply Cymoxanil 8% + Mancozeb 64% WP at 3g/litre\n"
            "• Or Metalaxyl + Mancozeb at 2.5g/litre\n"
            "• Spray every 7-10 days during humid weather\n\n"
            "**Prevention:**\n"
            "• Use certified disease-free seed tubers\n"
            "• Plant resistant varieties: Kufri Jyoti, Kufri Bahar\n"
            "• Hill up soil to protect tubers\n"
            "• Destroy volunteer plants and crop debris"
        ),
    },
    # ── General Crop Care ─────────────────────────
    {
        "title": "Integrated Pest Management (IPM) for Farmers",
        "category": "treatment",
        "keywords": "ipm integrated pest management organic prevention biological control neem",
        "content": (
            "**Integrated Pest Management (IPM)** combines multiple strategies to manage "
            "pests while minimizing chemical use.\n\n"
            "**Key IPM practices:**\n"
            "1. **Cultural control**: Crop rotation, proper spacing, timely sowing\n"
            "2. **Biological control**: Use of Trichoderma, Pseudomonas, neem-based products\n"
            "3. **Mechanical control**: Pheromone traps, light traps, manual removal\n"
            "4. **Chemical control**: Use only as last resort, follow recommended dosages\n\n"
            "**Neem-based solutions:**\n"
            "• Neem oil 3000 ppm at 5ml/litre for sucking pests\n"
            "• Neem cake at 250 kg/hectare mixed in soil for nematode control"
        ),
    },
    {
        "title": "Pesticide Safety Guidelines for Farmers",
        "category": "safety",
        "keywords": "pesticide safety guidelines mixing spraying precautions health keetnashak suraksha",
        "content": (
            "**Pesticide Safety Guidelines:**\n\n"
            "**Before spraying:**\n"
            "• Read label carefully — follow exact dosage\n"
            "• Wear protective clothing: gloves, mask, goggles\n"
            "• Mix pesticides in open, well-ventilated areas\n"
            "• Never mix different pesticides unless recommended\n\n"
            "**During spraying:**\n"
            "• Spray in early morning or evening (avoid wind)\n"
            "• Walk with wind direction, not against it\n"
            "• Do not eat, drink, or smoke while spraying\n\n"
            "**After spraying:**\n"
            "• Wash hands and face thoroughly with soap\n"
            "• Bathe and change clothes after spraying\n"
            "• Observe waiting period before harvest\n"
            "• Dispose of empty containers safely — never reuse for food/water"
        ),
    },
    {
        "title": "Soil Health and Fertilization Guide",
        "category": "agronomy",
        "keywords": "soil health fertilizer npk urea dap potash mitti khaad",
        "content": (
            "**Soil Health Management:**\n\n"
            "**Get your soil tested!** Visit nearest Soil Testing Lab or KVK.\n\n"
            "**Key nutrients:**\n"
            "• **Nitrogen (N)**: For vegetative growth — Urea (46% N)\n"
            "• **Phosphorus (P)**: For root and flower development — DAP (18% N, 46% P)\n"
            "• **Potassium (K)**: For disease resistance and fruit quality — MOP (60% K)\n\n"
            "**General recommendations:**\n"
            "• Apply farmyard manure (FYM) at 10 tonnes/hectare before sowing\n"
            "• Split nitrogen application: 50% at sowing, 25% at 30 days, 25% at 60 days\n"
            "• Apply full dose of P and K at sowing\n"
            "• For zinc deficiency: Zinc Sulphate at 25 kg/hectare"
        ),
    },
    {
        "title": "Water Management and Irrigation",
        "category": "agronomy",
        "keywords": "water irrigation sinchai pani drip sprinkler flood canal",
        "content": (
            "**Efficient Water Management:**\n\n"
            "**Drip Irrigation** saves 40-60% water compared to flood irrigation.\n"
            "Government subsidies available (up to 90% for small farmers).\n\n"
            "**Crop-specific irrigation:**\n"
            "• **Wheat**: 4-5 irrigations at CRI, tillering, jointing, flowering, grain filling\n"
            "• **Rice**: Maintain 2-3 cm standing water. AWD technique saves 25% water\n"
            "• **Potato**: Regular irrigation every 7-10 days. Avoid waterlogging\n"
            "• **Tomato**: Critical at flowering and fruit set. Avoid wetting foliage\n\n"
            "**Signs of water stress:**\n"
            "• Wilting in afternoon that doesn't recover next morning\n"
            "• Leaf rolling (in rice and maize)\n"
            "• Light green or yellowing leaves"
        ),
    },
    {
        "title": "Onion Black Mold / Smut (Aspergillus niger)",
        "category": "disease",
        "keywords": "onion pyaz kanda black mold smut kaali fafundi leaves bulb storage",
        "content": (
            "**Onion Black Mold** is a common fungal disease in hot climates.\n\n"
            "**Symptoms:**\n"
            "• Black powdery masses of spores on outer scales of bulb\n"
            "• Black streaks on leaves and neck\n"
            "• Bulbs shrivel and rot in storage\n\n"
            "**Treatment:**\n"
            "• Seed treatment with Carbendazim at 2g/kg\n"
            "• Spray Mancozeb 0.25% or Tricyclazole 0.1%\n"
            "• Ensure proper curing (drying) of bulbs before storage\n\n"
            "**Prevention:**\n"
            "• Store in cool, well-ventilated rooms\n"
            "• Avoid injury to bulbs during harvest"
        ),
    },
    {
        "title": "Chilli/Pepper Bacterial Spot (Xanthomonas campestris)",
        "category": "disease",
        "keywords": "chilli pepper mirch capsicum bacterial spot leaf fruit dark lesions",
        "content": (
            "**Bacterial Spot in Chilli/Pepper** is caused by Xanthomonas campestris.\n\n"
            "**Symptoms:**\n"
            "• Small, irregular, water-soaked spots on leaves\n"
            "• Spots turn dark brown with yellow halos\n"
            "• Leaves turn yellow and drop (defoliation)\n"
            "• Raised, wart-like brown spots on fruit\n\n"
            "**Treatment:**\n"
            "• Spray Copper Oxychloride (3g/L) + Streptocycline (1g/10L)\n"
            "• Repeat every 10-12 days\n\n"
            "**Prevention:**\n"
            "• Use disease-free seeds\n"
            "• Crop rotation with non-solanaceous crops (corn, beans)"
        ),
    },
]


# ─────────────────────────────────────────────────
# Load structured JSON knowledge files at import time
# ─────────────────────────────────────────────────

def _load_knowledge_json_files() -> List[Dict[str, str]]:
    """Load disease knowledge from ai-service/data/knowledge_base/*.json"""
    entries: List[Dict[str, str]] = []

    kb_dir = Path(__file__).parent.parent.parent.parent / "ai-service" / "data" / "knowledge_base"
    if not kb_dir.exists():
        logger.info("Knowledge base directory not found at %s — skipping JSON load", kb_dir)
        return entries

    for json_file in sorted(kb_dir.glob("*.json")):
        try:
            diseases = json.loads(json_file.read_text(encoding="utf-8"))
            for d in diseases:
                # Build keyword string from fields
                keywords_parts = [
                    d.get("crop", "").lower(),
                    d.get("disease_name", "").lower(),
                    d.get("hindi_name", ""),
                    d.get("scientific_name", "").lower(),
                    " ".join(d.get("symptoms", []))[:200].lower(),
                ]

                # Build content string
                symptoms_text = "\n".join(f"• {s}" for s in d.get("symptoms", []))
                treatment_text = "\n".join(f"• {t}" for t in d.get("treatment", []))
                prevention_text = "\n".join(f"• {p}" for p in d.get("prevention", []))

                pesticide = d.get("recommended_pesticide", {})
                pesticide_text = ""
                if isinstance(pesticide, dict) and pesticide.get("name"):
                    pesticide_text = (
                        f"\n\n**Recommended Pesticide:** {pesticide['name']}\n"
                        f"• Dosage: {pesticide.get('dosage', 'N/A')}\n"
                        f"• Interval: {pesticide.get('spray_interval', 'N/A')}\n"
                        f"• Waiting period: {pesticide.get('waiting_period', 'N/A')}"
                    )

                content = (
                    f"**{d.get('disease_name', '')}** ({d.get('hindi_name', '')})\n"
                    f"Caused by: {d.get('cause', 'Unknown')}\n\n"
                    f"**Symptoms:**\n{symptoms_text}\n\n"
                    f"**Treatment:**\n{treatment_text}\n\n"
                    f"**Prevention:**\n{prevention_text}"
                    f"{pesticide_text}"
                )

                entries.append({
                    "title": f"{d.get('disease_name', 'Unknown')} ({d.get('scientific_name', '')})",
                    "category": "disease",
                    "keywords": " ".join(keywords_parts),
                    "content": content,
                })

            logger.info("Loaded %d diseases from %s", len(diseases), json_file.name)

        except Exception as e:
            logger.warning("Failed to load knowledge file %s: %s", json_file.name, str(e))

    return entries


# Merge JSON knowledge into the in-memory knowledge base
_json_entries = _load_knowledge_json_files()
if _json_entries:
    KNOWLEDGE_BASE.extend(_json_entries)
    logger.info("Knowledge base total: %d entries (%d from JSON)", len(KNOWLEDGE_BASE), len(_json_entries))


def _tokenize(text: str) -> List[str]:
    """Simple tokenizer — lowercase, split on non-alphanumeric, remove stopwords."""
    words = re.findall(r'[a-z0-9\u0900-\u097f]+', text.lower())
    return [w for w in words if w not in STOPWORDS]


def _compute_relevance(query_tokens: List[str], doc_keywords: str, doc_content: str) -> float:
    """
    Compute keyword-overlap relevance score between query and document.
    Weighted: keyword matches count 3x, content matches count 1x.
    """
    keyword_tokens = set(_tokenize(doc_keywords))
    content_tokens = set(_tokenize(doc_content))
    query_set = set(query_tokens)

    if not query_set:
        return 0.0

    keyword_hits = len(query_set & keyword_tokens)
    content_hits = len(query_set & content_tokens)

    # Weighted score normalized to 0-1
    raw_score = (keyword_hits * 3.0 + content_hits * 1.0) / (len(query_set) * 3.0)
    return min(1.0, round(raw_score, 3))


def _load_faiss_index():
    """Load FAISS index and embedding model. Returns (index, model) or (None, None)."""
    global _faiss_index, _embeddings_model, _documents

    if _faiss_index is not None:
        return _faiss_index, _embeddings_model

    index_path = Path(settings.faiss_index_path)
    if not index_path.exists():
        logger.warning("FAISS index not found at %s — using in-memory knowledge base", index_path)
        return None, None

    try:
        import faiss
        from langchain_openai import OpenAIEmbeddings

        _faiss_index = faiss.read_index(str(index_path / "index.faiss"))
        _embeddings_model = OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            openai_api_key=settings.openai_api_key,
        )

        # Load document metadata
        import pickle
        meta_path = index_path / "documents.pkl"
        if meta_path.exists():
            with open(meta_path, "rb") as f:
                _documents = pickle.load(f)

        logger.info("FAISS index loaded: %d vectors", _faiss_index.ntotal)
        return _faiss_index, _embeddings_model

    except Exception as e:
        logger.error("Failed to load FAISS index: %s", str(e))
        return None, None


async def _search_faiss(query: str, top_k: int, request_id: str) -> List[KnowledgeResult]:
    """Search using FAISS vector store with OpenAI embeddings."""
    import numpy as np

    logger.info("[%s] FAISS search: '%s' (top_k=%d)", request_id, query[:60], top_k)

    # Embed query
    query_embedding = await _embeddings_model.aembed_query(query)
    query_vector = np.array([query_embedding], dtype="float32")

    # Search
    distances, indices = _faiss_index.search(query_vector, top_k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx < 0:
            continue

        doc = _documents[idx] if _documents and idx < len(_documents) else {}

        # Convert L2 distance to relevance score (0-1)
        relevance = 1.0 / (1.0 + float(dist))

        results.append(
            KnowledgeResult(
                title=doc.get("title", f"Document {idx}"),
                content=doc.get("content", ""),
                relevance_score=round(relevance, 3),
                category=doc.get("category", "general"),
                source="faiss_vector_store",
            )
        )

    return results


def _search_keyword(query: str, top_k: int, request_id: str, crop: Optional[str] = None) -> List[KnowledgeResult]:
    """Search using keyword matching over the in-memory knowledge base."""
    query_tokens = _tokenize(query)

    if not query_tokens:
        logger.warning("[%s] Empty query after tokenization", request_id)
        return []

    scored_docs = []
    
    # Crop aliases for filtering
    crop_aliases = {
        "tomato": ["tomato", "tamatar"],
        "potato": ["potato", "aloo"],
        "rice": ["rice", "chawal", "dhaan", "paddy"],
        "wheat": ["wheat", "gehu", "gehun"],
        "onion": ["onion", "pyaz", "kanda"],
        "pepper": ["pepper", "chilli", "mirch", "capsicum"],
        "corn": ["corn", "maize", "makka"],
    }
    
    target_crop_keywords = crop_aliases.get(crop, []) if crop else []

    for doc in KNOWLEDGE_BASE:
        # ── Crop Filtering Logic ──
        # If a specific crop is requested, SKIP docs that belong to other crops.
        # We determine a doc's crop by checking if its keywords contain any alias of a KNOWN crop.
        doc_keywords_str = doc.get("keywords", "")
        
        if crop and target_crop_keywords:
            # Check if this doc is for the target crop
            is_target_crop = any(alias in doc_keywords_str for alias in target_crop_keywords)
            
            # Check if this doc matches ANY known crop
            is_any_crop = False
            for c_name, aliases in crop_aliases.items():
                if any(alias in doc_keywords_str for alias in aliases):
                    is_any_crop = True
                    break
            
            # If doc is successfully identified as Another Crop, skip it.
            # If doc is General (no crop keywords), keep it.
            if is_any_crop and not is_target_crop:
                continue

        score = _compute_relevance(
            query_tokens,
            doc.get("keywords", ""),
            doc.get("content", ""),
        )
        if score > 0.05:  # Minimum relevance threshold
            scored_docs.append((score, doc))

    # Sort by score descending
    scored_docs.sort(key=lambda x: x[0], reverse=True)

    results = []
    for score, doc in scored_docs[:top_k]:
        results.append(
            KnowledgeResult(
                title=doc["title"],
                content=doc["content"],
                relevance_score=score,
                category=doc.get("category", "general"),
                source="in_memory_knowledge_base",
            )
        )

    return results


async def search_knowledge(
    query: str,
    top_k: int = 3,
    request_id: str = "",
    crop: Optional[str] = None,
) -> List[KnowledgeResult]:
    """
    Main entry point for knowledge retrieval.

    Strategy:
    1. Try FAISS vector search (if index available + OpenAI key configured)
    2. Fall back to keyword-based in-memory search
    3. Return top-k results with relevance scores

    Args:
        query: Search query (Hindi or English)
        top_k: Number of results to return
        request_id: Request tracking ID

    Returns:
        List of KnowledgeResult with title, content, relevance_score
    """
    logger.info("[%s] Knowledge search: '%s' (top_k=%d)", request_id, query[:80], top_k)

    # ── Try FAISS ─────────────────────────────────
    if not (settings.is_demo and settings.mock_ai_responses):
        index, model = _load_faiss_index()
        if index is not None and model is not None:
            try:
                results = await _search_faiss(query, top_k, request_id)
                if results:
                    logger.info("[%s] FAISS returned %d results", request_id, len(results))
                    return results
            except Exception as e:
                logger.error("[%s] FAISS search failed: %s", request_id, str(e))

    # ── Keyword fallback ──────────────────────────
    results = _search_keyword(query, top_k, request_id, crop=crop)
    logger.info("[%s] Keyword search returned %d results", request_id, len(results))

    if not results:
        # Return a generic helpful result
        results = [
            KnowledgeResult(
                title="General Agricultural Advice",
                content=(
                    "For specific crop disease diagnosis, please upload a photo of the affected plant. "
                    "For general queries, contact your nearest Krishi Vigyan Kendra (KVK) or "
                    "call Kisan Call Centre at 1800-180-1551 (toll free)."
                ),
                relevance_score=0.1,
                category="general",
                source="fallback",
            )
        ]

    return results
