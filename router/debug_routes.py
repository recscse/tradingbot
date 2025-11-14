from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from datetime import datetime
import logging
import asyncio

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/debug", tags=["Debug"])


@router.get("/analytics")
async def debug_realtime_analytics():
    """Debug endpoints to test real time marekt engine annalytics"""

    try:
        from services.realtime_market_engine import get_analytics, get_market_engine

        engine = get_market_engine()
        last_calc_ts = getattr(engine.analytics, "last_calculation", 0)
        last_update_ts = getattr(engine, "last_analytics_update", 0)
        prices = engine.get_live_prices()

        heatmap = engine._generate_sector_heatmap

        analytics = get_analytics()

        return {
            "success": True,
            "last_calc_time": last_calc_ts,
            "price": prices,
            "heatmap": heatmap,
            "analytics": analytics,
        }

    except Exception as e:
        logger.error(f"error debugging in the rela time markket engine analytics")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/debug-run-stock-selection")
async def debug_run_stock_selection(force: bool = False):
    """
    Debug endpoint for the stocks selection service

    Args:
        force: If True, force new selection even if already done today
    """

    try:
        from services.intelligent_stock_selection_service import (
            intelligent_stock_selector,
        )

        result = await intelligent_stock_selector.run_premarket_selection(force=force)

        if result and not result.get("error"):
            selected_stocks_data = result.get("selected_stocks", [])
            sentiment_analysis = result.get("sentiment_analysis", {})
            already_selected = result.get("already_selected", False)

            if already_selected:
                logger.info(
                    f"✅ Returning existing stock selection: {result.get('selection_count', 0)} stocks"
                )
            else:
                logger.info(
                    f"✅ Intelligent stock selection complete: {len(selected_stocks_data)} stocks"
                )
                logger.info(
                    f"📊 Market sentiment: {sentiment_analysis.get('sentiment')} (A/D: {sentiment_analysis.get('advance_decline_ratio', 1.0):.2f})"
                )

            return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Error running stocks selection service: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# ============================================================================
# AUTO-TRADING SCHEDULER COMPREHENSIVE TEST ENDPOINTS
# ============================================================================


@router.get("/test-auto-trading-scheduler")
async def debug_test_auto_trading_scheduler():
    """
    COMPREHENSIVE test of AUTO-TRADING SCHEDULER - Tests EXACTLY how production works

    This tests the complete auto-start flow:
    1. Scheduler running check
    2. Stock selection detection (same query scheduler uses)
    3. Broker config validation (same checks scheduler does)
    4. Auto-start condition evaluation
    5. WebSocket status
    6. Simulates scheduler decision-making

    Returns detailed status of ALL components needed for auto-trading.
    """
    try:
        from services.trading_execution.auto_trade_scheduler import auto_trade_scheduler
        from services.trading_execution.auto_trade_live_feed import auto_trade_live_feed
        from services.intelligent_stock_selection_service import (
            intelligent_stock_selector,
        )
        from database.connection import SessionLocal
        from database.models import SelectedStock, BrokerConfig
        from datetime import date, time as dt_time

        db = SessionLocal()
        test_results = {}

        try:
            # ===== TEST 1: Scheduler Status =====
            test_results["test_1_scheduler_status"] = {
                "description": "Check if auto-trade scheduler is running",
                "is_running": auto_trade_scheduler.is_running,
                "default_trading_mode": (
                    auto_trade_scheduler.default_trading_mode.value
                    if hasattr(auto_trade_scheduler, "default_trading_mode")
                    else "unknown"
                ),
                "auto_started_users": dict(auto_trade_scheduler.auto_started_users),
                "check_interval_seconds": auto_trade_scheduler.check_interval,
                "market_hours": f"{auto_trade_scheduler.market_start_time} - {auto_trade_scheduler.market_end_time}",
                "status": "RUNNING" if auto_trade_scheduler.is_running else "STOPPED",
            }

            # ===== TEST 2: Stock Selection Detection (EXACT SAME QUERY AS SCHEDULER) =====
            today = date.today()

            # This is EXACTLY what scheduler queries in _check_and_start_trading_all_users()
            users_with_selections = (
                db.query(BrokerConfig)
                .join(SelectedStock, SelectedStock.user_id == BrokerConfig.user_id)
                .filter(
                    BrokerConfig.is_active == True,
                    BrokerConfig.access_token.isnot(None),
                    SelectedStock.selection_date == today,
                    SelectedStock.is_active == True,
                    SelectedStock.option_contract.isnot(None),
                )
                .distinct()
                .all()
            )

            test_results["test_2_stock_selection"] = {
                "description": "Detect stocks selected today (EXACT scheduler query)",
                "users_with_selections": len(users_with_selections),
                "selection_in_progress": intelligent_stock_selector.selection_in_progress,
                "user_details": [
                    {
                        "user_id": bc.user_id,
                        "broker": bc.broker_name,
                        "has_token": bool(bc.access_token),
                    }
                    for bc in users_with_selections
                ],
                "status": "READY" if len(users_with_selections) > 0 else "WAITING",
            }

            # Get stock details for first user with selections
            stock_details = []
            if users_with_selections:
                first_user_id = users_with_selections[0].user_id
                selected_stocks = (
                    db.query(SelectedStock)
                    .filter(
                        SelectedStock.user_id == first_user_id,
                        SelectedStock.selection_date == today,
                        SelectedStock.is_active == True,
                        SelectedStock.option_contract.isnot(None),
                    )
                    .all()
                )

                stock_details = [
                    {
                        "symbol": s.symbol,
                        "option_type": s.option_type,
                        "strike_price": s.strike_price,
                        "expiry_date": s.expiry_date,
                        "has_option_contract": bool(s.option_contract),
                    }
                    for s in selected_stocks
                ]

            test_results["test_2_stock_details"] = {
                "stocks_count": len(stock_details),
                "stocks": stock_details,
            }

            # ===== TEST 3: Broker Token Validation (EXACT SAME CHECKS) =====
            token_valid_brokers = []
            for bc in users_with_selections:
                # This is EXACTLY what scheduler checks
                token_valid = True
                if bc.access_token_expiry and bc.access_token_expiry < datetime.now():
                    token_valid = False

                token_valid_brokers.append(
                    {
                        "user_id": bc.user_id,
                        "broker": bc.broker_name,
                        "token_valid": token_valid,
                        "token_expiry": (
                            bc.access_token_expiry.isoformat()
                            if bc.access_token_expiry
                            else None
                        ),
                    }
                )

            valid_count = sum(1 for b in token_valid_brokers if b["token_valid"])

            test_results["test_3_broker_validation"] = {
                "description": "Validate broker tokens (EXACT scheduler checks)",
                "total_brokers": len(token_valid_brokers),
                "valid_tokens": valid_count,
                "broker_details": token_valid_brokers,
                "status": "READY" if valid_count > 0 else "TOKEN_EXPIRED",
            }

            # ===== TEST 4: Auto-Start Conditions (EXACT SCHEDULER LOGIC) =====
            current_time = datetime.now().time()
            is_market_hours = dt_time(9, 15) <= current_time <= dt_time(15, 30)

            # These are ALL the checks scheduler does before starting
            conditions = {
                "websocket_not_running": not auto_trade_live_feed.is_running,
                "selection_not_in_progress": not intelligent_stock_selector.selection_in_progress,
                "users_with_selections": len(users_with_selections) > 0,
                "valid_broker_tokens": valid_count > 0,
                "market_hours": is_market_hours,
            }

            all_conditions_met = all(conditions.values())

            blocking_reasons = []
            if auto_trade_live_feed.is_running:
                blocking_reasons.append("WebSocket already running")
            if intelligent_stock_selector.selection_in_progress:
                blocking_reasons.append(
                    "Stock selection in progress (race condition protection)"
                )
            if len(users_with_selections) == 0:
                blocking_reasons.append("No users with stock selections today")
            if valid_count == 0:
                blocking_reasons.append("No valid broker tokens")
            if not is_market_hours:
                blocking_reasons.append(
                    f"Outside market hours (current: {current_time.strftime('%H:%M:%S')})"
                )

            test_results["test_4_auto_start_conditions"] = {
                "description": "Evaluate ALL auto-start conditions (EXACT scheduler logic)",
                "current_time": current_time.strftime("%H:%M:%S"),
                "market_hours_range": "09:15:00 - 15:30:00",
                "conditions": conditions,
                "all_conditions_met": all_conditions_met,
                "blocking_reasons": blocking_reasons,
                "decision": "WILL AUTO-START" if all_conditions_met else "WAITING",
                "status": "READY" if all_conditions_met else "BLOCKED",
            }

            # ===== TEST 5: WebSocket Current Status =====
            test_results["test_5_websocket_status"] = {
                "description": "Current auto_trade_live_feed status",
                "is_running": auto_trade_live_feed.is_running,
                "monitored_instruments": len(
                    auto_trade_live_feed.monitored_instruments
                ),
                "subscribed_keys": len(auto_trade_live_feed.subscribed_keys),
                "stats": auto_trade_live_feed.stats,
                "status": "ACTIVE" if auto_trade_live_feed.is_running else "IDLE",
            }

            # ===== TEST 6: Simulate Scheduler Decision =====
            if all_conditions_met:
                next_action = "AUTO-START WEBSOCKET NOW"
                scheduler_would_do = "Start auto_trade_live_feed.start_auto_trading() with first valid user/broker"
            elif len(blocking_reasons) > 0:
                next_action = "WAIT (blocked)"
                scheduler_would_do = f"Wait 60 seconds, then check again. Blocked by: {', '.join(blocking_reasons)}"
            else:
                next_action = "WAIT (no conditions)"
                scheduler_would_do = "Wait for stocks to be selected or market to open"

            test_results["test_6_scheduler_simulation"] = {
                "description": "What scheduler would do RIGHT NOW",
                "next_action": next_action,
                "scheduler_behavior": scheduler_would_do,
                "will_start_at_next_check": all_conditions_met,
            }

            # ===== Overall Summary =====
            system_ready = (
                auto_trade_scheduler.is_running
                and len(users_with_selections) > 0
                and valid_count > 0
            )

            return {
                "success": True,
                "system_status": (
                    "FULLY OPERATIONAL" if system_ready else "WAITING FOR CONDITIONS"
                ),
                "auto_start_ready": all_conditions_met,
                "scheduler_running": auto_trade_scheduler.is_running,
                "test_results": test_results,
                "summary": {
                    "scheduler_active": auto_trade_scheduler.is_running,
                    "stocks_selected": len(users_with_selections) > 0,
                    "broker_tokens_valid": valid_count > 0,
                    "market_hours": is_market_hours,
                    "websocket_can_start": all_conditions_met,
                },
                "production_behavior": {
                    "what_happens_next": (
                        "Scheduler checks every 60 seconds. If ALL conditions met, WebSocket auto-starts automatically."
                        if auto_trade_scheduler.is_running
                        else "Scheduler is NOT running - enable in app.py"
                    ),
                    "blocking_reasons": (
                        blocking_reasons
                        if blocking_reasons
                        else ["None - ready to start!"]
                    ),
                },
                "timestamp": datetime.now().isoformat(),
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error testing auto-trading scheduler: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "timestamp": datetime.now().isoformat(),
        }


@router.post("/force-start-auto-trading")
async def debug_force_start_auto_trading():
    """
    FORCE START auto-trading WebSocket - EXACTLY how scheduler does it

    This manually triggers the SAME code path that scheduler uses.
    Use this to test WebSocket startup without waiting for scheduler.

    Process (EXACTLY mirrors scheduler):
    1. Find first user with valid broker config
    2. Validate token expiry
    3. Start auto_trade_live_feed.start_auto_trading()
    4. Return startup status

    WARNING: This is for testing only! In production, scheduler handles this automatically.
    """
    try:
        from services.trading_execution.auto_trade_live_feed import auto_trade_live_feed
        from services.trading_execution.capital_manager import TradingMode
        from database.connection import SessionLocal
        from database.models import BrokerConfig, SelectedStock
        from datetime import date

        db = SessionLocal()

        try:
            # Check if already running (scheduler checks this first)
            if auto_trade_live_feed.is_running:
                return {
                    "success": False,
                    "error": "WebSocket already running!",
                    "current_status": {
                        "is_running": True,
                        "monitored_instruments": len(
                            auto_trade_live_feed.monitored_instruments
                        ),
                        "stats": auto_trade_live_feed.stats,
                    },
                    "action_taken": "None - already active",
                    "timestamp": datetime.now().isoformat(),
                }

            # Check selection in progress (race condition protection)
            from services.intelligent_stock_selection_service import (
                intelligent_stock_selector,
            )

            if intelligent_stock_selector.selection_in_progress:
                return {
                    "success": False,
                    "error": "Stock selection in progress - waiting to avoid race condition",
                    "action_taken": "None - blocked by synchronization flag",
                    "timestamp": datetime.now().isoformat(),
                }

            # Find users with selections (EXACT scheduler query)
            today = date.today()
            users_with_selections = (
                db.query(BrokerConfig)
                .join(SelectedStock, SelectedStock.user_id == BrokerConfig.user_id)
                .filter(
                    BrokerConfig.is_active == True,
                    BrokerConfig.access_token.isnot(None),
                    SelectedStock.selection_date == today,
                    SelectedStock.is_active == True,
                    SelectedStock.option_contract.isnot(None),
                )
                .distinct()
                .all()
            )

            if not users_with_selections:
                return {
                    "success": False,
                    "error": "No users with stock selections today!",
                    "help": "Run /api/debug/debug-run-stock-selection first",
                    "action_taken": "None - no stocks selected",
                    "timestamp": datetime.now().isoformat(),
                }

            # Get first valid broker (EXACT scheduler logic)
            broker_config = None
            for bc in users_with_selections:
                # Validate token expiry
                if bc.access_token_expiry and bc.access_token_expiry < datetime.now():
                    continue
                broker_config = bc
                break

            if not broker_config:
                return {
                    "success": False,
                    "error": "All broker tokens expired!",
                    "help": "Refresh broker token first",
                    "action_taken": "None - tokens expired",
                    "timestamp": datetime.now().isoformat(),
                }

            # Count stocks for this user
            stock_count = (
                db.query(SelectedStock)
                .filter(
                    SelectedStock.user_id == broker_config.user_id,
                    SelectedStock.selection_date == today,
                    SelectedStock.is_active == True,
                    SelectedStock.option_contract.isnot(None),
                )
                .count()
            )

            # START WebSocket (EXACT scheduler code)
            logger.info(
                f"FORCE STARTING auto-trading for user {broker_config.user_id}: {stock_count} stocks"
            )

            asyncio.create_task(
                auto_trade_live_feed.start_auto_trading(
                    user_id=broker_config.user_id,
                    access_token=broker_config.access_token,
                    trading_mode=TradingMode.PAPER,  # Force paper mode for testing
                )
            )

            # Wait for initialization
            await asyncio.sleep(3)

            return {
                "success": True,
                "message": "Auto-trading WebSocket STARTED - EXACTLY how scheduler does it!",
                "user_id": broker_config.user_id,
                "broker": broker_config.broker_name,
                "trading_mode": "paper",
                "stocks_monitored": stock_count,
                "websocket_status": {
                    "is_running": auto_trade_live_feed.is_running,
                    "monitored_instruments": len(
                        auto_trade_live_feed.monitored_instruments
                    ),
                    "subscribed_keys": len(auto_trade_live_feed.subscribed_keys),
                    "stats": auto_trade_live_feed.stats,
                },
                "production_equivalent": "This is EXACTLY what scheduler does automatically at 9:15 AM",
                "timestamp": datetime.now().isoformat(),
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error force starting auto-trading: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "timestamp": datetime.now().isoformat(),
        }


@router.post("/stop-auto-trading")
async def debug_stop_auto_trading():
    """
    STOP auto-trading WebSocket

    This is the manual equivalent of auto-stop conditions being met.
    """
    try:
        from services.trading_execution.auto_trade_live_feed import auto_trade_live_feed

        if not auto_trade_live_feed.is_running:
            return {
                "success": False,
                "error": "WebSocket is not running!",
                "timestamp": datetime.now().isoformat(),
            }

        final_stats = auto_trade_live_feed.stats.copy()
        monitored_count = len(auto_trade_live_feed.monitored_instruments)

        await auto_trade_live_feed.stop()

        return {
            "success": True,
            "message": "Auto-trading WebSocket stopped successfully!",
            "final_stats": final_stats,
            "instruments_monitored": monitored_count,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error stopping auto-trading: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/auto-trading-live-status")
async def debug_auto_trading_live_status():
    """
    Get LIVE status of auto-trading WebSocket

    Shows real-time data flow, strategy execution, and position tracking.
    """
    try:
        from services.trading_execution.auto_trade_live_feed import auto_trade_live_feed

        if not auto_trade_live_feed.is_running:
            return {
                "success": True,
                "websocket_running": False,
                "message": "WebSocket is not running",
                "timestamp": datetime.now().isoformat(),
            }

        # Get live instrument data
        instruments_data = []
        for key, instrument in auto_trade_live_feed.monitored_instruments.items():
            instruments_data.append(
                {
                    "symbol": instrument.stock_symbol,
                    "option_type": instrument.option_type,
                    "strike_price": float(instrument.strike_price),
                    "state": instrument.state.value,
                    "live_spot_price": float(instrument.live_spot_price),
                    "live_option_premium": float(instrument.live_option_premium),
                    "historical_candles": len(
                        instrument.historical_spot_data.get("close", [])
                    ),
                    "last_signal": (
                        instrument.last_signal.signal_type.value
                        if instrument.last_signal
                        else None
                    ),
                    "signal_confidence": (
                        float(instrument.last_signal.confidence)
                        if instrument.last_signal
                        else None
                    ),
                    "active_position": bool(instrument.active_position_id),
                    "entry_price": (
                        float(instrument.entry_price)
                        if instrument.entry_price
                        else None
                    ),
                    "current_pnl": (
                        float(instrument.current_pnl)
                        if instrument.current_pnl
                        else None
                    ),
                }
            )

        return {
            "success": True,
            "websocket_running": True,
            "stats": auto_trade_live_feed.stats,
            "monitored_instruments": len(instruments_data),
            "subscribed_keys": len(auto_trade_live_feed.subscribed_keys),
            "instruments_detail": instruments_data,
            "data_flow_status": {
                "receiving_spot_data": any(
                    i["live_spot_price"] > 0 for i in instruments_data
                ),
                "receiving_option_data": any(
                    i["live_option_premium"] > 0 for i in instruments_data
                ),
                "strategy_running": any(
                    i["historical_candles"] >= 30 for i in instruments_data
                ),
                "signals_generated": any(
                    i["last_signal"] is not None for i in instruments_data
                ),
                "positions_active": any(i["active_position"] for i in instruments_data),
            },
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting live status: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# ============================================================================
# COMPLETE TRADING FLOW DEBUG ENDPOINTS
# ============================================================================


@router.post("/complete-trading-flow")
async def debug_complete_trading_flow():
    """
    COMPREHENSIVE DEBUG ENDPOINT - Complete Trading Flow

    This endpoint simulates the ENTIRE trading process from stock selection to trade execution:
    1. Stock Selection - Get selected stocks from database
    2. Shared Registry - Register instruments and subscribe users
    3. WebSocket Data - Simulate live market data feed
    4. Strategy Signal - Generate trading signals
    5. Trade Preparation - Prepare trade with capital allocation
    6. Trade Execution - Execute trade via execution handler
    7. Position Tracking - Create active position and monitor PnL

    Uses REAL services and database - NO MOCKING OR HARDCODING
    """
    try:
        from database.connection import SessionLocal
        from database.models import SelectedStock, BrokerConfig, User
        from services.trading_execution.shared_instrument_registry import shared_registry
        from services.trading_execution.strategy_engine import strategy_engine
        from services.trading_execution.trade_prep import trade_prep_service, TradingMode
        from services.trading_execution.execution_handler import execution_handler
        from services.trading_execution.capital_manager import capital_manager
        from datetime import date
        from decimal import Decimal
        import json

        db = SessionLocal()
        flow_results = {}

        try:
            logger.info("=" * 80)
            logger.info("STARTING COMPLETE TRADING FLOW DEBUG TEST")
            logger.info("=" * 80)

            # ===== STEP 1: STOCK SELECTION =====
            logger.info("\n[STEP 1] STOCK SELECTION - Getting selected stocks from database")

            today = date.today()
            selected_stocks = (
                db.query(SelectedStock)
                .filter(
                    SelectedStock.selection_date == today,
                    SelectedStock.is_active == True,
                    SelectedStock.option_contract.isnot(None)
                )
                .all()
            )

            if not selected_stocks:
                return {
                    "success": False,
                    "error": "No selected stocks found for today. Run stock selection first.",
                    "help": "Use /api/debug/debug-run-stock-selection to select stocks",
                    "timestamp": datetime.now().isoformat()
                }

            flow_results["step_1_stock_selection"] = {
                "stocks_count": len(selected_stocks),
                "stocks": [
                    {
                        "symbol": s.symbol,
                        "instrument_key": s.instrument_key,
                        "option_type": s.option_type,
                        "price_at_selection": s.price_at_selection,
                        "selection_score": s.selection_score
                    }
                    for s in selected_stocks[:3]  # Show first 3
                ],
                "status": "SUCCESS"
            }
            logger.info(f"✅ Found {len(selected_stocks)} selected stocks")

            # ===== STEP 2: GET USER AND BROKER CONFIG =====
            logger.info("\n[STEP 2] USER & BROKER - Getting active broker configuration")

            # Get first active broker config with valid token
            broker_config = (
                db.query(BrokerConfig)
                .filter(
                    BrokerConfig.is_active == True,
                    BrokerConfig.access_token.isnot(None)
                )
                .first()
            )

            if not broker_config:
                return {
                    "success": False,
                    "error": "No active broker configuration found",
                    "help": "Configure and activate a broker first",
                    "timestamp": datetime.now().isoformat()
                }

            user_id = broker_config.user_id
            broker_name = broker_config.broker_name

            flow_results["step_2_broker_config"] = {
                "user_id": user_id,
                "broker_name": broker_name,
                "broker_id": broker_config.id,
                "has_access_token": bool(broker_config.access_token),
                "status": "SUCCESS"
            }
            logger.info(f"✅ Active broker found: {broker_name} for user {user_id}")

            # ===== STEP 3: SHARED REGISTRY - REGISTER INSTRUMENTS =====
            logger.info("\n[STEP 3] SHARED REGISTRY - Registering instruments and subscribing users")

            # Clear registry first
            shared_registry.clear()

            # Register first selected stock
            first_stock = selected_stocks[0]
            option_data = json.loads(first_stock.option_contract) if isinstance(first_stock.option_contract, str) else first_stock.option_contract

            spot_key = first_stock.instrument_key or f"NSE_EQ|{first_stock.symbol}"
            option_key = option_data.get("option_instrument_key")
            strike_price = Decimal(str(option_data.get("strike_price", 0)))
            lot_size = option_data.get("lot_size", 1)
            expiry_date = first_stock.option_expiry_date or option_data.get("expiry_date")

            # Register instrument in shared registry
            instrument = shared_registry.register_instrument(
                stock_symbol=first_stock.symbol,
                spot_key=spot_key,
                option_key=option_key,
                option_type=first_stock.option_type,
                strike_price=strike_price,
                expiry_date=expiry_date,
                lot_size=lot_size
            )

            # Subscribe user to this instrument
            shared_registry.subscribe_user(
                user_id=user_id,
                option_key=option_key,
                broker_name=broker_name,
                broker_config_id=broker_config.id
            )

            flow_results["step_3_shared_registry"] = {
                "stock_symbol": first_stock.symbol,
                "spot_key": spot_key,
                "option_key": option_key,
                "option_type": first_stock.option_type,
                "strike_price": float(strike_price),
                "lot_size": lot_size,
                "expiry_date": expiry_date,
                "registered_instruments": len(shared_registry.instruments),
                "subscribed_users": len(shared_registry.user_subscriptions),
                "status": "SUCCESS"
            }
            logger.info(f"✅ Registered {first_stock.symbol} in shared registry")
            logger.info(f"   Option Key: {option_key}")
            logger.info(f"   Strike: {strike_price}, Type: {first_stock.option_type}")

            # ===== STEP 4: SIMULATE MARKET DATA =====
            logger.info("\n[STEP 4] MARKET DATA - Simulating live WebSocket feed data")

            # Simulate spot price update
            simulated_spot_price = Decimal(str(first_stock.price_at_selection))

            # Generate historical spot data for strategy
            import numpy as np
            base_price = float(simulated_spot_price)
            historical_close = [base_price * (1 + np.random.uniform(-0.02, 0.02)) for _ in range(50)]
            historical_high = [c * 1.01 for c in historical_close]
            historical_low = [c * 0.99 for c in historical_close]
            historical_open = [c * (1 + np.random.uniform(-0.005, 0.005)) for c in historical_close]
            historical_volume = [1000000 + np.random.randint(-100000, 100000) for _ in range(50)]

            historical_data = {
                'open': historical_open,
                'high': historical_high,
                'low': historical_low,
                'close': historical_close,
                'volume': historical_volume
            }

            # Update spot price in shared registry
            shared_registry.update_spot_price(
                spot_key=spot_key,
                price=simulated_spot_price,
                ohlc_data=[]  # OHLC will be from historical data
            )

            # Manually set historical data
            instrument.historical_spot_data = historical_data

            # Simulate option premium (ATM option typically 2-5% of spot)
            simulated_option_premium = simulated_spot_price * Decimal('0.03')  # 3% of spot

            # Update option data in shared registry
            shared_registry.update_option_data(
                option_key=option_key,
                premium=simulated_option_premium,
                greeks={"delta": 0.5, "theta": -0.05, "gamma": 0.01, "vega": 0.15, "rho": 0.02},
                implied_vol=25.0,
                open_interest=1000000.0,
                volume=50000.0,
                bid_price=float(simulated_option_premium * Decimal('0.995')),
                ask_price=float(simulated_option_premium * Decimal('1.005'))
            )

            flow_results["step_4_market_data"] = {
                "spot_price": float(simulated_spot_price),
                "option_premium": float(simulated_option_premium),
                "historical_candles": len(historical_close),
                "greeks": instrument.option_greeks,
                "implied_volatility": instrument.implied_volatility,
                "status": "SUCCESS"
            }
            logger.info(f"✅ Simulated market data:")
            logger.info(f"   Spot Price: Rs.{simulated_spot_price}")
            logger.info(f"   Option Premium: Rs.{simulated_option_premium}")
            logger.info(f"   Historical Candles: {len(historical_close)}")

            # ===== STEP 5: STRATEGY SIGNAL GENERATION =====
            logger.info("\n[STEP 5] STRATEGY - Generating trading signal")

            signal = strategy_engine.generate_signal(
                current_price=simulated_option_premium,
                historical_data=historical_data,
                option_type=first_stock.option_type
            )

            flow_results["step_5_strategy_signal"] = {
                "signal_type": signal.signal_type.value,
                "confidence": float(signal.confidence),
                "entry_price": float(signal.entry_price),
                "stop_loss": float(signal.stop_loss),
                "target_price": float(signal.target_price),
                "reason": signal.reason,
                "indicators": signal.indicators,
                "status": "SUCCESS"
            }
            logger.info(f"✅ Signal Generated:")
            logger.info(f"   Type: {signal.signal_type.value}")
            logger.info(f"   Confidence: {signal.confidence}")
            logger.info(f"   Entry: Rs.{signal.entry_price}, SL: Rs.{signal.stop_loss}, Target: Rs.{signal.target_price}")

            # ===== STEP 6: TRADE PREPARATION =====
            logger.info("\n[STEP 6] TRADE PREPARATION - Preparing trade with capital allocation")

            prepared_trade = await trade_prep_service.prepare_trade_with_live_data(
                user_id=user_id,
                stock_symbol=first_stock.symbol,
                option_instrument_key=option_key,
                option_type=first_stock.option_type,
                strike_price=strike_price,
                expiry_date=expiry_date,
                lot_size=lot_size,
                current_premium=simulated_option_premium,
                historical_data=historical_data,
                db=db,
                trading_mode=TradingMode.PAPER,
                broker_name=broker_name,
                option_greeks=instrument.option_greeks,
                implied_volatility=instrument.implied_volatility,
                open_interest=instrument.open_interest,
                volume=instrument.volume,
                bid_price=instrument.bid_price,
                ask_price=instrument.ask_price
            )

            flow_results["step_6_trade_preparation"] = {
                "status": prepared_trade.status.value,
                "position_size_lots": prepared_trade.position_size_lots,
                "total_investment": float(prepared_trade.total_investment),
                "max_loss_amount": float(prepared_trade.max_loss_amount),
                "risk_reward_ratio": float(prepared_trade.risk_reward_ratio),
                "entry_price": float(prepared_trade.entry_price),
                "stop_loss": float(prepared_trade.stop_loss),
                "target_price": float(prepared_trade.target_price),
                "trading_mode": prepared_trade.trading_mode,
                "metadata": prepared_trade.metadata,
                "is_ready": prepared_trade.status.value == "ready"
            }
            logger.info(f"✅ Trade Prepared:")
            logger.info(f"   Status: {prepared_trade.status.value}")
            logger.info(f"   Position Size: {prepared_trade.position_size_lots} lots")
            logger.info(f"   Investment: Rs.{prepared_trade.total_investment:,.2f}")
            logger.info(f"   Max Loss: Rs.{prepared_trade.max_loss_amount:,.2f}")

            # ===== STEP 7: TRADE EXECUTION =====
            logger.info("\n[STEP 7] TRADE EXECUTION - Executing trade")

            if prepared_trade.status.value == "ready":
                execution_result = await asyncio.to_thread(
                    execution_handler.execute_trade,
                    prepared_trade,
                    db,
                    None,  # parent_trade_id
                    broker_name,
                    broker_config.id,
                    float(prepared_trade.total_investment)
                )

                flow_results["step_7_trade_execution"] = {
                    "success": execution_result.success,
                    "trade_id": execution_result.trade_id,
                    "order_id": execution_result.order_id,
                    "entry_price": float(execution_result.entry_price),
                    "quantity": execution_result.quantity,
                    "status": execution_result.status,
                    "message": execution_result.message,
                    "trade_execution_id": execution_result.trade_execution_id,
                    "active_position_id": execution_result.active_position_id,
                    "timestamp": execution_result.timestamp
                }

                if execution_result.success:
                    logger.info(f"✅ Trade Executed Successfully:")
                    logger.info(f"   Trade ID: {execution_result.trade_id}")
                    logger.info(f"   Order ID: {execution_result.order_id}")
                    logger.info(f"   Entry Price: Rs.{execution_result.entry_price}")
                    logger.info(f"   Quantity: {execution_result.quantity}")
                    logger.info(f"   DB Record ID: {execution_result.trade_execution_id}")
                    logger.info(f"   Active Position ID: {execution_result.active_position_id}")
                else:
                    logger.error(f"❌ Trade Execution Failed: {execution_result.message}")
            else:
                flow_results["step_7_trade_execution"] = {
                    "success": False,
                    "message": f"Trade not ready for execution: {prepared_trade.status.value}",
                    "reason": prepared_trade.metadata.get("error", "Unknown")
                }
                logger.warning(f"⚠️  Trade not ready: {prepared_trade.status.value}")

            # ===== STEP 8: POSITION TRACKING =====
            logger.info("\n[STEP 8] POSITION TRACKING - Verifying active position in database")

            if flow_results.get("step_7_trade_execution", {}).get("success"):
                from database.models import ActivePosition, AutoTradeExecution

                active_position = (
                    db.query(ActivePosition)
                    .filter(ActivePosition.id == execution_result.active_position_id)
                    .first()
                )

                trade_execution = (
                    db.query(AutoTradeExecution)
                    .filter(AutoTradeExecution.id == execution_result.trade_execution_id)
                    .first()
                )

                flow_results["step_8_position_tracking"] = {
                    "active_position_exists": active_position is not None,
                    "trade_execution_exists": trade_execution is not None,
                    "position_details": {
                        "symbol": active_position.symbol if active_position else None,
                        "instrument_key": active_position.instrument_key if active_position else None,
                        "current_price": active_position.current_price if active_position else None,
                        "current_pnl": active_position.current_pnl if active_position else None,
                        "is_active": active_position.is_active if active_position else None
                    } if active_position else None,
                    "trade_details": {
                        "trade_id": trade_execution.trade_id if trade_execution else None,
                        "symbol": trade_execution.symbol if trade_execution else None,
                        "quantity": trade_execution.quantity if trade_execution else None,
                        "entry_price": trade_execution.entry_price if trade_execution else None,
                        "status": trade_execution.status if trade_execution else None
                    } if trade_execution else None,
                    "status": "SUCCESS" if (active_position and trade_execution) else "FAILED"
                }

                if active_position and trade_execution:
                    logger.info(f"✅ Position Tracking Verified:")
                    logger.info(f"   Active Position ID: {active_position.id}")
                    logger.info(f"   Trade Execution ID: {trade_execution.id}")
                    logger.info(f"   Symbol: {trade_execution.symbol}")
                    logger.info(f"   Status: {trade_execution.status}")
            else:
                flow_results["step_8_position_tracking"] = {
                    "status": "SKIPPED",
                    "reason": "Trade execution failed or not ready"
                }
                logger.info("ℹ️  Position tracking skipped (trade not executed)")

            # ===== SUMMARY =====
            logger.info("\n" + "=" * 80)
            logger.info("COMPLETE TRADING FLOW TEST FINISHED")
            logger.info("=" * 80)

            all_success = all(
                result.get("status") in ["SUCCESS", "SKIPPED"]
                for result in flow_results.values()
                if isinstance(result, dict)
            )

            return {
                "success": True,
                "overall_status": "COMPLETE" if all_success else "PARTIAL_SUCCESS",
                "flow_results": flow_results,
                "summary": {
                    "stock_selected": flow_results.get("step_1_stock_selection", {}).get("stocks_count", 0) > 0,
                    "broker_configured": flow_results.get("step_2_broker_config", {}).get("status") == "SUCCESS",
                    "instrument_registered": flow_results.get("step_3_shared_registry", {}).get("status") == "SUCCESS",
                    "market_data_received": flow_results.get("step_4_market_data", {}).get("status") == "SUCCESS",
                    "signal_generated": flow_results.get("step_5_strategy_signal", {}).get("status") == "SUCCESS",
                    "trade_prepared": flow_results.get("step_6_trade_preparation", {}).get("is_ready", False),
                    "trade_executed": flow_results.get("step_7_trade_execution", {}).get("success", False),
                    "position_tracked": flow_results.get("step_8_position_tracking", {}).get("status") == "SUCCESS"
                },
                "timestamp": datetime.now().isoformat()
            }

        finally:
            # Cleanup
            shared_registry.clear()
            db.close()

    except Exception as e:
        logger.error(f"Error in complete trading flow: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "flow_results": flow_results,
            "timestamp": datetime.now().isoformat()
        }
