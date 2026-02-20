import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from decimal import Decimal
from services.trading_execution.trade_prep import TradePrepService, TradeStatus
from services.trading_execution.strategy_engine import TradingSignal, SignalType

@pytest.mark.asyncio
async def test_global_kill_switch():
    """Verify that no new trades are allowed if is_risk_halted is True"""
    service = TradePrepService()
    db = MagicMock()
    
    # Mock signal
    signal = TradingSignal(
        signal_type=SignalType.BUY, price=Decimal("100"), confidence=Decimal("0.8"),
        reason="Test", indicators={}, entry_price=Decimal("100"), stop_loss=Decimal("95"),
        target_price=Decimal("110"), trailing_stop_config={}, timestamp="now"
    )
    
    # CASE 1: Kill-switch ACTIVE
    from services.trading_execution.auto_trade_live_feed import AutoTradeLiveFeed
    feed = AutoTradeLiveFeed()
    
    instrument = MagicMock()
    instrument.stock_symbol = "TEST"
    
    with (
        patch.object(feed, "user_last_attempt_times", {}),
        patch("services.trading_execution.auto_trade_live_feed.shared_registry") as mock_registry,
        patch("services.trading_execution.auto_trade_live_feed.trade_prep_service") as mock_prep
    ):
        mock_registry.is_risk_halted = True
        mock_registry.halt_reason = "TEST_HALT"
        
        # This should return immediately and not call trade_prep
        await feed._execute_trade_for_user(instrument, signal, 1)
        mock_prep.prepare_trade_with_live_data.assert_not_called()
        print("✅ Kill-Switch blocked entry as expected")

def test_daily_loss_detection():
    """Verify pnl_tracker detects daily loss and sets halt flag"""
    from services.trading_execution.pnl_tracker import pnl_tracker, PositionPnL
    from services.trading_execution.shared_instrument_registry import shared_registry
    
    shared_registry.is_risk_halted = False
    
    # Simulate a heavy loss update
    bad_update = PositionPnL(
        position_id=1, trade_id="T1", user_id=1, symbol="RELIANCE", instrument_key="K1",
        entry_price=Decimal("100"), current_price=Decimal("40"), # 60% loss
        quantity=100, pnl=Decimal("-6000"), # 6000 loss, threshold is 5000
        pnl_percent=Decimal("-60"), pnl_points=Decimal("-60"),
        entry_time="now", holding_duration_minutes=10, stop_loss=Decimal("95"),
        target=Decimal("110"), highest_price=Decimal("100"), trailing_sl_active=False,
        status="ACTIVE", last_updated="now"
    )
    
    pnl_tracker._check_risk_breaches([bad_update], MagicMock())
    
    assert shared_registry.is_risk_halted is True
    assert shared_registry.halt_reason == "MAX_DAILY_LOSS_BREACHED"
    print("✅ Daily loss detection triggered Kill-Switch")
