import json
import logging
import requests
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import BrokerConfig, BrokerInstrument
from services.optimized_instrument_service import OptimizedInstrumentService

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
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

            # 4. Re-initialize optimized instrument service
            await self._reinitialize_optimized_service()

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

            # Download instrument master from complete API
            response = requests.get(
                "https://api.upstox.com/v2/option/contract", headers=headers
            )
            response.raise_for_status()

            instruments = response.json()["data"]

            # Save to file
            with open(self.instrument_file, "w") as f:
                json.dump(instruments, f, indent=2)

            logger.info(f"📥 Downloaded {len(instruments)} instruments")
            db.close()

        except Exception as e:
            logger.error(f"❌ Failed to download instruments: {e}")
            if "db" in locals():
                db.close()
            raise

    async def _update_instrument_database(self):
        """Update database with new instrument data"""
        try:
            db = next(get_db())

            with open(self.instrument_file, "r") as f:
                instruments = json.load(f)

            # Clear existing instruments
            db.query(BrokerInstrument).delete()

            # Insert new instruments in batches for better performance
            batch_size = 500
            for i in range(0, len(instruments), batch_size):
                batch = instruments[i : i + batch_size]

                for instrument in batch:
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
                        expiry=instrument.get("expiry"),
                        strike_price=instrument.get("strike_price"),
                        underlying_symbol=instrument.get("underlying_symbol", ""),
                    )
                    db.add(db_instrument)

                # Commit batch
                db.commit()
                logger.info(
                    f"📊 Processed batch {i//batch_size + 1}/{(len(instruments)-1)//batch_size + 1}"
                )

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
            expired_count = 0

            for instrument in instruments:
                expiry = instrument.get("expiry")
                if expiry:
                    try:
                        expiry_date = datetime.fromtimestamp(expiry / 1000)
                        if expiry_date > now:
                            active_instruments.append(instrument)
                        else:
                            expired_count += 1
                    except (ValueError, TypeError):
                        # Keep instruments with invalid expiry dates
                        active_instruments.append(instrument)
                else:
                    # No expiry means it's a spot instrument
                    active_instruments.append(instrument)

            # Save filtered instruments
            with open(self.instrument_file, "w") as f:
                json.dump(active_instruments, f, indent=2)

            logger.info(f"🧹 Cleaned {expired_count} expired instruments")

        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
            raise

    async def _reinitialize_optimized_service(self):
        """Re-initialize the optimized instrument service with new data"""
        try:
            logger.info("🔄 Re-initializing optimized instrument service...")

            # Clear existing cache
            OptimizedInstrumentService.redis_client.flushdb()

            # Re-initialize with new data
            result = await OptimizedInstrumentService.initialize_instruments_system()

            logger.info(f"✅ Optimized service re-initialized: {result}")

        except Exception as e:
            logger.error(f"❌ Failed to re-initialize optimized service: {e}")
            raise

    # ========== INTEGRATION METHODS FOR CENTRALIZED MANAGER ==========

    def get_stock_instruments(self, symbol: str, exchange: str = "NSE") -> Dict:
        """Get all instruments for a stock (spot, futures, options)"""
        try:
            # Use optimized service if available
            if OptimizedInstrumentService.is_initialized():
                mapping = OptimizedInstrumentService.get_stock_instruments(symbol)
                if mapping:
                    return self._convert_mapping_to_legacy_format(mapping)

            # Fallback to file-based lookup
            return self._get_stock_instruments_from_file(symbol, exchange)

        except Exception as e:
            logger.error(f"❌ Failed to get instruments for {symbol}: {e}")
            return {}

    def _convert_mapping_to_legacy_format(self, mapping: Dict) -> Dict:
        """Convert optimized service mapping to legacy format"""
        try:
            instruments = mapping.get("instruments", {})

            result = {"spot": None, "futures": [], "options": {"CE": [], "PE": []}}

            # Convert spot
            if instruments.get("EQ"):
                result["spot"] = instruments["EQ"][0]
            elif instruments.get("INDEX"):
                result["spot"] = instruments["INDEX"][0]

            # Convert futures
            result["futures"] = instruments.get("FUT", [])

            # Convert options
            result["options"]["CE"] = instruments.get("CE", [])
            result["options"]["PE"] = instruments.get("PE", [])

            return result

        except Exception as e:
            logger.error(f"❌ Failed to convert mapping: {e}")
            return {}

    def _get_stock_instruments_from_file(
        self, symbol: str, exchange: str = "NSE"
    ) -> Dict:
        """Fallback method to get instruments from file"""
        try:
            with open(self.instrument_file, "r") as f:
                instruments = json.load(f)

            stock_instruments = {
                "spot": None,
                "futures": [],
                "options": {"CE": [], "PE": []},
            }

            for instrument in instruments:
                # Check if this instrument belongs to the symbol
                trading_symbol = instrument.get("trading_symbol", "").upper()
                underlying_symbol = instrument.get("underlying_symbol", "").upper()

                if (
                    underlying_symbol == symbol.upper()
                    or trading_symbol == symbol.upper()
                    or trading_symbol.startswith(symbol.upper())
                ):

                    inst_type = instrument.get("instrument_type", "").upper()

                    if inst_type == "EQ":
                        stock_instruments["spot"] = instrument
                    elif inst_type == "FUT":
                        stock_instruments["futures"].append(instrument)
                    elif inst_type in ["CE", "PE"]:
                        stock_instruments["options"][inst_type].append(instrument)

            # Sort futures by expiry
            stock_instruments["futures"].sort(key=lambda x: x.get("expiry", 0))

            # Sort options by strike price
            for option_type in ["CE", "PE"]:
                stock_instruments["options"][option_type].sort(
                    key=lambda x: x.get("strike_price", 0)
                )

            return stock_instruments

        except Exception as e:
            logger.error(f"❌ Failed to get instruments from file for {symbol}: {e}")
            return {}

    def get_optimized_instruments(self, symbols: List[str]) -> Dict[str, Dict]:
        """Get optimized instruments for multiple symbols"""
        optimized_instruments = {}

        for symbol in symbols:
            instruments = self.get_stock_instruments(symbol)
            if instruments:
                optimized_instruments[symbol] = instruments

        return optimized_instruments

    def get_all_dashboard_instruments(self) -> List[str]:
        """Get all dashboard instruments (spot keys)"""
        try:
            if OptimizedInstrumentService.is_initialized():
                return OptimizedInstrumentService.get_all_dashboard_instruments()

            # Fallback: get from file
            return self._get_dashboard_instruments_from_file()

        except Exception as e:
            logger.error(f"❌ Failed to get dashboard instruments: {e}")
            return []

    def _get_dashboard_instruments_from_file(self) -> List[str]:
        """Fallback method to get dashboard instruments from file"""
        try:
            dashboard_keys = []

            with open(self.top_stocks_file, "r") as f:
                top_stocks_data = json.load(f)

            # Handle different JSON structures
            if isinstance(top_stocks_data, dict) and "securities" in top_stocks_data:
                top_stocks = top_stocks_data["securities"]
            else:
                top_stocks = top_stocks_data

            for stock in top_stocks:
                symbol = stock.get("symbol", "").upper()
                if symbol:
                    instruments = self.get_stock_instruments(symbol)
                    if instruments.get("spot"):
                        key = instruments["spot"].get("instrument_key")
                        if key:
                            dashboard_keys.append(key)

            return dashboard_keys

        except Exception as e:
            logger.error(f"❌ Failed to get dashboard instruments from file: {e}")
            return []

    def get_trading_instruments_for_selected_stocks(
        self, selected_stocks: List[Dict]
    ) -> List[str]:
        """Get comprehensive trading instruments for selected stocks"""
        try:
            if OptimizedInstrumentService.is_initialized():
                return OptimizedInstrumentService.get_trading_instruments_for_selected_stocks(
                    selected_stocks
                )

            # Fallback: manual generation
            return self._generate_trading_instruments_manual(selected_stocks)

        except Exception as e:
            logger.error(f"❌ Failed to get trading instruments: {e}")
            return []

    def _generate_trading_instruments_manual(
        self, selected_stocks: List[Dict]
    ) -> List[str]:
        """Manual trading instruments generation as fallback"""
        try:
            trading_keys = []

            for stock in selected_stocks[:10]:  # Limit to 10
                symbol = stock.get("symbol", "").upper()
                current_price = float(stock.get("ltp", stock.get("entry_price", 0)))

                instruments = self.get_stock_instruments(symbol)

                # 1. Add spot
                if instruments.get("spot"):
                    key = instruments["spot"].get("instrument_key")
                    if key:
                        trading_keys.append(key)

                # 2. Add 3 futures
                futures = instruments.get("futures", [])[:3]
                for future in futures:
                    key = future.get("instrument_key")
                    if key:
                        trading_keys.append(key)

                # 3. Add options around ATM
                if current_price > 0:
                    option_keys = self._get_atm_options_manual(
                        instruments, current_price
                    )
                    trading_keys.extend(option_keys)

            return list(set(trading_keys))  # Remove duplicates

        except Exception as e:
            logger.error(f"❌ Failed to generate trading instruments manually: {e}")
            return []

    def _get_atm_options_manual(
        self, instruments: Dict, current_price: float
    ) -> List[str]:
        """Manual ATM options selection"""
        try:
            option_keys = []

            # Calculate ATM strike
            atm_strike = round(current_price / 50) * 50

            # Define range
            if current_price < 500:
                strike_range = 200  # ±200
            elif current_price < 2000:
                strike_range = 500  # ±500
            else:
                strike_range = 1000  # ±1000

            min_strike = atm_strike - strike_range
            max_strike = atm_strike + strike_range

            # Get options within range
            for option_type in ["CE", "PE"]:
                options = instruments.get("options", {}).get(option_type, [])

                for option in options:
                    strike = option.get("strike_price", 0)
                    if min_strike <= strike <= max_strike:
                        key = option.get("instrument_key")
                        if key:
                            option_keys.append(key)

            return option_keys

        except Exception as e:
            logger.error(f"❌ Failed to get ATM options manually: {e}")
            return []

    async def force_refresh_and_reinitialize(self):
        """Force refresh of all data and reinitialize services"""
        try:
            logger.info("🔄 Force refresh and reinitialize started...")

            # Download fresh data
            await self._download_latest_instruments()

            # Clean expired
            await self._clean_expired_instruments()

            # Update database
            await self._update_instrument_database()

            # Reinitialize optimized service
            await self._reinitialize_optimized_service()

            logger.info("✅ Force refresh and reinitialize completed")

        except Exception as e:
            logger.error(f"❌ Force refresh failed: {e}")
            raise

    def get_service_status(self) -> Dict:
        """Get status of instrument services"""
        try:
            status = {
                "files_exist": {
                    "top_stocks": self.top_stocks_file.exists(),
                    "upstox_instruments": self.instrument_file.exists(),
                },
                "optimized_service_initialized": OptimizedInstrumentService.is_initialized(),
                "optimized_service_stats": OptimizedInstrumentService.get_service_stats(),
                "file_sizes": {},
                "last_modified": {},
            }

            # Get file info
            for file_name, file_path in [
                ("top_stocks", self.top_stocks_file),
                ("upstox_instruments", self.instrument_file),
            ]:
                if file_path.exists():
                    stat = file_path.stat()
                    status["file_sizes"][file_name] = stat.st_size
                    status["last_modified"][file_name] = datetime.fromtimestamp(
                        stat.st_mtime
                    ).isoformat()

            return status

        except Exception as e:
            logger.error(f"❌ Failed to get service status: {e}")
            return {"error": str(e)}


# Global instance
instrument_refresh_service = InstrumentRefreshService()


# Convenience functions to maintain compatibility
def get_stock_instruments(symbol: str, exchange: str = "NSE") -> Dict:
    """Get all instruments for a stock (spot, futures, options)"""
    return instrument_refresh_service.get_stock_instruments(symbol, exchange)


def get_optimized_instruments(symbols: List[str]) -> Dict[str, Dict]:
    """Get optimized instruments for multiple symbols"""
    return instrument_refresh_service.get_optimized_instruments(symbols)


async def get_all_dashboard_instruments() -> List[str]:
    """Get all dashboard instruments"""
    return instrument_refresh_service.get_all_dashboard_instruments()


def get_trading_instruments_for_selected_stocks(
    selected_stocks: List[Dict],
) -> List[str]:
    """Get trading instruments for selected stocks"""
    return instrument_refresh_service.get_trading_instruments_for_selected_stocks(
        selected_stocks
    )
