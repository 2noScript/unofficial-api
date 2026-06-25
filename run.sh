#!/usr/bin/env bash
set -e

if [ ! -f .env ]; then
    echo "Error: .env file not found. Copy .env.example to .env and fill in credentials."
    exit 1
fi

uv run uvicorn core.server:app --host 0.0.0.0 --port 8000 --reload
