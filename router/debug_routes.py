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
async def debug_run_stock_selection():
    """Debug endpoint for the stocks selection service"""

    try:
        from services.intelligent_stock_selection_service import (
            intelligent_stock_selector,
        )

        result = await intelligent_stock_selector.run_premarket_selection()

        if result and not result.get("error"):
            selected_stocks_data = result.get("selected_stocks", [])
            sentiment_analysis = result.get("sentiment_analysis", {})

            logger.info(
                f"✅ Intelligent stock selection complete: {len(selected_stocks_data)} stocks"
            )
            logger.info(
                f"📊 Market sentiment: {sentiment_analysis.get('sentiment')} (A/D: {sentiment_analysis.get('advance_decline_ratio', 1.0):.2f})"
            )

            return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Error running stocks selectionservice")
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
