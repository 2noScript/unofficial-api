#!/usr/bin/env bash
uv run uvicorn core.server:app --host 0.0.0.0 --port 8088 --reload
