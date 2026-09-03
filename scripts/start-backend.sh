#!/usr/bin/env bash
# ==============================================================================
# AgentPay Guard - Backend Launcher
# ==============================================================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/src/backend"

exec uvicorn app.main:app --reload
