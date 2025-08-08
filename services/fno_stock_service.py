import asyncio
import json
import logging
from datetime import datetime, time as dt_time
from pathlib import Path
from typing import List, Dict, Optional, Any
import requests
from bs4 import BeautifulSoup
import re
import time
import pytz

logger = logging.getLogger(__name__)


class FnoStockListService:
    """
    Simple F&O stock list fetcher using the working scraper logic.
    Based on the proven SimpleDhanScraper code.
    """

    def __init__(self):
        self.base_url = "https://dhan.co"
        
        # Market schedule integration
        self.ist = pytz.timezone("Asia/Kolkata")
        self.market_hours = {
            'early_start': dt_time(8, 0),    # 8:00 AM - Early preparation
            'premarket': dt_time(9, 0),      # 9:00 AM - Pre-market
            'market_open': dt_time(9, 15),   # 9:15 AM - Market open
            'market_close': dt_time(15, 30)  # 3:30 PM - Market close
        }

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
            "60 One WAM": "360ONE",   # Handle another variant of the typo
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
            "NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NIFTY-NEXT50"
        }
        
        # Path to extracted data file
        self.extracted_data_path = Path("dhan_nse_fno_extracted.json")
        
        # Last update tracking for market schedule compliance
        self.last_update_time = None
        self.update_required_hours = [8, 9]  # Update during early preparation and premarket

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
                    "next_update_time": "Monday 08:00 AM"
                }
            
            # Check if within update hours (8 AM or 9 AM)
            if current_hour in self.update_required_hours:
                return {
                    "compliant": True,
                    "reason": "update_window",
                    "message": f"Within update window: {current_hour}:00 AM",
                    "current_time": current_time.strftime("%H:%M:%S")
                }
            
            # Check if data is stale (older than 1 day)
            if self.json_file_path.exists():
                file_mtime = datetime.fromtimestamp(self.json_file_path.stat().st_mtime, tz=self.ist)
                hours_old = (current_time - file_mtime).total_seconds() / 3600
                
                if hours_old > 24:
                    return {
                        "compliant": True,
                        "reason": "stale_data",
                        "message": f"Data is {hours_old:.1f} hours old, refresh needed",
                        "last_update": file_mtime.strftime("%Y-%m-%d %H:%M:%S")
                    }
            
            # During market hours, use existing data
            if self.market_hours['market_open'] <= current_dt_time <= self.market_hours['market_close']:
                return {
                    "compliant": False,
                    "reason": "market_hours",
                    "message": "Market is open - avoiding updates during trading hours",
                    "next_update_time": "Tomorrow 08:00 AM"
                }
            
            return {
                "compliant": True,
                "reason": "off_hours",
                "message": "Market closed - safe to update",
                "current_time": current_time.strftime("%H:%M:%S")
            }
            
        except Exception as e:
            logger.error(f"Market schedule compliance check failed: {e}")
            return {
                "compliant": True,
                "reason": "error_fallback", 
                "message": f"Compliance check error: {str(e)}"
            }
    
    def get_fno_stocks(self) -> List[Dict[str, str]]:
        """
        Get F&O stocks with name and symbol - with market schedule compliance
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
                logger.warning("No existing data available, proceeding with update despite schedule")
        else:
            logger.info(f"✅ Market schedule compliant: {compliance_check['message']}")
        
        logger.info("🎯 Starting F&O stocks collection...")
        
        # Record update time
        self.last_update_time = datetime.now(self.ist)

        all_stocks = []
        methods_used = []

        # Method 0: Try extracted data first (most reliable)
        extracted_stocks = self._get_extracted_dhan_data()
        if extracted_stocks:
            all_stocks.extend(extracted_stocks)
            methods_used.append(f"ExtractedData({len(extracted_stocks)})")
            logger.info(f"✅ Using extracted data as primary source: {len(extracted_stocks)} stocks")
        else:
            logger.info("⚠️ No extracted data found, falling back to scraping methods")

        # Method 1: Main futures stocks list (fallback)
        if len(all_stocks) < 200:  # Only if extracted data is insufficient
            main_futures_stocks = self._get_main_futures_list()
            if main_futures_stocks:
                all_stocks.extend(main_futures_stocks)
                methods_used.append(f"MainFutures({len(main_futures_stocks)})")
                
        # Method 1.5: Try alternative URLs for complete lists
        if len(all_stocks) < 200:  # Only if we need more data
            alt_stocks = self._get_alternative_sources() 
            if alt_stocks:
                all_stocks.extend(alt_stocks)
                methods_used.append(f"AltSources({len(alt_stocks)})")

        # Method 2: Futures pagination (backup)
        if len(all_stocks) < 200:  # Only if we need more data
            futures_stocks = self._get_futures_pagination()
            if futures_stocks:
                all_stocks.extend(futures_stocks)
                methods_used.append(f"Futures({len(futures_stocks)})")

        # Method 3: F&O lot size (backup)
        if len(all_stocks) < 200:  # Only if we need more data
            lot_size_stocks = self._get_fno_lot_size()
            if lot_size_stocks:
                all_stocks.extend(lot_size_stocks)
                methods_used.append(f"LotSize({len(lot_size_stocks)})")

        # Method 4: Options pagination (backup)
        if len(all_stocks) < 200:  # Only if we need more data
            options_stocks = self._get_options_pagination()
            if options_stocks:
                all_stocks.extend(options_stocks)
                methods_used.append(f"Options({len(options_stocks)})")

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
        
        # FIXED: Always add indices (they're not scraped from dhan.co)
        for index_entry in index_entries:
            # Check if this index is already in the data
            already_exists = any(
                stock.get("symbol", "").upper() == index_entry["symbol"]
                for stock in unique_stocks
            )
            if not already_exists:
                unique_stocks.append(index_entry)
                logger.info(f"➕ Added index: {index_entry['name']} ({index_entry['symbol']})")
        
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
                if 'nifty 50' in name_lower or name_lower == 'nifty':
                    symbol = 'NIFTY'
                    fixed_symbols += 1
                elif 'nifty bank' in name_lower or 'bank nifty' in name_lower:
                    symbol = 'BANKNIFTY'
                    fixed_symbols += 1
                elif 'finnifty' in name_lower or 'fin nifty' in name_lower:
                    symbol = 'FINNIFTY'
                    fixed_symbols += 1
                elif 'midcap' in name_lower and 'nifty' in name_lower:
                    symbol = 'MIDCPNIFTY'
                    fixed_symbols += 1
                elif 'next 50' in name_lower and 'nifty' in name_lower:
                    symbol = 'NIFTY-NEXT50'
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
                    result.append({
                        "name": name,
                        "symbol": final_symbol,
                        "exchange": "NSE",
                    })

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
        
        logger.info(f"✅ F&O collection complete: {total_count} total ({indices_count} indices, {stocks_count} stocks) from {', '.join(methods_used)}, fixed {fixed_symbols} symbols")
        
        # Additional quality checks
        expected_total = 221  # 216 stocks + 5 indices
        if total_count != expected_total:
            logger.warning(f"⚠️ Count mismatch: Got {total_count}, expected {expected_total} (difference: {expected_total - total_count})")
        
        # Log sample of collected data for verification
        logger.info("📋 Sample of collected stocks:")
        for i, stock in enumerate(result[:5]):
            logger.info(f"   {i+1}. {stock.get('name', 'N/A')} -> {stock.get('symbol', 'N/A')}")
        
        if indices:
            logger.info("🏛️ Indices included:")
            for index in indices:
                logger.info(f"   - {index.get('name', 'N/A')} ({index.get('symbol', 'N/A')})")
        
        # Return combined list but log the breakdown
        return result

    def get_categorized_fno_data(self) -> Dict[str, any]:
        """Get F&O data separated into indices and stocks with metadata"""
        all_data = self.get_fno_stocks()
        
        indices = []
        stocks = []
        
        for item in all_data:
            if item["symbol"] in self.actual_indices:
                indices.append(item)
            else:
                stocks.append(item)
        
        return {
            "indices": indices,
            "stocks": stocks,
            "metadata": {
                "total_count": len(all_data),
                "indices_count": len(indices),
                "stocks_count": len(stocks),
                "last_updated": datetime.now().isoformat(),
                "data_quality": self._assess_data_quality(all_data)
            }
        }

    def _assess_data_quality(self, data: List[Dict[str, str]]) -> Dict[str, any]:
        """ENHANCED: Assess data quality with updated expected counts"""
        if not data:
            return {"score": 0, "issues": ["No data"]}
        
        issues = []
        score = 100  # Start with perfect score
        
        # Check for missing symbols
        missing_symbols = [item for item in data if not item.get("symbol")]
        if missing_symbols:
            issues.append(f"{len(missing_symbols)} items with missing symbols")
            score -= len(missing_symbols) * 2
        
        # Check for symbol format issues
        invalid_symbols = []
        for item in data:
            symbol = item.get("symbol", "")
            if symbol and not self._is_valid_symbol(symbol):
                invalid_symbols.append(symbol)
        
        if invalid_symbols:
            issues.append(f"{len(invalid_symbols)} invalid symbol formats")
            score -= len(invalid_symbols) * 3
        
        # Check for name format issues
        name_issues = 0
        for item in data:
            name = item.get("name", "")
            if not name or len(name.strip()) < 3:
                name_issues += 1
            elif re.search(r'^[0-9]', name) and not name.startswith('360'):  # Allow 360 One WAM
                name_issues += 1
        
        if name_issues:
            issues.append(f"{name_issues} name format issues")
            score -= name_issues * 2
        
        # UPDATED: Check expected count (should be around 221: 216 stocks + 5 indices)
        expected_min = 215  # Allow slight variance
        expected_max = 225
        actual_count = len(data)
        
        if actual_count < expected_min:
            issues.append(f"Count too low: {actual_count} (expected {expected_min}-{expected_max})")
            score -= 10
        elif actual_count > expected_max:
            issues.append(f"Count too high: {actual_count} (expected {expected_min}-{expected_max})")
            score -= 5
        
        # Check indices presence
        indices = ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'MIDCPNIFTY', 'NIFTY-NEXT50']
        present_indices = [item.get('symbol') for item in data if item.get('symbol') in indices]
        missing_indices = set(indices) - set(present_indices)
        
        if missing_indices:
            issues.append(f"Missing indices: {list(missing_indices)}")
            score -= len(missing_indices) * 5
        
        # Ensure score is not negative
        score = max(0, score)
        
        return {
            "score": score,
            "issues": issues if issues else ["No major issues detected"],
            "recommendations": self._get_quality_recommendations(issues),
            "breakdown": {
                "total_count": actual_count,
                "indices_found": len(present_indices),
                "stocks_found": actual_count - len(present_indices),
                "expected_total": 221
            }
        }

    def _get_quality_recommendations(self, issues: List[str]) -> List[str]:
        """Get recommendations based on data quality issues"""
        recommendations = []
        
        if any("missing symbols" in issue for issue in issues):
            recommendations.append("Run symbol mapping fix to resolve missing symbols")
        
        if any("invalid symbol" in issue for issue in issues):
            recommendations.append("Review and correct symbol formats")
        
        if any("name format" in issue for issue in issues):
            recommendations.append("Clean and standardize company names")
        
        if any("Count too" in issue for issue in issues):
            recommendations.append("Review data sources and filtering logic")
        
        if not recommendations:
            recommendations.append("Data quality is good")
        
        return recommendations

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

    def _get_extracted_dhan_data(self) -> list:
        """
        Load and process the extracted Dhan F&O data from JSON file
        This method provides the most reliable data source using pre-extracted data
        """
        try:
            if not self.extracted_data_path.exists():
                logger.debug(f"Extracted data file not found: {self.extracted_data_path}")
                return []
            
            logger.info(f"🔍 Loading extracted data from: {self.extracted_data_path}")
            
            with open(self.extracted_data_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            if not raw_data:
                logger.warning("Extracted data file is empty")
                return []
            
            logger.info(f"📊 Raw extracted data contains {len(raw_data)} records")
            
            # Process and clean the extracted data
            processed_stocks = []
            
            for item in raw_data:
                try:
                    # Extract raw name and symbol
                    raw_name = item.get("All Companies", "").strip()
                    raw_symbol = item.get("Symbol", "").strip()
                    
                    if not raw_name or not raw_symbol:
                        continue
                    
                    # Clean the name (fix duplicate first characters)
                    cleaned_name = self._clean_extracted_name(raw_name)
                    
                    # Clean the symbol (remove BS suffix and other processing)
                    cleaned_symbol = self._clean_extracted_symbol(raw_symbol)
                    
                    # Validate the cleaned data
                    if cleaned_name and cleaned_symbol and len(cleaned_name) >= 3:
                        processed_stocks.append({
                            "name": cleaned_name,
                            "symbol": cleaned_symbol,
                            "exchange": "NSE"
                        })
                        
                except Exception as e:
                    logger.debug(f"Error processing extracted item {item}: {e}")
                    continue
            
            logger.info(f"✅ Processed extracted data: {len(processed_stocks)} valid stocks from {len(raw_data)} raw records")
            
            # Log some samples for verification
            if processed_stocks:
                logger.info("📋 Sample processed stocks from extracted data:")
                for i, stock in enumerate(processed_stocks[:5]):
                    logger.info(f"   {i+1}. {stock['name']} -> {stock['symbol']}")
            
            return processed_stocks
            
        except Exception as e:
            logger.error(f"❌ Error loading extracted data: {e}")
            return []

    def _clean_extracted_name(self, raw_name: str) -> str:
        """
        Clean extracted company name - fixes common issues in extracted data
        """
        if not raw_name:
            return ""
        
        name = raw_name.strip()
        
        # Fix the specific issue with 3360 One WAM
        if name == "3360 One WAM":
            return "360 One WAM"
        
        # Fix duplicate first characters (NNifty -> Nifty, FFinnifty -> Finnifty, etc.)
        if len(name) >= 2 and name[0] == name[1]:
            # Check if it's a letter duplication at the start
            if name[0].isalpha():
                name = name[1:]  # Remove the first duplicate character
        
        # Additional name cleaning using existing method
        return self._clean_name(name)

    def _clean_extracted_symbol(self, raw_symbol: str) -> str:
        """
        Clean extracted symbol - removes suffixes and fixes format
        """
        if not raw_symbol:
            return ""
        
        symbol = raw_symbol.strip().upper()
        
        # Remove common suffixes from extracted data
        suffixes_to_remove = ["BS", "FUT", "OPT", "CE", "PE"]
        for suffix in suffixes_to_remove:
            if symbol.endswith(suffix):
                symbol = symbol[:-len(suffix)]
                break
        
        # Handle special cases and mappings
        symbol_mappings = {
            "BANKNIFTY": "BANKNIFTY",
            "FINNIFTY": "FINNIFTY", 
            "MIDCPNIFTY": "MIDCPNIFTY",
            "NIFTY": "NIFTY",
            "NIFTY NEXT 50": "NIFTY-NEXT50",
            "360ONE": "360ONE"
        }
        
        # Apply mappings
        if symbol in symbol_mappings:
            symbol = symbol_mappings[symbol]
        
        # Validate and return
        if self._is_valid_symbol(symbol):
            return symbol
        
        return ""

    def _get_main_futures_list(self) -> list:
        """NEW: Scrape the main futures stocks list page with enhanced extraction"""
        try:
            logger.info("🎯 Scraping main futures stocks list page...")
            url = f"{self.base_url}/futures-stocks-list/"
            
            # Use a more comprehensive request approach
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive", 
                "Upgrade-Insecure-Requests": "1",
                "Cache-Control": "max-age=0"
            }
            
            response = self.session.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            logger.info(f"📄 Main futures page response: {response.status_code}, content length: {len(response.text)}")
            
            # Parse with enhanced selectors
            soup = BeautifulSoup(response.text, "html.parser")
            stocks = []
            
            # Method 1: Look for data attributes (most reliable)
            data_elements = soup.find_all(attrs={"data-sym": True})
            for element in data_elements:
                try:
                    symbol = element.get("data-sym", "").strip()
                    # Look for company name in nearby elements
                    name = ""
                    
                    # Try to find name in parent or sibling elements
                    parent = element.parent
                    if parent:
                        name_element = parent.find(string=lambda text: text and len(text.strip()) > 3)
                        if name_element:
                            name = name_element.strip()
                    
                    if symbol and len(symbol) > 1:
                        stocks.append({"name": name or symbol, "symbol": symbol})
                        
                except Exception as e:
                    logger.debug(f"Error parsing data element: {e}")
                    continue
            
            # Method 2: Enhanced table parsing
            if not stocks:  # Only if Method 1 didn't work
                stocks.extend(self._parse_html_page(response.text))
            
            # Method 3: Look for specific CSS classes identified from the analysis
            if len(stocks) < 100:  # If we didn't get enough stocks
                try:
                    # Look for table-like structures
                    table_elements = soup.select(".css-p65e6u, [class*='table'], [class*='row']")
                    for table in table_elements:
                        table_stocks = self._extract_from_table_element(table)
                        stocks.extend(table_stocks)
                        
                except Exception as e:
                    logger.debug(f"Enhanced CSS parsing failed: {e}")
            
            # Remove duplicates
            unique_stocks = []
            seen_symbols = set()
            for stock in stocks:
                symbol = stock.get("symbol", "").strip().upper()
                if symbol and symbol not in seen_symbols and len(symbol) > 1:
                    seen_symbols.add(symbol)
                    unique_stocks.append(stock)
            
            logger.info(f"🎯 Main futures list extracted: {len(unique_stocks)} stocks")
            return unique_stocks
            
        except Exception as e:
            logger.warning(f"Main futures list scraping failed: {e}")
            return []

    def _extract_from_table_element(self, table_element) -> list:
        """Extract stocks from a table-like element"""
        stocks = []
        try:
            # Look for rows within the table
            rows = table_element.find_all(['tr', 'div'], class_=lambda x: x and ('row' in x.lower() or 'item' in x.lower()))
            
            for row in rows:
                try:
                    # Look for text that might be stock symbols (2-12 uppercase letters)
                    text_content = row.get_text()
                    
                    # Find potential symbols using regex
                    import re
                    symbol_matches = re.findall(r'\b([A-Z]{2,12})\b', text_content)
                    
                    for symbol in symbol_matches:
                        # Skip common words that aren't symbols
                        if symbol not in ['THE', 'AND', 'FOR', 'LTD', 'LIMITED', 'INC', 'CORP']:
                            # Try to find the corresponding company name
                            name_text = text_content.replace(symbol, '').strip()
                            name = self._clean_name(name_text) if name_text else symbol
                            
                            stocks.append({"name": name, "symbol": symbol})
                            break  # Only take the first valid symbol per row
                            
                except Exception as e:
                    continue
                    
        except Exception as e:
            logger.debug(f"Table element extraction failed: {e}")
            
        return stocks

    def _get_alternative_sources(self) -> list:
        """Try alternative URLs and methods to get complete FNO stock list"""
        all_alt_stocks = []
        
        # Alternative URLs to try
        alt_urls = [
            "/nse-equity-stocks/",
            "/stock-market/",
            "/equity-stocks-list/",
            "/nse-stocks-list/"
        ]
        
        for alt_url in alt_urls:
            try:
                url = f"{self.base_url}{alt_url}"
                logger.debug(f"Trying alternative URL: {url}")
                
                response = self.session.get(url, timeout=20)
                if response.status_code == 200:
                    # Look for FNO-specific content
                    if any(keyword in response.text.lower() for keyword in ['f&o', 'fno', 'futures', 'derivatives']):
                        alt_stocks = self._parse_html_page(response.text)
                        if alt_stocks:
                            all_alt_stocks.extend(alt_stocks)
                            logger.debug(f"Alternative source {alt_url}: {len(alt_stocks)} stocks")
                
                time.sleep(0.5)  # Be respectful
                
            except Exception as e:
                logger.debug(f"Alternative URL {alt_url} failed: {e}")
                continue
        
        # Deduplicate alternative sources
        unique_alt_stocks = []
        seen_symbols = set()
        for stock in all_alt_stocks:
            symbol = stock.get("symbol", "").strip().upper()
            if symbol and symbol not in seen_symbols:
                seen_symbols.add(symbol)
                unique_alt_stocks.append(stock)
        
        if unique_alt_stocks:
            logger.info(f"🔍 Alternative sources found: {len(unique_alt_stocks)} additional stocks")
        
        return unique_alt_stocks

    def _get_futures_pagination(self) -> list:
        """ENHANCED: Get futures stocks via pagination with more thorough scraping"""
        all_stocks = []
        page = 1
        max_pages = 20  # Increased from 10 to ensure we get all data

        while page <= max_pages:
            try:
                url = f"{self.base_url}/futures-stocks-list/?page={page}"
                response = self.session.get(url, timeout=30)

                if response.status_code != 200:
                    logger.debug(f"Futures page {page} returned status {response.status_code}")
                    break

                page_stocks = self._parse_html_page(response.text)
                if not page_stocks:
                    logger.debug(f"No stocks found on futures page {page}")
                    break

                all_stocks.extend(page_stocks)
                logger.debug(f"Futures page {page}: got {len(page_stocks)} stocks")
                page += 1
                time.sleep(0.5)

            except Exception as e:
                logger.debug(f"Futures page {page} failed: {e}")
                break

        logger.info(f"🔍 Futures pagination: collected {len(all_stocks)} stocks from {page-1} pages")
        return all_stocks

    def _get_fno_lot_size(self) -> list:
        """Get F&O stocks from lot size page - exact copy from working code"""
        try:
            url = f"{self.base_url}/nse-fno-lot-size/"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            return self._parse_html_page(response.text)

        except Exception as e:
            logger.debug(f"F&O lot size failed: {e}")
            return []

    def _get_options_pagination(self) -> list:
        """ENHANCED: Get options stocks via pagination with more thorough scraping"""
        all_stocks = []
        page = 1
        max_pages = 20  # Increased from 10 to ensure we get all data

        while page <= max_pages:
            try:
                url = f"{self.base_url}/options-stocks-list/?page={page}"
                response = self.session.get(url, timeout=30)

                if response.status_code != 200:
                    logger.debug(f"Options page {page} returned status {response.status_code}")
                    break

                page_stocks = self._parse_html_page(response.text)
                if not page_stocks:
                    logger.debug(f"No stocks found on options page {page}")
                    break

                all_stocks.extend(page_stocks)
                logger.debug(f"Options page {page}: got {len(page_stocks)} stocks")
                page += 1
                time.sleep(0.5)

            except Exception as e:
                logger.debug(f"Options page {page} failed: {e}")
                break

        logger.info(f"🔍 Options pagination: collected {len(all_stocks)} stocks from {page-1} pages")
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
        """Clean stock name - enhanced to handle special cases like 360 One WAM"""
        if not name_text:
            return ""

        cleaned = name_text.strip()

        # FIXED: Handle specific case of 360 One WAM being corrupted to 3360
        if cleaned == "3360 One WAM":
            return "360 One WAM"

        # Fix duplicate first characters (NNifty -> Nifty) but SKIP for numbers
        if (len(cleaned) > 1 and cleaned[0] == cleaned[1] and 
            cleaned[0].isupper() and not cleaned[0].isdigit()):
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
            r'\s+limited\s*$', r'\s+ltd\.?\s*$', r'\s+ltd\s*$',
            r'\s+company\s*$', r'\s+co\.?\s*$', r'\s+corp\.?\s*$',
            r'\s+corporation\s*$', r'\s+enterprises\s*$',
            r'\s+industries\s*$', r'\s+inc\.?\s*$', 
            r'\s+private\s*$', r'\s+pvt\.?\s*$',
            r'\s+group\s*$', r'\s+holding\s*$'
        ]
        
        for suffix in remove_suffixes:
            normalized = re.sub(suffix, '', normalized, flags=re.IGNORECASE)
        
        # Normalize common variations
        normalized = re.sub(r'\s+&\s+', ' and ', normalized)
        normalized = re.sub(r'\s+technologies\s*$', ' tech', normalized)
        normalized = re.sub(r'\s+financial\s+services\s*$', ' fin', normalized)
        normalized = re.sub(r'\s+pharmaceuticals?\s*$', ' pharma', normalized)
        
        # Clean whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized

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

        # Skip invalid entries (but be specific to avoid false positives)
        invalid_patterns = [
            r'^total\s', r'\btotal\s+results', r'\bshowing\s', r'\bresults\b', r'\bdownload\b'
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

            # Normalize company name for grouping
            normalized_name = self._normalize_company_name(name)
            
            if normalized_name not in company_groups:
                company_groups[normalized_name] = []
            
            company_groups[normalized_name].append({
                "original_name": name,
                "symbol": symbol,
                "stock": stock
            })

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
                if not re.search(r'^(SBI|LIC|HCL|JSW)$', symbol):
                    score += 5
                
                # Prefer symbols with company-specific patterns
                if re.search(r'(BANK|TECH|STEEL|LIFE|PORTS)', symbol):
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
            r'^gold$', r'^silver$', r'^crude oil$', r'natural gas futures', r'^commodity',
            r'currency', r'forex', r'bond', r'treasury', r'etf$', r'index fund'
        ]
        
        name_lower = name.lower()
        for pattern in skip_patterns:
            if re.search(pattern, name_lower):
                return False
        
        # Special handling for index names that might not have been scraped as symbols
        index_name_patterns = [
            r'nifty\s+50', r'nifty\s+bank', r'nifty.*bank', r'bank.*nifty',
            r'finnifty', r'fin\s*nifty', r'nifty.*midcap', r'midcap.*nifty',
            r'nifty.*next.*50'
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
            "LIMITED", "LTD", "LTD.", "COMPANY", "CO", "CO.", 
            "CORPORATION", "CORP", "CORP.", "ENTERPRISES", "GROUP",
            "INDUSTRIES", "INC", "INC.", "PVT", "PRIVATE", "&", "AND",
            "THE", "INDIA", "INDIAN"
        ]
        
        words = clean_name.split()
        filtered_words = []
        
        for word in words:
            # Remove punctuation
            word = re.sub(r'[^\w]', '', word)
            if word and word not in remove_words and len(word) > 1:
                filtered_words.append(word)
        
        if not filtered_words:
            # Fallback: use first few characters of original name
            return re.sub(r'[^\w]', '', name.upper())[:8]
        
        # Create symbol from first letters or abbreviation
        if len(filtered_words) == 1:
            return filtered_words[0][:8]  # Max 8 chars
        elif len(filtered_words) <= 3:
            return ''.join(filtered_words)[:8]
        else:
            # Use first letter of each word, max 8 chars
            return ''.join(word[0] for word in filtered_words[:8])

    def _is_valid_symbol(self, symbol: str) -> bool:
        """Validate if a symbol is proper for trading"""
        if not symbol:
            return False
        
        # Clean symbol
        symbol = symbol.strip().upper()
        
        # Check basic format - allow numbers at start for symbols like 360ONE
        if not re.match(r'^[A-Z0-9\-&]+$', symbol):
            return False
        
        # Length check
        if len(symbol) < 2 or len(symbol) > 12:
            return False
        
        # Avoid invalid patterns but allow 360ONE style symbols
        invalid_patterns = [
            r'^\d+$',  # All numbers only
            r'[_]{2,}',  # Multiple underscores
        ]
        
        for pattern in invalid_patterns:
            if re.search(pattern, symbol):
                return False
        
        # Special case: allow symbols that start with numbers if they contain letters (like 360ONE)
        if re.match(r'^\d+[A-Z]+', symbol):
            return True
        
        # Standard validation: must start with letter or be a known valid symbol
        if not re.match(r'^[A-Z]', symbol) and symbol not in ['360ONE']:
            return False
        
        return True

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


def get_categorized_fno_data() -> Dict[str, any]:
    """Get F&O data separated into indices and stocks with metadata"""
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
