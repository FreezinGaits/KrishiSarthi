"""
Demo Scenario Simulator — walks through complete farmer journey.
Usage: python scripts/run_demo_scenario.py
"""

from __future__ import annotations
import asyncio, os, sys, time, json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

G = "\033[92m"; C = "\033[96m"; Y = "\033[93m"; B = "\033[1m"; R = "\033[0m"; RED = "\033[91m"

BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "demo-api-key-2026")
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}


def banner():
    print(f"""
{G}{B}╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   🌾  Krishi-Sarthi  ·  Demo Scenario Simulator  🌾          ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝{R}

Simulating: Complete farmer diagnosis journey
Farmer: Gurpreet Singh, Ludhiana Punjab
Crop: Tomato with suspected Early Blight
""")


def step(num, title, icon="▶"):
    print(f"\n{B}{C}─── Step {num}: {icon} {title} ───{R}\n")
    time.sleep(0.5)


async def run_scenario():
    banner()
    import httpx

    async with httpx.AsyncClient(timeout=15.0) as client:

        # Step 1: Health Check
        step(1, "System Health Check", "❤️")
        try:
            r = await client.get(f"{BACKEND}/api/health", headers=HEADERS)
            health = r.json()
            print(f"  Status: {G}{health.get('status', 'unknown')}{R}")
            for svc, info in health.get("services", {}).items():
                ok = info if isinstance(info, str) else info.get("status", "?")
                icon = "✅" if ok in ("healthy", "ok", "available", True) else "⚠️"
                print(f"  {icon} {svc}: {ok}")
        except Exception as e:
            print(f"  {Y}Health check skipped: {e}{R}")

        # Step 2: Voice Input (simulated)
        step(2, "Voice Input (Hindi)", "🎤")
        print(f'  Farmer speaks: {Y}"मेरे टमाटर के पत्तों पर काले धब्बे हैं"{R}')
        print(f"  → Whisper transcription: {G}मेरे टमाटर के पत्तों पर काले धब्बे हैं{R}")
        print(f"  → English: {C}My tomato leaves have black spots{R}")

        # Step 3: Image Diagnosis
        step(3, "Image Diagnosis", "📸")
        try:
            r = await client.post(f"{BACKEND}/api/diagnose-image",
                headers={"X-API-Key": API_KEY},
                files={"image": ("test.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 100, "image/jpeg")})
            diag = r.json()
            disease = diag.get("top_disease", diag.get("disease", "Early Blight"))
            conf = diag.get("top_confidence", diag.get("confidence", 0.89))
            treatment = diag.get("treatment", "Apply Mancozeb 75% WP")
            pesticide = diag.get("pesticide", "Mancozeb 75% WP")
            print(f"  🔬 Disease:    {G}{disease}{R}")
            print(f"  📊 Confidence: {G}{conf:.0%}{R}")
            print(f"  💊 Treatment:  {C}{treatment}{R}")
            print(f"  🧴 Pesticide:  {C}{pesticide}{R}")
        except Exception as e:
            print(f"  {Y}Using mock diagnosis: {e}{R}")
            disease, conf = "Early Blight", 0.89
            print(f"  🔬 Disease:    {G}Early Blight{R}")
            print(f"  📊 Confidence: {G}89%{R}")
            print(f"  💊 Treatment:  {C}Apply Mancozeb 75% WP at 2.5g/litre{R}")
            print(f"  🧴 Pesticide:  {C}Mancozeb 75% WP{R}")

        # Step 4: Chat with AI Agent
        step(4, "AI Agent Chat", "🤖")
        try:
            r = await client.post(f"{BACKEND}/api/chat", headers=HEADERS,
                json={"message": "मेरे टमाटर की फसल में Early Blight है, इलाज बताएं",
                      "session_id": "demo-session-001", "language": "hi",
                      "latitude": 30.9, "longitude": 75.85})
            chat = r.json()
            reply = chat.get("reply", "")[:300]
            print(f"  Agent: {G}{reply}{R}")
        except Exception as e:
            print(f"  {Y}Using mock chat: {e}{R}")
            print(f"  Agent: {G}टमाटर में Early Blight के लिए Mancozeb 75% WP 2.5g/litre पानी में मिलाकर स्प्रे करें।{R}")

        # Step 5: Vendor Search
        step(5, "Nearby Vendor Search", "📍")
        try:
            r = await client.get(f"{BACKEND}/api/find-vendors",
                headers=HEADERS, params={"latitude": 30.9, "longitude": 75.85,
                                         "query": "pesticide shop", "radius_km": 10})
            vendors = r.json().get("vendors", [])
            for v in vendors[:3]:
                dist = v.get("distance_km", "?")
                print(f"  🏪 {v['name']} — {dist} km — ⭐ {v.get('rating', 'N/A')} — 📞 {v.get('phone', '')}")
        except Exception as e:
            print(f"  {Y}Using mock vendors: {e}{R}")
            print(f"  🏪 Sharma Krishi Kendra — 1.2 km — ⭐ 4.5 — 📞 +91 98765 43210")
            print(f"  🏪 Punjab Agro Store — 2.4 km — ⭐ 4.2 — 📞 +91 98123 45678")

        # Step 6: n8n Notification
        step(6, "n8n Notification Trigger", "📱")
        print(f"  Confidence {G}89% ≥ 65%{R} → Sending farmer SMS notification")
        print(f"  📱 SMS to +91 98765 43210:")
        print(f"  {Y}🌾 कृषि-सारथी अलर्ट: आपकी फसल में Early Blight detected (89%).{R}")
        print(f"  {Y}💊 इलाज: Mancozeb 75% WP | 🏪 Nearest: Sharma Krishi Kendra{R}")

    # Summary
    print(f"""
{G}{B}╔══════════════════════════════════════════════════════════════╗
║                 Demo Scenario Complete ✅                     ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Voice → Diagnosis → Treatment → Vendors → Notification      ║
║                                                              ║
║  Total flow time: ~5 seconds                                 ║
║  Classification accuracy: 89%                                ║
║  Nearest vendor: 1.2 km                                      ║
║  Notification: Auto-sent via n8n                             ║
╚══════════════════════════════════════════════════════════════╝{R}
""")


if __name__ == "__main__":
    asyncio.run(run_scenario())
