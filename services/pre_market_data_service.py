# import asyncio
# import aiohttp
# import json
# import logging
# from datetime import datetime, time
# from typing import Dict, List, Optional, Tuple
# from pathlib import Path
# from dataclasses import dataclass, asdict
# import pandas as pd
# import numpy as np
# from concurrent.futures import ThreadPoolExecutor
# import redis
# from sqlalchemy.orm import Session

# from database.connection import get_db
# from database.models import BrokerConfig, User

# logger = logging.getLogger(__name__)


# @dataclass
# class StockData:
#     symbol: str
#     name: str
#     instrument_key: str
#     exchange: str
#     segment: str
#     ltp: float
#     open: float
#     high: float
#     low: float
#     close: float
#     volume: int
#     change_percent: float


# @dataclass
# class ScreenerResult:
#     symbol: str
#     name: str
#     instrument_key: str
#     score: float
#     signals: List[str]
#     entry_price: float
#     target_price: float
#     stop_loss: float
#     risk_reward_ratio: float


# class SimpleInstrumentKeyBuilder:
#     """Simple fallback instrument key builder"""

#     def __init__(self):
#         self.default_stocks = [
#             {
#                 "symbol": "RELIANCE",
#                 "name": "Reliance Industries Ltd",
#                 "exchange": "NSE",
#             },
#             {
#                 "symbol": "TCS",
#                 "name": "Tata Consultancy Services Ltd",
#                 "exchange": "NSE",
#             },
#             {"symbol": "HDFC", "name": "HDFC Bank Ltd", "exchange": "NSE"},
#             {"symbol": "INFY", "name": "Infosys Ltd", "exchange": "NSE"},
#             {"symbol": "ICICIBANK", "name": "ICICI Bank Ltd", "exchange": "NSE"},
#             {"symbol": "SBIN", "name": "State Bank of India", "exchange": "NSE"},
#             {"symbol": "BHARTIARTL", "name": "Bharti Airtel Ltd", "exchange": "NSE"},
#             {"symbol": "ITC", "name": "ITC Ltd", "exchange": "NSE"},
#             {
#                 "symbol": "KOTAKBANK",
#                 "name": "Kotak Mahindra Bank Ltd",
#                 "exchange": "NSE",
#             },
#             {"symbol": "LT", "name": "Larsen & Toubro Ltd", "exchange": "NSE"},
#         ]

#     def load_data(self) -> Tuple[List[Dict], List[Dict]]:
#         """Load stock data - returns (stocks, instruments)"""
#         return self.default_stocks, []

#     def build_instrument_keys(self, **kwargs) -> Dict[str, List[str]]:
#         """Build instrument keys mapping"""
#         mapping = {}
#         for stock in self.default_stocks:
#             symbol = stock["symbol"]
#             # Create dummy instrument key for NSE EQ
#             instrument_key = f"NSE_EQ|INE000A01036"  # Dummy format
#             mapping[symbol] = [instrument_key]
#         return mapping


# class PreMarketDataService:
#     """
#     High-performance pre-market data preparation service.
#     Fetches OHLC data, applies screeners, and prepares trading signals.
#     """

#     def __init__(self):
#         try:
#             self.redis_client = redis.Redis(
#                 host="localhost", port=6379, db=0, decode_responses=True
#             )
#             # Test connection
#             self.redis_client.ping()
#         except Exception as e:
#             logger.warning(f"Redis connection failed: {e}. Using fallback cache.")
#             self.redis_client = None
#             self._fallback_cache = {}

#         self.session: Optional[aiohttp.ClientSession] = None
#         self.executor = ThreadPoolExecutor(max_workers=10)

#         # Try to import the real InstrumentKeyBuilder, fallback to simple version
#         try:
#             from services.instrument_key_builder import InstrumentKeyBuilder

#             self.instrument_builder = InstrumentKeyBuilder()
#             logger.info("✅ Using real InstrumentKeyBuilder")
#         except ImportError:
#             logger.warning("⚠️ InstrumentKeyBuilder not found, using simple fallback")
#             self.instrument_builder = SimpleInstrumentKeyBuilder()

#     def _cache_get(self, key: str) -> Optional[str]:
#         """Get from cache with fallback"""
#         if self.redis_client:
#             try:
#                 return self.redis_client.get(key)
#             except Exception:
#                 pass
#         return (
#             self._fallback_cache.get(key) if hasattr(self, "_fallback_cache") else None
#         )

#     def _cache_set(self, key: str, value: str, ttl: int = 3600):
#         """Set cache with fallback"""
#         if self.redis_client:
#             try:
#                 self.redis_client.setex(key, ttl, value)
#                 return
#             except Exception:
#                 pass
#         if hasattr(self, "_fallback_cache"):
#             self._fallback_cache[key] = value

#     async def __aenter__(self):
#         self.session = aiohttp.ClientSession(
#             timeout=aiohttp.ClientTimeout(total=30),
#             connector=aiohttp.TCPConnector(limit=100, limit_per_host=20),
#         )
#         return self

#     async def __aexit__(self, exc_type, exc_val, exc_tb):
#         if self.session:
#             await self.session.close()

#     def get_cached_trading_stocks(self) -> List[Dict]:
#         """Get cached trading stocks - main interface method"""
#         try:
#             cached = self._cache_get("trading_stocks_cache")
#             if cached:
#                 data = json.loads(cached)
#                 return data.get("selected_stocks", [])

#             # If no cache, return default stocks
#             logger.info("📦 No cached stocks found, returning default stocks")
#             return self._get_default_stocks()

#         except Exception as e:
#             logger.error(f"Failed to get cached stocks: {e}")
#             return self._get_default_stocks()

#     def _get_default_stocks(self) -> List[Dict]:
#         """Get default stocks for trading"""
#         default_stocks = []
#         for stock in self.instrument_builder.default_stocks:
#             default_stocks.append(
#                 {
#                     "symbol": stock["symbol"],
#                     "name": stock["name"],
#                     "exchange": stock["exchange"],
#                     "entry_price": 100.0,  # Dummy price
#                     "target_price": 103.0,
#                     "stop_loss": 98.0,
#                     "score": 75,
#                     "signals": ["DEFAULT"],
#                     "risk_reward_ratio": 1.5,
#                     "instrument_key": f"NSE_EQ|{stock['symbol']}",
#                 }
#             )
#         return default_stocks

#     async def initialize_pre_market_data(self, user_id: int) -> Dict:
#         """
#         Main function to initialize all pre-market data.
#         Should be called before market opens.
#         """
#         start_time = datetime.now()
#         logger.info("🚀 Starting pre-market data initialization...")

#         try:
#             # Step 1: Build instrument keys mapping (cached)
#             instrument_mapping = await self._build_instrument_mapping()

#             # Step 2: Fetch OHLC data for all instruments
#             try:
#                 ohlc_data = await self._fetch_bulk_ohlc_data(
#                     user_id, instrument_mapping
#                 )
#             except Exception as e:
#                 logger.warning(f"OHLC fetch failed: {e}. Using fallback data.")
#                 ohlc_data = self._generate_fallback_ohlc_data(instrument_mapping)

#             # Step 3: Apply screeners and generate signals
#             screener_results = await self._apply_screeners(ohlc_data)

#             # Step 4: Select top 20 stocks for trading
#             selected_stocks = self._select_trading_stocks(screener_results, limit=20)

#             # Step 5: Cache everything for fast access
#             await self._cache_trading_data(selected_stocks, instrument_mapping)

#             # Step 6: Prepare WebSocket subscription list
#             ws_instruments = [stock.instrument_key for stock in selected_stocks]

#             end_time = datetime.now()
#             processing_time = (end_time - start_time).total_seconds()

#             result = {
#                 "status": "success",
#                 "processing_time_seconds": processing_time,
#                 "total_instruments_analyzed": len(ohlc_data),
#                 "screener_results": len(screener_results),
#                 "selected_for_trading": len(selected_stocks),
#                 "websocket_instruments": ws_instruments,
#                 "trading_stocks": [asdict(stock) for stock in selected_stocks],
#                 "initialized_at": datetime.now().isoformat(),
#             }

#             logger.info(
#                 f"✅ Pre-market initialization completed in {processing_time:.2f}s"
#             )
#             return result

#         except Exception as e:
#             logger.error(f"❌ Pre-market initialization failed: {e}")
#             # Return fallback result
#             return {
#                 "status": "fallback",
#                 "error": str(e),
#                 "selected_for_trading": len(self._get_default_stocks()),
#                 "trading_stocks": self._get_default_stocks(),
#                 "initialized_at": datetime.now().isoformat(),
#             }

#     def _generate_fallback_ohlc_data(self, instrument_mapping: Dict) -> List[StockData]:
#         """Generate fallback OHLC data when API fails"""
#         logger.info("📊 Generating fallback OHLC data...")

#         fallback_data = []
#         for instrument_key, stock_info in instrument_mapping.items():
#             # Generate realistic but dummy data
#             base_price = 100 + (hash(stock_info["symbol"]) % 500)

#             stock_data = StockData(
#                 symbol=stock_info["symbol"],
#                 name=stock_info["name"],
#                 instrument_key=instrument_key,
#                 exchange=stock_info["exchange"],
#                 segment="EQ",
#                 ltp=base_price * 1.02,  # 2% up from close
#                 open=base_price * 0.995,
#                 high=base_price * 1.08,
#                 low=base_price * 0.99,
#                 close=base_price,
#                 volume=100000 + (hash(stock_info["symbol"]) % 500000),
#                 change_percent=2.0,
#             )
#             fallback_data.append(stock_data)

#         return fallback_data

#     async def _build_instrument_mapping(self) -> Dict[str, Dict]:
#         """Build and cache instrument key to stock mapping."""
#         cache_key = "instrument_mapping"
#         cached = self._cache_get(cache_key)

#         if cached:
#             logger.info("📦 Using cached instrument mapping")
#             return json.loads(cached)

#         logger.info("🔧 Building fresh instrument mapping...")

#         # Build mapping using instrument key builder
#         stock_instruments = self.instrument_builder.build_instrument_keys(
#             include_futures=False,  # Only EQ for screener
#             include_options=False,
#             max_options_per_type=0,
#             strike_range=0,
#         )

#         # Create reverse mapping: instrument_key -> stock_info
#         mapping = {}
#         top_stocks, _ = self.instrument_builder.load_data()

#         for stock in top_stocks:
#             symbol = stock["symbol"]
#             if symbol in stock_instruments:
#                 for instrument_key in stock_instruments[symbol]:
#                     mapping[instrument_key] = {
#                         "symbol": symbol,
#                         "name": stock["name"],
#                         "exchange": stock["exchange"],
#                     }

#         # Cache for 24 hours
#         self._cache_set(cache_key, json.dumps(mapping), 86400)
#         logger.info(f"📦 Cached mapping for {len(mapping)} instruments")

#         return mapping

#     async def _fetch_bulk_ohlc_data(
#         self, user_id: int, instrument_mapping: Dict
#     ) -> List[StockData]:
#         """Fetch OHLC data for all instruments in parallel."""
#         logger.info(
#             f"📊 Fetching OHLC data for {len(instrument_mapping)} instruments..."
#         )

#         # Get user's broker token
#         db = next(get_db())
#         broker = (
#             db.query(BrokerConfig)
#             .filter(
#                 BrokerConfig.user_id == user_id,
#                 BrokerConfig.broker_name.ilike("upstox"),
#                 BrokerConfig.is_active == True,
#             )
#             .first()
#         )

#         if not broker or not broker.access_token:
#             raise ValueError("No active Upstox broker found")

#         # Prepare requests
#         instrument_keys = list(instrument_mapping.keys())
#         tasks = []

#         # Split into batches for better performance
#         batch_size = 50
#         for i in range(0, len(instrument_keys), batch_size):
#             batch = instrument_keys[i : i + batch_size]
#             task = self._fetch_ohlc_batch(
#                 broker.access_token, batch, instrument_mapping
#             )
#             tasks.append(task)

#         # Execute all batches concurrently
#         batch_results = await asyncio.gather(*tasks, return_exceptions=True)

#         # Flatten results
#         all_stock_data = []
#         for result in batch_results:
#             if isinstance(result, Exception):
#                 logger.error(f"Batch failed: {result}")
#                 continue
#             all_stock_data.extend(result)

#         logger.info(f"📊 Successfully fetched data for {len(all_stock_data)} stocks")
#         return all_stock_data

#     async def _fetch_ohlc_batch(
#         self, access_token: str, instrument_keys: List[str], mapping: Dict
#     ) -> List[StockData]:
#         """Fetch OHLC data for a batch of instruments."""
#         results = []
#         headers = {"Authorization": f"Bearer {access_token}"}

#         for instrument_key in instrument_keys:
#             try:
#                 # Upstox API call for OHLC data
#                 url = f"https://api.upstox.com/v2/market-quote/ohlc?instrument_key={instrument_key}"

#                 async with self.session.get(url, headers=headers) as response:
#                     if response.status == 200:
#                         data = await response.json()
#                         quote_data = data.get("data", {}).get(instrument_key, {})

#                         if quote_data:
#                             stock_info = mapping[instrument_key]

#                             # Extract OHLC data
#                             ohlc = quote_data.get("ohlc", {})

#                             stock_data = StockData(
#                                 symbol=stock_info["symbol"],
#                                 name=stock_info["name"],
#                                 instrument_key=instrument_key,
#                                 exchange=stock_info["exchange"],
#                                 segment=quote_data.get("segment", ""),
#                                 ltp=quote_data.get("last_price", 0),
#                                 open=ohlc.get("open", 0),
#                                 high=ohlc.get("high", 0),
#                                 low=ohlc.get("low", 0),
#                                 close=ohlc.get("close", 0),
#                                 volume=quote_data.get("volume", 0),
#                                 change_percent=quote_data.get("net_change", 0),
#                             )
#                             results.append(stock_data)

#                     # Rate limiting
#                     await asyncio.sleep(0.1)

#             except Exception as e:
#                 logger.warning(f"Failed to fetch data for {instrument_key}: {e}")
#                 continue

#         return results

#     async def _apply_screeners(
#         self, stock_data: List[StockData]
#     ) -> List[ScreenerResult]:
#         """Apply multiple screeners to identify trading opportunities."""
#         logger.info(f"🔍 Applying screeners to {len(stock_data)} stocks...")

#         screener_results = []

#         for stock in stock_data:
#             try:
#                 # Apply multiple screening criteria
#                 score = 0
#                 signals = []

#                 # Price-based filters
#                 if stock.ltp > stock.close * 1.02:  # 2% up from previous close
#                     score += 20
#                     signals.append("BREAKOUT_UP")

#                 if stock.volume > 100000:  # High volume
#                     score += 15
#                     signals.append("HIGH_VOLUME")

#                 # Technical analysis (simplified)
#                 if stock.high > stock.close * 1.05:  # Strong momentum
#                     score += 25
#                     signals.append("MOMENTUM")

#                 # Risk management
#                 if stock.ltp > 50:  # Minimum price filter
#                     score += 10
#                     signals.append("PRICE_FILTER")

#                 # Gap analysis
#                 if stock.close > 0:  # Avoid division by zero
#                     gap_percent = ((stock.open - stock.close) / stock.close) * 100
#                     if gap_percent > 2:
#                         score += 30
#                         signals.append("GAP_UP")

#                 # Only consider stocks with minimum score
#                 if score >= 40 and signals:
#                     # Calculate targets and stop loss
#                     entry_price = stock.ltp if stock.ltp > 0 else stock.close
#                     target_price = entry_price * 1.03  # 3% target
#                     stop_loss = entry_price * 0.98  # 2% stop loss

#                     # Calculate risk-reward ratio safely
#                     risk = entry_price - stop_loss
#                     reward = target_price - entry_price
#                     risk_reward = reward / risk if risk > 0 else 1.5

#                     result = ScreenerResult(
#                         symbol=stock.symbol,
#                         name=stock.name,
#                         instrument_key=stock.instrument_key,
#                         score=score,
#                         signals=signals,
#                         entry_price=entry_price,
#                         target_price=target_price,
#                         stop_loss=stop_loss,
#                         risk_reward_ratio=risk_reward,
#                     )
#                     screener_results.append(result)

#             except Exception as e:
#                 logger.warning(f"Screener failed for {stock.symbol}: {e}")
#                 continue

#         # Sort by score (highest first)
#         screener_results.sort(key=lambda x: x.score, reverse=True)

#         logger.info(f"🔍 Screener found {len(screener_results)} potential trades")
#         return screener_results

#     def _select_trading_stocks(
#         self, screener_results: List[ScreenerResult], limit: int = 20
#     ) -> List[ScreenerResult]:
#         """Select top stocks for trading based on score and risk management."""
#         logger.info(f"🎯 Selecting top {limit} stocks for trading...")

#         # Additional filtering
#         filtered_results = []

#         for result in screener_results:
#             # Risk management filters
#             if result.risk_reward_ratio >= 1.5:  # Minimum R:R ratio
#                 if "BREAKOUT_UP" in result.signals or "GAP_UP" in result.signals:
#                     filtered_results.append(result)

#         # Return top N stocks
#         selected = filtered_results[:limit]

#         # If not enough stocks found, add some from the full list
#         if len(selected) < limit and screener_results:
#             remaining_needed = limit - len(selected)
#             for result in screener_results:
#                 if result not in selected and len(selected) < limit:
#                     selected.append(result)

#         logger.info(f"🎯 Selected {len(selected)} stocks for trading")
#         return selected

#     async def _cache_trading_data(
#         self, selected_stocks: List[ScreenerResult], instrument_mapping: Dict
#     ):
#         """Cache trading data for fast access during market hours."""
#         logger.info("💾 Caching trading data...")

#         # Cache selected stocks
#         cache_data = {
#             "selected_stocks": [asdict(stock) for stock in selected_stocks],
#             "instrument_mapping": instrument_mapping,
#             "cached_at": datetime.now().isoformat(),
#         }

#         self._cache_set("trading_stocks_cache", json.dumps(cache_data), 3600)

#         # Cache individual stock data for quick lookup
#         for stock in selected_stocks:
#             stock_cache_key = f"stock_data:{stock.symbol}"
#             self._cache_set(stock_cache_key, json.dumps(asdict(stock)), 3600)

#         logger.info("💾 Trading data cached successfully")

#     def get_status(self) -> Dict[str, any]:
#         """Get service status"""
#         return {
#             "service": "PreMarketDataService",
#             "redis_connected": self.redis_client is not None,
#             "instrument_builder": type(self.instrument_builder).__name__,
#             "status": "active",
#         }


# # Fast retrieval functions (module level)
# def get_cached_trading_stocks() -> Optional[List[Dict]]:
#     """Get cached trading stocks for fast access."""
#     try:
#         redis_client = redis.Redis(
#             host="localhost", port=6379, db=0, decode_responses=True
#         )
#         cached = redis_client.get("trading_stocks_cache")
#         if cached:
#             data = json.loads(cached)
#             return data.get("selected_stocks", [])
#     except Exception as e:
#         logger.error(f"Failed to get cached stocks: {e}")

#     # Return default stocks as fallback
#     return [
#         {"symbol": "RELIANCE", "name": "Reliance Industries", "exchange": "NSE"},
#         {"symbol": "TCS", "name": "Tata Consultancy Services", "exchange": "NSE"},
#         {"symbol": "HDFC", "name": "HDFC Bank", "exchange": "NSE"},
#         {"symbol": "INFY", "name": "Infosys", "exchange": "NSE"},
#         {"symbol": "ICICIBANK", "name": "ICICI Bank", "exchange": "NSE"},
#     ]


# def get_stock_data(symbol: str) -> Optional[Dict]:
#     """Get individual stock data from cache."""
#     try:
#         redis_client = redis.Redis(
#             host="localhost", port=6379, db=0, decode_responses=True
#         )
#         cached = redis_client.get(f"stock_data:{symbol}")
#         if cached:
#             return json.loads(cached)
#     except Exception as e:
#         logger.error(f"Failed to get stock data for {symbol}: {e}")
#     return None
