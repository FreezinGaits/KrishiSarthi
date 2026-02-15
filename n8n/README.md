# n8n Workflows — Krishi-Sarthi

## Overview

5 production-ready n8n workflow definitions that integrate with the Krishi-Sarthi backend via webhooks.

| Workflow | Trigger | Webhook Path | Purpose |
|----------|---------|-------------|---------|
| **Vendor Enrichment** | POST webhook | `/webhook/vendor-enrichment` | Enrich vendor data with quality scores |
| **Send Notification** | POST webhook | `/webhook/send-notification` | Format Hindi message → SMS/WhatsApp |
| **Escalation** | POST webhook | `/webhook/escalation` | Route low-confidence diagnoses to experts |
| **Retraining Trigger** | POST webhook | `/webhook/retraining-trigger` | Queue corrected diagnoses for model retraining |
| **Price Aggregation** | Daily cron (6 AM) | — | Aggregate pesticide prices across vendors |

---

## Quick Start

### 1. Install n8n

```bash
# Using npm
npm install -g n8n

# Or using Docker
docker run -it --rm -p 5678:5678 n8nio/n8n
```

### 2. Start n8n

```bash
n8n start
# Opens at http://localhost:5678
```

### 3. Import Workflows

1. Open n8n UI → **Workflows** → **Import from File**
2. Import each file from `n8n/workflows/`:
   - `vendor_enrichment.json`
   - `send_notification.json`
   - `escalation.json`
   - `retraining_trigger.json`
   - `price_aggregation.json`
3. **Activate** each workflow (toggle ON)

### 4. Set Environment Variable

In n8n Settings → Environment Variables:

```
KRISHI_API_KEY=dev-api-key-change-me
```

---

## How Backend Connects

```
Backend (FastAPI)                    n8n
┌──────────────────┐      POST     ┌──────────────────┐
│ agent_service.py │ ────────────→ │ send_notification │
│  (diagnosis done)│               │   or escalation   │
└──────────────────┘               └──────────────────┘
        │                                  │
        │ confidence ≥ 65%                 │ Routes to SMS
        │ confidence < 65%                 │ or WhatsApp
        ▼                                  ▼
  notification webhook              escalation webhook
```

**Backend service**: `backend/app/services/n8n_service.py`

| Function | Webhook Called |
|----------|--------------|
| `trigger_vendor_enrichment()` | `/webhook/vendor-enrichment` |
| `trigger_notification()` | `/webhook/send-notification` |
| `trigger_escalation()` | `/webhook/escalation` |
| `trigger_retraining()` | `/webhook/retraining-trigger` |

---

## Testing Webhooks

### With curl

```bash
# Notification
curl -X POST http://localhost:5678/webhook/send-notification \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+91 98765 43210",
    "channel": "sms",
    "metadata": {
      "disease_name": "Early Blight",
      "confidence": 0.87,
      "treatment": "Apply Mancozeb 75% WP at 2.5g/litre",
      "pesticide": "Mancozeb"
    }
  }'

# Escalation
curl -X POST http://localhost:5678/webhook/escalation \
  -H "Content-Type: application/json" \
  -d '{
    "diagnosis": {
      "disease_name": "Unknown Leaf Spot",
      "confidence": 0.35,
      "treatment": "Requires expert review"
    },
    "confidence": 0.35,
    "request_id": "test-123"
  }'

# Vendor Enrichment
curl -X POST http://localhost:5678/webhook/vendor-enrichment \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Krishi Store",
    "address": "Main Market, Ludhiana",
    "phone": "+91 98765 00000",
    "lat": 30.901,
    "lng": 75.857,
    "products": ["pesticides", "fertilizer", "seeds"],
    "rating": 4.5
  }'

# Retraining
curl -X POST http://localhost:5678/webhook/retraining-trigger \
  -H "Content-Type: application/json" \
  -d '{
    "original_disease": "Late Blight",
    "original_confidence": 0.45,
    "corrected_disease": "Septoria Leaf Spot",
    "model_version": "v1.0",
    "crop": "tomato"
  }'
```

### With Python

```bash
cd backend
python scripts/test_n8n_integration.py
```

---

## Production Notes

| Node | Replace With |
|------|-------------|
| `Send SMS (Mock)` | Twilio SMS node or MSG91 API |
| `Send WhatsApp (Mock)` | WhatsApp Business API node |
| `Alert PAU Agronomist` | Email node + Slack integration |
| `Load Pesticide Prices` | Web scraper or vendor API calls |
| `Store *` HTTP nodes | Point to production backend URL |
