# Krishi-Sarthi Frontend

React + Vite frontend for the Krishi-Sarthi AI farming assistant.

## Quick Start

```bash
# Install dependencies
npm install

# Start dev server (proxies /api to backend on :8000)
npm run dev
```

Opens at **http://localhost:3000**

## Connect to Backend

1. Start the FastAPI backend first:
   ```bash
   cd ../backend
   python run.py
   ```
2. Then start the frontend — Vite proxies all `/api/*` requests to `localhost:8000`

## Routes

| Route | Page | Description |
|-------|------|-------------|
| `/` | Home | Landing page with hero, features, stats |
| `/dashboard` | Dashboard | Main app — chat, voice, image scan, vendors |

## Architecture

```
src/
├── services/api.js      ← All backend API calls
├── pages/
│   ├── Home.jsx          ← Landing page
│   └── Dashboard.jsx     ← Main app with tabs
├── components/
│   ├── ChatInterface.jsx ← Bilingual chat (Hindi/English)
│   ├── VoiceRecorder.jsx ← MediaRecorder → Whisper STT
│   ├── ImageUpload.jsx   ← Drag-drop → PyTorch classifier
│   ├── DiagnosisCard.jsx ← Disease result with confidence ring
│   ├── VendorList.jsx    ← Vendor cards with ratings
│   └── MapView.jsx       ← Leaflet map with vendor pins
├── App.jsx               ← React Router
└── main.jsx              ← Entry point
```

## Backend Endpoints Used

| Component | Endpoint | Method |
|-----------|----------|--------|
| VoiceRecorder | `/api/speech-to-text` | POST |
| ImageUpload | `/api/diagnose-image` | POST |
| ChatInterface | `/api/chat` | POST |
| VendorList/MapView | `/api/find-vendors` | GET |
