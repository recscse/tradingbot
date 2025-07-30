# services/dhan_fno_scheduler.py
"""
Dhan F&O Daily Scheduler Service
===============================

Simple service that scrapes F&O data daily and saves to data/dhan_fno_stock.json
Runs as a background scheduler in your trading application.
"""

import asyncio
import logging
import os
import json
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Dict, Any
import traceback

# Import the Dhan scraper (place the scraper file in your services directory)
from .dhan_scraper_json_complete import CompleteDhanScraper


class DhanFNOSchedulerService:
    """
    Daily scheduler service for F&O data scraping and JSON file generation
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.scraper = CompleteDhanScraper()

        # File paths
        self.data_dir = Path("data")
        self.json_file_path = self.data_dir / "dhan_fno_stock.json"

        # Scheduling
        self.scheduled_time = time(9, 0)  # 9:00 AM daily
        self.is_running = False
        self.last_run = None
        self.last_status = None

        # Ensure data directory exists
        self.data_dir.mkdir(exist_ok=True)

        self.logger.info("✅ Dhan F&O Scheduler Service initialized")

    async def scrape_and_save_json(self) -> Dict[str, Any]:
        """Scrape F&O data and save to JSON file"""
        try:
            self.logger.info("🔄 Starting daily F&O data scraping...")
            start_time = datetime.now()

            # Run scraper in thread pool (since it's synchronous)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.scraper.scrape_and_convert,
                False,  # Don't save CSV
                False,  # Don't save JSON (we'll save our own)
            )

            if result and result.get("json_data"):
                json_data = result["json_data"]
                securities_count = len(json_data.get("securities", []))

                # Add metadata to the JSON
                enhanced_data = {
                    "metadata": {
                        "scraped_at": datetime.now().isoformat(),
                        "total_securities": securities_count,
                        "data_source": "dhan_website",
                        "scraper_version": "3.0.0",
                        "file_generated_by": "dhan_fno_scheduler_service",
                    },
                    "securities": json_data["securities"],
                }

                # Save to JSON file
                with open(self.json_file_path, "w", encoding="utf-8") as f:
                    json.dump(enhanced_data, f, indent=2, ensure_ascii=False)

                processing_time = (datetime.now() - start_time).total_seconds()

                self.last_run = datetime.now()
                self.last_status = {
                    "status": "success",
                    "securities_count": securities_count,
                    "processing_time_seconds": round(processing_time, 2),
                    "file_path": str(self.json_file_path),
                    "file_size_kb": round(
                        os.path.getsize(self.json_file_path) / 1024, 2
                    ),
                }

                self.logger.info(
                    f"✅ Successfully scraped {securities_count} F&O securities"
                )
                self.logger.info(f"💾 Data saved to: {self.json_file_path}")
                self.logger.info(f"⏱️ Processing time: {processing_time:.2f} seconds")

                return self.last_status

            else:
                raise Exception("No data returned from scraper")

        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"❌ F&O data scraping failed: {error_msg}")

            self.last_run = datetime.now()
            self.last_status = {
                "status": "error",
                "error": error_msg,
                "securities_count": 0,
                "processing_time_seconds": 0,
            }

            return self.last_status

    def load_existing_data(self) -> Dict[str, Any]:
        """Load existing F&O data from JSON file"""
        try:
            if self.json_file_path.exists():
                with open(self.json_file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                self.logger.info(
                    f"📖 Loaded existing F&O data: {len(data.get('securities', []))} securities"
                )
                return data
            else:
                self.logger.info("📁 No existing F&O data file found")
                return {"securities": [], "metadata": {}}

        except Exception as e:
            self.logger.error(f"❌ Error loading existing data: {e}")
            return {"securities": [], "metadata": {}}

    def get_securities_count(self) -> int:
        """Get count of securities in current JSON file"""
        try:
            data = self.load_existing_data()
            return len(data.get("securities", []))
        except:
            return 0

    def get_last_update_time(self) -> str:
        """Get last update time from JSON file"""
        try:
            data = self.load_existing_data()
            metadata = data.get("metadata", {})
            return metadata.get("scraped_at", "Never")
        except:
            return "Never"

    async def run_scheduler(self):
        """Main scheduler loop - runs daily at scheduled time"""
        self.is_running = True
        self.logger.info(
            f"⏰ Dhan F&O Scheduler started - will run daily at {self.scheduled_time}"
        )

        # Run immediately on first start if no data exists
        if not self.json_file_path.exists():
            self.logger.info("🚀 No existing data found - running initial scrape...")
            await self.scrape_and_save_json()

        while self.is_running:
            try:
                # Calculate time until next scheduled run
                now = datetime.now()
                today_scheduled = now.replace(
                    hour=self.scheduled_time.hour,
                    minute=self.scheduled_time.minute,
                    second=0,
                    microsecond=0,
                )

                # If today's scheduled time has passed, schedule for tomorrow
                if now >= today_scheduled:
                    next_run = today_scheduled + timedelta(days=1)
                else:
                    next_run = today_scheduled

                sleep_seconds = (next_run - now).total_seconds()

                self.logger.info(f"⏰ Next F&O data scrape scheduled for: {next_run}")
                self.logger.info(f"⏳ Sleeping for {sleep_seconds/3600:.1f} hours...")

                # Sleep until next run
                await asyncio.sleep(sleep_seconds)

                # Run the scraping if still running
                if self.is_running:
                    await self.scrape_and_save_json()

            except Exception as e:
                self.logger.error(f"❌ Scheduler error: {e}")
                self.logger.error(f"📝 Traceback: {traceback.format_exc()}")

                # Wait 1 hour before retrying on error
                await asyncio.sleep(3600)

    def stop_scheduler(self):
        """Stop the scheduler"""
        self.is_running = False
        self.logger.info("🛑 Dhan F&O Scheduler stopped")

    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get current scheduler status"""
        return {
            "scheduler_running": self.is_running,
            "scheduled_time": self.scheduled_time.strftime("%H:%M"),
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_status": self.last_status,
            "data_file": {
                "path": str(self.json_file_path),
                "exists": self.json_file_path.exists(),
                "securities_count": self.get_securities_count(),
                "last_updated": self.get_last_update_time(),
                "size_kb": (
                    round(os.path.getsize(self.json_file_path) / 1024, 2)
                    if self.json_file_path.exists()
                    else 0
                ),
            },
            "next_run": self._calculate_next_run(),
            "timestamp": datetime.now().isoformat(),
        }

    def _calculate_next_run(self) -> str:
        """Calculate next scheduled run time"""
        try:
            now = datetime.now()
            today_scheduled = now.replace(
                hour=self.scheduled_time.hour,
                minute=self.scheduled_time.minute,
                second=0,
                microsecond=0,
            )

            if now >= today_scheduled:
                next_run = today_scheduled + timedelta(days=1)
            else:
                next_run = today_scheduled

            return next_run.isoformat()
        except:
            return "Unknown"

    async def force_run(self) -> Dict[str, Any]:
        """Force run the scraper immediately (for manual triggers)"""
        self.logger.info("🔄 Force running F&O data scraper...")
        return await self.scrape_and_save_json()


# Global service instance
_dhan_fno_scheduler = None


def get_dhan_fno_scheduler() -> DhanFNOSchedulerService:
    """Get or create the global scheduler instance"""
    global _dhan_fno_scheduler

    if _dhan_fno_scheduler is None:
        _dhan_fno_scheduler = DhanFNOSchedulerService()

    return _dhan_fno_scheduler


async def start_dhan_fno_scheduler():
    """Start the Dhan F&O scheduler service"""
    try:
        logger = logging.getLogger(__name__)
        logger.info("🚀 Starting Dhan F&O Scheduler Service...")

        scheduler = get_dhan_fno_scheduler()

        # Start the scheduler in background
        scheduler_task = asyncio.create_task(scheduler.run_scheduler())

        logger.info("✅ Dhan F&O Scheduler Service started successfully")
        return scheduler_task

    except Exception as e:
        logger.error(f"❌ Failed to start Dhan F&O Scheduler: {e}")
        return None


def stop_dhan_fno_scheduler():
    """Stop the Dhan F&O scheduler service"""
    global _dhan_fno_scheduler

    if _dhan_fno_scheduler:
        _dhan_fno_scheduler.stop_scheduler()


# Utility functions for accessing the data
def get_fno_securities_from_file() -> Dict[str, Any]:
    """Utility function to load F&O securities from the JSON file"""
    try:
        scheduler = get_dhan_fno_scheduler()
        return scheduler.load_existing_data()
    except Exception as e:
        logging.getLogger(__name__).error(f"Error loading F&O securities: {e}")
        return {"securities": [], "metadata": {}}


def get_fno_symbols_list() -> list:
    """Utility function to get list of F&O symbols"""
    try:
        data = get_fno_securities_from_file()
        return [
            sec.get("symbol", "")
            for sec in data.get("securities", [])
            if sec.get("symbol")
        ]
    except Exception as e:
        logging.getLogger(__name__).error(f"Error getting F&O symbols: {e}")
        return []


def search_fno_securities(query: str) -> list:
    """Utility function to search F&O securities"""
    try:
        data = get_fno_securities_from_file()
        securities = data.get("securities", [])

        query_lower = query.lower()
        results = []

        for security in securities:
            name = security.get("name", "").lower()
            symbol = security.get("symbol", "").lower()

            if query_lower in name or query_lower in symbol:
                results.append(security)

        return results
    except Exception as e:
        logging.getLogger(__name__).error(f"Error searching F&O securities: {e}")
        return []
