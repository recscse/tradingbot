# """
# Startup Integration for Real-Time Trading System

# This module handles the initialization and integration of the enhanced real-time
# trading system components during application startup.

# Features:
# - Integrates Strategy Data Service with Instrument Registry
# - Connects Enhanced Analytics to real-time callbacks
# - Sets up UI broadcast callbacks for WebSocket updates
# - Initializes Strategy Engine with example strategies
# - Provides health checks and monitoring

# Usage in app.py:
#     from services.startup_integration import initialize_realtime_trading_system

#     # During startup (in lifespan function)
#     await initialize_realtime_trading_system()
# """

# import asyncio
# import logging
# from datetime import datetime
# from typing import Dict, Any, Optional

# logger = logging.getLogger(__name__)

# async def initialize_realtime_trading_system() -> bool:
#     """
#     Initialize the complete real-time trading system

#     This function connects all components:
#     1. Enhanced Instrument Registry (already done)
#     2. Strategy Data Service integration
#     3. Enhanced Analytics callbacks
#     4. UI broadcast integration
#     5. Strategy Engine initialization

#     Returns:
#         bool: True if initialization successful
#     """
#     logger.info("🚀 Initializing Real-Time Trading System...")

#     try:
#         # Step 1: Verify Instrument Registry is available
#         success_registry = await _initialize_instrument_registry()

#         # Step 2: Connect Enhanced Analytics
#         success_analytics = await _connect_enhanced_analytics()

#         # Step 3: Setup UI broadcast callbacks
#         success_ui = await _setup_ui_broadcast()

#         # Step 4: Initialize Strategy Engine
#         success_strategies = await _initialize_strategy_engine()

#         # Step 5: Connect to Centralized WebSocket Manager
#         success_websocket = await _connect_websocket_manager()

#         # Summary
#         total_components = 5
#         successful_components = sum([
#             success_registry, success_analytics, success_ui,
#             success_strategies, success_websocket
#         ])

#         if successful_components == total_components:
#             logger.info(f"✅ Real-Time Trading System fully initialized ({successful_components}/{total_components} components)")

#             # Start background monitoring
#             asyncio.create_task(_monitor_system_health())

#             return True
#         else:
#             logger.warning(f"⚠️ Partial initialization: {successful_components}/{total_components} components initialized")
#             return False

#     except Exception as e:
#         logger.error(f"❌ Error initializing real-time trading system: {e}")
#         return False

# async def _initialize_instrument_registry() -> bool:
#     """Initialize and verify instrument registry"""
#     try:
#         from services.instrument_registry import instrument_registry

#         # Verify enhanced features are available
#         has_strategy_callbacks = hasattr(instrument_registry, 'register_strategy_callback')
#         has_analytics_callbacks = hasattr(instrument_registry, 'register_analytics_callback')
#         has_ui_callbacks = hasattr(instrument_registry, 'register_ui_broadcast_callback')
#         has_realtime_price = hasattr(instrument_registry, 'get_real_time_price')

#         if all([has_strategy_callbacks, has_analytics_callbacks, has_ui_callbacks, has_realtime_price]):
#             logger.info("✅ Enhanced Instrument Registry verified")
#             return True
#         else:
#             logger.error("❌ Instrument Registry missing enhanced features")
#             return False

#     except ImportError as e:
#         logger.error(f"❌ Failed to import instrument registry: {e}")
#         return False

# async def _connect_enhanced_analytics() -> bool:
#     """Connect enhanced analytics to instrument registry callbacks"""
#     try:
#         from services.enhanced_market_analytics import enhanced_analytics
#         from services.instrument_registry import instrument_registry

#         # Define analytics callback function
#         def analytics_callback(analytics_payload: Dict[str, Any]):
#             """Process real-time analytics updates"""
#             try:
#                 updated_instruments = analytics_payload.get('updated_instruments', [])
#                 stats = analytics_payload.get('stats', {})

#                 # Trigger analytics recalculation in background
#                 asyncio.create_task(_update_analytics_background(updated_instruments, stats))

#             except Exception as e:
#                 logger.error(f"❌ Error in analytics callback: {e}")

#         # Register analytics callback
#         success = instrument_registry.register_analytics_callback(
#             analytics_callback,
#             "enhanced_market_analytics"
#         )

#         if success:
#             logger.info("✅ Enhanced Analytics connected to real-time data")
#             return True
#         else:
#             logger.error("❌ Failed to register analytics callback")
#             return False

#     except ImportError as e:
#         logger.error(f"❌ Enhanced analytics not available: {e}")
#         return False

# async def _setup_ui_broadcast() -> bool:
#     """Setup UI broadcast callbacks for WebSocket updates"""
#     try:
#         from services.instrument_registry import instrument_registry

#         # Define UI broadcast callback
#         def ui_broadcast_callback(ui_payload: Dict[str, Any]):
#             """Process UI broadcast updates"""
#             try:
#                 batch_data = ui_payload.get('batch_data', {})
#                 batch_size = ui_payload.get('batch_size', 0)

#                 # Forward to unified WebSocket manager for UI updates
#                 asyncio.create_task(_broadcast_to_ui(batch_data, batch_size))

#             except Exception as e:
#                 logger.error(f"❌ Error in UI broadcast callback: {e}")

#         # Register UI broadcast callback
#         success = instrument_registry.register_ui_broadcast_callback(
#             ui_broadcast_callback,
#             "websocket_ui_broadcast"
#         )

#         if success:
#             logger.info("✅ UI broadcast callbacks registered")
#             return True
#         else:
#             logger.error("❌ Failed to register UI broadcast callback")
#             return False

#     except Exception as e:
#         logger.error(f"❌ Error setting up UI broadcast: {e}")
#         return False

# async def _initialize_strategy_engine() -> bool:
#     """Initialize strategy engine with example strategies"""
#     try:
#         from services.enhanced_strategy_engine import (
#             get_strategy_engine,
#             create_and_start_momentum_strategy,
#             create_and_start_mean_reversion_strategy
#         )

#         # Get strategy engine
#         engine = get_strategy_engine()

#         # Create example strategies (can be customized)
#         example_instruments = [
#             "NSE_EQ|INE002A01018",  # Example: RELIANCE
#             "NSE_EQ|INE467B01029",  # Example: TCS
#         ]

#         # Create momentum strategy
#         momentum_success = create_and_start_momentum_strategy(
#             "auto_momentum_v1",
#             example_instruments,
#             0.015  # 1.5% momentum threshold
#         )

#         # Create mean reversion strategy
#         mean_reversion_success = create_and_start_mean_reversion_strategy(
#             "auto_mean_reversion_v1",
#             example_instruments,
#             20,   # 20 period SMA
#             1.8   # 1.8 standard deviation threshold
#         )

#         if momentum_success or mean_reversion_success:
#             logger.info(f"✅ Strategy Engine initialized (momentum: {momentum_success}, mean_reversion: {mean_reversion_success})")

#             # Start engine
#             await engine.start()

#             return True
#         else:
#             logger.warning("⚠️ No strategies created, but engine is available")
#             return True

#     except ImportError as e:
#         logger.error(f"❌ Strategy engine not available: {e}")
#         return False

# async def _connect_websocket_manager() -> bool:
#     """Connect to centralized WebSocket manager"""
#     try:
#         from services.centralized_ws_manager import centralized_manager

#         if centralized_manager:
#             logger.info("✅ Centralized WebSocket Manager connected")

#             # The centralized manager already calls instrument_registry.update_live_prices()
#             # which will trigger our callbacks automatically

#             return True
#         else:
#             logger.warning("⚠️ Centralized WebSocket Manager not available")
#             return False

#     except ImportError as e:
#         logger.error(f"❌ Centralized WebSocket Manager not available: {e}")
#         return False

# async def _update_analytics_background(updated_instruments: list, stats: Dict[str, Any]):
#     """Update analytics in background thread"""
#     try:
#         # This would trigger analytics recalculation based on updated instruments
#         # For now, just log the update
#         logger.debug(f"📊 Analytics update: {len(updated_instruments)} instruments, stats: {stats}")

#         # Here you could trigger specific analytics modules:
#         # - Gap analysis service
#         # - Breakout detection service
#         # - Market sentiment calculation
#         # etc.

#     except Exception as e:
#         logger.error(f"❌ Error in background analytics update: {e}")

# async def _broadcast_to_ui(batch_data: Dict[str, Any], batch_size: int):
#     """Broadcast data to UI via WebSocket"""
#     try:
#         # Forward to unified WebSocket manager for UI updates
#         from services.unified_websocket_manager import unified_manager

#         if unified_manager and unified_manager.is_running:
#             # Use the existing emit_direct_price_batch method
#             await unified_manager.emit_direct_price_batch(batch_data)

#             logger.debug(f"🖥️ Broadcasted {batch_size} instruments to UI")

#     except Exception as e:
#         logger.error(f"❌ Error broadcasting to UI: {e}")

# async def _monitor_system_health():
#     """Background task to monitor system health"""
#     logger.info("🏥 Starting system health monitoring...")

#     while True:
#         try:
#             await asyncio.sleep(300)  # Check every 5 minutes

#             # Check instrument registry
#             from services.instrument_registry import instrument_registry
#             registry_status = len(instrument_registry._live_prices)

#             # Check strategy engine
#             from services.enhanced_strategy_engine import get_strategy_engine
#             engine = get_strategy_engine()
#             engine_status = engine.get_engine_status()

#             logger.info(
#                 f"🏥 Health Check: "
#                 f"Registry={registry_status} instruments, "
#                 f"Engine={engine_status['active_strategies']} active strategies, "
#                 f"Positions={engine_status['total_positions']}, "
#                 f"P&L=₹{engine_status['total_pnl']:.2f}"
#             )

#         except Exception as e:
#             logger.error(f"❌ Health monitoring error: {e}")
#             await asyncio.sleep(60)  # Shorter retry on error

# def get_system_status() -> Dict[str, Any]:
#     """Get comprehensive system status for health checks"""
#     try:
#         status = {
#             'timestamp': datetime.now().isoformat(),
#             'components': {}
#         }

#         # Instrument Registry Status
#         try:
#             from services.instrument_registry import instrument_registry
#             status['components']['instrument_registry'] = {
#                 'available': True,
#                 'live_prices_count': len(instrument_registry._live_prices),
#                 'enriched_prices_count': len(instrument_registry._enriched_prices),
#                 'strategy_callbacks_count': len(instrument_registry._strategy_callbacks),
#                 'analytics_callbacks_count': len(instrument_registry._analytics_callbacks),
#                 'ui_callbacks_count': len(instrument_registry._ui_broadcast_callbacks),
#             }
#         except Exception as e:
#             status['components']['instrument_registry'] = {
#                 'available': False,
#                 'error': str(e)
#             }

#         # Strategy Engine Status
#         try:
#             from services.enhanced_strategy_engine import get_strategy_engine
#             engine = get_strategy_engine()
#             engine_status = engine.get_engine_status()
#             status['components']['strategy_engine'] = {
#                 'available': True,
#                 'is_running': engine_status['is_running'],
#                 'total_strategies': engine_status['total_strategies'],
#                 'active_strategies': engine_status['active_strategies'],
#                 'total_positions': engine_status['total_positions'],
#                 'total_pnl': engine_status['total_pnl']
#             }
#         except Exception as e:
#             status['components']['strategy_engine'] = {
#                 'available': False,
#                 'error': str(e)
#             }

#         # Enhanced Analytics Status
#         try:
#             from services.enhanced_market_analytics import enhanced_analytics
#             status['components']['enhanced_analytics'] = {
#                 'available': True,
#                 'cache_size': len(enhanced_analytics.cache),
#             }
#         except Exception as e:
#             status['components']['enhanced_analytics'] = {
#                 'available': False,
#                 'error': str(e)
#             }

#         # Centralized WebSocket Manager Status
#         try:
#             from services.centralized_ws_manager import centralized_manager
#             status['components']['centralized_websocket'] = {
#                 'available': centralized_manager is not None,
#             }
#         except Exception as e:
#             status['components']['centralized_websocket'] = {
#                 'available': False,
#                 'error': str(e)
#             }

#         return status

#     except Exception as e:
#         return {
#             'timestamp': datetime.now().isoformat(),
#             'error': str(e),
#             'components': {}
#         }

# # Helper functions for external use

# async def create_custom_momentum_strategy(
#     strategy_name: str,
#     instruments: list,
#     momentum_threshold: float = 0.02,
#     auto_start: bool = True
# ) -> bool:
#     """
#     Create a custom momentum strategy

#     Args:
#         strategy_name: Unique name for the strategy
#         instruments: List of instrument keys
#         momentum_threshold: Momentum threshold (default 2%)
#         auto_start: Whether to auto-start the strategy

#     Returns:
#         bool: True if successful
#     """
#     try:
#         from services.enhanced_strategy_engine import create_and_start_momentum_strategy, get_strategy_engine

#         success = create_and_start_momentum_strategy(
#             strategy_name, instruments, momentum_threshold
#         )

#         if success and auto_start:
#             engine = get_strategy_engine()
#             if not engine.is_running:
#                 await engine.start()

#         return success

#     except Exception as e:
#         logger.error(f"❌ Error creating custom momentum strategy: {e}")
#         return False

# async def create_custom_mean_reversion_strategy(
#     strategy_name: str,
#     instruments: list,
#     sma_period: int = 20,
#     deviation_threshold: float = 2.0,
#     auto_start: bool = True
# ) -> bool:
#     """
#     Create a custom mean reversion strategy

#     Args:
#         strategy_name: Unique name for the strategy
#         instruments: List of instrument keys
#         sma_period: SMA period for mean calculation
#         deviation_threshold: Standard deviation threshold
#         auto_start: Whether to auto-start the strategy

#     Returns:
#         bool: True if successful
#     """
#     try:
#         from services.enhanced_strategy_engine import create_and_start_mean_reversion_strategy, get_strategy_engine

#         success = create_and_start_mean_reversion_strategy(
#             strategy_name, instruments, sma_period, deviation_threshold
#         )

#         if success and auto_start:
#             engine = get_strategy_engine()
#             if not engine.is_running:
#                 await engine.start()

#         return success

#     except Exception as e:
#         logger.error(f"❌ Error creating custom mean reversion strategy: {e}")
#         return False

# def get_all_strategy_performance() -> Dict[str, Any]:
#     """Get performance summary for all strategies"""
#     try:
#         from services.strategy_data_service import get_strategy_performance_summary
#         from services.enhanced_strategy_engine import get_strategy_engine

#         # Get data service performance
#         data_service_perf = get_strategy_performance_summary()

#         # Get strategy engine performance
#         engine = get_strategy_engine()
#         engine_status = engine.get_engine_status()

#         return {
#             'timestamp': datetime.now().isoformat(),
#             'data_services': data_service_perf,
#             'strategy_engine': engine_status,
#             'summary': {
#                 'total_data_services': data_service_perf.get('total_strategies', 0),
#                 'total_engine_strategies': engine_status.get('total_strategies', 0),
#                 'active_strategies': engine_status.get('active_strategies', 0),
#                 'total_positions': engine_status.get('total_positions', 0),
#                 'total_pnl': engine_status.get('total_pnl', 0.0)
#             }
#         }

#     except Exception as e:
#         logger.error(f"❌ Error getting strategy performance: {e}")
#         return {'error': str(e)}

# if __name__ == "__main__":
#     # Test initialization
#     async def test_initialization():
#         success = await initialize_realtime_trading_system()
#         if success:
#             print("✅ Real-time trading system initialized successfully")

#             # Get status
#             status = get_system_status()
#             print(f"📊 System Status: {status}")

#             # Wait a bit then get performance
#             await asyncio.sleep(5)
#             performance = get_all_strategy_performance()
#             print(f"📈 Performance Summary: {performance}")
#         else:
#             print("❌ Failed to initialize real-time trading system")

#     # Run test
#     logging.basicConfig(level=logging.INFO)
#     asyncio.run(test_initialization())
