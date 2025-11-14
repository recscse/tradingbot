"""
Trade Execution Handler
Handles both paper trading (virtual) and live trading (real broker API) execution
"""

import logging
import uuid
from decimal import Decimal
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from sqlalchemy.orm import Session

from database.models import AutoTradeExecution, ActivePosition, User, BrokerConfig
from services.trading_execution.capital_manager import TradingMode
from services.trading_execution.trade_prep import PreparedTrade, TradeStatus

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """
    Trade execution result

    Attributes:
        success: Whether execution succeeded
        trade_id: Unique trade identifier
        order_id: Broker order ID (or paper trade ID)
        entry_price: Actual entry price
        quantity: Actual quantity executed
        status: Execution status
        message: Execution message/reason
        trade_execution_id: Database ID for trade execution record
        active_position_id: Database ID for active position record
        timestamp: Execution timestamp
        metadata: Additional execution metadata
    """

    success: bool
    trade_id: str
    order_id: Optional[str]
    entry_price: Decimal
    quantity: int
    status: str
    message: str
    trade_execution_id: Optional[int]
    active_position_id: Optional[int]
    timestamp: str
    metadata: Dict[str, Any]


class TradeExecutionHandler:
    """
    Handles trade execution for both paper and live trading

    Features:
    - Paper trading: Virtual execution with mock orders
    - Live trading: Real execution via broker API
    - Creates trade execution records
    - Creates active position for monitoring
    - Validates all parameters before execution
    - Logs execution details for tracking
    """

    def __init__(self):
        """Initialize execution handler"""
        logger.info("Trade Execution Handler initialized")

    def execute_trade(
        self,
        prepared_trade: PreparedTrade,
        db: Session,
        parent_trade_id: Optional[str] = None,
        broker_name: Optional[str] = None,
        broker_id: Optional[int] = None,
        allocated_capital: Optional[float] = None,
    ) -> ExecutionResult:
        """
        Execute trade (paper or live based on trading_mode)

        Args:
            prepared_trade: Prepared trade with all execution details
            db: Database session

        Returns:
            ExecutionResult with execution details

        Raises:
            ValueError: If prepared_trade is invalid
        """
        if not prepared_trade:
            raise ValueError("Prepared trade cannot be None")

        if prepared_trade.status != TradeStatus.READY:
            return ExecutionResult(
                success=False,
                trade_id="",
                order_id=None,
                entry_price=Decimal("0"),
                quantity=0,
                status="FAILED",
                message=f"Trade not ready for execution: {prepared_trade.status.value}",
                trade_execution_id=None,
                active_position_id=None,
                timestamp=datetime.now().isoformat(),
                metadata={"error": "Trade not ready"},
            )

        try:
            trading_mode = TradingMode(prepared_trade.trading_mode)

            if trading_mode == TradingMode.PAPER:
                return self._execute_paper_trade(
                    prepared_trade,
                    db,
                    broker_name=broker_name,
                    broker_id=broker_id,
                    allocated_capital=allocated_capital,
                )
            else:
                return self._execute_live_trade(prepared_trade, db)

        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return ExecutionResult(
                success=False,
                trade_id="",
                order_id=None,
                entry_price=Decimal("0"),
                quantity=0,
                status="ERROR",
                message=str(e),
                trade_execution_id=None,
                active_position_id=None,
                timestamp=datetime.now().isoformat(),
                metadata={"error": str(e)},
            )

    def _execute_paper_trade(
        self,
        prepared_trade: PreparedTrade,
        db: Session,
        broker_name: Optional[str] = None,
        broker_id: Optional[int] = None,
        allocated_capital: Optional[float] = None,
    ) -> ExecutionResult:
        """
        Execute paper trade (virtual/mock execution)

        Args:
            prepared_trade: Prepared trade details
            db: Database session

        Returns:
            ExecutionResult with virtual execution details
        """
        try:
            # Generate unique trade ID
            trade_id = f"PAPER_{uuid.uuid4().hex[:12].upper()}"

            # Generate mock order ID
            order_id = f"PT{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"

            # Simulate execution at prepared entry price
            entry_price = prepared_trade.entry_price
            quantity = prepared_trade.position_size_lots * prepared_trade.lot_size
            lots_traded = prepared_trade.position_size_lots
            total_investment = entry_price * Decimal(str(quantity))

            logger.info(f"Executing PAPER trade: {trade_id}")
            logger.info(f"  Symbol: {prepared_trade.stock_symbol}")
            logger.info(
                f"  Option: {prepared_trade.option_type} {prepared_trade.strike_price}"
            )
            logger.info(f"  Entry: Rs.{entry_price}, Qty: {quantity}, Lots: {lots_traded}")
            logger.info(f"  Total Investment: Rs.{total_investment:,.2f}")

            # Create trade execution record
            trade_execution = AutoTradeExecution(
                user_id=prepared_trade.user_id,
                trade_id=trade_id,
                symbol=prepared_trade.stock_symbol,
                instrument_key=prepared_trade.option_instrument_key,
                strategy_name="supertrend_ema",
                signal_type=f"BUY_{prepared_trade.option_type}",
                signal_strength=float(
                    prepared_trade.metadata.get("signal_confidence", 0) * 100
                ),
                entry_time=datetime.now(),
                entry_price=float(entry_price),
                entry_order_id=order_id,
                quantity=quantity,
                lot_size=prepared_trade.lot_size,
                lots_traded=lots_traded,
                total_investment=float(total_investment),
                initial_stop_loss=float(prepared_trade.stop_loss),
                target_1=float(prepared_trade.target_price),
                target_2=float(
                    prepared_trade.target_price * Decimal("1.1")
                ),  # 10% beyond first target
                status="ACTIVE",
                # Multi-demat support
                broker_name=broker_name or "Paper Trading",
                broker_config_id=broker_id,
                allocated_capital=allocated_capital,
                parent_trade_id=None,
                trading_mode=prepared_trade.trading_mode,
            )

            db.add(trade_execution)
            db.flush()  # Get the ID

            # Create active position for real-time tracking
            active_position = ActivePosition(
                trade_execution_id=trade_execution.id,
                user_id=prepared_trade.user_id,
                symbol=prepared_trade.stock_symbol,
                instrument_key=prepared_trade.option_instrument_key,
                current_price=float(entry_price),
                current_pnl=0.0,
                current_pnl_percentage=0.0,
                current_stop_loss=float(prepared_trade.stop_loss),
                trailing_stop_triggered=False,
                highest_price_reached=float(entry_price),
                unrealized_risk=float(prepared_trade.max_loss_amount),
                mark_to_market_time=datetime.now(),
                is_active=True,
                last_updated=datetime.now(),
            )

            db.add(active_position)
            db.commit()

            logger.info(f"✅ Paper trade executed successfully: {trade_id}")
            logger.info(f"  Trade Execution ID: {trade_execution.id}")
            logger.info(f"  Active Position ID: {active_position.id}")

            return ExecutionResult(
                success=True,
                trade_id=trade_id,
                order_id=order_id,
                entry_price=entry_price,
                quantity=quantity,
                status="EXECUTED",
                message="Paper trade executed successfully",
                trade_execution_id=trade_execution.id,
                active_position_id=active_position.id,
                timestamp=datetime.now().isoformat(),
                metadata={
                    "trading_mode": "paper",
                    "symbol": prepared_trade.stock_symbol,
                    "option_type": prepared_trade.option_type,
                    "strike": float(prepared_trade.strike_price),
                    "expiry": prepared_trade.expiry_date,
                    "stop_loss": float(prepared_trade.stop_loss),
                    "target": float(prepared_trade.target_price),
                    "investment": float(prepared_trade.total_investment),
                    "max_loss": float(prepared_trade.max_loss_amount),
                },
            )

        except Exception as e:
            db.rollback()
            logger.error(f"Error executing paper trade: {e}")
            raise

    def _execute_live_trade(
        self, prepared_trade: PreparedTrade, db: Session
    ) -> ExecutionResult:
        """
        Execute live trade via broker API

        Args:
            prepared_trade: Prepared trade details
            db: Database session

        Returns:
            ExecutionResult with real execution details
        """
        try:
            # Get broker configuration
            broker_config = (
                db.query(BrokerConfig)
                .join(User)
                .filter(
                    User.id == prepared_trade.user_id,
                    BrokerConfig.broker_name.ilike(f"%{prepared_trade.broker_name}%"),
                    BrokerConfig.is_active == True,
                )
                .first()
            )

            if not broker_config:
                raise ValueError(
                    f"No active broker configuration found: {prepared_trade.broker_name}"
                )

            # Generate unique trade ID
            trade_id = f"LIVE_{uuid.uuid4().hex[:12].upper()}"

            # Place order via broker
            order_result = self._place_broker_order(broker_config, prepared_trade)

            if not order_result.get("success"):
                raise ValueError(
                    f"Order placement failed: {order_result.get('message')}"
                )

            broker_order_id = order_result.get("order_id")
            actual_entry_price = Decimal(
                str(order_result.get("price", prepared_trade.entry_price))
            )
            actual_quantity = order_result.get(
                "quantity", prepared_trade.position_size_lots * prepared_trade.lot_size
            )
            lots_traded = prepared_trade.position_size_lots
            total_investment = actual_entry_price * Decimal(str(actual_quantity))

            logger.info(f"Executing LIVE trade: {trade_id}")
            logger.info(f"  Symbol: {prepared_trade.stock_symbol}")
            logger.info(f"  Broker Order ID: {broker_order_id}")
            logger.info(f"  Entry: Rs.{actual_entry_price}, Qty: {actual_quantity}, Lots: {lots_traded}")
            logger.info(f"  Total Investment: Rs.{total_investment:,.2f}")

            # Create trade execution record
            signal_conf = prepared_trade.metadata.get("signal_confidence", 0.7)
            signal_strength = float(signal_conf * 100) if signal_conf else 70.0

            trade_execution = AutoTradeExecution(
                user_id=prepared_trade.user_id,
                trade_id=trade_id,
                symbol=prepared_trade.stock_symbol,
                instrument_key=prepared_trade.option_instrument_key,
                strategy_name="supertrend_ema",
                signal_type=f"BUY_{prepared_trade.option_type}",
                signal_strength=signal_strength,
                entry_time=datetime.now(),
                entry_price=float(actual_entry_price),
                entry_order_id=broker_order_id,
                quantity=actual_quantity,
                lot_size=prepared_trade.lot_size,
                lots_traded=lots_traded,
                total_investment=float(total_investment),
                initial_stop_loss=float(prepared_trade.stop_loss),
                target_1=float(prepared_trade.target_price),
                target_2=float(prepared_trade.target_price * Decimal("1.1")),
                status="ACTIVE",
                # Multi-demat support - use actual broker details from config
                broker_name=prepared_trade.broker_name,
                broker_config_id=broker_config.id,
                allocated_capital=float(prepared_trade.total_investment),
                parent_trade_id=prepared_trade.parent_trade_id or None,
                trading_mode=prepared_trade.trading_mode,
            )

            db.add(trade_execution)
            db.flush()

            # Create active position
            active_position = ActivePosition(
                trade_execution_id=trade_execution.id,
                user_id=prepared_trade.user_id,
                symbol=prepared_trade.stock_symbol,
                instrument_key=prepared_trade.option_instrument_key,
                current_price=float(actual_entry_price),
                current_pnl=0.0,
                current_pnl_percentage=0.0,
                current_stop_loss=float(prepared_trade.stop_loss),
                trailing_stop_triggered=False,
                highest_price_reached=float(actual_entry_price),
                unrealized_risk=float(prepared_trade.max_loss_amount),
                mark_to_market_time=datetime.now(),
                is_active=True,
                last_updated=datetime.now(),
            )

            db.add(active_position)
            db.commit()

            logger.info(f"✅ Live trade executed successfully: {trade_id}")

            return ExecutionResult(
                success=True,
                trade_id=trade_id,
                order_id=broker_order_id,
                entry_price=actual_entry_price,
                quantity=actual_quantity,
                status="EXECUTED",
                message="Live trade executed successfully",
                trade_execution_id=trade_execution.id,
                active_position_id=active_position.id,
                timestamp=datetime.now().isoformat(),
                metadata={
                    "trading_mode": "live",
                    "broker": prepared_trade.broker_name,
                    "broker_order_id": broker_order_id,
                    "symbol": prepared_trade.stock_symbol,
                    "option_type": prepared_trade.option_type,
                    "strike": float(prepared_trade.strike_price),
                    "expiry": prepared_trade.expiry_date,
                },
            )

        except Exception as e:
            db.rollback()
            logger.error(f"Error executing live trade: {e}")
            raise

    def _place_broker_order(
        self, broker_config: BrokerConfig, prepared_trade: PreparedTrade
    ) -> Dict[str, Any]:
        """
        Place order via broker API

        Args:
            broker_config: Broker configuration with credentials
            prepared_trade: Prepared trade details

        Returns:
            Order result dict with success, order_id, price, quantity
        """
        try:
            broker_name = broker_config.broker_name.lower()
            quantity = prepared_trade.position_size_lots * prepared_trade.lot_size

            # Determine transaction type (BUY for both CE and PE initial entry)
            transaction_type = "BUY"

            if "upstox" in broker_name:
                from brokers.upstox_broker import UpstoxBroker

                broker = UpstoxBroker(broker_config)

                order_result = broker.place_order(
                    instrument_key=prepared_trade.option_instrument_key,
                    quantity=quantity,
                    order_type="MARKET",
                    transaction_type=transaction_type,
                    product_type="INTRADAY",
                )

                return {
                    "success": True,
                    "order_id": order_result.get("order_id"),
                    "price": prepared_trade.entry_price,
                    "quantity": quantity,
                    "broker": "Upstox",
                }

            elif "angel" in broker_name:
                from brokers.angel_broker import AngelOneBroker

                broker = AngelOneBroker(broker_config)

                order_result = broker.place_order(
                    symbol=prepared_trade.stock_symbol,
                    quantity=quantity,
                    order_type="MARKET",
                    transaction_type=transaction_type,
                )

                return {
                    "success": True,
                    "order_id": order_result.get("orderid"),
                    "price": prepared_trade.entry_price,
                    "quantity": quantity,
                    "broker": "AngelOne",
                }

            elif "dhan" in broker_name:
                from brokers.dhan_broker import DhanBroker

                broker = DhanBroker(broker_config)

                order_result = broker.place_order(
                    instrument_key=prepared_trade.option_instrument_key,
                    quantity=quantity,
                    order_type="MARKET",
                    transaction_type=transaction_type,
                )

                return {
                    "success": True,
                    "order_id": order_result.get("orderId"),
                    "price": prepared_trade.entry_price,
                    "quantity": quantity,
                    "broker": "Dhan",
                }

            else:
                raise ValueError(f"Unsupported broker: {broker_name}")

        except Exception as e:
            logger.error(f"Error placing broker order: {e}")
            return {"success": False, "message": str(e)}


# Create singleton instance
execution_handler = TradeExecutionHandler()
