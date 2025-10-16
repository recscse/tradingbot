from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from datetime import datetime
import logging

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


@router.get("/registry")
async def debug_registry():
    """Debug endpoint for instrument registry"""
    try:
        from services.instrument_registry import instrument_registry

        # Get registry stats
        stats = instrument_registry.get_stats()

        # Get sample live prices
        live_prices_sample = {}
        count = 0

        if hasattr(instrument_registry, "_live_prices"):
            for key, data in instrument_registry._live_prices.items():
                if count < 10:  # Limit to 10 samples
                    live_prices_sample[key] = data
                    count += 1

        # Check if registry is initialized
        initialized = (
            hasattr(instrument_registry, "_initialized")
            and instrument_registry._initialized
        )

        return {
            "success": True,
            "initialized": initialized,
            "stats": stats,
            "live_prices_sample": live_prices_sample,
            "live_prices_count": len(getattr(instrument_registry, "_live_prices", {})),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error debugging registry: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/centralized-ws")
async def debug_centralized_ws():
    """Debug endpoint for centralized WebSocket manager"""
    try:
        from services.centralized_ws_manager import centralized_manager

        # Get manager status
        status = centralized_manager.get_status()

        # Get health check
        health = await centralized_manager.health_check()

        # Get client info
        client_info = {
            "dashboard_clients": len(centralized_manager.dashboard_clients),
            "trading_clients": len(centralized_manager.trading_clients),
            "client_subscriptions": len(centralized_manager.client_subscriptions),
        }

        # Get data stats
        data_stats = {
            "data_count": centralized_manager.data_count,
            "update_count": centralized_manager.update_count,
            "cache_size": len(centralized_manager.market_data_cache),
            "last_data_received": (
                centralized_manager.last_data_received.isoformat()
                if centralized_manager.last_data_received
                else None
            ),
        }

        return {
            "success": True,
            "is_running": centralized_manager.is_running,
            "is_connected": centralized_manager.connection_ready.is_set(),
            "market_status": centralized_manager.market_status,
            "status": status,
            "health": health,
            "client_info": client_info,
            "data_stats": data_stats,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error debugging centralized WebSocket: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/websocket-clients")
async def debug_websocket_clients():
    """Debug endpoint for WebSocket clients"""
    try:
        from router.websocket_routes import active_connections, client_subscriptions

        # Get client info
        clients = []
        for client_id, ws in active_connections.items():
            subscriptions = list(client_subscriptions.get(client_id, set()))
            clients.append(
                {
                    "client_id": client_id,
                    "subscriptions_count": len(subscriptions),
                    "subscriptions_sample": subscriptions[:5] if subscriptions else [],
                }
            )

        return {
            "success": True,
            "total_clients": len(active_connections),
            "clients": clients,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error debugging WebSocket clients: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@router.post("/test-broadcast")
async def test_broadcast(message: str = "Test broadcast"):
    """Test the WebSocket broadcast mechanism"""
    try:
        from router.websocket_routes import broadcast_market_data
        from services.instrument_registry import instrument_registry

        # Get sample data from registry
        sample_data = {}
        sample_count = 0

        # Try to get actual data from registry
        if (
            hasattr(instrument_registry, "_live_prices")
            and instrument_registry._live_prices
        ):
            for key, data in instrument_registry._live_prices.items():
                if sample_count < 5:  # Limit to 5 instruments
                    sample_data[key] = data
                    sample_count += 1

        # If no data found, create dummy data
        if not sample_data:
            sample_data = {
                "NSE_INDEX|Nifty 50": {
                    "ltp": 25000.0,
                    "ltq": 0,
                    "cp": 24800.0,
                    "change": 200.0,
                    "change_percent": 0.81,
                    "timestamp": datetime.now().isoformat(),
                },
                "NSE_EQ|INE002A01018": {  # RELIANCE
                    "ltp": 2500.0,
                    "ltq": 100,
                    "cp": 2475.0,
                    "change": 25.0,
                    "change_percent": 1.01,
                    "timestamp": datetime.now().isoformat(),
                },
            }

        # Add test message
        for key in sample_data:
            sample_data[key]["test_message"] = message
            sample_data[key]["timestamp"] = datetime.now().isoformat()

        # Create task to broadcast data
        import asyncio

        asyncio.create_task(broadcast_market_data(sample_data))

        return {
            "success": True,
            "message": f"Test broadcast initiated with {len(sample_data)} instruments",
            "data_sample": sample_data,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error testing broadcast: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/instrument/{symbol}")
async def debug_instrument(symbol: str):
    """Debug endpoint for a specific instrument"""
    try:
        from services.instrument_registry import instrument_registry

        # Get instrument data
        spot_data = instrument_registry.get_spot_price(symbol.upper())

        # Get all keys associated with this symbol
        keys = instrument_registry.get_instrument_keys_for_trading(symbol.upper())

        # Get live prices for these keys
        live_prices = {}
        if hasattr(instrument_registry, "_live_prices"):
            for key in keys:
                if key in instrument_registry._live_prices:
                    live_prices[key] = instrument_registry._live_prices[key]

        return {
            "success": True,
            "symbol": symbol.upper(),
            "spot_data": spot_data,
            "instrument_keys": keys,
            "live_prices": live_prices,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error debugging instrument {symbol}: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/index-data")
async def debug_index_data():
    """Debug endpoint to inspect all index data"""
    try:
        from services.instrument_registry import instrument_registry

        debug_data = instrument_registry.debug_index_data()

        return {
            "success": True,
            "data": debug_data,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"❌ Error debugging index data: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/mcx-data")
async def debug_mcx_data():
    """Debug endpoint to inspect MCX data"""
    try:
        from services.instrument_registry import instrument_registry

        debug_data = instrument_registry.debug_mcx_data()

        return {
            "success": True,
            "data": debug_data,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"❌ Error debugging MCX data: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/test-options-selection")
async def debug_test_options_selection():
    """
    Debug endpoint to test options selection for selected stocks

    Tests:
    1. Load selected stocks from database
    2. Fetch option chains
    3. Select optimal strikes
    4. Calculate capital allocation
    5. Store option contracts
    """
    try:
        from services.enhanced_intelligent_options_selection import (
            enhanced_options_service,
        )
        from database.connection import SessionLocal
        from database.models import SelectedStock
        from datetime import date

        db = SessionLocal()

        try:
            # Step 1: Get today's selected stocks
            selected_stocks = (
                db.query(SelectedStock)
                .filter(
                    SelectedStock.selection_date == date.today(),
                    SelectedStock.is_active == True,
                )
                .all()
            )

            if not selected_stocks:
                return {
                    "success": False,
                    "error": "No selected stocks found for today. Run stock selection first.",
                    "timestamp": datetime.now().isoformat(),
                }

            logger.info(f"Found {len(selected_stocks)} selected stocks")

            # Step 2: Enhance with options
            result = (
                await enhanced_options_service.enhance_selected_stocks_with_options(
                    selected_stocks, selection_type="debug"
                )
            )

            # Step 3: Collect results
            enhanced_stocks = []
            for stock in selected_stocks:
                if stock.option_contract:
                    import json

                    option_data = (
                        json.loads(stock.option_contract)
                        if isinstance(stock.option_contract, str)
                        else stock.option_contract
                    )

                    enhanced_stocks.append(
                        {
                            "symbol": stock.symbol,
                            "option_type": stock.option_type,
                            "option_instrument_key": option_data.get(
                                "option_instrument_key"
                            ),
                            "strike_price": option_data.get("strike_price"),
                            "premium": option_data.get("premium"),
                            "expiry_date": stock.option_expiry_date,
                            "lot_size": option_data.get("lot_size"),
                            "volume": option_data.get("volume"),
                            "open_interest": option_data.get("open_interest"),
                            "selection_score": option_data.get("selection_score"),
                        }
                    )

            return {
                "success": True,
                "message": f"Options selection completed for {len(enhanced_stocks)} stocks",
                "selected_stocks_count": len(selected_stocks),
                "enhanced_stocks_count": len(enhanced_stocks),
                "enhanced_stocks": enhanced_stocks,
                "timestamp": datetime.now().isoformat(),
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error testing options selection: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/test-capital-manager")
async def debug_test_capital_manager():
    """
    Debug endpoint to test capital manager

    Tests:
    1. Get available capital (paper vs live mode)
    2. Calculate position size
    3. Validate capital availability
    4. Check broker configuration
    """
    try:
        from services.trading_execution.capital_manager import (
            capital_manager,
            TradingMode,
        )
        from database.connection import SessionLocal
        from decimal import Decimal

        db = SessionLocal()

        try:
            user_id = 1  # Test user

            # Test 1: Paper trading capital
            paper_capital = capital_manager.get_available_capital(
                user_id, db, TradingMode.PAPER
            )

            # Test 2: Live trading capital
            live_broker_config = capital_manager.get_active_broker_config(user_id, db)
            live_capital = capital_manager.get_available_capital(
                user_id, db, TradingMode.LIVE
            )

            # Test 3: Calculate position size
            test_premium = Decimal("85.50")
            test_lot_size = 250

            capital_allocation = capital_manager.calculate_position_size(
                paper_capital, test_premium, test_lot_size
            )

            # Test 4: Validate capital
            validation = capital_manager.validate_capital_availability(
                paper_capital,
                capital_allocation.position_value,
                max_capital_per_trade_percent=Decimal("0.20"),
            )

            return {
                "success": True,
                "paper_trading": {
                    "available_capital": float(paper_capital),
                    "capital_allocation": {
                        "total_capital": float(capital_allocation.total_capital),
                        "allocated_capital": float(
                            capital_allocation.allocated_capital
                        ),
                        "position_size_lots": capital_allocation.position_size_lots,
                        "position_value": float(capital_allocation.position_value),
                        "max_loss": float(capital_allocation.max_loss),
                        "capital_utilization_percent": float(
                            capital_allocation.capital_utilization_percent
                        ),
                        "risk_per_trade_percent": float(
                            capital_allocation.risk_per_trade_percent
                        ),
                    },
                    "validation": validation,
                },
                "live_trading": {
                    "broker_active": live_broker_config is not None,
                    "broker_name": (
                        live_broker_config.broker_name if live_broker_config else None
                    ),
                    "available_capital": float(live_capital) if live_capital > 0 else 0,
                },
                "test_parameters": {
                    "premium": float(test_premium),
                    "lot_size": test_lot_size,
                },
                "timestamp": datetime.now().isoformat(),
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error testing capital manager: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/test-trading-mode-db")
async def debug_test_trading_mode_db():
    """
    Debug endpoint to test trading mode from database

    Tests:
    1. Get user trading preferences
    2. Check if trading mode is stored
    3. Validate execution mode
    """
    try:
        from database.connection import SessionLocal
        from database.models import UserTradingConfig

        db = SessionLocal()

        try:
            user_id = 1  # Test user

            # Get trading config
            trading_config = (
                db.query(UserTradingConfig)
                .filter(UserTradingConfig.user_id == user_id)
                .first()
            )

            if not trading_config:
                # Create default config
                trading_config = UserTradingConfig(
                    user_id=user_id, trading_mode="paper", execution_mode="multi_demat"
                )
                db.add(trading_config)
                db.commit()
                db.refresh(trading_config)

                created = True
            else:
                created = False

            return {
                "success": True,
                "created": created,
                "user_id": user_id,
                "trading_mode": trading_config.trading_mode or "paper",
                "execution_mode": trading_config.execution_mode or "multi_demat",
                "auto_execute": (
                    trading_config.auto_execute
                    if hasattr(trading_config, "auto_execute")
                    else False
                ),
                "timestamp": datetime.now().isoformat(),
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error testing trading mode DB: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/test-strategy-engine")
async def debug_test_strategy_engine():
    """
    Debug endpoint to test strategy engine

    Tests:
    1. Generate signals with mock OHLC data
    2. Test for CE (call) options
    3. Test for PE (put) options
    4. Validate stop loss and target calculation
    """
    try:
        from services.trading_execution.strategy_engine import (
            strategy_engine,
            SignalType,
        )
        from decimal import Decimal
        import numpy as np

        # Create mock OHLC data (50 candles with uptrend)
        historical_data = {
            "open": list(np.linspace(3050, 3090, 50)),
            "high": list(np.linspace(3055, 3100, 50)),
            "low": list(np.linspace(3045, 3085, 50)),
            "close": list(np.linspace(3050, 3095, 50)),
            "volume": [10000] * 50,
        }

        current_price = Decimal("3097.7")

        # Test 1: CE (Call) signal
        ce_signal = strategy_engine.generate_signal(
            current_price=current_price,
            historical_data=historical_data,
            option_type="CE",
        )

        # Test 2: PE (Put) signal (mock downtrend data)
        downtrend_data = {
            "open": list(np.linspace(3100, 3060, 50)),
            "high": list(np.linspace(3110, 3070, 50)),
            "low": list(np.linspace(3090, 3050, 50)),
            "close": list(np.linspace(3100, 3055, 50)),
            "volume": [10000] * 50,
        }

        pe_signal = strategy_engine.generate_signal(
            current_price=Decimal("3055.0"),
            historical_data=downtrend_data,
            option_type="PE",
        )

        return {
            "success": True,
            "ce_signal": {
                "signal_type": ce_signal.signal_type.value,
                "confidence": float(ce_signal.confidence),
                "reason": ce_signal.reason,
                "entry_price": float(ce_signal.entry_price),
                "stop_loss": float(ce_signal.stop_loss),
                "target_price": float(ce_signal.target_price),
                "indicators": ce_signal.indicators,
                "risk_reward_ratio": (
                    float(
                        (ce_signal.target_price - ce_signal.entry_price)
                        / abs(ce_signal.entry_price - ce_signal.stop_loss)
                    )
                    if ce_signal.stop_loss != ce_signal.entry_price
                    else 0
                ),
            },
            "pe_signal": {
                "signal_type": pe_signal.signal_type.value,
                "confidence": float(pe_signal.confidence),
                "reason": pe_signal.reason,
                "entry_price": float(pe_signal.entry_price),
                "stop_loss": float(pe_signal.stop_loss),
                "target_price": float(pe_signal.target_price),
                "indicators": pe_signal.indicators,
                "risk_reward_ratio": (
                    float(
                        abs(pe_signal.entry_price - pe_signal.target_price)
                        / abs(pe_signal.stop_loss - pe_signal.entry_price)
                    )
                    if pe_signal.stop_loss != pe_signal.entry_price
                    else 0
                ),
            },
            "test_data_info": {
                "ce_test": "Uptrend data (3050 → 3095)",
                "pe_test": "Downtrend data (3100 → 3055)",
                "candles_count": 50,
            },
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error testing strategy engine: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/test-complete-flow")
async def debug_test_complete_flow():
    """
    Debug endpoint to test COMPLETE trading flow

    Flow:
    1. Check analytics availability
    2. Run stock selection
    3. Enhance with options
    4. Test capital allocation
    5. Test strategy signal generation
    6. Simulate trade preparation
    7. Check PnL tracker readiness

    This tests the ENTIRE system from start to finish!
    """
    try:
        from services.realtime_market_engine import get_analytics, get_market_engine
        from services.intelligent_stock_selection_service import (
            intelligent_stock_selector,
        )
        from services.enhanced_intelligent_options_selection import (
            enhanced_options_service,
        )
        from services.trading_execution.capital_manager import (
            capital_manager,
            TradingMode,
        )
        from services.trading_execution.strategy_engine import strategy_engine
        from services.trading_execution import trade_prep_service
        from database.connection import SessionLocal
        from database.models import SelectedStock, UserTradingConfig
        from datetime import date
        from decimal import Decimal
        import numpy as np

        db = SessionLocal()
        flow_results = {}

        try:
            # ===== STEP 1: Check Analytics =====
            logger.info("🔍 Step 1: Checking analytics availability...")
            try:
                analytics = get_analytics()
                engine = get_market_engine()

                flow_results["step_1_analytics"] = {
                    "success": True,
                    "market_sentiment": analytics.get("market_sentiment", {}).get(
                        "sentiment", "unknown"
                    ),
                    "advance_decline_ratio": analytics.get("market_sentiment", {}).get(
                        "advance_decline_ratio", 0
                    ),
                    "instruments_count": (
                        len(engine.instruments) if hasattr(engine, "instruments") else 0
                    ),
                    "analytics_available": bool(analytics),
                }
            except Exception as e:
                flow_results["step_1_analytics"] = {"success": False, "error": str(e)}

            # ===== STEP 2: Run Stock Selection =====
            logger.info("🔍 Step 2: Running intelligent stock selection...")
            try:
                selection_result = (
                    await intelligent_stock_selector.run_premarket_selection()
                )

                flow_results["step_2_stock_selection"] = {
                    "success": not selection_result.get("error"),
                    "selected_stocks_count": len(
                        selection_result.get("selected_stocks", [])
                    ),
                    "sentiment": selection_result.get("sentiment_analysis", {}).get(
                        "sentiment"
                    ),
                    "selected_stocks": [
                        s["symbol"] for s in selection_result.get("selected_stocks", [])
                    ],
                }
            except Exception as e:
                flow_results["step_2_stock_selection"] = {
                    "success": False,
                    "error": str(e),
                }

            # ===== STEP 3: Options Enhancement =====
            logger.info("🔍 Step 3: Enhancing with options...")
            try:
                selected_stocks = (
                    db.query(SelectedStock)
                    .filter(
                        SelectedStock.selection_date == date.today(),
                        SelectedStock.is_active == True,
                    )
                    .all()
                )

                if selected_stocks:
                    await enhanced_options_service.enhance_selected_stocks_with_options(
                        selected_stocks, "debug_test"
                    )

                    # Count stocks with option contracts
                    enhanced_count = sum(
                        1 for s in selected_stocks if s.option_contract
                    )

                    flow_results["step_3_options_enhancement"] = {
                        "success": True,
                        "stocks_with_options": enhanced_count,
                        "total_stocks": len(selected_stocks),
                    }
                else:
                    flow_results["step_3_options_enhancement"] = {
                        "success": False,
                        "error": "No selected stocks found",
                    }
            except Exception as e:
                flow_results["step_3_options_enhancement"] = {
                    "success": False,
                    "error": str(e),
                }

            # ===== STEP 4: Test Capital Allocation =====
            logger.info("🔍 Step 4: Testing capital allocation...")
            try:
                user_id = 1

                # Get trading mode from DB
                trading_config = (
                    db.query(UserTradingConfig)
                    .filter(UserTradingConfig.user_id == user_id)
                    .first()
                )

                if not trading_config:
                    trading_config = UserTradingConfig(
                        user_id=user_id,
                        trading_mode="paper",
                        execution_mode="multi_demat",
                    )
                    db.add(trading_config)
                    db.commit()

                trading_mode = TradingMode(trading_config.trading_mode or "paper")
                available_capital = capital_manager.get_available_capital(
                    user_id, db, trading_mode
                )

                # Test position sizing
                test_premium = Decimal("85.50")
                test_lot_size = 250
                allocation = capital_manager.calculate_position_size(
                    available_capital, test_premium, test_lot_size
                )

                flow_results["step_4_capital_allocation"] = {
                    "success": True,
                    "trading_mode": trading_mode.value,
                    "available_capital": float(available_capital),
                    "position_size_lots": allocation.position_size_lots,
                    "position_value": float(allocation.position_value),
                    "capital_utilization": float(
                        allocation.capital_utilization_percent
                    ),
                }
            except Exception as e:
                flow_results["step_4_capital_allocation"] = {
                    "success": False,
                    "error": str(e),
                }

            # ===== STEP 5: Test Strategy Signal =====
            logger.info("🔍 Step 5: Testing strategy signal generation...")
            try:
                # Mock uptrend data
                historical_data = {
                    "open": list(np.linspace(3050, 3090, 50)),
                    "high": list(np.linspace(3055, 3100, 50)),
                    "low": list(np.linspace(3045, 3085, 50)),
                    "close": list(np.linspace(3050, 3095, 50)),
                    "volume": [10000] * 50,
                }

                signal = strategy_engine.generate_signal(
                    current_price=Decimal("3097.7"),
                    historical_data=historical_data,
                    option_type="CE",
                )

                flow_results["step_5_strategy_signal"] = {
                    "success": True,
                    "signal_type": signal.signal_type.value,
                    "confidence": float(signal.confidence),
                    "entry_price": float(signal.entry_price),
                    "stop_loss": float(signal.stop_loss),
                    "target_price": float(signal.target_price),
                    "reason": signal.reason,
                }
            except Exception as e:
                flow_results["step_5_strategy_signal"] = {
                    "success": False,
                    "error": str(e),
                }

            # ===== STEP 6: Test Trade Preparation =====
            logger.info("🔍 Step 6: Testing trade preparation...")
            try:
                # Get first selected stock with option contract
                test_stock = (
                    db.query(SelectedStock)
                    .filter(
                        SelectedStock.selection_date == date.today(),
                        SelectedStock.is_active == True,
                        SelectedStock.option_contract.isnot(None),
                    )
                    .first()
                )

                if test_stock:
                    import json

                    option_data = (
                        json.loads(test_stock.option_contract)
                        if isinstance(test_stock.option_contract, str)
                        else test_stock.option_contract
                    )

                    prepared_trade = await trade_prep_service.prepare_trade(
                        user_id=user_id,
                        stock_symbol=test_stock.symbol,
                        option_instrument_key=option_data.get("option_instrument_key"),
                        option_type=test_stock.option_type,
                        strike_price=Decimal(str(option_data.get("strike_price", 0))),
                        expiry_date=test_stock.option_expiry_date,
                        lot_size=option_data.get("lot_size", 1),
                        db=db,
                        trading_mode=trading_mode,
                    )

                    flow_results["step_6_trade_preparation"] = {
                        "success": prepared_trade.status.value == "ready",
                        "status": prepared_trade.status.value,
                        "stock_symbol": prepared_trade.stock_symbol,
                        "entry_price": float(prepared_trade.entry_price),
                        "stop_loss": float(prepared_trade.stop_loss),
                        "target_price": float(prepared_trade.target_price),
                        "position_size_lots": prepared_trade.position_size_lots,
                        "total_investment": float(prepared_trade.total_investment),
                    }
                else:
                    flow_results["step_6_trade_preparation"] = {
                        "success": False,
                        "error": "No stock with option contract available",
                    }
            except Exception as e:
                flow_results["step_6_trade_preparation"] = {
                    "success": False,
                    "error": str(e),
                }

            # ===== STEP 7: Check PnL Tracker =====
            logger.info("🔍 Step 7: Checking PnL tracker readiness...")
            try:
                from services.trading_execution.pnl_tracker import pnl_tracker

                flow_results["step_7_pnl_tracker"] = {
                    "success": True,
                    "is_running": pnl_tracker.is_running,
                    "update_interval": pnl_tracker.update_interval_seconds,
                    "ready": True,
                }
            except Exception as e:
                flow_results["step_7_pnl_tracker"] = {"success": False, "error": str(e)}

            # ===== Calculate Overall Success =====
            all_steps_success = all(
                step.get("success", False) for step in flow_results.values()
            )

            return {
                "success": True,
                "all_steps_passed": all_steps_success,
                "flow_results": flow_results,
                "summary": {
                    "total_steps": len(flow_results),
                    "passed_steps": sum(
                        1 for s in flow_results.values() if s.get("success", False)
                    ),
                    "failed_steps": sum(
                        1 for s in flow_results.values() if not s.get("success", False)
                    ),
                },
                "timestamp": datetime.now().isoformat(),
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error in complete flow test: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "flow_results": flow_results,
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/test-full-live-execution")
async def debug_test_full_live_execution():
    """
    Debug endpoint to test COMPLETE LIVE EXECUTION flow

    This simulates the EXACT production flow:
    1. Select stocks intelligently
    2. Enhance with option contracts
    3. Load instruments for auto-trading
    4. Start WebSocket connection (simulated)
    5. Generate strategy signals with live data
    6. Execute trades automatically
    7. Monitor PnL in real-time
    8. Book profits/losses

    This is a FULL SIMULATION of the production system!
    """
    execution_log = []  # Initialize outside try block
    db = None

    try:
        from services.intelligent_stock_selection_service import (
            intelligent_stock_selector,
        )
        from services.enhanced_intelligent_options_selection import (
            enhanced_options_service,
        )
        from services.trading_execution.capital_manager import TradingMode
        from services.trading_execution.strategy_engine import strategy_engine
        from services.trading_execution import trade_prep_service, execution_handler
        from database.connection import SessionLocal
        from database.models import (
            SelectedStock,
            UserTradingConfig,
            ActivePosition,
            AutoTradeExecution,
        )
        from datetime import date
        from decimal import Decimal
        import json

        db = SessionLocal()

        try:
            # ===== PHASE 1: STOCK SELECTION =====
            execution_log.append(
                {
                    "phase": "1_STOCK_SELECTION",
                    "status": "STARTING",
                    "message": "Running intelligent stock selection...",
                }
            )

            selection_result = (
                await intelligent_stock_selector.run_premarket_selection()
            )

            if selection_result.get("error"):
                raise Exception(
                    f"Stock selection failed: {selection_result.get('error')}"
                )

            selected_stocks_data = selection_result.get("selected_stocks", [])
            sentiment = selection_result.get("sentiment_analysis", {}).get(
                "sentiment", "unknown"
            )

            execution_log.append(
                {
                    "phase": "1_STOCK_SELECTION",
                    "status": "COMPLETED",
                    "selected_count": len(selected_stocks_data),
                    "sentiment": sentiment,
                    "stocks": [s["symbol"] for s in selected_stocks_data],
                }
            )

            # ===== PHASE 2: OPTIONS ENHANCEMENT =====
            execution_log.append(
                {
                    "phase": "2_OPTIONS_ENHANCEMENT",
                    "status": "STARTING",
                    "message": "Fetching and selecting optimal option contracts...",
                }
            )

            selected_stocks = (
                db.query(SelectedStock)
                .filter(
                    SelectedStock.selection_date == date.today(),
                    SelectedStock.is_active == True,
                )
                .all()
            )

            if not selected_stocks:
                raise Exception("No stocks found in database after selection")

            # Enhance with options
            await enhanced_options_service.enhance_selected_stocks_with_options(
                selected_stocks, "live_test"
            )

            # Refresh and collect option details
            db.refresh(selected_stocks[0])
            enhanced_stocks = []
            for stock in selected_stocks:
                if stock.option_contract:
                    option_data = (
                        json.loads(stock.option_contract)
                        if isinstance(stock.option_contract, str)
                        else stock.option_contract
                    )
                    enhanced_stocks.append(
                        {
                            "symbol": stock.symbol,
                            "option_type": stock.option_type,
                            "strike": option_data.get("strike_price"),
                            "premium": option_data.get("premium"),
                            "instrument_key": option_data.get("option_instrument_key"),
                        }
                    )

            execution_log.append(
                {
                    "phase": "2_OPTIONS_ENHANCEMENT",
                    "status": "COMPLETED",
                    "enhanced_count": len(enhanced_stocks),
                    "options": enhanced_stocks,
                }
            )

            # ===== PHASE 3: LOAD AUTO-TRADE INSTRUMENTS =====
            execution_log.append(
                {
                    "phase": "3_LOAD_INSTRUMENTS",
                    "status": "STARTING",
                    "message": "Loading instruments for auto-trading...",
                }
            )

            user_id = 1
            trading_config = (
                db.query(UserTradingConfig)
                .filter(UserTradingConfig.user_id == user_id)
                .first()
            )

            if not trading_config:
                trading_config = UserTradingConfig(
                    user_id=user_id, trading_mode="paper", execution_mode="multi_demat"
                )
                db.add(trading_config)
                db.commit()

            trading_mode = TradingMode(trading_config.trading_mode or "paper")

            # Simulate loading instruments (don't actually start WebSocket)
            loaded_instruments = []
            for stock in selected_stocks:
                if stock.option_contract:
                    option_data = (
                        json.loads(stock.option_contract)
                        if isinstance(stock.option_contract, str)
                        else stock.option_contract
                    )
                    loaded_instruments.append(
                        {
                            "stock_symbol": stock.symbol,
                            "spot_key": f"NSE_EQ|{stock.symbol}",
                            "option_key": option_data.get("option_instrument_key"),
                            "option_type": stock.option_type,
                            "strike": option_data.get("strike_price"),
                            "lot_size": option_data.get("lot_size"),
                        }
                    )

            execution_log.append(
                {
                    "phase": "3_LOAD_INSTRUMENTS",
                    "status": "COMPLETED",
                    "loaded_count": len(loaded_instruments),
                    "trading_mode": trading_mode.value,
                    "instruments": loaded_instruments,
                }
            )

            # ===== PHASE 4: STRATEGY SIGNAL GENERATION =====
            execution_log.append(
                {
                    "phase": "4_STRATEGY_SIGNALS",
                    "status": "STARTING",
                    "message": "Generating trading signals for loaded instruments...",
                }
            )

            # Generate mock OHLC data based on market sentiment
            import numpy as np

            if sentiment in ["bullish", "very_bullish"]:
                # Uptrend data
                historical_data = {
                    "open": list(np.linspace(3050, 3090, 50)),
                    "high": list(np.linspace(3055, 3100, 50)),
                    "low": list(np.linspace(3045, 3085, 50)),
                    "close": list(np.linspace(3050, 3095, 50)),
                    "volume": [10000] * 50,
                }
                current_price = Decimal("3097.7")
            else:
                # Downtrend data
                historical_data = {
                    "open": list(np.linspace(3100, 3060, 50)),
                    "high": list(np.linspace(3110, 3070, 50)),
                    "low": list(np.linspace(3090, 3050, 50)),
                    "close": list(np.linspace(3100, 3055, 50)),
                    "volume": [10000] * 50,
                }
                current_price = Decimal("3055.0")

            # Generate signals for each stock
            signals_generated = []
            for instrument in loaded_instruments:
                try:
                    signal = strategy_engine.generate_signal(
                        current_price=current_price,
                        historical_data=historical_data,
                        option_type=instrument["option_type"],
                    )

                    # Validate signal
                    is_valid = signal.confidence >= Decimal("0.65") and (
                        (
                            instrument["option_type"] == "CE"
                            and signal.signal_type.value == "buy"
                        )
                        or (
                            instrument["option_type"] == "PE"
                            and signal.signal_type.value == "sell"
                        )
                    )

                    signals_generated.append(
                        {
                            "symbol": instrument["stock_symbol"],
                            "signal_type": signal.signal_type.value,
                            "confidence": float(signal.confidence),
                            "entry_price": float(signal.entry_price),
                            "stop_loss": float(signal.stop_loss),
                            "target": float(signal.target_price),
                            "valid": is_valid,
                            "reason": signal.reason,
                        }
                    )
                except Exception as e:
                    signals_generated.append(
                        {
                            "symbol": instrument["stock_symbol"],
                            "error": str(e),
                            "valid": False,
                        }
                    )

            valid_signals = [s for s in signals_generated if s.get("valid")]

            execution_log.append(
                {
                    "phase": "4_STRATEGY_SIGNALS",
                    "status": "COMPLETED",
                    "total_signals": len(signals_generated),
                    "valid_signals": len(valid_signals),
                    "signals": signals_generated,
                }
            )

            # ===== PHASE 5: TRADE EXECUTION =====
            execution_log.append(
                {
                    "phase": "5_TRADE_EXECUTION",
                    "status": "STARTING",
                    "message": f"Executing {len(valid_signals)} valid trades...",
                }
            )

            executed_trades = []
            for signal_data in valid_signals:
                try:
                    # Find stock in database
                    stock = (
                        db.query(SelectedStock)
                        .filter(
                            SelectedStock.symbol == signal_data["symbol"],
                            SelectedStock.selection_date == date.today(),
                            SelectedStock.is_active == True,
                        )
                        .first()
                    )

                    if not stock or not stock.option_contract:
                        continue

                    option_data = (
                        json.loads(stock.option_contract)
                        if isinstance(stock.option_contract, str)
                        else stock.option_contract
                    )

                    # Prepare trade
                    prepared_trade = await trade_prep_service.prepare_trade(
                        user_id=user_id,
                        stock_symbol=stock.symbol,
                        option_instrument_key=option_data.get("option_instrument_key"),
                        option_type=stock.option_type,
                        strike_price=Decimal(str(option_data.get("strike_price", 0))),
                        expiry_date=stock.option_expiry_date,
                        lot_size=option_data.get("lot_size", 1),
                        db=db,
                        trading_mode=trading_mode,
                    )

                    if prepared_trade.status.value != "ready":
                        executed_trades.append(
                            {
                                "symbol": stock.symbol,
                                "status": "FAILED",
                                "reason": f"Trade not ready: {prepared_trade.status.value}",
                            }
                        )
                        continue

                    # Execute trade
                    execution_result = execution_handler.execute_trade(
                        prepared_trade, db
                    )

                    if execution_result.success:
                        executed_trades.append(
                            {
                                "symbol": stock.symbol,
                                "status": "EXECUTED",
                                "trade_id": execution_result.trade_id,
                                "order_id": execution_result.order_id,
                                "entry_price": float(execution_result.entry_price),
                                "quantity": execution_result.quantity,
                                "position_id": execution_result.active_position_id,
                            }
                        )
                    else:
                        executed_trades.append(
                            {
                                "symbol": stock.symbol,
                                "status": "FAILED",
                                "reason": execution_result.message,
                            }
                        )

                except Exception as e:
                    executed_trades.append(
                        {
                            "symbol": signal_data["symbol"],
                            "status": "ERROR",
                            "error": str(e),
                        }
                    )

            successful_executions = [
                t for t in executed_trades if t.get("status") == "EXECUTED"
            ]

            execution_log.append(
                {
                    "phase": "5_TRADE_EXECUTION",
                    "status": "COMPLETED",
                    "total_attempts": len(executed_trades),
                    "successful": len(successful_executions),
                    "failed": len(executed_trades) - len(successful_executions),
                    "trades": executed_trades,
                }
            )

            # ===== PHASE 6: PNL MONITORING SIMULATION =====
            execution_log.append(
                {
                    "phase": "6_PNL_MONITORING",
                    "status": "STARTING",
                    "message": "Simulating PnL monitoring and profit booking...",
                }
            )

            # Get active positions
            active_positions = (
                db.query(ActivePosition)
                .filter(
                    ActivePosition.user_id == user_id, ActivePosition.is_active == True
                )
                .all()
            )

            pnl_snapshots = []
            for position in active_positions:
                try:
                    trade = (
                        db.query(AutoTradeExecution)
                        .filter(AutoTradeExecution.id == position.trade_execution_id)
                        .first()
                    )

                    if not trade:
                        continue

                    # Simulate price movement (5% profit)
                    entry_price = Decimal(str(trade.entry_price))
                    simulated_current_price = entry_price * Decimal("1.05")  # 5% profit
                    quantity = trade.quantity

                    # Calculate PnL
                    pnl_points = simulated_current_price - entry_price
                    pnl_amount = pnl_points * Decimal(str(quantity))
                    pnl_percent = (pnl_points / entry_price) * Decimal("100")

                    # Calculate trailing SL (2% trail)
                    trailing_sl = simulated_current_price * Decimal("0.98")

                    pnl_snapshots.append(
                        {
                            "symbol": position.symbol,
                            "trade_id": trade.trade_id,
                            "entry_price": float(entry_price),
                            "current_price": float(simulated_current_price),
                            "pnl_amount": float(pnl_amount),
                            "pnl_percent": float(pnl_percent),
                            "trailing_sl": float(trailing_sl),
                            "target": float(trade.target_1) if trade.target_1 else 0,
                            "status": "IN_PROFIT",
                        }
                    )

                except Exception as e:
                    pnl_snapshots.append({"symbol": position.symbol, "error": str(e)})

            execution_log.append(
                {
                    "phase": "6_PNL_MONITORING",
                    "status": "COMPLETED",
                    "positions_monitored": len(pnl_snapshots),
                    "pnl_snapshots": pnl_snapshots,
                }
            )

            # ===== PHASE 7: PROFIT BOOKING SIMULATION =====
            execution_log.append(
                {
                    "phase": "7_PROFIT_BOOKING",
                    "status": "STARTING",
                    "message": "Simulating target hit and profit booking...",
                }
            )

            profit_bookings = []
            for pnl_snapshot in pnl_snapshots:
                if pnl_snapshot.get("status") == "IN_PROFIT":
                    # Simulate target hit (profit booking)
                    profit_bookings.append(
                        {
                            "symbol": pnl_snapshot["symbol"],
                            "exit_reason": "TARGET_HIT",
                            "entry_price": pnl_snapshot["entry_price"],
                            "exit_price": pnl_snapshot["current_price"],
                            "gross_pnl": pnl_snapshot["pnl_amount"],
                            "net_pnl": pnl_snapshot["pnl_amount"]
                            * 0.995,  # After 0.5% brokerage
                            "pnl_percent": pnl_snapshot["pnl_percent"],
                            "status": "PROFIT_BOOKED",
                        }
                    )

            execution_log.append(
                {
                    "phase": "7_PROFIT_BOOKING",
                    "status": "COMPLETED",
                    "profits_booked": len(profit_bookings),
                    "bookings": profit_bookings,
                }
            )

            # ===== FINAL SUMMARY =====
            total_pnl = sum(b["net_pnl"] for b in profit_bookings)

            return {
                "success": True,
                "message": "COMPLETE LIVE EXECUTION SIMULATION SUCCESSFUL",
                "execution_log": execution_log,
                "summary": {
                    "stocks_selected": len(selected_stocks_data),
                    "options_enhanced": len(enhanced_stocks),
                    "signals_generated": len(signals_generated),
                    "valid_signals": len(valid_signals),
                    "trades_executed": len(successful_executions),
                    "profits_booked": len(profit_bookings),
                    "total_pnl": float(total_pnl),
                    "trading_mode": trading_mode.value,
                },
                "all_phases_completed": len(execution_log) == 7,
                "timestamp": datetime.now().isoformat(),
            }

        finally:
            if db:
                db.close()

    except Exception as e:
        logger.error(f"Error in full live execution test: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "execution_log": execution_log,
            "phases_completed": len(
                [log for log in execution_log if log.get("status") == "COMPLETED"]
            ),
            "timestamp": datetime.now().isoformat(),
        }
