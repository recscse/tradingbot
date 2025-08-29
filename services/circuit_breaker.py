"""
Circuit Breaker System for Auto-Trading
Prevents catastrophic losses during system failures, market crashes, or connection issues
"""

import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
import json

logger = logging.getLogger(__name__)

class CircuitBreakerState(Enum):
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"          # Trading halted
    HALF_OPEN = "HALF_OPEN"  # Testing if system is recovered

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker thresholds"""
    max_loss_percentage: float = 10.0  # Max loss % before circuit breaker
    max_loss_amount: float = 100000.0  # Max loss amount in currency
    max_consecutive_losses: int = 5     # Max consecutive losing trades
    websocket_failure_threshold: int = 3  # Max WebSocket failures
    api_failure_threshold: int = 5      # Max API failures
    recovery_timeout: int = 300         # Seconds before trying half-open
    volatility_threshold: float = 5.0   # Market volatility % threshold

@dataclass
class SystemHealth:
    """System health metrics"""
    websocket_connected: bool = False
    api_responsive: bool = True
    last_price_update: Optional[datetime] = None
    consecutive_failures: int = 0
    market_volatility: float = 0.0
    system_load: float = 0.0

class AutoTradingCircuitBreaker:
    """
    Circuit breaker system for auto-trading
    Monitors system health and trading performance to prevent catastrophic losses
    """
    
    def __init__(self, config: CircuitBreakerConfig = None):
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitBreakerState.CLOSED
        self.health = SystemHealth()
        self.failure_count = 0
        self.last_failure_time = None
        self.consecutive_losses = 0
        self.total_pnl = 0.0
        self.daily_pnl = 0.0
        self.breach_history: List[Dict[str, Any]] = []
        self.callbacks: List[Callable] = []
        
        # Trading halt reasons
        self.halt_reasons: List[str] = []
        
        logger.info("🔴 Auto-Trading Circuit Breaker initialized")
    
    def add_callback(self, callback: Callable):
        """Add callback to be notified when circuit breaker trips"""
        self.callbacks.append(callback)
    
    async def check_trading_allowed(self) -> Dict[str, Any]:
        """
        Check if trading is allowed based on current system state
        
        Returns:
            Dictionary with trading status and reasons
        """
        try:
            if self.state == CircuitBreakerState.OPEN:
                return {
                    "allowed": False,
                    "state": self.state.value,
                    "reasons": self.halt_reasons,
                    "estimated_recovery": self._get_estimated_recovery_time()
                }
            
            # Check various conditions
            checks = await self._perform_health_checks()
            
            if not checks["healthy"]:
                await self._trip_circuit_breaker(checks["reasons"])
                return {
                    "allowed": False,
                    "state": self.state.value,
                    "reasons": checks["reasons"]
                }
            
            # Half-open state: allow limited trading
            if self.state == CircuitBreakerState.HALF_OPEN:
                return {
                    "allowed": True,
                    "state": self.state.value,
                    "limited": True,
                    "max_position_size": 0.5,  # 50% of normal position size
                    "reasons": ["Testing system recovery"]
                }
            
            # Normal operation
            return {
                "allowed": True,
                "state": self.state.value,
                "health": checks
            }
            
        except Exception as e:
            logger.error(f"❌ Error checking trading allowed: {e}")
            await self._trip_circuit_breaker([f"System error: {str(e)}"])
            return {"allowed": False, "state": "ERROR", "reasons": ["System error"]}
    
    async def _perform_health_checks(self) -> Dict[str, Any]:
        """Perform comprehensive system health checks"""
        reasons = []
        
        # 1. WebSocket connectivity check
        if not self.health.websocket_connected:
            reasons.append("WebSocket disconnected")
        
        # 2. Recent price updates check
        if self.health.last_price_update:
            time_since_update = datetime.now(timezone.utc) - self.health.last_price_update
            if time_since_update > timedelta(seconds=30):
                reasons.append("No recent price updates")
        
        # 3. P&L checks
        if self.config.max_loss_percentage > 0:
            # Assume initial capital for percentage calculation
            initial_capital = 500000  # This should come from account service
            loss_percentage = abs(self.daily_pnl) / initial_capital * 100
            if self.daily_pnl < 0 and loss_percentage > self.config.max_loss_percentage:
                reasons.append(f"Daily loss exceeds {self.config.max_loss_percentage}%")
        
        if self.daily_pnl < -self.config.max_loss_amount:
            reasons.append(f"Daily loss exceeds ₹{self.config.max_loss_amount:,.2f}")
        
        # 4. Consecutive losses check
        if self.consecutive_losses >= self.config.max_consecutive_losses:
            reasons.append(f"Too many consecutive losses ({self.consecutive_losses})")
        
        # 5. System failures check
        if self.failure_count >= self.config.api_failure_threshold:
            reasons.append("Too many API failures")
        
        # 6. Market volatility check
        if self.health.market_volatility > self.config.volatility_threshold:
            reasons.append(f"High market volatility ({self.health.market_volatility:.2f}%)")
        
        return {
            "healthy": len(reasons) == 0,
            "reasons": reasons,
            "health_score": max(0, 100 - len(reasons) * 20),
            "checks_performed": 6
        }
    
    async def _trip_circuit_breaker(self, reasons: List[str]):
        """Trip the circuit breaker and halt trading"""
        if self.state != CircuitBreakerState.OPEN:
            self.state = CircuitBreakerState.OPEN
            self.halt_reasons = reasons
            self.last_failure_time = datetime.now(timezone.utc)
            
            # Log the breach
            breach_info = {
                "timestamp": self.last_failure_time.isoformat(),
                "reasons": reasons,
                "daily_pnl": self.daily_pnl,
                "consecutive_losses": self.consecutive_losses,
                "failure_count": self.failure_count,
                "health": {
                    "websocket_connected": self.health.websocket_connected,
                    "market_volatility": self.health.market_volatility
                }
            }
            self.breach_history.append(breach_info)
            
            logger.critical(f"🚨 CIRCUIT BREAKER TRIPPED! Reasons: {', '.join(reasons)}")
            
            # Notify callbacks
            for callback in self.callbacks:
                try:
                    await callback("circuit_breaker_tripped", breach_info)
                except Exception as e:
                    logger.error(f"❌ Error in circuit breaker callback: {e}")
            
            # Start recovery timer
            asyncio.create_task(self._recovery_timer())
    
    async def _recovery_timer(self):
        """Timer for circuit breaker recovery"""
        await asyncio.sleep(self.config.recovery_timeout)
        
        if self.state == CircuitBreakerState.OPEN:
            # Move to half-open state for testing
            self.state = CircuitBreakerState.HALF_OPEN
            self.halt_reasons = ["Testing system recovery"]
            logger.warning("⚡ Circuit breaker moving to HALF-OPEN state for testing")
            
            # Notify callbacks
            for callback in self.callbacks:
                try:
                    await callback("circuit_breaker_half_open", {
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                except Exception as e:
                    logger.error(f"❌ Error in recovery callback: {e}")
    
    async def update_trade_result(self, trade_result: Dict[str, Any]):
        """Update circuit breaker with trade result"""
        try:
            pnl = trade_result.get("pnl", 0.0)
            self.total_pnl += pnl
            self.daily_pnl += pnl
            
            if pnl < 0:
                self.consecutive_losses += 1
            else:
                self.consecutive_losses = 0  # Reset on profitable trade
            
            # If in half-open state and trade was successful, consider closing circuit
            if self.state == CircuitBreakerState.HALF_OPEN and pnl >= 0:
                await self._close_circuit_breaker()
            
            logger.debug(f"📊 Trade result updated: P&L={pnl}, Consecutive losses={self.consecutive_losses}")
            
        except Exception as e:
            logger.error(f"❌ Error updating trade result: {e}")
    
    async def _close_circuit_breaker(self):
        """Close circuit breaker and resume normal trading"""
        self.state = CircuitBreakerState.CLOSED
        self.halt_reasons = []
        self.failure_count = 0
        self.consecutive_losses = 0
        
        logger.info("✅ Circuit breaker CLOSED - Normal trading resumed")
        
        # Notify callbacks
        for callback in self.callbacks:
            try:
                await callback("circuit_breaker_closed", {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "recovery_successful": True
                })
            except Exception as e:
                logger.error(f"❌ Error in recovery callback: {e}")
    
    async def update_system_health(self, health_data: Dict[str, Any]):
        """Update system health metrics"""
        try:
            if "websocket_connected" in health_data:
                self.health.websocket_connected = health_data["websocket_connected"]
            
            if "last_price_update" in health_data:
                self.health.last_price_update = health_data["last_price_update"]
            
            if "market_volatility" in health_data:
                self.health.market_volatility = health_data["market_volatility"]
            
            if "api_failure" in health_data and health_data["api_failure"]:
                self.failure_count += 1
            
            # Reset failure count on successful API calls
            if "api_success" in health_data and health_data["api_success"]:
                self.failure_count = max(0, self.failure_count - 1)
            
        except Exception as e:
            logger.error(f"❌ Error updating system health: {e}")
    
    def _get_estimated_recovery_time(self) -> Optional[str]:
        """Get estimated recovery time"""
        if not self.last_failure_time:
            return None
        
        recovery_time = self.last_failure_time + timedelta(seconds=self.config.recovery_timeout)
        return recovery_time.isoformat()
    
    async def force_close(self):
        """Manually close circuit breaker (admin function)"""
        await self._close_circuit_breaker()
        logger.warning("⚠️ Circuit breaker manually closed")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status"""
        return {
            "state": self.state.value,
            "halt_reasons": self.halt_reasons,
            "health": {
                "websocket_connected": self.health.websocket_connected,
                "api_responsive": self.health.api_responsive,
                "last_price_update": self.health.last_price_update.isoformat() if self.health.last_price_update else None,
                "consecutive_failures": self.health.consecutive_failures,
                "market_volatility": self.health.market_volatility
            },
            "performance": {
                "total_pnl": self.total_pnl,
                "daily_pnl": self.daily_pnl,
                "consecutive_losses": self.consecutive_losses,
                "failure_count": self.failure_count
            },
            "config": {
                "max_loss_percentage": self.config.max_loss_percentage,
                "max_loss_amount": self.config.max_loss_amount,
                "max_consecutive_losses": self.config.max_consecutive_losses,
                "recovery_timeout": self.config.recovery_timeout
            },
            "breach_history_count": len(self.breach_history),
            "estimated_recovery": self._get_estimated_recovery_time()
        }

# Global circuit breaker instance
circuit_breaker = AutoTradingCircuitBreaker()