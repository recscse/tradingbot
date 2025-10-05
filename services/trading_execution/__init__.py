"""
Trading Execution Package
Modular trading system with capital management, strategy engine, and execution
"""

from services.trading_execution.capital_manager import (
    capital_manager,
    TradingMode,
    CapitalAllocation,
    TradingCapitalManager
)

from services.trading_execution.strategy_engine import (
    strategy_engine,
    TradingSignal,
    SignalType,
    TrailingStopType,
    StrategyEngine
)

from services.trading_execution.trade_prep import (
    trade_prep_service,
    PreparedTrade,
    TradeStatus,
    TradePrepService
)

from services.trading_execution.execution_handler import (
    execution_handler,
    ExecutionResult,
    TradeExecutionHandler
)

from services.trading_execution.pnl_tracker import (
    pnl_tracker,
    PositionPnL,
    RealTimePnLTracker
)

__all__ = [
    'capital_manager',
    'TradingMode',
    'CapitalAllocation',
    'TradingCapitalManager',
    'strategy_engine',
    'TradingSignal',
    'SignalType',
    'TrailingStopType',
    'StrategyEngine',
    'trade_prep_service',
    'PreparedTrade',
    'TradeStatus',
    'TradePrepService',
    'execution_handler',
    'ExecutionResult',
    'TradeExecutionHandler',
    'pnl_tracker',
    'PositionPnL',
    'RealTimePnLTracker',
]
