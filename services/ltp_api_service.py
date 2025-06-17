import asyncio
import aiohttp
import json
import logging
from datetime import datetime, time
from typing import Dict, List, Optional, Callable
from services.optimized_instrument_service import (
    get_all_websocket_keys,
    get_fast_retrieval,
)

logger = logging.getLogger(__name__)


class LTPAPIService:
    """
    LTP API service for dashboard data.
    Integrates with your existing instrument services.
    """

    def __init__(self):
        self.base_url = "https://api.upstox.com/v2/market-quote/ltp"
        self.session: Optional[aiohttp.ClientSession] = None
        self.access_token = None
        self.polling_active = False
        self.polling_task = None
        self.callback_func: Optional[Callable] = None
        self.batch_size = 500

    async def initialize(self, user_id: int, access_token: str):
        """Initialize LTP service"""
        try:
            self.access_token = access_token

            # Initialize HTTP session
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                connector=aiohttp.TCPConnector(limit=100),
            )

            logger.info(f"✅ LTP service initialized for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"❌ LTP service initialization failed: {e}")
            raise

    async def start_dashboard_polling(self, callback_func: Callable):
        """Start polling for dashboard data"""
        if self.polling_active:
            logger.warning("LTP polling already active")
            return

        self.polling_active = True
        self.callback_func = callback_func

        # Start polling task
        self.polling_task = asyncio.create_task(self._polling_loop())

        logger.info("📊 Dashboard LTP polling started")

    async def _polling_loop(self):
        """Main polling loop"""
        while self.polling_active:
            try:
                if not self._is_market_open():
                    await asyncio.sleep(60)
                    continue

                # Get all WebSocket keys from your existing service
                all_instruments = get_fast_retrieval()

                if all_instruments:
                    ltp_data = await self._fetch_all_ltp_data(all_instruments)

                    if ltp_data and self.callback_func:
                        await self.callback_func(ltp_data)

                # Poll every 3 seconds during market hours
                await asyncio.sleep(3)

            except Exception as e:
                logger.error(f"❌ LTP polling error: {e}")
                await asyncio.sleep(10)

    async def _fetch_all_ltp_data(self, instrument_keys: List[str]) -> List[Dict]:
        """Fetch LTP data for all instruments"""
        all_data = []

        # Split into batches
        batches = [
            instrument_keys[i : i + self.batch_size]
            for i in range(0, len(instrument_keys), self.batch_size)
        ]

        for batch in batches:
            try:
                batch_data = await self._fetch_ltp_batch(batch)
                all_data.extend(batch_data)
                await asyncio.sleep(1)  # Rate limiting

            except Exception as e:
                logger.error(f"❌ Batch fetch failed: {e}")
                continue

        return all_data

    async def _fetch_ltp_batch(self, instrument_keys: List[str]) -> List[Dict]:
        """Fetch LTP batch"""
        try:
            instrument_string = ",".join(instrument_keys)
            url = f"{self.base_url}?instrument_key={instrument_string}"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json",
            }

            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._format_ltp_data(data.get("data", {}))
                else:
                    logger.error(f"❌ LTP API error: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"❌ LTP batch fetch error: {e}")
            return []

    def _format_ltp_data(self, raw_data: Dict) -> List[Dict]:
        """Format LTP data"""
        formatted_data = []

        for instrument_key, data in raw_data.items():
            try:
                # Use your existing service to get stock info
                stock_info = get_fast_retrieval.get_stock_from_instrument_key(
                    instrument_key
                )
                symbol = (
                    stock_info.get("symbol")
                    if stock_info
                    else self._extract_symbol(instrument_key)
                )

                formatted_item = {
                    "instrument_key": instrument_key,
                    "symbol": symbol,
                    "ltp": data.get("last_price", 0),
                    "change": self._calculate_change(data),
                    "change_percent": self._calculate_change_percent(data),
                    "timestamp": datetime.now().isoformat(),
                    "data_source": "LTP_API",
                }

                formatted_data.append(formatted_item)

            except Exception as e:
                logger.warning(f"Error formatting data for {instrument_key}: {e}")
                continue

        return formatted_data

    def _extract_symbol(self, instrument_key: str) -> str:
        """Extract symbol from instrument key"""
        try:
            return (
                instrument_key.split("|")[1]
                if "|" in instrument_key
                else instrument_key
            )
        except:
            return instrument_key

    def _calculate_change(self, data: Dict) -> float:
        """Calculate price change"""
        try:
            current = data.get("last_price", 0)
            previous = data.get("previous_close", 0)
            return current - previous
        except:
            return 0

    def _calculate_change_percent(self, data: Dict) -> float:
        """Calculate percentage change"""
        try:
            current = data.get("last_price", 0)
            previous = data.get("previous_close", 0)
            if previous == 0:
                return 0
            return ((current - previous) / previous) * 100
        except:
            return 0

    def _is_market_open(self) -> bool:
        """Check if market is open"""
        now = datetime.now()
        current_time = now.time()

        if now.weekday() >= 5:  # Weekend
            return False

        market_open = time(9, 15)
        market_close = time(15, 30)

        return market_open <= current_time <= market_close

    async def stop_polling(self):
        """Stop LTP polling"""
        self.polling_active = False

        if self.polling_task:
            self.polling_task.cancel()

        if self.session:
            await self.session.close()

        logger.info("⏹️ LTP polling stopped")

    def _get_all_instrument_keys(self) -> List[str]:
        """ENHANCED: Get all instrument keys using OptimizedInstrumentService"""
        try:
            # INTEGRATION: Use your OptimizedInstrumentService
            from services.optimized_instrument_service import fast_retrieval

            # Get all WebSocket keys for dashboard
            all_keys = fast_retrieval.get_all_websocket_keys()
            if all_keys:
                logger.info(
                    f"📊 Retrieved {len(all_keys)} instruments from OptimizedInstrumentService"
                )
                return all_keys

            # Fallback: Try cached dashboard instruments
            import redis

            redis_client = redis.Redis(
                host="localhost", port=6379, db=0, decode_responses=True
            )
            cached = redis_client.get("dashboard_instruments_cache")
            if cached:
                data = json.loads(cached)
                return data.get("instruments", [])

            # Final fallback: Load from file
            return self._load_from_file()

        except Exception as e:
            logger.error(f"Error getting instrument keys: {e}")
            return []
