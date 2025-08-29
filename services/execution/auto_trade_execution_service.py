"""
Auto Trade Execution Service - Modular Options Trading
Executes trades on selected stocks based on market sentiment and technical signals
Uses fast numpy processing and modular architecture
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, time
from typing import Dict, List, Optional, Any, Tuple
import pytz
import json
from dataclasses import dataclass, asdict
from enum import Enum

# Database imports
from sqlalchemy.orm import Session
from database.connection import SessionLocal
from database.models import (
    SelectedStock, AutoTradingSession, TradeExecution, 
    UserTradingConfig, BrokerConfig
)

# Service imports
from services.auto_stock_selection_service import (
    auto_stock_selection_service, StockSelectionResult
)
from services.live_adapter import live_feed_adapter
from services.upstox_option_service import upstox_option_service

logger = logging.getLogger(__name__)
IST = pytz.timezone('Asia/Kolkata')

class TradeDirection(Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(Enum):
    PENDING = "PENDING"
    PLACED = "PLACED"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"

@dataclass
class TradeSignal:
    """Trade signal for execution"""
    symbol: str
    option_type: str  # CE/PE
    strike_price: float
    direction: TradeDirection
    quantity: int
    trigger_price: float
    stop_loss: float
    target: float
    confidence_score: float
    expiry_date: str
    instrument_key: str
    reason: str

@dataclass
class TradeOrder:
    """Trade order tracking"""
    trade_id: str
    symbol: str
    direction: TradeDirection
    quantity: int
    entry_price: float
    current_price: float
    stop_loss: float
    target: float
    status: OrderStatus
    pnl: float
    pnl_percent: float
    entry_time: datetime
    exit_time: Optional[datetime]
    exit_reason: Optional[str]
    broker_order_id: Optional[str]

class AutoTradeExecutionService:
    """
    Modular Auto Trade Execution Service
    
    Features:
    - Executes trades on selected stocks from AutoStockSelectionService
    - Options trading with CE/PE based on market sentiment
    - Real-time price monitoring and position management
    - Stop-loss and target management
    - Risk management and position sizing
    - Modular broker integration
    """
    
    def __init__(self, user_id: int = 1):
        self.user_id = user_id
        self.live_adapter = live_feed_adapter
        self.option_service = upstox_option_service
        self.selection_service = auto_stock_selection_service
        
        # Configuration
        self.max_concurrent_trades = 2  # Maximum positions at once
        self.default_quantity = 50  # Default lot size
        self.risk_per_trade = 2.0  # Risk per trade in percentage
        self.max_daily_loss = 5.0  # Maximum daily loss in percentage
        
        # Trading state
        self.active_trades: Dict[str, TradeOrder] = {}
        self.daily_pnl = 0.0
        self.trades_executed_today = 0
        self.is_trading_active = False
        
        # Load user configuration
        self._load_user_config()
        
        logger.info(f"✅ AutoTradeExecutionService initialized for user {self.user_id}")
    
    def _load_user_config(self):
        """Load user-specific trading configuration"""
        try:
            db = SessionLocal()
            
            # Get user trading config
            user_config = db.query(UserTradingConfig).filter(
                UserTradingConfig.user_id == self.user_id
            ).first()
            
            if user_config:
                self.default_quantity = user_config.default_qty or self.default_quantity
                self.risk_per_trade = user_config.stop_loss_percent or self.risk_per_trade
                self.max_concurrent_trades = user_config.max_positions or self.max_concurrent_trades
                logger.info(f"✅ Loaded user config: qty={self.default_quantity}, risk={self.risk_per_trade}%")
            
            db.close()
            
        except Exception as e:
            logger.error(f"❌ Failed to load user config: {e}")
    
    async def start_trading_session(self):
        """Start automated trading session"""
        logger.info("🚀 Starting automated trading session...")
        
        try:
            # Check if market is open
            if not self._is_market_open():
                logger.warning("⏰ Market is closed, trading session not started")
                return False
            
            # Get today's selected stocks
            selected_stocks = await self._get_selected_stocks()
            if not selected_stocks:
                logger.warning("📭 No stocks selected for today")
                return False
            
            # Start monitoring and trading
            self.is_trading_active = True
            
            # Register for live price updates
            await self._register_price_callbacks(selected_stocks)
            
            # Generate initial trade signals
            trade_signals = await self._generate_trade_signals(selected_stocks)
            
            # Execute trade signals
            for signal in trade_signals:
                await self._execute_trade_signal(signal)
            
            # Start position monitoring
            asyncio.create_task(self._monitor_positions())
            
            logger.info(f"✅ Trading session started with {len(trade_signals)} signals")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start trading session: {e}")
            return False
    
    async def _get_selected_stocks(self) -> List[StockSelectionResult]:
        """Get today's selected stocks"""
        try:
            db = SessionLocal()
            
            # Get selected stocks from database
            selected_records = db.query(SelectedStock).filter(
                SelectedStock.selection_date == datetime.now().date(),
                SelectedStock.is_active == True
            ).all()
            
            db.close()
            
            if not selected_records:
                return []
            
            # Convert to StockSelectionResult objects
            results = []
            for record in selected_records:
                try:
                    # Parse option contract if available
                    option_contract = None
                    if record.option_contract:
                        option_contract = json.loads(record.option_contract)
                    
                    # Parse score breakdown
                    score_breakdown = {}
                    if record.score_breakdown:
                        score_breakdown = json.loads(record.score_breakdown)
                    
                    result = StockSelectionResult(
                        symbol=record.symbol,
                        sector=record.sector,
                        selection_score=record.selection_score,
                        selection_reason=record.selection_reason,
                        price_at_selection=record.price_at_selection,
                        option_type=record.option_type or "NEUTRAL",
                        option_contract=option_contract,
                        atm_strike=score_breakdown.get("atm_strike"),
                        market_sentiment_alignment=record.option_type in ["CE", "PE"],
                        adr_score=score_breakdown.get("adr_score", 0.5),
                        sector_momentum=score_breakdown.get("sector_momentum", 0.0),
                        volume_score=score_breakdown.get("volume_score", 0.5),
                        technical_score=score_breakdown.get("technical_score", 0.5),
                        expiry_date=record.option_expiry_date,
                        instrument_key=record.instrument_key
                    )
                    results.append(result)
                    
                except Exception as e:
                    logger.error(f"❌ Error processing selected stock {record.symbol}: {e}")
                    continue
            
            logger.info(f"📊 Retrieved {len(results)} selected stocks for trading")
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to get selected stocks: {e}")
            return []
    
    async def _register_price_callbacks(self, selected_stocks: List[StockSelectionResult]):
        """Register for live price updates"""
        try:
            instrument_keys = []
            
            for stock in selected_stocks:
                # Add stock instrument key
                if stock.instrument_key:
                    instrument_keys.append(stock.instrument_key)
                
                # Add option instrument key if available
                if stock.option_contract and stock.option_contract.get("instrument_key"):
                    instrument_keys.append(stock.option_contract["instrument_key"])
            
            # Register callback with live feed adapter
            self.live_adapter.register_tick_callback(
                "auto_trade_execution",
                instrument_keys,
                self._handle_price_update
            )
            
            logger.info(f"📡 Registered for {len(instrument_keys)} price updates")
            
        except Exception as e:
            logger.error(f"❌ Failed to register price callbacks: {e}")
    
    def _handle_price_update(self, instrument_key: str, price_data: Dict):
        """Handle real-time price updates"""
        try:
            # Update active trades
            asyncio.create_task(self._update_trade_positions(instrument_key, price_data))
            
        except Exception as e:
            logger.error(f"❌ Error handling price update for {instrument_key}: {e}")
    
    async def _generate_trade_signals(self, selected_stocks: List[StockSelectionResult]) -> List[TradeSignal]:
        """Generate trade signals from selected stocks"""
        signals = []
        
        for stock in selected_stocks:
            try:
                # Skip if no option type determined
                if stock.option_type == "NEUTRAL":
                    logger.info(f"⏭️ Skipping {stock.symbol} - neutral sentiment")
                    continue
                
                # Get current price for signal validation
                current_price = await self._get_current_price(stock.instrument_key)
                if not current_price:
                    logger.warning(f"⚠️ No current price for {stock.symbol}")
                    continue
                
                # Generate signal based on technical analysis
                signal = await self._analyze_entry_signal(stock, current_price)
                if signal:
                    signals.append(signal)
                    logger.info(f"📈 Generated {signal.direction.value} signal for {signal.symbol} {signal.option_type}")
                
            except Exception as e:
                logger.error(f"❌ Error generating signal for {stock.symbol}: {e}")
                continue
        
        return signals
    
    async def _analyze_entry_signal(
        self, stock: StockSelectionResult, current_price: Dict
    ) -> Optional[TradeSignal]:
        """Analyze if we should enter a trade"""
        try:
            symbol = stock.symbol
            option_type = stock.option_type
            
            # Check if we already have a position in this stock
            if any(symbol in trade_id for trade_id in self.active_trades.keys()):
                logger.info(f"⏭️ Already have position in {symbol}")
                return None
            
            # Get option contract details
            if not stock.option_contract:
                logger.warning(f"⚠️ No option contract for {symbol}")
                return None
            
            option_instrument_key = stock.option_contract.get("instrument_key")
            strike_price = stock.option_contract.get("strike_price", stock.atm_strike)
            lot_size = stock.option_contract.get("lot_size", 50)
            
            if not option_instrument_key:
                logger.warning(f"⚠️ No option instrument key for {symbol}")
                return None
            
            # Get option current price
            option_price_data = await self._get_current_price(option_instrument_key)
            if not option_price_data:
                logger.warning(f"⚠️ No option price data for {symbol} {option_type}")
                return None
            
            option_ltp = option_price_data.get("ltp", 0)
            if option_ltp <= 0:
                logger.warning(f"⚠️ Invalid option price for {symbol} {option_type}")
                return None
            
            # Calculate position size based on risk management
            quantity = self._calculate_position_size(option_ltp, lot_size)
            
            # Calculate stop loss and target
            stop_loss, target = self._calculate_stop_loss_target(option_ltp, option_type)
            
            # Determine entry conditions
            entry_signal = self._check_entry_conditions(
                stock, current_price, option_price_data, option_type
            )
            
            if entry_signal["should_enter"]:
                signal = TradeSignal(
                    symbol=symbol,
                    option_type=option_type,
                    strike_price=strike_price,
                    direction=TradeDirection.BUY,  # Always buy options
                    quantity=quantity,
                    trigger_price=option_ltp,
                    stop_loss=stop_loss,
                    target=target,
                    confidence_score=entry_signal["confidence"],
                    expiry_date=stock.expiry_date or "",
                    instrument_key=option_instrument_key,
                    reason=entry_signal["reason"]
                )
                
                return signal
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error analyzing entry signal for {stock.symbol}: {e}")
            return None
    
    def _check_entry_conditions(
        self, stock: StockSelectionResult, stock_price: Dict, 
        option_price: Dict, option_type: str
    ) -> Dict[str, Any]:
        """Check if entry conditions are met"""
        try:
            reasons = []
            confidence = 0.5
            
            # Technical momentum check
            stock_change = stock_price.get("change_percent", 0)
            if option_type == "CE" and stock_change > 0.5:
                reasons.append("bullish momentum")
                confidence += 0.2
            elif option_type == "PE" and stock_change < -0.5:
                reasons.append("bearish momentum")
                confidence += 0.2
            
            # Volume check
            volume = stock_price.get("volume", 0)
            if volume > stock.volume_score * 1000000:  # Above average volume
                reasons.append("high volume")
                confidence += 0.1
            
            # Option price movement check
            option_change = option_price.get("change_percent", 0)
            if abs(option_change) > 2:  # Significant option movement
                reasons.append("option momentum")
                confidence += 0.1
            
            # Market timing check (avoid first and last 30 minutes)
            current_time = datetime.now(IST).time()
            if time(10, 0) <= current_time <= time(15, 0):
                reasons.append("optimal market timing")
                confidence += 0.1
            
            # Selection score check
            if stock.selection_score > 70:
                reasons.append("high selection score")
                confidence += 0.1
            
            # Entry decision
            should_enter = confidence > 0.7 and len(reasons) >= 2
            
            return {
                "should_enter": should_enter,
                "confidence": min(confidence, 1.0),
                "reason": ", ".join(reasons) if reasons else "neutral conditions"
            }
            
        except Exception as e:
            logger.error(f"❌ Error checking entry conditions: {e}")
            return {"should_enter": False, "confidence": 0.0, "reason": "error in analysis"}
    
    def _calculate_position_size(self, option_price: float, lot_size: int) -> int:
        """Calculate position size based on risk management"""
        try:
            # Calculate maximum loss per trade (2% of capital)
            # Assuming ₹100,000 capital as default
            capital = 100000  # This should come from user configuration
            max_loss = capital * (self.risk_per_trade / 100)
            
            # Calculate quantity based on option price and stop loss
            stop_loss_percent = 0.3  # 30% stop loss on options
            loss_per_lot = option_price * lot_size * stop_loss_percent
            
            if loss_per_lot > 0:
                max_lots = int(max_loss / loss_per_lot)
                quantity = max(1, min(max_lots, 2)) * lot_size  # Limit to 2 lots max
            else:
                quantity = lot_size
            
            return quantity
            
        except Exception as e:
            logger.error(f"❌ Error calculating position size: {e}")
            return self.default_quantity
    
    def _calculate_stop_loss_target(self, option_price: float, option_type: str) -> Tuple[float, float]:
        """Calculate stop loss and target prices"""
        try:
            # Stop loss: 30% below entry for options
            stop_loss = option_price * 0.7
            
            # Target: 50% above entry for options (1.5:1 risk-reward)
            target = option_price * 1.5
            
            return stop_loss, target
            
        except Exception as e:
            logger.error(f"❌ Error calculating stop loss/target: {e}")
            return option_price * 0.8, option_price * 1.2
    
    async def _execute_trade_signal(self, signal: TradeSignal):
        """Execute a trade signal"""
        try:
            # Check concurrent trade limit
            if len(self.active_trades) >= self.max_concurrent_trades:
                logger.warning(f"⚠️ Maximum concurrent trades reached ({self.max_concurrent_trades})")
                return
            
            # Check daily loss limit
            if self.daily_pnl <= -abs(self.max_daily_loss):
                logger.warning(f"⚠️ Daily loss limit reached: {self.daily_pnl:.2f}%")
                return
            
            # Generate trade ID
            trade_id = f"{signal.symbol}_{signal.option_type}_{datetime.now().strftime('%H%M%S')}"
            
            # Get user's trading mode
            trading_mode = await self._get_user_trading_mode()
            
            # Prepare trade order details (SAME for both paper and live)
            trade_order = TradeOrder(
                trade_id=trade_id,
                symbol=signal.symbol,
                direction=signal.direction,
                quantity=signal.quantity,
                entry_price=signal.trigger_price,
                current_price=signal.trigger_price,
                stop_loss=signal.stop_loss,
                target=signal.target,
                status=OrderStatus.PENDING,
                pnl=0.0,
                pnl_percent=0.0,
                entry_time=datetime.now(IST),
                exit_time=None,
                exit_reason=None,
                broker_order_id=None
            )
            
            # ONLY DIFFERENCE: Execute based on trading mode
            if trading_mode == "PAPER":
                # Paper trading: Record virtually, NO broker API call
                trade_order.status = OrderStatus.EXECUTED
                trade_order.broker_order_id = f"PAPER_{trade_id}"
                logger.info(f"📄 PAPER TRADE: {signal.symbol} {signal.option_type} @ ₹{signal.trigger_price}")
            else:
                # Live trading: Call broker API AND record
                broker_result = await self._execute_via_broker(trade_order, signal)
                if broker_result["success"]:
                    trade_order.status = OrderStatus.EXECUTED
                    trade_order.broker_order_id = broker_result["order_id"]
                    trade_order.entry_price = broker_result.get("execution_price", signal.trigger_price)
                    logger.info(f"🔴 LIVE TRADE: {signal.symbol} {signal.option_type} @ ₹{trade_order.entry_price}")
                else:
                    trade_order.status = OrderStatus.REJECTED
                    logger.error(f"❌ LIVE TRADE FAILED: {broker_result.get('error', 'Unknown error')}")
                    return
            
            # Add to active trades
            self.active_trades[trade_id] = trade_order
            self.trades_executed_today += 1
            
            # Store in database
            await self._store_trade_execution(signal, trade_order)
            
            logger.info(
                f"✅ Executed trade: {signal.symbol} {signal.option_type} "
                f"{signal.direction.value} {signal.quantity} @ ₹{signal.trigger_price:.2f}"
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to execute trade signal for {signal.symbol}: {e}")
    
    async def _store_trade_execution(self, signal: TradeSignal, trade_order: TradeOrder):
        """Store trade execution in database"""
        try:
            db = SessionLocal()
            
            trade_execution = TradeExecution(
                user_id=self.user_id,
                symbol=signal.symbol,
                trade_type=signal.direction.value,
                entry_price=signal.trigger_price,
                quantity=signal.quantity,
                entry_time=trade_order.entry_time,
                status="OPEN",
                confidence_score=signal.confidence_score,
                technical_indicators=json.dumps({
                    "option_type": signal.option_type,
                    "strike_price": signal.strike_price,
                    "stop_loss": signal.stop_loss,
                    "target": signal.target,
                    "expiry_date": signal.expiry_date
                }),
                execution_notes=signal.reason
            )
            
            db.add(trade_execution)
            db.commit()
            db.close()
            
        except Exception as e:
            logger.error(f"❌ Failed to store trade execution: {e}")
    
    async def _monitor_positions(self):
        """Monitor active positions for stop loss and target"""
        logger.info("👁️ Starting position monitoring...")
        
        while self.is_trading_active:
            try:
                for trade_id, trade_order in list(self.active_trades.items()):
                    await self._check_exit_conditions(trade_id, trade_order)
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"❌ Error in position monitoring: {e}")
                await asyncio.sleep(10)
    
    async def _check_exit_conditions(self, trade_id: str, trade_order: TradeOrder):
        """Check if we should exit a trade"""
        try:
            current_price = trade_order.current_price
            entry_price = trade_order.entry_price
            
            # Calculate current P&L
            if trade_order.direction == TradeDirection.BUY:
                pnl = (current_price - entry_price) * trade_order.quantity
                pnl_percent = ((current_price - entry_price) / entry_price) * 100
            else:
                pnl = (entry_price - current_price) * trade_order.quantity
                pnl_percent = ((entry_price - current_price) / entry_price) * 100
            
            trade_order.pnl = pnl
            trade_order.pnl_percent = pnl_percent
            
            should_exit = False
            exit_reason = ""
            
            # Stop loss check
            if trade_order.direction == TradeDirection.BUY and current_price <= trade_order.stop_loss:
                should_exit = True
                exit_reason = "STOP_LOSS"
            
            # Target check
            if trade_order.direction == TradeDirection.BUY and current_price >= trade_order.target:
                should_exit = True
                exit_reason = "TARGET"
            
            # Time-based exit (near market close)
            current_time = datetime.now(IST).time()
            if current_time >= time(15, 20):  # 3:20 PM
                should_exit = True
                exit_reason = "TIME_BASED"
            
            # Trailing stop loss (if profitable)
            if pnl_percent > 20:  # 20% profit
                trailing_stop = current_price * 0.9  # 10% trailing stop
                if trade_order.direction == TradeDirection.BUY and current_price <= trailing_stop:
                    should_exit = True
                    exit_reason = "TRAILING_STOP"
            
            if should_exit:
                await self._exit_trade(trade_id, trade_order, exit_reason)
            
        except Exception as e:
            logger.error(f"❌ Error checking exit conditions for {trade_id}: {e}")
    
    async def _exit_trade(self, trade_id: str, trade_order: TradeOrder, exit_reason: str):
        """Exit a trade"""
        try:
            trade_order.exit_time = datetime.now(IST)
            trade_order.exit_reason = exit_reason
            trade_order.status = OrderStatus.EXECUTED
            
            # Update daily P&L
            self.daily_pnl += trade_order.pnl_percent
            
            # Remove from active trades
            if trade_id in self.active_trades:
                del self.active_trades[trade_id]
            
            # Update database
            await self._update_trade_in_db(trade_order)
            
            logger.info(
                f"🔚 Exited trade: {trade_order.symbol} "
                f"P&L: ₹{trade_order.pnl:.2f} ({trade_order.pnl_percent:.1f}%) "
                f"Reason: {exit_reason}"
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to exit trade {trade_id}: {e}")
    
    async def _update_trade_in_db(self, trade_order: TradeOrder):
        """Update trade execution in database"""
        try:
            db = SessionLocal()
            
            # Find the trade execution record
            trade_execution = db.query(TradeExecution).filter(
                TradeExecution.symbol == trade_order.symbol,
                TradeExecution.entry_time == trade_order.entry_time,
                TradeExecution.user_id == self.user_id
            ).first()
            
            if trade_execution:
                trade_execution.exit_price = trade_order.current_price
                trade_execution.exit_time = trade_order.exit_time
                trade_execution.pnl = trade_order.pnl
                trade_execution.pnl_percentage = trade_order.pnl_percent
                trade_execution.status = "CLOSED"
                trade_execution.exit_reason = trade_order.exit_reason
                
                db.commit()
            
            db.close()
            
        except Exception as e:
            logger.error(f"❌ Failed to update trade in database: {e}")
    
    async def _update_trade_positions(self, instrument_key: str, price_data: Dict):
        """Update trade positions with new prices"""
        try:
            current_ltp = price_data.get("ltp", 0)
            if current_ltp <= 0:
                return
            
            # Find trades using this instrument
            for trade_id, trade_order in self.active_trades.items():
                # This is a simplified check - in reality you'd match instrument keys properly
                if instrument_key in trade_order.symbol:  # Simplified matching
                    trade_order.current_price = current_ltp
                    
        except Exception as e:
            logger.error(f"❌ Error updating trade positions: {e}")
    
    async def _get_current_price(self, instrument_key: str) -> Optional[Dict]:
        """Get current price for an instrument"""
        try:
            return self.live_adapter.get_latest_price(instrument_key)
        except Exception as e:
            logger.error(f"❌ Error getting current price for {instrument_key}: {e}")
            return None
    
    async def _get_user_trading_mode(self) -> str:
        """Get user's current trading mode (PAPER or LIVE)"""
        try:
            db = SessionLocal()
            
            # Get user trading config
            user_config = db.query(UserTradingConfig).filter(
                UserTradingConfig.user_id == self.user_id
            ).first()
            
            db.close()
            
            if user_config and user_config.trade_mode:
                return user_config.trade_mode.upper()
            
            # Default to paper trading for safety
            return "PAPER"
            
        except Exception as e:
            logger.error(f"❌ Error getting user trading mode: {e}")
            return "PAPER"  # Safe default
    
    async def _execute_via_broker(self, trade_order: TradeOrder, signal: TradeSignal) -> Dict[str, Any]:
        """Execute trade via broker API for live trading"""
        try:
            # Get user's broker configuration
            db = SessionLocal()
            broker_config = db.query(BrokerConfig).filter(
                BrokerConfig.user_id == self.user_id,
                BrokerConfig.is_active == True
            ).first()
            db.close()
            
            if not broker_config:
                return {"success": False, "error": "No active broker configuration found"}
            
            # Import broker service based on configuration
            broker_name = broker_config.broker_name.lower()
            
            if broker_name == "upstox":
                from brokers.upstox_broker import upstox_broker_service
                broker_service = upstox_broker_service
            elif broker_name == "angelone":
                from brokers.angelone_broker import angelone_broker_service  
                broker_service = angelone_broker_service
            elif broker_name == "dhan":
                from brokers.dhan_broker import dhan_broker_service
                broker_service = dhan_broker_service
            else:
                return {"success": False, "error": f"Unsupported broker: {broker_name}"}
            
            # Prepare order data for broker API
            order_data = {
                "symbol": signal.symbol,
                "instrument_key": signal.instrument_key,
                "quantity": signal.quantity,
                "price": signal.trigger_price,
                "order_type": "LIMIT",
                "product": "MIS",  # Intraday for options
                "validity": "DAY",
                "disclosed_quantity": 0,
                "transaction_type": signal.direction.value
            }
            
            # Execute order via broker
            result = await broker_service.place_order(self.user_id, order_data)
            
            if result["success"]:
                logger.info(f"🔴 LIVE ORDER PLACED: {signal.symbol} {signal.option_type} via {broker_name.upper()}")
                return {
                    "success": True,
                    "order_id": result.get("order_id"),
                    "execution_price": result.get("execution_price", signal.trigger_price),
                    "broker_used": broker_name
                }
            else:
                logger.error(f"❌ LIVE ORDER FAILED: {result.get('error', 'Unknown broker error')}")
                return {
                    "success": False,
                    "error": result.get("error", "Broker order failed")
                }
                
        except Exception as e:
            logger.error(f"❌ Error executing via broker: {e}")
            return {"success": False, "error": str(e)}
    
    def _is_market_open(self) -> bool:
        """Check if market is open for trading"""
        current_time = datetime.now(IST).time()
        market_start = time(9, 15)  # 9:15 AM
        market_end = time(15, 30)   # 3:30 PM
        
        return market_start <= current_time <= market_end
    
    async def stop_trading_session(self):
        """Stop the trading session"""
        logger.info("🛑 Stopping trading session...")
        
        self.is_trading_active = False
        
        # Exit all active trades
        for trade_id, trade_order in list(self.active_trades.items()):
            await self._exit_trade(trade_id, trade_order, "SESSION_END")
        
        # Unregister price callbacks
        self.live_adapter.unregister_callback("auto_trade_execution")
        
        logger.info(f"✅ Trading session stopped. Daily P&L: {self.daily_pnl:.2f}%")
    
    def get_trading_stats(self) -> Dict[str, Any]:
        """Get current trading statistics"""
        return {
            "is_active": self.is_trading_active,
            "active_trades": len(self.active_trades),
            "trades_executed_today": self.trades_executed_today,
            "daily_pnl": self.daily_pnl,
            "active_positions": [
                {
                    "symbol": trade.symbol,
                    "direction": trade.direction.value,
                    "pnl_percent": trade.pnl_percent,
                    "status": trade.status.value
                }
                for trade in self.active_trades.values()
            ]
        }

# Global service instance
auto_trade_execution_service = AutoTradeExecutionService()

async def start_auto_trade_execution():
    """Start the auto trade execution service"""
    logger.info("🚀 Starting Auto Trade Execution Service...")
    return auto_trade_execution_service