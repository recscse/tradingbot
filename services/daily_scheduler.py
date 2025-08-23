# services/daily_scheduler.py
"""
Daily Scheduler Service - Automatically runs stock selection at 9:00 AM
"""

import asyncio
import logging
from datetime import datetime, time
import pytz
from typing import Optional

from services.simple_stock_selector import simple_stock_selector
from services.market_timing_service import market_timing_service

logger = logging.getLogger(__name__)

class DailyScheduler:
    """Scheduler that runs stock selection automatically at 9:00 AM on trading days"""
    
    def __init__(self):
        self.ist = pytz.timezone("Asia/Kolkata")
        self.stock_selection_time = time(9, 0)  # 9:00 AM
        self.is_running = False
        self.scheduler_task: Optional[asyncio.Task] = None
    
    async def start_scheduler(self):
        """Start the daily scheduler"""
        if self.is_running:
            logger.warning("Daily scheduler is already running")
            return
        
        self.is_running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("📅 Daily scheduler started - will run stock selection at 9:00 AM on trading days")
    
    async def stop_scheduler(self):
        """Stop the daily scheduler"""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        logger.info("📅 Daily scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.is_running:
            try:
                # Check if it's time to run stock selection
                if market_timing_service.should_run_stock_selection():
                    await self._run_daily_stock_selection()
                
                # Sleep for 1 minute before checking again
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                logger.info("📅 Scheduler loop cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Error in scheduler loop: {e}")
                # Continue running even if there's an error
                await asyncio.sleep(60)
    
    async def _run_daily_stock_selection(self):
        """Run the daily stock selection"""
        try:
            logger.info("🎯 Running automatic daily stock selection...")
            
            success = simple_stock_selector.run_daily_selection()
            
            if success:
                logger.info("✅ Daily stock selection completed successfully")
            else:
                logger.error("❌ Daily stock selection failed")
                
        except Exception as e:
            logger.error(f"❌ Error running daily stock selection: {e}")
    
    async def trigger_manual_selection(self) -> bool:
        """Manually trigger stock selection (for testing)"""
        try:
            logger.info("🔧 Manual stock selection triggered")
            
            success = simple_stock_selector.run_daily_selection()
            
            if success:
                logger.info("✅ Manual stock selection completed")
            else:
                logger.error("❌ Manual stock selection failed")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error in manual stock selection: {e}")
            return False


# Create singleton instance
daily_scheduler = DailyScheduler()


# Optional: Auto-start scheduler when module is imported (for production)
async def auto_start_scheduler():
    """Auto-start the scheduler in production"""
    try:
        await daily_scheduler.start_scheduler()
    except Exception as e:
        logger.error(f"Failed to auto-start daily scheduler: {e}")

# Uncomment the following lines to auto-start in production:
# import asyncio
# if __name__ != "__main__":  # Only auto-start when imported, not when run directly
#     asyncio.create_task(auto_start_scheduler())