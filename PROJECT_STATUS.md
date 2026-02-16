# 🌾 Krishi-Sarthi — Project Status & Capabilities

> **Last updated**: 15 Feb 2026  
> **Branch**: `real-integration`  
> **Honest assessment** — no exaggerations, no false claims.

---

## Table of Contents

1. [What is Krishi-Sarthi?](#what-is-krishi-sarthi)
2. [The "Demo" Label — Honest Explanation](#the-demo-label--honest-explanation)
3. [What Actually Works (Real APIs)](#what-actually-works-real-apis)
4. [What Doesn't Work Yet / Limitations](#what-doesnt-work-yet--limitations)
5. [What's Remaining to Make It Production-Ready](#whats-remaining-to-make-it-production-ready)
6. [Architecture Overview](#architecture-overview)
7. [How to Run the Project](#how-to-run-the-project)
8. [API Endpoints Reference](#api-endpoints-reference)
9. [File Structure](#file-structure)

---

## What is Krishi-Sarthi?

Krishi-Sarthi (कृषि-सारथी, "Agriculture Guide") is an AI-powered agricultural assistant built for Indian farmers. It was originally built as a Smart India Hackathon project.

The system lets farmers:
- **Speak in Hindi** → AI transcribes and understands
- **Upload a crop photo** → AI identifies the disease
- **Get treatment advice** → with specific pesticide names & dosages
- **Find nearby pesticide shops** → using Google Maps data
- **Chat with an AI agent** → that orchestrates all of the above

The tech stack is:
- **Backend**: FastAPI (Python) with async architecture
- **Frontend**: React (Vite) single-page app
- **AI Services**: OpenAI GPT-4o Vision, Whisper API, LangChain agent
- **Data**: FAISS vector store, ICAR/PAU agricultural knowledge base
- **Vendor Search**: Google Places API + OpenStreetMap fallbacks
- **Automation**: n8n webhook integrations (notifications, escalation)

---

## The "Demo" Label — Honest Explanation

**Why does the UI say "Demo Mode Active"?**

The frontend has a hardcoded `<DemoBanner />` component in `Dashboard.jsx` that always shows **"🔬 Demo Mode Active — Krishi-Sarthi Hackathon Build"** regardless of what the backend is actually doing. It was put there for the hackathon presentation and was never removed.

Additionally:
- The Home page has a "Try Demo" button (which just navigates to the Dashboard — same as "Start Diagnosis")
- The Dashboard has a "Demo" tab with a "Presentation Mode" feature that walks through hardcoded steps for judges
- The `run_demo.py` launcher script forces `DEMO_MODE=true` by copying `.env.demo` to `backend/.env`

**Is it actually a demo?**

It depends on how you run it:

| How you run it | What happens |
|---|---|
| `python run_demo.py` | Forces demo mode. All AI features use **hardcoded mock data**. No real API calls. |
| `python backend/run.py` + `npm run dev` (separately) | Uses your `.env` settings. If `DEMO_MODE=false` and API keys are set, **real APIs are used**. |

**Current `.env` status**: `DEMO_MODE=false`, `MOCK_AI_RESPONSES=false`, `MOCK_VENDOR_DATA=false` — so when you run the servers manually, **real APIs are used**.

**The "Demo" label is cosmetic and misleading.** The backend is hitting real OpenAI and Google APIs when started manually.

---

## What Actually Works (Real APIs)

### ✅ 1. Crop Disease Diagnosis (`POST /api/diagnose-image`)

**Status: WORKING with real GPT-4o Vision API**

When you upload a crop image:
1. Image is validated (format, size)
2. Sent to **OpenAI GPT-4o Vision API** with an agricultural expertise system prompt
3. GPT-4o analyzes the image and returns disease name, confidence, affected crop
4. The system matches the disease against a **30-disease database** with ICAR/PAU-sourced treatments
5. Returns: disease name, confidence score, treatment with specific dosages, pesticide brand names

**Disease database includes**: Rice Blast, Brown Spot, Bacterial Leaf Blight, Sheath Blight, Tomato Early Blight, Late Blight, Septoria Leaf Spot, Wheat Brown Rust, Yellow Rust, Loose Smut, Karnal Bunt, Powdery Mildew, Downy Mildew, and 17 more.

**Fallback chain**: Local PyTorch model (if trained) → GPT-4o Vision API → Demo mock data

**Important Note**: If GPT-4o Vision fails (e.g. quota exceeded) and the system falls back to demo mode:
- If filename contains a crop keyword (e.g. "tomato_leaf.jpg"), it returns a relevant disease.
- If filename is unknown (e.g. "image.jpg"), it returns **"Unidentified (Demo Mode)"** instead of guessing randomly. This prevents misleading results.

**Limitations**:
- Accuracy depends entirely on GPT-4o Vision's ability to identify crop diseases — it's good but not infallible
- No local PyTorch model is trained yet (the training script exists but hasn't been run)
- Costs money per API call (OpenAI charges for Vision API usage)
- No image preprocessing or augmentation before sending to API

### ✅ 2. Voice Input / Speech-to-Text (`POST /api/speech-to-text`)

**Status: WORKING with real OpenAI Whisper API**

When you record or upload audio:
1. Audio is validated (format: webm, wav, mp3, m4a, ogg, flac; max 10MB)
2. Sent to **OpenAI Whisper API** with Hindi language hint
3. Returns transcription with language detection and confidence score

**Fallback chain**: OpenAI Whisper API → Demo mock transcript (if DEMO_MODE=true)

**Limitations**:
- Requires microphone access in browser (may not work on all mobile browsers)
- Costs money per API call
- Only tested with Hindi and English — other Indian languages may work but aren't validated
- No local Whisper model — always needs internet

### ✅ 3. Vendor Search (`POST /api/find-vendors`)

**Status: WORKING with real Google Places API**

When you search for nearby vendors:
1. Searches **Google Places API** for agricultural supply stores near your coordinates
2. Returns: shop name, address, distance, rating, coordinates
3. Results shown on a **Leaflet map** in the frontend

**Fallback chain**: Google Places API → OpenStreetMap Overpass API → Nominatim → Demo vendor list (Punjab-focused)

**Limitations**:
- Only searches for shops with keywords like "pesticide shop", "agricultural supply", "krishi kendra"
- Phone numbers are not fetched by default (requires a separate Google Places Details API call per vendor — expensive)
- No pricing data for pesticides (that would require a separate data source)
- Google Places API has usage quotas and costs money
- Default radius is 10km — rural areas may have no results

### ✅ 4. AI Chat Agent (`POST /api/chat`)

**Status: WORKING with LangChain + GPT-4o**

The chat agent orchestrates all services:
1. **Intent detection**: Keyword matching in Hindi and English to detect what the farmer wants (disease diagnosis, vendor search, treatment advice, greeting)
2. **Tool orchestration**: LangChain agent with tools for diagnosis, vendor search, and knowledge base queries
3. **Knowledge retrieval**: Searches ICAR disease knowledge base using FAISS vector search or keyword matching
4. **Response generation**: GPT-4o generates farmer-friendly responses

**Fallback chain**: LangChain + GPT-4o agent → Rule-based orchestrator (if OpenAI unavailable)

**Limitations**:
- LangChain agent quality depends on prompt engineering — responses can be verbose or miss context
- No conversation memory across sessions (each session starts fresh)
- No multi-turn context tracking (can't say "and what about the other plant?")
- Rule-based fallback is simplistic — pattern matching only

### ✅ 5. Knowledge Base (RAG)

**Status: WORKING (keyword search mode)**

The RAG service loads agricultural knowledge from:
- `rice_diseases.json` — 4 diseases with ICAR data
- `tomato_diseases.json` — 5 diseases with ICAR/IIHR data
- `wheat_diseases.json` — 4 diseases with ICAR-IIWBR data
- Plus ~10 hardcoded knowledge entries in the service itself

**Total: 23 knowledge documents loaded** (confirmed from startup logs)

**Limitations**:
- FAISS vector index is **not built** — knowledge search uses simple keyword matching, not semantic search
- To enable FAISS, you'd need to run an index-building script (doesn't exist yet)
- Only covers rice, tomato, and wheat — no other crops
- No Punjabi language content — all in English with some Hindi terms
- Knowledge base is static — no automatic updates

### ⚠️ 6. Notifications / SMS (`POST /api/notify-vendor`)

**Status: PARTIALLY WORKING — n8n webhooks configured but n8n not running**

The notification service is designed to trigger n8n workflows that send SMS/WhatsApp via Twilio. The Twilio API keys are configured in `.env`.

**Reality**: 
- The webhook trigger code is written and correct
- n8n is **not running** on this machine, so all notification attempts fail silently
- When n8n is not available, notifications are logged but not sent
- In demo mode, notifications are "simulated" (just logged)
- **No direct Twilio integration** — it goes through n8n, which goes through Twilio

### ⚠️ 7. n8n Automation Workflows

**Status: DEFINED but NOT RUNNING**

Five n8n workflow JSON files exist in `n8n/workflows/`:
- `send_notification.json` — SMS/WhatsApp via Twilio
- `escalation.json` — Route low-confidence diagnoses to human experts
- `retraining_trigger.json` — Trigger model retraining on farmer corrections
- `vendor_enrichment.json` — Enrich vendor data with pricing
- `price_aggregation.json` — Aggregate pesticide prices

**Reality**: These are workflow definitions. To use them, you need to install and configure n8n separately, import these workflows, and configure Twilio credentials within n8n. None of this is set up.

### ✅ 8. Database

**Status: WORKING (SQLite fallback)**

The app is designed for PostgreSQL but falls back to SQLite when Postgres isn't available. Currently running on SQLite at `./krishi_sarthi.db`.

**Limitations**:
- SQLite is single-writer — can't handle concurrent requests well
- No data persistence beyond the SQLite file
- ORM models exist but are minimal (no user accounts, no diagnosis history saved)

---

## What Doesn't Work Yet / Limitations

### 🔴 Critical Gaps

| Feature | Status | Why |
|---|---|---|
| **Local PyTorch classifier** | Not trained | Training script exists (`train_classifier.py`) but hasn't been executed. Needs PlantVillage dataset download. |
| **FAISS vector search** | Not built | Index file doesn't exist. Knowledge search uses keyword matching only. |
| **n8n automations** | Not running | n8n server not installed/running. All 5 workflow files are just definitions. |
| **SMS/WhatsApp notifications** | Not functional | Depends on n8n, which isn't running. |
| **User authentication** | Doesn't exist | No login, no user accounts, no session persistence. Anyone can access everything. |
| **Diagnosis history** | Not saved | Diagnoses are returned but not stored in the database. |
| **Multi-language UI** | Only English/Hindi mix | UI has hardcoded Hindi labels but no language switcher. No Punjabi, Tamil, etc. |

### 🟡 Partial / Cosmetic Issues

| Issue | Details |
|---|---|
| **"Demo Mode Active" banner** | Always shows, even when using real APIs. Hardcoded in `DemoMode.jsx`. |
| **"Try Demo" button** | Landing page button says "Try Demo" — just navigates to Dashboard. |
| **"Demo" tab** | Dashboard has a Demo/Presentation tab with hardcoded walkthrough steps. |
| **"15+ Crop Diseases" stat** | Landing page claims 15+ but the database has 30 diseases. Should be updated. |
| **"20+ Punjab Vendors" stat** | Hardcoded stat on landing page, not reflective of real Google Places results. |
| **Hardcoded API key** | Frontend sends `X-API-Key: krishi-sarthi-api-key-change-this` — hardcoded default. |
| **No HTTPS** | Runs on HTTP only. Not secure for production. |
| **No error UI** | If backend is down, frontend just shows a white screen or raw error. |

---

## What's Remaining to Make It Production-Ready

### Phase 1: Remove Demo Artifacts
- [ ] Remove `<DemoBanner />` from Dashboard or make it conditional on actual backend `demo_mode`
- [ ] Change "Try Demo" button to "Get Started" or similar
- [ ] Remove/rename the "Demo" tab or make it only visible in actual demo mode
- [ ] Update landing page stats to reflect real data
- [ ] Fix the hardcoded API key in `api.js`
- [ ] Remove `run_demo.py` and `.env.demo` or clearly separate them

### Phase 2: Core Functionality Gaps
- [ ] Train the local PyTorch EfficientNet-B0 classifier (run `train_classifier.py`)
- [ ] Build FAISS vector index for semantic knowledge search
- [ ] Add more crops to the knowledge base (cotton, sugarcane, maize, mustard, potato)
- [ ] Save diagnosis history to the database
- [ ] Add user accounts and authentication (JWT or similar)
- [ ] Add a feedback mechanism (farmer can correct a wrong diagnosis)

### Phase 3: Infrastructure
- [ ] Set up PostgreSQL instead of SQLite
- [ ] Set up Redis for caching and rate limiting
- [ ] Install and configure n8n for notification workflows
- [ ] Set up Twilio integration through n8n
- [ ] Add HTTPS with proper SSL certificates
- [ ] Deploy to a cloud server (AWS/GCP/Azure)
- [ ] Add monitoring and logging (Prometheus, Grafana)

### Phase 4: UX and Polish
- [ ] Add proper error handling in the frontend (error boundaries, retry logic)
- [ ] Add loading states and progress indicators
- [ ] Make the UI responsive for mobile (farmers use phones, not desktops)
- [ ] Add Punjabi language support in the UI
- [ ] Add offline mode / PWA support
- [ ] Add image preview before upload
- [ ] Add diagnosis confidence visualization

### Phase 5: Testing
- [ ] Add unit tests for all services
- [ ] Add integration tests for API endpoints
- [ ] Add end-to-end tests with real images
- [ ] Load testing for concurrent users
- [ ] Test with actual farmers (usability testing)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)               │
│  Home Page ─── Dashboard ─── Chat / Voice / Image / Map │
│                     :3000                                │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP (Vite proxy → /api)
┌──────────────────────▼──────────────────────────────────┐
│                  Backend (FastAPI)                        │
│                     :8000                                │
│                                                          │
│  Routers:                                                │
│    /api/chat ──────────► agent_service.py                │
│    /api/diagnose-image ► classifier_service.py           │
│    /api/speech-to-text ► whisper_service.py              │
│    /api/find-vendors ──► vendor_service.py               │
│    /api/notify-vendor ─► n8n_service.py                  │
│    /api/health ────────► health check                    │
│                                                          │
│  Services:                                               │
│    classifier ──► GPT-4o Vision API (OpenAI)             │
│    whisper ─────► Whisper API (OpenAI)                   │
│    vendor ──────► Google Places API + OSM                │
│    agent ───────► LangChain + GPT-4o (OpenAI)           │
│    rag ─────────► FAISS / Keyword search                 │
│    n8n ─────────► n8n webhooks (not running)             │
│                                                          │
│  Database: SQLite (fallback from PostgreSQL)              │
└──────────────────────────────────────────────────────────┘
```

---

## How to Run the Project

### Prerequisites

- **Python 3.10+** installed
- **Node.js 18+** installed
- **Git** installed

### Step-by-Step

**1. Open your terminal and navigate to the project:**
```powershell
cd "d:\Code Playground\KrishiSarthi"
```

**2. Make sure you are on the right branch:**
```powershell
git checkout real-integration
```

**3. Check that the `.env` file has your API keys:**
```powershell
# Open .env in your editor and verify these fields:
# OPENAI_API_KEY=sk-proj-...        ← Your OpenAI key
# GOOGLE_MAPS_API_KEY=AIzaSy...     ← Your Google Maps key
# DEMO_MODE=false                   ← Must be false for real APIs
# MOCK_AI_RESPONSES=false            ← Must be false for real APIs
# MOCK_VENDOR_DATA=false             ← Must be false for real APIs
```

**4. Install backend Python dependencies:**
```powershell
cd backend
pip install -r requirements.txt
```

**5. Start the backend server (Terminal 1):**
```powershell
cd backend
python run.py
```
You should see the Krishi-Sarthi banner and `✅ Krishi-Sarthi backend ready!`

**6. Install frontend dependencies (new terminal):**
```powershell
cd frontend
npm install
```

**7. Start the frontend dev server (Terminal 2):**
```powershell
cd frontend
npm run dev
```
You should see `VITE ready` with `http://localhost:3000/`

**8. Open the app in your browser:**
```
http://localhost:3000
```

### Important Notes

- **Do NOT use `python run_demo.py`** — it forces demo mode with mock data
- **Do NOT use `start_demo.bat` or `start_demo.sh`** — same issue
- Always start backend and frontend separately for real API mode
- The "Demo Mode Active" banner on the UI is a cosmetic bug — ignore it
- Backend health check at `http://localhost:8000/api/health` will show `"degraded"` because PostgreSQL and Redis aren't running — this is normal and the app works fine with SQLite fallback
- API documentation (Swagger) is at `http://localhost:8000/docs`

### Testing the APIs

**Test disease diagnosis** (upload any crop leaf image):
- Go to Dashboard → Scan tab → Upload an image
- Or use the Chat tab and describe a crop problem

**Test voice input**:
- Go to Dashboard → Voice tab → Press Record
- Speak in Hindi (e.g., "मेरे टमाटर के पत्तों पर काले धब्बे हैं")

**Test vendor search**:
- Go to Dashboard → Vendors tab
- It auto-searches based on your browser's geolocation (defaults to Ludhiana)

**Test chat**:
- Go to Dashboard → Chat tab
- Type a question like "What is the treatment for wheat rust?"

---

## API Endpoints Reference

| Method | Endpoint | Description | Real API Used |
|---|---|---|---|
| POST | `/api/chat` | Chat with AI agent | OpenAI GPT-4o + LangChain |
| POST | `/api/diagnose-image` | Upload crop image for diagnosis | OpenAI GPT-4o Vision |
| POST | `/api/speech-to-text` | Upload audio for transcription | OpenAI Whisper |
| POST | `/api/find-vendors` | Search nearby pesticide shops | Google Places API |
| POST | `/api/notify-vendor` | Send SMS/WhatsApp notification | n8n → Twilio (not running) |
| GET | `/api/health` | Health check with service status | — |
| GET | `/docs` | Swagger API documentation | — |
| GET | `/redoc` | ReDoc API documentation | — |

---

## File Structure

```
KrishiSarthi/
├── .env                          # API keys and configuration
├── PROJECT_STATUS.md             # This file
├── run_demo.py                   # ⚠️ Forces demo mode — don't use for real
│
├── backend/
│   ├── run.py                    # ✅ Use this to start backend
│   ├── requirements.txt          # Python dependencies
│   ├── app/
│   │   ├── main.py               # FastAPI app entry point
│   │   ├── config.py             # Settings loaded from .env
│   │   ├── middleware.py          # Request logging, timing
│   │   ├── models/
│   │   │   ├── database.py       # SQLAlchemy async engine
│   │   │   ├── orm.py            # ORM models
│   │   │   └── schemas.py        # Pydantic request/response schemas
│   │   ├── routers/
│   │   │   ├── chat.py           # /api/chat
│   │   │   ├── diagnosis.py      # /api/diagnose-image
│   │   │   ├── speech.py         # /api/speech-to-text
│   │   │   ├── vendors.py        # /api/find-vendors
│   │   │   ├── notifications.py  # /api/notify-vendor
│   │   │   └── health.py         # /api/health
│   │   ├── services/
│   │   │   ├── agent_service.py     # LangChain AI agent (572 lines)
│   │   │   ├── classifier_service.py # GPT-4o Vision + 30 diseases (425 lines)
│   │   │   ├── vendor_service.py     # Google Places + OSM (220 lines)
│   │   │   ├── whisper_service.py    # OpenAI Whisper STT (265 lines)
│   │   │   ├── rag_service.py        # Knowledge retrieval (522 lines)
│   │   │   └── n8n_service.py        # Notification webhooks (311 lines)
│   │   └── utils/
│   │       └── logger.py          # Colored console logger
│   └── data/
│       └── vendors_punjab.json    # Fallback vendor data
│
├── frontend/
│   ├── package.json               # React 18 + Vite 6
│   ├── vite.config.js             # Dev server config (proxy /api → :8000)
│   ├── index.html                 # Entry HTML
│   └── src/
│       ├── main.jsx               # React entry point
│       ├── App.jsx                # Routes: / and /dashboard
│       ├── index.css              # Global styles
│       ├── pages/
│       │   ├── Home.jsx           # Landing page
│       │   └── Dashboard.jsx      # Main app dashboard
│       ├── components/
│       │   ├── ChatInterface.jsx  # Chat with AI agent
│       │   ├── VoiceRecorder.jsx  # Microphone recording
│       │   ├── ImageUpload.jsx    # Crop image upload
│       │   ├── DiagnosisCard.jsx  # Disease result display
│       │   ├── VendorList.jsx     # Vendor listings
│       │   ├── MapView.jsx        # Leaflet map for vendors
│       │   └── DemoMode.jsx       # ⚠️ Hardcoded demo components
│       └── services/
│           └── api.js             # API client functions
│
├── ai-service/
│   ├── train_classifier.py        # EfficientNet-B0 training script
│   └── data/
│       └── knowledge_base/
│           ├── rice_diseases.json    # 4 ICAR diseases
│           ├── tomato_diseases.json  # 5 ICAR/IIHR diseases
│           └── wheat_diseases.json   # 4 ICAR-IIWBR diseases
│
└── n8n/
    └── workflows/                  # n8n workflow definitions (not running)
        ├── send_notification.json
        ├── escalation.json
        ├── retraining_trigger.json
        ├── vendor_enrichment.json
        └── price_aggregation.json
```
