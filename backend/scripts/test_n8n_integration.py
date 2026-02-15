"""
n8n Integration Test Script
============================
Tests all n8n webhook endpoints and verifies responses.
Run: python scripts/test_n8n_integration.py

Requires n8n to be running at N8N_BASE_URL (default: http://localhost:5678).
Falls back to backend n8n_service demo-mode simulation if n8n is unreachable.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from typing import Dict, List, Tuple

# Add backend to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass

import httpx

# ── Configuration ─────────────────────────────────
N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://localhost:5678")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
TIMEOUT = 10.0

# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


# ── Test Payloads ─────────────────────────────────

NOTIFICATION_PAYLOAD = {
    "event": "send_notification",
    "notification_id": "TEST-NOTIF-001",
    "phone": "+91 98765 43210",
    "channel": "sms",
    "message": "Test notification from integration test",
    "metadata": {
        "disease_name": "Early Blight",
        "confidence": 0.87,
        "treatment": "Apply Mancozeb 75% WP at 2.5g/litre of water",
        "pesticide": "Mancozeb 75% WP",
        "nearest_vendor": "Kisan Agro Center, Ludhiana",
        "location": {"lat": 30.9, "lng": 75.85},
    },
}

ESCALATION_PAYLOAD = {
    "event": "low_confidence_escalation",
    "diagnosis": {
        "disease_name": "Unknown Leaf Spot",
        "confidence": 0.35,
        "treatment": "Requires expert review",
        "pesticide": "",
        "location": {"lat": 30.9, "lng": 75.85},
    },
    "confidence": 0.35,
    "request_id": "TEST-ESC-001",
}

VENDOR_ENRICHMENT_PAYLOAD = {
    "vendor_id": "TEST-VND-001",
    "name": "Test Krishi Store",
    "address": "Main Market, Model Town, Ludhiana, Punjab 141002",
    "phone": "+91 98765 00000",
    "lat": 30.901,
    "lng": 75.857,
    "city": "Ludhiana",
    "state": "Punjab",
    "products": ["Mancozeb", "Imidacloprid", "DAP Fertilizer", "Hybrid Seeds"],
    "rating": 4.5,
    "accepts_digital_payment": True,
    "delivery_available": False,
}

RETRAINING_PAYLOAD = {
    "event": "retraining_sample",
    "original_disease": "Late Blight",
    "original_confidence": 0.45,
    "corrected_disease": "Septoria Leaf Spot",
    "corrected_by": "dr_singh_pau",
    "correction_source": "escalation_review",
    "model_version": "v1.0",
    "crop": "tomato",
    "image_path": "/uploads/test_image.jpg",
    "request_id": "TEST-RTR-001",
    "location": {"lat": 30.9, "lng": 75.85},
}


# ── Test Runner ───────────────────────────────────

async def test_webhook(
    client: httpx.AsyncClient,
    name: str,
    webhook_path: str,
    payload: dict,
    expected_fields: List[str],
) -> Tuple[bool, str]:
    """Test a single n8n webhook endpoint."""
    url = f"{N8N_BASE_URL}{webhook_path}"

    try:
        response = await client.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT,
        )

        if response.status_code == 200:
            try:
                data = response.json()
            except Exception:
                data = {"raw": response.text[:200]}

            # Check for expected fields
            missing = [f for f in expected_fields if f not in str(data)]
            if missing:
                return True, f"200 OK but missing fields: {missing} | Response: {json.dumps(data)[:150]}"
            return True, f"200 OK | {json.dumps(data)[:120]}"

        elif response.status_code == 404:
            return False, f"404 — Workflow not active or webhook path mismatch"
        else:
            return False, f"HTTP {response.status_code} | {response.text[:100]}"

    except httpx.ConnectError:
        return False, f"Connection refused — is n8n running at {N8N_BASE_URL}?"
    except httpx.TimeoutException:
        return False, f"Timeout after {TIMEOUT}s"
    except Exception as e:
        return False, f"Error: {str(e)[:100]}"


async def test_backend_n8n_service() -> List[Tuple[str, bool, str]]:
    """Test n8n integration through the backend's n8n_service (demo mode)."""
    results = []

    try:
        from app.config import get_settings
        settings = get_settings()

        if not settings.is_demo:
            results.append(("Backend n8n_service", False, "Not in DEMO_MODE — skipping backend service test"))
            return results

        # Test trigger_notification
        try:
            from app.services.n8n_service import trigger_notification
            resp = await trigger_notification(
                phone="+91 98765 43210",
                message="Integration test notification",
                channel="sms",
                metadata={"disease_name": "Test Disease", "confidence": 0.9},
                request_id="INT-TEST-001",
            )
            status = getattr(resp, 'status', str(resp))
            results.append(("Backend: trigger_notification()", True, f"Status: {status}"))
        except Exception as e:
            results.append(("Backend: trigger_notification()", False, str(e)[:100]))

        # Test trigger_escalation
        try:
            from app.services.n8n_service import trigger_escalation
            resp = await trigger_escalation(
                diagnosis_data={"disease_name": "Unknown", "confidence": 0.3},
                confidence=0.3,
                request_id="INT-TEST-002",
            )
            results.append(("Backend: trigger_escalation()", True, f"Response: {json.dumps(resp)[:100]}"))
        except Exception as e:
            results.append(("Backend: trigger_escalation()", False, str(e)[:100]))

        # Test trigger_vendor_enrichment
        try:
            from app.services.n8n_service import trigger_vendor_enrichment
            resp = await trigger_vendor_enrichment(
                vendor_data={"name": "Test Vendor", "lat": 30.9, "lng": 75.85},
                request_id="INT-TEST-003",
            )
            results.append(("Backend: trigger_vendor_enrichment()", True, f"Response: {json.dumps(resp)[:100]}"))
        except Exception as e:
            results.append(("Backend: trigger_vendor_enrichment()", False, str(e)[:100]))

    except ImportError as e:
        results.append(("Backend n8n_service", False, f"Import error: {e} — run from backend/ directory"))

    return results


async def run_all_tests():
    """Execute all n8n integration tests."""
    print(f"\n{BOLD}{CYAN}╔══════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYAN}║    Krishi-Sarthi  ·  n8n Integration Tests           ║{RESET}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════╝{RESET}\n")

    print(f"  n8n URL:     {N8N_BASE_URL}")
    print(f"  Backend URL: {BACKEND_URL}")
    print(f"  Timeout:     {TIMEOUT}s\n")

    # ── Phase 1: Direct webhook tests ─────────────
    print(f"{BOLD}─── Phase 1: n8n Webhook Tests ──────────────────────{RESET}\n")

    webhook_tests = [
        (
            "Send Notification (SMS)",
            "/webhook/send-notification",
            NOTIFICATION_PAYLOAD,
            ["status", "notification_id"],
        ),
        (
            "Low Confidence Escalation",
            "/webhook/escalation",
            ESCALATION_PAYLOAD,
            ["status", "escalation_id"],
        ),
        (
            "Vendor Enrichment",
            "/webhook/vendor-enrichment",
            VENDOR_ENRICHMENT_PAYLOAD,
            ["status", "vendor_id"],
        ),
        (
            "Model Retraining Trigger",
            "/webhook/retraining-trigger",
            RETRAINING_PAYLOAD,
            ["status", "sample_id"],
        ),
    ]

    results: List[Tuple[str, bool, str]] = []
    n8n_available = True

    async with httpx.AsyncClient() as client:
        for name, path, payload, expected in webhook_tests:
            passed, detail = await test_webhook(client, name, path, payload, expected)
            results.append((name, passed, detail))

            icon = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
            print(f"  {icon}  {name}")
            print(f"         {detail}\n")

            if "Connection refused" in detail:
                n8n_available = False
                print(f"  {YELLOW}⚠  n8n not reachable — skipping remaining webhook tests{RESET}\n")
                # Mark remaining as skipped
                for remaining_name, _, _, _ in webhook_tests[webhook_tests.index((name, path, payload, expected)) + 1:]:
                    results.append((remaining_name, False, "Skipped — n8n not available"))
                    print(f"  {YELLOW}○ SKIP{RESET}  {remaining_name}")
                    print(f"         Skipped — n8n not available\n")
                break

    # ── Phase 2: Backend service tests ────────────
    print(f"\n{BOLD}─── Phase 2: Backend n8n_service Tests ──────────────{RESET}\n")

    backend_results = await test_backend_n8n_service()
    results.extend(backend_results)

    for name, passed, detail in backend_results:
        icon = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
        print(f"  {icon}  {name}")
        print(f"         {detail}\n")

    # ── Summary ───────────────────────────────────
    total = len(results)
    passed = sum(1 for _, p, _ in results if p)
    failed = total - passed

    print(f"\n{BOLD}═══════════════════════════════════════════════════════{RESET}")
    print(f"  {BOLD}Results:{RESET}  {GREEN}{passed} passed{RESET}  ·  {RED if failed else GREEN}{failed} failed{RESET}  ·  {total} total")

    if not n8n_available:
        print(f"\n  {YELLOW}💡 Tip: Start n8n with 'npx n8n start' and import workflows{RESET}")
        print(f"  {YELLOW}   from n8n/workflows/ to test webhook endpoints.{RESET}")

    print(f"{BOLD}═══════════════════════════════════════════════════════{RESET}\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
