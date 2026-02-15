"""
Krishi-Sarthi — API Integration Test Script

Tests all 4 core endpoints against the running backend.
Run with: python test_api.py
"""

import asyncio
import json
import sys
import time

try:
    import httpx
except ImportError:
    print("❌ httpx not installed. Run: pip install httpx")
    sys.exit(1)

BASE_URL = "http://localhost:8000"
API_KEY = "krishi-sarthi-dev-key-2024"
HEADERS = {"X-API-Key": API_KEY}

PASS = "✅ PASS"
FAIL = "❌ FAIL"
SKIP = "⚠️  SKIP"

results = []


def report(name: str, passed: bool, detail: str = ""):
    status = PASS if passed else FAIL
    results.append((name, passed))
    print(f"  {status}  {name}")
    if detail:
        for line in detail.split("\n"):
            print(f"         {line}")


async def run_tests():
    async with httpx.AsyncClient(base_url=BASE_URL, headers=HEADERS, timeout=30.0) as client:

        # ── 0. Health Check ───────────────────────
        print("\n  ─── Health Check ───────────────────")
        try:
            r = await client.get("/health")
            data = r.json()
            report("Health endpoint", r.status_code == 200,
                   f"Status: {data.get('status')} | Demo: {data.get('demo_mode')}")
        except Exception as e:
            report("Health endpoint", False, str(e))
            print("\n  ❌ Backend not running! Start with: python run.py")
            return

        # ── 1. Speech-to-Text ─────────────────────
        print("\n  ─── Speech-to-Text ─────────────────")
        try:
            # Create a minimal WAV header (empty audio, but valid format)
            wav_header = (
                b"RIFF" + (36).to_bytes(4, "little") +
                b"WAVE" +
                b"fmt " + (16).to_bytes(4, "little") +
                (1).to_bytes(2, "little") +    # PCM
                (1).to_bytes(2, "little") +    # mono
                (16000).to_bytes(4, "little") + # 16kHz
                (32000).to_bytes(4, "little") + # byte rate
                (2).to_bytes(2, "little") +    # block align
                (16).to_bytes(2, "little") +   # bits per sample
                b"data" + (0).to_bytes(4, "little")
            )
            files = {"audio": ("test.wav", wav_header, "audio/wav")}
            r = await client.post("/api/speech-to-text", files=files)
            data = r.json()
            if r.status_code == 200:
                transcript = data.get("transcript", data.get("text", ""))
                lang = data.get("detected_language", "?")
                conf = data.get("confidence", 0)
                report("Speech-to-Text", True,
                       f"Transcript: '{transcript[:60]}'\n"
                       f"Language: {lang} | Confidence: {conf:.2f}")
            else:
                report("Speech-to-Text", False, f"Status {r.status_code}: {data}")
        except Exception as e:
            report("Speech-to-Text", False, str(e))

        # ── 2. Diagnose Image ─────────────────────
        print("\n  ─── Image Diagnosis ────────────────")
        try:
            # Create a minimal 1x1 JPEG
            # Smallest valid JPEG: FF D8 FF E0 ... FF D9
            import struct
            # Use a small red pixel JPEG (minimal valid)
            jpeg_bytes = bytes([
                0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46,
                0x49, 0x46, 0x00, 0x01, 0x01, 0x00, 0x00, 0x01,
                0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
                0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08,
                0x07, 0x07, 0x07, 0x09, 0x09, 0x08, 0x0A, 0x0C,
                0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
                0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D,
                0x1A, 0x1C, 0x1C, 0x20, 0x24, 0x2E, 0x27, 0x20,
                0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
                0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27,
                0x39, 0x3D, 0x38, 0x32, 0x3C, 0x2E, 0x33, 0x34,
                0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
                0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4,
                0x00, 0x1F, 0x00, 0x00, 0x01, 0x05, 0x01, 0x01,
                0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04,
                0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0xFF,
                0xC4, 0x00, 0xB5, 0x10, 0x00, 0x02, 0x01, 0x03,
                0x03, 0x02, 0x04, 0x03, 0x05, 0x05, 0x04, 0x04,
                0x00, 0x00, 0x01, 0x7D, 0x01, 0x02, 0x03, 0x00,
                0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06,
                0x13, 0x51, 0x61, 0x07, 0x22, 0x71, 0x14, 0x32,
                0x81, 0x91, 0xA1, 0x08, 0x23, 0x42, 0xB1, 0xC1,
                0x15, 0x52, 0xD1, 0xF0, 0x24, 0x33, 0x62, 0x72,
                0x82, 0x09, 0x0A, 0x16, 0x17, 0x18, 0x19, 0x1A,
                0x25, 0x26, 0x27, 0x28, 0x29, 0x2A, 0x34, 0x35,
                0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00,
                0x3F, 0x00, 0x7B, 0x94, 0x11, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                0xFF, 0xD9
            ])
            files = {"image": ("tomato_leaf_test.jpg", jpeg_bytes, "image/jpeg")}
            r = await client.post("/api/diagnose-image", files=files)
            data = r.json()
            if r.status_code == 200:
                disease = data.get("top_disease", "?")
                conf = data.get("top_confidence", 0)
                pesticide = data.get("pesticide", "?")
                report("Image Diagnosis", True,
                       f"Disease: {disease}\n"
                       f"Confidence: {conf:.0%} | Pesticide: {pesticide}")
            else:
                report("Image Diagnosis", False, f"Status {r.status_code}: {data}")
        except Exception as e:
            report("Image Diagnosis", False, str(e))

        # ── 3. Vendor Search ──────────────────────
        print("\n  ─── Vendor Search ──────────────────")
        try:
            payload = {
                "latitude": 30.9,
                "longitude": 75.85,
                "query": "pesticide shop",
                "radius_km": 10,
            }
            r = await client.post("/api/find-vendors",
                                  json=payload,
                                  headers={"Content-Type": "application/json"})
            data = r.json()
            if r.status_code == 200:
                vendors = data.get("vendors", [])
                total = data.get("total", 0)
                top = vendors[0]["name"] if vendors else "None"
                report("Vendor Search", True,
                       f"Found: {total} vendors\n"
                       f"Nearest: {top}")
            else:
                report("Vendor Search", False, f"Status {r.status_code}: {data}")
        except Exception as e:
            report("Vendor Search", False, str(e))

        # ── 4. Chat / Agent ───────────────────────
        print("\n  ─── Chat / Agent ───────────────────")
        queries = [
            ("Hindi disease query", "Mere tamatar ki patti par kale dhabbe hain, kya karu?"),
            ("Vendor search query", "Nazdiki keetnashak dukaan kahan hai?"),
            ("Greeting", "Namaste, mujhe madad chahiye"),
        ]

        for test_name, query in queries:
            try:
                payload = {
                    "message": query,
                    "session_id": "test-session",
                    "language": "hi",
                    "latitude": 30.9,
                    "longitude": 75.85,
                }
                r = await client.post("/api/chat",
                                      json=payload,
                                      headers={"Content-Type": "application/json"})
                data = r.json()
                if r.status_code == 200:
                    reply = data.get("reply", "")[:80]
                    report(f"Chat: {test_name}", True, f"Reply: {reply}...")
                else:
                    report(f"Chat: {test_name}", False, f"Status {r.status_code}")
            except Exception as e:
                report(f"Chat: {test_name}", False, str(e))

    # ── Summary ───────────────────────────────────
    total = len(results)
    passed = sum(1 for _, p in results if p)
    failed = total - passed

    print("\n  ═══════════════════════════════════════")
    print(f"  Results: {passed}/{total} passed", end="")
    if failed:
        print(f"  ({failed} failed)")
    else:
        print("  🎉 All tests passed!")
    print("  ═══════════════════════════════════════\n")


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════╗
    ║   🧪  Krishi-Sarthi API Test Suite          ║
    ╚══════════════════════════════════════════════╝
    """)
    asyncio.run(run_tests())
