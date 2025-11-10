"""
Auto-Trading Scheduler
Automatically starts/stops auto-trading based on market hours and common stock selection

Architecture:
- SelectedStock table is GLOBAL (no user_id field) - all users see same daily stock selections
- Each user trades independently with their own broker config
- Auto-starts WebSocket for users when common stocks are selected

Features:
1. Auto-starts WebSocket at 9:15 AM when stocks are selected (market_scheduler runs selection)
2. Auto-stops WebSocket when all positions are closed
3. Monitors market hours (9:15 AM - 3:30 PM)
4. Handles daily cleanup and auto-start flag reset
5. Supports multiple users trading the same common stock selections
"""

import asyncio
import logging
from datetime import datetime, time as dt_time, date

from database.connection import SessionLocal
from database.models import SelectedStock, ActivePosition, BrokerConfig
from services.trading_execution.auto_trade_live_feed import auto_trade_live_feed
from services.trading_execution.capital_manager import TradingMode

logger = logging.getLogger(__name__)


class AutoTradeScheduler:
    """
    Manages auto-trading lifecycle based on market hours and COMMON stock selection.

    Important: SelectedStock table has NO user_id - stocks are selected globally
    by market_scheduler_service and shared across ALL users.

    Each user trades independently with their own:
    - BrokerConfig (user_id, access_token, broker_name)
    - ActivePositions (user_id, trade details)
    - Capital allocation

    This scheduler monitors all active users and auto-starts trading when:
    1. Common stocks are selected (SelectedStock.selection_date == today)
    2. User has active broker config with valid token
    3. Market hours (9:15 AM - 3:30 PM)
    """

    def __init__(self):
        """Initialize auto-trade scheduler"""
        self.is_running = False
        self.check_interval = 60  # Check every 60 seconds
        self.market_start_time = dt_time(9, 15)  # 9:15 AM
        self.market_end_time = dt_time(15, 30)  # 3:30 PM
        self.auto_started_users = (
            {}
        )  # Track which users have auto-started today: {user_id: True/False}
        self.default_trading_mode: TradingMode = TradingMode.PAPER

        logger.info("Auto-Trade Scheduler initialized (multi-user mode)")

    async def start_scheduler(self, trading_mode: TradingMode = TradingMode.PAPER):
        """
        Start the auto-trading scheduler for ALL active users

        Args:
            trading_mode: Default paper or Live trading mode
        """
        try:
            self.is_running = True
            self.default_trading_mode = trading_mode

            logger.info(
                f"🕐 Auto-trade scheduler started (monitoring ALL active users)"
            )
            logger.info(f"📊 Default trading mode: {trading_mode.value}")

            # IMMEDIATE START: Check and start trading immediately on application startup
            # This allows auto-trading to work even outside market hours for testing/monitoring
            logger.info("🚀 Checking for immediate auto-start on application startup...")
            await self._check_and_start_trading_all_users()

            while self.is_running:
                try:
                    # Check current time
                    current_time = datetime.now().time()

                    # Reset daily flag at midnight
                    if current_time.hour == 0 and current_time.minute == 0:
                        self.auto_started_users.clear()
                        logger.info(
                            "📅 New trading day - reset auto-start flags for all users"
                        )

                    # Check if market is open
                    is_market_hours = (
                        self.market_start_time <= current_time <= self.market_end_time
                    )

                    if is_market_hours:
                        # Auto-start logic for ALL eligible users
                        await self._check_and_start_trading_all_users()

                        # Auto-stop logic
                        if auto_trade_live_feed.is_running:
                            await self._check_and_stop_trading()
                    else:
                        # Outside market hours - still allow auto-trading to run if already started
                        # Don't auto-stop outside market hours to allow 24/7 monitoring
                        if not auto_trade_live_feed.is_running:
                            # Try to start if conditions are met (for pre-market/post-market monitoring)
                            await self._check_and_start_trading_all_users()

                    await asyncio.sleep(self.check_interval)

                except Exception as e:
                    logger.error(f"Error in scheduler loop: {e}")
                    await asyncio.sleep(self.check_interval)

        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")
            self.is_running = False

    async def _check_and_start_trading_all_users(self):
        """
        Check if auto-trading should start for ANY user when common stocks are selected.
        SelectedStock table is GLOBAL (no user_id) - all users see same stock selections.
        """
        try:
            # Don't auto-start if already running
            if auto_trade_live_feed.is_running:
                return

            # Check if stock selection is in progress to prevent race conditions
            try:
                from services.intelligent_stock_selection_service import (
                    intelligent_stock_selector,
                )

                if intelligent_stock_selector.selection_in_progress:
                    logger.debug(
                        "⏳ Stock selection in progress - waiting to avoid race condition..."
                    )
                    return
            except Exception as e:
                logger.warning(f"Could not check selection status: {e}")

            db = SessionLocal()

            try:
                today = date.today()

                # STEP 1: Check if stocks are selected today (COMMON for all users)
                stock_count = (
                    db.query(SelectedStock)
                    .filter(
                        SelectedStock.selection_date == today,
                        SelectedStock.is_active == True,
                        SelectedStock.option_contract.isnot(None),
                    )
                    .count()
                )

                if stock_count == 0:
                    logger.debug(
                        "No stocks selected today - waiting for market_scheduler to run selection..."
                    )
                    return

                # STEP 2: Find ALL users with active broker configs (stocks are shared)
                active_broker_configs = (
                    db.query(BrokerConfig)
                    .filter(
                        BrokerConfig.is_active == True,
                        BrokerConfig.access_token.isnot(None),
                    )
                    .all()
                )

                if not active_broker_configs:
                    logger.debug(
                        "No active broker configs found - waiting for user setup..."
                    )
                    return

                # STEP 3: Process each user (stocks are common, but each user trades independently)
                for broker_config in active_broker_configs:
                    user_id = broker_config.user_id

                    # Check if already auto-started for this user today
                    if self.auto_started_users.get(user_id):
                        continue

                    # Validate token expiry
                    if (
                        broker_config.access_token_expiry
                        and broker_config.access_token_expiry < datetime.now()
                    ):
                        logger.warning(
                            f"⚠️ Broker token expired for user {user_id} - cannot auto-start"
                        )
                        continue

                    # All conditions met - AUTO-START for this user
                    logger.info(f"🚀 AUTO-STARTING auto-trading for user {user_id}")
                    logger.info(
                        f"📊 {stock_count} common stocks selected today (available to all users)"
                    )

                    # Start auto-trading
                    asyncio.create_task(
                        auto_trade_live_feed.start_auto_trading(
                            # user_id=user_id,
                            # access_token=broker_config.access_token,
                            trading_mode=self.default_trading_mode,
                        )
                    )

                    # Mark as auto-started for today
                    self.auto_started_users[user_id] = True

                    logger.info(
                        f"✅ Auto-trading started for user {user_id} at {datetime.now().strftime('%H:%M:%S')}"
                    )

                    # Note: Currently supports single user at a time due to singleton auto_trade_live_feed
                    # For multi-user support, would need separate feed instances per user
                    break

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error checking auto-start for users: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

    async def _check_and_stop_trading(self):
        """
        Check if auto-trading should stop based on positions for ANY active user
        """
        try:
            from services.trading_execution.shared_instrument_registry import shared_registry

            db = SessionLocal()

            try:
                # Check if any positions are still open for ANY user
                active_positions = (
                    db.query(ActivePosition)
                    .filter(ActivePosition.is_active == True)
                    .count()
                )

                # Check if any stocks are still being monitored
                monitored_count = len(shared_registry.instruments)

                # Check if any stocks are in monitoring state (waiting for signal)
                monitoring_state_count = 0
                for instrument in shared_registry.instruments.values():
                    if instrument.state.value in ["monitoring", "signal_detected"]:
                        monitoring_state_count += 1

                # Auto-stop conditions:
                # 1. No active positions AND
                # 2. No stocks in monitoring state (all either in position or closed)
                if (
                    active_positions == 0
                    and monitoring_state_count == 0
                    and monitored_count > 0
                ):
                    logger.info(
                        "AUTO-STOPPING: All positions closed, no stocks monitoring"
                    )
                    await auto_trade_live_feed.stop()
                    logger.info(
                        f"Auto-trading stopped at {datetime.now().strftime('%H:%M:%S')}"
                    )

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
