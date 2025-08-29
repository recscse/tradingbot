"""
Auto-Trading Coordinator Service
Main orchestrator for the complete auto-trading system
Integrates all components: Strategy, Execution, Risk Management, Monitoring
"""

import asyncio
import logging
import time
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import pandas as pd
from contextlib import asynccontextmanager

from services.strategies.fibonacci_ema_strategy import FibonacciEMAStrategy, FibonacciSignal
from services.strategies.dynamic_risk_reward import DynamicRiskReward
from services.strategies.nifty_09_40_integration import get_nifty_strategy_integration, initialize_nifty_strategy
from services.execution.real_time_execution_engine import RealTimeExecutionEngine
from services.execution.broker_integration_manager import BrokerIntegrationManager, BrokerType
from services.execution.position_monitor import PositionMonitor
from services.execution.order_management_system import OrderManagementSystem
from services.unified_trading_executor import unified_trading_executor, UnifiedTradeSignal, TradingMode
from services.auto_stock_selection_service import AutoStockSelectionService
from services.auto_trading_data_service import AutoTradingDataService
from services.database.trading_db_service import TradingDatabaseService
from services.centralized_ws_manager import CentralizedWebSocketManager

logger = logging.getLogger(__name__)

class TradingSystemState(Enum):
    INACTIVE = "INACTIVE"
    INITIALIZING = "INITIALIZING"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    EMERGENCY_STOP = "EMERGENCY_STOP"
    SHUTTING_DOWN = "SHUTTING_DOWN"

class SystemMode(Enum):
    PAPER_TRADING = "PAPER_TRADING"
    LIVE_TRADING = "LIVE_TRADING"
    BACKTEST = "BACKTEST"

@dataclass
class TradingSession:
    """Trading session configuration and state"""
    session_id: str
    user_id: int
    mode: SystemMode
    selected_stocks: List[Dict[str, Any]]
    risk_parameters: Dict[str, Any]
    strategy_config: Dict[str, Any]
    max_positions: int = 5
    max_daily_loss: float = 50000.0
    session_start_time: datetime = None
    session_end_time: Optional[datetime] = None
    total_pnl: float = 0.0
    trades_count: int = 0

@dataclass
class SystemHealth:
    """System health monitoring"""
    overall_status: str = "HEALTHY"
    data_feed_status: str = "CONNECTED"
    broker_status: str = "CONNECTED"
    strategy_status: str = "ACTIVE"
    execution_status: str = "ACTIVE"
    database_status: str = "CONNECTED"
    last_health_check: datetime = None
    error_count_24h: int = 0
    uptime_seconds: int = 0

class AutoTradingCoordinator:
    """
    Main Auto-Trading System Coordinator
    
    Orchestrates the complete auto-trading workflow:
    1. Market data ingestion and processing
    2. F&O stock selection and filtering
    3. Fibonacci + EMA strategy signal generation
    4. Risk management and position sizing
    5. Order execution and management
    6. Real-time position monitoring
    7. Performance tracking and reporting
    8. Emergency controls and kill switch
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.system_state = TradingSystemState.INACTIVE
        self.system_health = SystemHealth()
        self.start_time = datetime.now(timezone.utc)
        
        # Core services - will be initialized later
        self.db_service: Optional[TradingDatabaseService] = None
        self.ws_manager: Optional[CentralizedWebSocketManager] = None
        self.data_service: Optional[AutoTradingDataService] = None
        self.stock_selection_service: Optional[AutoStockSelectionService] = None
        self.fibonacci_strategy: Optional[FibonacciEMAStrategy] = None
        self.risk_manager: Optional[DynamicRiskReward] = None
        self.broker_manager: Optional[BrokerIntegrationManager] = None
        self.execution_engine: Optional[RealTimeExecutionEngine] = None
        self.position_monitor: Optional[PositionMonitor] = None
        self.order_manager: Optional[OrderManagementSystem] = None
        
        # Session management
        self.active_sessions: Dict[str, TradingSession] = {}
        self.system_metrics = {
            'total_trades_today': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'total_pnl_today': 0.0,
            'active_positions': 0,
            'signals_generated': 0,
            'signals_executed': 0,
            'avg_execution_time_ms': 0.0,
            'uptime_percentage': 100.0
        }
        
        # Control flags
        self.emergency_stop_active = False
        self.daily_loss_limit_hit = False
        self.max_positions_reached = False
        
        # Callbacks for UI updates
        self.status_callbacks: List[Callable] = []
        self.trade_callbacks: List[Callable] = []
        self.error_callbacks: List[Callable] = []
        
        logger.info("Auto-Trading Coordinator initialized")
    
    async def initialize_system(self) -> bool:
        """Initialize all system components"""
        try:
            self.system_state = TradingSystemState.INITIALIZING
            logger.info("Initializing Auto-Trading System...")
            
            # Initialize database service
            self.db_service = TradingDatabaseService()
            await self.db_service.initialize()
            
            # Initialize WebSocket manager
            self.ws_manager = CentralizedWebSocketManager()
            await self.ws_manager.initialize()
            
            # Initialize data processing service
            self.data_service = AutoTradingDataService()
            await self.data_service.initialize()
            
            # Initialize stock selection service
            self.stock_selection_service = AutoStockSelectionService(self.db_service)
            
            # Initialize strategy components
            self.fibonacci_strategy = FibonacciEMAStrategy()
            self.risk_manager = DynamicRiskReward()
            
            # Initialize NIFTY 09:40 strategy
            from services.websocket.auto_trading_websocket import get_websocket_manager
            websocket_manager = await get_websocket_manager()
            await initialize_nifty_strategy(websocket_manager)
            self.nifty_strategy = await get_nifty_strategy_integration()
            
            # Initialize broker integration
            self.broker_manager = BrokerIntegrationManager()
            await self._setup_brokers()
            
            # Initialize position monitor
            self.position_monitor = PositionMonitor(self.db_service, self.ws_manager)
            await self.position_monitor.start_monitoring()
            
            # Initialize order management system
            self.order_manager = OrderManagementSystem(
                self.broker_manager, 
                self.db_service, 
                self.position_monitor
            )
            await self.order_manager.start_system()
            
            # Initialize execution engine
            self.execution_engine = RealTimeExecutionEngine(
                self.db_service,
                self.ws_manager,
                self.fibonacci_strategy,
                self.risk_manager
            )
            await self.execution_engine.start_execution_engine()
            
            # Setup event callbacks
            await self._setup_callbacks()
            
            # Start system monitoring
            asyncio.create_task(self._system_health_monitor())
            asyncio.create_task(self._market_data_processor())
            asyncio.create_task(self._signal_generator())
            asyncio.create_task(self._performance_tracker())
            
            self.system_state = TradingSystemState.ACTIVE
            logger.info("Auto-Trading System initialized successfully")
            
            await self._notify_system_status("SYSTEM_INITIALIZED")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Auto-Trading System: {e}")
            self.system_state = TradingSystemState.INACTIVE
            await self._notify_error("INITIALIZATION_FAILED", str(e))
            return False
    
    async def _setup_brokers(self):
        """Setup broker connections"""
        try:
            # Add configured brokers
            broker_configs = self.config.get('brokers', {})
            
            for broker_name, credentials in broker_configs.items():
                if broker_name.upper() == 'UPSTOX':
                    await self.broker_manager.add_broker(BrokerType.UPSTOX, credentials)
                elif broker_name.upper() == 'ANGEL_ONE':
                    await self.broker_manager.add_broker(BrokerType.ANGEL_ONE, credentials)
                # Add more brokers as needed
            
            logger.info("Broker connections established")
            
        except Exception as e:
            logger.error(f"Failed to setup brokers: {e}")
            raise
    
    async def _setup_callbacks(self):
        """Setup inter-service callbacks"""
        try:
            # Position monitor callbacks
            self.position_monitor.add_position_callback(self._handle_position_update)
            self.position_monitor.add_risk_callback(self._handle_risk_limit_breach)
            
            # Order manager callbacks
            self.order_manager.add_order_callback(self._handle_order_event)
            
            # Data service callbacks
            await self.data_service.register_fibonacci_callback(
                "MAIN_STRATEGY", 
                self._handle_fibonacci_signal
            )
            
            logger.info("Inter-service callbacks configured")
            
        except Exception as e:
            logger.error(f"Failed to setup callbacks: {e}")
            raise
    
    async def start_trading_session(self, session_config: Dict[str, Any]) -> str:
        """Start a new trading session"""
        try:
            session_id = f"SESSION_{int(time.time() * 1000)}"
            
            # Validate session config
            if not self._validate_session_config(session_config):
                raise ValueError("Invalid session configuration")
            
            # Create trading session
            session = TradingSession(
                session_id=session_id,
                user_id=session_config['user_id'],
                mode=SystemMode(session_config.get('mode', 'PAPER_TRADING')),
                selected_stocks=session_config.get('selected_stocks', []),
                risk_parameters=session_config.get('risk_parameters', {}),
                strategy_config=session_config.get('strategy_config', {}),
                max_positions=session_config.get('max_positions', 5),
                max_daily_loss=session_config.get('max_daily_loss', 50000.0),
                session_start_time=datetime.now(timezone.utc)
            )
            
            self.active_sessions[session_id] = session
            
            # Initialize session-specific components
            await self._initialize_session_components(session)
            
            # Start stock selection if not provided
            if not session.selected_stocks:
                session.selected_stocks = await self._select_trading_stocks(session)
            
            # Subscribe to market data for selected stocks
            await self._subscribe_to_market_data(session.selected_stocks)
            
            logger.info(f"Trading session started: {session_id} with {len(session.selected_stocks)} stocks")
            
            await self._notify_session_event("SESSION_STARTED", session_id)
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to start trading session: {e}")
            await self._notify_error("SESSION_START_FAILED", str(e))
            raise
    
    async def _select_trading_stocks(self, session: TradingSession) -> List[Dict[str, Any]]:
        """Select F&O stocks for trading based on Fibonacci strategy suitability"""
        try:
            # Get F&O stock universe
            fno_stocks = await self.stock_selection_service.get_fno_stocks_from_indices()
            
            # Score stocks for Fibonacci strategy
            scored_stocks = await self.stock_selection_service.score_fno_stocks_for_fibonacci_strategy(fno_stocks)
            
            # Select top stocks
            max_stocks = session.strategy_config.get('max_stocks', 20)
            selected = scored_stocks[:max_stocks]
            
            logger.info(f"Selected {len(selected)} stocks for trading")
            return selected
            
        except Exception as e:
            logger.error(f"Error selecting trading stocks: {e}")
            return []
    
    async def _subscribe_to_market_data(self, selected_stocks: List[Dict[str, Any]]):
        """Subscribe to real-time market data for selected stocks"""
        try:
            instrument_keys = [stock['instrument_key'] for stock in selected_stocks]
            
            # Priority subscription for selected stocks
            await self.ws_manager.priority_subscription(selected_stocks)
            
            logger.info(f"Subscribed to market data for {len(instrument_keys)} instruments")
            
        except Exception as e:
            logger.error(f"Error subscribing to market data: {e}")
    
    async def _market_data_processor(self):
        """Main market data processing loop"""
        while self.system_state in [TradingSystemState.ACTIVE, TradingSystemState.PAUSED]:
            try:
                if self.system_state == TradingSystemState.PAUSED:
                    await asyncio.sleep(1.0)
                    continue
                
                # Process incoming market data
                await self.data_service.process_market_data_batch()
                
                await asyncio.sleep(0.1)  # 100ms processing cycle
                
            except Exception as e:
                logger.error(f"Error in market data processing: {e}")
                await asyncio.sleep(1.0)
    
    async def _signal_generator(self):
        """Main signal generation loop"""
        while self.system_state in [TradingSystemState.ACTIVE, TradingSystemState.PAUSED]:
            try:
                if self.system_state == TradingSystemState.PAUSED:
                    await asyncio.sleep(1.0)
                    continue
                
                # Generate signals for all active sessions
                for session in self.active_sessions.values():
                    await self._generate_session_signals(session)
                
                await asyncio.sleep(5.0)  # 5-second signal generation cycle
                
            except Exception as e:
                logger.error(f"Error in signal generation: {e}")
                await asyncio.sleep(10.0)
    
    async def _generate_session_signals(self, session: TradingSession):
        """Generate trading signals for a session"""
        try:
            if self.emergency_stop_active or self.daily_loss_limit_hit:
                return
            
            for stock in session.selected_stocks:
                symbol = stock['symbol']
                instrument_key = stock['instrument_key']
                
                # Get current market data
                current_price = await self.data_service.get_current_price(instrument_key)
                if not current_price:
                    continue
                
                # Get OHLC data for strategy
                ohlc_1m = await self.data_service.get_ohlc_data(instrument_key, '1m', 100)
                ohlc_5m = await self.data_service.get_ohlc_data(instrument_key, '5m', 50)
                
                if ohlc_1m.empty or ohlc_5m.empty:
                    continue
                
                # Generate Fibonacci signal
                signal = await self.fibonacci_strategy.generate_signal(
                    ohlc_1m, ohlc_5m, current_price, symbol
                )
                
                if signal and signal.strength >= 70:  # High-confidence signals only
                    self.system_metrics['signals_generated'] += 1
                    
                    # Check if we can execute the signal
                    if await self._can_execute_signal(session, signal):
                        await self._execute_fibonacci_signal(session, signal, symbol, current_price)
                
        except Exception as e:
            logger.error(f"Error generating session signals: {e}")
    
    async def _can_execute_signal(self, session: TradingSession, signal: FibonacciSignal) -> bool:
        """Check if signal can be executed based on risk limits"""
        # Check max positions limit
        active_positions = len([pos for pos in self.position_monitor.positions.values() 
                              if pos.status.value == 'ACTIVE'])
        
        if active_positions >= session.max_positions:
            return False
        
        # Check daily loss limit
        if abs(session.total_pnl) >= session.max_daily_loss and session.total_pnl < 0:
            return False
        
        # Check emergency stop
        if self.emergency_stop_active:
            return False
        
        return True
    
    async def _execute_fibonacci_signal(self, session: TradingSession, signal: FibonacciSignal, 
                                      symbol: str, current_price: float):
        """Execute Fibonacci trading signal using unified executor"""
        try:
            # Determine trading mode based on session
            trading_mode = TradingMode.PAPER if session.mode == SystemMode.PAPER_TRADING else TradingMode.LIVE
            
            # Calculate position size and option details
            position_size, lot_size = await self._calculate_position_size(session, signal, current_price)
            
            # Get option contract details for the signal
            option_details = await self._resolve_option_contract(
                symbol, signal.option_type, current_price, signal.fibonacci_level
            )
            
            if not option_details:
                logger.warning(f"Could not resolve option contract for {symbol}")
                return
            
            # Create unified trade signal
            unified_signal = UnifiedTradeSignal(
                user_id=session.user_id,
                symbol=symbol,
                instrument_key=option_details["instrument_key"],
                option_type=signal.option_type,
                strike_price=option_details["strike_price"],
                signal_type="BUY",  # Always buying options
                entry_price=current_price,
                quantity=position_size,
                lot_size=lot_size,
                invested_amount=position_size * current_price,
                stop_loss=signal.stop_loss,
                target=signal.target_1,  # Use first target
                confidence_score=signal.strength / 100.0,
                strategy_name="fibonacci_ema",
                trading_mode=trading_mode
            )
            
            # Execute through unified executor
            result = await unified_trading_executor.execute_trade_signal(unified_signal)
            
            if result.success:
                self.system_metrics['signals_executed'] += 1
                self.system_metrics['successful_trades'] += 1
                session.trades_count += 1
                
                logger.info(f"✅ Signal executed successfully for {symbol}: {signal.signal_type} ({trading_mode.value})")
                
                # Emit real-time updates
                await self._emit_execution_updates(session, signal, symbol, result, trading_mode)
                
                await self._notify_trade_event("SIGNAL_EXECUTED", {
                    'session_id': session.session_id,
                    'symbol': symbol,
                    'signal_type': signal.signal_type,
                    'strength': signal.strength,
                    'trading_mode': trading_mode.value,
                    'execution_result': {
                        'trade_id': result.trade_id,
                        'success': result.success,
                        'execution_price': result.execution_price,
                        'invested_amount': unified_signal.invested_amount
                    }
                })
            else:
                self.system_metrics['failed_trades'] += 1
                logger.warning(f"❌ Signal execution failed for {symbol}: {result.error_message}")
            
        except Exception as e:
            logger.error(f"❌ Error executing Fibonacci signal for {symbol}: {e}")
            self.system_metrics['failed_trades'] += 1
    
    async def _handle_fibonacci_signal(self, instrument_key: str, signal_data: Dict[str, Any]):
        """Handle Fibonacci signal from data service"""
        try:
            # This is called by the data service when a signal is detected
            symbol = signal_data.get('symbol', '')
            current_price = signal_data.get('current_price', 0.0)
            
            # Find relevant session and process signal
            for session in self.active_sessions.values():
                if any(stock['instrument_key'] == instrument_key for stock in session.selected_stocks):
                    # Create signal object
                    signal = FibonacciSignal(
                        signal_type=signal_data['signal_type'],
                        strength=signal_data['strength'],
                        instrument_key=instrument_key,
                        stop_loss=signal_data['stop_loss'],
                        target=signal_data['target']
                    )
                    
                    if await self._can_execute_signal(session, signal):
                        await self._execute_fibonacci_signal(session, signal, symbol, current_price)
                    
                    break
            
        except Exception as e:
            logger.error(f"Error handling Fibonacci signal: {e}")
    
    async def _handle_position_update(self, event_type: str, position_data: Any):
        """Handle position updates from position monitor"""
        try:
            if event_type == "POSITION_CLOSED":
                # Update session metrics
                for session in self.active_sessions.values():
                    # Update total P&L (would need position details to match session)
                    pass
            
            await self._notify_position_event(event_type, position_data)
            
        except Exception as e:
            logger.error(f"Error handling position update: {e}")
    
    async def _handle_risk_limit_breach(self, limit_type: str, current_value: float):
        """Handle risk limit breaches"""
        try:
            logger.critical(f"Risk limit breach: {limit_type} = {current_value}")
            
            if limit_type == "DAILY_LOSS":
                self.daily_loss_limit_hit = True
                await self.pause_trading()
            elif limit_type == "PORTFOLIO_HEAT":
                await self.pause_trading()
            
            await self._notify_risk_event("RISK_LIMIT_BREACH", {
                'limit_type': limit_type,
                'current_value': current_value,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error handling risk limit breach: {e}")
    
    async def _handle_order_event(self, event_type: str, order_id: str, order_data: Dict[str, Any]):
        """Handle order events from order manager"""
        try:
            await self._notify_order_event(event_type, {
                'order_id': order_id,
                'data': order_data,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error handling order event: {e}")
    
    async def _system_health_monitor(self):
        """Monitor system health"""
        while self.system_state != TradingSystemState.SHUTTING_DOWN:
            try:
                # Update system health
                self.system_health.last_health_check = datetime.now(timezone.utc)
                self.system_health.uptime_seconds = int(
                    (datetime.now(timezone.utc) - self.start_time).total_seconds()
                )
                
                # Check component health
                broker_health = self.broker_manager.get_broker_health() if self.broker_manager else {}
                
                # Update health status
                if all(status.get('status') == 'HEALTHY' for status in broker_health.values()):
                    self.system_health.broker_status = "CONNECTED"
                else:
                    self.system_health.broker_status = "DEGRADED"
                
                await asyncio.sleep(30.0)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in system health monitor: {e}")
                await asyncio.sleep(60.0)
    
    async def _performance_tracker(self):
        """Track system performance metrics"""
        while self.system_state != TradingSystemState.SHUTTING_DOWN:
            try:
                # Update system metrics
                if self.position_monitor:
                    position_summary = self.position_monitor.get_position_summary()
                    self.system_metrics['active_positions'] = position_summary['active_positions']
                    self.system_metrics['total_pnl_today'] = position_summary['portfolio_metrics']['total_pnl']
                
                if self.order_manager:
                    order_stats = self.order_manager.get_system_status()
                    self.system_metrics['avg_execution_time_ms'] = order_stats['statistics'].get('avg_execution_time_ms', 0.0)
                
                # Calculate success rates
                total_trades = self.system_metrics['successful_trades'] + self.system_metrics['failed_trades']
                if total_trades > 0:
                    success_rate = self.system_metrics['successful_trades'] / total_trades * 100
                    self.system_metrics['success_rate'] = success_rate
                
                await asyncio.sleep(10.0)  # Update every 10 seconds
                
            except Exception as e:
                logger.error(f"Error tracking performance: {e}")
                await asyncio.sleep(30.0)
    
    async def emergency_stop(self, reason: str = "Manual emergency stop"):
        """Trigger emergency stop"""
        try:
            logger.critical(f"EMERGENCY STOP TRIGGERED: {reason}")
            self.system_state = TradingSystemState.EMERGENCY_STOP
            self.emergency_stop_active = True
            
            # Stop execution engine
            if self.execution_engine:
                await self.execution_engine._trigger_emergency_stop(reason)
            
            # Cancel all pending orders
            if self.order_manager:
                for order_id in list(self.order_manager.active_orders.keys()):
                    await self.order_manager.cancel_order(order_id)
            
            # Close all positions
            if self.position_monitor:
                await self.position_monitor.shutdown()
            
            await self._notify_system_status("EMERGENCY_STOP_ACTIVATED")
            
        except Exception as e:
            logger.error(f"Error during emergency stop: {e}")
    
    async def pause_trading(self):
        """Pause trading operations"""
        try:
            self.system_state = TradingSystemState.PAUSED
            logger.info("Trading operations paused")
            
            await self._notify_system_status("TRADING_PAUSED")
            
        except Exception as e:
            logger.error(f"Error pausing trading: {e}")
    
    async def resume_trading(self):
        """Resume trading operations"""
        try:
            if self.system_state == TradingSystemState.PAUSED:
                self.system_state = TradingSystemState.ACTIVE
                self.daily_loss_limit_hit = False
                logger.info("Trading operations resumed")
                
                await self._notify_system_status("TRADING_RESUMED")
            
        except Exception as e:
            logger.error(f"Error resuming trading: {e}")
    
    def _validate_session_config(self, config: Dict[str, Any]) -> bool:
        """Validate trading session configuration"""
        required_fields = ['user_id']
        return all(field in config for field in required_fields)
    
    async def _initialize_session_components(self, session: TradingSession):
        """Initialize session-specific components"""
        # Configure risk parameters
        if self.risk_manager and session.risk_parameters:
            # Apply session-specific risk parameters
            pass
        
        # Configure strategy parameters
        if self.fibonacci_strategy and session.strategy_config:
            # Apply session-specific strategy parameters
            pass
    
    async def _calculate_position_size(self, session: TradingSession, signal: FibonacciSignal, 
                                     current_price: float) -> tuple[int, int]:
        """Calculate position size and lot size for the signal"""
        try:
            # Default lot size for F&O
            lot_size = 50  # This should be retrieved from instrument master
            
            # Calculate position size based on risk management
            capital = session.risk_parameters.get('allocated_capital', 100000)  # Default ₹1L
            risk_per_trade = session.risk_parameters.get('risk_per_trade', 2.0)  # 2%
            
            max_loss_per_trade = capital * (risk_per_trade / 100)
            
            # Assuming 30% stop loss on options
            stop_loss_amount = current_price * 0.30
            
            if stop_loss_amount > 0:
                max_lots = int(max_loss_per_trade / (stop_loss_amount * lot_size))
                lots = max(1, min(max_lots, 2))  # Minimum 1, maximum 2 lots
            else:
                lots = 1
            
            position_size = lots * lot_size
            return position_size, lot_size
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 50, 50  # Default fallback
    
    async def _resolve_option_contract(self, symbol: str, option_type: str, 
                                     current_price: float, fibonacci_level: str) -> Optional[Dict]:
        """Resolve option contract details"""
        try:
            # This would typically use option service to get ATM contract
            # For now, return mock data structure
            strike_price = int(current_price / 50) * 50  # Round to nearest 50
            
            return {
                "instrument_key": f"{symbol}_{option_type}_{strike_price}",
                "strike_price": strike_price,
                "expiry_date": "2024-01-25",  # Weekly expiry
                "lot_size": 50
            }
            
        except Exception as e:
            logger.error(f"Error resolving option contract: {e}")
            return None
    
    async def _emit_execution_updates(self, session: TradingSession, signal: FibonacciSignal,
                                    symbol: str, result, trading_mode: TradingMode):
        """Emit real-time execution updates"""
        try:
            # Emit through WebSocket manager if available
            if hasattr(self, 'ws_manager') and self.ws_manager:
                update_data = {
                    'type': 'fibonacci_signal_executed',
                    'session_id': session.session_id,
                    'symbol': symbol,
                    'signal_type': signal.signal_type,
                    'strength': signal.strength,
                    'trading_mode': trading_mode.value,
                    'entry_price': result.execution_price,
                    'stop_loss': signal.stop_loss,
                    'target': signal.target_1,
                    'trade_id': result.trade_id,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                # Emit to all connected clients
                await self.ws_manager.broadcast_to_all(update_data)
            
        except Exception as e:
            logger.error(f"Error emitting execution updates: {e}")
    
    # Notification methods
    async def _notify_system_status(self, status: str):
        """Notify system status change"""
        for callback in self.status_callbacks:
            try:
                await callback("SYSTEM_STATUS", {
                    'status': status,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'system_state': self.system_state.value
                })
            except Exception as e:
                logger.error(f"Error in status callback: {e}")
    
    async def _notify_trade_event(self, event_type: str, data: Dict[str, Any]):
        """Notify trade events"""
        for callback in self.trade_callbacks:
            try:
                await callback(event_type, data)
            except Exception as e:
                logger.error(f"Error in trade callback: {e}")
    
    async def _notify_position_event(self, event_type: str, data: Any):
        """Notify position events"""
        pass  # Implementation depends on UI requirements
    
    async def _notify_order_event(self, event_type: str, data: Dict[str, Any]):
        """Notify order events"""
        pass  # Implementation depends on UI requirements
    
    async def _notify_risk_event(self, event_type: str, data: Dict[str, Any]):
        """Notify risk events"""
        pass  # Implementation depends on UI requirements
    
    async def _notify_session_event(self, event_type: str, session_id: str):
        """Notify session events"""
        pass  # Implementation depends on UI requirements
    
    async def _notify_error(self, error_type: str, message: str):
        """Notify errors"""
        for callback in self.error_callbacks:
            try:
                await callback(error_type, {
                    'message': message,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            except Exception as e:
                logger.error(f"Error in error callback: {e}")
    
    # Public API methods
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            'system_state': self.system_state.value,
            'system_health': asdict(self.system_health),
            'system_metrics': self.system_metrics.copy(),
            'active_sessions': len(self.active_sessions),
            'emergency_stop_active': self.emergency_stop_active,
            'daily_loss_limit_hit': self.daily_loss_limit_hit,
            'uptime_seconds': self.system_health.uptime_seconds
        }
    
    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get trading session status"""
        session = self.active_sessions.get(session_id)
        if not session:
            return None
        
        return asdict(session)
    
    def add_status_callback(self, callback: Callable):
        """Add system status callback"""
        self.status_callbacks.append(callback)
    
    def add_trade_callback(self, callback: Callable):
        """Add trade event callback"""
        self.trade_callbacks.append(callback)
    
    def add_error_callback(self, callback: Callable):
        """Add error callback"""
        self.error_callbacks.append(callback)
    
    async def shutdown(self):
        """Graceful system shutdown"""
        try:
            logger.info("Shutting down Auto-Trading System...")
            self.system_state = TradingSystemState.SHUTTING_DOWN
            
            # Close all active sessions
            for session_id in list(self.active_sessions.keys()):
                await self.stop_trading_session(session_id)
            
            # Shutdown components in reverse order
            if self.execution_engine:
                await self.execution_engine.shutdown()
            
            if self.order_manager:
                await self.order_manager.shutdown()
            
            if self.position_monitor:
                await self.position_monitor.shutdown()
            
            if self.broker_manager:
                await self.broker_manager.shutdown()
            
            if self.data_service:
                await self.data_service.shutdown()
            
            if self.ws_manager:
                await self.ws_manager.cleanup()
            
            logger.info("Auto-Trading System shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during system shutdown: {e}")
    
    async def stop_trading_session(self, session_id: str):
        """Stop a trading session"""
        try:
            if session_id in self.active_sessions:
                session = self.active_sessions[session_id]
                session.session_end_time = datetime.now(timezone.utc)
                
                # Remove from active sessions
                self.active_sessions.pop(session_id)
                
                logger.info(f"Trading session stopped: {session_id}")
                await self._notify_session_event("SESSION_STOPPED", session_id)
            
        except Exception as e:
            logger.error(f"Error stopping trading session {session_id}: {e}")
    
    async def stop_all_sessions(self):
        """Stop all active trading sessions"""
        try:
            session_ids = list(self.active_sessions.keys())
            for session_id in session_ids:
                await self.stop_trading_session(session_id)
            
            # Set system to inactive
            self.system_state = TradingSystemState.INACTIVE
            logger.info(f"All trading sessions stopped ({len(session_ids)} sessions)")
            
        except Exception as e:
            logger.error(f"Error stopping all sessions: {e}")
    
    async def resume_system(self):
        """Resume the trading system from paused state"""
        try:
            if self.system_state == TradingSystemState.PAUSED:
                self.system_state = TradingSystemState.ACTIVE
                self.daily_loss_limit_hit = False
                logger.info("Trading system resumed")
                await self._notify_system_status("SYSTEM_RESUMED")
            else:
                logger.warning(f"Cannot resume system from state: {self.system_state.value}")
            
        except Exception as e:
            logger.error(f"Error resuming system: {e}")

# Context manager for easy system lifecycle management
@asynccontextmanager
async def auto_trading_system(config: Dict[str, Any]):
    """Context manager for auto-trading system lifecycle"""
    coordinator = AutoTradingCoordinator(config)
    
    try:
        # Initialize system
        success = await coordinator.initialize_system()
        if not success:
            raise RuntimeError("Failed to initialize auto-trading system")
        
        yield coordinator
        
    finally:
        # Always shutdown cleanly
        await coordinator.shutdown()