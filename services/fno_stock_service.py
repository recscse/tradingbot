import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
import re
import time

logger = logging.getLogger(__name__)


class FnoStockListService:
    """
    Simple F&O stock list fetcher using the working scraper logic.
    Based on the proven SimpleDhanScraper code.
    """

    def __init__(self):
        self.base_url = "https://dhan.co"

        # File path for saving JSON
        self.json_file_path = Path("data/fno_stock_list.json")

        # Setup session like the working scraper
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Connection": "keep-alive",
            }
        )

        # Manual symbol mapping for missing symbols
        self.missing_symbols_map = {
            "Mahindra & Mahindra": "M&M",
            "Bajaj Auto": "BAJAJ-AUTO",
            "M&M Financial Services": "M&MFIN",
            "Nifty Bank": "BANKNIFTY",
            "Finnifty": "FINNIFTY",
            "Nifty Midcap Select": "MIDCPNIFTY",
            "Nifty 50": "NIFTY",
            "Nifty Next 50": "NIFTY-NEXT50",
            "360 One WAM": "360ONE",
        }

    def get_fno_stocks(self) -> List[Dict[str, str]]:
        """
        Get F&O stocks with name and symbol - using working scraper logic
        """
        logger.info("🎯 Getting F&O stocks (name and symbol only)...")

        all_stocks = []

        # Method 1: Futures pagination
        futures_stocks = self._get_futures_pagination()
        if futures_stocks:
            all_stocks.extend(futures_stocks)
            logger.info(f"✅ Futures: {len(futures_stocks)} stocks")

        # Method 2: F&O lot size
        lot_size_stocks = self._get_fno_lot_size()
        if lot_size_stocks:
            all_stocks.extend(lot_size_stocks)
            logger.info(f"✅ Lot size: {len(lot_size_stocks)} stocks")

        # Method 3: Options pagination
        options_stocks = self._get_options_pagination()
        if options_stocks:
            all_stocks.extend(options_stocks)
            logger.info(f"✅ Options: {len(options_stocks)} stocks")

        # Deduplicate using the working logic
        unique_stocks = self._deduplicate_stocks(all_stocks)
        logger.info(f"📊 Total unique stocks: {len(unique_stocks)}")

        # Convert to the format we need and fill missing symbols
        result = []
        for stock in unique_stocks:
            name = stock.get("name", "").strip()
            symbol = stock.get("symbol", "").strip()

            # Fill missing symbol using manual mapping
            if not symbol and name in self.missing_symbols_map:
                symbol = self.missing_symbols_map[name]
                logger.info(f"🔧 Fixed missing symbol for {name}: {symbol}")

            result.append(
                {
                    "name": name,
                    "symbol": symbol,
                    "exchange": "NSE",
                }
            )

        return result

    def fix_existing_json_symbols(
        self, input_file: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Fix missing symbols in existing JSON file
        """
        try:
            # Load existing data
            if input_file:
                file_path = Path(input_file)
            else:
                file_path = self.json_file_path

            if not file_path.exists():
                logger.error(f"File {file_path} does not exist")
                return {"status": "error", "error": "File not found"}

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            securities = data.get("securities", [])
            updated_count = 0

            # Fix missing symbols
            for security in securities:
                name = security.get("name", "").strip()
                symbol = security.get("symbol", "").strip()

                if not symbol and name in self.missing_symbols_map:
                    security["symbol"] = self.missing_symbols_map[name]
                    updated_count += 1
                    logger.info(
                        f"🔧 Fixed symbol for {name}: {self.missing_symbols_map[name]}"
                    )

            # Update metadata
            data["last_updated"] = datetime.now().isoformat()
            data["total_count"] = len(securities)

            # Save updated data
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ Updated {updated_count} missing symbols in {file_path}")

            return {
                "status": "success",
                "updated_count": updated_count,
                "total_securities": len(securities),
                "file_path": str(file_path),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"❌ Error fixing symbols: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def _get_futures_pagination(self) -> list:
        """Get futures stocks via pagination - exact copy from working code"""
        all_stocks = []
        page = 1

        while page <= 10:
            try:
                url = f"{self.base_url}/futures-stocks-list/?page={page}"
                response = self.session.get(url, timeout=30)

                if response.status_code != 200:
                    break

                page_stocks = self._parse_html_page(response.text)
                if not page_stocks:
                    break

                all_stocks.extend(page_stocks)
                page += 1
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"Futures page {page} failed: {e}")
                break

        return all_stocks

    def _get_fno_lot_size(self) -> list:
        """Get F&O stocks from lot size page - exact copy from working code"""
        try:
            url = f"{self.base_url}/nse-fno-lot-size/"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            return self._parse_html_page(response.text)

        except Exception as e:
            logger.error(f"F&O lot size failed: {e}")
            return []

    def _get_options_pagination(self) -> list:
        """Get options stocks via pagination - exact copy from working code"""
        all_stocks = []
        page = 1

        while page <= 10:
            try:
                url = f"{self.base_url}/options-stocks-list/?page={page}"
                response = self.session.get(url, timeout=30)

                if response.status_code != 200:
                    break

                page_stocks = self._parse_html_page(response.text)
                if not page_stocks:
                    break

                all_stocks.extend(page_stocks)
                page += 1
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"Options page {page} failed: {e}")
                break

        return all_stocks

    def _parse_html_page(self, html_content: str) -> list:
        """Parse HTML page - exact copy from working code"""
        soup = BeautifulSoup(html_content, "html.parser")
        stocks = []

        # Find table rows
        rows = soup.select("table tbody tr")
        if not rows:
            rows = soup.select("tbody tr")
        if not rows:
            rows = soup.select("tr")

        for row in rows:
            try:
                # Skip header rows
                if self._is_header_row(row):
                    continue

                stock = self._extract_name_symbol(row)
                if stock and self._is_valid_stock(stock):
                    stocks.append(stock)

            except:
                continue

        return stocks

    def _extract_name_symbol(self, row) -> dict:
        """Extract name and symbol - exact copy from working code"""
        try:
            cells = row.find_all(["td", "th"])
            if len(cells) < 1:
                return None

            # Extract and clean name
            name_text = cells[0].get_text(strip=True)
            name = self._clean_name(name_text)

            # Extract symbol
            symbol = self._extract_symbol(row, cells[0])

            return {"name": name, "symbol": symbol if symbol else ""}

        except:
            return None

    def _clean_name(self, name_text: str) -> str:
        """Clean stock name - exact copy from working code"""
        if not name_text:
            return ""

        cleaned = name_text.strip()

        # Fix duplicate first characters (NNifty -> Nifty)
        if len(cleaned) > 1 and cleaned[0] == cleaned[1] and cleaned[0].isupper():
            cleaned = cleaned[1:]

        # Remove common suffixes
        cleaned = re.sub(
            r"\s*(Invest|Buy|Sell|Limited|Ltd\.?)\s*$", "", cleaned, flags=re.IGNORECASE
        )

        # Clean whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        return cleaned

    def _extract_symbol(self, row, name_cell) -> str:
        """Extract symbol - exact copy from working code"""
        # Check image in name cell
        img = name_cell.find("img")
        if img:
            # Check alt text
            if img.get("alt"):
                match = re.search(r"\b([A-Z]{2,12})\b", img["alt"])
                if match:
                    return match.group(1)

            # Check src path
            if img.get("src"):
                match = re.search(r"/symbol/([A-Z]+)\.png", img["src"], re.IGNORECASE)
                if match:
                    return match.group(1).upper()

        # Check data attributes
        for attr in ["data-symbol", "data-stock"]:
            if name_cell.get(attr):
                symbol = name_cell[attr].strip().upper()
                if re.match(r"^[A-Z]{2,12}$", symbol):
                    return symbol

        # Look for symbol in parentheses
        text = name_cell.get_text()
        match = re.search(r"\(([A-Z]{2,12})\)", text)
        if match:
            return match.group(1)

        return ""

    def _is_header_row(self, row) -> bool:
        """Check if row is header - exact copy from working code"""
        text = row.get_text().lower()
        return any(term in text for term in ["name", "symbol", "ltp", "lot size"])

    def _is_valid_stock(self, stock: dict) -> bool:
        """Validate stock data - exact copy from working code"""
        name = stock.get("name", "").strip()

        if not name or len(name) < 3:
            return False

        # Skip invalid entries
        invalid_terms = ["total", "showing", "results", "download"]
        if any(term in name.lower() for term in invalid_terms):
            return False

        return True

    def _deduplicate_stocks(self, all_stocks: list) -> list:
        """Remove duplicates - exact copy from working code"""
        if not all_stocks:
            return []

        seen = {}
        unique_stocks = []

        for stock in all_stocks:
            name = stock.get("name", "").strip()
            symbol = stock.get("symbol", "").strip().upper()

            if not self._is_valid_stock(stock):
                continue

            # Create identifier
            if symbol and len(symbol) >= 2:
                identifier = f"SYM:{symbol}"
            else:
                clean_name = re.sub(r"[^\w\s]", "", name.lower())
                clean_name = re.sub(r"\s+", "_", clean_name.strip())
                identifier = f"NAME:{clean_name}"

            if identifier not in seen:
                seen[identifier] = stock
                unique_stocks.append(stock)
            else:
                # Merge symbols if missing
                existing = seen[identifier]
                if not existing.get("symbol") and stock.get("symbol"):
                    existing["symbol"] = stock.get("symbol")

        return unique_stocks

    def save_to_json(self, stocks: List[Dict[str, str]]) -> bool:
        """Save stocks to JSON file"""
        try:
            data = {
                "securities": stocks,
                "last_updated": datetime.now().isoformat(),
                "total_count": len(stocks),
                "data_source": "dhan_scraper",
            }

            with open(self.json_file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"💾 Saved {len(stocks)} F&O stocks to {self.json_file_path}")
            return True

        except Exception as e:
            logger.error(f"❌ Error saving to JSON: {e}")
            return False

    def load_from_json(self) -> List[Dict[str, str]]:
        """Load stocks from JSON file"""
        try:
            if not self.json_file_path.exists():
                logger.warning(f"JSON file {self.json_file_path} does not exist")
                return []

            with open(self.json_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            stocks = data.get("securities", [])
            logger.info(
                f"📂 Loaded {len(stocks)} F&O stocks from {self.json_file_path}"
            )
            return stocks

        except Exception as e:
            logger.error(f"❌ Error loading from JSON: {e}")
            return []

    def update_fno_list(self) -> Dict[str, any]:
        """Main method to update F&O stock list"""
        start_time = datetime.now()
        logger.info("🚀 Starting F&O stock list update...")

        try:
            # Fetch fresh data using working scraper logic
            stocks = self.get_fno_stocks()

            if not stocks:
                logger.warning("No stocks fetched, keeping existing data")
                return {
                    "status": "failed",
                    "error": "No stocks fetched",
                    "timestamp": datetime.now().isoformat(),
                }

            # Save to JSON
            saved = self.save_to_json(stocks)

            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            result = {
                "status": "success" if saved else "partial_success",
                "total_stocks": len(stocks),
                "file_saved": saved,
                "file_path": str(self.json_file_path),
                "processing_time_seconds": processing_time,
                "last_updated": datetime.now().isoformat(),
            }

            logger.info(f"✅ F&O stock list update completed in {processing_time:.2f}s")
            return result

        except Exception as e:
            logger.error(f"❌ F&O stock list update failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }


# Standalone functions for easy integration
def update_fno_stock_list() -> Dict[str, any]:
    """Standalone function to update F&O stock list"""
    service = FnoStockListService()
    return service.update_fno_list()


def get_fno_stocks_from_file() -> List[Dict[str, str]]:
    """Get F&O stocks from saved JSON file"""
    service = FnoStockListService()
    return service.load_from_json()


def fix_missing_symbols_in_json(input_file: str = None) -> Dict[str, any]:
    """Standalone function to fix missing symbols in existing JSON"""
    service = FnoStockListService()
    return service.fix_existing_json_symbols(input_file)


# For testing
def main():
    """Test function"""
    # Fix existing JSON file
    # print("Fixing missing symbols in existing JSON...")
    # fix_result = fix_missing_symbols_in_json("paste.txt")
    # print(f"Fix result: {fix_result}")

    # Or update from scratch
    result = update_fno_stock_list()
    print(f"Update result: {result}")

    # stocks = get_fno_stocks_from_file()
    # print(f"Loaded {len(stocks)} stocks from file")
    # if stocks:
    #     print("Sample stocks:")
    #     for stock in stocks[:5]:
    #         print(f"  {stock}")


if __name__ == "__main__":
    main()
