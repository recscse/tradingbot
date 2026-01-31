import asyncio
import json
import os
from pathlib import Path
from playwright.async_api import async_playwright
import pandas as pd


async def download_dhan_data():
    """
    Download NSE F&O lot size data from Dhan website using Playwright
    """

    # Create downloads directory
    downloads_dir = Path("./downloads")
    downloads_dir.mkdir(exist_ok=True)

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(
            headless=False,  # Set to True if you don't want to see browser
            slow_mo=1000,  # Slow down actions for better visibility
        )

        # Create context with download path
        context = await browser.new_context(
            accept_downloads=True, viewport={"width": 1280, "height": 720}
        )

        page = await context.new_page()

        try:
            print("🌐 Navigating to Dhan website...")
            await page.goto(
                "https://dhan.co/nse-fno-lot-size/", wait_until="networkidle"
            )

            print("⏳ Waiting for page to load completely...")
            await page.wait_for_timeout(3000)

            # Wait for download button and click it
            print("🔍 Looking for download button...")

            # Try multiple selectors for the download button
            download_selectors = [
                'button[aria-label*="download"]',
                'button:has-text("Download")',
                '[data-testid*="download"]',
                ".download-btn",
                'button:has-text("Export")',
                'a[href*="download"]',
                'button[title*="download"]',
            ]

            download_button = None
            for selector in download_selectors:
                try:
                    download_button = await page.wait_for_selector(
                        selector, timeout=5000
                    )
                    if download_button:
                        print(f"✅ Found download button with selector: {selector}")
                        break
                except:
                    continue

            if not download_button:
                # If no button found, try to get data directly from the page
                print(
                    "⚠️ Download button not found, trying to extract data from page..."
                )
                return await extract_data_from_page(page)

            # Set up download promise before clicking
            print("📥 Starting download...")
            async with page.expect_download() as download_info:
                await download_button.click()

            download = await download_info.value

            # Save the downloaded file
            download_path = downloads_dir / download.suggested_filename
            await download.save_as(download_path)

            print(f"✅ File downloaded successfully: {download_path}")

            # Process the downloaded file
            processed_data = await process_downloaded_file(download_path)
            if processed_data:
                await save_to_app_data(processed_data)
            return processed_data

        except Exception as e:
            print(f"❌ Error during download: {e}")
            # Try alternative method - extract data directly from page
            extracted_data = await extract_data_from_page(page)
            if extracted_data:
                await save_to_app_data(extracted_data)
            return extracted_data

        finally:
            await browser.close()


async def save_to_app_data(data):
    """
    Transform and save data to data/fno_stock_list.json
    """
    try:
        print("🔄 Transforming data for application...")
        
        securities = []
        
        # Handle different data formats
        # Format 1: List of lists (from page extraction)
        # ["AAdani Enterprises", "ADANIENTBS", "300", ...]
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
            for row in data:
                if len(row) >= 2:
                    name = row[0].strip()
                    symbol = row[1].strip()
                    
                    # Clean symbol (remove 'BS' suffix)
                    if symbol.endswith("BS"):
                        symbol = symbol[:-2]
                    
                    # Clean name (remove first char if it duplicates second char, common scraping artifact)
                    if len(name) > 1 and name[0] == name[1]:
                        name = name[1:]
                        
                    securities.append({
                        "name": name,
                        "symbol": symbol,
                        "exchange": "NSE"
                    })

        # Format 2: List of dicts (from CSV/JSON download)
        elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            for row in data:
                # Try to find symbol and name columns
                symbol = None
                name = None
                
                # Check keys
                for key, value in row.items():
                    key_lower = key.lower()
                    if "symbol" in key_lower:
                        symbol = str(value).strip()
                    elif "underlying" in key_lower or "company" in key_lower or "name" in key_lower:
                        name = str(value).strip()
                
                if symbol:
                    if not name:
                        name = symbol
                        
                    # Clean symbol
                    if symbol.endswith("BS"):
                        symbol = symbol[:-2]
                        
                    securities.append({
                        "name": name,
                        "symbol": symbol,
                        "exchange": "NSE"
                    })

        if securities:
            # Sort by symbol
            securities.sort(key=lambda x: x["symbol"])
            
            output_data = {
                "securities": securities,
                "last_updated": pd.Timestamp.now().isoformat(),
                "total_count": len(securities),
                "data_source": "dhan_playwright_dynamic"
            }
            
            # Create data directory if not exists
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)
            
            target_file = data_dir / "fno_stock_list.json"
            
            # Backup existing file
            if target_file.exists():
                backup_file = data_dir / f"fno_stock_list_backup_{int(pd.Timestamp.now().timestamp())}.json"
                import shutil
                shutil.copy(target_file, backup_file)
                print(f"📦 Backed up existing file to: {backup_file}")
            
            # Save new file
            with open(target_file, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2)
                
            print(f"✅ Successfully updated {target_file}")
            print(f"📊 Total securities: {len(securities)}")
            
        else:
            print("⚠️ No valid securities found to save")

    except Exception as e:
        print(f"❌ Error saving to app data: {e}")



async def extract_data_from_page(page):
    """
    Extract data directly from the page if download doesn't work
    """
    try:
        print("🔍 Extracting data directly from page...")

        # Wait for table or data to load
        await page.wait_for_timeout(5000)

        # Try to find table data
        table_selectors = [
            "table",
            ".table",
            '[role="table"]',
            ".data-table",
            ".lot-size-table",
        ]

        for selector in table_selectors:
            try:
                tables = await page.query_selector_all(selector)
                if tables:
                    print(f"✅ Found table with selector: {selector}")
                    break
            except:
                continue

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
                        
                        if (index === 0 && row.querySelectorAll('th').length > 0) {
                            headers = rowData;
                        } else if (rowData.length > 0) {
                            if (headers.length > 0) {
                                const obj = {};
                                rowData.forEach((cell, i) => {
                                    obj[headers[i] || `column_${i}`] = cell;
                                });
                                tableData.push(obj);
                            } else {
                                tableData.push(rowData);
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
            # Save extracted data
            output_file = "dhan_nse_fno_extracted.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"✅ Data extracted and saved to: {output_file}")
            print(f"📊 Records extracted: {len(data)}")

            return data
        else:
            print("❌ No data found on the page")
            return None

    except Exception as e:
        print(f"❌ Error extracting data from page: {e}")
        return None


async def process_downloaded_file(file_path):
    """
    Process the downloaded file and extract data
    """
    try:
        file_extension = file_path.suffix.lower()

        if file_extension == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(
                f"✅ JSON file processed: {len(data) if isinstance(data, list) else 'N/A'} records"
            )
            return data

        elif file_extension in [".csv", ".xlsx", ".xls"]:
            if file_extension == ".csv":
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)

            # Convert to list of dictionaries
            data = df.to_dict("records")

            # Save as JSON for consistency
            json_file = file_path.with_suffix(".json")
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(
                f"✅ {file_extension.upper()} file converted to JSON: {len(data)} records"
            )
            return data

        else:
            print(f"⚠️ Unsupported file format: {file_extension}")
            return None

    except Exception as e:
        print(f"❌ Error processing downloaded file: {e}")
        return None


def display_data_summary(data):
    """
    Display a summary of the downloaded data
    """
    if not data:
        print("❌ No data to display")
        return

    print("\n" + "=" * 50)
    print("📊 DATA SUMMARY")
    print("=" * 50)

    if isinstance(data, list) and len(data) > 0:
        print(f"📈 Total records: {len(data)}")

        # Show first record structure
        if isinstance(data[0], dict):
            print(f"📝 Columns: {list(data[0].keys())}")

            # Show first few records
            print(f"\n🔍 Sample records:")
            for i, record in enumerate(data[:3]):
                print(f"  Record {i+1}: {record}")
        else:
            print(f"🔍 Sample data: {data[:3]}")

    print("=" * 50)


async def main():
    """
    Main function to run the scraper
    """
    print("🚀 Starting Dhan NSE F&O data extraction...")

    data = await download_dhan_data()

    if data:
        display_data_summary(data)

        # Optionally save to CSV for easy viewing
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            try:
                df = pd.DataFrame(data)
                csv_file = "dhan_nse_fno_data.csv"
                df.to_csv(csv_file, index=False)
                print(f"\n💾 Data also saved as CSV: {csv_file}")
            except Exception as e:
                print(f"⚠️ Could not save as CSV: {e}")

    else:
        print("❌ Failed to extract any data")


if __name__ == "__main__":
    # Install required packages
    print("📦 Make sure you have installed:")
    print("   pip install playwright pandas")
    print("   playwright install chromium")
    print()

    # Run the scraper
    asyncio.run(main())
