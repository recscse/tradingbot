
"""
Simple Dhan F&O Scraper - Name and Symbol Only
==============================================

Gets F&O stocks with only name and symbol columns.

Requirements:
pip install requests beautifulsoup4 pandas
"""

import requests
import pandas as pd
from bs4 import BeautifulSoup
import re
import time
from datetime import datetime
import logging


class SimpleDhanScraper:
    """
    Simple scraper for name and symbol only
    """

    def __init__(self):
        self.base_url = "https://dhan.co"

        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Setup session
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Connection": "keep-alive",
            }
        )

    def get_fno_stocks(self) -> pd.DataFrame:
        """
        Get F&O stocks with name and symbol only
        """
        self.logger.info("🎯 Getting F&O stocks (name and symbol only)...")

        all_stocks = []

        # Method 1: Futures pagination
        futures_stocks = self._get_futures_pagination()
        if futures_stocks:
            all_stocks.extend(futures_stocks)
            self.logger.info(f"✅ Futures: {len(futures_stocks)} stocks")

        # Method 2: F&O lot size
        lot_size_stocks = self._get_fno_lot_size()
        if lot_size_stocks:
            all_stocks.extend(lot_size_stocks)
            self.logger.info(f"✅ Lot size: {len(lot_size_stocks)} stocks")

        # Method 3: Options pagination
        options_stocks = self._get_options_pagination()
        if options_stocks:
            all_stocks.extend(options_stocks)
            self.logger.info(f"✅ Options: {len(options_stocks)} stocks")

        # Deduplicate
        unique_stocks = self._deduplicate_stocks(all_stocks)
        self.logger.info(f"📊 Total unique stocks: {len(unique_stocks)}")

        # Convert to DataFrame with only name and symbol
        df = self._create_dataframe(unique_stocks)

        return df

    def _get_futures_pagination(self) -> list:
        """Get futures stocks via pagination"""
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
                self.logger.error(f"Futures page {page} failed: {e}")
                break

        return all_stocks

    def _get_fno_lot_size(self) -> list:
        """Get F&O stocks from lot size page"""
        try:
            url = f"{self.base_url}/nse-fno-lot-size/"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            return self._parse_html_page(response.text)

        except Exception as e:
            self.logger.error(f"F&O lot size failed: {e}")
            return []

    def _get_options_pagination(self) -> list:
        """Get options stocks via pagination"""
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
                self.logger.error(f"Options page {page} failed: {e}")
                break

        return all_stocks

    def _parse_html_page(self, html_content: str) -> list:
        """Parse HTML page and extract name and symbol only"""
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
        """Extract only name and symbol from table row"""
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
        """Clean stock name"""
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
        """Extract stock symbol"""
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
        """Check if row is header"""
        text = row.get_text().lower()
        return any(term in text for term in ["name", "symbol", "ltp", "lot size"])

    def _is_valid_stock(self, stock: dict) -> bool:
        """Validate stock data"""
        name = stock.get("name", "").strip()

        if not name or len(name) < 3:
            return False

        # Skip invalid entries
        invalid_terms = ["total", "showing", "results", "download"]
        if any(term in name.lower() for term in invalid_terms):
            return False

        return True

    def _deduplicate_stocks(self, all_stocks: list) -> list:
        """Remove duplicate stocks"""
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

    def _create_dataframe(self, stocks: list) -> pd.DataFrame:
        """Create DataFrame with only name and symbol"""
        # Extract only name and symbol
        data = []
        for stock in stocks:
            data.append(
                {"name": stock.get("name", ""), "symbol": stock.get("symbol", "")}
            )

        # Create DataFrame
        df = pd.DataFrame(data)

        # Ensure columns exist
        if "name" not in df.columns:
            df["name"] = ""
        if "symbol" not in df.columns:
            df["symbol"] = ""

        # Reorder columns
        df = df[["name", "symbol"]]

        return df

    def save_csv(self, df: pd.DataFrame, filename: str = None) -> str:
        """Save DataFrame to CSV"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"dhan_fno_name_symbol_{timestamp}.csv"

        df.to_csv(filename, index=False)
        self.logger.info(f"💾 Data saved to: {filename}")
        return filename


def main():
    """Main function"""
    print("🚀 Simple Dhan F&O Scraper - Name & Symbol Only")
    print("=" * 50)

    scraper = SimpleDhanScraper()

    try:
        # Get F&O stocks
        df = scraper.get_fno_stocks()

        print(f"\n📊 RESULTS:")
        print(f"   Total Stocks: {len(df)}")

        # Save to CSV
        filename = scraper.save_csv(df)
        print(f"   Saved to: {filename}")

        # Show sample data
        print(f"\n📋 Sample data (first 15 rows):")
        print(df.head(15).to_string(index=False))

        # Show symbol completeness
        symbols_filled = len(df[df["symbol"] != ""])
        symbol_percentage = (symbols_filled / len(df) * 100) if len(df) > 0 else 0
        print(
            f"\n📊 Symbol completeness: {symbols_filled}/{len(df)} ({symbol_percentage:.1f}%)"
        )

        print(f"\n🎉 SUCCESS! {len(df)} F&O stocks with name and symbol")

        return df

    except Exception as e:
        print(f"\n❌ Failed: {e}")


if __name__ == "__main__":
    main()
