#!/bin/bash
# Krishi-Sarthi Demo Launcher

GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${GREEN}========================================"
echo "  Krishi-Sarthi Demo Launcher"
echo -e "========================================${NC}"
echo ""

cleanup() {
    echo ""
    echo "Shutting down..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

# Start backend
echo "[1/2] Starting Backend (port 8000)..."
cd "$(dirname "$0")/backend"
DEMO_MODE=true python3 run.py &
BACKEND_PID=$!

sleep 3

# Start frontend
echo "[2/2] Starting Frontend (port 3000)..."
cd "$(dirname "$0")/frontend"
[ ! -d node_modules ] && npm install
npm run dev &
FRONTEND_PID=$!

sleep 3

echo ""
echo -e "${GREEN}========================================"
echo "  Demo Ready!"
echo ""
echo -e "  Frontend:  ${CYAN}http://localhost:3000${GREEN}"
echo -e "  Backend:   ${CYAN}http://localhost:8000${GREEN}"
echo -e "  API Docs:  ${CYAN}http://localhost:8000/docs${GREEN}"
echo -e "========================================${NC}"
echo ""
echo "Press Ctrl+C to stop..."

wait
