#!/usr/bin/env bash
# ==============================================================================
# AgentPay Guard - All-in-One Launcher
# Runs Backend (8000), MCP Server (8002), Web Frontend (3000), and ngrok Tunnel
# ==============================================================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# Colors for output
RED='\031[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
MAGENTA='\033[0;35m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${CYAN}====================================================${NC}"
echo -e "${CYAN}        🛡️  Starting AgentPay Guard Stack            ${NC}"
echo -e "${CYAN}====================================================${NC}"

# 1. Activate Python virtual environment if present
if [ -d "$ROOT_DIR/.venv" ]; then
    echo -e "${BLUE}[+] Activating virtual environment (.venv)...${NC}"
    source "$ROOT_DIR/.venv/bin/activate"
elif [ -d "$ROOT_DIR/venv" ]; then
    echo -e "${BLUE}[+] Activating virtual environment (venv)...${NC}"
    source "$ROOT_DIR/venv/bin/activate"
fi

# Track process IDs for graceful shutdown
PIDS=()

cleanup() {
    echo -e "\n${YELLOW}[!] Stopping all services...${NC}"
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
        fi
    done
    echo -e "${GREEN}[✔] All services stopped successfully.${NC}"
    exit 0
}

trap cleanup INT TERM EXIT

# 2. Start Backend FastAPI Server (Port 8000)
echo -e "${GREEN}[1/4] Launching Backend API Server (http://localhost:8000)...${NC}"
(
    export PYTHONPATH="$ROOT_DIR/src/backend:$ROOT_DIR/src"
    cd "$ROOT_DIR/src/backend"
    exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
) 2>&1 | sed "s/^/[BACKEND] /" &
PIDS+=($!)

# 3. Start Standalone MCP Remote Server (Port 8002)
echo -e "${GREEN}[2/4] Launching MCP Remote Server (http://localhost:8002/mcp)...${NC}"
(
    export PYTHONPATH="$ROOT_DIR/src/mcp:$ROOT_DIR/src/backend:$ROOT_DIR/src"
    cd "$ROOT_DIR/src/mcp"
    exec python3 -m uvicorn remote_server:app --host 0.0.0.0 --port 8002 --reload
) 2>&1 | sed "s/^/[MCP]     /" &
PIDS+=($!)

# 4. Start Next.js Web Dashboard (Port 3000)
echo -e "${GREEN}[3/4] Launching Web Frontend Dashboard (http://localhost:3000)...${NC}"
(
    cd "$ROOT_DIR/src/web"
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}[!] node_modules missing in src/web. Running npm install...${NC}"
        npm install
    fi
    exec npm run dev
) 2>&1 | sed "s/^/[WEB]     /" &
PIDS+=($!)

# 5. Start ngrok Tunnel (Port 8000)
if command -v ngrok &> /dev/null; then
    echo -e "${GREEN}[4/4] Launching ngrok tunnel for Backend Webhooks (Port 8000)...${NC}"
    (
        exec ngrok http 8000
    ) 2>&1 | sed "s/^/[NGROK]   /" &
    PIDS+=($!)
else
    echo -e "${YELLOW}[4/4] ngrok not found in PATH. Skipping ngrok tunnel creation.${NC}"
    echo -e "${YELLOW}      (Install ngrok to automatically expose webhook & MCP endpoints publicly).${NC}"
fi

echo -e "\n${MAGENTA}====================================================${NC}"
echo -e "${GREEN}✔ AgentPay Guard services are running!${NC}"
echo -e "${CYAN}  • Backend API & Embedded MCP: ${NC}http://localhost:8000"
echo -e "${CYAN}  • Standalone MCP Server:     ${NC}http://localhost:8002/mcp"
echo -e "${CYAN}  • Web Dashboard:             ${NC}http://localhost:3000"
if command -v ngrok &> /dev/null; then
    echo -e "${CYAN}  • ngrok Tunnel Dashboard:     ${NC}http://localhost:4040"
fi
echo -e "${MAGENTA}Press Ctrl+C to terminate all services.${NC}"
echo -e "${MAGENTA}====================================================${NC}\n"

# Wait indefinitely for background processes
wait
