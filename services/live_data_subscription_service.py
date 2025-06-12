import asyncio
import logging
from typing import Dict, List, Set
from datetime import datetime
from services.upstox.ws_client import UpstoxWebSocketClient
from utils.instrument_key_cache import save_instrument_keys

logger = logging.getLogger(__name__)


class LiveDataSubscriptionService:
    def __init__(self):
        self.subscribed_instruments = set()
        self.active_connections = {}
        self.subscription_callbacks = {}

    async def subscribe_selected_stocks(self, selected_stocks: Dict, access_token: str):
        """
        ENHANCED: Use cached instruments and integrate with LiveTradingEngine
        """
        try:
            # Get cached trading instruments (from MarketScheduleService)
            trading_instruments = await self._get_cached_trading_instruments()

            if not trading_instruments:
                logger.warning("No cached trading instruments, generating fallback")
                # Your existing fallback logic
                trading_instruments = await self._generate_instruments_fallback(
                    selected_stocks
                )

            # Save for WebSocket use (your existing logic)
            save_instrument_keys(trading_instruments)

            # Create WebSocket connection (your existing logic)
            ws_client = UpstoxWebSocketClient(
                access_token=access_token,
                instrument_keys=trading_instruments,
                callback=self._handle_live_data_with_trading,  # ENHANCED callback
                on_auth_error=self._handle_auth_error,
            )

            await ws_client.connect_and_stream()

            logger.info(
                f"📡 Subscribed to {len(trading_instruments)} focused trading instruments"
            )

        except Exception as e:
            logger.error(f"❌ Live data subscription failed: {e}")
            raise

    async def _handle_live_data_with_trading(self, data: Dict):
        """Enhanced callback that feeds data to both dashboard and trading engine"""
        try:
            # KEEP: Your existing live data handling
            await self._handle_live_data(data)  # Your existing method

            # NEW: Feed data to LiveTradingEngine instances
            if data.get("type") == "live_feed" and data.get("data"):
                await self._feed_to_trading_engines(data["data"])

        except Exception as e:
            logger.error(f"❌ Enhanced live data handling failed: {e}")

    async def _feed_to_trading_engines(self, feeds: Dict):
        """Feed live data to all active LiveTradingEngine instances"""
        try:
            # Get active trading engines from TradingEngine
            from services.trading_services.trading_engine import trading_engine

            if hasattr(trading_engine, "live_trading_engines"):
                for user_id, engine in trading_engine.live_trading_engines.items():
                    try:
                        # Feed each tick to the trading engine
                        for instrument_key, tick_data in feeds.items():
                            await engine.process_live_tick(instrument_key, tick_data)
                    except Exception as e:
                        logger.error(f"Error feeding data to engine {user_id}: {e}")

        except Exception as e:
            logger.error(f"Error feeding to trading engines: {e}")

    async def _get_cached_trading_instruments(self):
        """Get cached trading instruments"""
        try:
            import redis
            import json

            redis_client = redis.Redis(
                host="localhost", port=6379, db=0, decode_responses=True
            )
            cached = redis_client.get("selected_trading_instruments")

            if cached:
                return json.loads(cached)

        except Exception as e:
            logger.error(f"Error getting cached instruments: {e}")

        return []

    def _process_tick_data(self, instrument_key: str, tick_data: Dict) -> Dict:
        """Process raw tick data"""
        try:
            return {
                "instrument_key": instrument_key,
                "ltp": tick_data.get("ltp"),
                "ltq": tick_data.get("ltq"),
                "ltt": tick_data.get("ltt"),
                "volume": tick_data.get("volume"),
                "bid_price": tick_data.get("bid_price"),
                "ask_price": tick_data.get("ask_price"),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"❌ Tick data processing failed: {e}")
            return {}

    async def _broadcast_tick_data(self, instrument_key: str, tick_data: Dict):
        """Broadcast tick data to all subscribers"""
        try:
            # Notify dashboard subscribers
            if hasattr(self, "dashboard_callbacks"):
                for callback in self.dashboard_callbacks:
                    try:
                        await callback(instrument_key, tick_data)
                    except Exception as e:
                        logger.error(f"❌ Dashboard callback failed: {e}")

            # Notify trading engine
            if hasattr(self, "trading_callbacks"):
                for callback in self.trading_callbacks:
                    try:
                        await callback(instrument_key, tick_data)
                    except Exception as e:
                        logger.error(f"❌ Trading callback failed: {e}")

        except Exception as e:
            logger.error(f"❌ Broadcast failed for {instrument_key}: {e}")

    async def _handle_market_status(self, data: Dict):
        """Handle market status updates"""
        try:
            status = data.get("status", "")
            logger.info(f"📊 Market status: {status}")

            if status in ["NORMAL_CLOSE", "CLOSING_END"]:
                # Market closed - stop subscriptions
                await self.stop_all_subscriptions()

        except Exception as e:
            logger.error(f"❌ Market status handling failed: {e}")

    async def _handle_auth_error(self):
        """Handle authentication errors"""
        logger.error("🔐 WebSocket authentication failed")
        # Implement token refresh logic here

    async def stop_all_subscriptions(self):
        """Stop all active subscriptions"""
        try:
            for connection in self.active_connections.values():
                connection.stop()

            self.active_connections.clear()
            self.subscribed_instruments.clear()

            logger.info("⏹️ All subscriptions stopped")

        except Exception as e:
            logger.error(f"❌ Failed to stop subscriptions: {e}")
