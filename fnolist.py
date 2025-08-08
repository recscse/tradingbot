import asyncio
import os
import json
from playwright.async_api import async_playwright
import pandas as pd
from pathlib import Path

# Configuration
URL = "https://dhan.co/futures-stocks-list/"
DOWNLOAD_DIR = Path("data/fno_stock.json")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Set True for headless
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        try:
            await page.goto(URL, wait_until="networkidle")
            print("Page loaded.")

            # Wait for download
            async with page.expect_download() as download_info:
                await page.get_by_label("To download the complete data").click(
                    timeout=10000
                )

            download = await download_info.value
            file_path = os.path.join(DOWNLOAD_DIR, download.suggested_filename)
            await download.save_as(file_path)
            print(f"Downloaded: {file_path}")

        except Exception as e:
            print("Error during download:", e)
            await browser.close()
            return

        await browser.close()

        # Process CSV
        try:
            df = pd.read_csv(file_path)
            print("Available columns:", df.columns.tolist())

            # Flexible column mapping
            name_col = next(
                (
                    col
                    for col in df.columns
                    if col.lower() in ["name", "instrument name", "trading symbol"]
                ),
                None,
            )
            symbol_col = next(
                (
                    col
                    for col in df.columns
                    if col.lower() in ["symbol", "instrument id", "token"]
                ),
                None,
            )

            if not name_col or not symbol_col:
                raise ValueError(
                    f"Could not find Name or Symbol columns. Found: {df.columns.tolist()}"
                )

            # Select and rename
            result_df = df[[name_col, symbol_col]].copy()
            result_df.columns = ["Name", "Symbol"]
            result_df["Exchange"] = "NSE"

            # Convert to list of dicts (for JSON)
            result_json = result_df.to_dict(orient="records")

            # Save as JSON
            json_path = os.path.join(DOWNLOAD_DIR, "futures_stocks_nse.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(result_json, f, indent=2)

            print(f"✅ JSON saved to: {json_path}")
            print(f"Total entries: {len(result_json)}")
            print("\nSample JSON output:")
            print(json.dumps(result_json[:2], indent=2))

            # Optional: Also save as CSV
            csv_path = os.path.join(DOWNLOAD_DIR, "futures_stocks_nse.csv")
            result_df.to_csv(csv_path, index=False)
            print(f"📄 CSV also saved to: {csv_path}")

        except Exception as e:
            print("Error processing file:", e)


if __name__ == "__main__":
    asyncio.run(main())
