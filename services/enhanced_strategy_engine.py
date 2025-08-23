"""
Enhanced Real-Time Strategy Engine

This engine provides real-time trading strategy execution with zero-delay price access.
It integrates with the Strategy Data Service for ultra-fast market data processing.

Features:
- Real-time strategy execution with zero latency
- Portfolio management and position tracking
- Risk management and stop-loss execution
- Multiple strategy types (momentum, mean reversion, breakout, arbitrage)
- Advanced order management
- Performance tracking and analytics
- Integration with existing trading infrastructure

Usage:
    from services.enhanced_strategy_engine import RealTimeStrategyEngine, MomentumStrategy
    
    # Create engine
    engine = RealTimeStrategyEngine()
    
    # Create and register strategy
    momentum_strategy = MomentumStrategy("momentum_v1", ["RELIANCE", "TCS"])
    engine.register_strategy(momentum_strategy)
    
    # Start real-time execution
    await engine.start()
"""

import asyncio
import logging
import time
import json
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import numpy as np

from services.strategy_data_service import get_strategy_data_service
from services.strategy_engine import fibonacci_levels, simple_ema, strategy_score

logger = logging.getLogger(__name__)

class OrderType(Enum):
    """Order types for strategy execution"""
    BUY = "buy"
    SELL = "sell"
    BUY_LIMIT = "buy_limit"
    SELL_LIMIT = "sell_limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"

class OrderStatus(Enum):
    """Order execution status"""
    PENDING = "pending"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"
    FAILED = "failed"

class SignalType(Enum):
    """Trading signal types"""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"

@dataclass
class TradingSignal:
    """Trading signal data structure"""
    instrument_key: str
    symbol: str
    signal_type: SignalType
    strength: float  # 0-1 scale
    price: float
    timestamp: datetime
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'instrument_key': self.instrument_key,
            'symbol': self.symbol,
            'signal_type': self.signal_type.value,
            'strength': round(self.strength, 3),
            'price': self.price,
            'timestamp': self.timestamp.isoformat(),
            'reason': self.reason,
            'metadata': self.metadata
        }

@dataclass
class Position:
    """Trading position data structure"""
    instrument_key: str
    symbol: str
    quantity: int
    entry_price: float
    current_price: float
    entry_time: datetime
    last_update: datetime
    pnl: float = 0.0
    pnl_percent: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    def update_price(self, new_price: float):
        """Update position with new price"""
        self.current_price = new_price
        self.last_update = datetime.now()
        
        # Calculate P&L
        price_diff = new_price - self.entry_price
        if self.quantity > 0:  # Long position
            self.pnl = price_diff * abs(self.quantity)
        else:  # Short position
            self.pnl = -price_diff * abs(self.quantity)
        
        self.pnl_percent = (self.pnl / (self.entry_price * abs(self.quantity))) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'instrument_key': self.instrument_key,
            'symbol': self.symbol,
            'quantity': self.quantity,
            'entry_price': self.entry_price,
            'current_price': self.current_price,
            'entry_time': self.entry_time.isoformat(),
            'last_update': self.last_update.isoformat(),
            'pnl': round(self.pnl, 2),
            'pnl_percent': round(self.pnl_percent, 3),
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit
        }

class BaseStrategy(ABC):
    """Abstract base class for trading strategies"""
    
    def __init__(self, strategy_name: str, instruments: List[str]):
        self.strategy_name = strategy_name
        self.instruments = instruments
        self.is_active = False
        self.positions: Dict[str, Position] = {}
        self.signals_generated = 0
        self.trades_executed = 0
        self.last_signal_time = None
        
        # Get strategy data service
        self.data_service = get_strategy_data_service(strategy_name)
        self.data_service.subscribe_to_instruments(instruments)
        self.data_service.set_price_callback(self._on_price_update)
        
        # Strategy-specific parameters
        self.max_position_size = 100  # Maximum quantity per position
        self.risk_per_trade = 0.02  # 2% risk per trade
        self.max_positions = 5  # Maximum concurrent positions
        
        logger.info(f"✅ Strategy '{strategy_name}' initialized with {len(instruments)} instruments")
    
    @abstractmethod
    def generate_signal(self, instrument_key: str, price_data: Dict[str, Any]) -> Optional[TradingSignal]:
        """Generate trading signal based on price data"""
        pass
    
    @abstractmethod
    def should_exit_position(self, position: Position, current_price: float) -> bool:
        """Determine if position should be closed"""
        pass
    
    def _on_price_update(self, instrument_key: str, price_data: Dict[str, Any]):
        """Handle real-time price updates - ZERO DELAY"""
        try:
            current_price = price_data.get('ltp', 0)
            if not current_price:
                return
            
            # Update existing positions
            if instrument_key in self.positions:
                position = self.positions[instrument_key]
                position.update_price(current_price)
                
                # Check exit conditions
                if self.should_exit_position(position, current_price):
                    self._exit_position(position)
            
            # Generate new signals if not at max positions
            if len(self.positions) < self.max_positions:
                signal = self.generate_signal(instrument_key, price_data)
                if signal:
                    self._process_signal(signal)
                    
        except Exception as e:
            logger.error(f"❌ Error in price update for strategy {self.strategy_name}: {e}")
    
    def _process_signal(self, signal: TradingSignal):
        """Process generated trading signal"""
        try:
            self.signals_generated += 1
            self.last_signal_time = datetime.now()
            
            # Execute trade based on signal
            if signal.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
                self._enter_long_position(signal)
            elif signal.signal_type in [SignalType.SELL, SignalType.STRONG_SELL]:
                self._enter_short_position(signal)
            
            logger.info(f"📊 Signal processed: {signal.signal_type.value} for {signal.symbol}")
            
        except Exception as e:
            logger.error(f"❌ Error processing signal for {self.strategy_name}: {e}")
    
    def _enter_long_position(self, signal: TradingSignal):
        """Enter long position based on signal"""
        try:
            # Calculate position size based on risk
            quantity = self._calculate_position_size(signal.price)
            
            # Create position
            position = Position(
                instrument_key=signal.instrument_key,
                symbol=signal.symbol,
                quantity=quantity,
                entry_price=signal.price,
                current_price=signal.price,
                entry_time=signal.timestamp,
                last_update=signal.timestamp,
                stop_loss=signal.price * 0.95,  # 5% stop loss
                take_profit=signal.price * 1.10  # 10% take profit
            )
            
            self.positions[signal.instrument_key] = position
            self.trades_executed += 1
            
            logger.info(f"📈 Long position opened: {signal.symbol} @ ₹{signal.price} (qty: {quantity})")
            
        except Exception as e:
            logger.error(f"❌ Error entering long position: {e}")
    
    def _enter_short_position(self, signal: TradingSignal):
        """Enter short position based on signal"""
        try:
            # Calculate position size based on risk
            quantity = -self._calculate_position_size(signal.price)  # Negative for short
            
            # Create position
            position = Position(
                instrument_key=signal.instrument_key,
                symbol=signal.symbol,
                quantity=quantity,
                entry_price=signal.price,
                current_price=signal.price,
                entry_time=signal.timestamp,
                last_update=signal.timestamp,
                stop_loss=signal.price * 1.05,  # 5% stop loss (higher for short)
                take_profit=signal.price * 0.90  # 10% take profit (lower for short)
            )
            
            self.positions[signal.instrument_key] = position
            self.trades_executed += 1
            
            logger.info(f"📉 Short position opened: {signal.symbol} @ ₹{signal.price} (qty: {quantity})")
            
        except Exception as e:
            logger.error(f"❌ Error entering short position: {e}")
    
    def _exit_position(self, position: Position):
        """Exit existing position"""
        try:
            pnl = position.pnl
            pnl_percent = position.pnl_percent
            
            # Remove from positions
            del self.positions[position.instrument_key]
            
            logger.info(
                f"🔚 Position closed: {position.symbol} "
                f"P&L: ₹{pnl:.2f} ({pnl_percent:+.2f}%)"
            )
            
        except Exception as e:
            logger.error(f"❌ Error exiting position: {e}")
    
    def _calculate_position_size(self, price: float) -> int:
        """Calculate position size based on risk management"""
        try:
            # Simple position sizing - can be enhanced
            base_quantity = min(self.max_position_size, max(1, int(10000 / price)))
            return base_quantity
            
        except Exception as e:
            logger.error(f"❌ Error calculating position size: {e}")
            return 1
    
    def get_portfolio_status(self) -> Dict[str, Any]:
        """Get current portfolio status"""
        try:
            total_pnl = sum(pos.pnl for pos in self.positions.values())
            total_positions = len(self.positions)
            
            return {
                'strategy_name': self.strategy_name,
                'is_active': self.is_active,
                'total_positions': total_positions,
                'total_pnl': round(total_pnl, 2),
                'signals_generated': self.signals_generated,
                'trades_executed': self.trades_executed,
                'last_signal_time': self.last_signal_time.isoformat() if self.last_signal_time else None,
                'positions': [pos.to_dict() for pos in self.positions.values()],
                'data_service_status': self.data_service.get_portfolio_status()
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting portfolio status: {e}")
            return {'error': str(e)}

class MomentumStrategy(BaseStrategy):
    """Momentum-based trading strategy"""
    
    def __init__(self, strategy_name: str, instruments: List[str]):
        super().__init__(strategy_name, instruments)
        self.price_history: Dict[str, List[float]] = {}
        self.momentum_threshold = 0.02  # 2% momentum threshold
        self.lookback_period = 10  # Number of price points to consider
    
    def generate_signal(self, instrument_key: str, price_data: Dict[str, Any]) -> Optional[TradingSignal]:
        """Generate momentum-based signals"""
        try:
            current_price = price_data.get('ltp', 0)
            if not current_price:
                return None
            
            # Initialize price history for new instruments
            if instrument_key not in self.price_history:
                self.price_history[instrument_key] = []
            
            # Add current price to history
            self.price_history[instrument_key].append(current_price)
            
            # Keep only recent prices
            if len(self.price_history[instrument_key]) > self.lookback_period:
                self.price_history[instrument_key] = self.price_history[instrument_key][-self.lookback_period:]
            
            # Need enough price history
            if len(self.price_history[instrument_key]) < self.lookback_period:
                return None
            
            # Calculate momentum
            prices = self.price_history[instrument_key]
            old_price = prices[0]
            momentum = (current_price - old_price) / old_price
            
            # Generate signal based on momentum
            if momentum > self.momentum_threshold:
                return TradingSignal(
                    instrument_key=instrument_key,
                    symbol=price_data.get('symbol', instrument_key),
                    signal_type=SignalType.BUY,
                    strength=min(1.0, momentum / (self.momentum_threshold * 2)),
                    price=current_price,
                    timestamp=datetime.now(),
                    reason=f"Positive momentum: {momentum:.3f}",
                    metadata={'momentum': momentum, 'lookback': self.lookback_period}
                )
            elif momentum < -self.momentum_threshold:
                return TradingSignal(
                    instrument_key=instrument_key,
                    symbol=price_data.get('symbol', instrument_key),
                    signal_type=SignalType.SELL,
                    strength=min(1.0, abs(momentum) / (self.momentum_threshold * 2)),
                    price=current_price,
                    timestamp=datetime.now(),
                    reason=f"Negative momentum: {momentum:.3f}",
                    metadata={'momentum': momentum, 'lookback': self.lookback_period}
                )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error generating momentum signal: {e}")
            return None
    
    def should_exit_position(self, position: Position, current_price: float) -> bool:
        """Check if momentum position should be exited"""
        try:
            # Stop loss check
            if position.stop_loss:
                if position.quantity > 0 and current_price <= position.stop_loss:
                    return True
                if position.quantity < 0 and current_price >= position.stop_loss:
                    return True
            
            # Take profit check
            if position.take_profit:
                if position.quantity > 0 and current_price >= position.take_profit:
                    return True
                if position.quantity < 0 and current_price <= position.take_profit:
                    return True
            
            # Time-based exit (hold for max 1 hour)
            time_held = datetime.now() - position.entry_time
            if time_held > timedelta(hours=1):
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error checking exit conditions: {e}")
            return False

class MeanReversionStrategy(BaseStrategy):
    """Mean reversion trading strategy"""
    
    def __init__(self, strategy_name: str, instruments: List[str]):
        super().__init__(strategy_name, instruments)
        self.price_history: Dict[str, List[float]] = {}
        self.sma_period = 20
        self.deviation_threshold = 2.0  # Standard deviations
    
    def generate_signal(self, instrument_key: str, price_data: Dict[str, Any]) -> Optional[TradingSignal]:
        """Generate mean reversion signals"""
        try:
            current_price = price_data.get('ltp', 0)
            if not current_price:
                return None
            
            # Initialize price history
            if instrument_key not in self.price_history:
                self.price_history[instrument_key] = []
            
            # Add current price
            self.price_history[instrument_key].append(current_price)
            
            # Keep only recent prices
            if len(self.price_history[instrument_key]) > self.sma_period * 2:
                self.price_history[instrument_key] = self.price_history[instrument_key][-self.sma_period * 2:]
            
            # Need enough history
            if len(self.price_history[instrument_key]) < self.sma_period:
                return None
            
            # Calculate SMA and standard deviation
            prices = np.array(self.price_history[instrument_key][-self.sma_period:])
            sma = np.mean(prices)
            std = np.std(prices)
            
            if std == 0:
                return None
            
            # Calculate z-score
            z_score = (current_price - sma) / std
            
            # Generate signals based on z-score
            if z_score > self.deviation_threshold:  # Price too high, sell
                return TradingSignal(
                    instrument_key=instrument_key,
                    symbol=price_data.get('symbol', instrument_key),
                    signal_type=SignalType.SELL,
                    strength=min(1.0, (abs(z_score) - self.deviation_threshold) / self.deviation_threshold),
                    price=current_price,
                    timestamp=datetime.now(),
                    reason=f"Mean reversion sell: z-score {z_score:.2f}",
                    metadata={'z_score': z_score, 'sma': sma, 'std': std}
                )
            elif z_score < -self.deviation_threshold:  # Price too low, buy
                return TradingSignal(
                    instrument_key=instrument_key,
                    symbol=price_data.get('symbol', instrument_key),
                    signal_type=SignalType.BUY,
                    strength=min(1.0, (abs(z_score) - self.deviation_threshold) / self.deviation_threshold),
                    price=current_price,
                    timestamp=datetime.now(),
                    reason=f"Mean reversion buy: z-score {z_score:.2f}",
                    metadata={'z_score': z_score, 'sma': sma, 'std': std}
                )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error generating mean reversion signal: {e}")
            return None
    
    def should_exit_position(self, position: Position, current_price: float) -> bool:
        """Check if mean reversion position should be exited"""
        try:
            # Stop loss and take profit
            if position.stop_loss:
                if position.quantity > 0 and current_price <= position.stop_loss:
                    return True
                if position.quantity < 0 and current_price >= position.stop_loss:
                    return True
            
            if position.take_profit:
                if position.quantity > 0 and current_price >= position.take_profit:
                    return True
                if position.quantity < 0 and current_price <= position.take_profit:
                    return True
            
            # Mean reversion exit: if price moves back toward mean
            prices = self.price_history.get(position.instrument_key, [])
            if len(prices) >= self.sma_period:
                sma = np.mean(prices[-self.sma_period:])
                
                # Exit if price is moving toward mean
                if position.quantity > 0 and current_price < position.entry_price:
                    # Long position, price dropping toward mean
                    return abs(current_price - sma) < abs(position.entry_price - sma) * 0.5
                elif position.quantity < 0 and current_price > position.entry_price:
                    # Short position, price rising toward mean
                    return abs(current_price - sma) < abs(position.entry_price - sma) * 0.5
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error checking mean reversion exit conditions: {e}")
            return False

class RealTimeStrategyEngine:
    """
    Main engine for managing multiple real-time trading strategies
    """
    
    def __init__(self):
        self.strategies: Dict[str, BaseStrategy] = {}
        self.is_running = False
        self.total_trades = 0
        self.total_pnl = 0.0
        self.start_time = None
        
        # Performance tracking
        self.signals_per_minute = 0
        self.last_performance_update = time.time()
        
        logger.info("✅ Real-Time Strategy Engine initialized")
    
    def register_strategy(self, strategy: BaseStrategy) -> bool:
        """Register a strategy with the engine"""
        try:
            if strategy.strategy_name in self.strategies:
                logger.warning(f"⚠️ Strategy '{strategy.strategy_name}' already registered")
                return False
            
            self.strategies[strategy.strategy_name] = strategy
            logger.info(f"✅ Strategy '{strategy.strategy_name}' registered")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error registering strategy: {e}")
            return False
    
    def remove_strategy(self, strategy_name: str) -> bool:
        """Remove a strategy from the engine"""
        try:
            if strategy_name not in self.strategies:
                logger.warning(f"⚠️ Strategy '{strategy_name}' not found")
                return False
            
            strategy = self.strategies[strategy_name]
            strategy.is_active = False
            del self.strategies[strategy_name]
            
            logger.info(f"✅ Strategy '{strategy_name}' removed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error removing strategy: {e}")
            return False
    
    async def start(self) -> bool:
        """Start real-time strategy execution"""
        try:
            if self.is_running:
                logger.warning("⚠️ Strategy engine is already running")
                return False
            
            self.is_running = True
            self.start_time = datetime.now()
            
            # Activate all strategies
            for strategy in self.strategies.values():
                strategy.is_active = True
            
            # Start monitoring loop
            asyncio.create_task(self._monitoring_loop())
            
            logger.info(f"🚀 Strategy engine started with {len(self.strategies)} strategies")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error starting strategy engine: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop strategy execution"""
        try:
            self.is_running = False
            
            # Deactivate all strategies
            for strategy in self.strategies.values():
                strategy.is_active = False
            
            logger.info("🛑 Strategy engine stopped")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error stopping strategy engine: {e}")
            return False
    
    async def _monitoring_loop(self):
        """Background monitoring and performance tracking"""
        while self.is_running:
            try:
                # Update performance metrics
                await self._update_performance_metrics()
                
                # Log status every minute
                await asyncio.sleep(60)
                
                if self.is_running:
                    status = self.get_engine_status()
                    logger.info(
                        f"📊 Engine Status: {status['active_strategies']} strategies, "
                        f"{status['total_positions']} positions, "
                        f"₹{status['total_pnl']:.2f} P&L"
                    )
                    
            except Exception as e:
                logger.error(f"❌ Error in monitoring loop: {e}")
                await asyncio.sleep(60)
    
    async def _update_performance_metrics(self):
        """Update engine performance metrics"""
        try:
            # Update totals
            self.total_trades = sum(s.trades_executed for s in self.strategies.values())
            self.total_pnl = sum(sum(p.pnl for p in s.positions.values()) for s in self.strategies.values())
            
            # Update signals per minute
            current_time = time.time()
            time_diff = current_time - self.last_performance_update
            
            if time_diff >= 60:  # Update every minute
                total_signals = sum(s.signals_generated for s in self.strategies.values())
                self.signals_per_minute = total_signals / (time_diff / 60)
                self.last_performance_update = current_time
                
        except Exception as e:
            logger.error(f"❌ Error updating performance metrics: {e}")
    
    def get_engine_status(self) -> Dict[str, Any]:
        """Get comprehensive engine status"""
        try:
            active_strategies = sum(1 for s in self.strategies.values() if s.is_active)
            total_positions = sum(len(s.positions) for s in self.strategies.values())
            total_signals = sum(s.signals_generated for s in self.strategies.values())
            
            uptime = None
            if self.start_time:
                uptime = (datetime.now() - self.start_time).total_seconds()
            
            return {
                'is_running': self.is_running,
                'total_strategies': len(self.strategies),
                'active_strategies': active_strategies,
                'total_positions': total_positions,
                'total_trades': self.total_trades,
                'total_pnl': round(self.total_pnl, 2),
                'total_signals': total_signals,
                'signals_per_minute': round(self.signals_per_minute, 1),
                'uptime_seconds': uptime,
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'strategies': {
                    name: strategy.get_portfolio_status()
                    for name, strategy in self.strategies.items()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting engine status: {e}")
            return {'error': str(e)}
    
    def get_strategy(self, strategy_name: str) -> Optional[BaseStrategy]:
        """Get strategy by name"""
        return self.strategies.get(strategy_name)
    
    def get_all_positions(self) -> List[Dict[str, Any]]:
        """Get all positions across all strategies"""
        try:
            all_positions = []
            
            for strategy_name, strategy in self.strategies.items():
                for position in strategy.positions.values():
                    pos_dict = position.to_dict()
                    pos_dict['strategy_name'] = strategy_name
                    all_positions.append(pos_dict)
            
            return all_positions
            
        except Exception as e:
            logger.error(f"❌ Error getting all positions: {e}")
            return []
    
    def force_exit_all_positions(self) -> int:
        """Force exit all positions across all strategies"""
        try:
            positions_closed = 0
            
            for strategy in self.strategies.values():
                for position in list(strategy.positions.values()):
                    strategy._exit_position(position)
                    positions_closed += 1
            
            logger.info(f"🔚 Force closed {positions_closed} positions")
            return positions_closed
            
        except Exception as e:
            logger.error(f"❌ Error force closing positions: {e}")
            return 0


# Global engine instance
_strategy_engine: Optional[RealTimeStrategyEngine] = None

def get_strategy_engine() -> RealTimeStrategyEngine:
    """Get or create global strategy engine instance"""
    global _strategy_engine
    if _strategy_engine is None:
        _strategy_engine = RealTimeStrategyEngine()
    return _strategy_engine

def create_and_start_momentum_strategy(
    strategy_name: str,
    instruments: List[str],
    momentum_threshold: float = 0.02
) -> bool:
    """
    Quick helper to create and start a momentum strategy
    
    Args:
        strategy_name: Name for the strategy
        instruments: List of instrument keys
        momentum_threshold: Momentum threshold (default 2%)
        
    Returns:
        bool: True if successful
    """
    try:
        engine = get_strategy_engine()
        
        # Create momentum strategy
        momentum_strategy = MomentumStrategy(strategy_name, instruments)
        momentum_strategy.momentum_threshold = momentum_threshold
        
        # Register with engine
        success = engine.register_strategy(momentum_strategy)
        
        if success:
            logger.info(f"✅ Momentum strategy '{strategy_name}' created and registered")
            return True
        else:
            logger.error(f"❌ Failed to register momentum strategy '{strategy_name}'")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error creating momentum strategy: {e}")
        return False

def create_and_start_mean_reversion_strategy(
    strategy_name: str,
    instruments: List[str],
    sma_period: int = 20,
    deviation_threshold: float = 2.0
) -> bool:
    """
    Quick helper to create and start a mean reversion strategy
    
    Args:
        strategy_name: Name for the strategy
        instruments: List of instrument keys
        sma_period: SMA period for mean calculation
        deviation_threshold: Standard deviation threshold
        
    Returns:
        bool: True if successful
    """
    try:
        engine = get_strategy_engine()
        
        # Create mean reversion strategy
        mean_reversion_strategy = MeanReversionStrategy(strategy_name, instruments)
        mean_reversion_strategy.sma_period = sma_period
        mean_reversion_strategy.deviation_threshold = deviation_threshold
        
        # Register with engine
        success = engine.register_strategy(mean_reversion_strategy)
        
        if success:
            logger.info(f"✅ Mean reversion strategy '{strategy_name}' created and registered")
            return True
        else:
            logger.error(f"❌ Failed to register mean reversion strategy '{strategy_name}'")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error creating mean reversion strategy: {e}")
        return False


if __name__ == "__main__":
    # Example usage and testing
    async def main():
        logging.basicConfig(level=logging.INFO)
        
        # Create engine
        engine = get_strategy_engine()
        
        # Example instruments (you'd use real instrument keys)
        instruments = [
            "NSE_EQ|INE002A01018",  # Example: Reliance
            "NSE_EQ|INE467B01029"   # Example: TCS
        ]
        
        # Create momentum strategy
        create_and_start_momentum_strategy("momentum_test", instruments, 0.015)
        
        # Create mean reversion strategy  
        create_and_start_mean_reversion_strategy("mean_reversion_test", instruments, 15, 1.5)
        
        # Start engine
        await engine.start()
        
        # Run for a while (in production, this would run continuously)
        await asyncio.sleep(300)  # Run for 5 minutes
        
        # Get status
        status = engine.get_engine_status()
        print(f"📊 Final Engine Status: {json.dumps(status, indent=2)}")
        
        # Stop engine
        await engine.stop()
    
    # Run example
    asyncio.run(main())