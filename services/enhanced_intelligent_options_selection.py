"""
Enhanced Intelligent Options Selection Service
Integrates stock selection with options contracts, expiry selection, and ATM strikes
"""

import logging
import asyncio
from datetime import datetime, timedelta, time as dt_time, date
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal
from dataclasses import dataclass, asdict, field
from enum import Enum
from sqlalchemy.orm import Session
from database.connection import SessionLocal
from database.models import SelectedStock
from utils.timezone_utils import get_ist_now_naive

# Import existing services
from services.intelligent_stock_selection_service import (
    intelligent_stock_selector,
    MarketSentiment,
    TradingPhase,
    StockSelection,
)
from services.upstox_option_service import upstox_option_service
from services.dynamic_risk_config import dynamic_risk_manager, MarketVolatility

logger = logging.getLogger(__name__)


def determine_option_direction_from_sentiment(
    sentiment: MarketSentiment, change_percent: float = 0.0
) -> str:
    """
    Determine option direction (CE/PE) based on market sentiment and stock movement

    CRITICAL: Never use default values without considering market sentiment.
    Wrong direction selection can lead to catastrophic losses.

    Args:
        sentiment: Current market sentiment
        change_percent: Stock's change percentage for additional confirmation

    Returns:
        "CE" for bullish sentiment (buy calls), "PE" for bearish sentiment (buy puts)

    Raises:
        ValueError: If sentiment is invalid or cannot be determined
    """
    if not sentiment:
        raise ValueError(
            "Market sentiment is REQUIRED - cannot determine option direction without it"
        )

    # Map market sentiment to option direction
    if sentiment in [MarketSentiment.VERY_BULLISH, MarketSentiment.BULLISH]:
        # Bullish market - buy CALL options
        logger.info(
            f"Bullish sentiment ({sentiment.value}) - selecting CE (Call) options"
        )
        return "CE"
    elif sentiment in [MarketSentiment.VERY_BEARISH, MarketSentiment.BEARISH]:
        # Bearish market - buy PUT options
        logger.info(
            f"Bearish sentiment ({sentiment.value}) - selecting PE (Put) options"
        )
        return "PE"
    else:
        # Neutral market - use stock's own momentum as tiebreaker
        if change_percent > 0.5:
            logger.info(
                f"Neutral sentiment with positive momentum ({change_percent:.2f}%) - selecting CE (Call) options"
            )
            return "CE"
        elif change_percent < -0.5:
            logger.info(
                f"Neutral sentiment with negative momentum ({change_percent:.2f}%) - selecting PE (Put) options"
            )
            return "PE"
        else:
            # True neutral - this is risky, log warning
            logger.warning(
                f"NEUTRAL sentiment with minimal movement ({change_percent:.2f}%) - defaulting to CE but this is RISKY"
            )
            return "CE"


@dataclass
class OptionContract:
    """
    Enhanced option contract with complete trading details

    Attributes:
        stock_symbol: Underlying stock ticker symbol
        option_instrument_key: Instrument key for option contract (used for trading)
        underlying_instrument_key: Instrument key for underlying asset
        option_type: Option type - CE (Call) or PE (Put)
        strike_price: Strike price of option contract
        expiry_date: Expiry date in YYYY-MM-DD format
        premium: Current option premium price
        volume: Trading volume
        open_interest: Open interest for contract
        bid_price: Current bid price
        ask_price: Current ask price
        delta: Option delta Greek
        gamma: Option gamma Greek
        theta: Option theta Greek
        vega: Option vega Greek
        implied_volatility: Implied volatility percentage
        lot_size: Number of shares per lot
        minimum_lot: Minimum tradeable lots
        freeze_quantity: Maximum order quantity before freeze
        selection_reason: Reason for contract selection
        confidence_score: Selection confidence (0-1)
        risk_reward_ratio: Risk to reward ratio
        selected_at: Timestamp of selection
        valid_until: Validity timestamp
    """

    # Contract identification
    stock_symbol: str
    option_instrument_key: str
    underlying_instrument_key: str
    option_type: str  # "CE" or "PE"
    strike_price: Decimal
    expiry_date: str

    # Market data
    premium: Decimal
    volume: int
    open_interest: int
    bid_price: Decimal
    ask_price: Decimal

    # Greeks
    delta: Decimal
    gamma: Decimal
    theta: Decimal
    vega: Decimal
    implied_volatility: Decimal

    # Trading details
    lot_size: int
    minimum_lot: int
    freeze_quantity: int

    # Selection metadata
    selection_reason: str
    confidence_score: Decimal
    risk_reward_ratio: Decimal

    # Timestamps
    selected_at: str
    valid_until: str


@dataclass
class EnhancedStockSelection(StockSelection):
    """
    Extended stock selection with options contract details

    Attributes:
        selected_option_contract: Selected option contract for trading
        available_expiry_dates: List of available expiry dates
        atm_strike: At-the-money strike price
        recommended_strike: Recommended strike for trading
        capital_allocation: Capital allocated for this position
        max_loss: Maximum acceptable loss amount
        target_profit: Target profit amount
        risk_reward_ratio: Risk to reward ratio
        entry_conditions: Entry criteria for trade
        exit_conditions: Exit criteria for trade
        trailing_stop_loss: Trailing stop loss configuration
    """

    # Options contract information
    selected_option_contract: Optional[OptionContract] = None
    available_expiry_dates: List[str] = field(default_factory=list)
    atm_strike: Decimal = Decimal("0.0")
    recommended_strike: Decimal = Decimal("0.0")

    # Options strategy parameters
    capital_allocation: Decimal = Decimal("0.0")
    position_size_lots: int = 1
    max_loss: Decimal = Decimal("0.0")
    target_profit: Decimal = Decimal("0.0")
    risk_reward_ratio: Decimal = Decimal("0.0")

    # Entry and exit conditions
    entry_conditions: Dict[str, Any] = field(default_factory=dict)
    exit_conditions: Dict[str, Any] = field(default_factory=dict)
    trailing_stop_loss: Dict[str, Any] = field(default_factory=dict)


class ExpirySelectionStrategy(Enum):
    """Expiry selection strategies based on market conditions"""

    NEAREST_WEEKLY = "nearest_weekly"  # Nearest Thursday expiry
    NEAREST_MONTHLY = "nearest_monthly"  # Nearest monthly expiry
    OPTIMAL_THETA = "optimal_theta"  # Best theta decay balance
    HIGH_LIQUIDITY = "high_liquidity"  # Highest OI and volume


class EnhancedIntelligentOptionsService:
    """
    Enhanced service that combines intelligent stock selection with options trading

    This service:
    1. Selects stocks using intelligent_stock_selector
    2. Finds optimal option contracts (CE/PE) for each stock
    3. Determines best expiry dates based on strategy
    4. Calculates capital allocation and risk parameters
    5. Stores option instrument keys for trade execution
    """

    def __init__(self):
        """Initialize enhanced options service with configuration"""
        self.base_selector = intelligent_stock_selector
        self.option_service = upstox_option_service

        # Enhanced selection state
        self.premarket_options_selections: List[EnhancedStockSelection] = []
        self.final_options_selections: List[EnhancedStockSelection] = []

        # Options-specific configuration
        self.options_config = {
            "expiry_strategy": ExpirySelectionStrategy.NEAREST_WEEKLY,
            "strike_selection_range": 5,
            "min_option_volume": 100,
            "min_open_interest": 500,
            "max_premium_percentage": Decimal("5.0"),
            "min_iv_threshold": Decimal("15.0"),
            "max_iv_threshold": Decimal("40.0"),
            "capital_per_stock": Decimal("50000"),
            "max_risk_per_trade": Decimal("0.02"),
        }

        logger.info("Enhanced Intelligent Options Service initialized")

    async def enhance_selected_stocks_with_options(
        self, selected_stocks: List[StockSelection], selection_type: str = "final"
    ) -> Dict[str, Any]:
        """
        Enhance already-selected stocks with option contracts

        This function is called AFTER stock selection is complete.
        It takes the selected stocks and adds option contract details.

        Args:
            selected_stocks: List of stocks already selected by intelligent_stock_selector
            selection_type: Type of selection - "premarket" or "final"

        Returns:
            Dictionary containing enhanced selections with option contracts

        Raises:
            ValueError: If selected_stocks is empty or invalid
        """
        try:
            if not selected_stocks:
                return {
                    "success": False,
                    "error": "No stocks provided for option enhancement",
                    "enhanced_selections": [],
                }

            logger.info(
                f"Enhancing {len(selected_stocks)} selected stocks with option contracts"
            )

            # Enhance with options contracts
            enhanced_selections = []

            db = SessionLocal()
            try:
                for stock in selected_stocks:
                    enhanced_stock = await self._enhance_stock_with_options(stock, db)
                    if enhanced_stock and enhanced_stock.selected_option_contract:
                        enhanced_selections.append(enhanced_stock)
                        logger.info(
                            f"Enhanced {stock.symbol} with {enhanced_stock.selected_option_contract.option_type} "
                            f"option at strike {enhanced_stock.selected_option_contract.strike_price}"
                        )
                    else:
                        logger.warning(
                            f"Could not find suitable option contract for {stock.symbol}"
                        )
            finally:
                db.close()

            # Store based on selection type
            if selection_type == "premarket":
                self.premarket_options_selections = enhanced_selections
            else:
                self.final_options_selections = enhanced_selections

            # Calculate capital allocation and risk management
            await self._calculate_capital_allocation(enhanced_selections)

            result = {
                "success": True,
                "selection_type": selection_type,
                "total_stocks": len(selected_stocks),
                "enhanced_selections": [asdict(stock) for stock in enhanced_selections],
                "options_contracts_found": len(enhanced_selections),
                "total_capital_required": float(
                    sum(s.capital_allocation for s in enhanced_selections)
                ),
                "options_ready": len(enhanced_selections) > 0,
                "timestamp": datetime.now().isoformat(),
            }

            # Save enhanced selections to database
            db_type = f"{selection_type}_options"
            await self._save_enhanced_selections_to_db(enhanced_selections, db_type)

            logger.info(
                f"Options enhancement complete: {len(enhanced_selections)}/{len(selected_stocks)} stocks enhanced"
            )
            return result

        except ValueError as ve:
            logger.error(f"Validation error in options enhancement: {ve}")
            return {"success": False, "error": str(ve)}
        except Exception as e:
            logger.error(f"Error in options enhancement: {e}")
            return {"success": False, "error": str(e)}

    async def _enhance_stock_with_options(
        self, stock_selection: StockSelection, db: Session
    ) -> Optional[EnhancedStockSelection]:
        """
        Enhance stock selection with options contract details

        Args:
            stock_selection: Base stock selection from intelligent selector
            db: Database session

        Returns:
            Enhanced selection with option contract or None if not found

        Raises:
            ValueError: If stock selection is invalid
        """
        if not stock_selection or not stock_selection.symbol:
            raise ValueError("Invalid stock selection provided")

        try:
            # Get underlying instrument key
            underlying_key = stock_selection.instrument_key
            if not underlying_key:
                underlying_key = f"NSE_EQ|{stock_selection.symbol}"

            # Step 1: Get available expiry dates and lot size
            expiry_dates, lot_size = await self._get_available_expiry_and_lot_size(underlying_key, db)
            if not expiry_dates:
                logger.warning(f"No expiry dates found for {stock_selection.symbol}")
                return None

            # Step 2: Select optimal expiry
            selected_expiry = await self._select_optimal_expiry(
                expiry_dates, underlying_key, db
            )
            if not selected_expiry:
                logger.warning(f"No suitable expiry found for {stock_selection.symbol}")
                return None

            # Step 3: Get option chain for selected expiry
            option_chain = await self._get_option_chain_async(
                underlying_key, selected_expiry, db
            )
            if not option_chain or not option_chain.get("data"):
                logger.warning(f"No option chain data for {stock_selection.symbol}")
                return None

            # Step 4: Select optimal strike and option type
            # CRITICAL: Determine option direction based on market sentiment
            # Never default without considering market conditions
            # VALIDATED: CE/PE logic is correct - uses market sentiment and stock momentum

            options_direction = getattr(
                stock_selection, "options_direction", None
            ) or getattr(stock_selection, "option_type", None)

            # If not available in selection, determine from current market sentiment
            if not options_direction:
                current_sentiment = self.base_selector.current_sentiment
                change_percent = float(getattr(stock_selection, "change_percent", 0.0))

                if not current_sentiment:
                    error_msg = f"Cannot determine option direction for {stock_selection.symbol} - market sentiment unavailable"
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                options_direction = determine_option_direction_from_sentiment(
                    current_sentiment, change_percent
                )
                logger.info(
                    f"Determined option direction for {stock_selection.symbol}: {options_direction} based on {current_sentiment.value} sentiment"
                )

            # VALIDATED: Uses real-time LTP for ATM strike selection
            # Handle both StockSelection (has ltp) and SelectedStock (has price_at_selection)
            # StockSelection.ltp contains real-time price from market data at selection time
            underlying_price = getattr(stock_selection, "ltp", None) or getattr(
                stock_selection, "price_at_selection", 0
            )
            optimal_contract = await self._select_optimal_option_contract(
                option_chain,
                options_direction,
                Decimal(str(underlying_price)),
                lot_size=lot_size
            )

            if not optimal_contract:
                logger.warning(
                    f"No suitable option contract for {stock_selection.symbol}"
                )
                return None

            # Step 5: Create enhanced selection
            # Handle both StockSelection dataclass and SelectedStock database model
            # SelectedStock doesn't have all fields, so we use getattr with defaults
            enhanced_selection = EnhancedStockSelection(
                # Required fields (with fallbacks for database model)
                symbol=stock_selection.symbol,
                name=getattr(stock_selection, "name", stock_selection.symbol),  # Fallback to symbol
                instrument_key=stock_selection.instrument_key,
                sector=getattr(stock_selection, "sector", "UNKNOWN"),
                lot_size=lot_size,  # Use correctly fetched lot size
                # Price fields (handle both ltp and price_at_selection)
                ltp=getattr(stock_selection, "ltp", None) or getattr(stock_selection, "price_at_selection", 0.0),
                change_percent=getattr(stock_selection, "change_percent", 0.0) or getattr(stock_selection, "change_percent_at_selection", 0.0),
                change=getattr(stock_selection, "change", 0.0),
                volume=getattr(stock_selection, "volume", 0) or getattr(stock_selection, "volume_at_selection", 0),
                value_crores=getattr(stock_selection, "value_crores", 0.0),
                high=getattr(stock_selection, "high", 0.0),
                low=getattr(stock_selection, "low", 0.0),
                previous_close=getattr(stock_selection, "previous_close", 0.0),
                # Scoring fields (with defaults)
                sentiment_score=getattr(stock_selection, "sentiment_score", 0.5),
                sector_score=getattr(stock_selection, "sector_score", 0.5),
                technical_score=getattr(stock_selection, "technical_score", 0.5),
                volume_score=getattr(stock_selection, "volume_score", 0.5),
                value_score=getattr(stock_selection, "value_score", 0.5),
                final_score=getattr(stock_selection, "final_score", 0.0) or getattr(stock_selection, "selection_score", 0.0),
                # Selection metadata
                selection_reason=getattr(stock_selection, "selection_reason", "options_enhancement") or getattr(stock_selection, "selection_reason", ""),
                confidence_level=getattr(stock_selection, "confidence_level", 0.5),
                risk_level=getattr(stock_selection, "risk_level", "MEDIUM"),
                recommended_quantity=lot_size,  # Set recommended quantity to one lot size by default
                target_value=getattr(stock_selection, "target_value", 0.0),
                stop_loss=getattr(stock_selection, "stop_loss", 0.0),
                options_direction=getattr(stock_selection, "options_direction", None) or getattr(stock_selection, "option_type", "CE"),
                selected_at=getattr(stock_selection, "selected_at", datetime.now().isoformat()),
                valid_until=getattr(stock_selection, "valid_until", (datetime.now().replace(hour=15, minute=30)).isoformat()),
                # Add enhanced fields
                selected_option_contract=optimal_contract,
                available_expiry_dates=expiry_dates,
                atm_strike=Decimal(str(option_chain.get("atm_strike", 0.0))),
                recommended_strike=optimal_contract.strike_price,
            )

            # Step 6: Calculate entry/exit conditions
            await self._calculate_entry_exit_conditions(enhanced_selection)

            return enhanced_selection

        except ValueError as ve:
            logger.error(
                f"Validation error enhancing stock with options for {stock_selection.symbol}: {ve}"
            )
            return None
        except Exception as e:
            logger.error(
                f"Error enhancing stock with options for {stock_selection.symbol}: {e}"
            )
            return None

    async def _get_available_expiry_and_lot_size(
        self, underlying_key: str, db: Session
    ) -> Tuple[List[str], int]:
        """
        Get available expiry dates and lot size for the underlying

        Args:
            underlying_key: Instrument key for underlying asset
            db: Database session

        Returns:
            Tuple of (List of expiry dates, lot_size)

        Raises:
            ValueError: If underlying_key is invalid
        """
        if not underlying_key:
            raise ValueError("Underlying key cannot be empty")

        try:
            # Get option contracts to find expiry dates and lot size
            contracts = self.option_service.get_option_contracts(underlying_key, db)
            if not contracts:
                return [], 0

            # Extract unique expiry dates
            expiry_dates = list(
                set(
                    contract.get("expiry")
                    for contract in contracts
                    if contract.get("expiry")
                )
            )
            expiry_dates.sort()

            # Extract lot size from the first contract
            lot_size = int(contracts[0].get("lot_size", 0))

            # Filter only future expiry dates
            today = datetime.now().date()
            future_expiries = [
                expiry
                for expiry in expiry_dates
                if datetime.strptime(expiry, "%Y-%m-%d").date() > today
            ]

            return future_expiries[:10], lot_size

        except ValueError as ve:
            logger.error(
                f"Validation error getting expiry dates for {underlying_key}: {ve}"
            )
            return [], 0
        except Exception as e:
            logger.error(f"Error getting expiry dates for {underlying_key}: {e}")
            return [], 0

    async def _select_optimal_expiry(
        self, expiry_dates: List[str], underlying_key: str, db: Session
    ) -> Optional[str]:
        """
        Select optimal expiry based on strategy and liquidity

        Args:
            expiry_dates: List of available expiry dates
            underlying_key: Instrument key for underlying
            db: Database session

        Returns:
            Selected expiry date or None

        Raises:
            ValueError: If expiry_dates is empty
        """
        if not expiry_dates:
            return None

        try:
            strategy = self.options_config["expiry_strategy"]
            today = datetime.now().date()

            if strategy == ExpirySelectionStrategy.NEAREST_WEEKLY:
                # Find nearest Thursday (weekly expiry)
                for expiry in expiry_dates:
                    expiry_date = datetime.strptime(expiry, "%Y-%m-%d").date()
                    if expiry_date.weekday() == 3:  # Thursday
                        return expiry

                # Fallback to nearest expiry
                return expiry_dates[0]

            elif strategy == ExpirySelectionStrategy.NEAREST_MONTHLY:
                # Find nearest monthly expiry (last Thursday of month)
                for expiry in expiry_dates:
                    expiry_date = datetime.strptime(expiry, "%Y-%m-%d").date()
                    if expiry_date.weekday() == 3:  # Thursday
                        # Check if it's last Thursday of month
                        next_week = expiry_date + timedelta(days=7)
                        if next_week.month != expiry_date.month:
                            return expiry

                # Fallback to first available
                return expiry_dates[0]

            elif strategy == ExpirySelectionStrategy.OPTIMAL_THETA:
                # Select expiry with optimal time decay (7-21 days)
                optimal_expiries = []
                for expiry in expiry_dates:
                    expiry_date = datetime.strptime(expiry, "%Y-%m-%d").date()
                    days_to_expiry = (expiry_date - today).days
                    if 7 <= days_to_expiry <= 21:
                        optimal_expiries.append(expiry)

                return optimal_expiries[0] if optimal_expiries else expiry_dates[0]

            elif strategy == ExpirySelectionStrategy.HIGH_LIQUIDITY:
                # Select expiry with highest total OI and volume
                best_expiry = None
                max_liquidity_score = 0

                for expiry in expiry_dates[:3]:
                    chain = await self._get_option_chain_async(
                        underlying_key, expiry, db
                    )
                    if chain and chain.get("analytics"):
                        total_oi = chain["analytics"].get("total_call_oi", 0) + chain[
                            "analytics"
                        ].get("total_put_oi", 0)
                        liquidity_score = total_oi

                        if liquidity_score > max_liquidity_score:
                            max_liquidity_score = liquidity_score
                            best_expiry = expiry

                return best_expiry or expiry_dates[0]

            # Default: nearest expiry
            return expiry_dates[0]

        except ValueError as ve:
            logger.error(f"Validation error selecting optimal expiry: {ve}")
            return expiry_dates[0] if expiry_dates else None
        except Exception as e:
            logger.error(f"Error selecting optimal expiry: {e}")
            return expiry_dates[0] if expiry_dates else None

    async def _get_option_chain_async(
        self, underlying_key: str, expiry_date: str, db: Session
    ) -> Optional[Dict[str, Any]]:
        """
        Async wrapper for option chain fetching

        Args:
            underlying_key: Instrument key for underlying
            expiry_date: Expiry date in YYYY-MM-DD format
            db: Database session

        Returns:
            Option chain data dictionary or None

        Raises:
            ValueError: If parameters are invalid
        """
        if not underlying_key or not expiry_date:
            raise ValueError("Underlying key and expiry date are required")

        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            option_chain = await loop.run_in_executor(
                None,
                self.option_service.get_option_chain,
                underlying_key,
                expiry_date,
                db,
            )
            return option_chain
        except ValueError as ve:
            logger.error(f"Validation error getting option chain: {ve}")
            return None
        except Exception as e:
            logger.error(f"Error getting option chain async: {e}")
            return None

    async def _select_optimal_option_contract(
        self,
        option_chain: Dict[str, Any],
        option_direction: str,
        underlying_price: Decimal,
        lot_size: int = 0
    ) -> Optional[OptionContract]:
        """
        Select optimal option contract based on direction and criteria

        Args:
            option_chain: Option chain data from Upstox API
            option_direction: "CE" for calls or "PE" for puts
            underlying_price: Current underlying asset price
            lot_size: Lot size for the option contract (if known)

        Returns:
            Selected OptionContract or None

        Raises:
            ValueError: If parameters are invalid
        """
        if not option_chain:
            raise ValueError("Option chain cannot be empty")
        if option_direction not in ["CE", "PE"]:
            raise ValueError("Option direction must be 'CE' or 'PE'")
        if underlying_price <= 0:
            raise ValueError("Underlying price must be positive")

        try:
            chain_data = option_chain.get("data", [])
            if not chain_data:
                return None

            atm_strike = Decimal(str(option_chain.get("atm_strike", underlying_price)))
            spot_price = Decimal(str(option_chain.get("spot_price", underlying_price)))

            # Filter contracts by option type and liquidity
            eligible_contracts = []

            for strike_data in chain_data:
                strike_price = Decimal(str(strike_data.get("strike_price", 0)))

                # Get option data based on direction
                option_data = None
                option_type = option_direction

                if option_direction == "CE" and strike_data.get("call_options"):
                    option_data = strike_data["call_options"]
                elif option_direction == "PE" and strike_data.get("put_options"):
                    option_data = strike_data["put_options"]
                else:
                    continue

                market_data = option_data.get("market_data", {})
                option_greeks = option_data.get("option_greeks", {})

                # Extract and validate data
                volume = int(market_data.get("volume", 0))
                oi = int(market_data.get("oi", 0))
                premium = Decimal(str(market_data.get("ltp", 0)))
                iv = Decimal(str(option_greeks.get("iv", 0)))

                # Apply filters
                min_volume = self.options_config["min_option_volume"]
                min_oi = self.options_config["min_open_interest"]
                min_iv = self.options_config["min_iv_threshold"]
                max_iv = self.options_config["max_iv_threshold"]

                if (
                    volume >= min_volume
                    and oi >= min_oi
                    and premium > 0
                    and min_iv <= iv <= max_iv
                ):

                    # Calculate selection criteria
                    distance_from_atm = abs(strike_price - atm_strike)
                    premium_percentage = (premium / spot_price) * Decimal("100")

                    if (
                        premium_percentage
                        <= self.options_config["max_premium_percentage"]
                    ):
                        selection_score = self._calculate_option_selection_score(
                            distance_from_atm, premium, volume, oi, iv, spot_price
                        )

                        eligible_contracts.append(
                            {
                                "strike_data": strike_data,
                                "option_data": option_data,
                                "option_type": option_type,
                                "strike_price": strike_price,
                                "distance_from_atm": distance_from_atm,
                                "premium": premium,
                                "volume": volume,
                                "oi": oi,
                                "iv": iv,
                                "market_data": market_data,
                                "option_greeks": option_greeks,
                                "selection_score": selection_score,
                            }
                        )

            if not eligible_contracts:
                logger.warning(f"No eligible {option_direction} contracts found")
                return None

            # Select best contract based on selection score
            best_contract = max(eligible_contracts, key=lambda x: x["selection_score"])

            # Determine lot size - use parameter if provided, else try to get from data, else default 0
            # Defaulting to 0 allows trade_prep_service to fetch the correct lot size
            final_lot_size = lot_size
            if final_lot_size <= 0:
                final_lot_size = int(best_contract["option_data"].get("lot_size", 0))

            # Create OptionContract object
            option_contract = OptionContract(
                stock_symbol=option_chain.get("underlying_key", "").split("|")[-1],
                option_instrument_key=best_contract["option_data"].get(
                    "instrument_key", ""
                ),
                underlying_instrument_key=option_chain.get("underlying_key", ""),
                option_type=best_contract["option_type"],
                strike_price=best_contract["strike_price"],
                expiry_date=option_chain.get("expiry", ""),
                premium=best_contract["premium"],
                volume=best_contract["volume"],
                open_interest=best_contract["oi"],
                bid_price=Decimal(
                    str(best_contract["market_data"].get("bid_price", 0))
                ),
                ask_price=Decimal(
                    str(best_contract["market_data"].get("ask_price", 0))
                ),
                delta=Decimal(str(best_contract["option_greeks"].get("delta", 0))),
                gamma=Decimal(str(best_contract["option_greeks"].get("gamma", 0))),
                theta=Decimal(str(best_contract["option_greeks"].get("theta", 0))),
                vega=Decimal(str(best_contract["option_greeks"].get("vega", 0))),
                implied_volatility=best_contract["iv"],
                lot_size=final_lot_size,
                minimum_lot=int(best_contract["option_data"].get("minimum_lot", 1)),
                freeze_quantity=int(
                    best_contract["option_data"].get("freeze_quantity", 500)
                ),
                selection_reason=f"Best {option_direction} contract: Strike {best_contract['strike_price']}, IV {best_contract['iv']:.1f}%, OI {best_contract['oi']}",
                confidence_score=min(
                    best_contract["selection_score"] / Decimal("100"), Decimal("1.0")
                ),
                risk_reward_ratio=Decimal("0.0"),
                selected_at=datetime.now().isoformat(),
                valid_until=(datetime.now().replace(hour=15, minute=30)).isoformat(),
            )

            return option_contract

        except ValueError as ve:
            logger.error(f"Validation error selecting optimal option contract: {ve}")
            return None
        except Exception as e:
            logger.error(f"Error selecting optimal option contract: {e}")
            return None

    def _calculate_option_selection_score(
        self,
        distance_from_atm: Decimal,
        premium: Decimal,
        volume: int,
        oi: int,
        iv: Decimal,
        underlying_price: Decimal
    ) -> Decimal:
        """
        Calculate selection score for option contract

        Args:
            distance_from_atm: Distance of strike from ATM
            premium: Option premium
            volume: Trading volume
            oi: Open interest
            iv: Implied volatility
            underlying_price: Current underlying price for normalization

        Returns:
            Selection score (0-100 scale)
        """
        try:
            # Scoring factors (0-100 scale)

            # 1. Distance from ATM (prefer ATM or slightly OTM)
            # Use dynamic threshold: 1% of underlying price or 50 points, whichever is larger
            # This handles both low-priced stocks and high-priced indices
            distance_threshold = max(Decimal("50"), underlying_price * Decimal("0.01"))
            
            distance_score = max(
                Decimal("0"),
                Decimal("100") - (distance_from_atm / distance_threshold) * Decimal("100"),
            )

            # 2. Liquidity (volume + OI)
            liquidity_score = min(
                Decimal("100"), (Decimal(str(volume + oi)) / Decimal("100"))
            )

            # 3. IV score (prefer moderate IV)
            iv_optimal = Decimal("25.0")
            iv_score = max(
                Decimal("0"), Decimal("100") - abs(iv - iv_optimal) * Decimal("2")
            )

            # 4. Premium score (prefer reasonable premiums)
            premium_score = min(Decimal("100"), premium * Decimal("10"))

            # Weighted final score
            final_score = (
                distance_score * Decimal("0.4")
                + liquidity_score * Decimal("0.3")
                + iv_score * Decimal("0.2")
                + premium_score * Decimal("0.1")
            )

            return final_score

        except Exception as e:
            logger.error(f"Error calculating option selection score: {e}")
            return Decimal("0.0")

    async def _calculate_capital_allocation(
        self, selections: List[EnhancedStockSelection]
    ):
        """
        Calculate capital allocation and risk parameters using dynamic risk config

        Args:
            selections: List of enhanced stock selections

        Raises:
            ValueError: If selections is invalid
        """
        try:
            total_stocks = len(selections)
            if total_stocks == 0:
                return

            # Get current market sentiment for risk adjustment
            current_sentiment = (
                self.base_selector.current_sentiment.value
                if self.base_selector.current_sentiment
                else "neutral"
            )

            # Determine market volatility
            volatility_level = MarketVolatility.MEDIUM

            # Get adjusted risk configuration
            adjusted_risk_config = dynamic_risk_manager.adjust_for_market_conditions(
                current_sentiment, volatility_level
            )

            # Get position size limits
            total_capital = self.options_config["capital_per_stock"] * Decimal("10")
            position_limits = dynamic_risk_manager.get_position_size_limits(
                float(total_capital)
            )

            # Dynamic risk parameters
            max_loss_per_position = Decimal(
                str(adjusted_risk_config.max_loss_per_position)
            )
            max_total_exposure = Decimal(str(adjusted_risk_config.max_total_exposure))
            position_size_multiplier = Decimal(
                str(adjusted_risk_config.position_size_multiplier)
            )

            logger.info("Dynamic Risk Config Applied:")
            logger.info(f"   Max loss per position: {max_loss_per_position*100:.1f}%")
            logger.info(f"   Max total exposure: {max_total_exposure*100:.1f}%")
            logger.info(f"   Position size multiplier: {position_size_multiplier:.2f}x")

            for selection in selections:
                if not selection.selected_option_contract:
                    continue

                contract = selection.selected_option_contract
                premium = contract.premium
                lot_size = contract.lot_size

                if premium > 0 and lot_size > 0:
                    # Calculate position size
                    base_capital_per_position = Decimal(
                        str(position_limits["recommended_position_capital"])
                    )
                    adjusted_capital = (
                        base_capital_per_position * position_size_multiplier
                    )

                    # Calculate maximum lots
                    max_lots_by_capital = int(adjusted_capital / (premium * lot_size))
                    max_loss_amount = total_capital * max_loss_per_position
                    max_lots_by_risk = int(max_loss_amount / (premium * lot_size))

                    # Use the more conservative of capital or risk limits
                    recommended_lots = min(max_lots_by_capital, max_lots_by_risk)
                    recommended_lots = max(1, recommended_lots)

                    # Calculate capital allocation
                    selection.capital_allocation = premium * lot_size * recommended_lots
                    selection.position_size_lots = int(recommended_lots)
                    selection.max_loss = selection.capital_allocation

                    target_multiplier = (
                        Decimal(str(adjusted_risk_config.profit_booking_levels[-1]))
                        if adjusted_risk_config.profit_booking_levels
                        else Decimal("1.5")
                    )
                    selection.target_profit = (
                        selection.capital_allocation * target_multiplier
                    )
                    selection.risk_reward_ratio = (
                        selection.target_profit / selection.max_loss
                        if selection.max_loss > 0
                        else Decimal("0")
                    )

                    contract.risk_reward_ratio = selection.risk_reward_ratio

                    logger.info(f"Dynamic capital allocation for {selection.symbol}:")
                    logger.info(
                        f"   Capital: Rs.{selection.capital_allocation:,.0f} ({recommended_lots} lots)"
                    )
                    logger.info(f"   Max Loss: Rs.{selection.max_loss:,.0f}")
                    logger.info(f"   Target Profit: Rs.{selection.target_profit:,.0f}")

        except ValueError as ve:
            logger.error(f"Validation error calculating capital allocation: {ve}")
        except Exception as e:
            logger.error(f"Error calculating capital allocation: {e}")

    async def _calculate_entry_exit_conditions(self, selection: EnhancedStockSelection):
        """
        Calculate entry and exit conditions based on EMA + SuperTrend

        Args:
            selection: Enhanced stock selection

        Raises:
            ValueError: If selection is invalid
        """
        if not selection or not selection.selected_option_contract:
            raise ValueError("Invalid selection or missing option contract")

        try:
            # Entry conditions
            selection.entry_conditions = {
                "market_sentiment_confirmed": True,
                "option_iv_range": f"{self.options_config['min_iv_threshold']}-{self.options_config['max_iv_threshold']}%",
                "minimum_volume": self.options_config["min_option_volume"],
                "ema_condition": "Price above/below EMA based on direction",
                "supertrend_condition": "SuperTrend signal confirmation",
            }

            # Exit conditions
            selection.exit_conditions = {
                "profit_target": f"{selection.target_profit:,.0f} (150% return)",
                "stop_loss": f"{selection.max_loss:,.0f} (100% premium loss)",
                "time_decay_exit": "Exit 1 day before expiry if no profit",
                "ema_crossover": "Exit on EMA crossover against position",
                "supertrend_reversal": "Exit on SuperTrend reversal",
                "market_sentiment_change": "Exit if market sentiment changes significantly",
            }

            # Trailing stop loss
            selection.trailing_stop_loss = {
                "activation_profit": float(
                    selection.capital_allocation * Decimal("0.5")
                ),
                "trail_percentage": 20,
                "minimum_profit_lock": float(
                    selection.capital_allocation * Decimal("0.3")
                ),
            }

        except ValueError as ve:
            logger.error(f"Validation error calculating entry/exit conditions: {ve}")
        except Exception as e:
            logger.error(f"Error calculating entry/exit conditions: {e}")

    async def _validate_existing_options_contracts(
        self,
    ) -> List[EnhancedStockSelection]:
        """
        Validate existing options contracts are still tradeable

        Returns:
            List of validated enhanced selections
        """
        try:
            validated_selections = []
            db = SessionLocal()

            try:
                for selection in self.premarket_options_selections:
                    if not selection.selected_option_contract:
                        continue

                    # Get fresh option chain
                    option_chain = await self._get_option_chain_async(
                        selection.selected_option_contract.underlying_instrument_key,
                        selection.selected_option_contract.expiry_date,
                        db,
                    )

                    if option_chain and option_chain.get("data"):
                        # Update contract with latest data
                        updated_contract = await self._update_option_contract_data(
                            selection.selected_option_contract, option_chain
                        )

                        if updated_contract:
                            selection.selected_option_contract = updated_contract
                            validated_selections.append(selection)
            finally:
                db.close()

            return validated_selections

        except Exception as e:
            logger.error(f"Error validating existing options contracts: {e}")
            return []

    async def _update_option_contract_data(
        self, contract: OptionContract, option_chain: Dict[str, Any]
    ) -> Optional[OptionContract]:
        """
        Update option contract with latest market data

        Args:
            contract: Existing option contract
            option_chain: Fresh option chain data

        Returns:
            Updated OptionContract or None

        Raises:
            ValueError: If parameters are invalid
        """
        if not contract or not option_chain:
            raise ValueError("Contract and option chain are required")

        try:
            chain_data = option_chain.get("data", [])

            for strike_data in chain_data:
                if (
                    Decimal(str(strike_data.get("strike_price")))
                    == contract.strike_price
                ):
                    # Find matching option type
                    option_data = None
                    if contract.option_type == "CE" and strike_data.get("call_options"):
                        option_data = strike_data["call_options"]
                    elif contract.option_type == "PE" and strike_data.get(
                        "put_options"
                    ):
                        option_data = strike_data["put_options"]

                    if option_data:
                        market_data = option_data.get("market_data", {})
                        option_greeks = option_data.get("option_greeks", {})

                        # Update with fresh data
                        contract.premium = Decimal(
                            str(market_data.get("ltp", contract.premium))
                        )
                        contract.volume = int(
                            market_data.get("volume", contract.volume)
                        )
                        contract.open_interest = int(
                            market_data.get("oi", contract.open_interest)
                        )
                        contract.bid_price = Decimal(
                            str(market_data.get("bid_price", contract.bid_price))
                        )
                        contract.ask_price = Decimal(
                            str(market_data.get("ask_price", contract.ask_price))
                        )

                        contract.delta = Decimal(
                            str(option_greeks.get("delta", contract.delta))
                        )
                        contract.gamma = Decimal(
                            str(option_greeks.get("gamma", contract.gamma))
                        )
                        contract.theta = Decimal(
                            str(option_greeks.get("theta", contract.theta))
                        )
                        contract.vega = Decimal(
                            str(option_greeks.get("vega", contract.vega))
                        )
                        contract.implied_volatility = Decimal(
                            str(option_greeks.get("iv", contract.implied_volatility))
                        )

                        return contract

            return None

        except ValueError as ve:
            logger.error(f"Validation error updating option contract data: {ve}")
            return None
        except Exception as e:
            logger.error(f"Error updating option contract data: {e}")
            return None

    async def _save_enhanced_selections_to_db(
        self, selections: List[EnhancedStockSelection], selection_type: str
    ) -> bool:
        """
        Save enhanced selections with options data to database
        UPDATED: Now updates existing records to prevent duplicates and ensure data integrity.
        """
        if not selection_type:
            raise ValueError("Selection type cannot be empty")

        try:
            if not selections:
                return True

            db = SessionLocal()
            try:
                today = get_ist_now_naive().date()

                # Save new selections
                for selection in selections:
                    if not selection.selected_option_contract:
                        continue

                    contract = selection.selected_option_contract

                    # Prepare metadata
                    sentiment_direction = getattr(
                        selection, "options_direction", None
                    ) or getattr(selection, "option_type", contract.option_type)

                    enhanced_metadata = {
                        "stock_symbol": selection.symbol,
                        "sector": selection.sector,
                        "sentiment_direction": sentiment_direction,
                        "final_score": float(selection.final_score),
                        "option_instrument_key": contract.option_instrument_key,
                        "option_type": contract.option_type,
                        "strike_price": float(contract.strike_price),
                        "expiry_date": contract.expiry_date,
                        "premium": float(contract.premium),
                        "volume": contract.volume,
                        "open_interest": contract.open_interest,
                        "implied_volatility": float(contract.implied_volatility),
                        "lot_size": contract.lot_size,
                        "delta": float(contract.delta),
                        "gamma": float(contract.gamma),
                        "theta": float(contract.theta),
                        "vega": float(contract.vega),
                        "capital_allocation": float(selection.capital_allocation),
                        "position_size_lots": int(selection.position_size_lots),
                        "max_loss": float(selection.max_loss),
                        "target_profit": float(selection.target_profit),
                        "risk_reward_ratio": float(selection.risk_reward_ratio),
                        "entry_conditions": selection.entry_conditions,
                        "exit_conditions": selection.exit_conditions,
                        "trailing_stop_loss": selection.trailing_stop_loss,
                    }

                    # Prepare option contract JSON for database
                    import json
                    option_contract_json = json.dumps({
                        "option_instrument_key": contract.option_instrument_key,
                        "underlying_instrument_key": contract.underlying_instrument_key,
                        "option_type": contract.option_type,
                        "strike_price": float(contract.strike_price),
                        "expiry_date": contract.expiry_date,
                        "premium": float(contract.premium),
                        "lot_size": contract.lot_size,
                        "minimum_lot": contract.minimum_lot,
                        "freeze_quantity": contract.freeze_quantity,
                        "volume": contract.volume,
                        "open_interest": contract.open_interest,
                        "bid_price": float(contract.bid_price),
                        "ask_price": float(contract.ask_price),
                        "delta": float(contract.delta),
                        "gamma": float(contract.gamma),
                        "theta": float(contract.theta),
                        "vega": float(contract.vega),
                        "implied_volatility": float(contract.implied_volatility),
                        "selection_reason": contract.selection_reason,
                        "confidence_score": float(contract.confidence_score),
                        "risk_reward_ratio": float(contract.risk_reward_ratio),
                        "selected_at": contract.selected_at,
                        "valid_until": contract.valid_until,
                    })

                    # Prepare available expiry dates JSON
                    option_expiry_dates_json = json.dumps(selection.available_expiry_dates)

                    # Prepare complete option chain data (if available)
                    option_chain_data_json = json.dumps({
                        "atm_strike": float(selection.atm_strike),
                        "recommended_strike": float(selection.recommended_strike),
                        "available_expiries": selection.available_expiry_dates,
                        "selection_metadata": {
                            "capital_allocation": float(selection.capital_allocation),
                            "max_loss": float(selection.max_loss),
                            "target_profit": float(selection.target_profit),
                            "risk_reward_ratio": float(selection.risk_reward_ratio),
                            "entry_conditions": selection.entry_conditions,
                            "exit_conditions": selection.exit_conditions,
                            "trailing_stop_loss": selection.trailing_stop_loss,
                        }
                    })

                    # CHECK FOR EXISTING RECORD
                    existing_stock = db.query(SelectedStock).filter(
                        SelectedStock.symbol == selection.symbol,
                        SelectedStock.selection_date == today,
                        SelectedStock.is_active == True
                    ).first()

                    if existing_stock:
                        logger.info(f"Updating existing SelectedStock record for {selection.symbol}")
                        # Update existing record
                        existing_stock.option_type = contract.option_type
                        existing_stock.option_contract = option_contract_json
                        existing_stock.option_expiry_date = contract.expiry_date
                        existing_stock.option_expiry_dates = option_expiry_dates_json
                        existing_stock.option_chain_data = option_chain_data_json
                        existing_stock.score_breakdown = str(enhanced_metadata)
                        # Append selection reason to history
                        if "options" not in existing_stock.selection_reason:
                             existing_stock.selection_reason += f" | {contract.option_type} {contract.strike_price}"
                    else:
                        logger.info(f"Creating NEW SelectedStock record for {selection.symbol} (Fallback)")
                        # Create new record (fallback)
                        selected_stock = SelectedStock(
                            symbol=selection.symbol,
                            instrument_key=selection.instrument_key,
                            selection_date=today,
                            selection_score=float(selection.final_score),
                            selection_reason=f"{selection_type}_options_{contract.option_type}_{contract.strike_price}",
                            price_at_selection=float(selection.ltp),
                            volume_at_selection=int(selection.volume),
                            change_percent_at_selection=float(selection.change_percent),
                            sector=selection.sector,
                            score_breakdown=str(enhanced_metadata),
                            is_active=True,
                            option_type=contract.option_type,
                            option_contract=option_contract_json,
                            option_expiry_date=contract.expiry_date,
                            option_expiry_dates=option_expiry_dates_json,
                            option_chain_data=option_chain_data_json,
                        )
                        db.add(selected_stock)

                db.commit()
                logger.info(
                    f"Saved {len(selections)} enhanced options selections to database"
                )
                return True

            except Exception as e:
                db.rollback()
                logger.error(f"Database save error: {e}")
                return False
            finally:
                db.close()

        except ValueError as ve:
            logger.error(f"Validation error saving enhanced selections: {ve}")
            return False
        except Exception as e:
            logger.error(f"Error saving enhanced selections: {e}")
            return False

    def get_final_options_selections(self, db: Session = None) -> List[Dict[str, Any]]:
        """
        Get final options selections for trading from database

        Args:
            db: Database session

        Returns:
            List of selections with option contract details
        """
        try:
            if db is None:
                from database.connection import SessionLocal

                db = SessionLocal()
                should_close = True
            else:
                should_close = False

            try:
                from datetime import date
                import json

                # Query SelectedStock table for today's selections with options
                selected_stocks = (
                    db.query(SelectedStock)
                    .filter(
                        SelectedStock.selection_date == get_ist_now_naive().date(),
                        SelectedStock.is_active == True,
                        SelectedStock.option_contract.isnot(None),
                    )
                    .all()
                )

                selections = []
                for stock in selected_stocks:
                    # Parse option_contract JSON
                    option_data = {}
                    if stock.option_contract:
                        try:
                            option_data = json.loads(stock.option_contract)
                        except:
                            option_data = {}

                    # Parse score_breakdown JSON for capital details
                    score_data = {}
                    if stock.score_breakdown:
                        try:
                            score_data = json.loads(stock.score_breakdown)
                        except:
                            score_data = {}

                    selection = {
                        "id": stock.id,
                        "symbol": stock.symbol,
                        "instrument_key": stock.instrument_key,
                        "option_type": stock.option_type,
                        "option_instrument_key": option_data.get(
                            "option_instrument_key"
                        ),
                        "strike_price": option_data.get("strike_price", 0),
                        "expiry_date": stock.option_expiry_date,
                        "premium": option_data.get("premium", 0),
                        "lot_size": option_data.get("lot_size", 0),
                        "volume": option_data.get("volume", 0),
                        "open_interest": option_data.get("open_interest", 0),
                        "implied_volatility": option_data.get("implied_volatility", 0),
                        "delta": option_data.get("delta", 0),
                        "capital_allocation": score_data.get("capital_allocation", 0),
                        "max_loss": score_data.get("max_loss", 0),
                        "target_profit": score_data.get("target_profit", 0),
                        "position_size_lots": score_data.get("position_size_lots", 1),
                        "selection_score": stock.selection_score,
                        "sector": stock.sector,
                    }
                    selections.append(selection)

                logger.info(
                    f"Retrieved {len(selections)} final options selections from database"
                )
                return selections

            finally:
                if should_close:
                    db.close()

        except Exception as e:
            logger.error(f"Error getting final options selections: {e}")
            return []

    def get_options_trading_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive options trading summary

        Returns:
            Dictionary with trading summary and distributions
        """
        try:
            final_selections = self.final_options_selections

            if not final_selections:
                return {
                    "status": "no_selections",
                    "message": "No final options selections available",
                    "ready_for_trading": False,
                }

            total_capital = sum(s.capital_allocation for s in final_selections)
            total_max_loss = sum(s.max_loss for s in final_selections)
            total_target_profit = sum(s.target_profit for s in final_selections)

            summary = {
                "status": "ready",
                "total_selections": len(final_selections),
                "ready_for_trading": True,
                "capital_summary": {
                    "total_capital_required": float(total_capital),
                    "total_max_loss": float(total_max_loss),
                    "total_target_profit": float(total_target_profit),
                    "overall_risk_reward": (
                        float(total_target_profit / total_max_loss)
                        if total_max_loss > 0
                        else 0
                    ),
                },
                "selections_breakdown": [
                    {
                        "symbol": s.symbol,
                        "option_type": (
                            s.selected_option_contract.option_type
                            if s.selected_option_contract
                            else "N/A"
                        ),
                        "strike": (
                            float(s.selected_option_contract.strike_price)
                            if s.selected_option_contract
                            else 0
                        ),
                        "expiry": (
                            s.selected_option_contract.expiry_date
                            if s.selected_option_contract
                            else "N/A"
                        ),
                        "premium": (
                            float(s.selected_option_contract.premium)
                            if s.selected_option_contract
                            else 0
                        ),
                        "capital": float(s.capital_allocation),
                        "max_loss": float(s.max_loss),
                        "target_profit": float(s.target_profit),
                        "risk_reward": float(s.risk_reward_ratio),
                    }
                    for s in final_selections
                ],
                "expiry_distribution": {},
                "option_type_distribution": {},
                "sector_distribution": {},
                "timestamp": datetime.now().isoformat(),
            }

            # Calculate distributions
            expiry_counts = {}
            option_type_counts = {"CE": 0, "PE": 0}
            sector_counts = {}

            for selection in final_selections:
                if selection.selected_option_contract:
                    expiry = selection.selected_option_contract.expiry_date
                    expiry_counts[expiry] = expiry_counts.get(expiry, 0) + 1

                    option_type = selection.selected_option_contract.option_type
                    option_type_counts[option_type] = (
                        option_type_counts.get(option_type, 0) + 1
                    )

                sector = selection.sector
                sector_counts[sector] = sector_counts.get(sector, 0) + 1

            summary["expiry_distribution"] = expiry_counts
            summary["option_type_distribution"] = option_type_counts
            summary["sector_distribution"] = sector_counts

            return summary

        except Exception as e:
            logger.error(f"Error getting options trading summary: {e}")
            return {"status": "error", "error": str(e), "ready_for_trading": False}


# Create singleton instance
enhanced_options_service = EnhancedIntelligentOptionsService()
