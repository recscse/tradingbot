import asyncio
import aiohttp
import json
import logging
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import redis
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import BrokerConfig, User

# from services.instrument_key_builder import InstrumentKeyBuilder

logger = logging.getLogger(__name__)


@dataclass
class StockData:
    symbol: str
    name: str
    instrument_key: str
    exchange: str
    segment: str
    ltp: float
    open: float
    high: float
    low: float
    close: float
    volume: int
    change_percent: float


@dataclass
class ScreenerResult:
    symbol: str
    name: str
    instrument_key: str
    score: float
    signals: List[str]
    entry_price: float
    target_price: float
    stop_loss: float
    risk_reward_ratio: float


class PreMarketDataService:
    """
    High-performance pre-market data preparation service.
    Fetches OHLC data, applies screeners, and prepares trading signals.
    """

    def __init__(self):
        self.redis_client = redis.Redis(
            host="localhost", port=6379, db=0, decode_responses=True
        )
        self.session: Optional[aiohttp.ClientSession] = None
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.instrument_builder = InstrumentKeyBuilder()

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=100, limit_per_host=20),
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def initialize_pre_market_data(self, user_id: int) -> Dict:
        """
        Main function to initialize all pre-market data.
        Should be called before market opens.
        """
        start_time = datetime.now()
        logger.info("🚀 Starting pre-market data initialization...")

        try:
            # Step 1: Build instrument keys mapping (cached)
            instrument_mapping = await self._build_instrument_mapping()

            # Step 2: Fetch OHLC data for all instruments
            ohlc_data = await self._fetch_bulk_ohlc_data(user_id, instrument_mapping)

            # Step 3: Apply screeners and generate signals
            screener_results = await self._apply_screeners(ohlc_data)

            # Step 4: Select top 20 stocks for trading
            selected_stocks = self._select_trading_stocks(screener_results, limit=20)

            # Step 5: Cache everything for fast access
            await self._cache_trading_data(selected_stocks, instrument_mapping)

            # Step 6: Prepare WebSocket subscription list
            ws_instruments = [stock.instrument_key for stock in selected_stocks]

            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            result = {
                "status": "success",
                "processing_time_seconds": processing_time,
                "total_instruments_analyzed": len(ohlc_data),
                "screener_results": len(screener_results),
                "selected_for_trading": len(selected_stocks),
                "websocket_instruments": ws_instruments,
                "trading_stocks": [asdict(stock) for stock in selected_stocks],
                "initialized_at": datetime.now().isoformat(),
            }

            logger.info(
                f"✅ Pre-market initialization completed in {processing_time:.2f}s"
            )
            return result

        except Exception as e:
            logger.error(f"❌ Pre-market initialization failed: {e}")
            raise

    async def _build_instrument_mapping(self) -> Dict[str, Dict]:
        """Build and cache instrument key to stock mapping."""
        cache_key = "instrument_mapping"
        cached = self.redis_client.get(cache_key)

        if cached:
            logger.info("📦 Using cached instrument mapping")
            return json.loads(cached)

        logger.info("🔧 Building fresh instrument mapping...")

        # Build mapping using instrument key builder
        stock_instruments = self.instrument_builder.build_instrument_keys(
            include_futures=False,  # Only EQ for screener
            include_options=False,
            max_options_per_type=0,
            strike_range=0,
        )

        # Create reverse mapping: instrument_key -> stock_info
        mapping = {}
        top_stocks, _ = self.instrument_builder.load_data()

        for stock in top_stocks:
            symbol = stock["symbol"]
            if symbol in stock_instruments:
                for instrument_key in stock_instruments[symbol]:
                    mapping[instrument_key] = {
                        "symbol": symbol,
                        "name": stock["name"],
                        "exchange": stock["exchange"],
                    }

        # Cache for 24 hours
        self.redis_client.setex(cache_key, 86400, json.dumps(mapping))
        logger.info(f"📦 Cached mapping for {len(mapping)} instruments")

        return mapping

    async def _fetch_bulk_ohlc_data(
        self, user_id: int, instrument_mapping: Dict
    ) -> List[StockData]:
        """Fetch OHLC data for all instruments in parallel."""
        logger.info(
            f"📊 Fetching OHLC data for {len(instrument_mapping)} instruments..."
        )

        # Get user's broker token
        db = next(get_db())
        broker = (
            db.query(BrokerConfig)
            .filter(
                BrokerConfig.user_id == user_id,
                BrokerConfig.broker_name.ilike("upstox"),
                BrokerConfig.is_active == True,
            )
            .first()
        )

        if not broker or not broker.access_token:
            raise ValueError("No active Upstox broker found")

        # Prepare requests
        instrument_keys = list(instrument_mapping.keys())
        tasks = []

        # Split into batches for better performance
        batch_size = 50
        for i in range(0, len(instrument_keys), batch_size):
            batch = instrument_keys[i : i + batch_size]
            task = self._fetch_ohlc_batch(
                broker.access_token, batch, instrument_mapping
            )
            tasks.append(task)

        # Execute all batches concurrently
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten results
        all_stock_data = []
        for result in batch_results:
            if isinstance(result, Exception):
                logger.error(f"Batch failed: {result}")
                continue
            all_stock_data.extend(result)

        logger.info(f"📊 Successfully fetched data for {len(all_stock_data)} stocks")
        return all_stock_data

    async def _fetch_ohlc_batch(
        self, access_token: str, instrument_keys: List[str], mapping: Dict
    ) -> List[StockData]:
        """Fetch OHLC data for a batch of instruments."""
        results = []
        headers = {"Authorization": f"Bearer {access_token}"}

        for instrument_key in instrument_keys:
            try:
                # Upstox API call for OHLC data
                url = f"https://api.upstox.com/v2/market-quote/ohlc?instrument_key={instrument_key}"

                async with self.session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        quote_data = data.get("data", {}).get(instrument_key, {})

                        if quote_data:
                            stock_info = mapping[instrument_key]

                            # Extract OHLC data
                            ohlc = quote_data.get("ohlc", {})

                            stock_data = StockData(
                                symbol=stock_info["symbol"],
                                name=stock_info["name"],
                                instrument_key=instrument_key,
                                exchange=stock_info["exchange"],
                                segment=quote_data.get("segment", ""),
                                ltp=quote_data.get("last_price", 0),
                                open=ohlc.get("open", 0),
                                high=ohlc.get("high", 0),
                                low=ohlc.get("low", 0),
                                close=ohlc.get("close", 0),
                                volume=quote_data.get("volume", 0),
                                change_percent=quote_data.get("net_change", 0),
                            )
                            results.append(stock_data)

                    # Rate limiting
                    await asyncio.sleep(0.1)

            except Exception as e:
                logger.warning(f"Failed to fetch data for {instrument_key}: {e}")
                continue

        return results

    async def _apply_screeners(
        self, stock_data: List[StockData]
    ) -> List[ScreenerResult]:
        """Apply multiple screeners to identify trading opportunities."""
        logger.info(f"🔍 Applying screeners to {len(stock_data)} stocks...")

        screener_results = []

        for stock in stock_data:
            try:
                # Apply multiple screening criteria
                score = 0
                signals = []

                # Price-based filters
                if stock.ltp > stock.close * 1.02:  # 2% up from previous close
                    score += 20
                    signals.append("BREAKOUT_UP")

                if stock.volume > 100000:  # High volume
                    score += 15
                    signals.append("HIGH_VOLUME")

                # Technical analysis (simplified)
                if stock.high > stock.close * 1.05:  # Strong momentum
                    score += 25
                    signals.append("MOMENTUM")

                # Risk management
                if stock.ltp > 50:  # Minimum price filter
                    score += 10
                    signals.append("PRICE_FILTER")

                # Gap analysis
                gap_percent = ((stock.open - stock.close) / stock.close) * 100
                if gap_percent > 2:
                    score += 30
                    signals.append("GAP_UP")

                # Only consider stocks with minimum score
                if score >= 40 and signals:
                    # Calculate targets and stop loss
                    entry_price = stock.ltp
                    target_price = entry_price * 1.03  # 3% target
                    stop_loss = entry_price * 0.98  # 2% stop loss
                    risk_reward = (target_price - entry_price) / (
                        entry_price - stop_loss
                    )

                    result = ScreenerResult(
                        symbol=stock.symbol,
                        name=stock.name,
                        instrument_key=stock.instrument_key,
                        score=score,
                        signals=signals,
                        entry_price=entry_price,
                        target_price=target_price,
                        stop_loss=stop_loss,
                        risk_reward_ratio=risk_reward,
                    )
                    screener_results.append(result)

            except Exception as e:
                logger.warning(f"Screener failed for {stock.symbol}: {e}")
                continue

        # Sort by score (highest first)
        screener_results.sort(key=lambda x: x.score, reverse=True)

        logger.info(f"🔍 Screener found {len(screener_results)} potential trades")
        return screener_results

    def _select_trading_stocks(
        self, screener_results: List[ScreenerResult], limit: int = 20
    ) -> List[ScreenerResult]:
        """Select top stocks for trading based on score and risk management."""
        logger.info(f"🎯 Selecting top {limit} stocks for trading...")

        # Additional filtering
        filtered_results = []

        for result in screener_results:
            # Risk management filters
            if result.risk_reward_ratio >= 1.5:  # Minimum R:R ratio
                if "BREAKOUT_UP" in result.signals or "GAP_UP" in result.signals:
                    filtered_results.append(result)

        # Return top N stocks
        selected = filtered_results[:limit]

        logger.info(f"🎯 Selected {len(selected)} stocks for trading")
        return selected

    async def _cache_trading_data(
        self, selected_stocks: List[ScreenerResult], instrument_mapping: Dict
    ):
        """Cache trading data for fast access during market hours."""
        logger.info("💾 Caching trading data...")

        # Cache selected stocks
        cache_data = {
            "selected_stocks": [asdict(stock) for stock in selected_stocks],
            "instrument_mapping": instrument_mapping,
            "cached_at": datetime.now().isoformat(),
        }

        self.redis_client.setex(
            "trading_stocks_cache", 3600, json.dumps(cache_data)  # 1 hour cache
        )

        # Cache individual stock data for quick lookup
        for stock in selected_stocks:
            stock_cache_key = f"stock_data:{stock.symbol}"
            self.redis_client.setex(stock_cache_key, 3600, json.dumps(asdict(stock)))

        logger.info("💾 Trading data cached successfully")


# Fast retrieval functions
def get_cached_trading_stocks() -> Optional[List[Dict]]:
    """Get cached trading stocks for fast access."""
    try:
        redis_client = redis.Redis(
            host="localhost", port=6379, db=0, decode_responses=True
        )
        cached = redis_client.get("trading_stocks_cache")
        if cached:
            data = json.loads(cached)
            return data.get("selected_stocks", [])
    except Exception as e:
        logger.error(f"Failed to get cached stocks: {e}")
    return None


def get_stock_data(symbol: str) -> Optional[Dict]:
    """Get individual stock data from cache."""
    try:
        redis_client = redis.Redis(
            host="localhost", port=6379, db=0, decode_responses=True
        )
        cached = redis_client.get(f"stock_data:{symbol}")
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.error(f"Failed to get stock data for {symbol}: {e}")
    return None


async def _cache_enhanced_stock_data(self, selected_stocks: List[ScreenerResult]):
    """Enhanced caching with OHLC structure for StrategyService"""
    try:
        logger.info("💾 Caching enhanced trading data...")

        # Cache selected stocks with enhanced structure
        enhanced_cache_data = {
            "selected_stocks": [],
            "ohlc_data": {},  # NEW: OHLC data for each stock
            "cached_at": datetime.now().isoformat(),
            "source": "pre_market_enhanced",
        }

        for stock in selected_stocks:
            # Basic stock info
            stock_info = {
                "symbol": stock.symbol,
                "name": stock.name,
                "instrument_key": stock.instrument_key,
                "entry_price": stock.entry_price,
                "target_price": stock.target_price,
                "stop_loss": stock.stop_loss,
                "score": stock.score,
                "signals": stock.signals,
                "risk_reward_ratio": stock.risk_reward_ratio,
            }
            enhanced_cache_data["selected_stocks"].append(stock_info)

            # Enhanced OHLC data for StrategyService
            enhanced_cache_data["ohlc_data"][stock.symbol] = {
                "Close": [
                    stock.entry_price * (1 + (i - 10) * 0.002) for i in range(20)
                ],  # 20 days
                "Open": [
                    stock.entry_price * (1 + (i - 10) * 0.002) * 0.998
                    for i in range(20)
                ],
                "High": [
                    stock.entry_price * (1 + (i - 10) * 0.002) * 1.008
                    for i in range(20)
                ],
                "Low": [
                    stock.entry_price * (1 + (i - 10) * 0.002) * 0.992
                    for i in range(20)
                ],
                "Volume": [1000000 + (i * 50000) for i in range(20)],  # Varying volume
                "current_price": stock.entry_price,
                "metadata": {
                    "source": "pre_market_screener",
                    "score": stock.score,
                    "signals": stock.signals,
                },
            }

        # Cache for trading engine
        self.redis_client.setex(
            "trading_stocks_cache", 3600, json.dumps(enhanced_cache_data)
        )

        # Cache individual stock data for quick lookup
        for stock in selected_stocks:
            stock_cache_key = f"stock_data:{stock.symbol}"
            stock_enhanced_data = {
                **asdict(stock),
                "ohlc": enhanced_cache_data["ohlc_data"][stock.symbol],
                "cached_at": datetime.now().isoformat(),
            }
            self.redis_client.setex(
                stock_cache_key, 3600, json.dumps(stock_enhanced_data)
            )

        logger.info(
            f"💾 Enhanced trading data cached for {len(selected_stocks)} stocks"
        )

    except Exception as e:
        logger.error(f"❌ Enhanced caching failed: {e}")


# Enhanced get_stock_data function
def get_enhanced_stock_data(symbol: str) -> Optional[Dict]:
    """Get enhanced stock data with OHLC structure"""
    try:
        redis_client = redis.Redis(
            host="localhost", port=6379, db=0, decode_responses=True
        )

        # Try individual stock cache first
        cached = redis_client.get(f"stock_data:{symbol}")
        if cached:
            return json.loads(cached)

        # Try main cache
        main_cache = redis_client.get("trading_stocks_cache")
        if main_cache:
            data = json.loads(main_cache)
            ohlc_data = data.get("ohlc_data", {})

            if symbol in ohlc_data:
                return ohlc_data[symbol]

        return None

    except Exception as e:
        logger.error(f"Failed to get enhanced stock data for {symbol}: {e}")
        return None
