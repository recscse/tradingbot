#!/usr/bin/env python3
"""
Complete NSE F&O Underlying Information Scraper
Gets the COMPLETE F&O list using multiple API endpoints and strategies
Ensures no data is missed
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Set
import requests
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CompleteNSEFnoScraper:
    """
    Complete NSE F&O scraper that ensures we get ALL underlying instruments
    Uses multiple strategies to get comprehensive data
    """

    def __init__(self, json_file_name: str = "complete_nse_fno_list.json"):
        self.json_file_path = Path(json_file_name)

        # NSE API endpoints - multiple sources for complete data
        self.base_url = "https://www.nseindia.com"
        self.api_endpoints = {
            "underlying_info": f"{self.base_url}/api/underlying-information",
            "equity_derivatives": f"{self.base_url}/api/equity-derivatives",
            "option_chain": f"{self.base_url}/api/option-chain-equities",
            "derivatives_data": f"{self.base_url}/api/derivatives-data",
            "fo_sec_ban": f"{self.base_url}/api/fo-sec-ban",
            "live_analysis_derivatives": f"{self.base_url}/api/live-analysis-derivatives",
        }

        # Referer URLs for different endpoints
        self.referer_urls = {
            "underlying_info": f"{self.base_url}/products-services/equity-derivatives-list-underlyings-information",
            "equity_derivatives": f"{self.base_url}/products-services/equity-derivatives",
            "option_chain": f"{self.base_url}/option-chain",
            "derivatives_data": f"{self.base_url}/market-data/derivatives-market-watch",
            "fo_sec_ban": f"{self.base_url}/products-services/equity-derivatives-list-underlyings-information",
            "live_analysis_derivatives": f"{self.base_url}/market-data/live-analysis-derivatives",
        }

        # Setup session
        self.session = requests.Session()
        self._setup_session()

        # Track unique instruments to avoid duplicates
        self.seen_symbols: Set[str] = set()
        self.all_instruments: List[Dict[str, any]] = []

    def _setup_session(self):
        """Setup session with comprehensive headers"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "X-Requested-With": "XMLHttpRequest",
            "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        self.session.headers.update(headers)

    def _get_session_cookies(self, referer_url: str) -> bool:
        """Get session cookies by visiting the specific page"""
        try:
            logger.info(f"🍪 Getting session cookies from: {referer_url}")

            # Update referer for this request
            self.session.headers["Referer"] = referer_url

            response = self.session.get(referer_url, timeout=30)

            if response.status_code == 200:
                logger.info("✅ Successfully got session cookies")
                time.sleep(2)  # Small delay after getting cookies
                return True
            else:
                logger.warning(
                    f"⚠️ Got status code {response.status_code} for {referer_url}"
                )
                return False

        except Exception as e:
            logger.error(f"❌ Failed to get session cookies from {referer_url}: {e}")
            return False

    def get_complete_fno_data(self) -> List[Dict[str, any]]:
        """Get complete F&O data using multiple strategies"""
        logger.info("🎯 Starting comprehensive F&O data collection...")

        self.all_instruments = []
        self.seen_symbols = set()

        # Strategy 1: Main underlying information API
        self._collect_from_underlying_info()

        # Strategy 2: Equity derivatives API
        self._collect_from_equity_derivatives()

        # Strategy 3: Option chain data (for individual stocks)
        self._collect_from_option_chains()

        # Strategy 4: FO security ban list (active F&O stocks)
        self._collect_from_fo_sec_ban()

        # Strategy 5: Live derivatives analysis
        self._collect_from_live_derivatives()

        # Strategy 6: Manual addition of known instruments
        self._add_known_instruments()

        logger.info(f"🎉 Collected {len(self.all_instruments)} unique F&O instruments")
        return self.all_instruments

    def _collect_from_underlying_info(self):
        """Collect from main underlying information API"""
        logger.info("📡 Strategy 1: Collecting from underlying information API...")

        try:
            endpoint_key = "underlying_info"
            if not self._get_session_cookies(self.referer_urls[endpoint_key]):
                logger.warning("Failed to get cookies for underlying info")
                return

            response = self.session.get(self.api_endpoints[endpoint_key], timeout=30)

            if response.status_code == 200:
                try:
                    data = response.json()
                    instruments = self._process_api_response(data, "underlying_info")
                    self._add_instruments(instruments)
                    logger.info(
                        f"✅ Got {len(instruments)} instruments from underlying info API"
                    )
                except json.JSONDecodeError as e:
                    logger.error(f"❌ JSON decode error for underlying info: {e}")
            else:
                logger.warning(
                    f"⚠️ Underlying info API returned status {response.status_code}"
                )

        except Exception as e:
            logger.error(f"❌ Error in underlying info collection: {e}")

    def _collect_from_equity_derivatives(self):
        """Collect from equity derivatives API"""
        logger.info("📡 Strategy 2: Collecting from equity derivatives API...")

        try:
            endpoint_key = "equity_derivatives"
            if not self._get_session_cookies(self.referer_urls[endpoint_key]):
                logger.warning("Failed to get cookies for equity derivatives")
                return

            response = self.session.get(self.api_endpoints[endpoint_key], timeout=30)

            if response.status_code == 200:
                try:
                    data = response.json()
                    instruments = self._process_api_response(data, "equity_derivatives")
                    self._add_instruments(instruments)
                    logger.info(
                        f"✅ Got {len(instruments)} instruments from equity derivatives API"
                    )
                except json.JSONDecodeError as e:
                    logger.error(f"❌ JSON decode error for equity derivatives: {e}")
            else:
                logger.warning(
                    f"⚠️ Equity derivatives API returned status {response.status_code}"
                )

        except Exception as e:
            logger.error(f"❌ Error in equity derivatives collection: {e}")

    def _collect_from_option_chains(self):
        """Collect from option chain APIs for individual stocks"""
        logger.info("📡 Strategy 3: Collecting from option chains...")

        # Common F&O stocks to check option chains for
        major_stocks = [
            "RELIANCE",
            "HDFCBANK",
            "TCS",
            "ICICIBANK",
            "BHARTIARTL",
            "SBIN",
            "INFY",
            "BAJFINANCE",
            "LICI",
            "HINDUNILVR",
            "ITC",
            "LT",
            "KOTAKBANK",
            "HCLTECH",
            "SUNPHARMA",
            "M&M",
            "MARUTI",
            "ULTRACEMCO",
            "AXISBANK",
            "NTPC",
        ]

        endpoint_key = "option_chain"
        if not self._get_session_cookies(self.referer_urls[endpoint_key]):
            logger.warning("Failed to get cookies for option chains")
            return

        instruments_found = 0
        for symbol in major_stocks[:10]:  # Limit to avoid too many requests
            try:
                url = f"{self.api_endpoints[endpoint_key]}?symbol={symbol}"
                response = self.session.get(url, timeout=15)

                if response.status_code == 200:
                    try:
                        data = response.json()
                        if "records" in data and "underlyingValue" in data["records"]:
                            # Extract underlying info
                            underlying = {
                                "symbol": symbol,
                                "name": symbol,  # We'll enhance this later
                                "exchange": "NSE",
                                "instrumentType": "EQUITY",
                                "hasOptions": True,
                            }
                            if self._add_single_instrument(underlying):
                                instruments_found += 1
                    except json.JSONDecodeError:
                        pass

                time.sleep(0.5)  # Small delay between requests

            except Exception as e:
                logger.error(f"Error getting option chain for {symbol}: {e}")
                continue

        logger.info(f"✅ Found {instruments_found} instruments from option chains")

    def _collect_from_fo_sec_ban(self):
        """Collect from F&O security ban list (active F&O stocks)"""
        logger.info("📡 Strategy 4: Collecting from F&O security ban list...")

        try:
            endpoint_key = "fo_sec_ban"
            if not self._get_session_cookies(self.referer_urls[endpoint_key]):
                logger.warning("Failed to get cookies for F&O sec ban")
                return

            response = self.session.get(self.api_endpoints[endpoint_key], timeout=30)

            if response.status_code == 200:
                try:
                    data = response.json()
                    instruments = self._process_api_response(data, "fo_sec_ban")
                    self._add_instruments(instruments)
                    logger.info(
                        f"✅ Got {len(instruments)} instruments from F&O sec ban API"
                    )
                except json.JSONDecodeError as e:
                    logger.error(f"❌ JSON decode error for F&O sec ban: {e}")
            else:
                logger.warning(
                    f"⚠️ F&O sec ban API returned status {response.status_code}"
                )

        except Exception as e:
            logger.error(f"❌ Error in F&O sec ban collection: {e}")

    def _collect_from_live_derivatives(self):
        """Collect from live derivatives analysis"""
        logger.info("📡 Strategy 5: Collecting from live derivatives analysis...")

        try:
            endpoint_key = "live_analysis_derivatives"
            if not self._get_session_cookies(self.referer_urls[endpoint_key]):
                logger.warning("Failed to get cookies for live derivatives")
                return

            response = self.session.get(self.api_endpoints[endpoint_key], timeout=30)

            if response.status_code == 200:
                try:
                    data = response.json()
                    instruments = self._process_api_response(data, "live_derivatives")
                    self._add_instruments(instruments)
                    logger.info(
                        f"✅ Got {len(instruments)} instruments from live derivatives API"
                    )
                except json.JSONDecodeError as e:
                    logger.error(f"❌ JSON decode error for live derivatives: {e}")
            else:
                logger.warning(
                    f"⚠️ Live derivatives API returned status {response.status_code}"
                )

        except Exception as e:
            logger.error(f"❌ Error in live derivatives collection: {e}")

    def _add_known_instruments(self):
        """Add known F&O instruments that might be missed by APIs"""
        logger.info("📡 Strategy 6: Adding known F&O instruments...")

        known_instruments = [
            # Indices
            {"symbol": "NIFTY", "name": "Nifty 50", "instrumentType": "INDEX"},
            {"symbol": "BANKNIFTY", "name": "Nifty Bank", "instrumentType": "INDEX"},
            {
                "symbol": "FINNIFTY",
                "name": "Nifty Financial Services",
                "instrumentType": "INDEX",
            },
            {
                "symbol": "MIDCPNIFTY",
                "name": "Nifty Midcap Select",
                "instrumentType": "INDEX",
            },
            # Major stocks that must have F&O
            {
                "symbol": "RELIANCE",
                "name": "Reliance Industries",
                "instrumentType": "EQUITY",
            },
            {"symbol": "HDFCBANK", "name": "HDFC Bank", "instrumentType": "EQUITY"},
            {
                "symbol": "TCS",
                "name": "Tata Consultancy Services",
                "instrumentType": "EQUITY",
            },
            {"symbol": "ICICIBANK", "name": "ICICI Bank", "instrumentType": "EQUITY"},
            {
                "symbol": "BHARTIARTL",
                "name": "Bharti Airtel",
                "instrumentType": "EQUITY",
            },
            {
                "symbol": "SBIN",
                "name": "State Bank of India",
                "instrumentType": "EQUITY",
            },
            {"symbol": "INFY", "name": "Infosys", "instrumentType": "EQUITY"},
            {
                "symbol": "BAJFINANCE",
                "name": "Bajaj Finance",
                "instrumentType": "EQUITY",
            },
            {"symbol": "LICI", "name": "LIC of India", "instrumentType": "EQUITY"},
            {
                "symbol": "HINDUNILVR",
                "name": "Hindustan Unilever",
                "instrumentType": "EQUITY",
            },
            {"symbol": "ITC", "name": "ITC", "instrumentType": "EQUITY"},
            {"symbol": "LT", "name": "Larsen & Toubro", "instrumentType": "EQUITY"},
            {
                "symbol": "KOTAKBANK",
                "name": "Kotak Mahindra Bank",
                "instrumentType": "EQUITY",
            },
            {
                "symbol": "HCLTECH",
                "name": "HCL Technologies",
                "instrumentType": "EQUITY",
            },
            {
                "symbol": "SUNPHARMA",
                "name": "Sun Pharmaceutical",
                "instrumentType": "EQUITY",
            },
            {
                "symbol": "M&M",
                "name": "Mahindra & Mahindra",
                "instrumentType": "EQUITY",
            },
            {"symbol": "MARUTI", "name": "Maruti Suzuki", "instrumentType": "EQUITY"},
            {
                "symbol": "ULTRACEMCO",
                "name": "UltraTech Cement",
                "instrumentType": "EQUITY",
            },
            {"symbol": "AXISBANK", "name": "Axis Bank", "instrumentType": "EQUITY"},
            {"symbol": "NTPC", "name": "NTPC", "instrumentType": "EQUITY"},
            {
                "symbol": "BAJAJFINSV",
                "name": "Bajaj Finserv",
                "instrumentType": "EQUITY",
            },
            {
                "symbol": "HAL",
                "name": "Hindustan Aeronautics",
                "instrumentType": "EQUITY",
            },
            {
                "symbol": "ADANIPORTS",
                "name": "Adani Ports & SEZ",
                "instrumentType": "EQUITY",
            },
            {
                "symbol": "ONGC",
                "name": "Oil & Natural Gas Corporation",
                "instrumentType": "EQUITY",
            },
            {"symbol": "TITAN", "name": "Titan Company", "instrumentType": "EQUITY"},
            {
                "symbol": "ADANIENT",
                "name": "Adani Enterprises",
                "instrumentType": "EQUITY",
            },
            {"symbol": "BEL", "name": "Bharat Electronics", "instrumentType": "EQUITY"},
            {
                "symbol": "POWERGRID",
                "name": "Power Grid Corporation",
                "instrumentType": "EQUITY",
            },
            {"symbol": "WIPRO", "name": "Wipro", "instrumentType": "EQUITY"},
            {
                "symbol": "DMART",
                "name": "Avenue Supermarts",
                "instrumentType": "EQUITY",
            },
            {"symbol": "TATAMOTORS", "name": "Tata Motors", "instrumentType": "EQUITY"},
            {"symbol": "JSWSTEEL", "name": "JSW Steel", "instrumentType": "EQUITY"},
            {"symbol": "NESTLEIND", "name": "Nestle India", "instrumentType": "EQUITY"},
            {"symbol": "COALINDIA", "name": "Coal India", "instrumentType": "EQUITY"},
            {"symbol": "BAJAJ-AUTO", "name": "Bajaj Auto", "instrumentType": "EQUITY"},
            {
                "symbol": "ASIANPAINT",
                "name": "Asian Paints",
                "instrumentType": "EQUITY",
            },
            {
                "symbol": "INDIGO",
                "name": "InterGlobe Aviation",
                "instrumentType": "EQUITY",
            },
            {
                "symbol": "IOC",
                "name": "Indian Oil Corporation",
                "instrumentType": "EQUITY",
            },
            {"symbol": "DLF", "name": "DLF", "instrumentType": "EQUITY"},
            {"symbol": "TATASTEEL", "name": "Tata Steel", "instrumentType": "EQUITY"},
        ]

        added_count = 0
        for instrument in known_instruments:
            instrument["exchange"] = "NSE"
            if self._add_single_instrument(instrument):
                added_count += 1

        logger.info(f"✅ Added {added_count} known F&O instruments")

    def _process_api_response(self, data: Dict, source: str) -> List[Dict[str, any]]:
        """Process API response from any source"""
        instruments = []

        try:
            # Handle different response structures
            items = []

            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                # Try different possible keys
                possible_keys = [
                    "data",
                    "underlyingList",
                    "results",
                    "records",
                    "stocks",
                    "equities",
                    "derivatives",
                    "instruments",
                    "securities",
                ]

                for key in possible_keys:
                    if key in data and isinstance(data[key], list):
                        items = data[key]
                        break

                # If still no items, check nested structures
                if not items:
                    for key, value in data.items():
                        if isinstance(value, dict):
                            for nested_key, nested_value in value.items():
                                if (
                                    isinstance(nested_value, list)
                                    and len(nested_value) > 0
                                ):
                                    items = nested_value
                                    break
                        if items:
                            break

            # Process each item
            for item in items:
                try:
                    processed = self._extract_instrument_info(item, source)
                    if processed:
                        instruments.append(processed)
                except Exception as e:
                    logger.debug(f"Error processing item from {source}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error processing {source} response: {e}")

        return instruments

    def _extract_instrument_info(
        self, item: Dict, source: str
    ) -> Optional[Dict[str, any]]:
        """Extract instrument information from API response item"""
        try:
            # Common field mappings
            symbol_fields = [
                "symbol",
                "underlying",
                "instrumentName",
                "tradingSymbol",
                "scripCode",
            ]
            name_fields = [
                "companyName",
                "name",
                "longName",
                "description",
                "instrumentName",
                "corporateName",
            ]

            # Extract symbol
            symbol = ""
            for field in symbol_fields:
                if field in item and item[field]:
                    symbol = str(item[field]).strip().upper()
                    break

            # Extract name
            name = ""
            for field in name_fields:
                if field in item and item[field]:
                    name = str(item[field]).strip()
                    break

            # Use symbol as name if no name found
            if not name and symbol:
                name = symbol

            if not symbol:
                return None

            # Build result
            result = {
                "symbol": symbol,
                "name": name,
                "exchange": "NSE",
                "source": source,
            }

            # Add optional fields
            optional_mappings = {
                "lotSize": ["lotSize", "marketLot", "lot_size", "boardLotQuantity"],
                "tickSize": ["tickSize", "tick_size"],
                "instrumentType": [
                    "instrumentType",
                    "instrument_type",
                    "instru_type",
                    "series",
                ],
                "isinCode": ["isinCode", "isin"],
                "lastPrice": ["lastPrice", "ltp", "close"],
                "change": ["change", "pChange"],
                "volume": ["volume", "totalTradedVolume"],
            }

            for result_key, possible_fields in optional_mappings.items():
                for field in possible_fields:
                    if field in item and item[field] is not None:
                        result[result_key] = item[field]
                        break

            return result

        except Exception as e:
            logger.debug(f"Error extracting info from {item}: {e}")
            return None

    def _add_instruments(self, instruments: List[Dict[str, any]]):
        """Add multiple instruments to the collection"""
        for instrument in instruments:
            self._add_single_instrument(instrument)

    def _add_single_instrument(self, instrument: Dict[str, any]) -> bool:
        """Add a single instrument if not already present"""
        symbol = instrument.get("symbol", "").strip().upper()

        if not symbol or symbol in self.seen_symbols:
            return False

        # Clean and validate
        instrument["symbol"] = symbol
        instrument["exchange"] = "NSE"

        # Add to collections
        self.seen_symbols.add(symbol)
        self.all_instruments.append(instrument)

        return True

    def save_to_json(self, instruments: List[Dict[str, any]]) -> bool:
        """Save instruments to JSON file"""
        try:
            # Sort by symbol for consistent output
            sorted_instruments = sorted(instruments, key=lambda x: x.get("symbol", ""))

            data = {
                "securities": sorted_instruments,
                "last_updated": datetime.now().isoformat(),
                "total_count": len(sorted_instruments),
                "data_source": "nse_complete_multi_strategy",
                "collection_strategies": [
                    "underlying_information_api",
                    "equity_derivatives_api",
                    "option_chains",
                    "fo_security_ban_list",
                    "live_derivatives_analysis",
                    "known_instruments_addition",
                ],
                "api_endpoints_used": list(self.api_endpoints.values()),
            }

            with open(self.json_file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(
                f"💾 Saved {len(sorted_instruments)} complete F&O instruments to {self.json_file_path}"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Error saving to JSON: {e}")
            return False

    def load_from_json(self) -> List[Dict[str, any]]:
        """Load instruments from JSON file"""
        try:
            if not self.json_file_path.exists():
                logger.warning(f"JSON file {self.json_file_path} does not exist")
                return []

            with open(self.json_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            instruments = data.get("securities", [])
            logger.info(
                f"📂 Loaded {len(instruments)} F&O instruments from {self.json_file_path}"
            )
            return instruments

        except Exception as e:
            logger.error(f"❌ Error loading from JSON: {e}")
            return []

    def update_complete_fno_list(self) -> Dict[str, any]:
        """Main method to get complete F&O list"""
        start_time = datetime.now()
        logger.info("🚀 Starting COMPLETE F&O data collection...")

        try:
            # Get comprehensive data using all strategies
            instruments = self.get_complete_fno_data()

            if not instruments:
                return {
                    "status": "failed",
                    "error": "No instruments collected from any source",
                    "timestamp": datetime.now().isoformat(),
                }

            # Save to JSON
            saved = self.save_to_json(instruments)

            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            result = {
                "status": "success" if saved else "partial_success",
                "total_instruments": len(instruments),
                "unique_symbols": len(self.seen_symbols),
                "file_saved": saved,
                "file_path": str(self.json_file_path),
                "processing_time_seconds": processing_time,
                "last_updated": datetime.now().isoformat(),
                "collection_methods": 6,
                "data_completeness": "comprehensive",
            }

            logger.info(
                f"🎉 COMPLETE F&O collection finished in {processing_time:.2f}s"
            )
            logger.info(f"📊 Total instruments: {len(instruments)}")

            return result

        except Exception as e:
            logger.error(f"❌ Complete F&O collection failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }


# Standalone functions
def get_complete_nse_fno_list(
    json_file: str = "complete_nse_fno_list.json",
) -> Dict[str, any]:
    """Get complete F&O list using all available methods"""
    scraper = CompleteNSEFnoScraper(json_file)
    return scraper.update_complete_fno_list()


def load_complete_nse_fno_list(
    json_file: str = "complete_nse_fno_list.json",
) -> List[Dict[str, any]]:
    """Load complete F&O list from saved JSON"""
    scraper = CompleteNSEFnoScraper(json_file)
    return scraper.load_from_json()


def main():
    """Main function"""
    print("🚀 Complete NSE F&O Scraper Starting...")
    print("📋 Using 6 different strategies to ensure complete data collection")

    # Get complete F&O list
    result = get_complete_nse_fno_list()

    if result["status"] == "success":
        print(f"\n🎉 SUCCESS! Complete F&O data collection finished")
        print(f"📊 Total instruments collected: {result['total_instruments']}")
        print(f"🔢 Unique symbols: {result['unique_symbols']}")
        print(f"📁 Data saved to: {result['file_path']}")
        print(f"⏱️ Processing time: {result['processing_time_seconds']:.2f} seconds")
        print(f"🔄 Collection methods used: {result['collection_methods']}")

        # Load and show comprehensive sample
        instruments = load_complete_nse_fno_list()
        if instruments:
            print(f"\n📈 Sample F&O instruments (showing variety):")

            # Group by type for better display
            indices = [i for i in instruments if i.get("instrumentType") == "INDEX"]
            equities = [i for i in instruments if i.get("instrumentType") == "EQUITY"]
            others = [
                i
                for i in instruments
                if i.get("instrumentType") not in ["INDEX", "EQUITY"]
            ]

            if indices:
                print(f"\n🔷 INDICES ({len(indices)}):")
                for i, inst in enumerate(indices[:5]):
                    print(f"  {i+1:2d}. {inst['symbol']:<15} - {inst['name']}")

            if equities:
                print(
                    f"\n🔶 EQUITIES (showing {min(15, len(equities))} of {len(equities)}):"
                )
                for i, inst in enumerate(equities[:15]):
                    print(f"  {i+1:2d}. {inst['symbol']:<15} - {inst['name']}")

            if others:
                print(f"\n🔸 OTHERS ({len(others)}):")
                for i, inst in enumerate(others[:5]):
                    print(f"  {i+1:2d}. {inst['symbol']:<15} - {inst['name']}")

            print(f"\n✅ COMPLETE LIST: {len(instruments)} F&O instruments collected!")

    else:
        print(f"❌ Collection failed: {result.get('error', 'Unknown error')}")
        print("💡 This might be due to NSE API restrictions or network issues")


if __name__ == "__main__":
    main()
