import pytest
import asyncio
import os
from typing import Generator
from fastapi.testclient import TestClient

# Test environment setup
os.environ.update({
    "DATABASE_URL": "sqlite:///./test.db",
    "JWT_SECRET_KEY": "test-secret-key-for-testing",
    "REDIS_ENABLED": "false", 
    "TESTING": "true",
    "CI": "true"
})

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def market_hub():
    """Provide Market Data Hub for tests"""
    try:
        from services.market_data_hub import start_market_hub, market_data_hub
        await start_market_hub()
        yield market_data_hub
        await market_data_hub.stop()
    except ImportError:
        pytest.skip("Market Data Hub not available")

@pytest.fixture
async def enhanced_breakout_engine():
    """Provide Enhanced Breakout Engine for tests"""
    try:
        from services.enhanced_breakout_engine import enhanced_breakout_engine
        yield enhanced_breakout_engine
    except ImportError:
        pytest.skip("Enhanced Breakout Engine not available")

@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    try:
        from app import sio_app
        with TestClient(sio_app) as test_client:
            yield test_client
    except ImportError:
        pytest.skip("App import failed - skipping test")

@pytest.fixture
def sample_market_data():
    """Provide sample market data for testing"""
    return {
        'NSE_EQ|26000': {
            'ltp': 2500.0,
            'chp': 1.5,
            'change': 37.50,
            'volume': 150000,
            'symbol': 'RELIANCE'
        },
        'NSE_EQ|11536': {
            'ltp': 3800.0,
            'chp': 0.8,
            'change': 30.0,
            'volume': 120000,
            'symbol': 'TCS'
        }
    }

@pytest.fixture
def mock_websocket_data():
    """Provide mock WebSocket data for testing"""
    return {
        "type": "price_update",
        "data": {
            "prices": {
                'NSE_EQ|26000': {
                    'ltp': 2500.0,
                    'change': 37.50,
                    'volume': 150000
                }
            },
            "timestamp": "2024-01-01T10:00:00Z"
        }
    }
