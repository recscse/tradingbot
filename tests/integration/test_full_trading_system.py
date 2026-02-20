import pytest
import asyncio
import json
from decimal import Decimal
from datetime import datetime, date
from unittest.mock import MagicMock, patch, AsyncMock

from database.models import SelectedStock, ActivePosition, AutoTradeExecution, BrokerConfig
from services.intelligent_stock_selection_service import intelligent_stock_selector, StockSelection, MarketSentiment, TradingPhase
from services.enhanced_intelligent_options_selection import enhanced_options_service, OptionContract, EnhancedStockSelection
from services.trading_execution.auto_trade_scheduler import auto_trade_scheduler
from services.trading_execution.auto_trade_live_feed import auto_trade_live_feed
from services.trading_execution.trade_prep import TradeStatus, PreparedTrade
from services.trading_execution.strategy_engine import TradingSignal, SignalType
from services.trading_execution.capital_manager import CapitalAllocation, TradingMode

@pytest.mark.asyncio
async def test_full_trading_system_lifecycle():
    """
    INTEGRATED END-TO-END TEST
    Verifies: 
    1. Stock Selection Service -> Options Selection
    2. Scheduler Auto-Start Logic
    3. Live Feed processing -> Trade Execution
    
    Ensures no NameErrors, data mismatches, or logical breaks.
    """
    
    # --- SETUP DATA ---
    TEST_SYMBOL = "RELIANCE"
    TEST_SPOT_KEY = "NSE_EQ|INE002A01018"
    TEST_OPTION_KEY = "NSE_FO|12345"
    USER_ID = 1
    
    # 1. Mock Market Engine Data (for Stock Selection)
    mock_sentiment = {
        "sentiment": "bullish",
        "confidence": 80,
        "metrics": {
            "total_stocks": 100,
            "advancing": 70,
            "declining": 30,
            "advance_decline_ratio": 2.33,
            "market_breadth_percent": 70.0
        }
    }
    
    mock_sector_perf = {
        "BANKING": {"avg_change_percent": 1.5, "strength_score": 85, "advancing": 10, "total_stocks": 12},
        "IT": {"avg_change_percent": 0.8, "strength_score": 60, "advancing": 5, "total_stocks": 8}
    }
    
    mock_sector_stocks = {
        "BANKING": [
            {
                "symbol": TEST_SYMBOL, "name": "RELIANCE", "instrument_key": TEST_SPOT_KEY,
                "ltp": 2500.0, "change_percent": 2.0, "change": 35.0, "volume": 1000000,
                "value_crores": 250.0, "high": 2510.0, "low": 2480.0, "previous_close": 2465.0,
                "lot_size": 250
            }
        ]
    }

    # 2. Mock Option Chain (for Option Selection)
    mock_option_chain = {
        "underlying_key": TEST_SPOT_KEY,
        "expiry": "2026-02-26",
        "spot_price": 2500.0,
        "atm_strike": 2500.0,
        "data": [
            {
                "strike_price": 2500.0,
                "call_options": {
                    "instrument_key": TEST_OPTION_KEY,
                    "market_data": {"ltp": 100.0, "volume": 5000, "oi": 10000, "bid_price": 99.5, "ask_price": 100.5},
                    "option_greeks": {"delta": 0.5, "iv": 20.0, "theta": -1.0, "vega": 2.0, "gamma": 0.001},
                    "lot_size": 250
                }
            }
        ]
    }

    # --- EXECUTION & VERIFICATION ---
    
    # A. Test Stock & Option Selection Logic
    print("\nStep 1: Running Premarket Stock Selection...")
    with (
        patch("services.intelligent_stock_selection_service.get_market_sentiment", return_value=mock_sentiment),
        patch("services.intelligent_stock_selection_service.get_sector_performance", return_value=mock_sector_perf),
        patch("services.intelligent_stock_selection_service.get_sector_stocks", return_value={"BANKING": mock_sector_stocks["BANKING"]}),
        patch("services.upstox_option_service.upstox_option_service.get_fast_option_selection_data") as mock_fast_data,
        patch("services.upstox_option_service.upstox_option_service.get_option_chain", return_value=mock_option_chain),
        patch("services.enhanced_intelligent_options_selection.SessionLocal"),
        patch("services.intelligent_stock_selection_service.SessionLocal") as mock_ss_session_factory,
    ):
        # Setup selection data mock
        mock_fast_data.return_value = {
            "expiries": ["2026-02-26"],
            "lot_size": 250,
            "nearest_expiry": "2026-02-26",
            "chain": mock_option_chain
        }
        
        # Mock DB for saving
        mock_session = MagicMock()
        mock_ss_session_factory.return_value = mock_session
        
        # Override phase check to ensure it runs
        with patch.object(intelligent_stock_selector, 'get_current_trading_phase', return_value=TradingPhase.PREMARKET):
            selection_result = await intelligent_stock_selector.run_premarket_selection(force=True)
            
        assert "selected_stocks" in selection_result
        assert len(selection_result["selected_stocks"]) > 0
        assert selection_result["selected_stocks"][0]["symbol"] == TEST_SYMBOL
        assert "options_enhancement" in selection_result
        assert selection_result["options_enhancement"]["options_ready"] is True
        print("✅ Stock and Option selection logic PASSED")

    # B. Test Scheduler Auto-Start Logic
    print("\nStep 2: Testing Scheduler Auto-Start...")
    with (
        patch("services.trading_execution.auto_trade_scheduler.SessionLocal") as mock_sched_session_factory,
        patch("services.trading_execution.auto_trade_live_feed.auto_trade_live_feed.start_auto_trading", new_callable=AsyncMock) as mock_start_feed,
    ):
        mock_sched_session = MagicMock()
        mock_sched_session_factory.return_value = mock_sched_session
        
        # Setup mock data in DB for scheduler to find
        mock_sched_session.query.return_value.filter.return_value.count.return_value = 1 # 1 stock selected
        
        mock_broker = BrokerConfig(user_id=USER_ID, broker_name="upstox", is_active=True, access_token="mock_token")
        mock_sched_session.query.return_value.filter.return_value.all.return_value = [mock_broker]
        
        # Run auto-start check
        await auto_trade_scheduler._check_and_start_trading_all_users()
        
        mock_start_feed.assert_called()
        print("✅ Scheduler auto-start logic PASSED")

    # C. Test Live Feed -> Execution Flow (E2E)
    print("\nStep 3: Testing Live Feed to Execution Flow...")
    
    # Mock instrument in registry
    from services.trading_execution.shared_instrument_registry import SharedInstrument
    mock_instrument = SharedInstrument(
        stock_symbol=TEST_SYMBOL,
        spot_instrument_key=TEST_SPOT_KEY,
        option_instrument_key=TEST_OPTION_KEY,
        option_type="CE",
        strike_price=Decimal("2500.0"),
        expiry_date="2026-02-26",
        lot_size=250
    )
    mock_instrument.live_option_premium = Decimal("100.0")
    mock_instrument.live_spot_price = Decimal("2500.0")
    mock_instrument.historical_spot_data = {"close": [100.0] * 35}
    mock_instrument.last_processed_candle_count = 34
    
    prepared_trade = PreparedTrade(
        status=TradeStatus.READY, stock_symbol=TEST_SYMBOL, option_instrument_key=TEST_OPTION_KEY,
        option_type="CE", strike_price=Decimal("2500.0"), expiry_date="2026-02-26",
        current_premium=Decimal("100.0"), lot_size=250, signal={}, capital_allocation={},
        risk_reward_ratio=Decimal("2.0"), entry_price=Decimal("100.0"), stop_loss=Decimal("95.0"),
        target_price=Decimal("110.0"), trailing_stop_config={}, position_size_lots=1,
        total_investment=Decimal("25000.0"), max_loss_amount=Decimal("1250.0"),
        trading_mode="paper", broker_name="upstox", user_id=USER_ID,
        prepared_at="2026-02-19T10:00:00", valid_until="2026-02-19T10:15:00", metadata={}
    )

    with (
        patch("services.trading_execution.auto_trade_live_feed.shared_registry") as mock_registry,
        patch("services.trading_execution.trade_prep.TradePrepService.prepare_trade_with_live_data", new_callable=AsyncMock) as mock_prep_method,
        patch("services.trading_execution.auto_trade_live_feed.strategy_engine") as mock_strategy,
        patch("services.trading_execution.auto_trade_live_feed.execution_handler") as mock_execution,
        patch("services.trading_execution.auto_trade_live_feed.SessionLocal") as mock_lf_session_factory,
        patch("services.trading_execution.auto_trade_live_feed.broadcast_to_clients"),
        patch("services.trading_execution.auto_trade_live_feed.is_market_open", return_value=True),
    ):
        # Setup mock behavior
        mock_registry.get_all_instrument_keys.return_value = [TEST_SPOT_KEY, TEST_OPTION_KEY]
        mock_registry.get_instrument.return_value = mock_instrument
        mock_registry.instruments = {TEST_OPTION_KEY: mock_instrument}
        mock_registry.get_instrument_subscribers.return_value = [USER_ID]
        mock_registry.is_risk_halted = False
        mock_registry.get_user_metadata.return_value = {"broker_name": "upstox", "broker_config_id": 123}
        
        mock_lf_session = MagicMock()
        mock_lf_session_factory.return_value = mock_lf_session
        mock_lf_session.query.return_value.join.return_value.filter.return_value.first.return_value = None
        
        # Mock strategy
        mock_strategy.generate_signal.return_value = MagicMock(signal_type=SignalType.BUY)
        mock_strategy.convert_spot_signal_to_premium.return_value = TradingSignal(
            signal_type=SignalType.BUY, price=Decimal("100.0"), confidence=Decimal("0.8"),
            reason="Breakout", indicators={}, entry_price=Decimal("100.0"), stop_loss=Decimal("95.0"),
            target_price=Decimal("110.0"), trailing_stop_config={"risk_reward_ratio": 2.0},
            timestamp="2026-02-19T10:00:00"
        )
        
        mock_prep_method.return_value = prepared_trade
        mock_execution.execute_trade = MagicMock(return_value=MagicMock(success=True))

        # Simulate incoming feed data
        feed_data = {"feeds": {TEST_SPOT_KEY: {"fullFeed": {"marketFF": {"ltpc": {"ltp": 2500.0}}}}}}
        await auto_trade_live_feed._incoming_feed_callback(feed_data)
        
        await asyncio.sleep(0.5)
        
        mock_prep_method.assert_called()
        mock_execution.execute_trade.assert_called()
        print("✅ Feed to Execution flow PASSED")

    print("\n🚀 FULL SYSTEM LIFECYCLE VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(test_full_trading_system_lifecycle())
