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
from sentence_transformers import SentenceTransformer

from app.config import get_settings
from app.utils.logger import get_logger


logger = get_logger("service.rag")
settings = get_settings()

# ── ChromaDB support ─────────────────────────────
try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    _CHROMADB_AVAILABLE = True
except Exception:
    _CHROMADB_AVAILABLE = False

# ── LangChain / Groq support ─────────────────────
try:
    from langchain_groq import ChatGroq
    from langchain_community.embeddings import FastEmbedEmbeddings
    from langchain_community.vectorstores import FAISS as LC_FAISS
    from langchain_core.prompts import PromptTemplate
    from langchain_core.runnables import RunnableParallel, RunnablePassthrough
    from langchain_core.output_parsers import StrOutputParser
    _RAG_CHAIN_AVAILABLE = True
except ImportError:
    _RAG_CHAIN_AVAILABLE = False

# Chroma globals
_chroma_client = None
_chroma_collection = None

# ── Lazy-loaded globals ───────────────────────────
# ── Lazy-loaded globals ───────────────────────────
_faiss_index = None
_embeddings_model = None
_documents: Optional[List[Dict]] = None

_chroma_client = None
_chroma_collection = None
_embedding_model = None


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
    """Load FAISS vectorstore (either raw faiss.Index or langchain_community.FAISS)."""
    global _faiss_index, _embeddings_model, _documents

    if _faiss_index is not None:
        return _faiss_index, _embeddings_model

    index_path = Path(settings.faiss_index_path or "faiss_index")
    # Fallback: check root directory if not found in configured path
    if not index_path.exists():
        root_index = Path("faiss_index")
        if root_index.exists():
            logger.info("FAISS index found in root directory: %s", root_index)
            index_path = root_index

    if not index_path.exists():
        logger.warning("FAISS index not found at %s (or root) — using in-memory knowledge base", index_path)
        return None, None

    # First try to load LangChain-community FAISS store (the one your notebook built)
    try:
        from langchain_community.embeddings import FastEmbedEmbeddings
        from langchain_community.vectorstores import FAISS as LC_FAISS

        # Recreate embeddings (EXACTLY matching notebook)
        emb = FastEmbedEmbeddings(
            model_name="BAAI/bge-small-en-v1.5",
            parallel=1,
            batch_size=64,
        )

        # Try loading the vector store from the directory
        try:
            vs = LC_FAISS.load_local(str(index_path), emb, allow_dangerous_deserialization=True)
            _faiss_index = vs  # store the vectorstore object
            _embeddings_model = emb
            # Attempt to extract docs if the vectorstore stores them
            try:
                _documents = getattr(vs, "docstore", None)
            except Exception:
                _documents = None

            logger.info("LangChain FAISS vector store loaded from %s", index_path)
            return _faiss_index, _embeddings_model
        except Exception as e:
            logger.warning("LangChain FAISS load_local failed: %s", e)
            # fallthrough to raw faiss attempt
    except Exception as e:
        logger.debug("langchain_community.FAISS not available or failed: %s", e)

    # Fallback: try raw faiss index + langchain OpenAI embeddings (old path)
    try:
        import faiss
        from langchain.embeddings import OpenAIEmbeddings

        idx_file = index_path / "index.faiss"
        if not idx_file.exists():
            logger.warning("FAISS index file %s missing — using in-memory knowledge base", idx_file)
            return None, None

        _faiss_index = faiss.read_index(str(idx_file))
        _embeddings_model = OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            openai_api_key=settings.openai_api_key,
        )

        # Load metadata (if present)
        meta_path = index_path / "documents.pkl"
        if meta_path.exists():
            import pickle
            with open(meta_path, "rb") as f:
                _documents = pickle.load(f)
        else:
            logger.warning("FAISS metadata file not found at %s", meta_path)

        logger.info("Raw FAISS index loaded: %d vectors", _faiss_index.ntotal)
        return _faiss_index, _embeddings_model

    except Exception as e:
        logger.error("Failed to load FAISS index: %s", str(e))
        logger.exception(e)
        return None, None


def _load_chroma():
    global _chroma_client, _chroma_collection, _embedding_model

    if _chroma_collection is not None:
        return _chroma_collection

    chroma_path = Path("ai-service/models/chroma_db")

    if not chroma_path.exists():
        logger.warning("Chroma DB not found at %s", chroma_path)
        return None

    try:
        _chroma_client = chromadb.PersistentClient(
            path=str(chroma_path)
        )

        _chroma_collection = _chroma_client.get_collection("crop_knowledge")

        _embedding_model = SentenceTransformer("BAAI/bge-small-en-v1.5")

        logger.info("Chroma DB loaded successfully")

        return _chroma_collection

    except Exception as e:
        logger.error("Chroma load failed: %s", e)
        return None


async def _search_faiss(query: str, top_k: int, request_id: str) -> List[KnowledgeResult]:
    """
    Search that handles either:
      - raw faiss.Index + embeddings model
      - langchain_community.FAISS vectorstore object (preferred if available)
    Returns a list of KnowledgeResult (already unfiltered); caller may filter by relevance.
    """
    logger.info("[%s] FAISS search: '%s' (top_k=%d)", request_id, query[:60], top_k)

    # If _faiss_index is a LangChain FAISS object (vector store), use its retriever
    vs = _faiss_index
    emb = _embeddings_model

    # Attempt path for LangChain FAISS vectorstore
    try:
        # Many vectorstore implementations expose similarity_search/get_relevant_documents/as_retriever
        if vs is not None and not hasattr(vs, "ntotal"):  # heuristic: raw faiss index has ntotal attr
            # Build retriever with a reasonable search type (mmr) if available
            retriever = None
            try:
                retriever = vs.as_retriever(
                    search_type="mmr",
                    search_kwargs={"k": top_k, "fetch_k": max(10, top_k * 4), "lambda_mult": 0.7},
                )
            except Exception:
                # fallback: no as_retriever; try similarity_search API
                retriever = None

            docs = None
            if retriever is not None:
                # try async-style get_relevant_documents if available
                try:
                    if hasattr(retriever, "get_relevant_documents"):
                        docs = retriever.get_relevant_documents(query)
                    elif hasattr(retriever, "invoke"):
                        docs = retriever.invoke(query)
                    else:
                        # some retrievers are callable
                        docs = retriever(query)
                except Exception:
                    logger.exception("[%s] retriever failure, will try vectorstore.similarity_search", request_id)

            if docs is None:
                # fallback to vectorstore similarity_search if available
                try:
                    if hasattr(vs, "similarity_search"):
                        docs = vs.similarity_search(query, k=top_k)
                    elif hasattr(vs, "get_relevant_documents"):
                        docs = vs.get_relevant_documents(query)
                    else:
                        docs = []
                except Exception:
                    logger.exception("[%s] vectorstore similarity_search failed", request_id)
                    docs = []

            output = []
            for d in (docs or []):
                # doc may be a langchain Document
                text = getattr(d, "page_content", None) or getattr(d, "content", None) or str(d)
                meta = getattr(d, "metadata", {}) or {}
                # We don't have a precise distance here; set a conservative relevance (0.8) — RAG will still filter later.
                output.append(
                    KnowledgeResult(
                        title=(meta.get("title") or (text[:80] if isinstance(text, str) else "document")),
                        content=text,
                        relevance_score=0.8,
                        category=meta.get("category", "general"),
                        source="faiss_vector_store",
                    )
                )

            logger.info("[%s] LangChain FAISS returned %d results", request_id, len(output))
            return output

    except Exception:
        logger.exception("[%s] FAISS vectorstore search path failed, falling back to raw faiss", request_id)

    # --- Raw faiss Index path (older code) ---
    try:
        import numpy as np

        # embed query -- try async embed (aembed_query) then fallback to sync embed_query
        query_embedding = None
        try:
            if hasattr(emb, "aembed_query"):
                query_embedding = await emb.aembed_query(query)
            elif hasattr(emb, "embed_query"):
                query_embedding = emb.embed_query(query)
            elif hasattr(emb, "encode"):
                # some local models use encode([...])
                query_embedding = emb.encode([query])[0]
        except Exception:
            logger.exception("[%s] Embedding generation failed (faiss path)", request_id)
            raise

        query_vector = np.array([query_embedding], dtype="float32")
        distances, indices = _faiss_index.search(query_vector, top_k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0:
                continue
            doc = _documents[idx] if _documents and idx < len(_documents) else {}
            relevance = 1.0 / (1.0 + float(dist))
            results.append(
                KnowledgeResult(
                    title=doc.get("title", f"Document {idx}"),
                    content=doc.get("content", ""),
                    relevance_score=round(relevance, 3),
                    category=doc.get("category", "general"),
                    source="faiss_index",
                )
            )

        logger.info("[%s] Raw FAISS returned %d hits", request_id, len(results))
        return results

    except Exception as e:
        logger.exception("[%s] FAISS search failed: %s", request_id, str(e))
        return []


async def _search_chroma(query: str, top_k: int, request_id: str):

    collection = _load_chroma()

    if collection is None:
        return []

    try:
        query_embedding = _embedding_model.encode(query).tolist()

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )

        docs = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]

        filtered = []

        # iterate by index so we handle missing distance entries gracefully
        for i in range(len(docs)):
            doc = docs[i]
            dist = distances[i] if i < len(distances) else None

            if dist is None:
                logger.info("[%s] Chroma candidate missing distance index=%d — skipping", request_id, i)
                continue

            # Convert distance -> similarity-like relevance (0-1)
            try:
                relevance = 1.0 / (1.0 + float(dist))
            except Exception:
                logger.exception("[%s] Failed to convert distance to relevance (dist=%s)", request_id, dist)
                continue

            logger.info("[%s] Chroma candidate relevance=%.3f (idx=%d)", request_id, relevance, i)

            # FILTER OUT LOW-RELEVANCE DOCUMENTS
            if relevance < 0.65:
                logger.info("[%s] Chroma candidate filtered out (relevance=%.3f) idx=%d", request_id, relevance, i)
                continue

            filtered.append(
                KnowledgeResult(
                    title=(doc[:80] if isinstance(doc, str) else "document"),
                    content=doc,
                    relevance_score=round(relevance, 3),
                    source="chroma_rag"
                )
            )

        logger.info("[%s] Chroma returned %d FILTERED results", request_id, len(filtered))
        return filtered

    except Exception as e:
        logger.error("[%s] Chroma search failed: %s", request_id, e)
        return []


def _load_vector_store():
    """
    Try loading Chroma first, then FAISS.
    Returns:
        ("chroma", client, collection)
        ("faiss", index, embeddings_model, documents)
        (None, None)
    """
    global _chroma_client, _chroma_collection

    # Try Chroma first
    chroma_dir = Path(settings.chroma_persist_dir)

    if _CHROMADB_AVAILABLE and chroma_dir.exists():
        try:
            # NEW Chroma loading (correct version)
            try:
                import chromadb

                chroma_dir = Path(settings.chroma_persist_dir)

                if chroma_dir.exists():

                    _chroma_client = chromadb.PersistentClient(
                        path=str(chroma_dir)
                    )

                    _chroma_collection = _chroma_client.get_collection("crop_knowledge")

                    logger.info(
                        "Loaded Chroma DB with %d documents",
                        _chroma_collection.count()
                    )

                    return ("chroma", _chroma_client, _chroma_collection)

            except Exception as e:

                logger.warning("Failed to load Chroma DB: %s", str(e))


            _chroma_collection = _chroma_client.get_collection("crop_knowledge")

            logger.info("Loaded Chroma DB from %s", chroma_dir)

            return ("chroma", _chroma_client, _chroma_collection)

        except Exception as e:
            logger.warning("Chroma load failed: %s", str(e))

    # Fallback to FAISS
    index, model = _load_faiss_index()

    if index is not None and model is not None:
        return ("faiss", index, model, _documents)

    return (None, None)


async def _rewrite_query(query: str, history: List[str], llm: ChatGroq) -> str:
    """
    Rewrite query to be self-contained based on chat history.
    """
    if not history:
        return query

    try:
        rewrite_prompt = PromptTemplate.from_template(
            """Given a chat history and the latest user question which might reference context in the chat history, formulate a standalone question which can be understood without the chat history. Do NOT answer the question, just rewrite it if needed and otherwise return it as is.

Chat History:
{history}

Latest Question: {question}
Standalone Question:"""
        )
        
        chain = rewrite_prompt | llm | StrOutputParser()
        rewritten = await chain.ainvoke({"history": "\n".join(history), "question": query})
        return rewritten.strip()
    except Exception as e:
        logger.warning("Query rewrite failed: %s", e)
        return query


def _format_docs(docs):
    return "\n\n".join(
        f"{doc.page_content}\nSource: {doc.metadata.get('image', 'unknown')}"
        for doc in docs
    )


async def query_rag(query: str, request_id: str = "", chat_history: List[str] = None) -> str:
    """
    Execute the full RAG pipeline: Retriever -> Prompt -> LLM.
    Uses LangChain LCEL exactly as per the notebook.
    """
    if not _RAG_CHAIN_AVAILABLE:
        return "RAG dependencies (langchain-groq, fastembed) not installed."

    # Ensure vector store is loaded
    vs, _ = _load_faiss_index()
    if vs is None:
        return "Knowledge base not available (FAISS index missing)."

    # Check for Groq API key
    if not settings.groq_api_key:
        return "Groq API key not configured."

    try:
        # 1. Setup Retriever
        retriever = vs.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": 6,
                "fetch_k": 20,
                "lambda_mult": 0.7
            }
        )

        llm = ChatGroq(
            model=getattr(settings, "groq_model", "llama-3.1-8b-instant"),
            api_key=settings.groq_api_key,
            temperature=0.0,
        )

        # 2a. Rewrite Query if history exists
        if chat_history:
            original_query = query
            query = await _rewrite_query(query, chat_history, llm)
            logger.info("[%s] Rewrote query: '%s' -> '%s'", request_id, original_query, query)

        # 3. Setup Prompt (Krishi-Sarthi Persona)
        # Use simple string for template to avoid syntax issues in tool calls
        template_str = """
You are Krishi-Sarthi, an agricultural AI assistant.

Answer ONLY using provided context.

Provide:

- Disease name
- Key symptoms
- One recommended action
- Source image reference

If answer not in context say:
"I don't have enough information."

Context:
{context}

Question:
{question}

Answer with citation:
"""
        prompt = PromptTemplate(
            template=template_str,
            input_variables=["context", "question"]
        )

        # 4. Build Chain
        chain = (
            RunnableParallel({
                "context": retriever | _format_docs,
                "question": RunnablePassthrough()
            })
            | prompt
            | llm
            | StrOutputParser()
        )

        logger.info("[%s] Executing RAG chain for: %s", request_id, query)
        
        # Check relevance before generating answer (using retriever to fetch docs first)
        docs = await retriever.ainvoke(query)
        if not docs:
            return "I couldn't find any relevant information in my knowledge base."
            
        # Basic content-based relevance check (heuristic)
        # In a real system, we'd use the retriever's scores (if available) or a re-ranker.
        # For now, trust the retriever but if it returns very few/short docs, be cautious.
        
        result = await chain.ainvoke(query)
        return result

    except Exception as e:
        logger.error("[%s] RAG chain execution failed: %s", request_id, str(e))
        return f"Error processing request: {str(e)}"


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
    # ── Try Vector Store (Chroma → FAISS) ─────────────────
    # ── Try Chroma FIRST ─────────────────────────────

    chroma_results = await _search_chroma(query, top_k, request_id)

    if chroma_results:
        logger.info("[%s] Using Chroma RAG", request_id)
        return chroma_results


    # ── Try FAISS fallback ───────────────────────────

    if not (settings.is_demo and settings.mock_ai_responses):

        index, model = _load_faiss_index()

        if index is not None and model is not None:

            try:

                results = await _search_faiss(query, top_k, request_id)

                if results:
                    return results

            except Exception as e:
                logger.error("[%s] FAISS failed: %s", request_id, str(e))



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
    # Final relevance filter: keep only sufficiently relevant RAG hits
    filtered = [r for r in results if r.relevance_score >= 0.65]
    if filtered:
        return filtered

    return results
