"""
Real-Time PnL Tracker
Monitors active positions and calculates live PnL with WebSocket updates
"""

import logging
import asyncio
from decimal import Decimal
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from database.models import ActivePosition, AutoTradeExecution
from services.trading_execution.strategy_engine import (
    strategy_engine,
    SignalType,
    TrailingStopType
)
from utils.timezone_utils import get_ist_now_naive, get_ist_isoformat

logger = logging.getLogger(__name__)


@dataclass
class PositionPnL:
    """
    Real-time position PnL details

    Attributes:
        position_id: Active position ID
        trade_id: Trade identifier
        user_id: User identifier
        symbol: Stock symbol
        instrument_key: Option instrument key
        entry_price: Entry price
        current_price: Current market price
        quantity: Position quantity
        pnl: Current profit/loss amount
        pnl_percent: Current PnL percentage
        pnl_points: Points gained/lost
        entry_time: Trade entry timestamp
        holding_duration_minutes: Duration in trade (minutes)
        stop_loss: Current stop loss level
        target: Target price
        highest_price: Highest price reached
        trailing_sl_active: Whether trailing SL is active
        status: Position status
        last_updated: Last update timestamp
    """
    position_id: int
    trade_id: str
    user_id: int
    symbol: str
    instrument_key: str
    entry_price: Decimal
    current_price: Decimal
    quantity: int
    pnl: Decimal
    pnl_percent: Decimal
    pnl_points: Decimal
    entry_time: str
    holding_duration_minutes: int
    stop_loss: Decimal
    target: Decimal
    highest_price: Decimal
    trailing_sl_active: bool
    status: str
    last_updated: str


class RealTimePnLTracker:
    """
    Real-time PnL tracking system

    Features:
    - Monitors all active positions
    - Calculates live PnL from market data
    - Updates trailing stop losses
    - Detects target/SL hits
    - Broadcasts updates via WebSocket
    - Auto-exits positions when conditions met
    """

    def __init__(self):
        """Initialize PnL tracker"""
        self.update_interval_seconds = 1  # Update every 1 second
        self.is_running = False
        logger.info("Real-Time PnL Tracker initialized")

    async def start_tracking(self, db: Session = None):
        """
        Start real-time PnL tracking loop

        Args:
            db: Database session (optional, will create own session if not provided)
        """
        self.is_running = True
        logger.info("🔴 Starting real-time PnL tracking...")

        # Import database connection
        from database.connection import SessionLocal

        try:
            while self.is_running:
                # Create new session for each iteration to avoid stale connections
                session = SessionLocal()
                try:
                    await self.update_all_positions(session)
                finally:
                    session.close()

                await asyncio.sleep(self.update_interval_seconds)

        except Exception as e:
            logger.error(f"Error in PnL tracking loop: {e}")
            self.is_running = False

    def stop_tracking(self):
        """Stop real-time PnL tracking"""
        self.is_running = False
        logger.info("⏹️ Stopped real-time PnL tracking")

    async def update_all_positions(self, db: Session):
        """
        Update all active positions with live PnL

        Args:
            db: Database session
        """
        try:
            # Get all active positions
            active_positions = db.query(ActivePosition).filter(
                ActivePosition.is_active == True
            ).all()

            if not active_positions:
                return

            # Get live market data
            from services.realtime_market_engine import get_market_engine
            market_engine = get_market_engine()

            pnl_updates = []

            for position in active_positions:
                try:
                    # Get current price from market engine
                    current_price = self._get_current_price(
                        position.instrument_key,
                        market_engine
                    )

                    if current_price <= 0:
                        logger.debug(f"No price data for {position.instrument_key}")
                        continue

                    # Get trade execution details
                    trade_execution = db.query(AutoTradeExecution).filter(
                        AutoTradeExecution.id == position.trade_execution_id
                    ).first()

                    if not trade_execution:
                        continue

                    # Calculate PnL
                    pnl_data = self._calculate_pnl(
                        position,
                        trade_execution,
                        current_price
                    )

                    # Update trailing stop loss
                    updated_sl = self._update_trailing_stop_loss(
                        position,
                        trade_execution,
                        current_price
                    )

                    # Check exit conditions
                    should_exit, exit_reason = self._check_exit_conditions(
                        position,
                        trade_execution,
                        current_price,
                        pnl_data
                    )

                    # Update position in database
                    position.current_price = float(current_price)
                    position.current_pnl = float(pnl_data['pnl'])
                    position.current_pnl_percentage = float(pnl_data['pnl_percent'])
                    position.current_stop_loss = float(updated_sl)
                    position.highest_price_reached = float(pnl_data['highest_price'])
                    position.mark_to_market_time = get_ist_now_naive()
                    position.last_updated = get_ist_now_naive()

                    # If exit condition met, close position
                    if should_exit:
                        await self._close_position(
                            position,
                            trade_execution,
                            current_price,
                            exit_reason,
                            db
                        )

                    # Prepare PnL update for broadcasting
                    pnl_update = PositionPnL(
                        position_id=position.id,
                        trade_id=trade_execution.trade_id,
                        user_id=position.user_id,
                        symbol=position.symbol,
                        instrument_key=position.instrument_key,
                        entry_price=Decimal(str(trade_execution.entry_price)),
                        current_price=current_price,
                        quantity=trade_execution.quantity,
                        pnl=pnl_data['pnl'],
                        pnl_percent=pnl_data['pnl_percent'],
                        pnl_points=pnl_data['pnl_points'],
                        entry_time=trade_execution.entry_time.isoformat(),
                        holding_duration_minutes=pnl_data['holding_duration_minutes'],
                        stop_loss=updated_sl,
                        target=Decimal(str(trade_execution.target_1)),
                        highest_price=pnl_data['highest_price'],
                        trailing_sl_active=position.trailing_stop_triggered,
                        status="CLOSED" if should_exit else "ACTIVE",
                        last_updated=get_ist_isoformat()
                    )

                    pnl_updates.append(pnl_update)

                except Exception as e:
                    logger.error(f"Error updating position {position.id}: {e}")
                    continue

            # Commit all updates
            db.commit()

            # Broadcast PnL updates via WebSocket
            if pnl_updates:
                await self._broadcast_pnl_updates(pnl_updates)

        except Exception as e:
            logger.error(f"Error updating all positions: {e}")
            db.rollback()

    def _get_current_price(
        self,
        instrument_key: str,
        market_engine: Any
    ) -> Decimal:
        """
        Get current price from market engine

        Args:
            instrument_key: Instrument key
            market_engine: Market engine instance

        Returns:
            Current price or 0 if not available
        """
        try:
            if instrument_key in market_engine.instruments:
                instrument = market_engine.instruments[instrument_key]
                return Decimal(str(instrument.current_price))
            return Decimal('0')

        except Exception as e:
            logger.debug(f"Error getting price for {instrument_key}: {e}")
            return Decimal('0')

    def _calculate_pnl(
        self,
        position: ActivePosition,
        trade_execution: AutoTradeExecution,
        current_price: Decimal
    ) -> Dict[str, Any]:
        """
        Calculate position PnL

        Args:
            position: Active position
            trade_execution: Trade execution record
            current_price: Current market price

        Returns:
            Dict with PnL calculations
        """
        try:
            entry_price = Decimal(str(trade_execution.entry_price))
            quantity = trade_execution.quantity

            # Get total investment (use from trade record if available, else calculate)
            total_investment = Decimal(str(trade_execution.total_investment)) if trade_execution.total_investment else (entry_price * Decimal(str(quantity)))

            # Calculate PnL
            pnl_points = current_price - entry_price
            pnl_amount = pnl_points * Decimal(str(quantity))

            # CRITICAL FIX: Calculate percentage based on total_investment, not per-unit price
            pnl_percent = (pnl_amount / total_investment) * Decimal('100') if total_investment > 0 else Decimal('0')

            # Track highest price
            highest_price = max(
                Decimal(str(position.highest_price_reached)),
                current_price
            )

            # Calculate holding duration
            entry_time = trade_execution.entry_time
            holding_duration = (datetime.now() - entry_time).total_seconds() / 60

            return {
                'pnl': pnl_amount,
                'pnl_percent': pnl_percent,
                'pnl_points': pnl_points,
                'highest_price': highest_price,
                'holding_duration_minutes': int(holding_duration),
                'total_investment': total_investment
            }

        except Exception as e:
            logger.error(f"Error calculating PnL: {e}")
            return {
                'pnl': Decimal('0'),
                'pnl_percent': Decimal('0'),
                'pnl_points': Decimal('0'),
                'highest_price': Decimal(str(position.highest_price_reached)),
                'holding_duration_minutes': 0
            }

    def _update_trailing_stop_loss(
        self,
        position: ActivePosition,
        trade_execution: AutoTradeExecution,
        current_price: Decimal
    ) -> Decimal:
        """
        Update trailing stop loss using ENHANCED strategy engine with LOCK PROFIT mechanism

        ENHANCED LOGIC (from strategy_engine.py):
        1. If profit >= 50% of target: Trail to BREAKEVEN (make position risk-free)
        2. If profit >= 100% of target: Lock 80% of profit
        3. Otherwise: Use SuperTrend/ATR/percentage trailing

        Args:
            position: Active position
            trade_execution: Trade execution record
            current_price: Current market price

        Returns:
            Updated stop loss level
        """
        try:
            from services.trading_execution.strategy_engine import strategy_engine, TrailingStopType

            entry_price = Decimal(str(trade_execution.entry_price))
            current_sl = Decimal(str(position.current_stop_loss))
            target_price = Decimal(str(trade_execution.target_1)) if trade_execution.target_1 else None

            # Determine position type (both CE and PE are long positions when buying options)
            position_type = "LONG"

            # Get SuperTrend value from shared registry
            supertrend_value = None
            try:
                from services.trading_execution.shared_instrument_registry import shared_registry

                instrument = shared_registry.get_instrument(position.instrument_key)

                if instrument and hasattr(instrument, 'last_signal') and instrument.last_signal:
                    supertrend_raw = instrument.last_signal.indicators.get('supertrend_1x')
                    if supertrend_raw and supertrend_raw > 0:
                        supertrend_value = Decimal(str(supertrend_raw))

            except Exception as e:
                logger.debug(f"Could not fetch SuperTrend for trailing SL: {e}")

            # Use strategy engine's ENHANCED trailing stop with LOCK PROFIT
            new_sl = strategy_engine.update_trailing_stop(
                current_price=current_price,
                entry_price=entry_price,
                current_stop_loss=current_sl,
                trailing_type=TrailingStopType.SUPERTREND_1X,
                supertrend_value=supertrend_value,
                position_type=position_type,
                target_price=target_price  # Pass target for lock profit calculation
            )

            # Update trailing stop triggered flag
            if new_sl > current_sl:
                position.trailing_stop_triggered = True
                logger.info(
                    f"Enhanced trailing SL updated: "
                    f"{current_sl:.2f} -> {new_sl:.2f} for position {position.id}"
                )

            return new_sl

        except Exception as e:
            logger.error(f"Error updating trailing SL: {e}")
            return Decimal(str(position.current_stop_loss))

    def _check_exit_conditions(
        self,
        position: ActivePosition,
        trade_execution: AutoTradeExecution,
        current_price: Decimal,
        pnl_data: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Check if position should be exited

        Args:
            position: Active position
            trade_execution: Trade execution record
            current_price: Current market price
            pnl_data: PnL calculation data

        Returns:
            Tuple of (should_exit, exit_reason)
        """
        try:
            entry_price = Decimal(str(trade_execution.entry_price))
            stop_loss = Decimal(str(position.current_stop_loss))
            target_1 = Decimal(str(trade_execution.target_1))

            position_type = "LONG" if "CE" in trade_execution.signal_type else "SHORT"

            # Check stop loss hit
            if position_type == "LONG":
                if current_price <= stop_loss:
                    return True, "STOP_LOSS_HIT"
            else:
                if current_price >= stop_loss:
                    return True, "STOP_LOSS_HIT"

            # Check target hit
            if position_type == "LONG":
                if current_price >= target_1:
                    return True, "TARGET_HIT"
            else:
                if current_price <= target_1:
                    return True, "TARGET_HIT"

            # Check time-based exit (e.g., close before market close)
            current_time = datetime.now().time()
            if current_time.hour >= 15 and current_time.minute >= 20:
                return True, "TIME_BASED_EXIT"

            return False, None

        except Exception as e:
            logger.error(f"Error checking exit conditions: {e}")
            return False, None

    async def _place_exit_order(
        self,
        trade_execution: AutoTradeExecution,
        exit_price: Decimal,
        db: Session
    ) -> Optional[str]:
        """
        Place exit order (SELL) to close position

        Args:
            trade_execution: Trade execution record
            exit_price: Expected exit price
            db: Database session

        Returns:
            Order ID if successful, None if failed or paper trading
        """
        try:
            # Skip if paper trading
            if trade_execution.trading_mode == "paper":
                logger.info(f"Paper trading - skipping actual exit order placement")
                return None

            # Get broker configuration
            from database.models import BrokerConfig

            broker_config = (
                db.query(BrokerConfig)
                .filter(
                    BrokerConfig.id == trade_execution.broker_config_id,
                    BrokerConfig.is_active == True
                )
                .first()
            )

            if not broker_config:
                logger.error(f"No active broker config found for trade {trade_execution.trade_id}")
                return None

            broker_name = broker_config.broker_name.lower()
            quantity = trade_execution.quantity

            # Place SELL order based on broker
            if "upstox" in broker_name:
                from services.upstox.upstox_order_service import get_upstox_order_service

                # Get Upstox Order Service with V3 API
                order_service = get_upstox_order_service(
                    access_token=broker_config.access_token,
                    use_sandbox=False
                )

                # Place exit (SELL) order using V3 API
                result = order_service.place_order_v3(
                    quantity=quantity,
                    instrument_token=trade_execution.instrument_key,
                    order_type="MARKET",
                    transaction_type="SELL",  # SELL to exit position
                    product="I",  # Intraday
                    validity="DAY",
                    price=0.0,  # Market order
                    trigger_price=0.0,
                    disclosed_quantity=0,
                    is_amo=False,
                    tag=f"exit_{trade_execution.trade_id}",
                    slice=True  # Enable auto-slicing
                )

                if not result.get("success"):
                    logger.error(f"Upstox exit order failed: {result.get('message')}")
                    return None

                # Extract order IDs
                order_ids = result.get("data", {}).get("order_ids", [])
                primary_order_id = order_ids[0] if order_ids else None
                latency = result.get("metadata", {}).get("latency", 0)

                logger.info(
                    f"Upstox V3 exit order placed: {len(order_ids)} orders, "
                    f"latency: {latency}ms, IDs: {order_ids}"
                )

                return primary_order_id

            elif "angel" in broker_name:
                from brokers.angel_broker import AngelOneBroker

                broker = AngelOneBroker(broker_config)

                order_result = broker.place_order(
                    symbol=trade_execution.symbol,
                    quantity=quantity,
                    order_type="MARKET",
                    transaction_type="SELL",
                )

                return order_result.get("orderid")

            elif "dhan" in broker_name:
                from brokers.dhan_broker import DhanBroker

                broker = DhanBroker(broker_config)

                order_result = broker.place_order(
                    instrument_key=trade_execution.instrument_key,
                    quantity=quantity,
                    order_type="MARKET",
                    transaction_type="SELL",
                )

                return order_result.get("orderId")

            else:
                logger.error(f"Unsupported broker for exit order: {broker_name}")
                return None

        except Exception as e:
            logger.error(f"Error placing exit order: {e}")
            return None

    async def _close_position(
        self,
        position: ActivePosition,
        trade_execution: AutoTradeExecution,
        exit_price: Decimal,
        exit_reason: str,
        db: Session
    ):
        """
        Close position and update trade execution

        Args:
            position: Active position to close
            trade_execution: Associated trade execution
            exit_price: Exit price
            exit_reason: Reason for exit
            db: Database session
        """
        try:
            logger.info(f"🚪 Closing position {trade_execution.trade_id}: {exit_reason}")

            # Place exit order if live trading
            exit_order_id = None
            if trade_execution.trading_mode == "live":
                exit_order_id = await self._place_exit_order(
                    trade_execution,
                    exit_price,
                    db
                )

            # Calculate final PnL
            entry_price = Decimal(str(trade_execution.entry_price))
            quantity = trade_execution.quantity
            total_investment = Decimal(str(trade_execution.total_investment)) if trade_execution.total_investment else (entry_price * Decimal(str(quantity)))

            pnl_points = exit_price - entry_price
            gross_pnl = pnl_points * Decimal(str(quantity))

            # Assume 0.5% brokerage + taxes
            brokerage = gross_pnl * Decimal('0.005')
            net_pnl = gross_pnl - brokerage

            # CRITICAL FIX: Calculate percentage based on total_investment
            pnl_percent = (net_pnl / total_investment) * Decimal('100') if total_investment > 0 else Decimal('0')

            # Update trade execution
            trade_execution.exit_time = get_ist_now_naive()
            trade_execution.exit_price = float(exit_price)
            trade_execution.exit_order_id = exit_order_id
            trade_execution.exit_reason = exit_reason
            trade_execution.gross_pnl = float(gross_pnl)
            trade_execution.net_pnl = float(net_pnl)
            trade_execution.pnl_percentage = float(pnl_percent)
            trade_execution.status = "CLOSED"

            # Deactivate position
            position.is_active = False
            position.last_updated = get_ist_now_naive()

            db.commit()

            logger.info(f"✅ Position closed: PnL = Rs.{net_pnl:.2f} ({pnl_percent:.2f}%)")

            # Broadcast position close event to UI
            try:
                from router.unified_websocket_routes import broadcast_to_clients

                close_data = {
                    "position_id": position.id,
                    "trade_id": trade_execution.trade_id,
                    "user_id": position.user_id,
                    "symbol": position.symbol,
                    "instrument_key": position.instrument_key,
                    "entry_price": float(entry_price),
                    "exit_price": float(exit_price),
                    "quantity": quantity,
                    "gross_pnl": float(gross_pnl),
                    "net_pnl": float(net_pnl),
                    "pnl_percent": float(pnl_percent),
                    "pnl_points": float(pnl_points),
                    "exit_reason": exit_reason,
                    "entry_time": trade_execution.entry_time.isoformat(),
                    "exit_time": datetime.now().isoformat(),
                    "holding_duration_minutes": int((datetime.now() - trade_execution.entry_time).total_seconds() / 60),
                    "timestamp": datetime.now().isoformat()
                }

                await broadcast_to_clients("position_closed", close_data)
                logger.info(f"Broadcasted position close event for trade {trade_execution.trade_id}")

            except Exception as broadcast_error:
                logger.error(f"Error broadcasting position close: {broadcast_error}")

        except Exception as e:
            logger.error(f"Error closing position: {e}")
            db.rollback()

    async def _broadcast_pnl_updates(self, pnl_updates: List[PositionPnL]):
        """
        Broadcast PnL updates via WebSocket

        Args:
            pnl_updates: List of position PnL updates
        """
        try:
            from router.unified_websocket_routes import broadcast_to_clients

            for pnl_update in pnl_updates:
                # Format data to match frontend expectations
                update_data = {
                    "position_id": pnl_update.position_id,
                    "trade_id": pnl_update.trade_id,
                    "user_id": pnl_update.user_id,
                    "symbol": pnl_update.symbol,
                    "current_price": float(pnl_update.current_price),
                    "pnl": float(pnl_update.pnl),
                    "pnl_percent": float(pnl_update.pnl_percent),
                    "stop_loss": float(pnl_update.stop_loss),
                    "target": float(pnl_update.target),
                    "trailing_sl_active": pnl_update.trailing_sl_active,
                    "highest_price": float(pnl_update.highest_price),
                    "last_updated": pnl_update.last_updated,
                    "timestamp": datetime.now().isoformat()
                }

                await broadcast_to_clients("pnl_update", update_data)
                logger.debug(f"Broadcasted PnL update for position {pnl_update.position_id}")

        except Exception as e:
            logger.error(f"Error broadcasting PnL updates: {e}")

    def get_user_positions_summary(
        self,
        user_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """
        Get summary of all positions for a user

        Args:
            user_id: User identifier
            db: Database session

        Returns:
            Summary dict with aggregate PnL and positions
        """
        try:
            active_positions = db.query(ActivePosition).filter(
                and_(
                    ActivePosition.user_id == user_id,
                    ActivePosition.is_active == True
                )
            ).all()

            total_pnl = sum(
                Decimal(str(pos.current_pnl)) for pos in active_positions
            )

            total_investment = Decimal('0')
            for pos in active_positions:
                trade = db.query(AutoTradeExecution).filter(
                    AutoTradeExecution.id == pos.trade_execution_id
                ).first()
                if trade:
                    total_investment += Decimal(str(trade.entry_price)) * Decimal(str(trade.quantity))

            return {
                "user_id": user_id,
                "active_positions_count": len(active_positions),
                "total_pnl": float(total_pnl),
                "total_investment": float(total_investment),
                "pnl_percent": float((total_pnl / total_investment * Decimal('100')) if total_investment > 0 else Decimal('0')),
                "last_updated": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting user positions summary: {e}")
            return {
                "user_id": user_id,
                "error": str(e)
            }


# Create singleton instance
pnl_tracker = RealTimePnLTracker()
