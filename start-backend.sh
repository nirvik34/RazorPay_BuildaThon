#!/usr/bin/env bash
cd "$(dirname "$0")/src/backend"
exec uvicorn app.main:app --reload
