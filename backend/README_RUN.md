# 🌾 Krishi-Sarthi — Quick Start Guide

Run the entire system locally in under 5 minutes.

## Prerequisites

- **Python 3.10+** (3.11 recommended)
- **pip** package manager
- A modern browser (Chrome/Edge/Firefox)

## 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

> **Optional — PyTorch** (for real model inference, not needed for demo):
> ```bash
> pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
> ```

## 2. Configure Environment

The `.env` file is already configured for demo mode. Key settings:

| Variable | Default | Purpose |
|----------|---------|---------|
| `DEMO_MODE` | `true` | Enables mock responses |
| `MOCK_AI_RESPONSES` | `true` | Uses demo classifier/whisper |
| `MOCK_VENDOR_DATA` | `true` | Uses demo vendor data |
| `API_KEY` | `krishi-sarthi-dev-key-2024` | API authentication |

## 3. Start Backend

```bash
cd backend
python run.py
```

You should see:
```
✅ Krishi-Sarthi backend ready!
🚀 Starting server on http://0.0.0.0:8000
```

## 4. Open Demo UI

Open `frontend/demo.html` in your browser.

> **Tip:** If you get CORS errors, serve via Python:
> ```bash
> cd frontend
> python -m http.server 3000
> ```
> Then open http://localhost:3000/demo.html

## 5. Run API Tests

In a separate terminal:

```bash
cd backend
python test_api.py
```

## Quick Demo Scripts

### Test via curl

```bash
# Health check
curl http://localhost:8000/health

# Chat
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: krishi-sarthi-dev-key-2024" \
  -d '{"message": "Mere tamatar mein rog hai", "language": "hi"}'

# Vendor search
curl -X POST http://localhost:8000/api/find-vendors \
  -H "Content-Type: application/json" \
  -H "X-API-Key: krishi-sarthi-dev-key-2024" \
  -d '{"latitude": 30.9, "longitude": 75.85, "query": "pesticide"}'
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check (no auth) |
| GET | `/docs` | Swagger UI (no auth) |
| POST | `/api/speech-to-text` | Audio → text |
| POST | `/api/diagnose-image` | Image → disease |
| POST | `/api/find-vendors` | Location → vendors |
| POST | `/api/chat` | Text/image → agent |
| POST | `/api/notify-vendor` | Send notification |

All `/api/*` endpoints require `X-API-Key` header.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| Database error | Auto-falls back to SQLite in demo mode |
| Redis error | Ignored in demo mode (in-memory rate limiting) |
| CORS errors | Serve frontend via `python -m http.server 3000` |
| Port 8000 in use | Change `API_PORT` in `.env` |
