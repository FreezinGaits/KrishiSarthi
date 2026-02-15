"""
Krishi-Sarthi — Backend Startup Script

Verifies all dependencies, initializes services, and starts the FastAPI server.
Run with: python run.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Ensure the backend directory is in the Python path
BACKEND_DIR = Path(__file__).parent
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))
os.chdir(str(PROJECT_ROOT))

# Load .env from project root
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")


def print_banner():
    print(r"""
    ╔══════════════════════════════════════════════════╗
    ║          🌾  KRISHI-SARTHI  🌾                   ║
    ║     Vernacular Agentic AI for Farmers            ║
    ║                                                  ║
    ║     Voice • Vision • Vendor Discovery            ║
    ╚══════════════════════════════════════════════════╝
    """)


def check_env():
    """Verify critical environment variables."""
    from app.config import get_settings
    settings = get_settings()

    checks = {
        "App Name": settings.app_name,
        "Environment": settings.environment,
        "Demo Mode": "✅ ON" if settings.is_demo else "❌ OFF",
        "Mock AI": "✅ ON" if settings.mock_ai_responses else "❌ OFF",
        "Mock Vendors": "✅ ON" if settings.mock_vendor_data else "❌ OFF",
        "Database URL": settings.database_url[:40] + "..." if len(settings.database_url) > 40 else settings.database_url,
        "OpenAI Key": "✅ Set" if settings.openai_api_key else "⚠️  Not set",
        "Google Maps Key": "✅ Set" if settings.google_maps_api_key else "⚠️  Not set (using OSM)",
        "Twilio SID": "✅ Set" if settings.twilio_account_sid else "⚠️  Not set",
        "n8n URL": settings.n8n_base_url,
    }

    print("  ┌─── Configuration ───────────────────────────┐")
    for key, val in checks.items():
        print(f"  │  {key:<18} {val}")
    print("  └────────────────────────────────────────────┘")
    print()

    return settings


async def verify_database(settings):
    """Verify database connection and create tables."""
    print("  ⏳ Initializing database...", end=" ", flush=True)
    try:
        from app.models.database import init_db
        await init_db()
        print("✅ Database ready")
        return True
    except Exception as e:
        print(f"⚠️  Database error: {e}")
        print("     → Using SQLite fallback for demo")
        # Fallback: override to SQLite
        os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./krishi_demo.db"
        try:
            # Clear cached settings
            from app.config import get_settings
            get_settings.cache_clear()
            from app.models import database
            import importlib
            importlib.reload(database)
            await database.init_db()
            print("  ✅ SQLite fallback ready")
            return True
        except Exception as e2:
            print(f"  ❌ SQLite fallback also failed: {e2}")
            return False


async def verify_redis(settings):
    """Verify Redis connection (optional for demo)."""
    print("  ⏳ Checking Redis...", end=" ", flush=True)
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url, socket_timeout=3)
        await r.ping()
        await r.close()
        print("✅ Redis connected")
        return True
    except Exception as e:
        print(f"⚠️  Redis not available ({type(e).__name__})")
        print("     → Using in-memory fallback (fine for demo)")
        return False


def verify_services():
    """Verify service modules can be imported."""
    print("  ⏳ Verifying services...", flush=True)
    services = {
        "Whisper STT": "app.services.whisper_service",
        "Classifier": "app.services.classifier_service",
        "Vendor Search": "app.services.vendor_service",
        "RAG Knowledge": "app.services.rag_service",
        "Agent": "app.services.agent_service",
        "n8n Webhooks": "app.services.n8n_service",
    }

    all_ok = True
    for name, module in services.items():
        try:
            __import__(module)
            print(f"     ✅ {name}")
        except ImportError as e:
            print(f"     ❌ {name}: {e}")
            all_ok = False
        except Exception as e:
            print(f"     ⚠️  {name}: {e} (non-fatal)")

    return all_ok


async def startup_checks():
    """Run all startup verification checks."""
    settings = check_env()

    # Ensure upload directory
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)

    db_ok = await verify_database(settings)
    redis_ok = await verify_redis(settings)
    services_ok = verify_services()

    print()
    if db_ok and services_ok:
        print("  ✅ Krishi-Sarthi backend ready!")
    elif settings.is_demo:
        print("  ⚠️  Some checks failed, but DEMO_MODE is ON — proceeding anyway")
    else:
        print("  ❌ Some critical checks failed. Fix issues above before running in production.")

    print()
    return settings


def main():
    """Entry point — run startup checks then launch uvicorn."""
    print_banner()

    settings = asyncio.run(startup_checks())

    print(f"  🚀 Starting server on http://{settings.api_host}:{settings.api_port}")
    print(f"  📖 API docs: http://localhost:{settings.api_port}/docs")
    print(f"  🌐 Demo UI:  Open frontend/demo.html in browser")
    print()

    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
