"""
MCX WebSocket Client - Modular structure with numpy/pandas integration
"""

import asyncio
import json
import ssl
import logging
import requests
import websockets
import traceback
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable, Any
from google.protobuf.json_format import MessageToDict
import services.upstox.MarketDataFeed_pb2 as pb

logger = logging.getLogger(__name__)


class MCXDataProcessor:
    """Handles data processing with numpy/pandas"""

    def __init__(self):
        self.price_data_df: Optional[pd.DataFrame] = None
        self.futures_chain_df: Optional[pd.DataFrame] = None
        self.volume_data_df: Optional[pd.DataFrame] = None
        self.last_update = datetime.now()

    def process_live_feed(self, mcx_feeds: Dict) -> Dict[str, pd.DataFrame]:
        """Process live MCX feed data into structured DataFrames"""
        try:
            processed_data = []

            for instrument_key, feed_data in mcx_feeds.items():
                if "fullFeed" in feed_data and "marketFF" in feed_data["fullFeed"]:
                    market_ff = feed_data["fullFeed"]["marketFF"]
                    ltpc = market_ff.get("ltpc", {})

                    # Extract all available data
                    data_row = {
                        'instrument_key': instrument_key,
                        'timestamp': datetime.now(),
                        'ltp': self._safe_float(ltpc.get('ltp')),
                        'cp': self._safe_float(ltpc.get('cp')),
                        'volume': self._safe_float(market_ff.get('tbq')),
                        'symbol': self._extract_symbol(instrument_key),
                        'exchange_token': self._extract_token(instrument_key)
                    }

                    # Calculate derived metrics
                    if data_row['ltp'] and data_row['cp'] and data_row['cp'] != 0:
                        data_row['change'] = data_row['ltp'] - data_row['cp']
                        data_row['change_percent'] = (data_row['change'] / data_row['cp']) * 100
                    else:
                        data_row['change'] = np.nan
                        data_row['change_percent'] = np.nan

                    # Extract OHLC if available
                    ohlc_data = market_ff.get('marketOHLC', {}).get('ohlc', [])
                    if ohlc_data and len(ohlc_data) > 0:
                        daily_ohlc = next((item for item in ohlc_data if item.get('interval') == '1d'), {})
                        data_row.update({
                            'open': self._safe_float(daily_ohlc.get('open')),
                            'high': self._safe_float(daily_ohlc.get('high')),
                            'low': self._safe_float(daily_ohlc.get('low')),
                            'close': self._safe_float(daily_ohlc.get('close'))
                        })

                    # Extract bid/ask data
                    bid_ask = market_ff.get('marketLevel', {}).get('bidAskQuote', [])
                    if bid_ask and len(bid_ask) > 0 and bid_ask[0]:
                        first_level = bid_ask[0]
                        data_row.update({
                            'bid_price': self._safe_float(first_level.get('bidP')),
                            'bid_qty': self._safe_float(first_level.get('bidQ')),
                            'ask_price': self._safe_float(first_level.get('askP')),
                            'ask_qty': self._safe_float(first_level.get('askQ'))
                        })

                    processed_data.append(data_row)

            # Create DataFrames
            if processed_data:
                current_df = pd.DataFrame(processed_data)

                # Update price data DataFrame
                self._update_price_dataframe(current_df)

                # Update futures chain DataFrame
                self._update_futures_chain_dataframe(current_df)

                # Update volume data DataFrame
                self._update_volume_dataframe(current_df)

                self.last_update = datetime.now()

                return {
                    'price_data': self.price_data_df,
                    'futures_chain': self.futures_chain_df,
                    'volume_data': self.volume_data_df,
                    'current_snapshot': current_df
                }

            return {}

        except Exception as e:
            logger.error(f"Error processing live feed: {e}")
            return {}

    def _update_price_dataframe(self, current_df: pd.DataFrame):
        """Update the main price data DataFrame"""
        try:
            if self.price_data_df is None:
                self.price_data_df = current_df.copy()
            else:
                # Append new data
                self.price_data_df = pd.concat([self.price_data_df, current_df], ignore_index=True)

                # Keep only last 1000 records per instrument to manage memory
                self.price_data_df = self.price_data_df.groupby('instrument_key').tail(1000).reset_index(drop=True)

        except Exception as e:
            logger.error(f"Error updating price DataFrame: {e}")

    def _update_futures_chain_dataframe(self, current_df: pd.DataFrame):
        """Update futures chain DataFrame grouped by underlying symbol"""
        try:
            # Group by symbol and create futures chain structure
            futures_data = []

            for symbol, group in current_df.groupby('symbol'):
                if symbol and symbol != 'UNKNOWN':
                    for _, row in group.iterrows():
                        chain_row = {
                            'symbol': symbol,
                            'instrument_key': row['instrument_key'],
                            'ltp': row['ltp'],
                            'change': row['change'],
                            'change_percent': row['change_percent'],
                            'volume': row['volume'],
                            'timestamp': row['timestamp']
                        }
                        futures_data.append(chain_row)

            if futures_data:
                new_chain_df = pd.DataFrame(futures_data)

                if self.futures_chain_df is None:
                    self.futures_chain_df = new_chain_df
                else:
                    # Update existing data
                    self.futures_chain_df = pd.concat([self.futures_chain_df, new_chain_df], ignore_index=True)

                    # Keep latest data per instrument
                    self.futures_chain_df = self.futures_chain_df.drop_duplicates(
                        subset=['instrument_key'], keep='last'
                    ).reset_index(drop=True)

        except Exception as e:
            logger.error(f"Error updating futures chain DataFrame: {e}")

    def _update_volume_dataframe(self, current_df: pd.DataFrame):
        """Update volume analysis DataFrame"""
        try:
            volume_data = current_df[['symbol', 'instrument_key', 'volume', 'timestamp']].copy()
            volume_data = volume_data.dropna(subset=['volume'])

            if len(volume_data) > 0:
                if self.volume_data_df is None:
                    self.volume_data_df = volume_data
                else:
                    self.volume_data_df = pd.concat([self.volume_data_df, volume_data], ignore_index=True)

                    # Keep only recent volume data
                    cutoff_time = datetime.now() - timedelta(hours=1)
                    self.volume_data_df = self.volume_data_df[
                        self.volume_data_df['timestamp'] > cutoff_time
                    ].reset_index(drop=True)

        except Exception as e:
            logger.error(f"Error updating volume DataFrame: {e}")

    def get_analytics(self) -> Dict[str, Any]:
        """Get analytics from the processed data"""
        try:
            analytics = {}

            if self.price_data_df is not None and len(self.price_data_df) > 0:
                # Basic statistics
                analytics['total_instruments'] = self.price_data_df['instrument_key'].nunique()
                analytics['total_symbols'] = self.price_data_df['symbol'].nunique()

                # Price analytics
                latest_prices = self.price_data_df.groupby('instrument_key').last()
                analytics['price_stats'] = {
                    'avg_change_percent': latest_prices['change_percent'].mean(),
                    'max_change_percent': latest_prices['change_percent'].max(),
                    'min_change_percent': latest_prices['change_percent'].min(),
                    'top_gainers': latest_prices.nlargest(5, 'change_percent')[['symbol', 'change_percent']].to_dict('records'),
                    'top_losers': latest_prices.nsmallest(5, 'change_percent')[['symbol', 'change_percent']].to_dict('records')
                }

            if self.volume_data_df is not None and len(self.volume_data_df) > 0:
                # Volume analytics
                volume_stats = self.volume_data_df.groupby('symbol')['volume'].sum().sort_values(ascending=False)
                analytics['volume_stats'] = {
                    'top_volume_symbols': volume_stats.head(10).to_dict(),
                    'total_volume': volume_stats.sum()
                }

            if self.futures_chain_df is not None and len(self.futures_chain_df) > 0:
                # Futures chain analytics
                chain_stats = self.futures_chain_df.groupby('symbol').agg({
                    'instrument_key': 'count',
                    'change_percent': 'mean'
                }).rename(columns={'instrument_key': 'contract_count', 'change_percent': 'avg_change'})

                analytics['futures_chain_stats'] = chain_stats.to_dict('index')

            analytics['last_update'] = self.last_update.isoformat()

            return analytics

        except Exception as e:
            logger.error(f"Error generating analytics: {e}")
            return {}

    def get_symbol_data(self, symbol: str) -> Dict[str, pd.DataFrame]:
        """Get all data for a specific symbol"""
        try:
            result = {}

            if self.price_data_df is not None:
                result['price_data'] = self.price_data_df[
                    self.price_data_df['symbol'] == symbol
                ].copy()

            if self.futures_chain_df is not None:
                result['futures_chain'] = self.futures_chain_df[
                    self.futures_chain_df['symbol'] == symbol
                ].copy()

            if self.volume_data_df is not None:
                result['volume_data'] = self.volume_data_df[
                    self.volume_data_df['symbol'] == symbol
                ].copy()

            return result

        except Exception as e:
            logger.error(f"Error getting symbol data: {e}")
            return {}

    def export_to_csv(self, base_path: str = "data/mcx_export"):
        """Export DataFrames to CSV files"""
        try:
            import os
            os.makedirs(base_path, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            if self.price_data_df is not None:
                self.price_data_df.to_csv(f"{base_path}/mcx_prices_{timestamp}.csv", index=False)

            if self.futures_chain_df is not None:
                self.futures_chain_df.to_csv(f"{base_path}/mcx_futures_chain_{timestamp}.csv", index=False)

            if self.volume_data_df is not None:
                self.volume_data_df.to_csv(f"{base_path}/mcx_volume_{timestamp}.csv", index=False)

            logger.info(f"Data exported to {base_path}")

        except Exception as e:
            logger.error(f"Error exporting data: {e}")

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        """Safely convert value to float"""
        try:
            return float(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _extract_symbol(instrument_key: str) -> str:
        """Extract symbol from instrument key"""
        try:
            # Enhanced symbol mapping for MCX
            mcx_mapping = {
                "463598": "CRUDEOIL",
                "114": "GOLD",
                "447500": "GOLD",
                # Add more mappings from mcx_instruments.json
            }

            if "|" in instrument_key:
                key_part = instrument_key.split("|")[1]
                return mcx_mapping.get(key_part, f"MCX_{key_part}")

            return "UNKNOWN"

        except Exception:
            return "UNKNOWN"

    @staticmethod
    def _extract_token(instrument_key: str) -> str:
        """Extract exchange token from instrument key"""
        try:
            if "|" in instrument_key:
                return instrument_key.split("|")[1]
            return instrument_key
        except Exception:
            return ""


class MCXWebSocketClient:
    """Enhanced MCX WebSocket client with pandas/numpy integration"""

    def __init__(self, callback: Optional[Callable] = None):
        self.access_token: Optional[str] = None
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.callback = callback or self._default_callback
        self.is_running = False
        self.mcx_instruments: List[str] = []
        self.retry_count = 0
        self.max_retries = 5

        # Data processor with pandas/numpy
        self.data_processor = MCXDataProcessor()

        # Performance metrics
        self.stats = {
            'messages_received': 0,
            'last_message_time': None,
            'connection_start_time': None,
            'errors': 0
        }

    async def initialize(self) -> bool:
        """Initialize the MCX WebSocket client"""
        try:
            logger.info("🔧 Initializing MCX WebSocket client...")

            # Get access token
            if not await self._get_access_token():
                return False

            # Load MCX instruments
            if not await self._load_mcx_instruments():
                return False

            logger.info("✅ MCX WebSocket client initialized successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to initialize MCX client: {e}")
            return False

    async def _get_access_token(self) -> bool:
        """Get access token from database"""
        try:
            from database.connection import SessionLocal
            from database.models import BrokerConfig
            from core.config import ADMIN_EMAIL

            with SessionLocal() as db:
                config = db.query(BrokerConfig).filter_by(
                    user_email=ADMIN_EMAIL,
                    broker="upstox"
                ).first()

                if config and config.access_token:
                    # Check if token is still valid
                    if config.access_token_expiry and datetime.now() < config.access_token_expiry:
                        self.access_token = config.access_token
                        logger.info("✅ Using valid access token from database")
                        return True
                    else:
                        logger.warning("⚠️ Access token expired, needs refresh")
                        return False
                else:
                    logger.error("❌ No access token found in database")
                    return False

        except Exception as e:
            logger.error(f"❌ Error getting access token: {e}")
            return False

    async def _load_mcx_instruments(self) -> bool:
        """Load MCX instrument keys using pandas"""
        try:
            import json
            from pathlib import Path

            # Load from mcx_instruments.json using pandas
            data_path = Path("data/mcx_instruments.json")
            if data_path.exists():
                with open(data_path, 'r', encoding='utf-8') as f:
                    instruments_data = json.load(f)

                # Convert to DataFrame for easier processing
                instruments_df = pd.DataFrame(instruments_data)

                # Filter MCX_FO instruments
                mcx_df = instruments_df[instruments_df['segment'] == 'MCX_FO'].copy()

                # Extract instrument keys
                self.mcx_instruments = mcx_df['instrument_key'].tolist()[:50]  # Limit for testing

                logger.info(f"✅ Loaded {len(self.mcx_instruments)} MCX instruments using pandas")
                logger.info(f"📊 Unique symbols: {mcx_df['underlying_symbol'].nunique()}")

                return True
            else:
                # Fallback instruments
                self.mcx_instruments = ["MCX_FO|463598", "MCX_COM|114"]
                logger.warning("⚠️ Using fallback MCX instruments")
                return True

        except Exception as e:
            logger.error(f"❌ Error loading MCX instruments: {e}")
            return False

    async def start(self) -> bool:
        """Start the MCX WebSocket connection"""
        try:
            if not self.access_token:
                logger.error("❌ No access token available")
                return False

            logger.info("🚀 Starting MCX WebSocket connection...")

            # Get WebSocket URL
            ws_url = await self._get_websocket_url()
            if not ws_url:
                return False

            self.is_running = True
            self.stats['connection_start_time'] = datetime.now()

            # Start WebSocket connection
            await self._connect_websocket(ws_url)

        except Exception as e:
            logger.error(f"❌ Error starting MCX WebSocket: {e}")
            self.stats['errors'] += 1
            return False

    async def _get_websocket_url(self) -> Optional[str]:
        """Get WebSocket URL from Upstox API"""
        try:
            url = "https://api.upstox.com/v3/feed/market-data-feed/authorize"
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {self.access_token}"
            }

            response = requests.get(url, headers=headers)
            logger.info(f"📡 WebSocket auth response: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    ws_url = data["data"]["authorized_redirect_uri"]
                    logger.info("✅ Got WebSocket URL successfully")
                    return ws_url
                else:
                    logger.error(f"❌ Auth failed: {data.get('errors', 'Unknown error')}")
                    return None
            else:
                logger.error(f"❌ HTTP error: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"❌ Error getting WebSocket URL: {e}")
            return None

    async def _connect_websocket(self, ws_url: str):
        """Connect to WebSocket and handle data"""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        try:
            async with websockets.connect(ws_url, ssl=ssl_context) as websocket:
                self.websocket = websocket
                logger.info("✅ MCX WebSocket connection established")

                # Subscribe to MCX instruments
                await self._subscribe_to_instruments()

                # Listen for messages
                await self._listen_for_messages()

        except Exception as e:
            logger.error(f"❌ WebSocket connection error: {e}")
            self.stats['errors'] += 1

            if self.retry_count < self.max_retries:
                self.retry_count += 1
                logger.info(f"🔄 Retrying connection... ({self.retry_count}/{self.max_retries})")
                await asyncio.sleep(5)
                await self.start()

    async def _subscribe_to_instruments(self):
        """Subscribe to MCX instruments"""
        try:
            if not self.mcx_instruments:
                logger.warning("⚠️ No MCX instruments to subscribe to")
                return

            # Wait a moment after connection
            await asyncio.sleep(1)

            subscription_data = {
                "guid": f"mcx_client_{datetime.now().timestamp()}",
                "method": "sub",
                "data": {
                    "mode": "full",
                    "instrumentKeys": self.mcx_instruments
                }
            }

            binary_data = json.dumps(subscription_data).encode('utf-8')
            await self.websocket.send(binary_data)

            logger.info(f"📡 Subscribed to {len(self.mcx_instruments)} MCX instruments")

        except Exception as e:
            logger.error(f"❌ Error subscribing to instruments: {e}")

    async def _listen_for_messages(self):
        """Listen for incoming WebSocket messages"""
        try:
            while self.is_running:
                try:
                    message = await self.websocket.recv()

                    # Update stats
                    self.stats['messages_received'] += 1
                    self.stats['last_message_time'] = datetime.now()

                    # Decode protobuf message
                    decoded_data = self._decode_protobuf(message)
                    if decoded_data:
                        # Process MCX data with pandas/numpy
                        await self._process_mcx_data(decoded_data)

                except websockets.exceptions.ConnectionClosed:
                    logger.warning("⚠️ WebSocket connection closed")
                    break
                except Exception as e:
                    logger.error(f"❌ Error processing message: {e}")
                    self.stats['errors'] += 1
                    continue

        except Exception as e:
            logger.error(f"❌ Error in message listener: {e}")

    def _decode_protobuf(self, buffer) -> Optional[Dict]:
        """Decode protobuf message to dictionary"""
        try:
            feed_response = pb.FeedResponse()
            feed_response.ParseFromString(buffer)
            return MessageToDict(feed_response)
        except Exception as e:
            logger.debug(f"Error decoding protobuf: {e}")
            return None

    async def _process_mcx_data(self, data: Dict):
        """Process MCX market data with pandas/numpy"""
        try:
            # Check if this is MCX live feed data
            if data.get("type") == "live_feed" and "feeds" in data:
                mcx_feeds = {}

                # Filter only MCX instruments
                for instrument_key, feed_data in data["feeds"].items():
                    if instrument_key.startswith("MCX_"):
                        mcx_feeds[instrument_key] = feed_data

                if mcx_feeds:
                    # Process data with pandas/numpy
                    processed_dataframes = self.data_processor.process_live_feed(mcx_feeds)

                    # Call callback with processed data
                    enhanced_data = {
                        "type": "mcx_live_feed",
                        "feeds": mcx_feeds,
                        "timestamp": data.get("currentTs", str(int(datetime.now().timestamp() * 1000))),
                        "count": len(mcx_feeds),
                        "dataframes": processed_dataframes,
                        "analytics": self.data_processor.get_analytics()
                    }

                    await self.callback(enhanced_data)

                    logger.debug(f"📊 Processed {len(mcx_feeds)} MCX instruments with pandas/numpy")

        except Exception as e:
            logger.error(f"❌ Error processing MCX data: {e}")
            self.stats['errors'] += 1

    async def _default_callback(self, data: Dict):
        """Default callback with enhanced data display"""
        try:
            print(f"\n{'='*60}")
            print("MCX LIVE DATA WITH PANDAS/NUMPY ANALYTICS")
            print(f"{'='*60}")

            print(f"📊 Instruments: {data.get('count')}")
            print(f"⏰ Timestamp: {data.get('timestamp')}")

            # Display analytics
            analytics = data.get('analytics', {})
            if analytics:
                print(f"\n📈 ANALYTICS:")
                print(f"  Total Instruments: {analytics.get('total_instruments', 0)}")
                print(f"  Total Symbols: {analytics.get('total_symbols', 0)}")

                price_stats = analytics.get('price_stats', {})
                if price_stats:
                    print(f"  Avg Change %: {price_stats.get('avg_change_percent', 0):.2f}%")

                    top_gainers = price_stats.get('top_gainers', [])
                    if top_gainers:
                        print(f"  Top Gainer: {top_gainers[0].get('symbol')} ({top_gainers[0].get('change_percent', 0):.2f}%)")

            # Display sample data
            feeds = data.get('feeds', {})
            for i, (instrument_key, feed_data) in enumerate(list(feeds.items())[:3]):
                if "fullFeed" in feed_data and "marketFF" in feed_data["fullFeed"]:
                    market_ff = feed_data["fullFeed"]["marketFF"]
                    ltpc = market_ff.get("ltpc", {})

                    print(f"\n📍 {instrument_key}:")
                    print(f"  LTP: {ltpc.get('ltp')}")
                    print(f"  Previous Close: {ltpc.get('cp')}")
                    print(f"  Volume: {market_ff.get('tbq')}")

            print(f"\n{'='*60}")

        except Exception as e:
            logger.error(f"Error in default callback: {e}")

    def get_data_summary(self) -> Dict:
        """Get comprehensive data summary"""
        return {
            "stats": self.stats,
            "analytics": self.data_processor.get_analytics(),
            "instruments_count": len(self.mcx_instruments),
            "is_running": self.is_running
        }

    def get_symbol_dataframes(self, symbol: str) -> Dict[str, pd.DataFrame]:
        """Get all DataFrames for a specific symbol"""
        return self.data_processor.get_symbol_data(symbol)

    def export_data(self, base_path: str = "data/mcx_export"):
        """Export all data to CSV files"""
        self.data_processor.export_to_csv(base_path)

    async def stop(self):
        """Stop the MCX WebSocket client"""
        logger.info("🛑 Stopping MCX WebSocket client")
        self.is_running = False

        if self.websocket:
            await self.websocket.close()
            self.websocket = None


# Singleton instance
mcx_client = MCXWebSocketClient()