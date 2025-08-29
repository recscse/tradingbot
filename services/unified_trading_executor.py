"""
Unified Trading Execution Service
Handles both PAPER and LIVE trading with shared components
Only the final execution step differs between modes
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum

from services.paper_trading_account import paper_trading_service
from services.circuit_breaker import circuit_breaker
from services.execution.auto_trade_execution_service import AutoTradeExecutionService
from services.execution.broker_integration_manager import BrokerIntegrationManager
from database.models import User

logger = logging.getLogger(__name__)

class TradingMode(Enum):
    PAPER = "PAPER"
    LIVE = "LIVE"

@dataclass
class UnifiedTradeSignal:
    """Unified trade signal for both paper and live trading"""
    user_id: int
    symbol: str
    instrument_key: str
    option_type: str  # CE/PE
    strike_price: float
    signal_type: str  # BUY/SELL
    entry_price: float
    quantity: int
    lot_size: int
    invested_amount: float
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    confidence_score: float = 0.0
    strategy_name: str = "fibonacci_ema"
    trading_mode: TradingMode = TradingMode.PAPER

@dataclass
class UnifiedTradeResult:
    """Unified trade result for both modes"""
    success: bool
    trade_id: str
    position_id: Optional[str] = None
    execution_price: Optional[float] = None
    execution_time: Optional[datetime] = None
    pnl: Optional[float] = None
    error_message: Optional[str] = None
    broker_order_id: Optional[str] = None  # Only for live trades

class UnifiedTradingExecutor:
    """
    Unified executor that handles both paper and live trading
    ALL components are shared except the final execution step
    """
    
    def __init__(self):
        self.live_executor = None  # Will be initialized when needed
        self.broker_manager = None  # Will be initialized when needed
        
        # Shared components for both modes
        self.active_signals: Dict[str, UnifiedTradeSignal] = {}
        self.execution_stats = {
            "total_signals": 0,
            "paper_trades": 0,
            "live_trades": 0,
            "successful_executions": 0,
            "failed_executions": 0
        }
        
        logger.info("🔄 Unified Trading Executor initialized")
    
    async def execute_trade_signal(self, signal: UnifiedTradeSignal) -> UnifiedTradeResult:
        """
        Main entry point for trade execution
        Routes to paper or live execution based on signal.trading_mode
        """
        try:
            # 1. SHARED: Circuit breaker check (same for both modes)
            circuit_check = await circuit_breaker.check_trading_allowed()
            if not circuit_check["allowed"]:
                return UnifiedTradeResult(
                    success=False,
                    trade_id=f"BLOCKED_{int(datetime.now().timestamp())}",
                    error_message=f"Trading halted: {', '.join(circuit_check.get('reasons', []))}"
                )
            
            # 2. SHARED: Pre-execution validation (same for both modes)
            validation = await self._validate_trade_signal(signal)
            if not validation["valid"]:
                return UnifiedTradeResult(
                    success=False,
                    trade_id=f"INVALID_{int(datetime.now().timestamp())}",
                    error_message=validation["reason"]
                )
            
            # 3. SHARED: Log signal processing
            self.active_signals[signal.symbol] = signal
            self.execution_stats["total_signals"] += 1
            
            # 4. ROUTING: Execute based on trading mode
            if signal.trading_mode == TradingMode.PAPER:
                result = await self._execute_paper_trade(signal)
                self.execution_stats["paper_trades"] += 1
            else:
                result = await self._execute_live_trade(signal)
                self.execution_stats["live_trades"] += 1
            
            # 5. SHARED: Post-execution processing (same for both modes)
            await self._post_execution_processing(signal, result)
            
            # Update success/failure stats
            if result.success:
                self.execution_stats["successful_executions"] += 1
            else:
                self.execution_stats["failed_executions"] += 1
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error executing trade signal: {e}")
            return UnifiedTradeResult(
                success=False,
                trade_id=f"ERROR_{int(datetime.now().timestamp())}",
                error_message=str(e)
            )
    
    async def _validate_trade_signal(self, signal: UnifiedTradeSignal) -> Dict[str, Any]:
        """
        SHARED: Validation logic for both paper and live trading
        """
        try:
            # Basic signal validation
            if not signal.symbol or not signal.instrument_key:
                return {"valid": False, "reason": "Missing symbol or instrument key"}
            
            if signal.invested_amount <= 0:
                return {"valid": False, "reason": "Invalid investment amount"}
            
            if signal.quantity <= 0 or signal.lot_size <= 0:
                return {"valid": False, "reason": "Invalid quantity or lot size"}
            
            # Mode-specific validation
            if signal.trading_mode == TradingMode.PAPER:
                paper_validation = await paper_trading_service.validate_trade(
                    signal.user_id, signal.invested_amount
                )
                if not paper_validation["valid"]:
                    return {"valid": False, "reason": paper_validation["reason"]}
            
            else:  # LIVE mode
                # Add live trading validations here
                # Check broker connection, margin, etc.
                pass
            
            return {"valid": True}
            
        except Exception as e:
            logger.error(f"❌ Error validating trade signal: {e}")
            return {"valid": False, "reason": f"Validation error: {str(e)}"}
    
    async def _execute_paper_trade(self, signal: UnifiedTradeSignal) -> UnifiedTradeResult:
        """
        PAPER MODE: Virtual execution using paper trading service
        """
        try:
            # Prepare trade data for paper trading service
            trade_data = {
                "symbol": signal.symbol,
                "instrument_key": signal.instrument_key,
                "option_type": signal.option_type,
                "strike_price": signal.strike_price,
                "entry_price": signal.entry_price,
                "quantity": signal.quantity,
                "lot_size": signal.lot_size,
                "invested_amount": signal.invested_amount,
                "stop_loss": signal.stop_loss,
                "target": signal.target
            }
            
            # Execute virtual trade
            paper_result = await paper_trading_service.execute_paper_trade(
                signal.user_id, trade_data
            )
            
            if paper_result["success"]:
                logger.info(f"📄 Paper trade executed: {signal.symbol} {signal.option_type}")
                
                return UnifiedTradeResult(
                    success=True,
                    trade_id=f"PAPER_{paper_result['position_id']}",
                    position_id=paper_result["position_id"],
                    execution_price=signal.entry_price,
                    execution_time=datetime.now(timezone.utc),
                    pnl=0.0  # Initial P&L is zero
                )
            else:
                return UnifiedTradeResult(
                    success=False,
                    trade_id=f"PAPER_FAILED_{int(datetime.now().timestamp())}",
                    error_message=paper_result["error"]
                )
                
        except Exception as e:
            logger.error(f"❌ Error executing paper trade: {e}")
            return UnifiedTradeResult(
                success=False,
                trade_id=f"PAPER_ERROR_{int(datetime.now().timestamp())}",
                error_message=str(e)
            )
    
    async def _execute_live_trade(self, signal: UnifiedTradeSignal) -> UnifiedTradeResult:
        """
        LIVE MODE: Real broker execution via broker integration
        """
        try:
            # Initialize live executor if not already done
            if not self.live_executor:
                self.live_executor = AutoTradeExecutionService()
            
            if not self.broker_manager:
                self.broker_manager = BrokerIntegrationManager()
            
            # Get user's broker configuration
            # This would come from database - simplified here
            user_broker = "upstox"  # This should be fetched from user settings
            
            # Prepare order for broker API
            order_data = {
                "symbol": signal.symbol,
                "instrument_key": signal.instrument_key,
                "quantity": signal.quantity * signal.lot_size,
                "price": signal.entry_price,
                "order_type": "LIMIT",
                "product": "MIS",  # Intraday
                "validity": "DAY",
                "disclosed_quantity": 0
            }
            
            # Execute via broker
            broker_result = await self.broker_manager.place_order(
                user_broker, order_data, signal.user_id
            )
            
            if broker_result["success"]:
                logger.info(f"🔴 LIVE trade executed: {signal.symbol} {signal.option_type} via {user_broker}")
                
                return UnifiedTradeResult(
                    success=True,
                    trade_id=f"LIVE_{broker_result.get('order_id', 'unknown')}",
                    broker_order_id=broker_result.get("order_id"),
                    execution_price=broker_result.get("execution_price", signal.entry_price),
                    execution_time=datetime.now(timezone.utc),
                    pnl=0.0  # Initial P&L is zero
                )
            else:
                return UnifiedTradeResult(
                    success=False,
                    trade_id=f"LIVE_FAILED_{int(datetime.now().timestamp())}",
                    error_message=broker_result.get("error", "Unknown broker error")
                )
                
        except Exception as e:
            logger.error(f"❌ Error executing live trade: {e}")
            return UnifiedTradeResult(
                success=False,
                trade_id=f"LIVE_ERROR_{int(datetime.now().timestamp())}",
                error_message=str(e)
            )
    
    async def _post_execution_processing(self, signal: UnifiedTradeSignal, result: UnifiedTradeResult):
        """
        SHARED: Post-execution processing for both modes
        """
        try:
            # Update circuit breaker with trade result
            if result.success:
                await circuit_breaker.update_trade_result({
                    "pnl": result.pnl or 0.0,
                    "success": True,
                    "execution_time": result.execution_time
                })
            else:
                await circuit_breaker.update_trade_result({
                    "pnl": 0.0,
                    "success": False,
                    "error": result.error_message
                })
            
            # Remove from active signals
            if signal.symbol in self.active_signals:
                del self.active_signals[signal.symbol]
            
            # Log execution result
            logger.info(f"🔄 Trade execution completed: {result.trade_id} (Success: {result.success})")
            
            # Emit WebSocket update for UI
            await self._emit_execution_update(signal, result)
            
        except Exception as e:
            logger.error(f"❌ Error in post-execution processing: {e}")
    
    async def _emit_execution_update(self, signal: UnifiedTradeSignal, result: UnifiedTradeResult):
        """
        SHARED: Emit WebSocket update for both modes
        """
        try:
            from services.unified_websocket_manager import unified_manager
            
            update_data = {
                "type": "trade_execution",
                "trade_id": result.trade_id,
                "symbol": signal.symbol,
                "option_type": signal.option_type,
                "trading_mode": signal.trading_mode.value,
                "success": result.success,
                "execution_price": result.execution_price,
                "invested_amount": signal.invested_amount,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": result.error_message if not result.success else None
            }
            
            await unified_manager.emit_to_all("trade_execution_update", update_data)
            
        except Exception as e:
            logger.error(f"❌ Error emitting execution update: {e}")
    
    async def close_position(self, position_id: str, user_id: int, trading_mode: TradingMode, exit_price: float) -> UnifiedTradeResult:
        """
        UNIFIED: Close position for both paper and live trading
        """
        try:
            if trading_mode == TradingMode.PAPER:
                # Close paper position
                result = await paper_trading_service.close_position(user_id, position_id, exit_price)
                
                if result["success"]:
                    return UnifiedTradeResult(
                        success=True,
                        trade_id=f"PAPER_CLOSE_{position_id}",
                        execution_price=exit_price,
                        execution_time=datetime.now(timezone.utc),
                        pnl=result["final_pnl"]
                    )
                else:
                    return UnifiedTradeResult(
                        success=False,
                        trade_id=f"PAPER_CLOSE_FAILED_{position_id}",
                        error_message=result["error"]
                    )
            
            else:  # LIVE mode
                # Close live position via broker
                # Implementation would go here
                pass
                
        except Exception as e:
            logger.error(f"❌ Error closing position: {e}")
            return UnifiedTradeResult(
                success=False,
                trade_id=f"CLOSE_ERROR_{position_id}",
                error_message=str(e)
            )
    
    async def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics for monitoring"""
        return {
            "stats": self.execution_stats,
            "active_signals": len(self.active_signals),
            "circuit_breaker_status": await circuit_breaker.get_status()
        }

# Global unified executor instance
unified_trading_executor = UnifiedTradingExecutor()