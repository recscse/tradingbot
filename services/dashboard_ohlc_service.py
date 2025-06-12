import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List
import yfinance as yf
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)


class DashboardOHLCService:
    def __init__(self):
        self.ohlc_cache = {}
        self.cache_file = Path("data/dashboard_ohlc.json")
        self.polling_active = False

    async def start_ohlc_polling(self, selected_stocks: Dict):
        """Start OHLC polling for selected stocks"""
        self.polling_active = True
        logger.info("📊 Starting OHLC polling for dashboard")

        while self.polling_active:
            try:
                await self._update_ohlc_data(selected_stocks)
                await asyncio.sleep(30)  # Update every 30 seconds

            except Exception as e:
                logger.error(f"❌ OHLC polling error: {e}")
                await asyncio.sleep(60)

    async def _update_ohlc_data(self, selected_stocks: Dict):
        """Update OHLC data for all selected stocks"""
        try:
            updated_data = {}

            for symbol, stock_data in selected_stocks.items():
                try:
                    # Get intraday data
                    ticker = f"{symbol}.NS"
                    data = yf.download(ticker, period="1d", interval="1m")

                    if not data.empty:
                        # Calculate current day OHLC
                        current_ohlc = {
                            "symbol": symbol,
                            "open": float(data["Open"].iloc[0]),
                            "high": float(data["High"].max()),
                            "low": float(data["Low"].min()),
                            "close": float(data["Close"].iloc[-1]),
                            "volume": int(data["Volume"].sum()),
                            "timestamp": datetime.now().isoformat(),
                            "change": float(
                                data["Close"].iloc[-1] - data["Open"].iloc[0]
                            ),
                            "change_percent": float(
                                (
                                    (data["Close"].iloc[-1] - data["Open"].iloc[0])
                                    / data["Open"].iloc[0]
                                )
                                * 100
                            ),
                        }

                        # Add technical levels
                        current_ohlc.update(self._calculate_support_resistance(data))

                        updated_data[symbol] = current_ohlc

                except Exception as e:
                    logger.error(f"❌ OHLC update failed for {symbol}: {e}")
                    continue

            # Update cache
            self.ohlc_cache = updated_data

            # Save to file for persistence
            await self._save_ohlc_cache()

            logger.info(f"📊 Updated OHLC for {len(updated_data)} stocks")

        except Exception as e:
            logger.error(f"❌ OHLC data update failed: {e}")

    def _calculate_support_resistance(self, data: pd.DataFrame) -> Dict:
        """Calculate support and resistance levels"""
        try:
            # Simple pivot-based support/resistance
            highs = data["High"].rolling(window=5, center=True).max()
            lows = data["Low"].rolling(window=5, center=True).min()

            resistance_levels = highs[highs == data["High"]].dropna().tail(3)
            support_levels = lows[lows == data["Low"]].dropna().tail(3)

            return {
                "resistance_levels": resistance_levels.tolist(),
                "support_levels": support_levels.tolist(),
                "pivot_point": float(
                    (data["High"].max() + data["Low"].min() + data["Close"].iloc[-1])
                    / 3
                ),
            }

        except Exception as e:
            logger.error(f"❌ Support/resistance calculation failed: {e}")
            return {"resistance_levels": [], "support_levels": [], "pivot_point": 0}

    async def _save_ohlc_cache(self):
        """Save OHLC cache to file"""
        try:
            with open(self.cache_file, "w") as f:
                json.dump(self.ohlc_cache, f, indent=2)

        except Exception as e:
            logger.error(f"❌ Failed to save OHLC cache: {e}")

    def get_ohlc_data(self, symbol: str = None) -> Dict:
        """Get OHLC data for specific symbol or all"""
        if symbol:
            return self.ohlc_cache.get(symbol, {})
        return self.ohlc_cache

    def stop_polling(self):
        """Stop OHLC polling"""
        self.polling_active = False
        logger.info("⏹️ OHLC polling stopped")
