#!/bin/bash

set -e

PORT=${PORT:-10000}

# Set Playwright environment variables for Render
export PLAYWRIGHT_BROWSERS_PATH=/tmp/.playwright
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=false

echo "Installing Playwright browser with dependencies..."
playwright install --with-deps chromium

echo "Verifying Playwright installation..."
python -c "
import asyncio
from playwright.async_api import async_playwright

async def test():
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
            await browser.close()
            print('✅ Playwright verification successful')
    except Exception as e:
        print(f'❌ Playwright verification failed: {e}')
        exit(1)

asyncio.run(test())
"

echo "Running Alembic database migrations..."
alembic upgrade head

echo "Starting FastAPI server with SocketIO on port $PORT..."
exec uvicorn app:sio_app --host 0.0.0.0 --port $PORT --workers 1
