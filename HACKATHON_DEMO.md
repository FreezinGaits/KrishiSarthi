# Krishi-Sarthi — Hackathon Demo Guide

## 🚀 Start Demo in 30 Seconds

### Windows
```
start_demo.bat
```

### Linux / Mac
```bash
chmod +x start_demo.sh
./start_demo.sh
```

### Or use Python
```bash
python run_demo.py
```

Opens:
- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000/docs

---

## 🎯 Demo Script (5 minutes)

### Slide 1: The Problem (30 sec)
> "Indian farmers lose ₹90,000 crore annually to crop diseases.
> Most can't identify diseases or find treatment fast enough.
> Krishi-Sarthi solves this with AI."

### Slide 2: Live Demo (3 min)

1. **Open** http://localhost:3000 — show the landing page
2. **Click** "Start Diagnosis" → Dashboard opens
3. **Voice tab** 🎤 — Click mic, say: *"मेरे टमाटर के पत्तों पर काले धब्बे हैं"*
   - Shows Hindi transcript
   - Automatically sends to AI chat
4. **Scan tab** 📸 — Upload a tomato leaf photo
   - Watch the scanning animation
   - Show the DiagnosisCard: disease, confidence ring, treatment
5. **Chat tab** 💬 — Type: *"इसका इलाज बताओ"*
   - AI responds with treatment + pesticide
6. **Vendors tab** 📍 — Show vendor cards + Leaflet map
   - Vendor ratings, distance, phone numbers
7. **Demo tab** 🎬 — Click "Presentation Mode"
   - Auto-runs full pipeline: Voice → Diagnosis → Treatment → Vendor → Notification
   - Timeline animation shows each step

### Slide 3: Architecture (1 min)
> "FastAPI backend + PyTorch classifier + LangChain agent + n8n automation.
> Hindi voice via Whisper. Vendor search via OpenStreetMap.
> Full automation: SMS notification on diagnosis, expert escalation on low confidence."

### Slide 4: Impact (30 sec)
> "Targets 86 million Punjab farmers.
> PAU-approved crop varieties and treatments.
> Works offline with cached knowledge base."

---

## 💡 Talking Points for Judges

| Question | Answer |
|----------|--------|
| How does voice work? | Whisper AI transcribes Hindi → LangChain agent processes |
| What AI model? | PyTorch CNN for 15+ diseases, LangChain for orchestration |
| How accurate? | 89% on test set (demo). Real model trained on PlantVillage dataset |
| Offline support? | FAISS vector store + cached knowledge base |
| Vendor data? | 20 vendors across 5 Punjab cities with live distance calc |
| Automation? | n8n workflows: notification, escalation, retraining, pricing |
| Security? | API key auth, rate limiting, CORS protection |
| Scalable? | FastAPI async, Redis caching, Postgres, Docker-ready |

---

## 📂 Key Files to Show Judges

| File | What It Shows |
|------|--------------|
| `backend/app/services/agent_service.py` | LangChain agentic orchestration |
| `ai-service/data/knowledge_base/` | Structured disease databases |
| `n8n/workflows/` | 5 automation workflow definitions |
| `frontend/src/components/` | Complete React component library |

---

## ⚠️ Troubleshooting

| Issue | Fix |
|-------|-----|
| Backend won't start | `cd backend && pip install -r requirements.txt` |
| Frontend blank page | `cd frontend && npm install && npm run dev` |
| CORS errors | Backend CORS_ORIGINS must include frontend URL |
| API returns 401 | Check X-API-Key header matches .env API_KEY |
