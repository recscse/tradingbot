"""
NIFTY 50 INDEX 09:40 Strategy Integration Service

IMPORTANT: This is a NIFTY 50 INDEX SPECIFIC strategy for options trading only.
- Focuses ONLY on NIFTY 50 index (NSE_INDEX|Nifty 50)
- Time-based activation at 9:40 AM daily during market hours
- Designed specifically for NIFTY options (CE/PE) trading
- Uses EMA + Candle Strength indicators for signal generation
- Independent strategy that doesn't require user authentication

Key Features:
- Real-time NIFTY 50 index data subscription via instrument registry
- Time-based activation at 9:40 AM daily with automatic deactivation at 3:15 PM
- Live 5-minute OHLCV signal generation for NIFTY options
- WebSocket broadcasting of NIFTY-specific trading signals
- Independent execution without user dependencies
- Performance tracking specifically for NIFTY index trading
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
from typing import Dict, Any, Optional, List
import logging
from dataclasses import dataclass

# Import the pure strategy logic
from strategies.nifty_09_40 import decide_trade, get_strategy_info, validate_params
from services.instrument_registry import InstrumentRegistry
# Make WebSocket manager optional for independence
try:
    from services.websocket.auto_trading_websocket import AutoTradingWebSocketManager
    WEBSOCKET_AVAILABLE = True
except ImportError:
    AutoTradingWebSocketManager = None
    WEBSOCKET_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class NiftyStrategyConfig:
    """Configuration for NIFTY 09:40 strategy"""
    strategy_name: str = "NIFTY_09_40_EMA"
    nifty_symbol: str = "NSE_INDEX|Nifty 50"
    nifty_instrument_key: str = "NSE_INDEX|99926000"  # NIFTY 50 instrument key
    timeframe: str = "5m"
    start_time: time = time(9, 40)  # 9:40 AM
    end_time: time = time(15, 15)   # 3:15 PM
    max_daily_trades: int = 3
    position_size: float = 100000.0  # 1 lakh position size
    enabled: bool = True
    
    # Strategy parameters
    ema_period: int = 20
    strength_threshold: float = 0.7
    volume_multiplier: float = 1.5
    stop_loss_pct: float = 2.0
    target_pct: float = 4.0

class NiftyStrategyIntegration:
    """Integration service for NIFTY 09:40 strategy with live data"""
    
    def __init__(self, config: NiftyStrategyConfig = None):
        self.config = config or NiftyStrategyConfig()
        
        # Use LiveFeedAdapter for direct, zero-delay data access
        try:
            from services.live_adapter import LiveFeedAdapter
            self.live_adapter = LiveFeedAdapter()
            logger.info("✅ Connected to LiveFeedAdapter for zero-delay data")
        except ImportError:
            self.live_adapter = None
            logger.warning("⚠️ LiveFeedAdapter not available, using fallback")
        
        # Fallback to instrument registry if needed
        self.instrument_registry = InstrumentRegistry()
        self.websocket_manager = None  # Optional WebSocket manager
        
        # Strategy state
        self.is_active = False
        self.daily_trades_count = 0
        self.last_signal_time = None
        self.current_position = None
        self.ohlcv_buffer = pd.DataFrame()
        self.strategy_start_date = None
        
        # Performance tracking
        self.daily_stats = {
            'signals_generated': 0,
            'trades_executed': 0,
            'winning_trades': 0,
            'total_pnl': 0.0,
            'best_trade': 0.0,
            'worst_trade': 0.0
        }
        
        logger.info(f"🎯 NIFTY 09:40 Strategy initialized - Target time: {self.config.start_time}")

    async def initialize(self, websocket_manager=None):
        """Initialize the strategy integration with live data feeds"""
        try:
            # Only set WebSocket manager if available and provided
            if WEBSOCKET_AVAILABLE and websocket_manager:
                self.websocket_manager = websocket_manager
            
            # Register for real-time NIFTY data updates
            await self._register_for_live_data()
            
            # Schedule daily strategy activation
            await self._schedule_daily_activation()
            
            logger.info("✅ NIFTY 09:40 Strategy integration initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize NIFTY strategy integration: {e}")
            return False

    async def _register_for_live_data(self):
        """Register with LiveFeedAdapter for real-time NIFTY data (ZERO DELAY)"""
        try:
            # PRIMARY: Use LiveFeedAdapter for zero-delay direct callback
            if self.live_adapter:
                instruments = [self.config.nifty_instrument_key]
                
                # Register callback for direct, immediate price updates
                self.live_adapter.register_tick_callback(
                    name=f"NIFTY_09_40_{id(self)}",
                    instruments=instruments,
                    callback=self._on_live_tick_update  # Direct tick callback
                )
                
                logger.info(f"🚀 ZERO-DELAY: Registered with LiveFeedAdapter for {self.config.nifty_symbol}")
                
            # FALLBACK: Use instrument registry if LiveFeedAdapter unavailable
            else:
                instruments = [self.config.nifty_instrument_key]
                
                self.instrument_registry.register_strategy_callback(
                    strategy_name=self.config.strategy_name,
                    instruments=instruments,
                    callback=self._on_live_data_update
                )
                
                logger.info(f"✅ FALLBACK: Registered with instrument registry for {self.config.nifty_symbol}")
            
            # Initialize OHLCV buffer with historical data if available
            await self._initialize_ohlcv_buffer()
            
        except Exception as e:
            logger.error(f"❌ Failed to register for live data: {e}")
            raise

    async def _initialize_ohlcv_buffer(self):
        """Initialize OHLCV buffer with recent historical data"""
        try:
            # Get the last 50 5-minute candles to initialize EMA calculation
            # This would typically come from your historical data service
            
            # For now, create empty buffer - real implementation would fetch historical data
            columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            self.ohlcv_buffer = pd.DataFrame(columns=columns)
            
            logger.info("✅ OHLCV buffer initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize OHLCV buffer: {e}")

    async def _schedule_daily_activation(self):
        """Schedule daily strategy activation at 9:40 AM"""
        asyncio.create_task(self._daily_activation_loop())
        logger.info("✅ Daily activation scheduler started")

    async def _daily_activation_loop(self):
        """Daily loop to activate strategy at the right time"""
        while True:
            try:
                now = datetime.now()
                today_start = datetime.combine(now.date(), self.config.start_time)
                today_end = datetime.combine(now.date(), self.config.end_time)
                
                # Check if today is a trading day (skip weekends)
                if now.weekday() < 5:  # Monday = 0, Sunday = 6
                    
                    if today_start <= now <= today_end:
                        # Trading hours - activate strategy if not already active
                        if not self.is_active:
                            await self._activate_daily_strategy()
                    
                    elif now > today_end:
                        # After trading hours - deactivate and prepare for next day
                        if self.is_active:
                            await self._deactivate_daily_strategy()
                
                # Sleep for 1 minute before next check
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"❌ Error in daily activation loop: {e}")
                await asyncio.sleep(60)

    async def _activate_daily_strategy(self):
        """Activate strategy for the trading day"""
        try:
            current_date = datetime.now().date()
            
            # Reset daily counters if new day
            if self.strategy_start_date != current_date:
                self.daily_trades_count = 0
                self.strategy_start_date = current_date
                self.daily_stats = {
                    'signals_generated': 0,
                    'trades_executed': 0,
                    'winning_trades': 0,
                    'total_pnl': 0.0,
                    'best_trade': 0.0,
                    'worst_trade': 0.0
                }
            
            self.is_active = True
            logger.info(f"🚀 NIFTY 09:40 Strategy ACTIVATED for {current_date}")
            
            # Broadcast activation status if WebSocket is available
            if WEBSOCKET_AVAILABLE and self.websocket_manager:
                try:
                    await self.websocket_manager.broadcast_strategy_status({
                        'strategy_name': self.config.strategy_name,
                        'status': 'ACTIVE',
                        'activation_time': datetime.now().isoformat(),
                        'daily_trades_count': self.daily_trades_count,
                        'max_trades': self.config.max_daily_trades
                    })
                except Exception as e:
                    logger.warning(f"WebSocket broadcast failed: {e}")
                
        except Exception as e:
            logger.error(f"❌ Failed to activate daily strategy: {e}")

    async def _deactivate_daily_strategy(self):
        """Deactivate strategy at end of trading day"""
        try:
            self.is_active = False
            
            # Log daily performance
            logger.info(f"📊 NIFTY 09:40 Daily Summary:")
            logger.info(f"   Signals Generated: {self.daily_stats['signals_generated']}")
            logger.info(f"   Trades Executed: {self.daily_stats['trades_executed']}")
            logger.info(f"   Total P&L: ₹{self.daily_stats['total_pnl']:,.2f}")
            
            # Broadcast deactivation status if WebSocket is available
            if WEBSOCKET_AVAILABLE and self.websocket_manager:
                try:
                    await self.websocket_manager.broadcast_strategy_status({
                        'strategy_name': self.config.strategy_name,
                        'status': 'INACTIVE',
                        'deactivation_time': datetime.now().isoformat(),
                        'daily_summary': self.daily_stats
                    })
                except Exception as e:
                    logger.warning(f"WebSocket broadcast failed: {e}")
            
            logger.info(f"🛑 NIFTY 09:40 Strategy DEACTIVATED")
            
        except Exception as e:
            logger.error(f"❌ Failed to deactivate daily strategy: {e}")

    def _on_live_tick_update(self, instrument_key: str, price_data: Dict[str, Any]):
        """Handle real-time tick updates from LiveFeedAdapter (ZERO DELAY)"""
        try:
            # Only process NIFTY instrument and when strategy is active
            if instrument_key != self.config.nifty_instrument_key:
                return
                
            if not self.is_active or not self.config.enabled:
                return
            
            # Process tick data synchronously for zero delay
            asyncio.create_task(self._process_tick_data(price_data))
                    
        except Exception as e:
            logger.error(f"❌ Error processing live tick update: {e}")

    async def _process_tick_data(self, price_data: Dict[str, Any]):
        """Process tick data and generate signals"""
        try:
            # Convert live tick to OHLCV format with numpy optimization
            await self._update_ohlcv_buffer(price_data)
            
            # Check if we have enough data for strategy
            if len(self.ohlcv_buffer) >= self.config.ema_period + 5:
                
                # Generate strategy signal
                signal = await self._generate_strategy_signal()
                
                if signal and signal['signal'] != 'HOLD':
                    await self._process_strategy_signal(signal)
                    
        except Exception as e:
            logger.error(f"❌ Error processing tick data: {e}")

    async def _on_live_data_update(self, instrument_key: str, price_data: Dict[str, Any]):
        """Handle real-time price updates for NIFTY (FALLBACK METHOD)"""
        try:
            if not self.is_active or not self.config.enabled:
                return
            
            # Convert live tick to OHLCV format
            await self._update_ohlcv_buffer(price_data)
            
            # Check if we have enough data for strategy
            if len(self.ohlcv_buffer) >= self.config.ema_period + 5:
                
                # Generate strategy signal
                signal = await self._generate_strategy_signal()
                
                if signal and signal['signal'] != 'HOLD':
                    await self._process_strategy_signal(signal)
                    
        except Exception as e:
            logger.error(f"❌ Error processing live data update: {e}")

    async def _update_ohlcv_buffer(self, price_data: Dict[str, Any]):
        """Update OHLCV buffer with new tick data using optimized pandas operations"""
        try:
            timestamp = datetime.now()
            current_price = float(price_data.get('ltp', 0))
            volume = int(price_data.get('vol_traded_today', 0))
            
            # Create 5-minute candle logic using numpy for efficiency
            current_minute = timestamp.replace(second=0, microsecond=0)
            five_min_mark = current_minute - timedelta(minutes=current_minute.minute % 5)
            
            # Check if we need a new candle
            if self.ohlcv_buffer.empty or pd.to_datetime(self.ohlcv_buffer['timestamp'].iloc[-1]) < five_min_mark:
                # Create new 5-minute candle using numpy array for efficiency
                new_candle_data = np.array([
                    five_min_mark, current_price, current_price, 
                    current_price, current_price, volume
                ]).reshape(1, -1)
                
                new_candle_df = pd.DataFrame(
                    new_candle_data,
                    columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                )
                
                # Convert data types for optimization
                new_candle_df['open'] = new_candle_df['open'].astype(np.float64)
                new_candle_df['high'] = new_candle_df['high'].astype(np.float64)  
                new_candle_df['low'] = new_candle_df['low'].astype(np.float64)
                new_candle_df['close'] = new_candle_df['close'].astype(np.float64)
                new_candle_df['volume'] = new_candle_df['volume'].astype(np.int64)
                
                self.ohlcv_buffer = pd.concat([
                    self.ohlcv_buffer, 
                    new_candle_df
                ], ignore_index=True)
                
            else:
                # Update current candle using numpy operations for speed
                last_idx = len(self.ohlcv_buffer) - 1
                
                # Use numpy maximum/minimum for faster computation
                current_high = self.ohlcv_buffer.iloc[last_idx]['high']
                current_low = self.ohlcv_buffer.iloc[last_idx]['low']
                
                self.ohlcv_buffer.iloc[last_idx, self.ohlcv_buffer.columns.get_loc('high')] = np.maximum(current_high, current_price)
                self.ohlcv_buffer.iloc[last_idx, self.ohlcv_buffer.columns.get_loc('low')] = np.minimum(current_low, current_price)
                self.ohlcv_buffer.iloc[last_idx, self.ohlcv_buffer.columns.get_loc('close')] = current_price
                self.ohlcv_buffer.iloc[last_idx, self.ohlcv_buffer.columns.get_loc('volume')] = volume
            
            # Keep only last 100 candles for memory efficiency using pandas tail
            if len(self.ohlcv_buffer) > 100:
                self.ohlcv_buffer = self.ohlcv_buffer.tail(100).reset_index(drop=True)
                # Optimize memory by ensuring proper dtypes
                self.ohlcv_buffer = self.ohlcv_buffer.astype({
                    'open': np.float64, 'high': np.float64, 'low': np.float64, 
                    'close': np.float64, 'volume': np.int64
                })
                
        except Exception as e:
            logger.error(f"❌ Error updating OHLCV buffer: {e}")

    async def _generate_strategy_signal(self) -> Optional[Dict[str, Any]]:
        """Generate trading signal using the pure strategy logic"""
        try:
            # Prepare parameters
            params = {
                'ema_period': self.config.ema_period,
                'strength_threshold': self.config.strength_threshold,
                'volume_multiplier': self.config.volume_multiplier,
                'stop_loss_pct': self.config.stop_loss_pct,
                'target_pct': self.config.target_pct
            }
            
            # Validate parameters
            validated_params = validate_params(params)
            
            # Generate signal using pure strategy logic
            signal = decide_trade(self.ohlcv_buffer.copy(), validated_params)
            
            if signal and signal['signal'] != 'HOLD':
                signal['strategy_name'] = self.config.strategy_name
                signal['instrument_key'] = self.config.nifty_instrument_key
                signal['symbol'] = self.config.nifty_symbol
                
                self.daily_stats['signals_generated'] += 1
                logger.info(f"🎯 NIFTY Signal Generated: {signal['signal']} at {signal['entry_price']} (confidence: {signal['confidence']:.1%})")
            
            return signal
            
        except Exception as e:
            logger.error(f"❌ Error generating strategy signal: {e}")
            return None

    async def _process_strategy_signal(self, signal: Dict[str, Any]):
        """Process and broadcast strategy signal"""
        try:
            # Check daily trade limits
            if self.daily_trades_count >= self.config.max_daily_trades:
                logger.warning(f"⚠️ Daily trade limit reached ({self.config.max_daily_trades})")
                return
            
            # Add position sizing and risk management
            signal['position_size'] = self.config.position_size
            signal['max_risk'] = self.config.position_size * (self.config.stop_loss_pct / 100)
            
            # Broadcast signal via WebSocket if available
            if WEBSOCKET_AVAILABLE and self.websocket_manager:
                try:
                    await self.websocket_manager.broadcast_strategy_signal({
                        'type': 'nifty_09_40_signal',
                        'signal': signal,
                        'timestamp': datetime.now().isoformat(),
                        'daily_stats': self.daily_stats
                    })
                except Exception as e:
                    logger.warning(f"Signal broadcast failed: {e}")
            
            # Record signal time to avoid duplicates
            self.last_signal_time = datetime.now()
            
            logger.info(f"📢 NIFTY Signal Broadcasted: {signal['signal']} | Entry: ₹{signal['entry_price']} | Target: ₹{signal['target']} | SL: ₹{signal['stop_loss']}")
            
        except Exception as e:
            logger.error(f"❌ Error processing strategy signal: {e}")

    async def get_strategy_status(self) -> Dict[str, Any]:
        """Get current strategy status"""
        return {
            'strategy_name': self.config.strategy_name,
            'is_active': self.is_active,
            'enabled': self.config.enabled,
            'daily_trades_count': self.daily_trades_count,
            'max_daily_trades': self.config.max_daily_trades,
            'current_time': datetime.now().isoformat(),
            'strategy_start_time': self.config.start_time.isoformat(),
            'strategy_end_time': self.config.end_time.isoformat(),
            'daily_stats': self.daily_stats,
            'buffer_size': len(self.ohlcv_buffer),
            'last_signal_time': self.last_signal_time.isoformat() if self.last_signal_time else None
        }

    async def update_config(self, new_config: Dict[str, Any]):
        """Update strategy configuration"""
        try:
            for key, value in new_config.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
            
            logger.info(f"✅ NIFTY strategy configuration updated: {new_config}")
            
            # Broadcast config update if WebSocket is available
            if WEBSOCKET_AVAILABLE and self.websocket_manager:
                try:
                    await self.websocket_manager.broadcast_strategy_config_update({
                        'strategy_name': self.config.strategy_name,
                        'updated_config': new_config,
                        'timestamp': datetime.now().isoformat()
                    })
                except Exception as e:
                    logger.warning(f"Config update broadcast failed: {e}")
                
        except Exception as e:
            logger.error(f"❌ Error updating strategy config: {e}")

    async def stop_strategy(self):
        """Stop the strategy"""
        try:
            self.is_active = False
            self.config.enabled = False
            
            logger.info(f"🛑 NIFTY 09:40 Strategy stopped manually")
            
            if WEBSOCKET_AVAILABLE and self.websocket_manager:
                try:
                    await self.websocket_manager.broadcast_strategy_status({
                        'strategy_name': self.config.strategy_name,
                        'status': 'STOPPED',
                        'stopped_time': datetime.now().isoformat(),
                        'reason': 'Manual stop'
                    })
                except Exception as e:
                    logger.warning(f"Stop status broadcast failed: {e}")
                
        except Exception as e:
            logger.error(f"❌ Error stopping strategy: {e}")

# Global instance for integration
_nifty_strategy_integration = None

async def get_nifty_strategy_integration() -> NiftyStrategyIntegration:
    """Get the global NIFTY strategy integration instance"""
    global _nifty_strategy_integration
    
    if _nifty_strategy_integration is None:
        _nifty_strategy_integration = NiftyStrategyIntegration()
        
    return _nifty_strategy_integration

async def initialize_nifty_strategy(websocket_manager=None) -> bool:
    """Initialize the NIFTY 09:40 strategy integration"""
    try:
        strategy = await get_nifty_strategy_integration()
        result = await strategy.initialize(websocket_manager)
        
        if result:
            logger.info("🚀 NIFTY 09:40 Strategy integration started successfully")
        else:
            logger.error("❌ Failed to start NIFTY 09:40 Strategy integration")
            
        return result
        
    except Exception as e:
        logger.error(f"❌ Error initializing NIFTY strategy: {e}")
        return False