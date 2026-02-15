"""
Krishi-Sarthi — One-Command Demo Launcher
==========================================
Starts the backend and frontend together for hackathon demo.

Usage:
    python run_demo.py
"""

import os
import sys
import time
import shutil
import signal
import subprocess
import platform
from pathlib import Path

ROOT = Path(__file__).parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"

# ANSI
G = "\033[92m"; C = "\033[96m"; Y = "\033[93m"; B = "\033[1m"; R = "\033[0m"; RED = "\033[91m"

BANNER = f"""
{G}{B}╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   🌾  कृषि-सारथी  ·  Krishi-Sarthi  ·  Demo Launcher  🌾    ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝{R}
"""

processes = []

def cleanup(*_):
    print(f"\n{Y}Shutting down...{R}")
    for p in processes:
        try:
            if platform.system() == "Windows":
                p.terminate()
            else:
                os.killpg(os.getpgid(p.pid), signal.SIGTERM)
        except Exception:
            pass
    sys.exit(0)

signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)


def check_prereqs():
    """Verify required tools exist."""
    errors = []
    if not shutil.which("python") and not shutil.which("python3"):
        errors.append("Python not found")
    if not shutil.which("node"):
        errors.append("Node.js not found")
    if not shutil.which("npm"):
        errors.append("npm not found")
    if not (FRONTEND / "node_modules").exists():
        print(f"{Y}[SETUP] Installing frontend dependencies...{R}")
        subprocess.run(["npm", "install"], cwd=str(FRONTEND), check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not (BACKEND / "requirements.txt").exists():
        errors.append("backend/requirements.txt not found")
    if errors:
        for e in errors:
            print(f"{RED}✗ {e}{R}")
        sys.exit(1)


def copy_demo_env():
    """Copy .env.demo to .env if it exists and .env is missing."""
    env_demo = ROOT / ".env.demo"
    env_target = BACKEND / ".env"
    if env_demo.exists() and not env_target.exists():
        shutil.copy2(str(env_demo), str(env_target))
        print(f"{G}[ENV] Copied .env.demo → backend/.env{R}")


def start_backend():
    """Launch FastAPI backend."""
    print(f"{C}[BACKEND] Starting FastAPI on port 8000...{R}")

    # Prefer venv Python if it exists
    venv_py = BACKEND / ".venv" / ("Scripts" if platform.system() == "Windows" else "bin") / "python"
    if venv_py.exists() or venv_py.with_suffix(".exe").exists():
        py = str(venv_py)
        print(f"{G}[VENV] Using {py}{R}")
    else:
        py = "python" if platform.system() == "Windows" else "python3"
        print(f"{Y}[WARN] No venv found, using system Python{R}")

    env = os.environ.copy()
    env["DEMO_MODE"] = "true"
    p = subprocess.Popen(
        [py, "run.py"],
        cwd=str(BACKEND),
        env=env,
    )
    processes.append(p)
    return p


def start_frontend():
    """Launch Vite dev server."""
    print(f"{C}[FRONTEND] Starting Vite on port 3000...{R}")
    npm = "npm.cmd" if platform.system() == "Windows" else "npm"
    p = subprocess.Popen(
        [npm, "run", "dev"],
        cwd=str(FRONTEND),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    processes.append(p)
    return p


def wait_for_ready():
    """Wait for backend to respond."""
    import urllib.request
    print(f"{Y}[WAIT] Waiting for backend...{R}", end="", flush=True)
    for _ in range(30):
        try:
            urllib.request.urlopen("http://localhost:8000/api/health", timeout=2)
            print(f" {G}Ready!{R}")
            return True
        except Exception:
            print(".", end="", flush=True)
            time.sleep(1)
    print(f"\n{Y}Backend may still be starting — check http://localhost:8000/docs{R}")
    return False


def print_urls():
    print(f"""
{G}{B}╔══════════════════════════════════════════════════════════════╗
║              Krishi-Sarthi Demo Started! 🎉                  ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║   🌐 Frontend:    {C}http://localhost:3000{G}                       ║
║   🔧 Backend API: {C}http://localhost:8000{G}                       ║
║   📚 API Docs:    {C}http://localhost:8000/docs{G}                  ║
║   ❤️  Health:      {C}http://localhost:8000/api/health{G}            ║
║                                                              ║
║   Press Ctrl+C to stop all services                          ║
╚══════════════════════════════════════════════════════════════╝{R}
""")


def main():
    print(BANNER)
    check_prereqs()
    copy_demo_env()

    start_backend()
    time.sleep(2)
    start_frontend()
    wait_for_ready()
    print_urls()

    # Keep running
    try:
        while True:
            for p in processes:
                if p.poll() is not None:
                    print(f"{RED}[ERROR] A process exited unexpectedly.{R}")
                    cleanup()
            time.sleep(2)
    except KeyboardInterrupt:
        cleanup()


if __name__ == "__main__":
    main()
