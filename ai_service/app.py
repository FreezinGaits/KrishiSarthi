# ai_service/app.py
from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import base64
import os
import tempfile
import shutil
import uvicorn
import json
from typing import Optional, Any, Dict
session_memory = {}
from langchain_groq import ChatGroq
from groq import Groq

# import your inference function
from .inference import predict_disease  # -> returns {"class_name":..., "confidence":...}

# --- Optional: RAG / LLM pieces (uses your notebook approach) ---
# If you have a saved FAISS index and embeddings configured like in your notebook,
# this will load them. If missing, endpoints still respond with image-only diagnosis.
RAG_ENABLED = True
try:
    from langchain_community.embeddings import FastEmbedEmbeddings
    from langchain_community.vectorstores import FAISS
    from langchain_groq import ChatGroq
    from langchain_core.prompts import PromptTemplate
    RAG_AVAILABLE = True
except Exception:
    RAG_AVAILABLE = False
    RAG_ENABLED = False

BASE_DIR = os.path.dirname(__file__)
FAISS_INDEX_DIR = os.path.join(BASE_DIR, "faiss_index")  # matches your notebook
DISEASE_META_PATH = os.path.join(BASE_DIR, "disease_metadata.json")
VENDOR_DATA_PATH = os.path.join(BASE_DIR, "vendors_punjab.json")
VENDOR_DATA_PATH = os.path.abspath(VENDOR_DATA_PATH)


vendors_data = []

if os.path.exists(VENDOR_DATA_PATH):
    try:
        with open(VENDOR_DATA_PATH, "r", encoding="utf-8") as f:
            vendors_data = json.load(f)
    except Exception as e:
        print("Vendor data load error:", e)

CLASS_LABELS_PATH = os.path.join(BASE_DIR, "class_labels.json")

app = FastAPI(title="Krishi-Sarthi API")

# Basic CORS for local development / frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change to production origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple API key middleware (frontend sends 'X-API-Key')
EXPECTED_API_KEY = "krishi-sarthi-api-key-change-this"

@app.middleware("http")
async def api_key_check(request: Request, call_next):
    # check only /api endpoints
    if request.url.path.startswith("/api"):
        key = request.headers.get("x-api-key") or request.headers.get("X-API-Key")
        if key != EXPECTED_API_KEY:
            return JSONResponse({"error": "invalid api key"}, status_code=401)
    return await call_next(request)

# Load disease metadata (if present)
if os.path.exists(DISEASE_META_PATH):
    with open(DISEASE_META_PATH, "r", encoding="utf-8") as f:
        disease_metadata = json.load(f)
else:
    disease_metadata = {}

# Load class label mapping (optional, used for nicer names)
if os.path.exists(CLASS_LABELS_PATH):
    with open(CLASS_LABELS_PATH, "r", encoding="utf-8") as f:
        idx_to_class = json.load(f)
else:
    idx_to_class = {}

# --- RAG init (if available and index exists) ---
vector_store = None
embeddings = None
retriever = None
llm = None
prompt_template = None

if RAG_AVAILABLE and os.path.isdir(FAISS_INDEX_DIR):
    try:
        embeddings = FastEmbedEmbeddings(
            model_name="BAAI/bge-small-en-v1.5",
            parallel=1,
            batch_size=64
        )
        vector_store = FAISS.load_local(FAISS_INDEX_DIR, embeddings, allow_dangerous_deserialization=True)
        retriever = vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": 6,
                "fetch_k": 20,
                "lambda_mult": 0.7
            }
        )
        # ChatGroq LLM — requires GROQ API key in env (you already set in notebook)
        if os.environ.get("GROQ_API_KEY"):
            llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.0)
        # Use same prompt template you had in the notebook
        prompt_template = PromptTemplate(
            template="""
        You are Krishi-Sarthi, an expert agricultural AI assistant.

        RULES:

        1. If image analysis is present in context, ALWAYS use it.
        2. If user greets (hi, hello, namaste), respond politely in a farming tone.
        3. If user asks about the uploaded image, base your answer on IMAGE ANALYSIS RESULT first.
        4. If context insufficient, use agricultural knowledge.
        5. Never hallucinate unknown image sources.

        Response format when disease identified:

        Disease: <name>
        Confidence: <value if available>
        Cause: <bugs/weather/fungal/etc>
        Key Symptoms:
        - ...
        Recommended Action:
        - ...

        If greeting:
        Respond warmly in short format.

        Context:
        {context}

        Question:
        {question}

        Answer:
        """,
            input_variables=["context", "question"]
        )


    except Exception as e:
        print("RAG init failed:", e)
        vector_store = None
        retriever = None
        llm = None
        prompt_template = None

# ---------- Request models ----------
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = ""
    image_base64: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    language: Optional[str] = "hi"
    options: Optional[Dict[str, Any]] = {}

# ---------- Endpoints ----------
@app.get("/api/health")
async def health():
    return {"status": "ok", "rag": bool(retriever), "llm": bool(llm)}


@app.post("/api/speech-to-text")
async def speech_to_text(audio: UploadFile = File(...)):
    try:
        # Save temp audio file
        suffix = os.path.splitext(audio.filename or "audio.webm")[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await audio.read())
            tmp_path = tmp.name

        # Use Groq Whisper
        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

        with open(tmp_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=file,
                model="whisper-large-v3"
            )

        os.unlink(tmp_path)

        return {"transcript": transcription.text}

    except Exception as e:
        print("STT ERROR:", e)
        return {"error": str(e)}

@app.post("/api/diagnose-image")

async def diagnose_image(image: UploadFile = File(...)):
    """
    Accepts multipart image -> returns prediction + metadata
    Frontend ImageUpload -> calls this.
    """
    # save to temp file
    suffix = os.path.splitext(image.filename)[1] or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = tmp.name
        content = await image.read()
        tmp.write(content)

    try:
        pred = predict_disease(tmp_path)  # expects {"class_name":..., "confidence":...}
    except Exception as e:
        os.unlink(tmp_path)
        raise HTTPException(status_code=500, detail=f"inference error: {e}")

    # enrich with disease metadata if available
    class_key = pred.get("class_name")
    meta = disease_metadata.get(class_key, {})
    print("meta returned: ", meta)
    response = {
        "disease": class_key,
        "confidence": pred.get("confidence", 0.0),
        "metadata": meta
    }

    os.unlink(tmp_path)
    return response

@app.post("/api/chat")
async def chat(req: ChatRequest):
    """
    Chat endpoint used by ChatInterface and sending images as base64.
    - If image_base64 present: save, run predict_disease and include diagnosis in reply.
    - If RAG available: retrieve context and call LLM (ChatGroq) to answer the message.
    Response shape expected by frontend: { reply: str, diagnosis: {...}, vendors: [...] }
    """
    if not req.session_id:
        req.session_id = "default"
    
    if req.session_id not in session_memory:
        session_memory[req.session_id] = []

    session_memory[req.session_id].append({
        "role": "user",
        "content": req.message
    })
    # ---- META QUESTION HANDLER ----
    lower_msg = req.message.lower().strip()

    meta_triggers = [
        "previous question",
        "what did i ask",
        "what was my",
        "most recent question",
        "what i just asked"
    ]

    is_meta_question = any(trigger in lower_msg for trigger in meta_triggers)

    if is_meta_question:
        history = session_memory.get(req.session_id, [])

        # exclude current question
        previous_turns = history[:-1]

        if not previous_turns:
            reply_text = "You haven't asked anything before this."
        else:
            last_user_msgs = [
                m["content"] for m in previous_turns
                if m["role"] == "user"
            ]

            if last_user_msgs:
                reply_text = f"Your previous question was:\n\n{last_user_msgs[-1]}"
            else:
                reply_text = "I cannot find a previous user question."

        # save assistant reply
        session_memory[req.session_id].append({
            "role": "assistant",
            "content": reply_text
        })

        # keep only last 20 messages
        if len(session_memory[req.session_id]) > 20:
            session_memory[req.session_id] = session_memory[req.session_id][-20:]

        return {"reply": reply_text, "diagnosis": None, "vendors": []}
    # history = session_memory.get(req.session_id, [])
    # history.append({"role": "user", "content": reply_text})
    # session_memory[req.session_id] = history
    diagnosis = None
    image_path_tmp = None

    # 1) If image is provided, decode and run inference
    if req.image_base64:
        try:
            header_removed = req.image_base64.split(",")[-1]  # tolerate full data:...;base64,... or raw base64
            data = base64.b64decode(header_removed)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                tmp.write(data)
                image_path_tmp = tmp.name
            diagnosis = predict_disease(image_path_tmp)
            # attach metadata
            diagnosis_meta = disease_metadata.get(diagnosis.get("class_name"), {})
            diagnosis["metadata"] = diagnosis_meta
        except Exception as e:
            if image_path_tmp and os.path.exists(image_path_tmp):
                os.unlink(image_path_tmp)
            return JSONResponse({"reply": "Image processing failed", "error": str(e)}, status_code=500)

    # 2) If RAG/LLM is ready, build context and call it
    reply_text = None
    if retriever and prompt_template and llm:
        # create query: include message + diagnosis summary if present
        if retriever and prompt_template and llm:
            try:
                # ---- BUILD STRONG CONTEXT ----
                context_blocks = []

                # 1️⃣ Always prioritize image diagnosis
                if diagnosis:
                    meta = diagnosis.get("metadata", {})
                    image_context = f"""
                        IMAGE ANALYSIS RESULT:
                        - Predicted class: {diagnosis.get('class_name')}
                        - Confidence: {diagnosis.get('confidence'):.2f}

                        METADATA:
                        {meta.get('summary', '')}
                        Symptoms: {meta.get('symptoms', '')}
                        Causes: {meta.get('causes', '')}
                        Treatment: {meta.get('treatment', '')}
                        """
                    context_blocks.append(image_context)

                # 2️⃣ Retrieve knowledge context
                retrieval_query = req.message
                if diagnosis:
                    retrieval_query += f" related to {diagnosis.get('class_name')}"

                retrieved_docs = retriever.invoke(retrieval_query)

                retrieved_text = "\n\n".join(
                    d.page_content for d in retrieved_docs
                ) if retrieved_docs else ""

                if retrieved_text:
                    context_blocks.append(retrieved_text)

                full_context = "\n\n".join(context_blocks)
                # Build conversation history text
                history_text = "\n".join(
                    f"{m['role'].upper()}: {m['content']}"
                    for m in session_memory[req.session_id][-10:]
                )
                # 3️⃣ Build prompt
                final_prompt = prompt_template.invoke({
                    "context": full_context + "\n\nConversation History:\n" + history_text,
                    "question": req.message
                })

                llm_resp = llm.invoke(final_prompt)

                if hasattr(llm_resp, "content"):
                    reply_text = llm_resp.content
                else:
                    reply_text = str(llm_resp)

            except Exception as e:
                print("RAG ERROR:", e)
                reply_text = "I encountered a knowledge retrieval issue. Please try again."


        # except Exception as e:
        #     print("RAG/LLM error:", e)
        #     # degrade to simple text reply
        #     # reply_text = f"I couldn't fetch extended context (RAG error). Here's a short reply: I detected {diagnosis.get('class_name') if diagnosis else 'no image'}."
        #     print("RAG ERROR:", e)
        #     return {
        #         "reply": f"RAG crashed: {str(e)}",
        #         "diagnosis": None,
        #         "vendors": []
        #     }
    else:
        # If no LLM, build simple reply using diagnosis if present, else echo
        if diagnosis:
            meta = diagnosis.get("metadata", {})
            reply_text = (
                f"Detected: {diagnosis.get('class_name')} (conf {diagnosis.get('confidence'):.2f}).\n"
                f"{meta.get('short_description','')}\n"
                f"Suggested action: {meta.get('one_line_treatment','See metadata for details')}"
            )
        else:
            reply_text = "I don't have RAG/LLM available on server. Ask about crop diseases or upload an image."

    # cleanup
    if image_path_tmp and os.path.exists(image_path_tmp):
        os.unlink(image_path_tmp)

    # vendors: simple empty list for now; your frontend expects vendors maybe from /find-vendors
    vendors = []
    # Save assistant reply
    session_memory[req.session_id].append({
        "role": "assistant",
        "content": reply_text
    })

    # 🔥 Keep only last 20 messages (10 turns)
    if len(session_memory[req.session_id]) > 20:
        session_memory[req.session_id] = session_memory[req.session_id][-20:]
    return {"reply": reply_text, "diagnosis": diagnosis, "vendors": vendors}
from math import radians, cos, sin, sqrt, atan2

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c


@app.post("/api/find-vendors")
async def find_vendors(data: dict):
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    radius_km = data.get("radius_km", 10)

    if latitude is None or longitude is None:
        return {"vendors": []}

    results = []

    for v in vendors_data:
        dist = calculate_distance(latitude, longitude, v["lat"], v["lng"])
        if dist <= radius_km:
            results.append({
                "name": v["name"],
                "address": v["address"],
                "lat": v["lat"],
                "lng": v["lng"],
                "phone": v.get("phone"),
                "rating": v.get("rating"),
                "distance_km": dist,
                "products": v.get("pesticides_available", [])[:5]
            })
    print("Vendor file path:", VENDOR_DATA_PATH)
    print("Vendor file exists:", os.path.exists(VENDOR_DATA_PATH))
    print("Vendors loaded:", len(vendors_data))
    print("Vendors loaded:", vendors_data)

    results.sort(key=lambda x: x["distance_km"])
    
    return {"vendors": results}

# small convenience to run locally
if __name__ == "__main__":
    uvicorn.run("ai_service.app:app", host="0.0.0.0", port=8000, reload=True)
