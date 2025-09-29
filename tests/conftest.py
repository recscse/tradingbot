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
    """Market Data Hub removed - using shared_market_processor"""
    pytest.skip("Market Data Hub removed - tests should use shared_market_processor")

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


# ==========================================
# Intelligent Stock Selection Service Fixtures
# ==========================================

from unittest.mock import Mock, AsyncMock
from typing import Dict, List, Any
from decimal import Decimal
from datetime import datetime

# Import the service under test
from services.intelligent_stock_selection_service import (
    IntelligentStockSelectionService,
    MarketSentiment,
    TradingPhase,
    StockSelection
)


@pytest.fixture
def comprehensive_market_data():
    """Comprehensive mock market data for intelligent stock selection testing"""
    return {
        "NSE_EQ|INE002A01018": {  # RELIANCE
            "symbol": "RELIANCE",
            "name": "RELIANCE INDUSTRIES LTD",
            "instrument_key": "NSE_EQ|INE002A01018",
            "sector": "ENERGY",
            "is_fno": True,
            "lot_size": 250,
            "ltp": 2847.50,
            "change": 45.30,
            "change_percent": 1.62,
            "volume": 2847520,
            "value_crores": 81.2,
            "high": 2855.00,
            "low": 2820.00,
            "previous_close": 2802.20,
            "bid_price": 2847.00,
            "ask_price": 2848.00,
            "atp": 2845.75
        },
        "NSE_EQ|INE467B01029": {  # TCS
            "symbol": "TCS",
            "name": "TATA CONSULTANCY SERVICES LTD",
            "instrument_key": "NSE_EQ|INE467B01029",
            "sector": "INFORMATION_TECHNOLOGY",
            "is_fno": True,
            "lot_size": 100,
            "ltp": 4125.80,
            "change": 78.50,
            "change_percent": 1.94,
            "volume": 1456780,
            "value_crores": 60.1,
            "high": 4135.00,
            "low": 4098.00,
            "previous_close": 4047.30,
            "bid_price": 4125.00,
            "ask_price": 4126.50,
            "atp": 4122.40
        },
        "NSE_EQ|INE040A01034": {  # HDFC Bank
            "symbol": "HDFCBANK",
            "name": "HDFC BANK LIMITED",
            "instrument_key": "NSE_EQ|INE040A01034",
            "sector": "BANKING_FINANCIAL_SERVICES",
            "is_fno": True,
            "lot_size": 550,
            "ltp": 1747.25,
            "change": -12.75,
            "change_percent": -0.72,
            "volume": 3254780,
            "value_crores": 56.8,
            "high": 1765.00,
            "low": 1742.00,
            "previous_close": 1760.00,
            "bid_price": 1746.80,
            "ask_price": 1747.70,
            "atp": 1748.90
        },
        "NSE_EQ|INE009A01021": {  # INFY
            "symbol": "INFY",
            "name": "INFOSYS LIMITED",
            "instrument_key": "NSE_EQ|INE009A01021",
            "sector": "INFORMATION_TECHNOLOGY",
            "is_fno": True,
            "lot_size": 300,
            "ltp": 1823.40,
            "change": 25.60,
            "change_percent": 1.42,
            "volume": 2147850,
            "value_crores": 39.2,
            "high": 1830.00,
            "low": 1810.00,
            "previous_close": 1797.80,
            "bid_price": 1823.00,
            "ask_price": 1823.80,
            "atp": 1821.65
        },
        "NSE_EQ|INE854D01024": {  # MARUTI
            "symbol": "MARUTI",
            "name": "MARUTI SUZUKI INDIA LIMITED",
            "instrument_key": "NSE_EQ|INE854D01024",
            "sector": "AUTOMOTIVE",
            "is_fno": True,
            "lot_size": 100,
            "ltp": 11456.75,
            "change": 156.25,
            "change_percent": 1.38,
            "volume": 487620,
            "value_crores": 55.8,
            "high": 11485.00,
            "low": 11320.00,
            "previous_close": 11300.50,
            "bid_price": 11455.00,
            "ask_price": 11458.50,
            "atp": 11442.30
        }
    }


@pytest.fixture
def mock_sector_performance_data():
    """Mock sector performance data for testing"""
    return {
        "INFORMATION_TECHNOLOGY": {
            "avg_change_percent": 1.5,
            "strength_score": 75,
            "advancing": 3,
            "total_stocks": 4
        },
        "ENERGY": {
            "avg_change_percent": 1.2,
            "strength_score": 68,
            "advancing": 1,
            "total_stocks": 1
        },
        "BANKING_FINANCIAL_SERVICES": {
            "avg_change_percent": -0.3,
            "strength_score": 45,
            "advancing": 0,
            "total_stocks": 1
        },
        "AUTOMOTIVE": {
            "avg_change_percent": 1.1,
            "strength_score": 60,
            "advancing": 1,
            "total_stocks": 1
        },
        "PHARMACEUTICAL": {
            "avg_change_percent": 0.8,
            "strength_score": 55,
            "advancing": 2,
            "total_stocks": 3
        },
        "FMCG": {
            "avg_change_percent": 0.5,
            "strength_score": 50,
            "advancing": 1,
            "total_stocks": 2
        }
    }


@pytest.fixture
def mock_sector_stocks_data():
    """Mock sector stocks mapping for testing"""
    def _get_sector_stocks(sector: str) -> Dict[str, List[Dict]]:
        sector_stock_data = {
            "INFORMATION_TECHNOLOGY": [
                {
                    "symbol": "TCS",
                    "name": "TATA CONSULTANCY SERVICES LTD",
                    "instrument_key": "NSE_EQ|INE467B01029",
                    "sector": "INFORMATION_TECHNOLOGY",
                    "is_fno": True,
                    "lot_size": 100,
                    "ltp": 4125.80,
                    "change": 78.50,
                    "change_percent": 1.94,
                    "volume": 1456780,
                    "value_crores": 60.1
                },
                {
                    "symbol": "INFY",
                    "name": "INFOSYS LIMITED",
                    "instrument_key": "NSE_EQ|INE009A01021",
                    "sector": "INFORMATION_TECHNOLOGY",
                    "is_fno": True,
                    "lot_size": 300,
                    "ltp": 1823.40,
                    "change": 25.60,
                    "change_percent": 1.42,
                    "volume": 2147850,
                    "value_crores": 39.2
                }
            ],
            "ENERGY": [
                {
                    "symbol": "RELIANCE",
                    "name": "RELIANCE INDUSTRIES LTD",
                    "instrument_key": "NSE_EQ|INE002A01018",
                    "sector": "ENERGY",
                    "is_fno": True,
                    "lot_size": 250,
                    "ltp": 2847.50,
                    "change": 45.30,
                    "change_percent": 1.62,
                    "volume": 2847520,
                    "value_crores": 81.2
                }
            ],
            "BANKING_FINANCIAL_SERVICES": [
                {
                    "symbol": "HDFCBANK",
                    "name": "HDFC BANK LIMITED",
                    "instrument_key": "NSE_EQ|INE040A01034",
                    "sector": "BANKING_FINANCIAL_SERVICES",
                    "is_fno": True,
                    "lot_size": 550,
                    "ltp": 1747.25,
                    "change": -12.75,
                    "change_percent": -0.72,
                    "volume": 3254780,
                    "value_crores": 56.8
                }
            ],
            "AUTOMOTIVE": [
                {
                    "symbol": "MARUTI",
                    "name": "MARUTI SUZUKI INDIA LIMITED",
                    "instrument_key": "NSE_EQ|INE854D01024",
                    "sector": "AUTOMOTIVE",
                    "is_fno": True,
                    "lot_size": 100,
                    "ltp": 11456.75,
                    "change": 156.25,
                    "change_percent": 1.38,
                    "volume": 487620,
                    "value_crores": 55.8
                }
            ],
            "PHARMACEUTICAL": [],
            "FMCG": []
        }
        return {sector: sector_stock_data.get(sector, [])}

    return _get_sector_stocks


@pytest.fixture
async def intelligent_stock_service_with_mocks(
    comprehensive_market_data,
    mock_sector_performance_data,
    mock_sector_stocks_data
):
    """Fully mocked intelligent stock selection service for testing"""
    service = IntelligentStockSelectionService()

    # Mock optimized service
    service.optimized_service = Mock()
    service.optimized_service.get_all_live_data = AsyncMock(return_value=comprehensive_market_data)
    service.optimized_service.get_sector_stocks = Mock(side_effect=mock_sector_stocks_data)
    service.optimized_service.get_sector_performance = Mock(return_value=mock_sector_performance_data)
    service.optimized_service.get_advance_decline_analysis = Mock(return_value={
        "advance_decline_ratio": 1.2,
        "market_breadth_percent": 15.5,
        "high_low_ratio": 1.8
    })
    service.optimized_service.get_market_breadth = Mock(return_value={
        "volume_weighted_breadth": {"volume_weighted_ratio": 1.1}
    })
    service.optimized_service.get_indices_data = Mock(return_value=[
        {"symbol": "NIFTY", "change_percent": 0.8},
        {"symbol": "BANKNIFTY", "change_percent": 0.5}
    ])

    # Mock analytics service
    service.analytics_service = Mock()
    service.analytics_service.get_current_analytics = AsyncMock(return_value={
        "market_sentiment": "bullish",
        "sentiment_score": 0.72
    })

    # Initialize services
    await service.initialize_services()

    return service


@pytest.fixture
def clean_intelligent_stock_service():
    """Clean service instance without mocks for integration tests"""
    return IntelligentStockSelectionService()


@pytest.fixture(params=[
    MarketSentiment.VERY_BULLISH,
    MarketSentiment.BULLISH,
    MarketSentiment.NEUTRAL,
    MarketSentiment.BEARISH,
    MarketSentiment.VERY_BEARISH
])
def all_market_sentiments(request):
    """Parametrized market sentiment for testing all scenarios"""
    return request.param


@pytest.fixture(params=[
    TradingPhase.PREMARKET,
    TradingPhase.MARKET_OPEN,
    TradingPhase.LIVE_TRADING,
    TradingPhase.POST_MARKET
])
def all_trading_phases(request):
    """Parametrized trading phase for testing all scenarios"""
    return request.param


@pytest.fixture
def sample_stock_for_scoring():
    """Sample stock data for unit testing scoring algorithms"""
    return {
        "symbol": "RELIANCE",
        "name": "RELIANCE INDUSTRIES LTD",
        "instrument_key": "NSE_EQ|INE002A01018",
        "sector": "ENERGY",
        "is_fno": True,
        "lot_size": 250,
        "ltp": 2847.50,
        "change": 45.30,
        "change_percent": 1.62,
        "volume": 2847520,
        "value_crores": 81.2,
        "high": 2855.00,
        "low": 2820.00,
        "previous_close": 2802.20,
        "bid_price": 2847.00,
        "ask_price": 2848.00,
        "atp": 2845.75
    }


@pytest.fixture
def performance_benchmarks():
    """Performance thresholds for benchmarking"""
    return {
        "sentiment_analysis_ms": 100,
        "sector_analysis_ms": 50,
        "stock_selection_ms": 200,
        "scoring_algorithm_ms": 10,
        "complete_workflow_ms": 1000
    }


# Test markers for categorizing tests
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.e2e = pytest.mark.e2e
pytest.mark.performance = pytest.mark.performance
pytest.mark.slow = pytest.mark.slow
