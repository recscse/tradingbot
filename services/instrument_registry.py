# In services/instrument_registry.py
import asyncio
import traceback
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from services.instrument_refresh_service import get_trading_service

logger = logging.getLogger(__name__)


class InstrumentRegistry:
    """Centralized registry for instruments with live data"""

    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return

        # Main data structures
        self._spot_instruments = {}  # instrument_key -> metadata
        self._fno_instruments = {}  # instrument_key -> metadata
        self._symbols_map = {}  # symbol -> instrument_keys
        self._live_prices = {}  # instrument_key -> price data
        self._options_chain = {}  # symbol -> structured options data

        self._enriched_prices = {}
        self._symbol_metadata = {}
        self._sector_mapping = {}
        self._performance_cache = {}
        self._last_analytics_update = None

        # Initialize enhanced features
        self._initialize_enhanced_features()

        # State tracking
        self._initialized = False
        self._last_update = None

        logger.info("🏗️ Instrument Registry created")
        self._initialized = True

    async def initialize_registry(self):
        """Initialize the registry with data from instrument service"""
        async with self._lock:
            logger.info("🔄 Starting instrument registry initialization...")

            try:
                # FIXED: Import the correct functions
                from services.instrument_refresh_service import (
                    get_spot_only_instruments,
                    get_fno_instrument_keys,
                )

                # Get spot instruments
                spot_instruments = get_spot_only_instruments()
                logger.info(f"📊 Retrieved {len(spot_instruments)} spot instruments")

                # Process spot instruments
                spot_count = 0
                for instr in spot_instruments:
                    try:
                        key = instr["instrument_key"]
                        self._spot_instruments[key] = instr

                        # Map symbol to instrument keys
                        symbol = instr["symbol"]
                        if symbol not in self._symbols_map:
                            self._symbols_map[symbol] = {
                                "spot": [],
                                "futures": [],
                                "calls": [],
                                "puts": [],
                            }

                        self._symbols_map[symbol]["spot"].append(key)
                        spot_count += 1
                    except Exception as e:
                        logger.error(
                            f"❌ Error processing spot instrument: {e}, Data: {instr}"
                        )

                logger.info(f"📊 Processed {spot_count} spot instruments")

                # Build F&O registry manually
                logger.info("📊 Building F&O registry...")
                fno_registry = {"stocks": {}}

                # Get F&O instruments for key symbols
                fno_symbols = [
                    "NIFTY",
                    "BANKNIFTY",
                    "RELIANCE",
                    "INFY",
                    "TCS",
                    "HDFCBANK",
                    "ICICIBANK",
                ]

                for symbol in fno_symbols:
                    try:
                        # FIXED: Use the correct function name
                        stock_data = get_fno_instrument_keys(symbol)
                        if stock_data and "error" not in stock_data:
                            fno_registry["stocks"][symbol] = stock_data
                            logger.info(f"✅ Successfully loaded F&O data for {symbol}")
                        else:
                            logger.warning(f"⚠️ No F&O data found for {symbol}")
                    except Exception as e:
                        logger.error(f"❌ Error getting F&O data for {symbol}: {e}")

                logger.info(
                    f"📊 F&O registry contains {len(fno_registry['stocks'])} stock entries"
                )

                # Process F&O instruments
                fno_count = 0
                for symbol, stock_data in fno_registry["stocks"].items():
                    try:
                        # Process spot
                        for instr in stock_data.get("spot", []):
                            key = instr["instrument_key"]
                            self._fno_instruments[key] = {
                                **instr,
                                "symbol": symbol,
                                "type": "SPOT",
                            }

                            if symbol not in self._symbols_map:
                                self._symbols_map[symbol] = {
                                    "spot": [],
                                    "futures": [],
                                    "calls": [],
                                    "puts": [],
                                }

                            self._symbols_map[symbol]["spot"].append(key)
                            fno_count += 1

                        # Process futures
                        for instr in stock_data.get("futures", []):
                            key = instr["instrument_key"]
                            self._fno_instruments[key] = {
                                **instr,
                                "symbol": symbol,
                                "type": "FUTURE",
                            }
                            self._symbols_map[symbol]["futures"].append(key)
                            fno_count += 1

                        # Process call options
                        for instr in stock_data.get("call_options", []):
                            key = instr["instrument_key"]
                            self._fno_instruments[key] = {
                                **instr,
                                "symbol": symbol,
                                "type": "CALL",
                            }
                            self._symbols_map[symbol]["calls"].append(key)
                            fno_count += 1

                        # Process put options
                        for instr in stock_data.get("put_options", []):
                            key = instr["instrument_key"]
                            self._fno_instruments[key] = {
                                **instr,
                                "symbol": symbol,
                                "type": "PUT",
                            }
                            self._symbols_map[symbol]["puts"].append(key)
                            fno_count += 1

                        # Build options chain structure
                        self._build_options_chain(symbol, stock_data)
                    except Exception as e:
                        logger.error(f"❌ Error processing F&O data for {symbol}: {e}")

                logger.info(f"📊 Processed {fno_count} F&O instruments")

                self._last_update = datetime.now()

                total_instruments = len(self._spot_instruments) + len(
                    self._fno_instruments
                )

                # Log detailed registry stats
                registry_stats = {
                    "spot_instruments": len(self._spot_instruments),
                    "fno_instruments": len(self._fno_instruments),
                    "symbols": len(self._symbols_map),
                    "options_chains": len(self._options_chain),
                }

                logger.info(
                    f"📊 Registry initialization complete. Stats: {registry_stats}"
                )

                if total_instruments == 0:
                    logger.error("❌ No instruments loaded into registry!")
                else:
                    logger.info(
                        f"✅ Instrument Registry initialized with {total_instruments} instruments"
                    )

                return True

            except Exception as e:
                logger.error(f"❌ Error initializing instrument registry: {e}")
                import traceback

                logger.error(f"❌ Traceback: {traceback.format_exc()}")
                return False

    def _initialize_enhanced_features(self):
        """Initialize enhanced registry features"""
        try:
            # Load sector mapping
            from services.sector_mapping import SYMBOL_TO_SECTOR

            self._sector_mapping = SYMBOL_TO_SECTOR

            # Build symbol metadata cache
            if hasattr(self, "_stock_mappings"):
                for symbol, mapping in self._stock_mappings.items():
                    self._symbol_metadata[symbol] = {
                        "name": mapping.get("name", symbol),
                        "exchange": mapping.get("exchange", "NSE"),
                        "sector": self._sector_mapping.get(symbol, "OTHER"),
                        "trading_symbol": symbol,
                        "has_derivatives": mapping.get("has_futures", False)
                        or mapping.get("has_options", False),
                    }

            logger.info(
                f"📊 Enhanced registry initialized with {len(self._symbol_metadata)} symbols"
            )

        except Exception as e:
            logger.error(f"Error initializing enhanced features: {e}")

    def _build_options_chain(self, symbol: str, stock_data: Dict[str, Any]):
        """Build structured options chain for a symbol"""
        calls = stock_data.get("call_options", [])
        puts = stock_data.get("put_options", [])

        # Group by expiry
        expirations = {}

        # Process calls
        for call in calls:
            expiry = call.get("expiry", "")
            if expiry not in expirations:
                expirations[expiry] = {"calls": {}, "puts": {}}

            strike = call.get("strike_price", 0)
            expirations[expiry]["calls"][strike] = call

        # Process puts
        for put in puts:
            expiry = put.get("expiry", "")
            if expiry not in expirations:
                expirations[expiry] = {"calls": {}, "puts": {}}

            strike = put.get("strike_price", 0)
            expirations[expiry]["puts"][strike] = put

        # Build final structure
        chain = {
            "symbol": symbol,
            "expirations": {},
            "strikes": set(),
            "updated_at": datetime.now().isoformat(),
        }

        for expiry, data in expirations.items():
            all_strikes = sorted(
                set(list(data["calls"].keys()) + list(data["puts"].keys()))
            )
            chain["strikes"].update(all_strikes)

            # Build ordered strikes data
            strikes_data = []
            for strike in all_strikes:
                call_data = data["calls"].get(strike)
                put_data = data["puts"].get(strike)

                strike_row = {"strike": strike, "call": call_data, "put": put_data}
                strikes_data.append(strike_row)

            # Store in chain
            chain["expirations"][expiry] = {
                "expiry": expiry,
                "strikes": all_strikes,
                "data": strikes_data,
            }

        # Sort strikes
        chain["strikes"] = sorted(chain["strikes"])

        # Store chain
        self._options_chain[symbol] = chain

    def update_live_prices(self, data: Dict[str, Any]) -> Dict[str, int]:
        """COMPLETE: Update with full enrichment and analytics"""
        start_time = datetime.now()
        stats = {"updated": 0, "new": 0, "ignored": 0, "enriched": 0, "errors": 0}

        for instrument_key, price_data in data.items():
            try:
                # Validate data quality
                if not self._validate_price_data(price_data):
                    stats["ignored"] += 1
                    continue

                # Extract symbol from enriched data
                symbol = price_data.get("symbol")
                if not symbol:
                    stats["ignored"] += 1
                    continue

                # Create complete enriched entry
                enriched_entry = self._create_complete_entry(
                    instrument_key, symbol, price_data
                )

                # Update storage
                if instrument_key in self._live_prices:
                    self._live_prices[instrument_key].update(enriched_entry)
                    stats["updated"] += 1
                else:
                    self._live_prices[instrument_key] = enriched_entry
                    stats["new"] += 1

                # Store in enriched cache
                self._enriched_prices[instrument_key] = enriched_entry
                stats["enriched"] += 1

                # Update performance cache
                self._update_performance_cache(symbol, enriched_entry)

            except Exception as e:
                stats["errors"] += 1
                logger.warning(f"Error processing {instrument_key}: {e}")

        # Update timestamps
        if stats["updated"] > 0 or stats["new"] > 0:
            self._last_update = datetime.now()
            self._last_analytics_update = datetime.now()

        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        if stats["enriched"] > 0:
            logger.info(
                f"📊 Registry update: {stats['enriched']} enriched in {processing_time:.2f}ms"
            )

        return stats

    def _validate_price_data(self, data: dict) -> bool:
        """Comprehensive data validation"""
        if not isinstance(data, dict):
            return False

        # Must have LTP
        ltp = data.get("ltp")
        if ltp is None or ltp <= 0:
            return False

        # Must have symbol
        if not data.get("symbol"):
            return False

        return True

    def _create_complete_entry(
        self, instrument_key: str, symbol: str, price_data: dict
    ) -> dict:
        """Create complete enriched entry"""
        metadata = self._symbol_metadata.get(symbol, {})

        # Base enriched entry
        entry = {
            # Identifiers
            "instrument_key": instrument_key,
            "symbol": symbol,
            "name": metadata.get("name", symbol),
            "trading_symbol": metadata.get("trading_symbol", symbol),
            "exchange": metadata.get("exchange", "NSE"),
            "sector": metadata.get("sector", "OTHER"),
            "instrument_type": price_data.get("instrument_type", "EQ"),
            # Core price data
            "ltp": price_data.get("ltp"),
            "cp": price_data.get("cp"),
            "change": price_data.get("change"),
            "change_percent": price_data.get("change_percent"),
            # OHLC data
            "open": price_data.get("open"),
            "high": price_data.get("high"),
            "low": price_data.get("low"),
            "close": price_data.get("close"),
            # Volume data
            "volume": price_data.get("volume", 0),
            "ltq": price_data.get("ltq", 0),
            "daily_volume": price_data.get("daily_volume"),
            # Advanced data
            "avg_trade_price": price_data.get("avg_trade_price"),
            "bid_price": price_data.get("bid_price"),
            "ask_price": price_data.get("ask_price"),
            "bid_qty": price_data.get("bid_qty"),
            "ask_qty": price_data.get("ask_qty"),
            # Options data (if applicable)
            "option_greeks": price_data.get("option_greeks"),
            "open_interest": price_data.get("open_interest"),
            # Computed indicators
            "trend": price_data.get("trend", "neutral"),
            "volatility": price_data.get("volatility", "normal"),
            # Metadata
            "timestamp": price_data.get("timestamp"),
            "last_updated": datetime.now().isoformat(),
            "data_source": price_data.get("data_source", "live"),
            "has_derivatives": metadata.get("has_derivatives", False),
            # Performance metrics
            "update_count": self._live_prices.get(instrument_key, {}).get(
                "update_count", 0
            )
            + 1,
        }

        return entry

    def _update_performance_cache(self, symbol: str, entry: dict):
        """Update performance tracking cache"""
        if symbol not in self._performance_cache:
            self._performance_cache[symbol] = {
                "max_price": entry["ltp"],
                "min_price": entry["ltp"],
                "max_volume": entry.get("volume", 0),
                "first_seen": datetime.now().isoformat(),
                "price_updates": 0,
            }

        cache = self._performance_cache[symbol]
        cache["max_price"] = max(cache["max_price"], entry["ltp"])
        cache["min_price"] = min(cache["min_price"], entry["ltp"])
        cache["max_volume"] = max(cache["max_volume"], entry.get("volume", 0))
        cache["price_updates"] += 1
        cache["last_update"] = datetime.now().isoformat()

    # COMPLETE PUBLIC API
    def get_enriched_prices(self) -> Dict[str, Dict[str, Any]]:
        """Get all enriched price data"""
        return self._enriched_prices.copy()

    def get_enriched_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get enriched price for specific symbol"""
        symbol = symbol.upper()
        for key, data in self._enriched_prices.items():
            if data.get("symbol") == symbol:
                return data
        return None

    def get_stocks_by_sector(
        self, sector: str = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group stocks by sector with optional filtering"""
        sectors = {}

        for key, data in self._enriched_prices.items():
            stock_sector = data.get("sector", "OTHER")

            # Filter by sector if specified
            if sector and stock_sector != sector.upper():
                continue

            if stock_sector not in sectors:
                sectors[stock_sector] = []

            sectors[stock_sector].append(data)

        # Sort each sector by performance
        for sector_name, stocks in sectors.items():
            stocks.sort(key=lambda x: x.get("change_percent", 0), reverse=True)

        return sectors

    def get_market_summary(self) -> Dict[str, Any]:
        """Comprehensive market summary"""
        all_stocks = list(self._enriched_prices.values())

        if not all_stocks:
            return {
                "error": "No market data available",
                "timestamp": datetime.now().isoformat(),
            }

        # Basic market breadth
        advancing = len([s for s in all_stocks if (s.get("change_percent") or 0) > 0])
        declining = len([s for s in all_stocks if (s.get("change_percent") or 0) < 0])
        unchanged = len(all_stocks) - advancing - declining

        # Volume analysis
        total_volume = sum(s.get("volume", 0) for s in all_stocks)
        avg_volume = total_volume / len(all_stocks) if all_stocks else 0

        # Sector performance
        sector_performance = {}
        sector_data = self.get_stocks_by_sector()

        for sector, stocks in sector_data.items():
            if stocks:
                avg_change = sum(s.get("change_percent", 0) for s in stocks) / len(
                    stocks
                )
                sector_performance[sector] = {
                    "count": len(stocks),
                    "avg_change_percent": round(avg_change, 2),
                    "advancing": len(
                        [s for s in stocks if (s.get("change_percent") or 0) > 0]
                    ),
                    "declining": len(
                        [s for s in stocks if (s.get("change_percent") or 0) < 0]
                    ),
                }

        # Top performers
        sorted_stocks = sorted(
            all_stocks, key=lambda x: x.get("change_percent", 0), reverse=True
        )

        return {
            "total_stocks": len(all_stocks),
            "advancing": advancing,
            "declining": declining,
            "unchanged": unchanged,
            "advance_decline_ratio": (
                round(advancing / declining, 2) if declining > 0 else float("inf")
            ),
            "market_breadth_percent": round(
                (advancing - declining) / len(all_stocks) * 100, 2
            ),
            "volume_stats": {
                "total_volume": total_volume,
                "average_volume": round(avg_volume, 0),
                "high_volume_stocks": len(
                    [s for s in all_stocks if s.get("volume", 0) > avg_volume * 2]
                ),
            },
            "sector_performance": sector_performance,
            "total_sectors": len(sector_performance),
            "top_performers": {
                "top_gainer": sorted_stocks[0] if sorted_stocks else None,
                "top_loser": sorted_stocks[-1] if sorted_stocks else None,
            },
            "market_indicators": {
                "high_volatility_stocks": len(
                    [s for s in all_stocks if s.get("volatility") == "high"]
                ),
                "strong_trends": len(
                    [
                        s
                        for s in all_stocks
                        if s.get("trend") in ["strong_bullish", "strong_bearish"]
                    ]
                ),
            },
            "timestamp": datetime.now().isoformat(),
            "last_update": self._last_update.isoformat() if self._last_update else None,
        }

    def get_spot_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get spot price for a symbol with enhanced error handling and consistent data access"""
        try:
            symbol = symbol.upper()

            if symbol not in self._symbols_map:
                # Try to find a similar symbol (for backward compatibility)
                similar_symbols = [s for s in self._symbols_map.keys() if symbol in s]
                if similar_symbols:
                    symbol = similar_symbols[0]
                    logger.info(f"🔍 Using similar symbol: {symbol}")
                else:
                    return None

            spot_keys = self._symbols_map[symbol]["spot"]
            if not spot_keys:
                return None

            # Get first spot key
            key = spot_keys[0]

            # Get instrument data with consistent access pattern
            instrument = None
            if key in self._spot_instruments:
                instrument = self._spot_instruments[key]
            elif key in self._fno_instruments:
                instrument = self._fno_instruments[key]

            if not instrument:
                return None

            # Get price data
            price_data = self._live_prices.get(key, {})

            # If no live price data, see if we can find any with the symbol
            if not price_data or price_data.get("ltp") is None:
                for spot_key in spot_keys:
                    if (
                        spot_key in self._live_prices
                        and self._live_prices[spot_key].get("ltp") is not None
                    ):
                        key = spot_key
                        price_data = self._live_prices[key]
                        break

            # Create the response with consistent data access
            response = {
                "symbol": symbol,
                "instrument_key": key,
                "trading_symbol": self._get_value(instrument, "trading_symbol", symbol),
                "exchange": self._get_value(instrument, "exchange", "NSE"),
                "last_price": price_data.get("ltp"),
                "change": price_data.get("change"),
                "change_percent": price_data.get("change_percent"),
                "volume": price_data.get("volume"),
                "high": price_data.get("high"),
                "low": price_data.get("low"),
                "open": price_data.get("open"),
                "close": price_data.get("close"),
                "last_updated": price_data.get("timestamp"),
            }

            # Add timestamp if missing
            if response["last_updated"] is None:
                response["last_updated"] = datetime.now().isoformat()

            return response

        except Exception as e:
            logger.error(f"❌ Error getting spot price for {symbol}: {e}")
            return None

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get structured data for dashboard with improved error handling"""
        try:
            # Get index data
            indices = []
            for symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "MIDCPNIFTY"]:
                index_data = self.get_spot_price(symbol)
                if index_data:
                    indices.append(index_data)

            # Get top stocks data
            top_stocks = []
            for symbol in self._symbols_map:
                # Skip indices
                if symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "MIDCPNIFTY"]:
                    continue

                stock_data = self.get_spot_price(symbol)
                if stock_data and stock_data.get("last_price") is not None:
                    top_stocks.append(stock_data)

            # Sort by volume (if available) or by price change
            top_stocks.sort(
                key=lambda x: (
                    x.get("volume", 0) or 0,
                    abs(x.get("change_percent", 0) or 0),
                ),
                reverse=True,
            )

            # Log what we're returning
            logger.info(
                f"📊 Dashboard data: {len(indices)} indices, {len(top_stocks)} top stocks"
            )

            return {
                "indices": indices,
                "top_stocks": top_stocks[:200],  # Top 50 by volume
                "total_stocks": len(top_stocks),
                "updated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"❌ Error getting dashboard data: {e}")
            # Return minimal data to avoid UI errors
            return {
                "indices": [],
                "top_stocks": [],
                "total_stocks": 0,
                "updated_at": datetime.now().isoformat(),
                "error": str(e),
            }

    def get_options_chain(self, symbol: str, expiry: str = None) -> Dict[str, Any]:
        """Get options chain for a symbol with live prices and visualization enhancements"""
        # Get base chain
        chain = self._options_chain.get(symbol)
        if not chain:
            return {"error": f"No options chain found for {symbol}"}

        # Get spot price for ATM identification
        spot_data = self.get_spot_price(symbol)
        spot_price = spot_data.get("last_price") if spot_data else None

        # Prepare visualization-friendly format
        visualization_data = {
            "symbol": symbol,
            "spot_price": spot_price,
            "expirations": [],
            "selected_expiry": None,
            "strikes": [],
            "call_data": [],
            "put_data": [],
            "atm_index": None,
            "updated_at": datetime.now().isoformat(),
        }

        # List all available expirations
        available_expirations = list(chain.get("expirations", {}).keys())
        visualization_data["expirations"] = sorted(available_expirations)

        # If no expiry specified, use the nearest one
        if not expiry and available_expirations:
            # Sort by date
            sorted_expiries = sorted(available_expirations)
            expiry = sorted_expiries[0]

        # Check if expiry exists
        if expiry not in available_expirations:
            return {
                "error": f"Expiry {expiry} not found",
                "available_expirations": visualization_data["expirations"],
            }

        visualization_data["selected_expiry"] = expiry

        # Get data for selected expiry
        expiry_data = chain["expirations"].get(expiry, {})
        strike_rows = expiry_data.get("data", [])

        # Extract strikes and option data
        for i, row in enumerate(strike_rows):
            strike = row.get("strike")
            visualization_data["strikes"].append(strike)

            # Extract call data
            call = row.get("call", {})
            if call:
                # Get live price data if available
                call_key = call.get("instrument_key")
                call_price_data = (
                    self._live_prices.get(call_key, {}) if call_key else {}
                )

                call_data = {
                    "strike": strike,
                    "instrument_key": call.get("instrument_key"),
                    "trading_symbol": call.get("trading_symbol"),
                    "expiry": call.get("expiry"),
                    "ltp": call.get("ltp") or call_price_data.get("ltp"),
                    "change": call.get("change") or call_price_data.get("change"),
                    "change_percent": call.get("change_percent")
                    or call_price_data.get("change_percent"),
                    "volume": call.get("volume") or call_price_data.get("volume"),
                    "oi": call.get("oi") or call_price_data.get("oi"),
                }
                visualization_data["call_data"].append(call_data)
            else:
                # Add placeholder to maintain strike alignment
                visualization_data["call_data"].append({"strike": strike})

            # Extract put data
            put = row.get("put", {})
            if put:
                # Get live price data if available
                put_key = put.get("instrument_key")
                put_price_data = self._live_prices.get(put_key, {}) if put_key else {}

                put_data = {
                    "strike": strike,
                    "instrument_key": put.get("instrument_key"),
                    "trading_symbol": put.get("trading_symbol"),
                    "expiry": put.get("expiry"),
                    "ltp": put.get("ltp") or put_price_data.get("ltp"),
                    "change": put.get("change") or put_price_data.get("change"),
                    "change_percent": put.get("change_percent")
                    or put_price_data.get("change_percent"),
                    "volume": put.get("volume") or put_price_data.get("volume"),
                    "oi": put.get("oi") or put_price_data.get("oi"),
                }
                visualization_data["put_data"].append(put_data)
            else:
                # Add placeholder to maintain strike alignment
                visualization_data["put_data"].append({"strike": strike})

            # Identify ATM strike index if this is exactly the spot price
            if spot_price and abs(strike - spot_price) < 0.01:
                visualization_data["atm_index"] = i

        # If ATM index wasn't set by exact match, find closest strike
        if (
            spot_price
            and visualization_data["atm_index"] is None
            and visualization_data["strikes"]
        ):
            visualization_data["atm_index"] = min(
                range(len(visualization_data["strikes"])),
                key=lambda i: abs(visualization_data["strikes"][i] - spot_price),
            )

        # Add analytics
        visualization_data["analytics"] = self._calculate_options_analytics(
            visualization_data, spot_price
        )

        return visualization_data

    def _calculate_options_analytics(
        self, chain_data: Dict[str, Any], spot_price: float = None
    ) -> Dict[str, Any]:
        """Calculate additional analytics for options chain visualization"""
        analytics = {
            "pcr_volume": None,
            "pcr_oi": None,
            "max_pain": None,
            "highest_oi_call": None,
            "highest_oi_put": None,
        }

        # Calculate Put-Call Ratio by volume
        total_call_volume = sum(
            call.get("volume", 0) or 0 for call in chain_data.get("call_data", [])
        )
        total_put_volume = sum(
            put.get("volume", 0) or 0 for put in chain_data.get("put_data", [])
        )

        if total_call_volume and total_call_volume > 0:
            analytics["pcr_volume"] = round(total_put_volume / total_call_volume, 2)

        # Calculate Put-Call Ratio by open interest
        total_call_oi = sum(
            call.get("oi", 0) or 0 for call in chain_data.get("call_data", [])
        )
        total_put_oi = sum(
            put.get("oi", 0) or 0 for put in chain_data.get("put_data", [])
        )

        if total_call_oi and total_call_oi > 0:
            analytics["pcr_oi"] = round(total_put_oi / total_call_oi, 2)

        # Find highest OI strikes
        if chain_data.get("call_data"):
            max_call_oi = 0
            max_call_strike = None

            for call in chain_data["call_data"]:
                oi = call.get("oi", 0) or 0
                if oi > max_call_oi:
                    max_call_oi = oi
                    max_call_strike = call.get("strike")

            if max_call_strike:
                analytics["highest_oi_call"] = {
                    "strike": max_call_strike,
                    "oi": max_call_oi,
                }

        if chain_data.get("put_data"):
            max_put_oi = 0
            max_put_strike = None

            for put in chain_data["put_data"]:
                oi = put.get("oi", 0) or 0
                if oi > max_put_oi:
                    max_put_oi = oi
                    max_put_strike = put.get("strike")

            if max_put_strike:
                analytics["highest_oi_put"] = {
                    "strike": max_put_strike,
                    "oi": max_put_oi,
                }

        # Calculate max pain (strike with minimum option writer loss)
        if (
            chain_data.get("strikes")
            and chain_data.get("call_data")
            and chain_data.get("put_data")
        ):
            min_pain = float("inf")
            max_pain_strike = None

            for strike in chain_data["strikes"]:
                # Calculate total loss for option writers at this strike
                total_loss = 0

                # Call losses
                for call in chain_data["call_data"]:
                    call_strike = call.get("strike")
                    call_oi = call.get("oi", 0) or 0

                    if call_strike and call_strike < strike:
                        # In-the-money calls cause loss to writers
                        total_loss += (strike - call_strike) * call_oi

                # Put losses
                for put in chain_data["put_data"]:
                    put_strike = put.get("strike")
                    put_oi = put.get("oi", 0) or 0

                    if put_strike and put_strike > strike:
                        # In-the-money puts cause loss to writers
                        total_loss += (put_strike - strike) * put_oi

                # Update max pain if this strike has less pain
                if total_loss < min_pain:
                    min_pain = total_loss
                    max_pain_strike = strike

            analytics["max_pain"] = max_pain_strike

        return analytics

    def _update_chain_with_prices(self, chain: Dict[str, Any]) -> Dict[str, Any]:
        """Update options chain with live prices - robust implementation"""
        updated_chain = {**chain, "updated_at": datetime.now().isoformat()}
        update_count = 0
        error_count = 0

        try:
            # Keep track of which expiries and strikes have prices
            updated_chain["price_coverage"] = {
                "total_options": 0,
                "options_with_prices": 0,
                "coverage_percent": 0.0,
            }

            total_options = 0
            options_with_prices = 0

            # Ensure expirations exists
            if "expirations" not in updated_chain:
                logger.warning("⚠️ No expirations in options chain")
                updated_chain["error"] = "No expirations in options chain"
                return updated_chain

            for expiry, exp_data in chain["expirations"].items():
                # Validate expiry data structure
                if not isinstance(exp_data, dict) or "data" not in exp_data:
                    logger.warning(f"⚠️ Invalid expiry data structure for {expiry}")
                    continue

                # Ensure the expiry exists in the updated chain
                if expiry not in updated_chain["expirations"]:
                    updated_chain["expirations"][expiry] = exp_data.copy()

                for i, strike_row in enumerate(exp_data["data"]):
                    try:
                        # Validate strike_row
                        if not isinstance(strike_row, dict):
                            continue

                        # Ensure data array is large enough
                        if i >= len(updated_chain["expirations"][expiry]["data"]):
                            # This should not happen if chains are identical
                            logger.warning(
                                f"⚠️ Strike row index {i} out of range for {expiry}"
                            )
                            continue

                        # Update call price if available
                        if "call" in strike_row and isinstance(
                            strike_row["call"], dict
                        ):
                            total_options += 1
                            call_key = strike_row["call"].get("instrument_key")

                            if call_key and call_key in self._live_prices:
                                call_price = self._live_prices[call_key]

                                # Ensure call exists in the updated chain
                                if (
                                    "call"
                                    not in updated_chain["expirations"][expiry]["data"][
                                        i
                                    ]
                                ):
                                    updated_chain["expirations"][expiry]["data"][i][
                                        "call"
                                    ] = strike_row["call"].copy()

                                # Copy price data to options chain - only non-None values
                                for field in [
                                    "ltp",
                                    "change",
                                    "change_percent",
                                    "oi",
                                    "volume",
                                    "ltq",
                                ]:
                                    if call_price.get(field) is not None:
                                        updated_chain["expirations"][expiry]["data"][i][
                                            "call"
                                        ][field] = call_price[field]

                                # Mark last update time
                                updated_chain["expirations"][expiry]["data"][i]["call"][
                                    "last_updated"
                                ] = call_price.get(
                                    "last_updated", datetime.now().isoformat()
                                )

                                options_with_prices += 1
                                update_count += 1

                        # Update put price if available
                        if "put" in strike_row and isinstance(strike_row["put"], dict):
                            total_options += 1
                            put_key = strike_row["put"].get("instrument_key")

                            if put_key and put_key in self._live_prices:
                                put_price = self._live_prices[put_key]

                                # Ensure put exists in the updated chain
                                if (
                                    "put"
                                    not in updated_chain["expirations"][expiry]["data"][
                                        i
                                    ]
                                ):
                                    updated_chain["expirations"][expiry]["data"][i][
                                        "put"
                                    ] = strike_row["put"].copy()

                                # Copy price data to options chain - only non-None values
                                for field in [
                                    "ltp",
                                    "change",
                                    "change_percent",
                                    "oi",
                                    "volume",
                                    "ltq",
                                ]:
                                    if put_price.get(field) is not None:
                                        updated_chain["expirations"][expiry]["data"][i][
                                            "put"
                                        ][field] = put_price[field]

                                # Mark last update time
                                updated_chain["expirations"][expiry]["data"][i]["put"][
                                    "last_updated"
                                ] = put_price.get(
                                    "last_updated", datetime.now().isoformat()
                                )

                                options_with_prices += 1
                                update_count += 1

                    except Exception as e:
                        error_count += 1
                        logger.warning(
                            f"⚠️ Error updating options chain at strike {strike_row.get('strike')}: {e}"
                        )

            # Update coverage stats
            updated_chain["price_coverage"]["total_options"] = total_options
            updated_chain["price_coverage"]["options_with_prices"] = options_with_prices

            if total_options > 0:
                updated_chain["price_coverage"]["coverage_percent"] = (
                    options_with_prices / total_options
                ) * 100

            # Add update metadata
            updated_chain["update_stats"] = {
                "updates": update_count,
                "errors": error_count,
                "timestamp": datetime.now().isoformat(),
            }

            logger.info(
                f"📊 Updated options chain for {chain.get('symbol')} with "
                f"{options_with_prices}/{total_options} prices "
                f"({updated_chain['price_coverage'].get('coverage_percent', 0):.1f}% coverage)"
            )

        except Exception as e:
            logger.error(f"❌ Error updating options chain: {e}")
            updated_chain["error"] = str(e)

        return updated_chain

    def get_instrument_keys_for_dashboard(self) -> List[str]:
        """Get instrument keys for dashboard WebSocket subscription"""
        # Get all spot keys
        keys = list(self._spot_instruments.keys())

        # Sort by priority (indices first)
        index_keys = [k for k in keys if "INDEX" in k]
        eq_keys = [k for k in keys if "EQ" in k]

        return index_keys + eq_keys

    def get_instrument_keys_for_trading(self, symbol: str) -> List[str]:
        """Get instrument keys for trading a specific symbol"""
        if symbol not in self._symbols_map:
            return []

        symbol_map = self._symbols_map[symbol]

        # Collect all keys for this symbol
        keys = []
        keys.extend(symbol_map["spot"])
        keys.extend(symbol_map["futures"])
        keys.extend(symbol_map["calls"])
        keys.extend(symbol_map["puts"])

        return keys

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        return {
            "spot_instruments": len(self._spot_instruments),
            "fno_instruments": len(self._fno_instruments),
            "symbols": len(self._symbols_map),
            "live_prices": len(self._live_prices),
            "options_chains": len(self._options_chain),
            "last_update": self._last_update.isoformat() if self._last_update else None,
        }

    def mark_stock_as_selected(self, symbol: str) -> bool:
        """Mark a stock as selected for trading"""
        symbol = symbol.upper()
        if symbol in self._symbols_map:
            if not hasattr(self, "_selected_stocks"):
                self._selected_stocks = set()
            self._selected_stocks.add(symbol)
            return True
        return False

    def clear_selected_stocks(self) -> None:
        """Clear all selected stocks"""
        if hasattr(self, "_selected_stocks"):
            self._selected_stocks.clear()

    def get_selected_stocks(self) -> List[str]:
        """Get list of selected stocks"""
        if hasattr(self, "_selected_stocks"):
            return list(self._selected_stocks)
        return []

    def is_stock_selected(self, symbol: str) -> bool:
        """Check if a stock is selected for trading"""
        if hasattr(self, "_selected_stocks"):
            return symbol.upper() in self._selected_stocks
        return False

    def debug_live_prices(self, limit: int = 10) -> Dict[str, Any]:
        """Debug method to check live prices"""
        sample_prices = {}
        count = 0

        for key, data in self._live_prices.items():
            if count < limit:
                sample_prices[key] = data
                count += 1

        return {
            "total_prices": len(self._live_prices),
            "last_update": self._last_update.isoformat() if self._last_update else None,
            "sample_prices": sample_prices,
        }

    def _get_value(self, data, key, default=None):
        """Helper method for consistent data access from either dictionary or object"""
        if data is None:
            return default

        # Handle dictionary access
        if hasattr(data, "get"):
            return data.get(key, default)

        # Handle object access
        return getattr(data, key, default)

    def validate_price_mapping(self, sample_size: int = 50) -> Dict[str, Any]:
        """Validate price mapping correctness with detailed reporting"""
        validation_results = {
            "total_instruments": len(self._spot_instruments)
            + len(self._fno_instruments),
            "instruments_with_prices": len(self._live_prices),
            "coverage_percent": 0.0,
            "sample_validations": [],
            "errors": [],
            "timestamp": datetime.now().isoformat(),
        }

        # Calculate coverage
        if validation_results["total_instruments"] > 0:
            validation_results["coverage_percent"] = (
                validation_results["instruments_with_prices"]
                / validation_results["total_instruments"]
                * 100
            )

        # Take a sample of instruments to validate
        all_instruments = list(self._spot_instruments.keys()) + list(
            self._fno_instruments.keys()
        )
        sample_size = min(sample_size, len(all_instruments))

        if sample_size > 0:
            # Use both random sampling and prioritize instruments we know should have prices
            priority_symbols = [
                "NIFTY",
                "BANKNIFTY",
                "RELIANCE",
                "INFY",
                "TCS",
                "HDFCBANK",
            ]
            priority_keys = []

            # Find instrument keys for priority symbols
            for symbol in priority_symbols:
                if symbol in self._symbols_map:
                    symbol_keys = []
                    for key_type in ["spot", "futures", "calls", "puts"]:
                        symbol_keys.extend(self._symbols_map[symbol][key_type])

                    if symbol_keys:
                        priority_keys.append(
                            symbol_keys[0]
                        )  # Take first key of each symbol

            # Select remaining keys randomly
            remaining_size = sample_size - len(priority_keys)
            if remaining_size > 0:
                import random

                random_keys = random.sample(
                    all_instruments, min(remaining_size, len(all_instruments))
                )
                sample_keys = priority_keys + random_keys
            else:
                sample_keys = priority_keys[:sample_size]

            # Validate each key in the sample
            for key in sample_keys:
                validation_entry = {
                    "instrument_key": key,
                    "has_price": key in self._live_prices,
                    "price": None,
                    "timestamp": None,
                    "data_format": None,
                    "update_count": None,
                    "in_registry": False,
                }

                # Get instrument details
                if key in self._spot_instruments:
                    validation_entry["in_registry"] = True
                    validation_entry["instrument_type"] = "spot"
                    validation_entry["symbol"] = self._get_value(
                        self._spot_instruments[key], "symbol"
                    )
                    validation_entry["exchange"] = self._get_value(
                        self._spot_instruments[key], "exchange"
                    )
                elif key in self._fno_instruments:
                    validation_entry["in_registry"] = True
                    validation_entry["instrument_type"] = "fno"
                    validation_entry["symbol"] = self._get_value(
                        self._fno_instruments[key], "symbol"
                    )
                    validation_entry["type"] = self._get_value(
                        self._fno_instruments[key], "type"
                    )

                # Get price details if available
                if key in self._live_prices:
                    price_data = self._live_prices[key]
                    validation_entry["price"] = price_data.get("ltp")
                    validation_entry["timestamp"] = price_data.get("timestamp")
                    validation_entry["data_format"] = price_data.get("data_format")
                    validation_entry["update_count"] = price_data.get("update_count")

                    # Validation check - does price make sense?
                    if validation_entry["price"] is not None:
                        if (
                            validation_entry["price"] <= 0
                            or validation_entry["price"] > 1000000
                        ):
                            validation_entry["price_suspicious"] = True
                            validation_results["errors"].append(
                                f"Suspicious price for {key}: {validation_entry['price']}"
                            )

                validation_results["sample_validations"].append(validation_entry)

        # Summarize results
        prices_found = sum(
            1 for v in validation_results["sample_validations"] if v["has_price"]
        )
        validation_results["sample_coverage_percent"] = (
            (prices_found / sample_size) * 100 if sample_size > 0 else 0
        )

        # Log validation results
        logger.info(
            f"🔍 Price mapping validation: {validation_results['instruments_with_prices']}/"
            f"{validation_results['total_instruments']} instruments have prices "
            f"({validation_results['coverage_percent']:.1f}% coverage)"
        )

        logger.info(
            f"🔍 Sample validation: {prices_found}/{sample_size} sample instruments have prices "
            f"({validation_results['sample_coverage_percent']:.1f}% sample coverage)"
        )

        if validation_results["errors"]:
            logger.warning(
                f"⚠️ Validation found {len(validation_results['errors'])} errors"
            )

        return validation_results

    # Add this function to instrument_registry.py

    def get_special_index_mapping(self):
        """
        Get special index symbol mappings based on the exact keys found in your system
        """
        return {
            # The exact keys that have good data in your system
            "NIFTY": ["NSE_INDEX|Nifty 50"],  # Has correct value 24968.4
            "BANKNIFTY": [
                "NSE_INDEX|Nifty Bank"
            ],  # No live data yet but correct instrument
            "FINNIFTY": [
                "NSE_INDEX|Nifty Fin Service",
                "NSE_INDEX|Nifty Financial Services",
            ],
            "SENSEX": ["BSE_INDEX|SENSEX"],  # Has correct value 81757.73
            "MIDCPNIFTY": [
                "NSE_INDEX|Nifty Midcap 50",
                "NSE_INDEX|NIFTY MID SELECT",
            ],  # Both keys appear in your system
        }

    def get_spot_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get spot price for a symbol with enhanced error handling and consistent data access"""
        try:
            symbol = symbol.upper()

            # Special handling for major indices
            special_index_mapping = self.get_special_index_mapping()
            possible_keys = []

            if symbol in special_index_mapping:
                # For major indices, try all possible instrument keys
                index_keys = special_index_mapping[symbol]
                logger.info(f"🔍 Searching for index {symbol} using keys: {index_keys}")

                # First, try to find any key that exists in _live_prices
                for index_key in index_keys:
                    if index_key in self._live_prices:
                        price_data = self._live_prices[index_key]
                        if price_data and price_data.get("ltp") is not None:
                            logger.info(
                                f"✅ Found live price for {symbol} using key: {index_key}"
                            )

                            # Calculate change values if necessary
                            ltp = price_data.get("ltp")
                            cp = price_data.get("cp")
                            change = price_data.get("change")
                            change_percent = price_data.get("change_percent")

                            # Calculate if not provided
                            if ltp is not None and cp is not None and cp != 0:
                                if change is None:
                                    change = ltp - cp
                                if change_percent is None:
                                    change_percent = (change / cp) * 100

                            # Build response
                            return {
                                "symbol": symbol,
                                "instrument_key": index_key,
                                "trading_symbol": symbol,
                                "name": symbol,
                                "exchange": "NSE" if "NSE_" in index_key else "BSE",
                                "last_price": ltp,
                                "change": change,
                                "change_percent": change_percent,
                                "volume": price_data.get("volume"),
                                "high": price_data.get("high"),
                                "low": price_data.get("low"),
                                "open": price_data.get("open"),
                                "close": price_data.get("close"),
                                "last_updated": price_data.get("timestamp")
                                or datetime.now().isoformat(),
                            }

                # Next, try to find the instrument in our registry
                for index_key in index_keys:
                    instrument = None
                    if index_key in self._spot_instruments:
                        instrument = self._spot_instruments[index_key]
                        possible_keys.append(index_key)
                    elif index_key in self._fno_instruments:
                        instrument = self._fno_instruments[index_key]
                        possible_keys.append(index_key)

                    if instrument:
                        logger.info(
                            f"✅ Found instrument for {symbol} using key: {index_key}"
                        )
                        # Now look for price data
                        price_data = self._live_prices.get(index_key, {})

                        ltp = price_data.get("ltp")
                        cp = price_data.get("cp")
                        change = price_data.get("change")
                        change_percent = price_data.get("change_percent")

                        # Calculate if not provided
                        if ltp is not None and cp is not None and cp != 0:
                            if change is None:
                                change = ltp - cp
                            if change_percent is None:
                                change_percent = (change / cp) * 100

                        # Build response
                        return {
                            "symbol": symbol,
                            "instrument_key": index_key,
                            "trading_symbol": self._get_value(
                                instrument, "trading_symbol", symbol
                            ),
                            "name": self._get_value(instrument, "name", symbol),
                            "exchange": self._get_value(
                                instrument,
                                "exchange",
                                "NSE" if "NSE_" in index_key else "BSE",
                            ),
                            "last_price": ltp,
                            "change": change,
                            "change_percent": change_percent,
                            "volume": price_data.get("volume"),
                            "high": price_data.get("high"),
                            "low": price_data.get("low"),
                            "open": price_data.get("open"),
                            "close": price_data.get("close"),
                            "last_updated": price_data.get("timestamp")
                            or datetime.now().isoformat(),
                        }

                # Special Fallback Case 1: For MIDCPNIFTY, search for NIFTY MID
                if symbol == "MIDCPNIFTY":
                    for key in self._live_prices:
                        if "NIFTY MID" in key:
                            price_data = self._live_prices[key]
                            if price_data and price_data.get("ltp") is not None:
                                logger.info(
                                    f"✅ Found MIDCPNIFTY price using key: {key}"
                                )
                                return {
                                    "symbol": symbol,
                                    "instrument_key": key,
                                    "trading_symbol": symbol,
                                    "exchange": "NSE",
                                    "last_price": price_data.get("ltp"),
                                    "change": price_data.get("change"),
                                    "change_percent": price_data.get("change_percent"),
                                    "last_updated": price_data.get("timestamp")
                                    or datetime.now().isoformat(),
                                }

                # Try one more approach - look for any index key with the symbol in it
                for key in self._live_prices:
                    if "INDEX" in key and (
                        symbol in key
                        or symbol.replace("NIFTY", "Nifty") in key
                        or (symbol == "BANKNIFTY" and "BANK" in key)
                        or (symbol == "FINNIFTY" and "FIN" in key)
                    ):
                        price_data = self._live_prices[key]
                        if price_data and price_data.get("ltp") is not None:
                            logger.info(
                                f"✅ Found fallback price for {symbol} using key: {key}"
                            )

                            # Extract and calculate
                            ltp = price_data.get("ltp")
                            cp = price_data.get("cp")
                            change = price_data.get("change")
                            change_percent = price_data.get("change_percent")

                            # Calculate if needed
                            if ltp is not None and cp is not None and cp != 0:
                                if change is None:
                                    change = ltp - cp
                                if change_percent is None:
                                    change_percent = (change / cp) * 100

                            return {
                                "symbol": symbol,
                                "instrument_key": key,
                                "trading_symbol": symbol,
                                "exchange": "NSE" if "NSE_" in key else "BSE",
                                "last_price": ltp,
                                "change": change,
                                "change_percent": change_percent,
                                "last_updated": price_data.get("timestamp")
                                or datetime.now().isoformat(),
                            }

                # If we found possible keys but no price data, log for debugging
                if possible_keys:
                    logger.warning(
                        f"⚠️ Found instrument keys for {symbol} but no price data: {possible_keys}"
                    )

                    # Return empty data structure with the right key instead of none
                    return {
                        "symbol": symbol,
                        "instrument_key": index_keys[0] if index_keys else None,
                        "trading_symbol": symbol,
                        "exchange": (
                            "NSE"
                            if "NSE_" in (index_keys[0] if index_keys else "")
                            else "BSE"
                        ),
                        "last_price": None,
                        "change": None,
                        "change_percent": None,
                        "last_updated": datetime.now().isoformat(),
                    }

            # Fall back to normal lookup if not a special index or no special handling worked
            if symbol not in self._symbols_map:
                # Try to find a similar symbol
                similar_symbols = [s for s in self._symbols_map.keys() if symbol in s]
                if similar_symbols:
                    symbol = similar_symbols[0]
                    logger.info(f"🔍 Using similar symbol: {symbol}")
                else:
                    return None

            # Get spot keys - THIS IS THE CRITICAL FIX to filter out ETF keys for indices
            spot_keys = self._symbols_map[symbol]["spot"]
            original_keys = spot_keys.copy()

            # If this might be an index-like symbol, filter to only include INDEX keys
            if any(idx in symbol for idx in ["NIFTY", "SENSEX", "MIDCAP", "BANK"]):
                filtered_keys = [key for key in spot_keys if "INDEX" in key]
                # If we found any INDEX keys, use only those
                if filtered_keys:
                    logger.info(
                        f"🔍 Filtered to {len(filtered_keys)} INDEX keys for {symbol}"
                    )
                    spot_keys = filtered_keys
                else:
                    logger.warning(
                        f"⚠️ No INDEX keys found for {symbol} in {original_keys}"
                    )

            # Regular check for stock
            if not spot_keys:
                return None

            # Prioritize keys that have live data
            best_key = None
            best_price_data = None

            for spot_key in spot_keys:
                price_data = self._live_prices.get(spot_key, {})
                if price_data and price_data.get("ltp") is not None:
                    best_key = spot_key
                    best_price_data = price_data
                    logger.info(
                        f"✅ Found live price for {symbol} using key: {spot_key}"
                    )
                    break

            # If no key has price data, fall back to first key
            if best_key is None:
                best_key = spot_keys[0]
                best_price_data = self._live_prices.get(best_key, {})
                logger.info(
                    f"⚠️ No live price found for {symbol}, using first key: {best_key}"
                )

            # Get instrument data for the selected key
            instrument = None
            if best_key in self._spot_instruments:
                instrument = self._spot_instruments[best_key]
            elif best_key in self._fno_instruments:
                instrument = self._fno_instruments[best_key]

            if not instrument:
                return None

            # Extract values with proper defaults
            ltp = best_price_data.get("ltp")
            cp = best_price_data.get("cp")

            # Calculate change and change_percent
            change = best_price_data.get("change")
            change_percent = best_price_data.get("change_percent")

            if ltp is not None and cp is not None and cp != 0:
                if change is None:
                    change = ltp - cp
                if change_percent is None:
                    change_percent = (change / cp) * 100

            # Create the response with consistent data access
            response = {
                "symbol": symbol,
                "instrument_key": best_key,
                "trading_symbol": self._get_value(instrument, "trading_symbol", symbol),
                "exchange": self._get_value(instrument, "exchange", "NSE"),
                "last_price": ltp,
                "change": change,
                "change_percent": change_percent,
                "volume": best_price_data.get("volume"),
                "high": best_price_data.get("high"),
                "low": best_price_data.get("low"),
                "open": best_price_data.get("open"),
                "close": best_price_data.get("close"),
                "last_updated": best_price_data.get("timestamp"),
            }

            # Add timestamp if missing
            if response["last_updated"] is None:
                response["last_updated"] = datetime.now().isoformat()

            return response

        except Exception as e:
            logger.error(f"❌ Error getting spot price for {symbol}: {e}")
            logger.error(traceback.format_exc())
            return None

    # Add this to instrument_registry.py

    def debug_index_data(self):
        """
        Debug function to inspect all index data and help diagnose issues
        """
        special_indices = ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "MIDCPNIFTY"]
        debug_info = {}

        for symbol in special_indices:
            symbol_debug = {
                "symbol": symbol,
                "found_in_symbols_map": symbol in self._symbols_map,
                "possible_instrument_keys": [],
                "live_prices": {},
            }

            # Check special index mapping
            special_mapping = self.get_special_index_mapping()
            possible_keys = special_mapping.get(symbol, [])
            symbol_debug["mapping_keys"] = possible_keys

            # Check for each possible key
            for key in possible_keys:
                key_info = {
                    "key": key,
                    "in_spot_instruments": key in self._spot_instruments,
                    "in_fno_instruments": key in self._fno_instruments,
                    "in_live_prices": key in self._live_prices,
                }

                if key in self._live_prices:
                    # Get the actual live price data (only essential fields)
                    price_data = self._live_prices[key]
                    key_info["price_data"] = {
                        "ltp": price_data.get("ltp"),
                        "cp": price_data.get("cp"),
                        "change": price_data.get("change"),
                        "change_percent": price_data.get("change_percent"),
                        "timestamp": price_data.get("timestamp"),
                    }

                symbol_debug["possible_instrument_keys"].append(key_info)

            # Check standard instrument lookup
            if symbol in self._symbols_map:
                spot_keys = self._symbols_map[symbol]["spot"]
                symbol_debug["spot_keys"] = spot_keys

                for key in spot_keys:
                    if key in self._live_prices:
                        price_data = self._live_prices[key]
                        symbol_debug["live_prices"][key] = {
                            "ltp": price_data.get("ltp"),
                            "cp": price_data.get("cp"),
                            "change": price_data.get("change"),
                            "change_percent": price_data.get("change_percent"),
                        }

            # Try to get spot price with current method
            spot_price = self.get_spot_price(symbol)
            if spot_price:
                symbol_debug["current_spot_price"] = {
                    "instrument_key": spot_price.get("instrument_key"),
                    "last_price": spot_price.get("last_price"),
                    "change": spot_price.get("change"),
                    "change_percent": spot_price.get("change_percent"),
                }

            debug_info[symbol] = symbol_debug

        return debug_info

    # Add these methods to your InstrumentRegistry class

    def subscribe(self, topic: str, callback):
        """Subscribe to registry events"""
        # Initialize _subscribers attribute if it doesn't exist
        if not hasattr(self, "_subscribers"):
            self._subscribers = {}
            self._event_tasks = set()

        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(callback)
        logger.info(f"✅ Registry: Registered subscriber for {topic}")
        return True

    def unsubscribe(self, topic: str, callback):
        """Unsubscribe from registry events"""
        if not hasattr(self, "_subscribers"):
            return False

        if topic in self._subscribers and callback in self._subscribers[topic]:
            self._subscribers[topic].remove(callback)
            return True
        return False

    def publish(self, topic: str, data: Any):
        """Publish event to subscribers"""
        if not hasattr(self, "_subscribers"):
            return

        if topic not in self._subscribers or not self._subscribers[topic]:
            return

        for callback in self._subscribers[topic]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    task = asyncio.create_task(callback(data))
                    self._event_tasks.add(task)
                    task.add_done_callback(lambda t: self._event_tasks.discard(t))
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"❌ Error in subscriber callback: {e}")

    def get_top_gainers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top gaining stocks by percentage change"""
        try:
            gainers = []

            # Get all stocks with valid price data
            for symbol, symbol_data in self._symbols_map.items():
                # Skip indices
                if symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "MIDCPNIFTY"]:
                    continue

                spot_price_data = self.get_spot_price(symbol)
                if (
                    spot_price_data
                    and spot_price_data.get("last_price") is not None
                    and spot_price_data.get("change_percent") is not None
                    and spot_price_data.get("change_percent") > 0
                ):

                    gainers.append(
                        {
                            "symbol": symbol,
                            "instrument_key": spot_price_data.get("instrument_key"),
                            "trading_symbol": spot_price_data.get("trading_symbol"),
                            "last_price": spot_price_data.get("last_price"),
                            "change": spot_price_data.get("change"),
                            "change_percent": spot_price_data.get("change_percent"),
                            "volume": spot_price_data.get("volume"),
                            "exchange": spot_price_data.get("exchange"),
                            "last_updated": spot_price_data.get("last_updated"),
                        }
                    )

            # Sort by change_percent descending and limit results
            gainers.sort(key=lambda x: x["change_percent"], reverse=True)

            logger.info(f"📈 Found {len(gainers)} gainers, returning top {limit}")
            return gainers[:limit]

        except Exception as e:
            logger.error(f"❌ Error getting top gainers: {e}")
            return []

    def get_top_losers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top losing stocks by percentage change"""
        try:
            losers = []

            # Get all stocks with valid price data
            for symbol, symbol_data in self._symbols_map.items():
                # Skip indices
                if symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "MIDCPNIFTY"]:
                    continue

                spot_price_data = self.get_spot_price(symbol)
                if (
                    spot_price_data
                    and spot_price_data.get("last_price") is not None
                    and spot_price_data.get("change_percent") is not None
                    and spot_price_data.get("change_percent") < 0
                ):

                    losers.append(
                        {
                            "symbol": symbol,
                            "instrument_key": spot_price_data.get("instrument_key"),
                            "trading_symbol": spot_price_data.get("trading_symbol"),
                            "last_price": spot_price_data.get("last_price"),
                            "change": spot_price_data.get("change"),
                            "change_percent": spot_price_data.get("change_percent"),
                            "volume": spot_price_data.get("volume"),
                            "exchange": spot_price_data.get("exchange"),
                            "last_updated": spot_price_data.get("last_updated"),
                        }
                    )

            # Sort by change_percent ascending (most negative first) and limit results
            losers.sort(key=lambda x: x["change_percent"])

            logger.info(f"📉 Found {len(losers)} losers, returning top {limit}")
            return losers[:limit]

        except Exception as e:
            logger.error(f"❌ Error getting top losers: {e}")
            return []

    def get_top_movers(self, limit: int = 10) -> Dict[str, List[Dict[str, Any]]]:
        """Get top gainers and losers with full data"""
        all_stocks = list(self._enriched_prices.values())
        valid_stocks = [s for s in all_stocks if s.get("change_percent") is not None]

        # Sort once for efficiency
        sorted_stocks = sorted(valid_stocks, key=lambda x: x.get("change_percent", 0))

        return {
            "gainers": sorted_stocks[-limit:][::-1],  # Top gainers (reversed)
            "losers": sorted_stocks[:limit],  # Top losers
            "total_stocks_analyzed": len(valid_stocks),
            "timestamp": datetime.now().isoformat(),
        }

    def get_top_movers(self, limit: int = 10) -> Dict[str, List[Dict[str, Any]]]:
        """Get top gainers and losers with full data"""
        all_stocks = list(self._enriched_prices.values())
        valid_stocks = [s for s in all_stocks if s.get("change_percent") is not None]

        # Sort once for efficiency
        sorted_stocks = sorted(valid_stocks, key=lambda x: x.get("change_percent", 0))

        return {
            "gainers": sorted_stocks[-limit:][::-1],  # Top gainers (reversed)
            "losers": sorted_stocks[:limit],  # Top losers
            "total_stocks_analyzed": len(valid_stocks),
            "timestamp": datetime.now().isoformat(),
        }

    def get_sector_analysis(self) -> Dict[str, Any]:
        """Complete sector analysis"""
        sector_data = self.get_stocks_by_sector()

        analysis = {}
        for sector, stocks in sector_data.items():
            if not stocks or sector == "OTHER":
                continue

            # Calculate sector metrics
            total_stocks = len(stocks)
            advancing = len([s for s in stocks if (s.get("change_percent") or 0) > 0])
            declining = len([s for s in stocks if (s.get("change_percent") or 0) < 0])

            avg_change = sum(s.get("change_percent", 0) for s in stocks) / total_stocks
            total_volume = sum(s.get("volume", 0) for s in stocks)

            # Top performers in sector
            top_performer = max(stocks, key=lambda x: x.get("change_percent", 0))
            worst_performer = min(stocks, key=lambda x: x.get("change_percent", 0))

            analysis[sector] = {
                "total_stocks": total_stocks,
                "advancing": advancing,
                "declining": declining,
                "unchanged": total_stocks - advancing - declining,
                "avg_change_percent": round(avg_change, 2),
                "total_volume": total_volume,
                "strength_score": round(
                    (advancing - declining) / total_stocks * 100, 2
                ),
                "top_performer": {
                    "symbol": top_performer.get("symbol"),
                    "name": top_performer.get("name"),
                    "change_percent": top_performer.get("change_percent"),
                },
                "worst_performer": {
                    "symbol": worst_performer.get("symbol"),
                    "name": worst_performer.get("name"),
                    "change_percent": worst_performer.get("change_percent"),
                },
            }

        # Sort sectors by performance
        sorted_sectors = sorted(
            analysis.items(), key=lambda x: x[1]["avg_change_percent"], reverse=True
        )

        return {
            "sector_analysis": dict(sorted_sectors),
            "best_performing_sector": sorted_sectors[0][0] if sorted_sectors else None,
            "worst_performing_sector": (
                sorted_sectors[-1][0] if sorted_sectors else None
            ),
            "total_sectors_analyzed": len(analysis),
            "timestamp": datetime.now().isoformat(),
        }

    def search_instruments(
        self, query: str, filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Advanced instrument search"""
        query = query.upper()
        results = []

        for key, data in self._enriched_prices.items():
            # Search in symbol, name, and trading symbol
            searchable_text = f"{data.get('symbol', '')} {data.get('name', '')} {data.get('trading_symbol', '')}".upper()

            if query in searchable_text:
                # Apply filters if provided
                if filters:
                    if (
                        filters.get("sector")
                        and data.get("sector") != filters["sector"].upper()
                    ):
                        continue
                    if (
                        filters.get("exchange")
                        and data.get("exchange") != filters["exchange"].upper()
                    ):
                        continue
                    if (
                        filters.get("min_price")
                        and data.get("ltp", 0) < filters["min_price"]
                    ):
                        continue
                    if (
                        filters.get("max_price")
                        and data.get("ltp", 0) > filters["max_price"]
                    ):
                        continue

                results.append(data)

        # Sort by relevance (exact symbol match first, then by volume)
        results.sort(
            key=lambda x: (
                0 if x.get("symbol") == query else 1,  # Exact symbol match first
                -(x.get("volume", 0)),  # Then by volume (descending)
            )
        )

        return results[:50]  # Limit results

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get registry performance statistics"""
        return {
            "total_instruments": len(self._enriched_prices),
            "total_symbols": len(
                set(data.get("symbol") for data in self._enriched_prices.values())
            ),
            "exchanges": list(
                set(data.get("exchange") for data in self._enriched_prices.values())
            ),
            "sectors": list(
                set(data.get("sector") for data in self._enriched_prices.values())
            ),
            "last_update": self._last_update.isoformat() if self._last_update else None,
            "update_frequency": len(self._performance_cache),
            "memory_usage_estimate": len(self._enriched_prices) * 2,  # KB estimate
            "timestamp": datetime.now().isoformat(),
        }

    async def _trigger_enhanced_analytics(self):
        try:
            from services.enhanced_market_analytics import enhanced_analytics

            analytics_data = enhanced_analytics.get_complete_analytics()

            logger.info(f"Analytics features generated: {list(analytics_data.keys())}")

            from services.unified_websocket_manager import unified_manager

            for feature, data in analytics_data.items():
                logger.info(f"Emitting event for feature: {feature} ")
                if feature not in [
                    "generated_at",
                    "processing_time_ms",
                    "cache_status",
                ]:
                    unified_manager.emit_event(f"{feature}_update", data)

        except Exception as e:
            logger.error(f"Enhanced analytics trigger error: {e}")


# Call this function periodically (every 30 seconds) in your main market data update loop
# You can add this to your centralized_ws_manager or call it from your main update cycle


# Create singleton instance
instrument_registry = InstrumentRegistry()
