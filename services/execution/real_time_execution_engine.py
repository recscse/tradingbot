"""
Real-time Execution Engine for Auto-Trading System
Handles live order placement, position management, and P&L tracking
Optimized for HFT with sub-50ms execution latency
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import json

from services.strategies.fibonacci_ema_strategy import FibonacciEMAStrategy, FibonacciSignal
from services.strategies.dynamic_risk_reward import DynamicRiskReward, PositionSize
from services.database.trading_db_service import TradingDatabaseService
from services.centralized_ws_manager import CentralizedWebSocketManager

logger = logging.getLogger(__name__)

class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    STOP_LIMIT = "STOP_LIMIT"

class OrderStatus(Enum):
    PENDING = "PENDING"
    PLACED = "PLACED"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

class PositionStatus(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PARTIAL = "PARTIAL"

@dataclass
class OrderRequest:
    """Order request structure for execution engine"""
    symbol: str
    instrument_key: str
    order_type: OrderType
    quantity: int
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    strategy_id: str = "FIBONACCI_EMA"
    user_id: Optional[int] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class ExecutionResult:
    """Result of order execution"""
    order_id: str
    status: OrderStatus
    filled_quantity: int
    filled_price: float
    execution_time_ms: float
    error_message: Optional[str] = None
    broker_response: Optional[Dict] = None

@dataclass
class LivePosition:
    """Live trading position with real-time tracking"""
    position_id: str
    symbol: str
    instrument_key: str
    entry_price: float
    quantity: int
    current_price: float
    unrealized_pnl: float
    stop_loss: float
    target: float
    entry_time: datetime
    last_updated: datetime
    status: PositionStatus
    trailing_stop: Optional[float] = None
    max_profit: float = 0.0
    max_drawdown: float = 0.0

class RealTimeExecutionEngine:
    """
    High-performance execution engine for auto-trading
    Features:
    - Sub-50ms order execution
    - Real-time position monitoring
    - Dynamic stop-loss management
    - Circuit breaker protection
    - Comprehensive error handling
    """
    
    def __init__(self, 
                 db_service: TradingDatabaseService,
                 ws_manager: CentralizedWebSocketManager,
                 fibonacci_strategy: FibonacciEMAStrategy,
                 risk_manager: DynamicRiskReward):
        
        self.db_service = db_service
        self.ws_manager = ws_manager
        self.fibonacci_strategy = fibonacci_strategy
        self.risk_manager = risk_manager
        
        # Execution state
        self.active_positions: Dict[str, LivePosition] = {}
        self.pending_orders: Dict[str, OrderRequest] = {}
        self.execution_history: List[ExecutionResult] = []
        
        # Performance tracking
        self.execution_metrics = {
            'total_orders': 0,
            'successful_orders': 0,
            'failed_orders': 0,
            'avg_execution_time_ms': 0.0,
            'total_pnl': 0.0,
            'active_positions_count': 0
        }
        
        # Circuit breaker settings
        self.circuit_breaker = {
            'enabled': True,
            'max_consecutive_failures': 5,
            'consecutive_failures': 0,
            'circuit_open': False,
            'last_failure_time': None,
            'recovery_time_seconds': 300  # 5 minutes
        }
        
        # Execution pool for concurrent operations
        self.executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="execution_")
        
        # Emergency controls
        self.emergency_stop = False
        self.max_daily_loss = 50000.0  # Maximum daily loss limit
        self.daily_loss = 0.0
        
        logger.info("Real-time Execution Engine initialized")

    async def start_execution_engine(self):
        """Start the execution engine with all monitoring tasks"""
        try:
            # Start position monitoring
            asyncio.create_task(self._monitor_positions())
            
            # Start price update handler
            asyncio.create_task(self._handle_price_updates())
            
            # Start metrics updater
            asyncio.create_task(self._update_metrics())
            
            # Start circuit breaker monitor
            asyncio.create_task(self._monitor_circuit_breaker())
            
            logger.info("Execution engine started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start execution engine: {e}")
            raise

    async def process_fibonacci_signal(self, signal: FibonacciSignal, symbol: str, 
                                     current_price: float, user_id: int = None) -> Optional[ExecutionResult]:
        """
        Process Fibonacci signal and execute trades
        Target execution time: < 50ms
        """
        start_time = time.time()
        
        try:
            # Check emergency stop
            if self.emergency_stop:
                logger.warning("Emergency stop active - skipping signal execution")
                return None
            
            # Check circuit breaker
            if self.circuit_breaker['circuit_open']:
                logger.warning("Circuit breaker open - skipping signal execution")
                return None
            
            # Check daily loss limit
            if self.daily_loss >= self.max_daily_loss:
                logger.warning(f"Daily loss limit reached: {self.daily_loss}")
                await self._trigger_emergency_stop("Daily loss limit exceeded")
                return None
            
            # Skip if signal strength is too low
            if signal.strength < 65:
                logger.debug(f"Signal strength too low: {signal.strength}")
                return None
            
            # Calculate position size
            position_size = await self.risk_manager.calculate_position_size(
                signal_strength=signal.strength,
                entry_price=current_price,
                stop_loss=signal.stop_loss,
                option_premium=current_price,
                symbol=symbol
            )
            
            if position_size.lot_size == 0:
                logger.warning("Position size calculated as 0 - skipping trade")
                return None
            
            # Create order request
            order_request = OrderRequest(
                symbol=symbol,
                instrument_key=signal.instrument_key,
                order_type=OrderType.MARKET,  # Market order for fast execution
                quantity=position_size.lot_size,
                stop_loss=signal.stop_loss,
                target=signal.target,
                user_id=user_id,
                strategy_id="FIBONACCI_EMA"
            )
            
            # Execute order
            execution_result = await self._execute_order(order_request)
            
            # Track execution time
            execution_time_ms = (time.time() - start_time) * 1000
            execution_result.execution_time_ms = execution_time_ms
            
            # Log to database
            if execution_result.status == OrderStatus.FILLED:
                await self._create_live_position(order_request, execution_result)
                await self.db_service.log_fibonacci_signal({
                    'symbol': symbol,
                    'signal_type': signal.signal_type,
                    'strength': signal.strength,
                    'entry_price': execution_result.filled_price,
                    'quantity': execution_result.filled_quantity,
                    'stop_loss': signal.stop_loss,
                    'target': signal.target,
                    'execution_time_ms': execution_time_ms,
                    'status': 'EXECUTED'
                }, user_id)
            
            # Update metrics
            self._update_execution_metrics(execution_result)
            
            logger.info(f"Signal processed in {execution_time_ms:.2f}ms - {execution_result.status}")
            return execution_result
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            logger.error(f"Error processing Fibonacci signal: {e} (Time: {execution_time_ms:.2f}ms)")
            self._handle_execution_failure()
            return None

    async def _execute_order(self, order_request: OrderRequest) -> ExecutionResult:
        """Execute order with broker API integration"""
        order_id = f"ORD_{int(time.time() * 1000000)}"
        
        try:
            # Add to pending orders
            self.pending_orders[order_id] = order_request
            
            # Simulate broker API call (replace with actual broker integration)
            # This is where you'd integrate with Upstox/Angel One/Dhan APIs
            await asyncio.sleep(0.01)  # Simulate network latency
            
            # Mock execution result (replace with actual broker response)
            filled_price = order_request.price if order_request.price else self._get_market_price(order_request.symbol)
            
            execution_result = ExecutionResult(
                order_id=order_id,
                status=OrderStatus.FILLED,
                filled_quantity=order_request.quantity,
                filled_price=filled_price,
                execution_time_ms=0.0,  # Will be set by caller
                broker_response={'mock': True, 'order_id': order_id}
            )
            
            # Remove from pending
            self.pending_orders.pop(order_id, None)
            
            return execution_result
            
        except Exception as e:
            logger.error(f"Order execution failed: {e}")
            self.pending_orders.pop(order_id, None)
            
            return ExecutionResult(
                order_id=order_id,
                status=OrderStatus.REJECTED,
                filled_quantity=0,
                filled_price=0.0,
                execution_time_ms=0.0,
                error_message=str(e)
            )

    async def _create_live_position(self, order_request: OrderRequest, execution_result: ExecutionResult):
        """Create and track live position"""
        position_id = f"POS_{order_request.symbol}_{int(time.time())}"
        
        position = LivePosition(
            position_id=position_id,
            symbol=order_request.symbol,
            instrument_key=order_request.instrument_key,
            entry_price=execution_result.filled_price,
            quantity=execution_result.filled_quantity,
            current_price=execution_result.filled_price,
            unrealized_pnl=0.0,
            stop_loss=order_request.stop_loss,
            target=order_request.target,
            entry_time=datetime.now(timezone.utc),
            last_updated=datetime.now(timezone.utc),
            status=PositionStatus.OPEN
        )
        
        self.active_positions[position_id] = position
        
        # Log to database
        await self.db_service.create_auto_trade_execution({
            'symbol': order_request.symbol,
            'instrument_key': order_request.instrument_key,
            'entry_price': execution_result.filled_price,
            'quantity': execution_result.filled_quantity,
            'stop_loss': order_request.stop_loss,
            'target': order_request.target,
            'strategy_used': order_request.strategy_id,
            'execution_latency_ms': execution_result.execution_time_ms,
            'status': 'ACTIVE'
        }, order_request.user_id)
        
        logger.info(f"Created live position: {position_id}")

    async def _monitor_positions(self):
        """Monitor active positions and manage stop-loss/targets"""
        while not self.emergency_stop:
            try:
                for position_id, position in list(self.active_positions.items()):
                    # Update current price
                    current_price = self._get_market_price(position.symbol)
                    position.current_price = current_price
                    
                    # Calculate unrealized P&L
                    position.unrealized_pnl = (current_price - position.entry_price) * position.quantity
                    
                    # Update max profit/drawdown
                    if position.unrealized_pnl > position.max_profit:
                        position.max_profit = position.unrealized_pnl
                    
                    drawdown = position.max_profit - position.unrealized_pnl
                    if drawdown > position.max_drawdown:
                        position.max_drawdown = drawdown
                    
                    # Check stop-loss
                    if current_price <= position.stop_loss:
                        await self._close_position(position, "STOP_LOSS")
                        continue
                    
                    # Check target
                    if current_price >= position.target:
                        await self._close_position(position, "TARGET")
                        continue
                    
                    # Update trailing stop if applicable
                    if position.trailing_stop:
                        new_trailing_stop = current_price * 0.98  # 2% trailing stop
                        if new_trailing_stop > position.trailing_stop:
                            position.trailing_stop = new_trailing_stop
                            logger.debug(f"Updated trailing stop for {position_id}: {new_trailing_stop}")
                    
                    position.last_updated = datetime.now(timezone.utc)
                
                # Update database
                await self._update_positions_in_db()
                
                await asyncio.sleep(0.1)  # 100ms monitoring cycle
                
            except Exception as e:
                logger.error(f"Error in position monitoring: {e}")
                await asyncio.sleep(1.0)

    async def _close_position(self, position: LivePosition, reason: str):
        """Close position and calculate final P&L"""
        try:
            # Execute closing order (replace with actual broker API)
            closing_price = position.current_price
            final_pnl = (closing_price - position.entry_price) * position.quantity
            
            # Update position status
            position.status = PositionStatus.CLOSED
            position.unrealized_pnl = final_pnl
            
            # Update daily P&L
            self.daily_loss += abs(final_pnl) if final_pnl < 0 else 0
            
            # Remove from active positions
            self.active_positions.pop(position.position_id, None)
            
            # Log closing
            await self.db_service.update_auto_trade_execution(position.position_id, {
                'exit_price': closing_price,
                'actual_pnl': final_pnl,
                'exit_reason': reason,
                'status': 'CLOSED',
                'max_profit_achieved': position.max_profit,
                'max_drawdown': position.max_drawdown
            })
            
            logger.info(f"Closed position {position.position_id}: {reason}, P&L: {final_pnl:.2f}")
            
        except Exception as e:
            logger.error(f"Error closing position {position.position_id}: {e}")

    def _get_market_price(self, symbol: str) -> float:
        """Get current market price for symbol"""
        # This should integrate with your centralized WebSocket manager
        # For now, returning a mock price
        return 100.0 + (time.time() % 10)  # Mock price variation

    async def _handle_price_updates(self):
        """Handle real-time price updates from WebSocket"""
        while not self.emergency_stop:
            try:
                # This should listen to price updates from centralized_ws_manager
                # and update position prices in real-time
                await asyncio.sleep(0.05)  # 50ms price update cycle
                
            except Exception as e:
                logger.error(f"Error handling price updates: {e}")
                await asyncio.sleep(1.0)

    async def _update_metrics(self):
        """Update execution metrics periodically"""
        while not self.emergency_stop:
            try:
                self.execution_metrics['active_positions_count'] = len(self.active_positions)
                self.execution_metrics['total_pnl'] = sum(
                    pos.unrealized_pnl for pos in self.active_positions.values()
                )
                
                await asyncio.sleep(5.0)  # Update every 5 seconds
                
            except Exception as e:
                logger.error(f"Error updating metrics: {e}")
                await asyncio.sleep(10.0)

    async def _monitor_circuit_breaker(self):
        """Monitor and manage circuit breaker"""
        while not self.emergency_stop:
            try:
                if self.circuit_breaker['circuit_open']:
                    # Check if recovery time has passed
                    if (self.circuit_breaker['last_failure_time'] and 
                        time.time() - self.circuit_breaker['last_failure_time'] > 
                        self.circuit_breaker['recovery_time_seconds']):
                        
                        self.circuit_breaker['circuit_open'] = False
                        self.circuit_breaker['consecutive_failures'] = 0
                        logger.info("Circuit breaker reset - resuming operations")
                
                await asyncio.sleep(30.0)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in circuit breaker monitor: {e}")
                await asyncio.sleep(60.0)

    def _update_execution_metrics(self, result: ExecutionResult):
        """Update execution metrics"""
        self.execution_metrics['total_orders'] += 1
        
        if result.status == OrderStatus.FILLED:
            self.execution_metrics['successful_orders'] += 1
        else:
            self.execution_metrics['failed_orders'] += 1
        
        # Update average execution time
        total_time = (self.execution_metrics['avg_execution_time_ms'] * 
                     (self.execution_metrics['total_orders'] - 1) + 
                     result.execution_time_ms)
        self.execution_metrics['avg_execution_time_ms'] = total_time / self.execution_metrics['total_orders']

    def _handle_execution_failure(self):
        """Handle execution failure and update circuit breaker"""
        self.circuit_breaker['consecutive_failures'] += 1
        self.circuit_breaker['last_failure_time'] = time.time()
        
        if (self.circuit_breaker['consecutive_failures'] >= 
            self.circuit_breaker['max_consecutive_failures']):
            self.circuit_breaker['circuit_open'] = True
            logger.warning("Circuit breaker opened due to consecutive failures")

    async def _trigger_emergency_stop(self, reason: str):
        """Trigger emergency stop and close all positions"""
        logger.critical(f"EMERGENCY STOP TRIGGERED: {reason}")
        self.emergency_stop = True
        
        # Close all active positions
        for position in list(self.active_positions.values()):
            await self._close_position(position, f"EMERGENCY_STOP: {reason}")
        
        # Log emergency stop
        await self.db_service.log_trading_system_event({
            'event_type': 'EMERGENCY_STOP',
            'description': reason,
            'active_positions_closed': len(self.active_positions)
        })

    async def _update_positions_in_db(self):
        """Update position data in database"""
        try:
            for position in self.active_positions.values():
                await self.db_service.update_live_position_price(
                    position.instrument_key,
                    position.current_price
                )
        except Exception as e:
            logger.error(f"Error updating positions in database: {e}")

    def get_execution_status(self) -> Dict[str, Any]:
        """Get current execution engine status"""
        return {
            'engine_status': 'ACTIVE' if not self.emergency_stop else 'EMERGENCY_STOP',
            'circuit_breaker_open': self.circuit_breaker['circuit_open'],
            'active_positions': len(self.active_positions),
            'pending_orders': len(self.pending_orders),
            'daily_loss': self.daily_loss,
            'metrics': self.execution_metrics,
            'positions': [
                {
                    'symbol': pos.symbol,
                    'entry_price': pos.entry_price,
                    'current_price': pos.current_price,
                    'unrealized_pnl': pos.unrealized_pnl,
                    'quantity': pos.quantity
                }
                for pos in self.active_positions.values()
            ]
        }

    async def shutdown(self):
        """Graceful shutdown of execution engine"""
        logger.info("Shutting down execution engine...")
        self.emergency_stop = True
        
        # Close all positions
        for position in list(self.active_positions.values()):
            await self._close_position(position, "SYSTEM_SHUTDOWN")
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        logger.info("Execution engine shutdown complete")