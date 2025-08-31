# services/breakout/__init__.py
"""
Modular Breakout Detection System

This package provides a comprehensive, modular breakout detection system
for real-time trading applications.
"""

from .data_adapters import (
    TickData,
    BreakoutDataAdapter,
    MarketDataHubAdapter,
    CentralizedWebSocketAdapter,
    InstrumentRegistryAdapter,
    RedisStreamAdapter,
    MultiSourceDataManager
)

from .scanner_service import (
    BreakoutSignal,
    BreakoutScannerService,
    initialize_breakout_system,
    get_breakout_system,
    start_breakout_system,
    stop_breakout_system,
    health_check_breakout_system,
    recover_breakout_system,
    get_breakout_system_statistics
)

__all__ = [
    'TickData',
    'BreakoutDataAdapter',
    'MarketDataHubAdapter', 
    'CentralizedWebSocketAdapter',
    'InstrumentRegistryAdapter',
    'RedisStreamAdapter',
    'MultiSourceDataManager',
    'BreakoutSignal',
    'BreakoutScannerService',
    'initialize_breakout_system',
    'get_breakout_system',
    'start_breakout_system',
    'stop_breakout_system',
    'health_check_breakout_system',
    'recover_breakout_system',
    'get_breakout_system_statistics'
]