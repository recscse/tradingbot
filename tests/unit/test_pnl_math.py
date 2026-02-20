import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, time
from services.trading_execution.pnl_tracker import pnl_tracker, PositionPnL

class MockModel:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

@pytest.mark.asyncio
async def test_pnl_exit_stop_loss():
    """Verify system triggers exit when price falls below SL"""
    mock_position = MockModel(
        id=1,
        trade_execution_id=101,
        user_id=1,
        current_stop_loss=95.0,
        instrument_key="MOCK_KEY",
        symbol="RELIANCE",
        highest_price_reached=100.0,
        trailing_stop_triggered=False,
        is_active=True
    )
    
    mock_trade = MockModel(
        id=101,
        trade_id="T1",
        entry_price=100.0,
        quantity=10,
        target_1=110.0,
        total_investment=1000.0,
        entry_time=datetime(2026, 2, 19, 10, 0, 0),
        strike_price=2500.0
    )
    
    mock_engine = MagicMock()
    mock_instr_data = MagicMock()
    mock_instr_data.current_price = 94.0
    mock_engine.instruments = {"MOCK_KEY": mock_instr_data}
    
    with (
        patch("services.realtime_market_engine.get_market_engine", return_value=mock_engine),
        patch("services.trading_execution.pnl_tracker.SessionLocal") as mock_session_factory,
        patch("services.trading_execution.pnl_tracker.strategy_engine") as mock_strat,
        patch("services.trading_execution.pnl_tracker.get_ist_now_naive", return_value=datetime(2026, 2, 19, 10, 10, 0))
    ):
        mock_session = MagicMock()
        mock_session_factory.return_value = mock_session
        
        # Setup session query behavior
        # First query: filter(ActivePosition.is_active == True).all()
        # Second query: filter(AutoTradeExecution.id == pos.trade_execution_id).first()
        
        mock_query_pos = MagicMock()
        mock_query_pos.filter.return_value.all.return_value = [mock_position]
        
        mock_query_trade = MagicMock()
        mock_query_trade.filter.return_value.first.return_value = mock_trade
        
        # Control what session.query(X) returns
        def side_effect(model):
            from database.models import ActivePosition, AutoTradeExecution
            if model == ActivePosition: return mock_query_pos
            if model == AutoTradeExecution: return mock_query_trade
            return MagicMock()
            
        mock_session.query.side_effect = side_effect
        
        mock_strat.update_trailing_stop.return_value = Decimal("95.0")
        
        with patch.object(pnl_tracker, "_close_position", new_callable=AsyncMock) as mock_close:
            await pnl_tracker.update_all_positions(mock_session)
            mock_close.assert_called()
            assert mock_close.call_args[0][3] == "STOP_LOSS_HIT"

@pytest.mark.asyncio
async def test_pnl_time_exit():
    """Verify system triggers exit at 3:20 PM regardless of price"""
    mock_position = MockModel(
        id=1,
        trade_execution_id=101,
        user_id=1,
        current_stop_loss=90.0,
        instrument_key="MOCK_KEY",
        symbol="RELIANCE",
        highest_price_reached=100.0,
        trailing_stop_triggered=False,
        is_active=True
    )
    
    mock_trade = MockModel(
        id=101,
        trade_id="T1",
        entry_price=100.0,
        quantity=10,
        target_1=120.0,
        total_investment=1000.0,
        entry_time=datetime(2026, 2, 19, 10, 0, 0),
        strike_price=2500.0
    )
    
    mock_engine = MagicMock()
    mock_instr_data = MagicMock()
    mock_instr_data.current_price = 105.0
    mock_engine.instruments = {"MOCK_KEY": mock_instr_data}
    
    mock_time = datetime(2026, 2, 19, 15, 21, 0)
    
    with (
        patch("services.realtime_market_engine.get_market_engine", return_value=mock_engine),
        patch("services.trading_execution.pnl_tracker.SessionLocal") as mock_session_factory,
        patch("services.trading_execution.pnl_tracker.get_ist_now_naive", return_value=mock_time)
    ):
        mock_session = MagicMock()
        mock_session_factory.return_value = mock_session
        
        mock_query_pos = MagicMock()
        mock_query_pos.filter.return_value.all.return_value = [mock_position]
        mock_query_trade = MagicMock()
        mock_query_trade.filter.return_value.first.return_value = mock_trade
        
        def side_effect(model):
            from database.models import ActivePosition, AutoTradeExecution
            if model == ActivePosition: return mock_query_pos
            if model == AutoTradeExecution: return mock_query_trade
            return MagicMock()
            
        mock_session.query.side_effect = side_effect
        
        with patch.object(pnl_tracker, "_close_position", new_callable=AsyncMock) as mock_close:
            await pnl_tracker.update_all_positions(mock_session)
            mock_close.assert_called()
            assert mock_close.call_args[0][3] == "TIME_BASED_EXIT"
