#!/usr/bin/env bash
# ==============================================================================
# AgentPay Guard - State Reset Utility
# ==============================================================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "[+] Resetting AgentPay Guard state..."

# 1. Reset running backend server if active
if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    curl -s -X POST http://127.0.0.1:8000/auth/reset-dev > /dev/null
    echo "[✔] Sent reset signal to active backend on http://127.0.0.1:8000"
fi

# 2. Reset persistent state files on disk
rm -f "$ROOT_DIR/src/backend/data/state.json"
rm -f "$ROOT_DIR/data/state.json"

echo "[✔] Cleared state files on disk."
echo "[✔] AgentPay Guard is ready for fresh registration!"
