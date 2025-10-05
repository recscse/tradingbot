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

    async def start_tracking(self, db: Session):
        """
        Start real-time PnL tracking loop

        Args:
            db: Database session
        """
        self.is_running = True
        logger.info("🔴 Starting real-time PnL tracking...")

        try:
            while self.is_running:
                await self.update_all_positions(db)
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
                    position.mark_to_market_time = datetime.now()
                    position.last_updated = datetime.now()

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
                        last_updated=datetime.now().isoformat()
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

            # Calculate PnL
            pnl_points = current_price - entry_price
            pnl_amount = pnl_points * Decimal(str(quantity))
            pnl_percent = (pnl_points / entry_price) * Decimal('100') if entry_price > 0 else Decimal('0')

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
                'holding_duration_minutes': int(holding_duration)
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
        Update trailing stop loss

        Args:
            position: Active position
            trade_execution: Trade execution record
            current_price: Current market price

        Returns:
            Updated stop loss level
        """
        try:
            entry_price = Decimal(str(trade_execution.entry_price))
            current_sl = Decimal(str(position.current_stop_loss))

            # Determine position type based on signal
            position_type = "LONG" if "CE" in trade_execution.signal_type else "SHORT"

            # Use SuperTrend 1x as trailing stop
            # In production, fetch actual SuperTrend value from strategy engine
            # For now, use simple percentage trailing

            if position_type == "LONG":
                # For long positions, trail below current price
                if current_price > entry_price:
                    # In profit - activate trailing
                    trailing_percent = Decimal('0.02')  # 2% trailing
                    potential_sl = current_price * (Decimal('1') - trailing_percent)
                    new_sl = max(current_sl, potential_sl)

                    if new_sl > current_sl:
                        position.trailing_stop_triggered = True

                    return new_sl
                else:
                    # Still at initial SL
                    return current_sl
            else:
                # For short positions, trail above current price
                if current_price < entry_price:
                    # In profit - activate trailing
                    trailing_percent = Decimal('0.02')
                    potential_sl = current_price * (Decimal('1') + trailing_percent)
                    new_sl = min(current_sl, potential_sl)

                    if new_sl < current_sl:
                        position.trailing_stop_triggered = True

                    return new_sl
                else:
                    return current_sl

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

            # Calculate final PnL
            entry_price = Decimal(str(trade_execution.entry_price))
            quantity = trade_execution.quantity
            pnl_points = exit_price - entry_price
            gross_pnl = pnl_points * Decimal(str(quantity))

            # Assume 0.5% brokerage + taxes
            brokerage = gross_pnl * Decimal('0.005')
            net_pnl = gross_pnl - brokerage

            pnl_percent = (pnl_points / entry_price) * Decimal('100') if entry_price > 0 else Decimal('0')

            # Update trade execution
            trade_execution.exit_time = datetime.now()
            trade_execution.exit_price = float(exit_price)
            trade_execution.exit_reason = exit_reason
            trade_execution.gross_pnl = float(gross_pnl)
            trade_execution.net_pnl = float(net_pnl)
            trade_execution.pnl_percentage = float(pnl_percent)
            trade_execution.status = "CLOSED"

            # Deactivate position
            position.is_active = False
            position.last_updated = datetime.now()

            db.commit()

            logger.info(f"✅ Position closed: PnL = Rs.{net_pnl:.2f} ({pnl_percent:.2f}%)")

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
            from services.unified_websocket_manager import emit_trading_pnl_update

            for pnl_update in pnl_updates:
                emit_trading_pnl_update({
                    "type": "pnl_update",
                    "data": asdict(pnl_update),
                    "timestamp": datetime.now().isoformat()
                })

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
