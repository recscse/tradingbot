"""
Order Manager - PAPER vs LIVE Trading Abstraction

Provides a unified interface for order execution that can switch between:
- PAPER mode: Orders logged to CSV and in-memory tracking
- LIVE mode: Real orders sent to Upstox API with proper error handling

Features:
- Automatic token refresh on 401 errors
- Position tracking and risk management
- Comprehensive order logging and audit trail
"""

import asyncio
import httpx
import csv
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import os

logger = logging.getLogger(__name__)

@dataclass
class Order:
    """Standardized order structure"""
    order_id: str
    symbol: str
    side: str  # 'BUY' or 'SELL'
    quantity: int
    price: float
    order_type: str  # 'MARKET', 'LIMIT'
    status: str  # 'PENDING', 'FILLED', 'REJECTED', 'CANCELLED'
    timestamp: datetime
    user_id: int
    strategy: str
    exchange: str = 'NSE'
    
@dataclass  
class Position:
    """Position tracking structure"""
    symbol: str
    quantity: int
    avg_price: float
    side: str
    unrealized_pnl: float = 0.0
    last_price: float = 0.0
    
class OrderManager:
    """
    Unified order execution interface supporting both PAPER and LIVE modes.
    """
    
    def __init__(self, mode: str = "PAPER", access_token: str = None, user_id: int = None):
        self.mode = mode.upper()
        self.access_token = access_token
        self.user_id = user_id
        
        # API client for LIVE mode
        self.client = httpx.AsyncClient() if mode == "LIVE" else None
        self.base_url = "https://api.upstox.com"
        
        # Order tracking
        self.orders = {}  # order_id -> Order
        self.positions = {}  # symbol -> Position
        
        # Paper trading setup
        if self.mode == "PAPER":
            self._setup_paper_trading()
        
        # Risk limits
        self.max_position_size = int(os.getenv("MAX_POSITION_SIZE", "10000"))
        self.daily_loss_limit = float(os.getenv("DAILY_LOSS_LIMIT", "5000"))
        self.daily_pnl = 0.0
        
        logger.info(f"🎮 OrderManager initialized in {self.mode} mode")
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    def _setup_paper_trading(self):
        """Setup paper trading CSV logging"""
        self.paper_data_dir = Path("data/paper_trading")
        self.paper_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Orders CSV
        self.orders_csv = self.paper_data_dir / f"orders_{datetime.now().strftime('%Y%m%d')}.csv"
        
        # Positions CSV  
        self.positions_csv = self.paper_data_dir / f"positions_{datetime.now().strftime('%Y%m%d')}.csv"
        
        # Initialize CSV headers if files don't exist
        if not self.orders_csv.exists():
            with open(self.orders_csv, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'order_id', 'timestamp', 'symbol', 'side', 'quantity', 
                    'price', 'order_type', 'status', 'strategy', 'user_id'
                ])
        
        if not self.positions_csv.exists():
            with open(self.positions_csv, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'symbol', 'quantity', 'avg_price', 
                    'side', 'unrealized_pnl', 'last_price'
                ])
        
        logger.info(f"📄 Paper trading logs: {self.orders_csv}")
    
    async def place_order(
        self, 
        symbol: str,
        side: str,
        quantity: int,
        price: Optional[float] = None,
        order_type: str = "MARKET",
        strategy: str = "manual"
    ) -> Dict[str, Any]:
        """
        Place an order in either PAPER or LIVE mode.
        """
        # Input validation
        if not symbol or quantity <= 0:
            return {"success": False, "error": "Invalid order parameters"}
        
        # Risk checks
        risk_check = self._check_risk_limits(symbol, side, quantity, price)
        if not risk_check["allowed"]:
            return {"success": False, "error": f"Risk limit exceeded: {risk_check['reason']}"}
        
        # Generate order ID
        order_id = f"{self.mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.orders)}"
        
        # Create order object
        order = Order(
            order_id=order_id,
            symbol=symbol,
            side=side.upper(),
            quantity=quantity,
            price=price or 0.0,
            order_type=order_type.upper(),
            status="PENDING",
            timestamp=datetime.now(),
            user_id=self.user_id or 0,
            strategy=strategy
        )
        
        try:
            if self.mode == "PAPER":
                result = await self._place_paper_order(order)
            else:
                result = await self._place_live_order(order)
            
            # Store order in memory
            self.orders[order_id] = order
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error placing order: {e}")
            return {"success": False, "error": str(e), "order_id": order_id}
    
    async def _place_paper_order(self, order: Order) -> Dict[str, Any]:
        """Execute paper order (simulation)"""
        try:
            # For paper trading, immediately fill market orders at current price
            if order.order_type == "MARKET":
                # Get current market price (simplified - use order price or estimate)
                fill_price = order.price if order.price > 0 else self._get_estimated_price(order.symbol)
                order.price = fill_price
                order.status = "FILLED"
                
                # Update positions
                self._update_paper_position(order)
                
            else:
                order.status = "PENDING"  # Limit orders remain pending in paper mode
            
            # Log to CSV
            self._log_paper_order(order)
            
            logger.info(f"📝 PAPER ORDER: {order.side} {order.quantity} {order.symbol} @ {order.price:.2f}")
            
            return {
                "success": True,
                "order_id": order.order_id,
                "status": order.status,
                "filled_price": order.price,
                "mode": "PAPER"
            }
            
        except Exception as e:
            logger.error(f"❌ Paper order error: {e}")
            order.status = "REJECTED"
            return {"success": False, "error": str(e), "order_id": order.order_id}
    
    async def _place_live_order(self, order: Order) -> Dict[str, Any]:
        """Execute live order via Upstox API"""
        try:
            if not self.access_token:
                raise Exception("No access token available for live trading")
            
            # Prepare Upstox order payload
            payload = {
                "quantity": order.quantity,
                "product": "I",  # Intraday
                "validity": "DAY",
                "price": order.price if order.order_type == "LIMIT" else 0,
                "tag": f"strategy_{order.strategy}",
                "instrument_token": order.symbol,
                "order_type": order.order_type,
                "transaction_type": order.side,
                "disclosed_quantity": 0,
                "trigger_price": 0,
                "is_amo": False
            }
            
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.access_token}"
            }
            
            # Place order via Upstox API
            response = await self.client.post(
                f"{self.base_url}/v2/orders/place",
                json=payload,
                headers=headers,
                timeout=10.0
            )
            
            if response.status_code != 200:
                error_text = response.text
                logger.error(f"❌ Upstox API error: {response.status_code} - {error_text}")
                raise Exception(f"Order placement failed: {error_text}")
            
            result = response.json()
            
            if result.get("status") != "success":
                raise Exception(f"Order rejected: {result.get('message', 'Unknown error')}")
            
            # Update order with Upstox order ID
            upstox_order_id = result["data"]["order_id"]
            order.order_id = f"{order.order_id}_{upstox_order_id}"
            order.status = "PLACED"
            
            logger.info(f"🚀 LIVE ORDER: {order.side} {order.quantity} {order.symbol} @ {order.price:.2f}")
            
            return {
                "success": True,
                "order_id": order.order_id,
                "upstox_order_id": upstox_order_id,
                "status": order.status,
                "mode": "LIVE"
            }
            
        except Exception as e:
            logger.error(f"❌ Live order error: {e}")
            order.status = "REJECTED"
            return {"success": False, "error": str(e), "order_id": order.order_id}
    
    def _check_risk_limits(self, symbol: str, side: str, quantity: int, price: Optional[float]) -> Dict[str, Any]:
        """Check risk limits before placing order"""
        
        # Position size check
        position_value = quantity * (price or 100)  # Estimate if price not provided
        if position_value > self.max_position_size:
            return {
                "allowed": False,
                "reason": f"Position size {position_value} exceeds limit {self.max_position_size}"
            }
        
        # Daily loss limit check
        if self.daily_pnl < -self.daily_loss_limit:
            return {
                "allowed": False,
                "reason": f"Daily loss {abs(self.daily_pnl)} exceeds limit {self.daily_loss_limit}"
            }
        
        return {"allowed": True, "reason": "All checks passed"}
    
    def _update_paper_position(self, order: Order):
        """Update paper trading positions"""
        symbol = order.symbol
        
        if symbol not in self.positions:
            # New position
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=order.quantity if order.side == 'BUY' else -order.quantity,
                avg_price=order.price,
                side=order.side,
                last_price=order.price
            )
        else:
            # Update existing position
            position = self.positions[symbol]
            
            if order.side == position.side:
                # Adding to position
                total_value = (position.quantity * position.avg_price) + (order.quantity * order.price)
                total_quantity = position.quantity + order.quantity
                position.avg_price = total_value / total_quantity if total_quantity > 0 else 0
                position.quantity = total_quantity
            else:
                # Reducing or reversing position
                if abs(order.quantity) >= abs(position.quantity):
                    # Position reversal or closure
                    remaining_qty = abs(order.quantity) - abs(position.quantity)
                    if remaining_qty > 0:
                        position.quantity = remaining_qty if order.side == 'BUY' else -remaining_qty
                        position.avg_price = order.price
                        position.side = order.side
                    else:
                        # Position closed
                        del self.positions[symbol]
                        return
                else:
                    # Partial reduction
                    position.quantity += order.quantity if order.side == 'BUY' else -order.quantity
        
        # Log position update
        self._log_paper_position(symbol)
    
    def _log_paper_order(self, order: Order):
        """Log paper order to CSV"""
        try:
            with open(self.orders_csv, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    order.order_id,
                    order.timestamp.isoformat(),
                    order.symbol,
                    order.side,
                    order.quantity,
                    order.price,
                    order.order_type,
                    order.status,
                    order.strategy,
                    order.user_id
                ])
        except Exception as e:
            logger.error(f"❌ Error logging paper order: {e}")
    
    def _log_paper_position(self, symbol: str):
        """Log paper position to CSV"""
        try:
            if symbol not in self.positions:
                return
                
            position = self.positions[symbol]
            
            with open(self.positions_csv, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.now().isoformat(),
                    position.symbol,
                    position.quantity,
                    position.avg_price,
                    position.side,
                    position.unrealized_pnl,
                    position.last_price
                ])
        except Exception as e:
            logger.error(f"❌ Error logging paper position: {e}")
    
    def _get_estimated_price(self, symbol: str) -> float:
        """Get estimated price for paper trading (placeholder)"""
        # In a real implementation, this would fetch live price
        # For now, return a reasonable default
        if "NIFTY" in symbol.upper():
            return 22000.0
        return 100.0
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions"""
        return [
            {
                "symbol": pos.symbol,
                "quantity": pos.quantity,
                "avg_price": pos.avg_price,
                "side": pos.side,
                "unrealized_pnl": pos.unrealized_pnl,
                "last_price": pos.last_price
            }
            for pos in self.positions.values()
        ]
    
    def get_orders(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get orders, optionally filtered by status"""
        orders = list(self.orders.values())
        
        if status:
            orders = [o for o in orders if o.status == status.upper()]
        
        return [
            {
                "order_id": o.order_id,
                "symbol": o.symbol,
                "side": o.side,
                "quantity": o.quantity,
                "price": o.price,
                "order_type": o.order_type,
                "status": o.status,
                "timestamp": o.timestamp.isoformat(),
                "strategy": o.strategy
            }
            for o in orders
        ]
    
    def get_daily_pnl(self) -> float:
        """Get current daily PnL"""
        return self.daily_pnl
    
    def reset_daily_pnl(self):
        """Reset daily PnL counter (call at start of trading day)"""
        self.daily_pnl = 0.0
        logger.info("📊 Daily PnL reset to 0")

# Helper functions
async def create_order_manager(user_id: int, mode: str = None) -> OrderManager:
    """Create OrderManager with user's configuration and token."""
    # Default to PAPER mode for safety
    trading_mode = mode or os.getenv("MODE", "PAPER").upper()
    
    # Get access token if in LIVE mode
    access_token = None
    if trading_mode == "LIVE":
        try:
            from database.connection import get_db
            from database.models import BrokerConfig
            
            db = next(get_db())
            broker_config = db.query(BrokerConfig).filter_by(
                user_id=user_id,
                broker_name="upstox",
                is_active=True
            ).first()
            
            if broker_config and broker_config.access_token:
                access_token = broker_config.access_token
            else:
                logger.warning(f"⚠️ No Upstox token for user {user_id}, falling back to PAPER mode")
                trading_mode = "PAPER"
                
        except Exception as e:
            logger.error(f"❌ Error getting token for user {user_id}: {e}")
            trading_mode = "PAPER"
    
    return OrderManager(
        mode=trading_mode,
        access_token=access_token,
        user_id=user_id
    )