"""
Load Demo Data — seed the database with demo content.
Usage: python scripts/load_demo_data.py
"""

from __future__ import annotations
import asyncio, os, sys, json
from pathlib import Path
from datetime import datetime, timedelta
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

G = "\033[92m"; C = "\033[96m"; Y = "\033[93m"; B = "\033[1m"; R = "\033[0m"


DEMO_FARMERS = [
    {"name": "Gurpreet Singh", "phone": "+91 98765 43210", "village": "Khanna, Ludhiana", "land_acres": 5, "crops": ["Wheat", "Rice"]},
    {"name": "Amrit Kaur", "phone": "+91 94170 12345", "village": "Moga, Punjab", "land_acres": 8, "crops": ["Tomato", "Potato"]},
    {"name": "Harjinder Pal", "phone": "+91 98145 67890", "village": "Bathinda, Punjab", "land_acres": 12, "crops": ["Wheat", "Cotton"]},
]

DEMO_DIAGNOSES = [
    {"disease": "Early Blight", "crop": "Tomato", "confidence": 0.89, "treatment": "Apply Mancozeb 75% WP at 2.5g/litre", "pesticide": "Mancozeb 75% WP"},
    {"disease": "Brown Rust", "crop": "Wheat", "confidence": 0.76, "treatment": "Spray Propiconazole 25% EC at 1ml/litre", "pesticide": "Propiconazole 25% EC"},
    {"disease": "Rice Blast", "crop": "Rice", "confidence": 0.92, "treatment": "Apply Tricyclazole 75% WP at 0.6g/litre", "pesticide": "Tricyclazole 75% WP"},
    {"disease": "Late Blight", "crop": "Tomato", "confidence": 0.45, "treatment": "Expert review needed — escalated to PAU", "pesticide": "Copper Oxychloride 50% WP"},
    {"disease": "Sheath Blight", "crop": "Rice", "confidence": 0.81, "treatment": "Apply Hexaconazole 5% EC at 2ml/litre", "pesticide": "Hexaconazole 5% EC"},
]


def load_vendor_data():
    """Load vendors from Punjab database."""
    vp = Path(__file__).parent.parent / "data" / "vendors_punjab.json"
    if vp.exists():
        return json.loads(vp.read_text(encoding="utf-8"))
    return []


async def seed_data():
    """Seed demo data (prints to console — can be adapted for DB)."""
    print(f"\n{B}{G}═══ Krishi-Sarthi Demo Data Loader ═══{R}\n")

    # Farmers
    print(f"{C}[FARMERS]{R}")
    for f in DEMO_FARMERS:
        print(f"  👨‍🌾 {f['name']} — {f['village']} — {f['land_acres']} acres — {', '.join(f['crops'])}")
    print(f"  {G}✓ {len(DEMO_FARMERS)} demo farmers loaded{R}\n")

    # Diagnoses
    print(f"{C}[DIAGNOSIS HISTORY]{R}")
    for i, d in enumerate(DEMO_DIAGNOSES):
        ts = (datetime.now() - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d")
        farmer = DEMO_FARMERS[i % len(DEMO_FARMERS)]
        status = "✅" if d["confidence"] >= 0.65 else "⚠️"
        print(f"  {status} [{ts}] {farmer['name']} → {d['disease']} ({d['confidence']:.0%}) on {d['crop']}")
    print(f"  {G}✓ {len(DEMO_DIAGNOSES)} diagnosis records loaded{R}\n")

    # Vendors
    vendors = load_vendor_data()
    print(f"{C}[VENDORS]{R}")
    for v in vendors[:8]:
        print(f"  🏪 {v['name']} — {v.get('city', '')} — ⭐ {v.get('rating', 'N/A')}")
    if len(vendors) > 8:
        print(f"  ... and {len(vendors) - 8} more")
    print(f"  {G}✓ {len(vendors)} Punjab vendors loaded{R}\n")

    # Summary
    print(f"{B}{G}Demo data ready! Total: {len(DEMO_FARMERS)} farmers, {len(DEMO_DIAGNOSES)} diagnoses, {len(vendors)} vendors{R}\n")


if __name__ == "__main__":
    asyncio.run(seed_data())
