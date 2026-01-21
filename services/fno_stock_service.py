import asyncio
import json
import logging
import os
import re
from datetime import datetime, time as dt_time
from pathlib import Path
from typing import List, Dict, Optional, Any
import pytz
import pandas as pd
from playwright.async_api import async_playwright

# Import sector mapping
try:
    from services.sector_mapping import SYMBOL_TO_SECTOR, get_sector_for_stock
except ImportError:
    # Fallback if import fails
    SYMBOL_TO_SECTOR = {}

    def get_sector_for_stock(symbol):
        return None


try:
    from utils.logging_utils import log_structured
except ImportError:

    def log_structured(event, level="INFO", message="", data=None):
        pass


logger = logging.getLogger(__name__)


class FnoStockListService:
    """
    F&O stock list fetcher using Playwright to scrape Dhan website.
    """

    def __init__(self):
        self.base_url = "https://dhan.co/nse-fno-lot-size/"

        # Market schedule integration
        self.ist = pytz.timezone("Asia/Kolkata")
        self.market_hours = {
            "early_start": dt_time(8, 0),  # 8:00 AM - Early preparation
            "premarket": dt_time(9, 0),  # 9:00 AM - Pre-market
            "market_open": dt_time(9, 15),  # 9:15 AM - Market open
            "market_close": dt_time(15, 30),  # 3:30 PM - Market close
        }

        # File path for saving JSON
        self.json_file_path = Path("data/fno_stock_list.json")
        self.downloads_dir = Path("./downloads")
        self.downloads_dir.mkdir(exist_ok=True)

        # Manual symbol mapping for missing symbols - ENHANCED
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
            "3360 One WAM": "360ONE",  # Handle data typo
            "60 One WAM": "360ONE",  # Handle another variant of the typo
        }

        # Preferred symbols for companies with multiple symbols
        self.preferred_symbols = {
            "HDFC Bank": "HDFCBANK",  # Prefer HDFCBANK over HDFC
            "ICICI Bank": "ICICIBANK",  # Prefer ICICIBANK over ICICI
            "LIC of India": "LICI",  # Prefer LICI over LIC
            "HCL Technologies": "HCLTECH",  # Prefer HCLTECH over HCL
            "Adani Ports & SEZ": "ADANIPORTS",  # Prefer ADANIPORTS over SEZ
            "JSW Steel": "JSWSTEEL",  # Prefer JSWSTEEL over JSW
            "SBI Life Insurance": "SBILIFE",  # Prefer SBILIFE over SBI
        }

        # Actual indices (not bank stocks)
        self.actual_indices = {
            "NIFTY",
            "BANKNIFTY",
            "FINNIFTY",
            "MIDCPNIFTY",
            "NIFTY-NEXT50",
        }

        # Last update tracking for market schedule compliance
        self.last_update_time = None
        self.update_required_hours = [
            8,
            9,
        ]  # Update during early preparation and premarket
        
        # Error tracking
        self.last_error: Optional[str] = None

    def is_market_schedule_compliant(self) -> Dict[str, Any]:
        """
        Check if current time aligns with market schedule for FNO updates
        """
        try:
            current_time = datetime.now(self.ist)
            current_dt_time = current_time.time()
            current_hour = current_time.hour

            # Check if it's a weekday
            if current_time.weekday() >= 5:
                return {
                    "compliant": False,
                    "reason": "weekend",
                    "message": "Market closed - Weekend",
                    "next_update_time": "Monday 08:00 AM",
                }

            # Check if within update hours (8 AM or 9 AM)
            if current_hour in self.update_required_hours:
                return {
                    "compliant": True,
                    "reason": "update_window",
                    "message": f"Within update window: {current_hour}:00 AM",
                    "current_time": current_time.strftime("%H:%M:%S"),
                }

            # Check if data is stale (older than 1 day)
            if self.json_file_path.exists():
                file_mtime = datetime.fromtimestamp(
                    self.json_file_path.stat().st_mtime, tz=self.ist
                )
                hours_old = (current_time - file_mtime).total_seconds() / 3600

                if hours_old > 24:
                    return {
                        "compliant": True,
                        "reason": "stale_data",
                        "message": f"Data is {hours_old:.1f} hours old, refresh needed",
                        "last_update": file_mtime.strftime("%Y-%m-%d %H:%M:%S"),
                    }

            # During market hours, use existing data
            if (
                self.market_hours["market_open"]
                <= current_dt_time
                <= self.market_hours["market_close"]
            ):
                return {
                    "compliant": False,
                    "reason": "market_hours",
                    "message": "Market is open - avoiding updates during trading hours",
                    "next_update_time": "Tomorrow 08:00 AM",
                }

            return {
                "compliant": True,
                "reason": "off_hours",
                "message": "Market closed - safe to update",
                "current_time": current_time.strftime("%H:%M:%S"),
            }

        except Exception as e:
            logger.error(f"Market schedule compliance check failed: {e}")
            self.last_error = f"Schedule compliance check failed: {str(e)}"
            return {
                "compliant": True,
                "reason": "error_fallback",
                "message": f"Compliance check error: {str(e)}",
            }

    async def get_fno_stocks(self) -> List[Dict[str, str]]:
        """
        Get F&O stocks using Playwright
        """
        # Check market schedule compliance first
        compliance_check = self.is_market_schedule_compliant()

        if not compliance_check["compliant"]:
            logger.info(f"⏰ Market schedule check: {compliance_check['message']}")

            # Try to load existing data if available
            existing_data = self.load_from_json()
            if existing_data:
                logger.info(f"📂 Using existing FNO data: {len(existing_data)} stocks")
                return existing_data
            else:
                logger.warning(
                    "No existing data available, proceeding with update despite schedule"
                )
        else:
            logger.info(f"✅ Market schedule compliant: {compliance_check['message']}")

        logger.info("🎯 Starting F&O stocks collection using Playwright...")

        # Record update time
        self.last_update_time = datetime.now(self.ist)

        raw_data = await self._fetch_dhan_data()
        if not raw_data:
            logger.error("❌ Failed to fetch data from Dhan")
            return []

        # Process and clean the data
        all_stocks = []
        for item in raw_data:
            # Handle different possible key names from scraping
            name = (
                item.get("All Companies")
                or item.get("Company Name")
                or item.get("NAME")
                or item.get("Underlying")
                or ""
            )
            raw_symbol = item.get("Symbol") or item.get("SYMBOL") or ""

            if not name and not raw_symbol:
                continue

            cleaned_name = self._clean_name(name)
            cleaned_symbol = self._clean_symbol(raw_symbol)

            stock = {"name": cleaned_name, "symbol": cleaned_symbol}
            if self._is_valid_stock(stock):
                all_stocks.append(stock)

        # Deduplicate using the working logic
        unique_stocks = self._deduplicate_stocks(all_stocks)

        # FIXED: Add explicit index entries with proper exchange field
        index_entries = [
            {"name": "Nifty 50", "symbol": "NIFTY", "exchange": "NSE"},
            {"name": "Nifty Bank", "symbol": "BANKNIFTY", "exchange": "NSE"},
            {"name": "Finnifty", "symbol": "FINNIFTY", "exchange": "NSE"},
            {"name": "Nifty Midcap Select", "symbol": "MIDCPNIFTY", "exchange": "NSE"},
            {"name": "Nifty Next 50", "symbol": "NIFTY-NEXT50", "exchange": "NSE"},
        ]

        # FIXED: Always add indices
        for index_entry in index_entries:
            # Check if this index is already in the data
            already_exists = any(
                stock.get("symbol", "").upper() == index_entry["symbol"]
                for stock in unique_stocks
            )
            if not already_exists:
                unique_stocks.append(index_entry)
                logger.info(
                    f"➕ Added index: {index_entry['name']} ({index_entry['symbol']})"
                )

        # Convert to the format we need and fill missing symbols
        result = []
        fixed_symbols = 0

        for stock in unique_stocks:
            name = stock.get("name", "").strip()
            symbol = stock.get("symbol", "").strip()

            # Fill missing symbol using manual mapping
            if not symbol and name in self.missing_symbols_map:
                symbol = self.missing_symbols_map[name]
                fixed_symbols += 1

            # Also check if this is an index name that needs symbol mapping
            if not symbol:
                name_lower = name.lower()
                if "nifty 50" in name_lower or name_lower == "nifty":
                    symbol = "NIFTY"
                    fixed_symbols += 1
                elif "nifty bank" in name_lower or "bank nifty" in name_lower:
                    symbol = "BANKNIFTY"
                    fixed_symbols += 1
                elif "finnifty" in name_lower or "fin nifty" in name_lower:
                    symbol = "FINNIFTY"
                    fixed_symbols += 1
                elif "midcap" in name_lower and "nifty" in name_lower:
                    symbol = "MIDCPNIFTY"
                    fixed_symbols += 1
                elif "next 50" in name_lower and "nifty" in name_lower:
                    symbol = "NIFTY-NEXT50"
                    fixed_symbols += 1

            # Only add stocks with valid data and proper validation
            if name and len(name.strip()) >= 3:  # Must have meaningful name
                # Ensure we have a valid symbol
                final_symbol = symbol
                if not final_symbol:
                    # Generate symbol from name as fallback
                    final_symbol = self._generate_symbol_from_name(name)

                # Validate the symbol
                if self._is_valid_symbol(final_symbol):
                    result.append(
                        {
                            "name": name,
                            "symbol": final_symbol,
                            "exchange": "NSE",
                        }
                    )

        # Separate indices from stocks for better organization
        indices = []
        stocks = []

        for item in result:
            if item["symbol"] in self.actual_indices:
                indices.append(item)
            else:
                stocks.append(item)

        # ENHANCED: Detailed data quality reporting
        total_count = len(result)
        indices_count = len(indices)
        stocks_count = len(stocks)

        logger.info(
            f"✅ F&O collection complete: {total_count} total ({indices_count} indices, {stocks_count} stocks), fixed {fixed_symbols} symbols"
        )

        # Return combined list but log the breakdown
        return result

    def _clean_symbol(self, raw_symbol: str) -> str:
        """
        Clean extracted symbol - removes suffixes and fixes format
        """
        if not raw_symbol:
            return ""

        symbol = str(raw_symbol).strip().upper()

        # Remove common suffixes from extracted data
        # Specifically remove 'BS' which is common in Dhan's lot size table
        if symbol.endswith("BS"):
            symbol = symbol[:-2]

        suffixes_to_remove = ["FUT", "OPT", "CE", "PE"]
        for suffix in suffixes_to_remove:
            if symbol.endswith(suffix):
                symbol = symbol[: -len(suffix)]
                break

        # Handle special cases and mappings
        symbol_mappings = {
            "NIFTY 50": "NIFTY",
            "NIFTY BANK": "BANKNIFTY",
            "NIFTY NEXT 50": "NIFTY-NEXT50",
            "NIFTYNXT50": "NIFTY-NEXT50",
            "360ONE": "360ONE",
        }

        if symbol in symbol_mappings:
            symbol = symbol_mappings[symbol]

        return symbol

    async def _fetch_dhan_data(self):
        """
        Download NSE F&O lot size data from Dhan website using Playwright
        """
        async with async_playwright() as p:
            # Launch browser with anti-detection args
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                ],
                slow_mo=100,
            )

            # Create context with realistic User-Agent
            context = await browser.new_context(
                accept_downloads=True,
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )

            page = await context.new_page()

            # Add init script to hide webdriver property
            await page.add_init_script(
                """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """
            )

            try:
                logger.info("🌐 Navigating to Dhan website...")
                try:
                    await page.goto(
                        self.base_url, wait_until="domcontentloaded", timeout=60000
                    )
                except Exception as e:
                    logger.warning(
                        f"⚠️ Navigation timeout/error (continuing as data might be loaded): {e}"
                    )

                logger.info("⏳ Waiting for page to load completely...")
                await page.wait_for_timeout(5000)

                # Try extraction first as it's more reliable than download which often fails/times out
                logger.info("🔍 Attempting direct data extraction...")
                data = await self._extract_data_from_page(page)

                if data:
                    return data

                # If extraction fails, try download
                logger.info("⚠️ Extraction yielded no data, trying download button...")

                # Wait for download button and click it
                download_selectors = [
                    'button[aria-label*="download"]',
                    'button:has-text("Download")',
                    '[data-testid*="download"]',
                    ".download-btn",
                    'button:has-text("Export")',
                    'a[href*="download"]',
                    'button[title*="download"]',
                    'a[class*="download"]',
                ]

                download_button = None
                for selector in download_selectors:
                    try:
                        download_button = await page.wait_for_selector(
                            selector, timeout=2000
                        )
                        if download_button:
                            logger.info(
                                f"✅ Found download button with selector: {selector}"
                            )
                            break
                    except:
                        continue

                if download_button:
                    logger.info("📥 Starting download...")
                    try:
                        async with page.expect_download(timeout=10000) as download_info:
                            await download_button.click()

                        download = await download_info.value
                        download_path = self.downloads_dir / download.suggested_filename
                        await download.save_as(download_path)

                        logger.info(f"✅ File downloaded successfully: {download_path}")
                        return await self._process_downloaded_file(download_path)
                    except Exception as e:
                        logger.warning(f"⚠️ Download failed: {e}")

                return None

            except Exception as e:
                logger.error(f"❌ Error during fetching: {e}")
                return None

            finally:
                await browser.close()

    async def _extract_data_from_page(self, page):
        """
        Extract data directly from the page
        """
        try:
            logger.info("🔍 Extracting data directly from page...")

            # Explicitly wait for table
            try:
                await page.wait_for_selector("table", timeout=10000)
            except:
                logger.warning("⚠️ Table element not found within timeout")

            # Extract table data
            data = await page.evaluate(
                """
                () => {
                    const tables = document.querySelectorAll('table, .table, [role="table"]');
                    let allData = [];
                    
                    tables.forEach(table => {
                        const rows = table.querySelectorAll('tr');
                        let headers = [];
                        let tableData = [];
                        
                        rows.forEach((row, index) => {
                            const cells = row.querySelectorAll('th, td');
                            const rowData = Array.from(cells).map(cell => cell.textContent.trim());
                            
                            // Try to detect header row
                            if (index === 0 && (row.querySelectorAll('th').length > 0 || rowData.some(t => t.toLowerCase().includes('symbol')))) {
                                headers = rowData;
                            } else if (rowData.length > 0) {
                                if (headers.length > 0) {
                                    const obj = {};
                                    rowData.forEach((cell, i) => {
                                        obj[headers[i] || `column_${i}`] = cell;
                                    });
                                    tableData.push(obj);
                                } else {
                                    // Fallback: create object with generic keys if no header
                                    const obj = {};
                                    rowData.forEach((cell, i) => {
                                        obj[`col_${i}`] = cell;
                                    });
                                    // Try to map known columns if header missing
                                    if (rowData.length >= 2) {
                                        obj['All Companies'] = rowData[0]; // Assumption
                                        obj['Symbol'] = rowData[1]; // Assumption
                                    }
                                    tableData.push(obj);
                                }
                            }
                        });
                        
                        if (tableData.length > 0) {
                            allData.push(...tableData);
                        }
                    });
                    
                    return allData;
                }
            """
            )

            if data and len(data) > 0:
                logger.info(f"📊 Records extracted from page: {len(data)}")
                return data
            else:
                logger.error("❌ No data found on the page")
                return None

        except Exception as e:
            logger.error(f"❌ Error extracting data from page: {e}")
            return None

    async def _process_downloaded_file(self, file_path):
        """
        Process the downloaded file and extract data
        """
        try:
            file_extension = file_path.suffix.lower()

            if file_extension == ".json":
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data

            elif file_extension in [".csv", ".xlsx", ".xls"]:
                if file_extension == ".csv":
                    df = pd.read_csv(file_path)
                else:
                    df = pd.read_excel(file_path)

                # Convert to list of dictionaries
                data = df.to_dict("records")
                return data

            else:
                logger.warning(f"⚠️ Unsupported file format: {file_extension}")
                return None

        except Exception as e:
            logger.error(f"❌ Error processing downloaded file: {e}")
            return None

    def _clean_name(self, name_text: str) -> str:
        """Clean stock name - enhanced to handle special cases like 360 One WAM"""
        if not name_text:
            return ""

        cleaned = str(name_text).strip()

        # FIXED: Handle specific case of 360 One WAM being corrupted to 3360
        if cleaned == "3360 One WAM":
            return "360 One WAM"

        # Fix duplicate first characters (NNifty -> Nifty) but SKIP for numbers
        if (
            len(cleaned) > 1
            and cleaned[0] == cleaned[1]
            and cleaned[0].isupper()
            and not cleaned[0].isdigit()
        ):
            cleaned = cleaned[1:]

        # ADDITIONAL FIX: Handle number-starting names more carefully
        # Don't apply duplicate removal to names starting with numbers
        if len(cleaned) > 3 and cleaned.startswith("3360"):
            # This is likely a corrupted "360" - fix it
            if "One WAM" in cleaned:
                cleaned = "360 One WAM"

        # Remove common suffixes
        cleaned = re.sub(
            r"\s*(Invest|Buy|Sell|Limited|Ltd\.?)\s*$", "", cleaned, flags=re.IGNORECASE
        )

        # Clean whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        return cleaned

    def _normalize_company_name(self, name: str) -> str:
        """Normalize company name for better deduplication"""
        if not name:
            return ""

        # Fix common data issues first
        if name == "3360 One WAM":
            name = "360 One WAM"

        normalized = name.strip()

        # Convert to lowercase for comparison
        normalized = normalized.lower()

        # Remove common suffixes and words
        remove_suffixes = [
            r"\s+limited\s*$",
            r"\s+ltd\.?\s*$",
            r"\s+ltd\s*$",
            r"\s+company\s*$",
            r"\s+co\.?\s*$",
            r"\s+corp\.?\s*$",
            r"\s+corporation\s*$",
            r"\s+enterprises\s*$",
            r"\s+industries\s*$",
            r"\s+inc\.?\s*$",
            r"\s+private\s*$",
            r"\s+pvt\.?\s*$",
            r"\s+group\s*$",
            r"\s+holding\s*$",
        ]

        for suffix in remove_suffixes:
            normalized = re.sub(suffix, "", normalized, flags=re.IGNORECASE)

        # Normalize common variations
        normalized = re.sub(r"\s+&\s+", " and ", normalized)
        normalized = re.sub(r"\s+technologies\s*$", " tech", normalized)
        normalized = re.sub(r"\s+financial\s+services\s*$", " fin", normalized)
        normalized = re.sub(r"\s+pharmaceuticals?\s*$", " pharma", normalized)

        # Clean whitespace
        normalized = re.sub(r"\s+", " ", normalized).strip()

        return normalized

    def _is_valid_stock(self, stock: dict) -> bool:
        """Validate stock data"""
        name = stock.get("name", "").strip()

        if not name or len(name) < 3:
            return False

        # Skip invalid entries (but be specific to avoid false positives)
        invalid_patterns = [
            r"^total\s",
            r"\btotal\s+results",
            r"\bshowing\s",
            r"\bresults\b",
            r"\bdownload\b",
        ]
        name_lower = name.lower()
        for pattern in invalid_patterns:
            if re.search(pattern, name_lower):
                return False

        return True

    def _deduplicate_stocks(self, all_stocks: list) -> list:
        """Enhanced deduplication with company name normalization and preferred symbols"""
        if not all_stocks:
            return []

        # Group by normalized company name
        company_groups = {}

        for stock in all_stocks:
            name = stock.get("name", "").strip()
            symbol = stock.get("symbol", "").strip().upper()

            if not self._is_valid_stock(stock):
                continue

            # Fix common name issues
            if name == "3360 One WAM":
                name = "360 One WAM"
                stock["name"] = name

            # Clean name
            name = self._clean_name(name)
            stock["name"] = name

            # Normalize company name for grouping
            normalized_name = self._normalize_company_name(name)

            if normalized_name not in company_groups:
                company_groups[normalized_name] = []

            company_groups[normalized_name].append(
                {"original_name": name, "symbol": symbol, "stock": stock}
            )

        # Select best entry from each group
        unique_stocks = []

        for normalized_name, entries in company_groups.items():
            if len(entries) == 1:
                # Single entry - just add it
                unique_stocks.append(entries[0]["stock"])
            else:
                # Multiple entries - select the best one
                best_entry = self._select_best_entry(entries)
                if best_entry:
                    unique_stocks.append(best_entry["stock"])

        # Filter out non-F&O eligible items
        filtered_stocks = []
        for stock in unique_stocks:
            if self._is_fno_eligible(stock):
                filtered_stocks.append(stock)

        return filtered_stocks

    def _select_best_entry(self, entries: list) -> dict:
        """Select the best entry from multiple entries for the same company"""
        if not entries:
            return None

        # Get the original name (first entry's name for reference)
        original_name = entries[0]["original_name"]

        # Check if we have a preferred symbol for this company
        if original_name in self.preferred_symbols:
            preferred_symbol = self.preferred_symbols[original_name]
            for entry in entries:
                if entry["symbol"] == preferred_symbol:
                    return entry

        # Scoring system for best entry
        scored_entries = []

        for entry in entries:
            score = 0
            symbol = entry["symbol"]

            # Score based on symbol quality
            if symbol:
                # Prefer longer symbols (more specific)
                score += len(symbol) * 2

                # Prefer symbols that match company name
                name_words = original_name.upper().split()
                if any(word in symbol for word in name_words):
                    score += 10

                # Prefer symbols without generic patterns
                if not re.search(r"^(SBI|LIC|HCL|JSW)$", symbol):
                    score += 5

                # Prefer symbols with company-specific patterns
                if re.search(r"(BANK|TECH|STEEL|LIFE|PORTS)", symbol):
                    score += 3

            scored_entries.append((score, entry))

        # Sort by score (descending) and return the best
        scored_entries.sort(key=lambda x: x[0], reverse=True)
        return scored_entries[0][1]

    def _is_fno_eligible(self, stock: dict) -> bool:
        """Check if a stock is eligible for F&O trading"""
        name = stock.get("name", "").strip()
        symbol = stock.get("symbol", "").strip()

        # Skip if no valid name or symbol
        if not name or not symbol:
            return False

        # Always include actual indices
        if symbol in self.actual_indices:
            return True

        # Skip items that are clearly not individual stocks (but be specific to avoid false positives)
        skip_patterns = [
            r"^gold$",
            r"^silver$",
            r"^crude oil$",
            r"natural gas futures",
            r"^commodity",
            r"currency",
            r"forex",
            r"bond",
            r"treasury",
            r"etf$",
            r"index fund",
        ]

        name_lower = name.lower()
        for pattern in skip_patterns:
            if re.search(pattern, name_lower):
                return False

        # Special handling for index names that might not have been scraped as symbols
        index_name_patterns = [
            r"nifty\s+50",
            r"nifty\s+bank",
            r"nifty.*bank",
            r"bank.*nifty",
            r"finnifty",
            r"fin\s*nifty",
            r"nifty.*midcap",
            r"midcap.*nifty",
            r"nifty.*next.*50",
        ]

        for pattern in index_name_patterns:
            if re.search(pattern, name_lower):
                return True

        return True

    def _generate_symbol_from_name(self, name: str) -> str:
        """Generate a trading symbol from company name"""
        if not name:
            return ""

        # Clean and normalize the name
        clean_name = name.strip().upper()

        # Remove common suffixes and words
        remove_words = [
            "LIMITED",
            "LTD",
            "LTD.",
            "COMPANY",
            "CO",
            "CO.",
            "CORPORATION",
            "CORP",
            "CORP.",
            "ENTERPRISES",
            "GROUP",
            "INDUSTRIES",
            "INC",
            "INC.",
            "PVT",
            "PRIVATE",
            "&",
            "AND",
            "THE",
            "INDIA",
            "INDIAN",
        ]

        words = clean_name.split()
        filtered_words = []

        for word in words:
            # Remove punctuation
            word = re.sub(r"[^\w]", "", word)
            if word and word not in remove_words and len(word) > 1:
                filtered_words.append(word)

        if not filtered_words:
            # Fallback: use first few characters of original name
            return re.sub(r"[^\w]", "", name.upper())[:8]

        # Create symbol from first letters or abbreviation
        if len(filtered_words) == 1:
            return filtered_words[0][:8]  # Max 8 chars
        elif len(filtered_words) <= 3:
            return "".join(filtered_words)[:8]
        else:
            # Use first letter of each word, max 8 chars
            return "".join(word[0] for word in filtered_words[:8])

    def _is_valid_symbol(self, symbol: str) -> bool:
        """Validate if a symbol is proper for trading"""
        if not symbol:
            return False

        # Clean symbol
        symbol = symbol.strip().upper()

        # Check basic format - allow numbers at start for symbols like 360ONE
        if not re.match(r"^[A-Z0-9\-&]+$", symbol):
            return False

        # Length check
        if len(symbol) < 2 or len(symbol) > 12:
            return False

        # Avoid invalid patterns but allow 360ONE style symbols
        invalid_patterns = [
            r"^\d+$",  # All numbers only
            r"[_]{2,}",  # Multiple underscores
        ]

        for pattern in invalid_patterns:
            if re.search(pattern, symbol):
                return False

        # Special case: allow symbols that start with numbers if they contain letters (like 360ONE)
        if re.match(r"^\d+[A-Z]+", symbol):
            return True

        # Standard validation: must start with letter or be a known valid symbol
        if not re.match(r"^[A-Z]", symbol) and symbol not in ["360ONE"]:
            return False

        return True

    def save_to_json(self, stocks: List[Dict[str, str]]) -> bool:
        """Save stocks to JSON file"""
        try:
            data = {
                "securities": stocks,
                "last_updated": datetime.now().isoformat(),
                "total_count": len(stocks),
                "data_source": "dhan_playwright",
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

    async def update_fno_list(self) -> Dict[str, any]:
        """Main method to update F&O stock list"""
        start_time = datetime.now()
        logger.info(" 🚀 Starting F&O stock list update...")
        log_structured(
            event="FNO_LIST_UPDATE_START",
            message="Starting F&O stock list update process",
        )

        try:
            # Fetch fresh data using Playwright
            stocks = await self.get_fno_stocks()

            if not stocks:
                logger.warning("No stocks fetched, keeping existing data")
                log_structured(
                    event="FNO_LIST_UPDATE_FAILED",
                    level="WARNING",
                    message="No stocks fetched from source",
                )
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

            logger.info(
                f"Γ£à F&O stock list update completed in {processing_time:.2f}s"
            )
            log_structured(
                event="FNO_LIST_UPDATE_COMPLETE",
                message=f"F&O stock list update completed: {len(stocks)} stocks",
                data=result,
            )
            self.last_error = None  # Clear error on success
            return result

        except Exception as e:
            logger.error(f"Γ¥î F&O stock list update failed: {e}")
            log_structured(event="FNO_LIST_UPDATE_ERROR", level="ERROR", message=str(e))
            self.last_error = f"FNO list update failed: {str(e)}"
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def get_categorized_fno_data(self) -> Dict[str, any]:
        """Get F&O data separated into indices and stocks with metadata and sector mapping"""
        # Note: This loads from file, so no async needed
        all_data = self.load_from_json()
        if not all_data:
            # Fallback if file not exists/empty
            return {"indices": [], "stocks": [], "metadata": {}}

        # Enhance data with sector information
        enhanced_data = []
        for item in all_data:
            enhanced_item = item.copy()
            symbol = item.get("symbol")

            if symbol:
                # Get sector from mapping
                sector = get_sector_for_stock(symbol)
                if sector:
                    enhanced_item["sector"] = sector
                else:
                    # Determine sector based on symbol for indices
                    if symbol in self.actual_indices:
                        enhanced_item["sector"] = "INDEX"
                    else:
                        enhanced_item["sector"] = (
                            "F&O"  # Default for F&O stocks without mapping
                        )
            else:
                enhanced_item["sector"] = "UNKNOWN"

            enhanced_data.append(enhanced_item)

        # Separate into indices and stocks
        indices = []
        stocks = []

        for item in enhanced_data:
            if item["symbol"] in self.actual_indices:
                indices.append(item)
            else:
                stocks.append(item)

        return {
            "indices": indices,
            "stocks": stocks,
            "metadata": {
                "total_count": len(enhanced_data),
                "indices_count": len(indices),
                "stocks_count": len(stocks),
                "last_updated": datetime.now().isoformat(),
            },
        }

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
                "error": "An internal error occurred while fixing missing symbols.",
                "timestamp": datetime.now().isoformat(),
            }


# Standalone functions for easy integration
def update_fno_stock_list() -> Dict[str, any]:
    """Standalone function to update F&O stock list"""
    service = FnoStockListService()
    # Since we are calling async method from sync function
    return asyncio.run(service.update_fno_list())


def get_fno_stocks_from_file() -> List[Dict[str, str]]:
    """Get F&O stocks from saved JSON file with sector mapping"""
    service = FnoStockListService()
    stocks = service.load_from_json()

    # Enhance each stock with sector information
    enhanced_stocks = []
    for stock in stocks:
        enhanced_stock = stock.copy()
        symbol = stock.get("symbol")

        if symbol:
            # Get sector from mapping
            sector = get_sector_for_stock(symbol)
            if sector:
                enhanced_stock["sector"] = sector
            else:
                # Determine sector based on symbol for indices
                if symbol in [
                    "NIFTY",
                    "BANKNIFTY",
                    "FINNIFTY",
                    "MIDCPNIFTY",
                    "NIFTY-NEXT50",
                ]:
                    enhanced_stock["sector"] = "INDEX"
                else:
                    enhanced_stock["sector"] = (
                        "F&O"  # Default for F&O stocks without mapping
                    )
        else:
            enhanced_stock["sector"] = "UNKNOWN"

        enhanced_stocks.append(enhanced_stock)

    return enhanced_stocks


def get_categorized_fno_data() -> Dict[str, any]:
    """Get F&O data separated into indices and stocks with metadata and sector mapping"""
    service = FnoStockListService()
    return service.get_categorized_fno_data()


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
    try:
        result = update_fno_stock_list()
        print(f"Update result: {result}")
    except Exception as e:
        print(f"Update failed: {e}")


if __name__ == "__main__":
    main()
