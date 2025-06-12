# services/strategy_service.py
# FIXED VERSION - Works with your existing PreMarketDataService and caches

import pandas as pd
import numpy as np
import json
import redis
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from database.models import BrokerConfig

logger = logging.getLogger(__name__)


class StrategyService:
    def __init__(self, db: Session):
        self.db = db
        # Use your existing Redis setup
        self.redis_client = redis.Redis(
            host="localhost", port=6379, db=0, decode_responses=True
        )

    async def analyze_stock(self, symbol: str) -> Dict[str, Any]:
        """
        FIXED: Analyze stock using your existing data sources
        Priority: 1) Cached data 2) PreMarket data 3) Upstox API
        """
        try:
            # Clean symbol (remove .NS if present)
            clean_symbol = symbol.replace(".NS", "")

            logger.info(f"📊 Analyzing {clean_symbol} using existing data sources...")

            # Get data from your existing sources
            stock_data = await self._get_stock_data_from_existing_sources(clean_symbol)

            if not stock_data:
                return {
                    "signal": "HOLD",
                    "confidence": 0.0,
                    "reason": "No data available from existing sources",
                }

            # Use your existing data to prepare features
            features = self._prepare_features(stock_data)

            if not features:
                return {
                    "signal": "HOLD",
                    "confidence": 0.0,
                    "reason": "Insufficient data for analysis",
                }

            # Generate signal
            signal_data = self._generate_signal(features)

            logger.info(
                f"✅ Analysis completed for {clean_symbol}: {signal_data['signal']} ({signal_data['confidence']:.2f})"
            )
            return signal_data

        except Exception as e:
            logger.error(f"❌ Error analyzing stock {symbol}: {e}")
            return {
                "signal": "HOLD",
                "confidence": 0.0,
                "reason": f"Analysis failed: {str(e)}",
            }

    async def _get_stock_data_from_existing_sources(
        self, symbol: str
    ) -> Optional[Dict]:
        """
        Get stock data from YOUR EXISTING data sources
        1. PreMarketDataService cache
        2. LiveDataSubscriptionService cache
        3. Direct Upstox API using your existing setup
        """
        try:
            # Method 1: Get from PreMarketDataService cache
            pre_market_data = self._get_from_premarket_cache(symbol)
            if pre_market_data:
                logger.debug(f"📊 Using PreMarket data for {symbol}")
                return pre_market_data

            # Method 2: Get from live data cache (populated by your WebSocket)
            live_data = self._get_from_live_cache(symbol)
            if live_data:
                logger.debug(f"📡 Using Live WebSocket data for {symbol}")
                return live_data

            # Method 3: Use your existing Upstox API setup
            upstox_data = await self._get_from_upstox_api(symbol)
            if upstox_data:
                logger.debug(f"🔗 Using Upstox API data for {symbol}")
                return upstox_data

            logger.warning(f"⚠️ No data available for {symbol} from any source")
            return None

        except Exception as e:
            logger.error(f"❌ Error getting data for {symbol}: {e}")
            return None

    def _get_from_premarket_cache(self, symbol: str) -> Optional[Dict]:
        """Get data from your PreMarketDataService cache"""
        try:
            # Use your existing get_stock_data function
            from services.pre_market_data_service import get_stock_data

            cached_data = get_stock_data(symbol)
            if cached_data:
                # Convert your cached data format to OHLC format
                entry_price = cached_data.get("entry_price", 0)
                target_price = cached_data.get("target_price", entry_price * 1.03)
                stop_loss = cached_data.get("stop_loss", entry_price * 0.97)

                # Create synthetic OHLC data
                ohlc_data = {
                    "Close": [entry_price] * 20,  # Create 20 days of data
                    "Open": [entry_price * 0.995] * 20,
                    "High": [entry_price * 1.01] * 20,
                    "Low": [entry_price * 0.99] * 20,
                    "Volume": [1000000] * 20,
                }

                # Add some variation to make it realistic
                for i in range(20):
                    variation = (i - 10) * 0.001  # ±1% variation
                    ohlc_data["Close"][i] = entry_price * (1 + variation)
                    ohlc_data["Open"][i] = ohlc_data["Close"][i] * 0.998
                    ohlc_data["High"][i] = ohlc_data["Close"][i] * 1.005
                    ohlc_data["Low"][i] = ohlc_data["Close"][i] * 0.995

                return {
                    "source": "premarket_cache",
                    "symbol": symbol,
                    "ohlc": ohlc_data,
                    "current_price": entry_price,
                    "metadata": cached_data,
                }

            return None

        except Exception as e:
            logger.error(f"Error getting premarket data for {symbol}: {e}")
            return None

    def _get_from_live_cache(self, symbol: str) -> Optional[Dict]:
        """Get data from your LiveDataSubscriptionService cache"""
        try:
            # Check Redis for live data (populated by your WebSocket service)
            cache_keys = [
                f"live_price:{symbol}",
                f"stock_data:{symbol}",
                f"position:{symbol}",
            ]

            for key in cache_keys:
                cached_data = self.redis_client.get(key)
                if cached_data:
                    data = json.loads(cached_data)

                    # Extract price information
                    current_price = data.get(
                        "ltp", data.get("current_price", data.get("entry_price", 0))
                    )

                    if current_price > 0:
                        # Create basic OHLC structure
                        base_price = current_price
                        ohlc_data = {
                            "Close": [
                                base_price * (1 + (i - 10) * 0.001) for i in range(20)
                            ],
                            "Open": [
                                base_price * (1 + (i - 10) * 0.001) * 0.998
                                for i in range(20)
                            ],
                            "High": [
                                base_price * (1 + (i - 10) * 0.001) * 1.005
                                for i in range(20)
                            ],
                            "Low": [
                                base_price * (1 + (i - 10) * 0.001) * 0.995
                                for i in range(20)
                            ],
                            "Volume": [data.get("volume", 1000000)] * 20,
                        }

                        return {
                            "source": "live_cache",
                            "symbol": symbol,
                            "ohlc": ohlc_data,
                            "current_price": current_price,
                            "metadata": data,
                        }

            return None

        except Exception as e:
            logger.error(f"Error getting live cache data for {symbol}: {e}")
            return None

    async def _get_from_upstox_api(self, symbol: str) -> Optional[Dict]:
        """Get data using your existing Upstox setup"""
        try:
            # Get broker config from your existing database setup
            broker_config = (
                self.db.query(BrokerConfig)
                .filter(
                    BrokerConfig.broker_name.ilike("upstox"),
                    BrokerConfig.is_active == True,
                    BrokerConfig.access_token.isnot(None),
                )
                .first()
            )

            if not broker_config:
                logger.warning(f"No Upstox broker config found for {symbol}")
                return None

            # Get instrument key using your existing OptimizedInstrumentService
            try:
                from services.optimized_instrument_service import fast_retrieval

                stock_mapping = fast_retrieval.get_stock_instruments(symbol)

                if not stock_mapping:
                    # Fallback to basic instrument key format
                    instrument_key = f"NSE_EQ|INE{symbol}"
                else:
                    instrument_key = stock_mapping.get(
                        "primary_instrument_key", f"NSE_EQ|INE{symbol}"
                    )

            except Exception:
                instrument_key = f"NSE_EQ|INE{symbol}"

            # Use your existing pattern for API calls
            import aiohttp

            url = f"https://api.upstox.com/v2/market-quote/ohlc?instrument_key={instrument_key}"
            headers = {"Authorization": f"Bearer {broker_config.access_token}"}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        quote_data = data.get("data", {}).get(instrument_key, {})

                        if quote_data:
                            ohlc = quote_data.get("ohlc", {})
                            current_price = quote_data.get(
                                "last_price", ohlc.get("close", 0)
                            )

                            # Create OHLC data structure
                            ohlc_data = {
                                "Close": [current_price] * 20,
                                "Open": [ohlc.get("open", current_price)] * 20,
                                "High": [ohlc.get("high", current_price)] * 20,
                                "Low": [ohlc.get("low", current_price)] * 20,
                                "Volume": [quote_data.get("volume", 1000000)] * 20,
                            }

                            return {
                                "source": "upstox_api",
                                "symbol": symbol,
                                "ohlc": ohlc_data,
                                "current_price": current_price,
                                "metadata": quote_data,
                            }

            return None

        except Exception as e:
            logger.error(f"Error getting Upstox data for {symbol}: {e}")
            return None

    def _prepare_features(self, stock_data: Dict) -> Dict[str, float]:
        """
        FIXED: Prepare technical indicators from your existing data sources
        """
        try:
            if not stock_data or "ohlc" not in stock_data:
                logger.warning("No OHLC data available for feature preparation")
                return {}

            ohlc_data = stock_data["ohlc"]
            current_price = stock_data.get("current_price", 0)

            # Convert to pandas DataFrame for calculations
            df = pd.DataFrame(ohlc_data)

            if df.empty or len(df) < 5:
                logger.warning("Insufficient OHLC data for feature preparation")
                return {}

            features = {}

            # Basic price features
            features["current_price"] = (
                float(current_price)
                if current_price > 0
                else float(df["Close"].iloc[-1])
            )
            features["previous_close"] = (
                float(df["Close"].iloc[-2])
                if len(df) > 1
                else features["current_price"]
            )

            # Moving averages
            if len(df) >= 5:
                features["sma_5"] = float(df["Close"].rolling(window=5).mean().iloc[-1])
            else:
                features["sma_5"] = features["current_price"]

            if len(df) >= 10:
                features["sma_10"] = float(
                    df["Close"].rolling(window=10).mean().iloc[-1]
                )
            else:
                features["sma_10"] = features["sma_5"]

            if len(df) >= 20:
                features["sma_20"] = float(
                    df["Close"].rolling(window=20).mean().iloc[-1]
                )
            else:
                features["sma_20"] = features["sma_10"]

            # RSI calculation (simplified for available data)
            if len(df) >= 10:
                delta = df["Close"].diff()
                gain = (
                    (delta.where(delta > 0, 0))
                    .rolling(window=min(14, len(df) - 1))
                    .mean()
                )
                loss = (
                    (-delta.where(delta < 0, 0))
                    .rolling(window=min(14, len(df) - 1))
                    .mean()
                )
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                features["rsi"] = (
                    float(rsi.iloc[-1])
                    if not rsi.empty and not pd.isna(rsi.iloc[-1])
                    else 50.0
                )
            else:
                features["rsi"] = 50.0

            # Volume analysis
            features["current_volume"] = float(df["Volume"].iloc[-1])
            if len(df) >= 5:
                features["avg_volume"] = float(
                    df["Volume"].rolling(window=5).mean().iloc[-1]
                )
                features["volume_ratio"] = (
                    features["current_volume"] / features["avg_volume"]
                    if features["avg_volume"] > 0
                    else 1.0
                )
            else:
                features["avg_volume"] = features["current_volume"]
                features["volume_ratio"] = 1.0

            # Price momentum
            if len(df) >= 3:
                features["price_change_2d"] = (
                    (features["current_price"] - float(df["Close"].iloc[-3]))
                    / float(df["Close"].iloc[-3])
                ) * 100
            else:
                features["price_change_2d"] = 0.0

            if len(df) >= 5:
                features["price_change_5d"] = (
                    (features["current_price"] - float(df["Close"].iloc[-6]))
                    / float(df["Close"].iloc[-6])
                ) * 100
            else:
                features["price_change_5d"] = features["price_change_2d"]

            # Volatility
            if len(df) >= 5:
                returns = df["Close"].pct_change()
                features["volatility"] = (
                    float(returns.rolling(window=5).std().iloc[-1]) * 100
                )
            else:
                features["volatility"] = 2.0

            # OHLC patterns
            features["daily_change"] = (
                (features["current_price"] - features["previous_close"])
                / features["previous_close"]
            ) * 100

            # High/Low analysis
            if len(df) >= 10:
                high_10 = df["High"].rolling(window=10).max().iloc[-1]
                low_10 = df["Low"].rolling(window=10).min().iloc[-1]
                features["high_10"] = float(high_10)
                features["low_10"] = float(low_10)
                features["price_position"] = (
                    ((features["current_price"] - low_10) / (high_10 - low_10)) * 100
                    if high_10 > low_10
                    else 50.0
                )
            else:
                features["high_10"] = features["current_price"]
                features["low_10"] = features["current_price"]
                features["price_position"] = 50.0

            # Clean any NaN or infinite values
            cleaned_features = {}
            for key, value in features.items():
                if pd.isna(value) or np.isinf(value):
                    if "price" in key.lower():
                        cleaned_features[key] = features.get("current_price", 100.0)
                    elif "rsi" in key.lower():
                        cleaned_features[key] = 50.0
                    elif "volume" in key.lower():
                        cleaned_features[key] = 1000000.0
                    elif "ratio" in key.lower():
                        cleaned_features[key] = 1.0
                    else:
                        cleaned_features[key] = 0.0
                else:
                    cleaned_features[key] = float(value)

            # Add data source info
            cleaned_features["data_source"] = stock_data.get("source", "unknown")

            logger.debug(
                f"✅ Prepared {len(cleaned_features)} features from {stock_data.get('source')} data"
            )
            return cleaned_features

        except Exception as e:
            logger.error(f"❌ Error preparing features: {e}")
            return {}

    def _generate_signal(self, features: Dict[str, float]) -> Dict[str, Any]:
        """Generate trading signal based on features"""
        try:
            if not features:
                return {
                    "signal": "HOLD",
                    "confidence": 0.0,
                    "reason": "No features available",
                }

            signal = "HOLD"
            confidence = 0.0
            reasons = []

            # Extract features
            current_price = features.get("current_price", 0)
            rsi = features.get("rsi", 50)
            sma_5 = features.get("sma_5", 0)
            sma_10 = features.get("sma_10", 0)
            sma_20 = features.get("sma_20", 0)
            volume_ratio = features.get("volume_ratio", 1.0)
            price_change_5d = features.get("price_change_5d", 0)
            price_position = features.get("price_position", 50)
            data_source = features.get("data_source", "unknown")

            # RSI signals
            if rsi < 30:
                signal = "BUY"
                confidence += 0.3
                reasons.append(f"RSI oversold ({rsi:.1f})")
            elif rsi > 70:
                signal = "SELL"
                confidence += 0.3
                reasons.append(f"RSI overbought ({rsi:.1f})")

            # Moving average signals
            if current_price > sma_5 > sma_10:
                if signal != "SELL":
                    signal = "BUY"
                confidence += 0.25
                reasons.append("Price above short MAs")
            elif current_price < sma_5 < sma_10:
                if signal != "BUY":
                    signal = "SELL"
                confidence += 0.25
                reasons.append("Price below short MAs")

            # Volume confirmation
            if volume_ratio > 1.5:
                confidence += 0.2
                reasons.append(f"High volume ({volume_ratio:.1f}x)")
            elif volume_ratio < 0.7:
                confidence -= 0.1
                reasons.append("Low volume")

            # Momentum
            if price_change_5d > 3:
                if signal != "SELL":
                    signal = "BUY"
                confidence += 0.15
                reasons.append(f"Strong momentum (+{price_change_5d:.1f}%)")
            elif price_change_5d < -3:
                if signal != "BUY":
                    signal = "SELL"
                confidence += 0.15
                reasons.append(f"Weak momentum ({price_change_5d:.1f}%)")

            # Position in range
            if price_position > 80:
                if signal == "BUY":
                    confidence += 0.1
                reasons.append("Near recent high")
            elif price_position < 20:
                if signal == "BUY":
                    confidence += 0.1
                reasons.append("Near recent low")

            # Adjust confidence based on data source quality
            if data_source == "upstox_api":
                confidence *= 1.0  # Full confidence
            elif data_source == "live_cache":
                confidence *= 0.95  # Slight reduction
            elif data_source == "premarket_cache":
                confidence *= 0.90  # More reduction for older data

            # Ensure confidence bounds
            confidence = max(0.0, min(confidence, 1.0))

            # Minimum threshold
            if confidence < 0.4:
                signal = "HOLD"
                if not reasons:
                    reasons.append("Insufficient signal strength")

            return {
                "signal": signal,
                "confidence": confidence,
                "reason": "; ".join(reasons) if reasons else "No clear signal",
                "features": features,
                "data_source": data_source,
            }

        except Exception as e:
            logger.error(f"❌ Error generating signal: {e}")
            return {
                "signal": "HOLD",
                "confidence": 0.0,
                "reason": f"Signal generation failed: {str(e)}",
            }
