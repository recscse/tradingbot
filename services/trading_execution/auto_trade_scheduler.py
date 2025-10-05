"""
Auto-Trading Scheduler
Automatically starts/stops auto-trading based on market hours and stock selection

Features:
1. Auto-starts WebSocket at 9:15 AM when stocks are selected
2. Auto-stops WebSocket when all positions are closed
3. Monitors market hours
4. Handles daily cleanup
"""

import asyncio
import logging
from datetime import datetime, time as dt_time, date
from typing import Optional
from sqlalchemy.orm import Session

from database.connection import SessionLocal
from database.models import SelectedStock, ActivePosition, BrokerConfig
from services.trading_execution.auto_trade_live_feed import auto_trade_live_feed
from services.trading_execution.capital_manager import TradingMode

logger = logging.getLogger(__name__)


class AutoTradeScheduler:
    """
    Manages auto-trading lifecycle based on market hours and stock selection
    """

    def __init__(self):
        """Initialize auto-trade scheduler"""
        self.is_running = False
        self.check_interval = 60  # Check every 60 seconds
        self.market_start_time = dt_time(9, 15)  # 9:15 AM
        self.market_end_time = dt_time(15, 30)  # 3:30 PM
        self.auto_started_today = False
        self.current_user_id: Optional[int] = None
        self.current_trading_mode: TradingMode = TradingMode.PAPER

        logger.info("Auto-Trade Scheduler initialized")

    async def start_scheduler(self, user_id: int, trading_mode: TradingMode = TradingMode.PAPER):
        """
        Start the auto-trading scheduler

        Args:
            user_id: User identifier
            trading_mode: Paper or Live trading
        """
        try:
            self.is_running = True
            self.current_user_id = user_id
            self.current_trading_mode = trading_mode

            logger.info(f"🕐 Auto-trade scheduler started for user {user_id}")

            while self.is_running:
                try:
                    # Check current time
                    current_time = datetime.now().time()
                    current_date = date.today()

                    # Reset daily flag at midnight
                    if current_time.hour == 0 and current_time.minute == 0:
                        self.auto_started_today = False
                        logger.info("📅 New trading day - reset auto-start flag")

                    # Check if market is open
                    is_market_hours = self.market_start_time <= current_time <= self.market_end_time

                    if is_market_hours:
                        # Auto-start logic
                        await self._check_and_start_trading()

                        # Auto-stop logic
                        if auto_trade_live_feed.is_running:
                            await self._check_and_stop_trading()
                    else:
                        # After market hours - ensure stopped
                        if auto_trade_live_feed.is_running:
                            logger.info("📉 Market closed - stopping auto-trading")
                            await auto_trade_live_feed.stop()

                    await asyncio.sleep(self.check_interval)

                except Exception as e:
                    logger.error(f"Error in scheduler loop: {e}")
                    await asyncio.sleep(self.check_interval)

        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")
            self.is_running = False

    async def _check_and_start_trading(self):
        """
        Check if auto-trading should start based on stock selection
        """
        try:
            # Don't auto-start if already started today
            if self.auto_started_today:
                return

            # Don't auto-start if already running
            if auto_trade_live_feed.is_running:
                return

            db = SessionLocal()

            try:
                # Check if stocks are selected for today
                today = date.today()
                selected_stocks = db.query(SelectedStock).filter(
                    SelectedStock.selection_date == today,
                    SelectedStock.is_active == True,
                    SelectedStock.option_contract.isnot(None)
                ).count()

                if selected_stocks == 0:
                    logger.debug("No stocks selected yet - waiting...")
                    return

                # Check if we have active broker config
                broker_config = db.query(BrokerConfig).filter(
                    BrokerConfig.user_id == self.current_user_id,
                    BrokerConfig.is_active == True,
                    BrokerConfig.access_token.isnot(None)
                ).first()

                if not broker_config:
                    logger.warning("No active broker config - cannot auto-start")
                    return

                # Validate token expiry
                if broker_config.access_token_expiry and broker_config.access_token_expiry < datetime.now():
                    logger.warning("Broker token expired - cannot auto-start")
                    return

                # All conditions met - AUTO-START
                logger.info(f"🚀 AUTO-STARTING auto-trading: {selected_stocks} stocks selected")

                # Start auto-trading
                asyncio.create_task(
                    auto_trade_live_feed.start_auto_trading(
                        user_id=self.current_user_id,
                        access_token=broker_config.access_token,
                        trading_mode=self.current_trading_mode
                    )
                )

                self.auto_started_today = True

                logger.info(f"✅ Auto-trading started at {datetime.now().strftime('%H:%M:%S')}")

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error checking auto-start: {e}")

    async def _check_and_stop_trading(self):
        """
        Check if auto-trading should stop based on positions
        """
        try:
            db = SessionLocal()

            try:
                # Check if any positions are still open
                active_positions = db.query(ActivePosition).filter(
                    ActivePosition.user_id == self.current_user_id,
                    ActivePosition.is_active == True
                ).count()

                # Check if any stocks are still being monitored
                monitored_count = len(auto_trade_live_feed.monitored_instruments)

                # Check if any stocks are in monitoring state (waiting for signal)
                monitoring_state_count = 0
                for instrument in auto_trade_live_feed.monitored_instruments.values():
                    if instrument.state.value in ['monitoring', 'signal_found']:
                        monitoring_state_count += 1

                # Auto-stop conditions:
                # 1. No active positions AND
                # 2. No stocks in monitoring state (all either in position or closed)
                if active_positions == 0 and monitoring_state_count == 0 and monitored_count > 0:
                    logger.info(f"🛑 AUTO-STOPPING: All positions closed, no stocks monitoring")
                    await auto_trade_live_feed.stop()
                    logger.info(f"✅ Auto-trading stopped at {datetime.now().strftime('%H:%M:%S')}")

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error checking auto-stop: {e}")

    async def stop_scheduler(self):
        """Stop the scheduler"""
        self.is_running = False
        logger.info("Auto-trade scheduler stopped")


# Singleton instance
auto_trade_scheduler = AutoTradeScheduler()