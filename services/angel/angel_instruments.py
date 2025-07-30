# services/angel/angel_instruments.py
"""
Angel Instruments Service
Downloads and manages Angel Broking instrument master data
"""
import os
import json
import logging
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class AngelInstruments:
    """Manages Angel Broking instruments master data"""

    INSTRUMENTS_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    CACHE_FILE = "data/angel_instruments.json"

    def __init__(self):
        self.instruments_df: Optional[pd.DataFrame] = None
        self.symbol_token_map: Dict[str, str] = {}
        self.token_symbol_map: Dict[str, str] = {}
        self.last_refresh: Optional[datetime] = None

        # Ensure data directory exists
        Path("data").mkdir(exist_ok=True)

        logger.info("🔧 Angel Instruments service initialized")

    def should_refresh(self) -> bool:
        """Check if instruments should be refreshed (daily)"""
        if not self.last_refresh:
            return True

        hours_since_refresh = (
            datetime.now() - self.last_refresh
        ).total_seconds() / 3600
        return hours_since_refresh >= 24  # Refresh daily as per Angel docs

    def load_from_cache(self) -> bool:
        """Load instruments from cache file"""
        try:
            if not os.path.exists(self.CACHE_FILE):
                return False

            with open(self.CACHE_FILE, "r") as f:
                cache_data = json.load(f)

            # Check cache age
            last_refresh_str = cache_data.get("last_refresh")
            if last_refresh_str:
                self.last_refresh = datetime.fromisoformat(last_refresh_str)
                if not self.should_refresh():
                    # Load cached data
                    self.symbol_token_map = cache_data.get("symbol_token_map", {})
                    self.token_symbol_map = cache_data.get("token_symbol_map", {})

                    # Load DataFrame
                    instruments_data = cache_data.get("instruments_data", [])
                    if instruments_data:
                        self.instruments_df = pd.DataFrame(instruments_data)

                    logger.info(
                        f"📂 Loaded {len(self.symbol_token_map)} symbols from cache"
                    )
                    return True

            return False

        except Exception as e:
            logger.error(f"❌ Error loading cache: {e}")
            return False

    def download_instruments(self) -> bool:
        """Download fresh instruments from Angel API"""
        try:
            logger.info("⬇️ Downloading Angel instruments...")

            response = requests.get(self.INSTRUMENTS_URL, timeout=30)

            if response.status_code == 200:
                data = response.json()
                self.instruments_df = pd.DataFrame(data)

                # Create symbol-to-token mappings
                self._create_mappings()

                # Cache the data
                self._save_to_cache()

                self.last_refresh = datetime.now()
                logger.info(f"✅ Downloaded {len(self.instruments_df)} instruments")
                logger.info(f"📊 Mapped {len(self.symbol_token_map)} symbols")
                return True
            else:
                logger.error(
                    f"❌ Failed to download instruments: HTTP {response.status_code}"
                )
                return False

        except Exception as e:
            logger.error(f"❌ Error downloading instruments: {e}")
            return False

    def _create_mappings(self):
        """Create symbol-to-token and token-to-symbol mappings"""
        try:
            self.symbol_token_map.clear()
            self.token_symbol_map.clear()

            for _, row in self.instruments_df.iterrows():
                symbol = str(row.get("symbol", "")).upper()
                token = str(row.get("token", ""))
                exchange = str(row.get("exch_seg", ""))

                if symbol and token and exchange:
                    # Store both plain symbol and exchange-suffixed symbol
                    self.symbol_token_map[symbol] = token

                    # For NSE stocks, also store with -EQ suffix
                    if exchange == "NSE" and not symbol.endswith("-EQ"):
                        self.symbol_token_map[f"{symbol}-EQ"] = token

                    # Reverse mapping
                    self.token_symbol_map[token] = symbol

            logger.info(f"✅ Created mappings for {len(self.symbol_token_map)} symbols")

        except Exception as e:
            logger.error(f"❌ Error creating mappings: {e}")

    def _save_to_cache(self):
        """Save instruments to cache file"""
        try:
            cache_data = {
                "last_refresh": (
                    self.last_refresh.isoformat() if self.last_refresh else None
                ),
                "symbol_token_map": self.symbol_token_map,
                "token_symbol_map": self.token_symbol_map,
                "instruments_data": (
                    self.instruments_df.to_dict("records")
                    if self.instruments_df is not None
                    else []
                ),
            }

            with open(self.CACHE_FILE, "w") as f:
                json.dump(cache_data, f, indent=2)

            logger.info(f"💾 Saved instruments to cache: {self.CACHE_FILE}")

        except Exception as e:
            logger.error(f"❌ Error saving cache: {e}")

    def get_token(self, symbol: str) -> Optional[str]:
        """Get token for a symbol"""
        return self.symbol_token_map.get(symbol.upper())

    def get_symbol(self, token: str) -> Optional[str]:
        """Get symbol for a token"""
        return self.token_symbol_map.get(str(token))

    def get_tokens_for_symbols(self, symbols: List[str]) -> List[str]:
        """Get tokens for multiple symbols"""
        tokens = []
        missing_symbols = []

        for symbol in symbols:
            token = self.get_token(symbol)
            if token:
                tokens.append(token)
            else:
                missing_symbols.append(symbol)

        if missing_symbols:
            logger.warning(
                f"⚠️ No tokens found for: {missing_symbols[:10]}"
            )  # Show first 10

        return tokens

    def refresh_if_needed(self) -> bool:
        """Refresh instruments if needed"""
        try:
            # Try loading from cache first
            if self.load_from_cache():
                return True

            # Download fresh data
            return self.download_instruments()

        except Exception as e:
            logger.error(f"❌ Error refreshing instruments: {e}")
            return False

    def get_stats(self) -> Dict:
        """Get statistics"""
        return {
            "total_instruments": (
                len(self.instruments_df) if self.instruments_df is not None else 0
            ),
            "total_symbols_mapped": len(self.symbol_token_map),
            "last_refresh": (
                self.last_refresh.isoformat() if self.last_refresh else None
            ),
            "cache_file": self.CACHE_FILE,
            "should_refresh": self.should_refresh(),
        }


# Global instance
_angel_instruments: Optional[AngelInstruments] = None


def get_instruments() -> AngelInstruments:
    """Get or create Angel instruments instance"""
    global _angel_instruments
    if _angel_instruments is None:
        _angel_instruments = AngelInstruments()
    return _angel_instruments
