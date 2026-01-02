"""
Multi-Demat Trade Executor
Executes trades across multiple demat accounts in parallel with proportional capital allocation
"""

import asyncio
import logging
from decimal import Decimal
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from dataclasses import dataclass

from database.models import BrokerConfig, User, AutoTradeExecution, ActivePosition
from services.trading_execution.multi_demat_capital_service import multi_demat_capital_service
from services.trading_execution.capital_manager import TradingMode
from services.trading_execution.trade_prep import trade_prep_service, PreparedTrade, TradeStatus
from services.trading_execution.execution_handler import execution_handler, ExecutionResult

logger = logging.getLogger(__name__)


@dataclass
class MultiDematExecutionResult:
    """Result from multi-demat execution"""
    success: bool
    total_demats: int
    successful_executions: int
    failed_executions: int
    executions: List[Dict[str, Any]]
    total_allocated_capital: Decimal
    total_quantity: int
    parent_trade_id: str
    error_message: Optional[str] = None


class MultiDematTradeExecutor:
    """
    Executes trades across multiple demat accounts in parallel

    Features:
    - Parallel execution using asyncio.gather()
    - Proportional capital allocation based on available margin
    - Individual demat failure handling
    - Aggregated results with parent trade linking
    - Per-demat trade records in database
    """

    def __init__(self):
        """Initialize multi-demat executor"""
        self.min_capital_per_demat = Decimal('1000')  # Minimum ₹1000 per demat
        logger.info("Multi-Demat Trade Executor initialized")

    async def execute_across_all_demats(
        self,
        user_id: int,
        stock_symbol: str,
        option_instrument_key: str,
        option_type: str,
        strike_price: Decimal,
        expiry_date: str,
        lot_size: int,
        premium_per_lot: Decimal,
        db: Session,
        trading_mode: TradingMode = TradingMode.LIVE
    ) -> MultiDematExecutionResult:
        """
        Execute trade across ALL active demats with valid tokens

        Args:
            user_id: User identifier
            stock_symbol: Stock symbol (e.g., "RELIANCE")
            option_instrument_key: Option instrument key
            option_type: CE or PE
            strike_price: Strike price
            expiry_date: Expiry date
            lot_size: Lot size
            premium_per_lot: Premium per lot
            db: Database session
            trading_mode: PAPER or LIVE

        Returns:
            MultiDematExecutionResult with aggregated execution details

        Raises:
            ValueError: If parameters are invalid
        """
        try:
            logger.info(
                f"Starting multi-demat execution for {stock_symbol} "
                f"{option_type} {strike_price} - User: {user_id}"
            )

            # Step 1: Calculate required capital for one lot
            required_capital_per_lot = premium_per_lot * Decimal(str(lot_size))

            # Step 2: Get capital overview and allocation plan
            capital_overview = multi_demat_capital_service.get_user_total_capital(
                user_id=user_id,
                db=db,
                trading_mode=trading_mode.value
            )

            if not capital_overview.get("demats"):
                logger.warning(f"No active demats found for user {user_id}")
                return MultiDematExecutionResult(
                    success=False,
                    total_demats=0,
                    successful_executions=0,
                    failed_executions=0,
                    executions=[],
                    total_allocated_capital=Decimal('0'),
                    total_quantity=0,
                    parent_trade_id="",
                    error_message="No active demat accounts with valid tokens"
                )

            # Step 3: Filter valid demats with sufficient free margin
            valid_demats = [
                d for d in capital_overview["demats"]
                if d.get("token_valid")
                and Decimal(str(d.get("free_margin", 0))) >= self.min_capital_per_demat
            ]

            if not valid_demats:
                logger.warning(f"No demats with sufficient free margin for user {user_id}")
                return MultiDematExecutionResult(
                    success=False,
                    total_demats=len(capital_overview["demats"]),
                    successful_executions=0,
                    failed_executions=0,
                    executions=[],
                    total_allocated_capital=Decimal('0'),
                    total_quantity=0,
                    parent_trade_id="",
                    error_message="No demats with sufficient free margin"
                )

            # Step 4: Calculate proportional allocation
            allocation_plan = self._calculate_allocation_plan(
                valid_demats,
                required_capital_per_lot,
                lot_size
            )

            logger.info(
                f"Allocation plan: {len(allocation_plan)} demats, "
                f"Total lots: {sum(a['lots'] for a in allocation_plan)}"
            )

            # Step 5: Generate parent trade ID for linking
            parent_trade_id = f"MULTI_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

            # Step 6: Execute trades in parallel across all demats
            execution_tasks = []
            for allocation in allocation_plan:
                if allocation["lots"] > 0:
                    task = self._execute_single_demat_trade(
                        user_id=user_id,
                        broker_name=allocation["broker_name"],
                        broker_id=allocation.get("broker_id"),
                        stock_symbol=stock_symbol,
                        option_instrument_key=option_instrument_key,
                        option_type=option_type,
                        strike_price=strike_price,
                        expiry_date=expiry_date,
                        lot_size=lot_size,
                        lots_to_trade=allocation["lots"],
                        allocated_capital=allocation["allocated_capital"],
                        premium=premium_per_lot,
                        parent_trade_id=parent_trade_id,
                        db=db,
                        trading_mode=trading_mode
                    )
                    execution_tasks.append(task)

            # Execute all trades in parallel
            results = await asyncio.gather(*execution_tasks, return_exceptions=True)

            # Step 7: Aggregate results
            aggregated_result = self._aggregate_execution_results(
                results,
                parent_trade_id,
                len(valid_demats)
            )

            logger.info(
                f"Multi-demat execution completed: {aggregated_result.successful_executions}/"
                f"{aggregated_result.total_demats} successful"
            )

            return aggregated_result

        except Exception as e:
            logger.error(f"Error in multi-demat execution: {e}")
            return MultiDematExecutionResult(
                success=False,
                total_demats=0,
                successful_executions=0,
                failed_executions=0,
                executions=[],
                total_allocated_capital=Decimal('0'),
                total_quantity=0,
                parent_trade_id="",
                error_message=str(e)
            )

    def _calculate_allocation_plan(
        self,
        valid_demats: List[Dict],
        required_capital_per_lot: Decimal,
        lot_size: int
    ) -> List[Dict[str, Any]]:
        """
        Calculate proportional allocation across demats

        Args:
            valid_demats: List of valid demat dictionaries
            required_capital_per_lot: Capital required per lot
            lot_size: Lot size

        Returns:
            List of allocation dictionaries
        """
        try:
            total_free_margin = sum(
                Decimal(str(d.get("free_margin", 0))) for d in valid_demats
            )

            if total_free_margin == 0:
                return []

            allocation_plan = []

            for demat in valid_demats:
                free_margin = Decimal(str(demat.get("free_margin", 0)))

                # Calculate proportion
                proportion = free_margin / total_free_margin

                # Calculate allocated capital (proportional to free margin)
                allocated_capital = free_margin * proportion

                # Calculate number of lots this demat can take
                lots = int(allocated_capital / required_capital_per_lot)

                # Ensure at least 1 lot if sufficient capital
                if allocated_capital >= required_capital_per_lot and lots == 0:
                    lots = 1

                # Recalculate actual allocated capital based on lots
                actual_allocated = Decimal(str(lots)) * required_capital_per_lot

                allocation_plan.append({
                    "broker_name": demat["broker_name"],
                    "broker_id": demat.get("broker_id"),
                    "free_margin": float(free_margin),
                    "proportion_percent": float(proportion * 100),
                    "allocated_capital": actual_allocated,
                    "lots": lots,
                    "quantity": lots * lot_size
                })

            return allocation_plan

        except Exception as e:
            logger.error(f"Error calculating allocation plan: {e}")
            return []

    async def _execute_single_demat_trade(
        self,
        user_id: int,
        broker_name: str,
        broker_id: Optional[int],
        stock_symbol: str,
        option_instrument_key: str,
        option_type: str,
        strike_price: Decimal,
        expiry_date: str,
        lot_size: int,
        lots_to_trade: int,
        allocated_capital: Decimal,
        premium: Decimal,
        parent_trade_id: str,
        db: Session,
        trading_mode: TradingMode
    ) -> Dict[str, Any]:
        """
        Execute trade for a single demat account

        Returns:
            Execution result dictionary
        """
        try:
            logger.info(
                f"Executing trade on {broker_name} - {lots_to_trade} lot(s) "
                f"for {stock_symbol} {option_type} {strike_price}"
            )

            # Prepare trade with specific broker
            prepared_trade = await trade_prep_service.prepare_trade(
                user_id=user_id,
                stock_symbol=stock_symbol,
                option_instrument_key=option_instrument_key,
                option_type=option_type,
                strike_price=strike_price,
                expiry_date=expiry_date,
                lot_size=lot_size,
                db=db,
                trading_mode=trading_mode,
                broker_name=broker_name  # Specify broker
            )

            if prepared_trade.status != TradeStatus.READY:
                logger.warning(
                    f"Trade not ready for {broker_name}: {prepared_trade.status.value}"
                )
                return {
                    "broker_name": broker_name,
                    "success": False,
                    "error": f"Trade not ready: {prepared_trade.status.value}",
                    "allocated_capital": float(allocated_capital),
                    "lots": lots_to_trade
                }

            # Override quantity with calculated lots
            prepared_trade.position_size_lots = lots_to_trade
            prepared_trade.quantity = lots_to_trade * lot_size

            # Execute trade
            execution_result = execution_handler.execute_trade(
                prepared_trade=prepared_trade,
                db=db,
                parent_trade_id=parent_trade_id,
                broker_name=broker_name,
                broker_id=broker_id,
                allocated_capital=float(allocated_capital)
            )

            if execution_result.success:
                logger.info(
                    f"✅ Trade executed successfully on {broker_name} - "
                    f"Trade ID: {execution_result.trade_id}"
                )
                return {
                    "broker_name": broker_name,
                    "success": True,
                    "trade_id": execution_result.trade_id,
                    "order_id": execution_result.order_id,
                    "entry_price": float(execution_result.entry_price),
                    "quantity": execution_result.quantity,
                    "lots": lots_to_trade,
                    "allocated_capital": float(allocated_capital),
                    "message": execution_result.message
                }
            else:
                logger.error(
                    f"❌ Trade execution failed on {broker_name}: {execution_result.message}"
                )
                return {
                    "broker_name": broker_name,
                    "success": False,
                    "error": execution_result.message,
                    "allocated_capital": float(allocated_capital),
                    "lots": lots_to_trade
                }

        except Exception as e:
            logger.error(f"Error executing trade on {broker_name}: {e}")
            return {
                "broker_name": broker_name,
                "success": False,
                "error": str(e),
                "allocated_capital": float(allocated_capital),
                "lots": lots_to_trade
            }

    def _aggregate_execution_results(
        self,
        results: List,
        parent_trade_id: str,
        total_demats: int
    ) -> MultiDematExecutionResult:
        """
        Aggregate execution results from all demats

        Args:
            results: List of execution results
            parent_trade_id: Parent trade ID
            total_demats: Total number of demats attempted

        Returns:
            Aggregated MultiDematExecutionResult
        """
        try:
            successful_executions = 0
            failed_executions = 0
            total_allocated_capital = Decimal('0')
            total_quantity = 0
            executions = []

            for result in results:
                # Handle exceptions
                if isinstance(result, Exception):
                    failed_executions += 1
                    executions.append({
                        "broker_name": "unknown",
                        "success": False,
                        "error": str(result)
                    })
                    continue

                # Process successful/failed executions
                if result.get("success"):
                    successful_executions += 1
                    total_allocated_capital += Decimal(str(result.get("allocated_capital", 0)))
                    total_quantity += result.get("quantity", 0)
                else:
                    failed_executions += 1

                executions.append(result)

            return MultiDematExecutionResult(
                success=successful_executions > 0,
                total_demats=total_demats,
                successful_executions=successful_executions,
                failed_executions=failed_executions,
                executions=executions,
                total_allocated_capital=total_allocated_capital,
                total_quantity=total_quantity,
                parent_trade_id=parent_trade_id,
                error_message=None if successful_executions > 0 else "All executions failed"
            )

        except Exception as e:
            logger.error(f"Error aggregating execution results: {e}")
            return MultiDematExecutionResult(
                success=False,
                total_demats=total_demats,
                successful_executions=0,
                failed_executions=total_demats,
                executions=[],
                total_allocated_capital=Decimal('0'),
                total_quantity=0,
                parent_trade_id=parent_trade_id,
                error_message=str(e)
            )


# Global service instance
multi_demat_executor = MultiDematTradeExecutor()
