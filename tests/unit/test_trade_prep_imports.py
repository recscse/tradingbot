import pytest
from unittest.mock import MagicMock, patch
from decimal import Decimal
from services.trading_execution.trade_prep import TradePrepService, TradeStatus
from services.trading_execution.strategy_engine import TradingSignal, SignalType
from services.trading_execution.capital_manager import CapitalAllocation, TradingMode

@pytest.mark.asyncio
async def test_prepare_trade_with_live_data_imports():
    """Test that prepare_trade_with_live_data can run without NameErrors"""
    service = TradePrepService()
    db = MagicMock()
    
    # Mock premium_signal
    premium_signal = TradingSignal(
        signal_type=SignalType.BUY,
        price=Decimal("100.0"),
        confidence=Decimal("0.8"),
        reason="Test signal",
        indicators={},
        entry_price=Decimal("100.0"),
        stop_loss=Decimal("95.0"),
        target_price=Decimal("110.0"),
        trailing_stop_config={"risk_reward_ratio": 2.0},
        timestamp="2026-02-19T10:00:00"
    )
    
    # Mock db.query(...).join(...).filter(...).count()
    # This is where ActivePosition and AutoTradeExecution are used
    db.query.return_value.join.return_value.filter.return_value.count.return_value = 0
    db.query.return_value.join.return_value.filter.return_value.first.return_value = None
    
    # Mock capital_manager
    with patch("services.trading_execution.trade_prep.capital_manager") as mock_capital_manager:
        mock_capital_manager.get_available_capital_for_new_position.return_value = Decimal("50000.0")
        mock_capital_manager.calculate_position_size.return_value = CapitalAllocation(
            total_capital=Decimal("100000.0"),
            allocated_capital=Decimal("10000.0"),
            position_size_lots=1,
            position_value=Decimal("25000.0"),
            max_loss=Decimal("500.0"),
            margin_required=Decimal("5000.0"),
            capital_utilization_percent=Decimal("20.0"),
            risk_per_trade_percent=Decimal("1.0")
        )
        mock_capital_manager.validate_capital_availability.return_value = {"valid": True}
        
        # We also need to mock log_to_db to avoid DB issues
        with patch("services.trading_execution.trade_prep.log_to_db"):
            result = await service.prepare_trade_with_live_data(
                premium_signal=premium_signal,
                user_id=1,
                stock_symbol="RELIANCE",
                option_instrument_key="NSE_FO|12345",
                option_type="CE",
                strike_price=Decimal("2500.0"),
                expiry_date="2026-02-26",
                lot_size=250,
                current_premium=Decimal("100.0"),
                historical_data={"close": [100.0] * 30},
                db=db,
                trading_mode=TradingMode.PAPER
            )
            
            assert result.status == TradeStatus.READY
            assert result.stock_symbol == "RELIANCE"
            # If we reached here without NameError, the imports are working
