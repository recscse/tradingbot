"""
Auto Trading WebSocket Service
Enhanced for Fibonacci + EMA Strategy Broadcasting
Provides real-time updates for trading signals, positions, and system status
"""

import asyncio
import logging
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set, Callable
from dataclasses import asdict
from enum import Enum
from collections import defaultdict, deque

# WebSocket imports
from services.unified_websocket_manager import unified_manager

# Service imports
from services.auto_stock_selection_service import (
    auto_stock_selection_service, StockSelectionResult
)
from services.execution.auto_trade_execution_service import (
    auto_trade_execution_service, TradeOrder, TradeSignal
)

# Enhanced imports for Phase 4 integration
try:
    from services.auto_trading_coordinator import AutoTradingCoordinator
    from services.execution.real_time_execution_engine import RealTimeExecutionEngine
    from services.execution.position_monitor import PositionMonitor
    from services.execution.order_management_system import OrderManagementSystem
except ImportError:
    # Fallback for gradual integration
    AutoTradingCoordinator = None
    RealTimeExecutionEngine = None
    PositionMonitor = None
    OrderManagementSystem = None

class MessageType(Enum):
    """Enhanced message types for comprehensive trading updates"""
    # Fibonacci Strategy Signals
    FIBONACCI_SIGNAL = "fibonacci_signal"
    FIBONACCI_SIGNAL_EXECUTED = "fibonacci_signal_executed"
    FIBONACCI_SIGNAL_REJECTED = "fibonacci_signal_rejected"
    
    # Position Updates
    POSITION_OPENED = "position_opened"
    POSITION_UPDATED = "position_updated"  
    POSITION_CLOSED = "position_closed"
    POSITION_PNL_UPDATE = "position_pnl_update"
    
    # Order Updates
    ORDER_PLACED = "order_placed"
    ORDER_FILLED = "order_filled"
    ORDER_CANCELLED = "order_cancelled"
    ORDER_REJECTED = "order_rejected"
    
    # System Status
    SYSTEM_STATUS = "system_status"
    TRADING_SESSION_STATUS = "trading_session_status"
    BROKER_STATUS = "broker_status"
    
    # Performance & Risk
    PERFORMANCE_UPDATE = "performance_update"
    RISK_ALERT = "risk_alert"
    PORTFOLIO_HEAT_UPDATE = "portfolio_heat_update"
    
    # Emergency Controls
    EMERGENCY_STOP = "emergency_stop"
    KILL_SWITCH_ACTIVATED = "kill_switch_activated"
    
    # Stock Selection
    STOCK_SELECTION_STARTED = "stock_selection_started"
    STOCK_SELECTION_UPDATED = "stock_selection_updated"
    
    # Legacy support
    AUTO_STOCK_UPDATE = "auto_stock_update"
    TRADING_SESSION_UPDATE = "trading_session_update"
    MARKET_SENTIMENT_UPDATE = "market_sentiment_update"
    TRADE_EXECUTED = "trade_executed"
    TRADE_EXITED = "trade_exited"

logger = logging.getLogger(__name__)

class AutoTradingWebSocketService:
    """
    Enhanced WebSocket service for auto trading events
    
    Broadcasts:
    - Fibonacci + EMA strategy signals
    - Real-time position and P&L updates
    - Order execution status
    - Risk alerts and portfolio heat
    - System status and broker health
    - Legacy stock selection updates
    """
    
    def __init__(self):
        self.is_active = False
        self.listeners = set()  # Track connected clients
        
        # Enhanced features
        self.client_subscriptions: Dict[str, Set[MessageType]] = defaultdict(set)
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.broadcast_history: deque = deque(maxlen=500)
        
        # Performance tracking
        self.broadcast_stats = {
            'total_messages_sent': 0,
            'messages_by_type': defaultdict(int),
            'active_connections': 0,
            'avg_broadcast_time_ms': 0.0,
            'failed_broadcasts': 0
        }
        
        # Rate limiting for high-frequency updates
        self.rate_limits = {
            MessageType.POSITION_PNL_UPDATE: 10,  # Max 10 P&L updates per second
            MessageType.FIBONACCI_SIGNAL: 20,     # Max 20 signals per second
            MessageType.POSITION_UPDATED: 5       # Max 5 position updates per second
        }
        self.rate_counters = defaultdict(int)
        self.last_rate_reset = time.time()
        
        # Integration with Phase 4 components
        self.coordinator: Optional[AutoTradingCoordinator] = None
        self.execution_engine: Optional[RealTimeExecutionEngine] = None
        self.position_monitor: Optional[PositionMonitor] = None
        self.order_manager: Optional[OrderManagementSystem] = None
        
    def integrate_with_coordinator(self, coordinator: 'AutoTradingCoordinator'):
        """Integrate with Phase 4 auto-trading coordinator"""
        self.coordinator = coordinator
        
        # Setup callbacks for real-time updates
        if coordinator:
            coordinator.add_status_callback(self._handle_system_status_update)
            coordinator.add_trade_callback(self._handle_trade_event)
            coordinator.add_error_callback(self._handle_system_error)
            logger.info("🔗 Integrated with Auto-Trading Coordinator")
    
    async def start_broadcasting(self):
        """Start enhanced broadcasting with Fibonacci strategy support"""
        if self.is_active:
            logger.warning("Auto trading WebSocket service already active")
            return
        
        self.is_active = True
        logger.info("🔴 Starting enhanced auto trading WebSocket service...")
        
        # Start enhanced background tasks
        asyncio.create_task(self._message_processor())
        asyncio.create_task(self._rate_limit_reset())
        asyncio.create_task(self._performance_tracker())
        
        # Start original monitoring tasks
        asyncio.create_task(self._monitor_stock_selection())
        asyncio.create_task(self._monitor_trade_execution())
        asyncio.create_task(self._monitor_market_sentiment())
        
        # Start new Phase 4 monitoring tasks
        if self.coordinator:
            asyncio.create_task(self._monitor_fibonacci_signals())
            asyncio.create_task(self._monitor_system_health())
        
    async def stop_broadcasting(self):
        """Stop broadcasting"""
        self.is_active = False
        logger.info("🔴 Stopped auto trading WebSocket service")
    
    async def _monitor_stock_selection(self):
        """Monitor stock selection updates"""
        last_selection_time = None
        
        while self.is_active:
            try:
                # Check if new stocks were selected
                # In practice, you'd integrate with actual selection events
                await asyncio.sleep(30)  # Check every 30 seconds
                
                # This is a placeholder - integrate with actual selection service
                current_time = datetime.now()
                
                # Broadcast daily stock selection at 9 AM
                if (current_time.hour == 9 and current_time.minute < 5 and 
                    (not last_selection_time or 
                     last_selection_time.date() != current_time.date())):
                    
                    await self._broadcast_stock_selection_update()
                    last_selection_time = current_time
                    
            except Exception as e:
                logger.error(f"❌ Error monitoring stock selection: {e}")
                await asyncio.sleep(60)
    
    async def _monitor_trade_execution(self):
        """Monitor trade execution updates"""
        last_stats = {}
        
        while self.is_active:
            try:
                # Get current trading stats
                current_stats = auto_trade_execution_service.get_trading_stats()
                
                # Check if stats changed
                if current_stats != last_stats:
                    await self._broadcast_trading_session_update(current_stats)
                    last_stats = current_stats.copy()
                
                await asyncio.sleep(5)  # Check every 5 seconds during trading
                
            except Exception as e:
                logger.error(f"❌ Error monitoring trade execution: {e}")
                await asyncio.sleep(30)
    
    async def _monitor_market_sentiment(self):
        """Monitor market sentiment changes"""
        last_sentiment = None
        
        while self.is_active:
            try:
                # Get current market sentiment
                # This would integrate with your sentiment analysis service
                current_sentiment = {
                    "sentiment": "bullish",
                    "confidence": 0.75,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Broadcast if changed
                if current_sentiment != last_sentiment:
                    await self._broadcast_market_sentiment_update(current_sentiment)
                    last_sentiment = current_sentiment.copy()
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"❌ Error monitoring market sentiment: {e}")
                await asyncio.sleep(120)
    
    async def _broadcast_stock_selection_update(self):
        """Broadcast stock selection updates"""
        try:
            # Get today's selected stocks from database
            from database.connection import SessionLocal
            from database.models import SelectedStock
            from datetime import date
            
            db = SessionLocal()
            try:
                selected_records = db.query(SelectedStock).filter(
                    SelectedStock.selection_date == date.today(),
                    SelectedStock.is_active == True
                ).all()
                
                stocks_data = []
                for record in selected_records:
                    try:
                        score_breakdown = {}
                        if record.score_breakdown:
                            score_breakdown = json.loads(record.score_breakdown)
                        
                        option_contract = None
                        if record.option_contract:
                            option_contract = json.loads(record.option_contract)
                        
                        stock_data = {
                            "symbol": record.symbol,
                            "sector": record.sector,
                            "selection_score": record.selection_score,
                            "selection_reason": record.selection_reason,
                            "price_at_selection": record.price_at_selection,
                            "option_type": record.option_type,
                            "atm_strike": score_breakdown.get("atm_strike"),
                            "adr_score": score_breakdown.get("adr_score", 0.5),
                            "sector_momentum": score_breakdown.get("sector_momentum", 0.0),
                            "volume_score": score_breakdown.get("volume_score", 0.5),
                            "technical_score": score_breakdown.get("technical_score", 0.5),
                            "expiry_date": record.option_expiry_date,
                            "option_contract": option_contract,
                            "selection_date": record.selection_date.isoformat(),
                            "updated_at": datetime.now().isoformat()
                        }
                        stocks_data.append(stock_data)
                        
                    except Exception as e:
                        logger.error(f"Error processing stock {record.symbol}: {e}")
                        continue
                
                # Broadcast to all connected clients
                update_data = {
                    "event": "auto_stock_update",
                    "data": {
                        "stocks": stocks_data,
                        "total_selected": len(stocks_data),
                        "selection_date": date.today().isoformat(),
                        "timestamp": datetime.now().isoformat()
                    }
                }
                
                await self._emit_to_all_clients(update_data)
                logger.info(f"📡 Broadcasted stock selection update: {len(stocks_data)} stocks")
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ Error broadcasting stock selection update: {e}")
    
    async def _broadcast_trading_session_update(self, stats: Dict[str, Any]):
        """Broadcast trading session updates"""
        try:
            update_data = {
                "event": "trading_session_update",
                "data": {
                    "is_active": stats.get("is_active", False),
                    "active_trades": stats.get("active_trades", 0),
                    "trades_executed_today": stats.get("trades_executed_today", 0),
                    "daily_pnl": stats.get("daily_pnl", 0.0),
                    "active_positions": stats.get("active_positions", []),
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            await self._emit_to_all_clients(update_data)
            logger.debug("📡 Broadcasted trading session update")
            
        except Exception as e:
            logger.error(f"❌ Error broadcasting trading session update: {e}")
    
    async def _broadcast_market_sentiment_update(self, sentiment: Dict[str, Any]):
        """Broadcast market sentiment updates"""
        try:
            update_data = {
                "event": "market_sentiment_update",
                "data": sentiment
            }
            
            await self._emit_to_all_clients(update_data)
            logger.info(f"📡 Broadcasted market sentiment update: {sentiment['sentiment']}")
            
        except Exception as e:
            logger.error(f"❌ Error broadcasting market sentiment update: {e}")
    
    async def broadcast_trade_execution(self, trade_signal: TradeSignal):
        """Broadcast when a trade is executed"""
        try:
            update_data = {
                "event": "trade_executed",
                "data": {
                    "symbol": trade_signal.symbol,
                    "option_type": trade_signal.option_type,
                    "direction": trade_signal.direction.value,
                    "quantity": trade_signal.quantity,
                    "strike_price": trade_signal.strike_price,
                    "trigger_price": trade_signal.trigger_price,
                    "stop_loss": trade_signal.stop_loss,
                    "target": trade_signal.target,
                    "confidence_score": trade_signal.confidence_score,
                    "reason": trade_signal.reason,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            await self._emit_to_all_clients(update_data)
            logger.info(f"📡 Broadcasted trade execution: {trade_signal.symbol} {trade_signal.option_type}")
            
        except Exception as e:
            logger.error(f"❌ Error broadcasting trade execution: {e}")
    
    async def broadcast_trade_exit(self, trade_order: TradeOrder, exit_reason: str):
        """Broadcast when a trade is exited"""
        try:
            update_data = {
                "event": "trade_exited",
                "data": {
                    "trade_id": trade_order.trade_id,
                    "symbol": trade_order.symbol,
                    "direction": trade_order.direction.value,
                    "entry_price": trade_order.entry_price,
                    "exit_price": trade_order.current_price,
                    "pnl": trade_order.pnl,
                    "pnl_percent": trade_order.pnl_percent,
                    "exit_reason": exit_reason,
                    "entry_time": trade_order.entry_time.isoformat(),
                    "exit_time": trade_order.exit_time.isoformat() if trade_order.exit_time else None,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            await self._emit_to_all_clients(update_data)
            logger.info(f"📡 Broadcasted trade exit: {trade_order.symbol} P&L: {trade_order.pnl_percent:.1f}%")
            
        except Exception as e:
            logger.error(f"❌ Error broadcasting trade exit: {e}")
    
    async def broadcast_position_update(self, symbol: str, current_price: float, pnl_data: Dict):
        """Broadcast real-time position updates"""
        try:
            update_data = {
                "event": "position_update",
                "data": {
                    "symbol": symbol,
                    "current_price": current_price,
                    "pnl": pnl_data.get("pnl", 0.0),
                    "pnl_percent": pnl_data.get("pnl_percent", 0.0),
                    "unrealized_pnl": pnl_data.get("unrealized_pnl", 0.0),
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            await self._emit_to_all_clients(update_data)
            
        except Exception as e:
            logger.error(f"❌ Error broadcasting position update: {e}")
    
    # =================== NEW FIBONACCI STRATEGY METHODS ===================
    
    async def broadcast_fibonacci_signal(self, signal_data: Dict[str, Any], session_id: str = None):
        """Broadcast Fibonacci + EMA strategy signal"""
        try:
            if not self._check_rate_limit(MessageType.FIBONACCI_SIGNAL):
                return
            
            message_data = {
                "event": MessageType.FIBONACCI_SIGNAL.value,
                "data": {
                    "signal_id": str(uuid.uuid4()),
                    "symbol": signal_data.get("symbol"),
                    "signal_type": signal_data.get("signal_type"),  # BUY_CE/BUY_PE
                    "strength": signal_data.get("strength", 0),
                    "confidence_score": signal_data.get("confidence_score", 0),
                    "entry_price": signal_data.get("entry_price", 0),
                    "stop_loss": signal_data.get("stop_loss", 0),
                    "target_1": signal_data.get("target_1", 0),
                    "target_2": signal_data.get("target_2", 0),
                    "risk_reward_ratio": signal_data.get("risk_reward_ratio", 0),
                    "fibonacci_levels": signal_data.get("fibonacci_levels", {}),
                    "ema_values": {
                        "ema_9": signal_data.get("ema_9", 0),
                        "ema_21": signal_data.get("ema_21", 0),
                        "ema_50": signal_data.get("ema_50", 0),
                        "alignment": signal_data.get("ema_alignment", "neutral")
                    },
                    "technical_indicators": {
                        "rsi_14": signal_data.get("rsi_14", 50),
                        "volume_confirmation": signal_data.get("volume_confirmation", False),
                        "volatility": signal_data.get("volatility", 0)
                    },
                    "timeframe_confluence": {
                        "tf_1m_signal": signal_data.get("tf_1m_signal", "neutral"),
                        "tf_5m_signal": signal_data.get("tf_5m_signal", "neutral"),
                        "confluence_score": signal_data.get("confluence_score", 0)
                    },
                    "market_conditions": {
                        "market_sentiment": signal_data.get("market_sentiment", "neutral"),
                        "index_momentum": signal_data.get("index_momentum", "neutral"),
                        "volatility_regime": signal_data.get("volatility_regime", "normal")
                    },
                    "session_id": session_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            }
            
            await self._queue_message(message_data, MessageType.FIBONACCI_SIGNAL)
            logger.info(f"📡 Fibonacci signal broadcasted: {signal_data.get('symbol')} {signal_data.get('signal_type')} (Strength: {signal_data.get('strength', 0)}%)")
            
        except Exception as e:
            logger.error(f"❌ Error broadcasting Fibonacci signal: {e}")
    
    async def broadcast_signal_execution_result(self, execution_data: Dict[str, Any], session_id: str = None):
        """Broadcast Fibonacci signal execution result"""
        try:
            success = execution_data.get("success", False)
            message_type = MessageType.FIBONACCI_SIGNAL_EXECUTED if success else MessageType.FIBONACCI_SIGNAL_REJECTED
            
            message_data = {
                "event": message_type.value,
                "data": {
                    "execution_id": execution_data.get("execution_id"),
                    "signal_id": execution_data.get("signal_id"),
                    "symbol": execution_data.get("symbol"),
                    "signal_type": execution_data.get("signal_type"),
                    "order_id": execution_data.get("order_id"),
                    "execution_price": execution_data.get("execution_price", 0),
                    "quantity": execution_data.get("quantity", 0),
                    "lot_size": execution_data.get("lot_size", 0),
                    "execution_time_ms": execution_data.get("execution_time_ms", 0),
                    "broker_used": execution_data.get("broker_used"),
                    "option_contract": execution_data.get("option_contract", {}),
                    "success": success,
                    "error_message": execution_data.get("error_message"),
                    "risk_allocated": execution_data.get("risk_allocated", 0),
                    "position_size_calculated": execution_data.get("position_size_calculated", 0),
                    "session_id": session_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            }
            
            await self._queue_message(message_data, message_type)
            status = "✅ EXECUTED" if success else "❌ REJECTED"
            logger.info(f"📡 Signal execution result: {execution_data.get('symbol')} {status}")
            
        except Exception as e:
            logger.error(f"❌ Error broadcasting signal execution result: {e}")
    
    async def broadcast_enhanced_position_update(self, position_data: Dict[str, Any], session_id: str = None):
        """Broadcast enhanced position update with Greeks and risk metrics"""
        try:
            if not self._check_rate_limit(MessageType.POSITION_UPDATED):
                return
            
            message_data = {
                "event": MessageType.POSITION_UPDATED.value,
                "data": {
                    "position_id": position_data.get("position_id"),
                    "symbol": position_data.get("symbol"),
                    "instrument_key": position_data.get("instrument_key"),
                    "position_type": position_data.get("position_type", "LONG"),
                    "quantity": position_data.get("quantity", 0),
                    "entry_price": position_data.get("entry_price", 0),
                    "current_price": position_data.get("current_price", 0),
                    "pnl_data": {
                        "unrealized_pnl": position_data.get("unrealized_pnl", 0),
                        "realized_pnl": position_data.get("realized_pnl", 0),
                        "total_pnl": position_data.get("total_pnl", 0),
                        "pnl_percentage": position_data.get("pnl_percentage", 0),
                        "day_pnl": position_data.get("day_pnl", 0)
                    },
                    "risk_metrics": {
                        "stop_loss": position_data.get("stop_loss", 0),
                        "target": position_data.get("target", 0),
                        "trailing_stop": position_data.get("trailing_stop"),
                        "risk_reward_current": position_data.get("risk_reward_current", 0),
                        "max_profit": position_data.get("max_profit", 0),
                        "max_drawdown": position_data.get("max_drawdown", 0)
                    },
                    "options_greeks": position_data.get("greeks", {}),  # Delta, Gamma, Theta, Vega
                    "time_metrics": {
                        "duration_minutes": position_data.get("duration_minutes", 0),
                        "time_to_expiry_hours": position_data.get("time_to_expiry_hours"),
                        "theta_decay_daily": position_data.get("theta_decay_daily", 0)
                    },
                    "strategy_context": {
                        "fibonacci_level_entry": position_data.get("fibonacci_level_entry"),
                        "ema_alignment_at_entry": position_data.get("ema_alignment_at_entry"),
                        "signal_strength_at_entry": position_data.get("signal_strength_at_entry", 0)
                    },
                    "session_id": session_id,
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }
            }
            
            await self._queue_message(message_data, MessageType.POSITION_UPDATED)
            
        except Exception as e:
            logger.error(f"❌ Error broadcasting enhanced position update: {e}")
    
    async def broadcast_position_closed(self, closure_data: Dict[str, Any], session_id: str = None):
        """Broadcast position closure with detailed analytics"""
        try:
            message_data = {
                "event": MessageType.POSITION_CLOSED.value,
                "data": {
                    "position_id": closure_data.get("position_id"),
                    "symbol": closure_data.get("symbol"),
                    "exit_reason": closure_data.get("exit_reason"),  # STOP_LOSS, TARGET_HIT, TIME_EXIT, etc.
                    "entry_details": {
                        "entry_price": closure_data.get("entry_price", 0),
                        "entry_time": closure_data.get("entry_time"),
                        "fibonacci_entry_level": closure_data.get("fibonacci_entry_level"),
                        "signal_strength": closure_data.get("entry_signal_strength", 0)
                    },
                    "exit_details": {
                        "exit_price": closure_data.get("exit_price", 0),
                        "exit_time": closure_data.get("exit_time"),
                        "final_pnl": closure_data.get("final_pnl", 0),
                        "pnl_percentage": closure_data.get("pnl_percentage", 0),
                        "risk_reward_achieved": closure_data.get("risk_reward_achieved", 0)
                    },
                    "performance_metrics": {
                        "duration_minutes": closure_data.get("duration_minutes", 0),
                        "max_profit_achieved": closure_data.get("max_profit_achieved", 0),
                        "max_drawdown": closure_data.get("max_drawdown", 0),
                        "profit_hit_percentage": closure_data.get("profit_hit_percentage", 0),
                        "drawdown_percentage": closure_data.get("drawdown_percentage", 0)
                    },
                    "strategy_analysis": {
                        "fibonacci_level_respect": closure_data.get("fibonacci_level_respect", "unknown"),
                        "ema_alignment_maintained": closure_data.get("ema_alignment_maintained", False),
                        "strategy_effectiveness": closure_data.get("strategy_effectiveness", "neutral")
                    },
                    "session_id": session_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            }
            
            await self._queue_message(message_data, MessageType.POSITION_CLOSED)
            
            pnl_status = "🟢 PROFIT" if closure_data.get("final_pnl", 0) > 0 else "🔴 LOSS"
            logger.info(f"📡 Position closed: {closure_data.get('symbol')} {pnl_status} ({closure_data.get('exit_reason')})")
            
        except Exception as e:
            logger.error(f"❌ Error broadcasting position closure: {e}")
    
    async def broadcast_risk_alert(self, alert_data: Dict[str, Any], session_id: str = None):
        """Broadcast risk management alerts"""
        try:
            message_data = {
                "event": MessageType.RISK_ALERT.value,
                "data": {
                    "alert_id": str(uuid.uuid4()),
                    "alert_type": alert_data.get("alert_type"),  # PORTFOLIO_HEAT, DAILY_LOSS, POSITION_RISK, etc.
                    "severity": alert_data.get("severity", "MEDIUM"),  # LOW, MEDIUM, HIGH, CRITICAL
                    "current_value": alert_data.get("current_value", 0),
                    "threshold_value": alert_data.get("threshold_value", 0),
                    "percentage_of_limit": alert_data.get("percentage_of_limit", 0),
                    "description": alert_data.get("description"),
                    "recommended_actions": alert_data.get("recommended_actions", []),
                    "affected_positions": alert_data.get("affected_positions", []),
                    "auto_action_taken": alert_data.get("auto_action_taken", False),
                    "auto_action_description": alert_data.get("auto_action_description"),
                    "portfolio_impact": {
                        "total_exposure": alert_data.get("total_exposure", 0),
                        "heat_percentage": alert_data.get("heat_percentage", 0),
                        "diversification_score": alert_data.get("diversification_score", 0)
                    },
                    "session_id": session_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            }
            
            await self._queue_message(message_data, MessageType.RISK_ALERT, priority=1)  # High priority
            
            severity_emoji = {"LOW": "🟡", "MEDIUM": "🟠", "HIGH": "🔴", "CRITICAL": "🚨"}.get(alert_data.get("severity", "MEDIUM"), "⚠️")
            logger.warning(f"📡 Risk Alert: {severity_emoji} {alert_data.get('alert_type')} - {alert_data.get('description')}")
            
        except Exception as e:
            logger.error(f"❌ Error broadcasting risk alert: {e}")
    
    async def broadcast_system_status_update(self, status_data: Dict[str, Any]):
        """Broadcast comprehensive system status"""
        try:
            message_data = {
                "event": MessageType.SYSTEM_STATUS.value,
                "data": {
                    "system_state": status_data.get("system_state", "UNKNOWN"),
                    "trading_active": status_data.get("trading_active", False),
                    "emergency_stop_active": status_data.get("emergency_stop_active", False),
                    "circuit_breaker_open": status_data.get("circuit_breaker_open", False),
                    "session_metrics": {
                        "active_sessions": status_data.get("active_sessions", 0),
                        "active_positions": status_data.get("active_positions", 0),
                        "pending_orders": status_data.get("pending_orders", 0)
                    },
                    "performance_today": {
                        "total_trades": status_data.get("total_trades_today", 0),
                        "successful_trades": status_data.get("successful_trades", 0),
                        "failed_trades": status_data.get("failed_trades", 0),
                        "success_rate": status_data.get("success_rate", 0),
                        "daily_pnl": status_data.get("daily_pnl", 0),
                        "signals_generated": status_data.get("signals_generated", 0),
                        "signals_executed": status_data.get("signals_executed", 0)
                    },
                    "system_health": {
                        "data_feed_status": status_data.get("data_feed_status", "UNKNOWN"),
                        "broker_status": status_data.get("broker_status", "UNKNOWN"),
                        "database_status": status_data.get("database_status", "UNKNOWN"),
                        "execution_engine_status": status_data.get("execution_engine_status", "UNKNOWN"),
                        "avg_execution_time_ms": status_data.get("avg_execution_time_ms", 0),
                        "uptime_seconds": status_data.get("uptime_seconds", 0)
                    },
                    "last_signal_time": status_data.get("last_signal_time"),
                    "last_trade_time": status_data.get("last_trade_time"),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            }
            
            await self._queue_message(message_data, MessageType.SYSTEM_STATUS)
            
        except Exception as e:
            logger.error(f"❌ Error broadcasting system status: {e}")
    
    async def _emit_to_all_clients(self, data: Dict[str, Any]):
        """Emit data to all connected WebSocket clients"""
        try:
            if unified_manager and unified_manager.is_active:
                # Use the unified WebSocket manager to broadcast
                await unified_manager.emit_to_all("auto_trading_update", data)
                
            else:
                logger.warning("Unified WebSocket manager not available for broadcasting")
                
        except Exception as e:
            logger.error(f"❌ Error emitting to clients: {e}")
    
    def add_listener(self, client_id: str):
        """Add a WebSocket client listener"""
        self.listeners.add(client_id)
        logger.info(f"📡 Added auto trading listener: {client_id}")
    
    def remove_listener(self, client_id: str):
        """Remove a WebSocket client listener"""
        self.listeners.discard(client_id)
        logger.info(f"📡 Removed auto trading listener: {client_id}")
    
    def get_listener_count(self) -> int:
        """Get number of active listeners"""
        return len(self.listeners)
    
    # =================== NEW HELPER METHODS ===================
    
    async def _queue_message(self, message_data: Dict[str, Any], message_type: MessageType, priority: int = 2):
        """Queue message for processing"""
        try:
            message_data['priority'] = priority
            message_data['message_type'] = message_type.value
            await self.message_queue.put(message_data)
            
        except Exception as e:
            logger.error(f"❌ Error queuing message: {e}")
    
    async def _message_processor(self):
        """Process queued messages and broadcast"""
        while self.is_active:
            try:
                try:
                    message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                
                start_time = time.time()
                
                # Broadcast via unified manager
                await self._emit_to_all_clients(message)
                
                # Update stats
                broadcast_time_ms = (time.time() - start_time) * 1000
                self.broadcast_stats['total_messages_sent'] += 1
                message_type = message.get('message_type', 'unknown')
                self.broadcast_stats['messages_by_type'][message_type] += 1
                
                # Update average broadcast time
                self._update_avg_broadcast_time(broadcast_time_ms)
                
                # Add to history
                self.broadcast_history.append({
                    'message_type': message_type,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'broadcast_time_ms': broadcast_time_ms
                })
                
            except Exception as e:
                logger.error(f"❌ Error in message processor: {e}")
                await asyncio.sleep(0.1)
    
    def _check_rate_limit(self, message_type: MessageType) -> bool:
        """Check rate limits for message types"""
        current_time = time.time()
        
        # Reset counters every second
        if current_time - self.last_rate_reset >= 1.0:
            self.rate_counters.clear()
            self.last_rate_reset = current_time
        
        # Check rate limit
        limit = self.rate_limits.get(message_type, 1000)  # Default high limit
        current_count = self.rate_counters[message_type]
        
        if current_count >= limit:
            return False
        
        self.rate_counters[message_type] += 1
        return True
    
    async def _rate_limit_reset(self):
        """Reset rate limit counters"""
        while self.is_active:
            try:
                await asyncio.sleep(1.0)
                self.rate_counters.clear()
            except Exception as e:
                logger.error(f"❌ Error in rate limit reset: {e}")
    
    async def _performance_tracker(self):
        """Track WebSocket performance"""
        while self.is_active:
            try:
                self.broadcast_stats['active_connections'] = len(self.listeners)
                await asyncio.sleep(10.0)  # Update every 10 seconds
            except Exception as e:
                logger.error(f"❌ Error in performance tracker: {e}")
                await asyncio.sleep(30.0)
    
    def _update_avg_broadcast_time(self, new_time_ms: float):
        """Update average broadcast time"""
        current_avg = self.broadcast_stats['avg_broadcast_time_ms']
        total_messages = self.broadcast_stats['total_messages_sent']
        
        if total_messages <= 1:
            self.broadcast_stats['avg_broadcast_time_ms'] = new_time_ms
        else:
            # Exponential moving average
            alpha = 0.1
            self.broadcast_stats['avg_broadcast_time_ms'] = (
                alpha * new_time_ms + (1 - alpha) * current_avg
            )
    
    async def _monitor_fibonacci_signals(self):
        """Monitor Fibonacci signals from coordinator"""
        while self.is_active:
            try:
                if self.coordinator:
                    # This would integrate with coordinator's signal callbacks
                    # For now, just a placeholder
                    pass
                
                await asyncio.sleep(1.0)
                
            except Exception as e:
                logger.error(f"❌ Error monitoring Fibonacci signals: {e}")
                await asyncio.sleep(5.0)
    
    async def _monitor_system_health(self):
        """Monitor system health and broadcast updates"""
        while self.is_active:
            try:
                if self.coordinator:
                    system_status = self.coordinator.get_system_status()
                    await self.broadcast_system_status_update(system_status)
                
                await asyncio.sleep(30.0)  # Broadcast every 30 seconds
                
            except Exception as e:
                logger.error(f"❌ Error monitoring system health: {e}")
                await asyncio.sleep(60.0)
    
    # Callback handlers for coordinator integration
    async def _handle_system_status_update(self, event_type: str, data: Dict[str, Any]):
        """Handle system status updates from coordinator"""
        try:
            await self.broadcast_system_status_update(data)
        except Exception as e:
            logger.error(f"❌ Error handling system status update: {e}")
    
    async def _handle_trade_event(self, event_type: str, data: Dict[str, Any]):
        """Handle trade events from coordinator"""
        try:
            if event_type == "SIGNAL_GENERATED":
                await self.broadcast_fibonacci_signal(data.get('signal_data', {}), data.get('session_id'))
            elif event_type == "SIGNAL_EXECUTED":
                await self.broadcast_signal_execution_result(data, data.get('session_id'))
            elif event_type == "POSITION_UPDATED":
                await self.broadcast_enhanced_position_update(data, data.get('session_id'))
            elif event_type == "POSITION_CLOSED":
                await self.broadcast_position_closed(data, data.get('session_id'))
                
        except Exception as e:
            logger.error(f"❌ Error handling trade event: {e}")
    
    async def _handle_system_error(self, error_type: str, data: Dict[str, Any]):
        """Handle system errors from coordinator"""
        try:
            # Convert system errors to risk alerts
            alert_data = {
                'alert_type': 'SYSTEM_ERROR',
                'severity': 'HIGH',
                'description': f"System Error: {error_type}",
                'error_message': data.get('message'),
                'auto_action_taken': False,
                'recommended_actions': ['Check system logs', 'Contact administrator']
            }
            await self.broadcast_risk_alert(alert_data)
            
        except Exception as e:
            logger.error(f"❌ Error handling system error: {e}")
    
    async def broadcast_session_started(self, data: Dict[str, Any]):
        """Broadcast trading session started event"""
        try:
            await self._broadcast_message(MessageType.SYSTEM_STATUS, {
                'type': 'session_started',
                'session_id': data.get('session_id'),
                'user_id': data.get('user_id'),
                'mode': data.get('mode'),
                'selected_stocks_count': data.get('selected_stocks_count'),
                'timestamp': data.get('timestamp')
            })
        except Exception as e:
            logger.error(f"Error broadcasting session started: {e}")
    
    async def broadcast_session_stopped(self, data: Dict[str, Any]):
        """Broadcast trading session stopped event"""
        try:
            await self._broadcast_message(MessageType.SYSTEM_STATUS, {
                'type': 'session_stopped',
                'session_id': data.get('session_id'),
                'user_id': data.get('user_id'),
                'final_pnl': data.get('final_pnl'),
                'total_trades': data.get('total_trades'),
                'timestamp': data.get('timestamp')
            })
        except Exception as e:
            logger.error(f"Error broadcasting session stopped: {e}")
    
    async def broadcast_stock_selection_started(self, data: Dict[str, Any]):
        """Broadcast stock selection started event"""
        try:
            await self._broadcast_message(MessageType.STOCK_SELECTION_STARTED, {
                'user_id': data.get('user_id'),
                'triggered_by': data.get('triggered_by'),
                'timestamp': data.get('timestamp')
            })
        except Exception as e:
            logger.error(f"Error broadcasting stock selection started: {e}")
    
    async def broadcast_real_time_metrics(self, metrics: Dict[str, Any]):
        """Broadcast real-time trading metrics"""
        try:
            await self._broadcast_message(MessageType.SYSTEM_STATUS, {
                'type': 'real_time_metrics',
                'metrics': metrics
            })
        except Exception as e:
            logger.error(f"Error broadcasting real-time metrics: {e}")
    
    async def broadcast_stock_removed(self, data: Dict[str, Any]):
        """Broadcast stock removal event"""
        try:
            await self._broadcast_message(MessageType.STOCK_SELECTION_UPDATED, {
                'action': 'stock_removed',
                'stock_id': data.get('stock_id'),
                'symbol': data.get('symbol'),
                'user_id': data.get('user_id'),
                'timestamp': data.get('timestamp')
            })
        except Exception as e:
            logger.error(f"Error broadcasting stock removed: {e}")
    
    async def broadcast_kill_switch_activated(self, data: Dict[str, Any]):
        """Broadcast kill switch activation event"""
        try:
            await self._broadcast_message(MessageType.EMERGENCY_STOP, {
                'type': 'kill_switch_activated',
                'symbol': data.get('symbol'),
                'user_id': data.get('user_id'),
                'trading_mode': data.get('trading_mode'),
                'positions_closed': data.get('positions_closed'),
                'total_pnl': data.get('total_pnl'),
                'triggered_by': data.get('triggered_by'),
                'timestamp': data.get('timestamp')
            })
        except Exception as e:
            logger.error(f"Error broadcasting kill switch activated: {e}")
    
    def get_enhanced_stats(self) -> Dict[str, Any]:
        """Get enhanced broadcasting statistics"""
        return {
            'basic_stats': {
                'active_connections': len(self.listeners),
                'is_broadcasting': self.is_active
            },
            'performance_stats': self.broadcast_stats.copy(),
            'rate_limits': self.rate_limits.copy(),
            'message_queue_size': self.message_queue.qsize(),
            'recent_messages': list(self.broadcast_history)[-10:],  # Last 10 messages
            'coordinator_connected': self.coordinator is not None
        }

# Global service instance
auto_trading_websocket_service = AutoTradingWebSocketService()

async def start_auto_trading_websocket():
    """Start the enhanced auto trading WebSocket service"""
    logger.info("🚀 Starting Enhanced Auto Trading WebSocket Service...")
    await auto_trading_websocket_service.start_broadcasting()
    return auto_trading_websocket_service

def integrate_websocket_with_coordinator(coordinator: 'AutoTradingCoordinator'):
    """Helper function to integrate WebSocket with coordinator"""
    auto_trading_websocket_service.integrate_with_coordinator(coordinator)
    logger.info("🔗 WebSocket integrated with Auto-Trading Coordinator")