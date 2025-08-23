# Test markers for pytest
import pytest

# Register custom markers
pytest_plugins = []

def pytest_configure(config):
    """Configure custom markers"""
    config.addinivalue_line("markers", "unit: Unit tests for individual components")
    config.addinivalue_line("markers", "integration: Integration tests across components") 
    config.addinivalue_line("markers", "performance: Performance and load tests")
    config.addinivalue_line("markers", "api: API endpoint tests")
    config.addinivalue_line("markers", "e2e: End-to-end workflow tests")
    config.addinivalue_line("markers", "accuracy: Trading accuracy validation tests")
    config.addinivalue_line("markers", "slow: Slow running tests (>5 seconds)")
    config.addinivalue_line("markers", "fast: Fast tests (<1 second)")
    config.addinivalue_line("markers", "breakout: Breakout engine related tests")
    config.addinivalue_line("markers", "websocket: WebSocket functionality tests")
    config.addinivalue_line("markers", "database: Database operations tests")
    config.addinivalue_line("markers", "broker: Broker integration tests")
