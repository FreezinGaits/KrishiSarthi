"""
Demo Seed Data Loader — Insert sample records for hackathon demo.

Run with: python -m scripts.seed_demo_data
"""

import asyncio
import json
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")


async def seed():
    from app.config import get_settings
    from app.models.database import init_db, async_session
    from app.models.orm import User, DiagnosisResult, Vendor, Notification, Session

    settings = get_settings()
    print("🌱 Seeding demo data...")

    await init_db()

    async with async_session() as db:
        # ── Users ─────────────────────────────────
        users = [
            User(
                id=str(uuid.uuid4()),
                phone="+91 98765 43210",
                name="Gurpreet Singh",
                language="hi",
                location_lat=30.9010,
                location_lng=75.8573,
                created_at=datetime.utcnow() - timedelta(days=30),
            ),
            User(
                id=str(uuid.uuid4()),
                phone="+91 98123 45678",
                name="Harjeet Kaur",
                language="hi",
                location_lat=31.6340,
                location_lng=74.8723,
                created_at=datetime.utcnow() - timedelta(days=15),
            ),
            User(
                id=str(uuid.uuid4()),
                phone="+91 94170 12345",
                name="Rajveer Sidhu",
                language="pa",
                location_lat=30.3398,
                location_lng=76.3869,
                created_at=datetime.utcnow() - timedelta(days=7),
            ),
        ]
        for u in users:
            db.add(u)
        print(f"  ✅ {len(users)} users added")

        # ── Diagnosis Records ─────────────────────
        diagnoses = [
            DiagnosisResult(
                id=str(uuid.uuid4()),
                user_id=users[0].id,
                image_path="uploads/tomato_leaf_001.jpg",
                disease_name="Tomato Early Blight",
                confidence=0.92,
                treatment="Apply Mancozeb 75% WP at 2.5g/L. Remove affected leaves.",
                pesticide="Mancozeb 75% WP",
                raw_predictions=json.dumps([
                    {"disease": "Tomato Early Blight", "confidence": 0.92},
                    {"disease": "Tomato Septoria Leaf Spot", "confidence": 0.65},
                ]),
                created_at=datetime.utcnow() - timedelta(days=2),
            ),
            DiagnosisResult(
                id=str(uuid.uuid4()),
                user_id=users[1].id,
                image_path="uploads/wheat_rust_002.jpg",
                disease_name="Wheat Yellow Rust",
                confidence=0.88,
                treatment="Apply Propiconazole 25% EC at 1ml/L IMMEDIATELY.",
                pesticide="Propiconazole 25% EC",
                raw_predictions=json.dumps([
                    {"disease": "Wheat Yellow Rust", "confidence": 0.88},
                    {"disease": "Wheat Brown Rust", "confidence": 0.72},
                ]),
                created_at=datetime.utcnow() - timedelta(days=1),
            ),
            DiagnosisResult(
                id=str(uuid.uuid4()),
                user_id=users[2].id,
                image_path="uploads/rice_blast_003.jpg",
                disease_name="Rice Leaf Blast",
                confidence=0.85,
                treatment="Apply Tricyclazole 75% WP at 0.6g/L.",
                pesticide="Tricyclazole 75% WP",
                raw_predictions=json.dumps([
                    {"disease": "Rice Leaf Blast", "confidence": 0.85},
                    {"disease": "Rice Brown Spot", "confidence": 0.60},
                ]),
                created_at=datetime.utcnow(),
            ),
        ]
        for d in diagnoses:
            db.add(d)
        print(f"  ✅ {len(diagnoses)} diagnosis records added")

        # ── Vendors ───────────────────────────────
        vendor_file = Path(__file__).parent.parent / "data" / "vendors_punjab.json"
        if vendor_file.exists():
            vendor_data = json.loads(vendor_file.read_text(encoding="utf-8"))
            for v in vendor_data[:10]:
                db.add(Vendor(
                    id=str(uuid.uuid4()),
                    name=v["name"],
                    address=v["address"],
                    phone=v["phone"],
                    lat=v["lat"],
                    lng=v["lng"],
                    rating=v.get("rating", 4.0),
                    pesticides_available=json.dumps(v.get("pesticides_available", [])),
                    verified=True,
                    created_at=datetime.utcnow() - timedelta(days=60),
                ))
            print(f"  ✅ {min(10, len(vendor_data))} vendors added from Punjab DB")
        else:
            print("  ⚠️  vendors_punjab.json not found — skipping vendor seed")

        # ── Notifications ─────────────────────────
        notifications = [
            Notification(
                id=str(uuid.uuid4()),
                user_id=users[0].id,
                vendor_id=None,
                channel="sms",
                message="आपकी फसल में टमाटर अगेती झुलसा रोग पाया गया। Mancozeb 75% WP 2.5g/L पानी में मिलाकर छिड़काव करें।",
                status="delivered",
                created_at=datetime.utcnow() - timedelta(hours=6),
            ),
        ]
        for n in notifications:
            db.add(n)
        print(f"  ✅ {len(notifications)} notifications added")

        await db.commit()

    print("\n🌾 Demo data seeded successfully!")
    print("   Users: 3 | Diagnoses: 3 | Vendors: 10 | Notifications: 1")


if __name__ == "__main__":
    asyncio.run(seed())
