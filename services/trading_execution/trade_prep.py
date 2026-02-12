"""
Trade Preparation Module
Validates and prepares trades for execution with complete risk management
"""

import logging
import asyncio
from decimal import Decimal
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from utils.timezone_utils import get_ist_now_naive, get_ist_isoformat
from services.trading_execution.capital_manager import (
    capital_manager,
    TradingMode,
    CapitalAllocation,
)
from services.trading_execution.strategy_engine import (
    strategy_engine,
    TradingSignal,
    SignalType,
    TrailingStopType,
)
from utils.logging_utils import log_trade_prep, log_to_db

logger = logging.getLogger(__name__)


class TradeStatus(Enum):
    """Trade preparation status"""

    READY = "ready"
    PENDING_SIGNAL = "pending_signal"
    INSUFFICIENT_CAPITAL = "insufficient_capital"
    NO_ACTIVE_BROKER = "no_active_broker"
    INVALID_PARAMS = "invalid_params"
    INVALID_OPTION = "invalid_option"
    ERROR = "error"


@dataclass
class PreparedTrade:
    """
    Complete trade preparation with all execution details

    Attributes:
        status: Trade preparation status
        stock_symbol: Stock symbol
        option_instrument_key: Option contract instrument key
        option_type: CE or PE
        strike_price: Option strike price
        expiry_date: Option expiry date
        current_premium: Current option premium
        lot_size: Lot size for the option
        signal: Trading signal from strategy
        capital_allocation: Capital allocation details
        risk_reward_ratio: Risk to reward ratio
        entry_price: Entry price for trade
        stop_loss: Stop loss price
        target_price: Target price
        trailing_stop_config: Trailing stop loss configuration
        position_size_lots: Number of lots to trade
        total_investment: Total capital required
        max_loss_amount: Maximum loss for this trade
        trading_mode: Paper or Live trading
        broker_name: Broker to use for execution
        user_id: User identifier
        prepared_at: Preparation timestamp
        valid_until: Trade validity end time
        metadata: Additional metadata
        parent_trade_id: Optional parent trade ID for multi-demat trades
    """

    status: TradeStatus
    stock_symbol: str
    option_instrument_key: str
    option_type: str
    strike_price: Decimal
    expiry_date: str
    current_premium: Decimal
    lot_size: int
    signal: Optional[Dict[str, Any]]
    capital_allocation: Optional[Dict[str, Any]]
    risk_reward_ratio: Decimal
    entry_price: Decimal
    stop_loss: Decimal
    target_price: Decimal
    trailing_stop_config: Dict[str, Any]
    position_size_lots: int
    total_investment: Decimal
    max_loss_amount: Decimal
    trading_mode: str
    broker_name: Optional[str]
    user_id: int
    prepared_at: str
    valid_until: str
    metadata: Dict[str, Any]
    parent_trade_id: Optional[str] = None
    product: str = "I"
    segment: str = "F&O"


class TradePrepService:
    """
    Trade Preparation Service

    Orchestrates the complete trade preparation process:
    1. Validates user's active broker and capital
    2. Fetches live market data for the option
    3. Runs strategy to generate trading signal
    4. Calculates position size and risk management
    5. Prepares complete trade execution details
    """

    def __init__(self):
        """Initialize trade preparation service"""
        self.signal_validity_minutes = 15  # Signals valid for 15 minutes
        self.stats = {
            "total_preparations": 0,
            "successful_preparations": 0,
            "failed_preparations": 0,
            "insufficient_capital": 0,
            "last_preparation_time": None
        }
        self.function_health = {
            "capital_allocation": {"status": "unknown", "last_run": None, "error": None},
            "signal_generation": {"status": "unknown", "last_run": None, "error": None},
            "option_validation": {"status": "unknown", "last_run": None, "error": None}
        }
        self.last_error = None
        logger.info("Trade Preparation Service initialized")

    def _update_function_health(self, func_name: str, status: str, error: str = None):
        """Update health status for a specific internal function"""
        self.function_health[func_name] = {
            "status": status,
            "last_run": get_ist_isoformat(),
            "error": error
        }

    def _safe_dispatch(self, coro):
        """Safely dispatch a coroutine to the main event loop from any thread"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.call_soon_threadsafe(lambda: asyncio.create_task(coro))
            else:
                asyncio.run_coroutine_threadsafe(coro, loop)
        except Exception as e:
            logger.error(f"Error in thread-safe dispatch: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get service status for system health monitoring"""
        # Service is healthy if most preparations succeed or if it's idle
        overall_status = "active"
        if self.stats["failed_preparations"] > 0 and self.stats["successful_preparations"] == 0:
            overall_status = "error"
        elif self.stats["failed_preparations"] > self.stats["successful_preparations"]:
            overall_status = "degraded"

        return {
            "status": overall_status,
            "stats": self.stats,
            "function_health": self.function_health,
            "last_error": self.last_error,
            "timestamp": get_ist_isoformat()
        }

    async def prepare_trade_with_live_data(
        self,
        user_id: int,
        stock_symbol: str,
        option_instrument_key: str,
        option_type: str,
        strike_price: Decimal,
        expiry_date: str,
        lot_size: int,
        current_premium: Decimal,
        historical_data: Dict[str, List[float]],
        db: Session,
        trading_mode: TradingMode = TradingMode.PAPER,
        broker_name: Optional[str] = None,
        option_greeks: Optional[Dict[str, float]] = None,
        implied_volatility: Optional[float] = None,
        open_interest: Optional[float] = None,
        volume: Optional[float] = None,
        bid_price: Optional[float] = None,
        ask_price: Optional[float] = None,
        target_lots: Optional[int] = None,
        product: str = "I",
        underlying_key: Optional[str] = None,
    ) -> PreparedTrade:
        """
        Prepare trade with live market data already provided (optimized for auto-trading)

        This method is optimized for auto_trade_live_feed which already has:
        - Current option premium from live WebSocket feed
        - Historical spot data for strategy calculation

        Args:
            user_id: User identifier
            stock_symbol: Underlying stock symbol
            option_instrument_key: Option contract instrument key
            option_type: "CE" for calls, "PE" for puts
            strike_price: Option strike price
            expiry_date: Option expiry date
            lot_size: Lot size for the option
            current_premium: Current option premium (from live feed)
            historical_data: Historical spot OHLC data
            db: Database session
            trading_mode: Paper or Live trading mode
            broker_name: Broker name (optional)
            underlying_key: Authoritative instrument key for the underlying asset (e.g. NSE_INDEX|Nifty 50)

        Returns:
            PreparedTrade with complete execution details

        Raises:
            ValueError: If parameters are invalid
        """
        if not user_id or user_id <= 0:
            raise ValueError("Invalid user_id provided")
        if not option_instrument_key:
            raise ValueError("Option instrument key is required")
        if option_type not in ["CE", "PE"]:
            raise ValueError("Option type must be 'CE' or 'PE'")
        if current_premium <= 0:
            raise ValueError("Current premium must be positive")
        if not historical_data or len(historical_data.get("close", [])) < 20:
            raise ValueError("Insufficient historical data provided")

        try:
            self.stats["total_preparations"] += 1
            self.stats["last_preparation_time"] = get_ist_isoformat()
            
            logger.info(
                f"Preparing trade for user {user_id}: {stock_symbol} {option_type} {strike_price} (with live data)"
            )

            # Step 0: Validate/Fetch Lot Size if missing or suspicious
            # Use provided underlying_key if available, fallback to guesser
            resolved_underlying_key = underlying_key or self._get_underlying_key(stock_symbol)

            if lot_size <= 1:
                try:
                    from services.upstox_option_service import upstox_option_service
                    # Fetch ATM data which includes lot size for the specific expiry
                    if resolved_underlying_key and expiry_date:
                        atm_data = upstox_option_service.get_atm_keys(resolved_underlying_key, expiry_date, db)
                        if atm_data and atm_data.get("lot_size", 0) > 0:
                            lot_size = atm_data["lot_size"]
                            logger.info(f"Fetched corrected lot_size for {stock_symbol} via ATM chain: {lot_size}")
                        else:
                            # Fallback to full contract fetch if ATM chain fails
                            contracts = upstox_option_service.get_option_contracts(resolved_underlying_key, db)
                            if contracts and len(contracts) > 0:
                                fetched_lot_size = int(contracts[0].get("lot_size", 0))
                                if fetched_lot_size > 0:
                                    lot_size = fetched_lot_size
                                    logger.info(f"Fetched corrected lot_size for {stock_symbol} via contracts fallback: {lot_size}")
                except Exception as e:
                    logger.warning(f"Failed to fetch lot size from broker for {stock_symbol}: {e}")

            if lot_size <= 0:
                 return self._create_error_trade(
                    TradeStatus.INVALID_PARAMS,
                    user_id,
                    stock_symbol,
                    option_instrument_key,
                    option_type,
                    strike_price,
                    expiry_date,
                    0,
                    trading_mode,
                    "Invalid lot size. Cannot execute trade without valid lot size.",
                )

            # Step 1: Validate broker configuration
            broker_config = capital_manager.get_active_broker_config(user_id, db)

            if not broker_config and trading_mode == TradingMode.LIVE:
                logger.warning(f"No active broker for user {user_id}")
                return self._create_error_trade(
                    TradeStatus.NO_ACTIVE_BROKER,
                    user_id,
                    stock_symbol,
                    option_instrument_key,
                    option_type,
                    strike_price,
                    expiry_date,
                    lot_size,
                    trading_mode,
                    "No active broker configuration found",
                )

            broker_name = (
                broker_config.broker_name if broker_config else "Paper Trading"
            )

            # Step 2: Check position limits BEFORE capital allocation
            # CRITICAL FIX: Prevent exceeding maximum concurrent positions
            from database.models import ActivePosition, AutoTradeExecution

            active_position_count = (
                db.query(ActivePosition)
                .join(
                    AutoTradeExecution,
                    ActivePosition.trade_execution_id == AutoTradeExecution.id,
                )
                .filter(
                    AutoTradeExecution.user_id == user_id,
                    ActivePosition.is_active == True,
                )
                .count()
            )

            MAX_CONCURRENT_POSITIONS = 10
            if active_position_count >= MAX_CONCURRENT_POSITIONS:
                logger.warning(
                    f"User {user_id} has {active_position_count} active positions "
                    f"(max: {MAX_CONCURRENT_POSITIONS})"
                )
                
                # Notify User of Limit
                from services.notifications.alert_manager import alert_manager
                self._safe_dispatch(alert_manager.send_admin_system_status(
                    "Risk Manager", "LIMIT_REACHED", 
                    f"Blocked trade for {stock_symbol}. Max positions ({MAX_CONCURRENT_POSITIONS}) reached."
                ))
                
                return self._create_error_trade(
                    TradeStatus.INSUFFICIENT_CAPITAL,
                    user_id,
                    stock_symbol,
                    option_instrument_key,
                    option_type,
                    strike_price,
                    expiry_date,
                    lot_size,
                    trading_mode,
                    f"Maximum {MAX_CONCURRENT_POSITIONS} concurrent positions reached. "
                    f"Close some positions before opening new ones.",
                )

            # Check if same stock already has an active position
            existing_position = (
                db.query(ActivePosition)
                .join(
                    AutoTradeExecution,
                    ActivePosition.trade_execution_id == AutoTradeExecution.id,
                )
                .filter(
                    AutoTradeExecution.user_id == user_id,
                    AutoTradeExecution.symbol == stock_symbol,
                    ActivePosition.is_active == True,
                )
                .first()
            )

            if existing_position:
                logger.warning(
                    f"User {user_id} already has active position in {stock_symbol} "
                    f"(position_id: {existing_position.id})"
                )
                return self._create_error_trade(
                    TradeStatus.INVALID_PARAMS,
                    user_id,
                    stock_symbol,
                    option_instrument_key,
                    option_type,
                    strike_price,
                    expiry_date,
                    lot_size,
                    trading_mode,
                    f"Position already exists for {stock_symbol}. "
                    f"Only one position per stock allowed.",
                )

            # Step 3: Get available capital for new position
            # Use new method that checks position limits instead of deducting from pool
            available_capital = capital_manager.get_available_capital_for_new_position(
                user_id, db, trading_mode
            )

            if available_capital <= 0:
                logger.warning(
                    f"No available capital for user {user_id} - insufficient funds"
                )
                return self._create_error_trade(
                    TradeStatus.INSUFFICIENT_CAPITAL,
                    user_id,
                    stock_symbol,
                    option_instrument_key,
                    option_type,
                    strike_price,
                    expiry_date,
                    lot_size,
                    trading_mode,
                    "Insufficient capital available for new position",
                )

            # Step 4: Calculate position size based on capital
            capital_allocation = capital_manager.calculate_position_size(
                available_capital, current_premium, lot_size, max_lots=target_lots
            )

            # Step 5: Validate sufficient capital
            capital_validation = capital_manager.validate_capital_availability(
                user_id, capital_allocation.allocated_capital, db, trading_mode
            )

            if not capital_validation.get("valid"):
                logger.warning(
                    f"Insufficient capital: need {capital_allocation.allocated_capital}"
                )
                
                # Notify User of Capital Failure
                from services.notifications.alert_manager import alert_manager
                self._safe_dispatch(alert_manager.send_admin_system_status(
                    "Capital Manager", "INSUFFICIENT_FUNDS", 
                    f"Blocked trade for {stock_symbol}. Need ₹{capital_allocation.allocated_capital:.2f}, but funds are low."
                ))
                
                return self._create_error_trade(
                    TradeStatus.INSUFFICIENT_CAPITAL,
                    user_id,
                    stock_symbol,
                    option_instrument_key,
                    option_type,
                    strike_price,
                    expiry_date,
                    lot_size,
                    trading_mode,
                    f"Insufficient capital. Need: {capital_allocation.allocated_capital}, Available: {available_capital}",
                )

            # Step 6: Validate option quality using Greeks and market data (NEW)
            if option_greeks and implied_volatility and open_interest:
                logger.info(f"Validating option quality with Greeks and market data")

                from services.trading_execution.option_analytics import option_analytics

                # Calculate spot ATR for Greeks analysis
                spot_atr = (
                    self._calculate_atr_from_historical(historical_data)
                    if historical_data
                    else None
                )

                option_validation = option_analytics.validate_option_for_entry(
                    greeks=option_greeks,
                    iv=implied_volatility,
                    oi=open_interest,
                    volume=volume or 0,
                    bid_price=bid_price or float(current_premium * Decimal("0.995")),
                    ask_price=ask_price or float(current_premium * Decimal("1.005")),
                    premium=float(current_premium),
                    quantity=capital_allocation.position_size_lots * lot_size,
                    spot_atr=spot_atr,
                )

                if not option_validation.valid:
                    logger.warning(
                        f"Option validation failed: {option_validation.reason}"
                    )
                    return self._create_error_trade(
                        TradeStatus.INVALID_OPTION,
                        user_id,
                        stock_symbol,
                        option_instrument_key,
                        option_type,
                        strike_price,
                        expiry_date,
                        lot_size,
                        trading_mode,
                        option_validation.reason,
                    )

                # Log warnings
                for warning in option_validation.warnings:
                    logger.warning(f"Option warning: {warning}")

                logger.info(
                    f"Option validated - Quality Score: {option_validation.metrics.get('quality_score')}/100"
                )
            else:
                logger.warning(
                    "Option Greeks/IV/OI not provided - skipping advanced validation"
                )

            # Step 7: Generate trading signal using provided SPOT historical data
            logger.info(
                f"Generating signal for {stock_symbol} using provided historical data"
            )

            # CRITICAL DEBUG: Log actual values being used for signal generation
            spot_current_price = Decimal(str(historical_data["close"][-1]))
            
            # CHECK ATM DISTANCE (Verify if selection is still relevant)
            try:
                strike_val = Decimal(str(strike_price))
                distance_pct = ((strike_val - spot_current_price) / spot_current_price) * 100
                moneyness = "OTM" if (option_type == "CE" and strike_val > spot_current_price) or \
                                   (option_type == "PE" and strike_val < spot_current_price) else "ITM"
                
                logger.info(f"ATM CHECK for {stock_symbol}: Spot={spot_current_price}, Strike={strike_val}")
                logger.info(f"  Moneyness: {moneyness} ({abs(distance_pct):.2f}% from Spot)")
                
                if abs(distance_pct) > 2.0:
                    logger.warning(f"⚠️ Strike {strike_val} is {abs(distance_pct):.2f}% away from Spot {spot_current_price}. Selection might be stale.")
            except Exception as dist_err:
                logger.warning(f"Could not calculate strike distance: {dist_err}")

            logger.info(f"DEBUG - Signal generation inputs for {stock_symbol}:")
            logger.info(f"  Spot current_price (last close): {spot_current_price}")
            logger.info(f"  Option premium: {current_premium}")
            logger.info(
                f"  Historical data length: {len(historical_data.get('close', []))} candles"
            )
            logger.info(f"  Last 3 closes: {historical_data.get('close', [])[-3:]}")

            # IMPORTANT: Strategy runs on SPOT data (trend detection on underlying)
            # We'll convert to premium-based values afterward
            spot_signal = strategy_engine.generate_signal(
                current_price=spot_current_price,  # Latest spot price
                historical_data=historical_data,
                option_type=option_type,
            )

            logger.info(
                f"Spot signal generated: {spot_signal.signal_type.value} at {spot_signal.entry_price}, "
                f"confidence={spot_signal.confidence}"
            )

            # Check signal validity BEFORE conversion
            # CRITICAL FIX: Don't convert HOLD signals - they're already invalid
            if spot_signal.signal_type == SignalType.HOLD:
                logger.info(
                    f"No clear trading signal for {stock_symbol} - spot signal is HOLD"
                )
                return self._create_pending_trade(
                    user_id,
                    stock_symbol,
                    option_instrument_key,
                    option_type,
                    strike_price,
                    expiry_date,
                    lot_size,
                    current_premium,
                    capital_allocation,
                    spot_signal,
                    trading_mode,
                    broker_name,
                )

            # Convert spot signal to premium signal (only for valid signals)
            premium_signal = strategy_engine.convert_spot_signal_to_premium(
                signal=spot_signal,
                spot_price=Decimal(str(historical_data["close"][-1])),
                option_premium=current_premium,
                option_delta=option_greeks.get("delta") if option_greeks else None,
            )

            logger.info(
                f"Premium signal: {premium_signal.signal_type.value} at {premium_signal.entry_price}, "
                f"SL={premium_signal.stop_loss}, Target={premium_signal.target_price}"
            )

            # Step 8: Calculate risk-reward ratio (now in premium terms)
            risk = abs(premium_signal.entry_price - premium_signal.stop_loss)
            # CRITICAL FIX: For Option Buying (Long), Target is ALWAYS higher than Entry (Premium must rise)
            # Previous logic incorrectly subtracted for PE, treating it as a short premium trade
            rr_ratio = Decimal(str(premium_signal.trailing_stop_config.get('risk_reward_ratio') or 2.0))
            target_price = premium_signal.entry_price + (risk * rr_ratio)
            
            # Update signal with correct target
            premium_signal.target_price = target_price
            
            risk_reward_ratio = rr_ratio

            # Step 9: Create prepared trade (with premium-based signal)
            prepared_trade = PreparedTrade(
                status=TradeStatus.READY,
                stock_symbol=stock_symbol,
                option_instrument_key=option_instrument_key,
                option_type=option_type,
                strike_price=strike_price,
                expiry_date=expiry_date,
                current_premium=current_premium,
                lot_size=lot_size,
                signal=asdict(premium_signal) if premium_signal else None,
                capital_allocation=asdict(capital_allocation),
                risk_reward_ratio=risk_reward_ratio,
                entry_price=premium_signal.entry_price,
                stop_loss=premium_signal.stop_loss,
                target_price=premium_signal.target_price,
                trailing_stop_config=premium_signal.trailing_stop_config,
                position_size_lots=capital_allocation.position_size_lots,
                total_investment=capital_allocation.allocated_capital,
                max_loss_amount=capital_allocation.max_loss,
                trading_mode=trading_mode.value,
                broker_name=broker_name,
                user_id=user_id,
                prepared_at=get_ist_isoformat(),
                valid_until=(
                    get_ist_now_naive() + timedelta(minutes=self.signal_validity_minutes)
                ).isoformat(),
                metadata={
                    "signal_confidence": float(premium_signal.confidence),
                    "signal_reason": premium_signal.reason,
                    "capital_utilization_percent": float(
                        capital_allocation.capital_utilization_percent
                    ),
                    "risk_per_trade_percent": float(
                        capital_allocation.risk_per_trade_percent
                    ),
                    "data_source": "live_websocket_feed",
                    "signal_conversion": "spot_to_premium",
                },
            )

            logger.info(f"Trade prepared successfully: {stock_symbol} {option_type}")
            log_to_db(
                component="trade_prep",
                message=f"Trade READY: {stock_symbol} {option_type} @ {premium_signal.entry_price}",
                level="INFO",
                user_id=user_id,
                symbol=stock_symbol,
                additional_data={
                    "option_type": option_type,
                    "strike": float(strike_price),
                    "premium": float(current_premium),
                    "lots": capital_allocation.position_size_lots
                }
            )
            
            logger.info(
                f"  Entry: {premium_signal.entry_price}, SL: {premium_signal.stop_loss}, Target: {premium_signal.target_price}"
            )
            logger.info(
                f"  Position: {capital_allocation.position_size_lots} lots, Investment: Rs.{capital_allocation.allocated_capital:,.2f}"
            )

            self.stats["successful_preparations"] += 1
            return prepared_trade

        except Exception as e:
            self.stats["failed_preparations"] += 1
            self.last_error = str(e)
            logger.error(f"Error preparing trade with live data: {e}")
            log_to_db(
                component="trade_prep",
                message=f"FAILED Prep: {stock_symbol} - {str(e)}",
                level="ERROR",
                user_id=user_id,
                symbol=stock_symbol
            )
            
            # Notify Admin/User of failure
            from services.notifications.alert_manager import alert_manager
            self._safe_dispatch(alert_manager.notify_critical_error(
                user_id=user_id,
                component="TRADE_PREP",
                error=f"Failed to prepare trade for {stock_symbol}: {str(e)}"
            ))
            
            return self._create_error_trade(
                TradeStatus.ERROR,
                user_id,
                stock_symbol,
                option_instrument_key,
                option_type,
                strike_price,
                expiry_date,
                lot_size,
                trading_mode,
                str(e),
            )

    def _get_underlying_key(self, symbol: str) -> Optional[str]:
        """
        Helper to map symbol/index names to Upstox instrument keys.
        Supports NIFTY, BANKNIFTY, FINNIFTY and Equity stocks.
        """
        sym = symbol.upper().strip()
        if sym == "NIFTY" or sym == "NIFTY 50":
            return "NSE_INDEX|Nifty 50"
        elif sym == "BANKNIFTY" or sym == "NIFTY BANK":
            return "NSE_INDEX|Nifty Bank"
        elif sym == "FINNIFTY" or sym == "NIFTY FIN SERVICE":
            return "NSE_INDEX|Nifty Fin Service"
        
        # Default for stocks
        return f"NSE_EQ|{sym}"

    async def prepare_trade(
        self,
        user_id: int,
        stock_symbol: str,
        option_instrument_key: str,
        option_type: str,
        strike_price: Decimal,
        expiry_date: str,
        lot_size: int,
        db: Session,
        trading_mode: TradingMode = TradingMode.PAPER,
        broker_name: Optional[str] = None,
        product: str = "I",
    ) -> PreparedTrade:
        """
        Prepare trade with complete validation and risk management

        Args:
            user_id: User identifier
            stock_symbol: Underlying stock symbol
            option_instrument_key: Option contract instrument key
            option_type: "CE" for calls, "PE" for puts
            strike_price: Option strike price
            expiry_date: Option expiry date
            lot_size: Lot size for the option
            db: Database session
            trading_mode: Paper or Live trading mode

        Returns:
            PreparedTrade with complete execution details

        Raises:
            ValueError: If parameters are invalid
        """
        if not user_id or user_id <= 0:
            raise ValueError("Invalid user_id provided")
        if not option_instrument_key:
            raise ValueError("Option instrument key is required")
        if option_type not in ["CE", "PE"]:
            raise ValueError("Option type must be 'CE' or 'PE'")

        try:
            logger.info(
                f"Preparing trade for user {user_id}: {stock_symbol} {option_type} {strike_price}"
            )

            # Step 0: Validate/Fetch Lot Size if missing
            if lot_size <= 1:
                try:
                    from services.upstox_option_service import upstox_option_service
                    # Fetch ATM data which includes lot size for the specific expiry
                    underlying_key = self._get_underlying_key(stock_symbol)
                    
                    if underlying_key and expiry_date:
                        atm_data = upstox_option_service.get_atm_keys(underlying_key, expiry_date, db)
                        if atm_data and atm_data.get("lot_size", 0) > 0:
                            lot_size = atm_data["lot_size"]
                            logger.info(f"Fetched missing lot_size for {stock_symbol} via ATM chain: {lot_size}")
                        else:
                            # Fallback to full contract fetch
                            contracts = upstox_option_service.get_option_contracts(underlying_key, db)
                            if contracts and len(contracts) > 0:
                                fetched_lot_size = int(contracts[0].get("lot_size", 0))
                                if fetched_lot_size > 0:
                                    lot_size = fetched_lot_size
                                    logger.info(f"Fetched missing lot_size for {stock_symbol} via contracts fallback: {lot_size}")
                except Exception as e:
                    logger.warning(f"Failed to fetch lot size from broker for {stock_symbol}: {e}")

            if lot_size <= 0:
                return self._create_error_trade(
                    TradeStatus.INVALID_PARAMS,
                    user_id,
                    stock_symbol,
                    option_instrument_key,
                    option_type,
                    strike_price,
                    expiry_date,
                    0,
                    trading_mode,
                    "Invalid lot size: 0. Cannot execute trade without valid lot size.",
                )

            # Step 1: Validate broker configuration
            broker_config = capital_manager.get_active_broker_config(user_id, db)

            if not broker_config and trading_mode == TradingMode.LIVE:
                logger.warning(f"No active broker for user {user_id}")
                return self._create_error_trade(
                    TradeStatus.NO_ACTIVE_BROKER,
                    user_id,
                    stock_symbol,
                    option_instrument_key,
                    option_type,
                    strike_price,
                    expiry_date,
                    lot_size,
                    trading_mode,
                    "No active broker configuration found",
                )

            broker_name = (
                broker_config.broker_name if broker_config else "Paper Trading"
            )

            # Step 2: Get available capital for new position
            # Use new method that checks position limits instead of deducting from pool
            available_capital = capital_manager.get_available_capital_for_new_position(
                user_id, db, trading_mode
            )

            if available_capital <= 0:
                logger.warning(
                    f"No available capital for user {user_id} - "
                    f"either max positions reached or insufficient funds"
                )
                return self._create_error_trade(
                    TradeStatus.INSUFFICIENT_CAPITAL,
                    user_id,
                    stock_symbol,
                    option_instrument_key,
                    option_type,
                    strike_price,
                    expiry_date,
                    lot_size,
                    trading_mode,
                    "Insufficient capital or max positions reached",
                )

            # Step 3: Fetch current option premium (live market data)
            current_premium = self._get_current_option_premium(
                option_instrument_key, broker_config, trading_mode
            )

            if current_premium <= 0:
                logger.error(
                    f"Could not fetch premium for {option_instrument_key} - REJECTING TRADE"
                )
                return self._create_error_trade(
                    TradeStatus.ERROR,
                    user_id,
                    stock_symbol,
                    option_instrument_key,
                    option_type,
                    strike_price,
                    expiry_date,
                    lot_size,
                    trading_mode,
                    "Cannot fetch live option premium - real-time price required for safe trading",
                )

            # Step 4: Calculate position size based on capital
            capital_allocation = capital_manager.calculate_position_size(
                available_capital, current_premium, lot_size
            )

            # Step 5: Validate sufficient capital
            capital_validation = capital_manager.validate_capital_availability(
                user_id, capital_allocation.allocated_capital, db, trading_mode
            )

            if not capital_validation.get("valid"):
                logger.warning(
                    f"Insufficient capital: need {capital_allocation.allocated_capital}"
                )
                
                # Notify User of Capital Failure
                from services.notifications.alert_manager import alert_manager
                self._safe_dispatch(alert_manager.send_admin_system_status(
                    "Capital Manager", "INSUFFICIENT_FUNDS", 
                    f"Blocked trade for {stock_symbol}. Need ₹{capital_allocation.allocated_capital:.2f}, but funds are low."
                ))
                
                return self._create_error_trade(
                    TradeStatus.INSUFFICIENT_CAPITAL,
                    user_id,
                    stock_symbol,
                    option_instrument_key,
                    option_type,
                    strike_price,
                    expiry_date,
                    lot_size,
                    trading_mode,
                    f"Insufficient capital. Need: {capital_allocation.allocated_capital}, Available: {available_capital}",
                )

            # Step 6 & 7: Generate trading signal using option premium-based strategy
            logger.info(
                f"Generating signal for {stock_symbol} using option premium strategy"
            )

            # Fetch historical data for option
            historical_data = self._get_historical_data(
                stock_symbol, option_instrument_key, broker_config, trading_mode
            )

            # CRITICAL: Reject trade if no real historical data available
            if not historical_data:
                logger.error(
                    f"Cannot generate signal without real historical data for {option_instrument_key}"
                )
                return self._create_error_trade(
                    TradeStatus.ERROR,
                    user_id,
                    stock_symbol,
                    option_instrument_key,
                    option_type,
                    strike_price,
                    expiry_date,
                    lot_size,
                    trading_mode,
                    "Cannot fetch real historical market data - required for strategy signal generation",
                )

            # Generate signal from option premium
            signal = strategy_engine.generate_signal(
                current_premium, historical_data, option_type
            )

            # Check signal validity
            if signal.signal_type == SignalType.HOLD:
                logger.info(f"No clear trading signal for {stock_symbol}")
                return self._create_pending_trade(
                    user_id,
                    stock_symbol,
                    option_instrument_key,
                    option_type,
                    strike_price,
                    expiry_date,
                    lot_size,
                    current_premium,
                    capital_allocation,
                    signal,
                    trading_mode,
                    broker_name,
                )

            # Step 8: Calculate risk-reward ratio
            risk = abs(signal.entry_price - signal.stop_loss)
            reward = abs(signal.target_price - signal.entry_price)
            risk_reward_ratio = reward / risk if risk > 0 else Decimal("0")

            # Step 9: Create prepared trade
            prepared_trade = PreparedTrade(
                status=TradeStatus.READY,
                stock_symbol=stock_symbol,
                option_instrument_key=option_instrument_key,
                option_type=option_type,
                strike_price=strike_price,
                expiry_date=expiry_date,
                current_premium=current_premium,
                lot_size=lot_size,
                signal=asdict(signal) if signal else None,
                capital_allocation=asdict(capital_allocation),
                risk_reward_ratio=risk_reward_ratio,
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                target_price=signal.target_price,
                trailing_stop_config=signal.trailing_stop_config,
                position_size_lots=capital_allocation.position_size_lots,
                total_investment=capital_allocation.allocated_capital,
                max_loss_amount=capital_allocation.max_loss,
                trading_mode=trading_mode.value,
                broker_name=broker_name,
                user_id=user_id,
                prepared_at=get_ist_isoformat(),
                valid_until=(
                    get_ist_now_naive() + timedelta(minutes=self.signal_validity_minutes)
                ).isoformat(),
                metadata={
                    "signal_confidence": float(signal.confidence),
                    "signal_reason": signal.reason,
                    "capital_utilization_percent": float(
                        capital_allocation.capital_utilization_percent
                    ),
                    "risk_per_trade_percent": float(
                        capital_allocation.risk_per_trade_percent
                    ),
                },
            )

            logger.info(f"Trade prepared successfully: {stock_symbol} {option_type}")
            logger.info(
                f"  Entry: {signal.entry_price}, SL: {signal.stop_loss}, Target: {signal.target_price}"
            )
            logger.info(
                f"  Position: {capital_allocation.position_size_lots} lots, Investment: Rs.{capital_allocation.allocated_capital:,.2f}"
            )
            
            log_to_db(
                component="trade_prep",
                message=f"Trade READY: {stock_symbol} {option_type} @ {signal.entry_price}",
                level="INFO",
                user_id=user_id,
                symbol=stock_symbol,
                additional_data={
                    "option_type": option_type,
                    "strike": float(strike_price),
                    "premium": float(current_premium),
                    "lots": capital_allocation.position_size_lots
                }
            )

            return prepared_trade

        except Exception as e:
            logger.error(f"Error preparing trade: {e}")
            log_to_db(
                component="trade_prep",
                message=f"FAILED Prep: {stock_symbol} - {str(e)}",
                level="ERROR",
                user_id=user_id,
                symbol=stock_symbol
            )
            
            # Notify Admin/User of failure
            from services.notifications.alert_manager import alert_manager
            self._safe_dispatch(alert_manager.notify_critical_error(
                user_id=user_id,
                component="TRADE_PREP",
                error=f"Failed to prepare trade for {stock_symbol}: {str(e)}"
            ))
            
            return self._create_error_trade(
                TradeStatus.ERROR,
                user_id,
                stock_symbol,
                option_instrument_key,
                option_type,
                strike_price,
                expiry_date,
                lot_size,
                trading_mode,
                str(e),
            )

    def _get_current_option_premium(
        self,
        option_instrument_key: str,
        broker_config: Optional[Any],
        trading_mode: TradingMode,
    ) -> Decimal:
        """
        Fetch current option premium from live market data

        CRITICAL: Always uses REAL market prices, even for paper trading.
        Paper trading needs accurate prices for realistic simulation.

        Args:
            option_instrument_key: Option instrument key
            broker_config: Broker configuration (optional for paper trading)
            trading_mode: Trading mode

        Returns:
            Current option premium (0 if not available)
        """
        try:
            # Always fetch REAL market prices - NO MOCK DATA
            from services.realtime_market_engine import get_market_engine

            engine = get_market_engine()

            if option_instrument_key in engine.instruments:
                instrument = engine.instruments[option_instrument_key]
                premium = Decimal(str(instrument.current_price))

                if premium > 0:
                    logger.info(
                        f"{'Paper' if trading_mode == TradingMode.PAPER else 'Live'} premium for {option_instrument_key}: Rs.{premium}"
                    )
                    return premium
                else:
                    logger.error(f"Premium is zero for {option_instrument_key}")
                    return Decimal("0")
            else:
                logger.error(
                    f"Instrument not found in market engine: {option_instrument_key}"
                )
                return Decimal("0")

        except Exception as e:
            logger.error(f"Error fetching option premium: {e}")
            return Decimal("0")

    def _get_historical_data(
        self,
        stock_symbol: str,
        option_instrument_key: str,
        broker_config: Optional[Any],
        trading_mode: TradingMode,
    ) -> Optional[Dict[str, List[float]]]:
        """
        Fetch historical candle data for strategy calculation from REAL market data

        CRITICAL: Always uses REAL historical data from broker API or market engine.
        NO MOCK DATA - returns None if real data unavailable.

        Args:
            stock_symbol: Stock symbol
            option_instrument_key: Option instrument key
            broker_config: Broker configuration
            trading_mode: Trading mode

        Returns:
            Dict with OHLC data lists, or None if unavailable
        """
        try:
            # First, try to get historical data from realtime market engine
            from services.realtime_market_engine import get_market_engine

            engine = get_market_engine()

            if option_instrument_key in engine.instruments:
                instrument = engine.instruments[option_instrument_key]

                # Check if instrument has historical spot data
                if (
                    hasattr(instrument, "historical_spot_data")
                    and instrument.historical_spot_data
                ):
                    historical_data = instrument.historical_spot_data
                    logger.info(
                        f"Using historical data from market engine for {option_instrument_key}"
                    )

                    # Validate data structure
                    if (
                        "close" in historical_data
                        and len(historical_data["close"]) >= 20
                    ):  # Minimum 20 candles for strategy
                        return historical_data
                    else:
                        logger.warning(
                            f"Insufficient historical data in market engine: {len(historical_data.get('close', []))} candles"
                        )

            # If market engine doesn't have data, fetch from broker API
            if broker_config:
                broker_name = broker_config.broker_name.lower()
                logger.info(f"Fetching historical data from {broker_name} broker API")

                if "upstox" in broker_name:
                    historical_data = self._fetch_upstox_historical_data(
                        option_instrument_key, broker_config
                    )
                    if historical_data:
                        return historical_data

                elif "angel" in broker_name:
                    historical_data = self._fetch_angel_historical_data(
                        option_instrument_key, broker_config
                    )
                    if historical_data:
                        return historical_data

                elif "dhan" in broker_name:
                    historical_data = self._fetch_dhan_historical_data(
                        option_instrument_key, broker_config
                    )
                    if historical_data:
                        return historical_data

                else:
                    logger.error(
                        f"Unsupported broker for historical data: {broker_name}"
                    )

            # If all methods fail, return None (DO NOT USE MOCK DATA)
            logger.error(
                f"Could not fetch real historical data for {option_instrument_key}"
            )
            return None

        except Exception as e:
            logger.error(f"Error fetching historical data: {e}", exc_info=True)
            return None

    def _fetch_upstox_historical_data(
        self, instrument_key: str, broker_config: Any
    ) -> Optional[Dict[str, List[float]]]:
        """
        Fetch historical data from Upstox API

        Args:
            instrument_key: Instrument key
            broker_config: Broker configuration

        Returns:
            OHLC data or None
        """
        try:
            from brokers.upstox_broker import UpstoxBroker
            from datetime import datetime, timedelta

            broker = UpstoxBroker(broker_config)

            # Fetch 1-minute candles for last 1 day
            to_date = get_ist_now_naive()
            from_date = to_date - timedelta(days=1)

            historical_data = broker.get_historical_data(
                instrument_key=instrument_key,
                interval="1minute",
                from_date=from_date.strftime("%Y-%m-%d"),
                to_date=to_date.strftime("%Y-%m-%d"),
            )

            if historical_data and "candles" in historical_data:
                candles = historical_data["candles"]

                if len(candles) < 20:
                    logger.warning(
                        f"Insufficient Upstox historical data: {len(candles)} candles"
                    )
                    return None

                # Convert to standard format
                opens = [candle[1] for candle in candles]
                highs = [candle[2] for candle in candles]
                lows = [candle[3] for candle in candles]
                closes = [candle[4] for candle in candles]
                volumes = [candle[5] for candle in candles]

                logger.info(f"Fetched {len(candles)} candles from Upstox")
                return {
                    "open": opens,
                    "high": highs,
                    "low": lows,
                    "close": closes,
                    "volume": volumes,
                }

            return None

        except Exception as e:
            logger.error(f"Error fetching Upstox historical data: {e}")
            return None

    def _fetch_angel_historical_data(
        self, instrument_key: str, broker_config: Any
    ) -> Optional[Dict[str, List[float]]]:
        """
        Fetch historical data from Angel One API

        Args:
            instrument_key: Instrument key
            broker_config: Broker configuration

        Returns:
            OHLC data or None
        """
        try:
            from brokers.angel_broker import AngelOneBroker
            from datetime import datetime, timedelta

            broker = AngelOneBroker(broker_config)

            # Angel One requires different instrument format
            # This is a placeholder - actual implementation depends on Angel One API
            logger.warning("Angel One historical data fetch not fully implemented")
            return None

        except Exception as e:
            logger.error(f"Error fetching Angel One historical data: {e}")
            return None

    def _fetch_dhan_historical_data(
        self, instrument_key: str, broker_config: Any
    ) -> Optional[Dict[str, List[float]]]:
        """
        Fetch historical data from Dhan API

        Args:
            instrument_key: Instrument key
            broker_config: Broker configuration

        Returns:
            OHLC data or None
        """
        try:
            from brokers.dhan_broker import DhanBroker
            from datetime import datetime, timedelta

            broker = DhanBroker(broker_config)

            # Dhan requires different instrument format
            # This is a placeholder - actual implementation depends on Dhan API
            logger.warning("Dhan historical data fetch not fully implemented")
            return None

        except Exception as e:
            logger.error(f"Error fetching Dhan historical data: {e}")
            return None

    def _create_pending_trade(
        self,
        user_id: int,
        stock_symbol: str,
        option_instrument_key: str,
        option_type: str,
        strike_price: Decimal,
        expiry_date: str,
        lot_size: int,
        current_premium: Decimal,
        capital_allocation: CapitalAllocation,
        signal: TradingSignal,
        trading_mode: TradingMode,
        broker_name: str,
        product: str = "I",
    ) -> PreparedTrade:
        """Create pending trade when no clear signal"""
        return PreparedTrade(
            status=TradeStatus.PENDING_SIGNAL,
            stock_symbol=stock_symbol,
            option_instrument_key=option_instrument_key,
            option_type=option_type,
            strike_price=strike_price,
            expiry_date=expiry_date,
            current_premium=current_premium,
            lot_size=lot_size,
            signal=asdict(signal),
            capital_allocation=asdict(capital_allocation),
            risk_reward_ratio=Decimal("0"),
            entry_price=current_premium,
            stop_loss=Decimal("0"),
            target_price=Decimal("0"),
            trailing_stop_config={},
            position_size_lots=capital_allocation.position_size_lots,
            total_investment=capital_allocation.allocated_capital,
            max_loss_amount=capital_allocation.max_loss,
            trading_mode=trading_mode.value,
            broker_name=broker_name,
            user_id=user_id,
            prepared_at=get_ist_isoformat(),
            valid_until=(
                get_ist_now_naive() + timedelta(minutes=self.signal_validity_minutes)
            ).isoformat(),
            metadata={"reason": signal.reason},
            product=product,
        )

    def _create_error_trade(
        self,
        status: TradeStatus,
        user_id: int,
        stock_symbol: str,
        option_instrument_key: str,
        option_type: str,
        strike_price: Decimal,
        expiry_date: str,
        lot_size: int,
        trading_mode: TradingMode,
        error_message: str,
        product: str = "I",
    ) -> PreparedTrade:
        """Create error trade response"""
        return PreparedTrade(
            status=status,
            stock_symbol=stock_symbol,
            option_instrument_key=option_instrument_key,
            option_type=option_type,
            strike_price=strike_price,
            expiry_date=expiry_date,
            current_premium=Decimal("0"),
            lot_size=lot_size,
            signal=None,
            capital_allocation=None,
            risk_reward_ratio=Decimal("0"),
            entry_price=Decimal("0"),
            stop_loss=Decimal("0"),
            target_price=Decimal("0"),
            trailing_stop_config={},
            position_size_lots=0,
            total_investment=Decimal("0"),
            max_loss_amount=Decimal("0"),
            trading_mode=trading_mode.value,
            broker_name=None,
            user_id=user_id,
            prepared_at=get_ist_isoformat(),
            valid_until=get_ist_isoformat(),
            metadata={"error": error_message},
            product=product,
        )

    def _calculate_atr_from_historical(
        self, historical_data: Dict[str, List[float]], period: int = 14
    ) -> Optional[float]:
        """
        Calculate Average True Range from historical data

        Args:
            historical_data: Dict with high, low, close lists
            period: ATR period (default 14)

        Returns:
            ATR value or None if insufficient data
        """
        try:
            high_prices = historical_data.get("high", [])
            low_prices = historical_data.get("low", [])
            close_prices = historical_data.get("close", [])

            if len(close_prices) < period + 1:
                return None

            import numpy as np

            high_arr = np.array(high_prices[-period - 1 :])
            low_arr = np.array(low_prices[-period - 1 :])
            close_arr = np.array(close_prices[-period - 1 :])

            # Calculate True Range
            tr1 = high_arr[1:] - low_arr[1:]
            tr2 = np.abs(high_arr[1:] - close_arr[:-1])
            tr3 = np.abs(low_arr[1:] - close_arr[:-1])

            tr = np.maximum(tr1, np.maximum(tr2, tr3))

            # Calculate ATR (simple moving average)
            atr = np.mean(tr)

            return float(atr)

        except Exception as e:
            logger.error(f"Error calculating ATR: {e}")
            return None


# Create singleton instance
trade_prep_service = TradePrepService()
