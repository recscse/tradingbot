# import asyncio
# import schedule
# import time
# import logging
# from datetime import datetime, time as dt_time
# from threading import Thread


# logger = logging.getLogger(__name__)


# class TradingScheduler:
#     """
#     Scheduler to automatically run pre-market data preparation.
#     Ensures system is ready before market opens.
#     """

#     def __init__(self):
#         self.is_running = False
#         self.scheduler_thread = None

#     def start_scheduler(self):
#         """Start the trading scheduler."""
#         if self.is_running:
#             logger.warning("Scheduler already running")
#             return

#         logger.info("🕐 Starting trading scheduler...")

#         # Schedule pre-market data preparation at 8:00 AM
#         schedule.every().day.at("08:00").do(self._run_premarket_job)

#         # Schedule end-of-day cleanup at 4:00 PM
#         schedule.every().day.at("16:00").do(self._run_eod_cleanup)

#         self.is_running = True
#         self.scheduler_thread = Thread(target=self._scheduler_loop, daemon=True)
#         self.scheduler_thread.start()

#         logger.info("✅ Trading scheduler started")

#     def stop_scheduler(self):
#         """Stop the trading scheduler."""
#         self.is_running = False
#         schedule.clear()
#         logger.info("🛑 Trading scheduler stopped")

#     def _scheduler_loop(self):
#         """Main scheduler loop."""
#         while self.is_running:
#             try:
#                 schedule.run_pending()
#                 time.sleep(60)  # Check every minute
#             except Exception as e:
#                 logger.error(f"Scheduler error: {e}")
#                 time.sleep(60)

#     def _run_premarket_job(self):
#         """Run pre-market data preparation job."""
#         logger.info("🌅 Running scheduled pre-market data preparation...")

#         try:
#             # Run async function in sync context
#             asyncio.run(self._async_premarket_job())
#             logger.info("✅ Scheduled pre-market job completed")

#         except Exception as e:
#             logger.error(f"❌ Scheduled pre-market job failed: {e}")

#     async def _async_premarket_job(self):
#         """ENHANCED: Async pre-market job with your services"""
#         try:
#             user_id = 1  # Replace with actual user management logic

#             # INTEGRATION: Use your PreMarketDataService
#             async with PreMarketDataService() as service:
#                 result = await service.initialize_pre_market_data(user_id)

#                 logger.info(f"🎯 Pre-market analysis results:")
#                 logger.info(
#                     f"   - Instruments analyzed: {result.get('total_instruments_analyzed', 0)}"
#                 )
#                 logger.info(
#                     f"   - Stocks selected: {result.get('selected_for_trading', 0)}"
#                 )
#                 logger.info(
#                     f"   - Processing time: {result.get('processing_time_seconds', 0):.2f}s"
#                 )

#                 return result

#         except Exception as e:
#             logger.error(f"Enhanced pre-market job error: {e}")
#             raise

#     def _run_eod_cleanup(self):
#         """Run end-of-day cleanup."""
#         logger.info("🌇 Running end-of-day cleanup...")

#         try:
#             # Clear caches
#             import redis

#             redis_client = redis.Redis(host="localhost", port=6379, db=0)

#             # Clear trading-related caches
#             keys_to_clear = ["trading_stocks_cache", "instrument_mapping"]

#             for key in keys_to_clear:
#                 redis_client.delete(key)

#             # Clear all position caches
#             position_keys = redis_client.keys("position:*")
#             if position_keys:
#                 redis_client.delete(*position_keys)

#             logger.info("✅ End-of-day cleanup completed")

#         except Exception as e:
#             logger.error(f"❌ End-of-day cleanup failed: {e}")


# # Global scheduler instance
# trading_scheduler = TradingScheduler()


# # Auto-start scheduler when module is imported
# def start_trading_scheduler():
#     """Start the trading scheduler on application startup."""
#     trading_scheduler.start_scheduler()


# # Function to manually trigger pre-market job (for testing)
# async def manual_premarket_job(user_id: int):
#     """Manually trigger pre-market data preparation."""
#     logger.info(f"🔧 Manual pre-market job triggered for user {user_id}")

#     async with PreMarketDataService() as service:
#         result = await service.initialize_pre_market_data(user_id)

#     return result


# @classmethod
# def create_scheduler(cls):
#     """Create and start scheduler instance"""
#     try:
#         scheduler = cls()
#         scheduler.start_scheduler()
#         return scheduler
#     except Exception as e:
#         logger.error(f"Error creating scheduler: {e}")
#         return None
