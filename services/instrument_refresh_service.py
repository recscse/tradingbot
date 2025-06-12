import json
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import BrokerConfig, BrokerInstrument
from utils.instrument_key_cache import save_instrument_keys

logger = logging.getLogger(__name__)


class InstrumentRefreshService:
    def __init__(self):
        self.instrument_file = Path("data/upstox_instruments.json")
        self.top_stocks_file = Path("data/top_stocks.json")

    async def refresh_daily_instruments(self):
        """Refresh instrument data daily"""
        logger.info("🔄 Starting daily instrument refresh...")

        try:
            # 1. Download latest instruments from Upstox
            await self._download_latest_instruments()

            # 2. Update database with new instruments
            await self._update_instrument_database()

            # 3. Clean expired instruments
            await self._clean_expired_instruments()

            # 4. Generate updated instrument keys
            await self._generate_updated_instrument_keys()

            logger.info("✅ Daily instrument refresh complete")

        except Exception as e:
            logger.error(f"❌ Instrument refresh failed: {e}")
            raise

    async def _download_latest_instruments(self):
        """Download latest instrument master from Upstox"""
        try:
            # Get Upstox access token
            db = next(get_db())
            broker_config = (
                db.query(BrokerConfig)
                .filter(
                    BrokerConfig.broker_name.ilike("upstox"),
                    BrokerConfig.is_active == True,
                )
                .first()
            )

            if not broker_config:
                raise Exception("No active Upstox configuration found")

            headers = {
                "Authorization": f"Bearer {broker_config.access_token}",
                "Accept": "application/json",
            }

            # Download instrument master
            response = requests.get(
                "https://api.upstox.com/v2/option/contract", headers=headers
            )
            response.raise_for_status()

            instruments = response.json()["data"]

            # Save to file
            with open(self.instrument_file, "w") as f:
                json.dump(instruments, f, indent=2)

            logger.info(f"📥 Downloaded {len(instruments)} instruments")

        except Exception as e:
            logger.error(f"❌ Failed to download instruments: {e}")
            raise

    async def _update_instrument_database(self):
        """Update database with new instrument data"""
        try:
            db = next(get_db())

            with open(self.instrument_file, "r") as f:
                instruments = json.load(f)

            # Clear existing instruments
            db.query(BrokerInstrument).delete()

            # Insert new instruments
            for instrument in instruments:
                db_instrument = BrokerInstrument(
                    broker_name="Upstox",
                    symbol=instrument.get("trading_symbol", ""),
                    name=instrument.get("name", ""),
                    exchange=instrument.get("exchange", ""),
                    segment=instrument.get("segment", ""),
                    instrument_type=instrument.get("instrument_type", ""),
                    isin=instrument.get("isin"),
                    lot_size=instrument.get("lot_size"),
                    tick_size=instrument.get("tick_size"),
                    instrument_key=instrument.get("instrument_key", ""),
                    security_type=instrument.get("security_type"),
                )
                db.add(db_instrument)

            db.commit()
            logger.info("✅ Database updated with new instruments")

        except Exception as e:
            logger.error(f"❌ Database update failed: {e}")
            db.rollback()
            raise
        finally:
            db.close()

    async def _clean_expired_instruments(self):
        """Remove expired instruments"""
        try:
            now = datetime.now()

            with open(self.instrument_file, "r") as f:
                instruments = json.load(f)

            # Filter out expired instruments
            active_instruments = []
            for instrument in instruments:
                expiry = instrument.get("expiry")
                if expiry:
                    expiry_date = datetime.fromtimestamp(expiry / 1000)
                    if expiry_date > now:
                        active_instruments.append(instrument)
                else:
                    # No expiry means it's a spot instrument
                    active_instruments.append(instrument)

            # Save filtered instruments
            with open(self.instrument_file, "w") as f:
                json.dump(active_instruments, f, indent=2)

            logger.info(
                f"🧹 Cleaned {len(instruments) - len(active_instruments)} expired instruments"
            )

        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
            raise

    def get_stock_instruments(self, symbol: str, exchange: str = "NSE") -> Dict:
        """Get all instruments for a stock (spot, futures, options)"""
        try:
            with open(self.instrument_file, "r") as f:
                instruments = json.load(f)

            stock_instruments = {
                "spot": None,
                "futures": [],
                "options": {"CE": [], "PE": []},
            }

            for instrument in instruments:
                if (
                    instrument.get("underlying_symbol", "").upper() == symbol.upper()
                    or instrument.get("trading_symbol", "").upper() == symbol.upper()
                ):

                    inst_type = instrument.get("instrument_type", "").upper()

                    if inst_type == "EQ":
                        stock_instruments["spot"] = instrument
                    elif inst_type == "FUT":
                        stock_instruments["futures"].append(instrument)
                    elif inst_type in ["CE", "PE"]:
                        stock_instruments["options"][inst_type].append(instrument)

            return stock_instruments

        except Exception as e:
            logger.error(f"❌ Failed to get instruments for {symbol}: {e}")
            return {}
