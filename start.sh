#!/bin/bash

set -e

PORT=${PORT:-10000}

echo "Installing Playwright browser for automation..."
export PLAYWRIGHT_BROWSERS_PATH=/tmp/.playwright
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=false
mkdir -p /tmp/.playwright
python -m playwright install chromium || echo "Playwright install failed - continuing anyway"


























echo "Running Alembic database migrations..."
alembic upgrade head

echo "Starting FastAPI server with SocketIO on port $PORT..."
exec uvicorn app:sio_app --host 0.0.0.0 --port $PORT --workers 1