# services/auto_stock_selection_service.py
import asyncio
import logging
import json
from datetime import datetime, time, timedelta
from typing import List, Dict, Any, Optional
import schedule
import threading
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import text

from database.connection import get_db
from database.models import SelectedStock, User, BrokerConfig
from services.market_data_queue import get_market_queue_service
from services.market_analytics_service import market_analytics

logger = logging.getLogger(__name__)


class StockSelectionCriteria:
    """Criteria for stock selection"""

    def __init__(self):
        self.min_price = 50.0  # Minimum stock price
        self.max_price = 5000.0  # Maximum stock price
        self.min_volume = 100000  # Minimum daily volume
        self.min_market_cap = 5000  # Minimum market cap in crores
        self.max_volatility = 15.0  # Maximum volatility percentage
        self.min_liquidity_score = 5.0  # Minimum liquidity score
        self.exclude_sectors = ["PENNY_STOCKS", "DELISTED"]  # Sectors to exclude
        self.preferred_exchanges = ["NSE", "BSE"]  # Preferred exchanges


class AutoStockSelectionService:
    """Automated stock selection service for daily trading"""

    def __init__(self):
        self.queue_service = get_market_queue_service()
        self.criteria = StockSelectionCriteria()
        self.is_running = False
        self.scheduler_thread = None
        self.selected_stocks = []

        # Morning scanning passes buffer (holds each pass results)
        self._morning_candidates: List[Dict[str, Any]] = []

        # Market timing
        # We'll run 3 passes at 09:15, 09:20, 09:25 and finalize at 09:30
        self.morning_pass_times = ["09:15", "09:20", "09:25"]
        self.morning_finalize_time = "09:30"
        self.cleanup_time = "16:00"  # EOD cleanup

        logger.info("✅ Auto Stock Selection Service initialized")

    def start_service(self):
        """Start the automated stock selection service"""
        if self.is_running:
            logger.warning("Auto stock selection service already running")
            return

        logger.info("🚀 Starting Auto Stock Selection Service...")

        # Schedule morning scanning passes
        for t in self.morning_pass_times:
            schedule.every().day.at(t).do(self._morning_scan_job)

        # Schedule finalization of morning picks
        schedule.every().day.at(self.morning_finalize_time).do(
            self._morning_finalize_job
        )

        # Schedule cleanup
        schedule.every().day.at(self.cleanup_time).do(self._cleanup_old_selections)

        # Start scheduler thread
        self.is_running = True
        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop, daemon=True
        )
        self.scheduler_thread.start()

        logger.info("✅ Auto Stock Selection Service started")

    def stop_service(self):
        """Stop the service"""
        self.is_running = False
        schedule.clear()
        logger.info("🛑 Auto Stock Selection Service stopped")

    def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.is_running:
            try:
                schedule.run_pending()
                threading.Event().wait(10)  # Check every 10 seconds
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                threading.Event().wait(60)

    def _morning_scan_job(self):
        """Run one morning scan pass (09:15 / 09:20 / 09:25)"""
        logger.info("🎯 Morning scan pass starting at %s", datetime.now().isoformat())
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            candidates = loop.run_until_complete(self._scan_candidates())
            loop.close()

            # append pass results with timestamp
            self._morning_candidates.append(
                {"ts": datetime.utcnow(), "candidates": candidates}
            )
            logger.info(
                "✅ Morning scan pass complete, candidates collected: %d",
                len(candidates),
            )

        except Exception as e:
            logger.exception("❌ Morning scan pass failed: %s", e)

    def _morning_finalize_job(self):
        """Called at 09:30 to combine passes and finalize picks"""
        logger.info("🔔 Finalizing morning picks at %s", datetime.now().isoformat())
        try:
            # Combine candidates across passes and aggregate scores
            aggregated = {}
            total_passes = len(self._morning_candidates) or 1
            for entry in self._morning_candidates:
                for c in entry["candidates"]:
                    sym = c["symbol"]
                    if sym not in aggregated:
                        aggregated[sym] = {
                            "symbol": sym,
                            "instrument_key": c.get("instrument_key"),
                            "latest_market_data": c.get("market_data", {}),
                            "scores": [],
                            "score_details_latest": c.get("score_details", {}),
                            "bias_votes": [],
                        }
                    aggregated[sym]["scores"].append(float(c.get("total_score", 0)))
                    aggregated[sym]["score_details_latest"] = c.get("score_details", {})
                    # track bias votes (if candidate had bias)
                    if c.get("bias"):
                        aggregated[sym]["bias_votes"].append(c.get("bias"))

            # create aggregated list using average score and bias majority
            combined = []
            for sym, info in aggregated.items():
                avg_score = float(np.mean(info["scores"])) if info["scores"] else 0.0
                # determine bias by majority vote across passes (if any)
                bias = None
                if info["bias_votes"]:
                    # bias values expected 'GREEN'/'RED' or 'UP'/'DOWN' depending on pass impl
                    # we will pick the most common string
                    bias = max(set(info["bias_votes"]), key=info["bias_votes"].count)
                combined.append(
                    {
                        "symbol": sym,
                        "instrument_key": info.get("instrument_key"),
                        "total_score": avg_score,
                        "score_details": info.get("score_details_latest", {}),
                        "market_data": info.get("latest_market_data", {}),
                        "bias": bias,
                    }
                )

            # Sort combined list and pick top N
            target_count = 4  # pick 3-4 stocks by default; configurable
            combined.sort(key=lambda x: x["total_score"], reverse=True)

            # get sector performance snapshot for diversification decisions
            sector_performance = market_analytics.get_sector_performance()

            # apply diversification rules
            final_picks = self._apply_diversification_rules(
                combined, target_count, sector_performance
            )

            # persist final picks
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._store_selected_stocks(final_picks))
            loop.close()

            # push final picks to downstream queue (strategy/execution)
            self._dispatch_to_downstream(final_picks)

            # clear morning buffer
            self._morning_candidates = []

            logger.info("✅ Finalized morning picks: %d", len(final_picks))

        except Exception as e:
            logger.exception("❌ Error finalizing morning picks: %s", e)
            # clear buffer to avoid stale accumulation
            self._morning_candidates = []

    async def select_daily_stocks(self, target_count: int = 20) -> Dict[str, Any]:
        """Backward-compatible full selection run (manual trigger). Persists results immediately."""
        try:
            logger.info(f"🔍 Running full selection (manual) target: {target_count}...")
            # Reuse the scanning pipeline but persist the immediate result
            candidates = await self._scan_candidates(target_count=target_count)
            sector_performance = market_analytics.get_sector_performance()
            picks = self._apply_diversification_rules(
                candidates, target_count, sector_performance
            )
            await self._store_selected_stocks(picks)
            self._dispatch_to_downstream(picks)
            return {
                "status": "success",
                "selected_count": len(picks),
                "selected_stocks": picks,
                "selection_time": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.exception("Error in select_daily_stocks: %s", e)
            return {"status": "error", "error": str(e), "selected_count": 0}

    async def _scan_candidates(self, target_count: int = 100) -> List[Dict[str, Any]]:
        """
        Single pass scanner: returns a list of candidate dicts (DOES NOT persist).
        This method is the lightweight scanner used by morning passes.
        """
        try:
            market_data = market_analytics.get_live_market_data()
            if not market_data:
                logger.warning("No market data available for scanning")
                return []

            volume_leaders = market_analytics.get_volume_analysis(200)
            momentum_stocks = market_analytics.get_momentum_stocks(2.0, 1.2, 100)
            sector_performance = market_analytics.get_sector_performance()

            # compute market bias from F&O universe
            market_bias = self._compute_market_bias(market_data)
            logger.info("Market bias for pass: %s", market_bias)

            scored_stocks = []
            for instrument_key, data in market_data.items():
                if not isinstance(data, dict):
                    continue
                symbol = data.get("symbol", "")
                if not symbol:
                    continue

                stock_score = await self._calculate_stock_score(
                    symbol, data, volume_leaders, momentum_stocks, sector_performance
                )

                # if score > 0 include candidate; attach bias alignment score
                if stock_score["total_score"] > 0:
                    # attach pass bias info: prefer symbols aligned with market bias
                    # simple alignment: if market_bias == GREEN and change_percent>0 -> aligned
                    cp = data.get("change_percent", 0)
                    aligned = None
                    if market_bias == "GREEN" and cp > 0:
                        aligned = "UP"
                    elif market_bias == "RED" and cp < 0:
                        aligned = "DOWN"
                    else:
                        aligned = "NEUTRAL"

                    scored_stocks.append(
                        {
                            "symbol": symbol,
                            "instrument_key": instrument_key,
                            "score_details": stock_score,
                            "total_score": stock_score["total_score"],
                            "market_data": data,
                            "bias": aligned,  # UP/DOWN/NEUTRAL
                        }
                    )

            # sort and return top target_count candidates
            scored_stocks.sort(key=lambda x: x["total_score"], reverse=True)
            return scored_stocks[:target_count]

        except Exception as e:
            logger.exception("Error in _scan_candidates: %s", e)
            return []

    def _compute_market_bias(self, market_data: Dict[str, Any]) -> str:
        """
        Determine market bias (GREEN/RED/MIXED) based on fraction of F&O symbols with positive change.
        """
        try:
            total = 0
            pos = 0
            neg = 0
            for k, d in market_data.items():
                if not isinstance(d, dict):
                    continue
                cp = d.get("change_percent")
                if cp is None:
                    continue
                total += 1
                if cp > 0:
                    pos += 1
                elif cp < 0:
                    neg += 1

            if total == 0:
                return "MIXED"

            pct_pos = pos / total
            if pct_pos >= 0.55:
                return "GREEN"
            elif pct_pos <= 0.45:
                return "RED"
            else:
                return "MIXED"

        except Exception as e:
            logger.exception("Error computing market bias: %s", e)
            return "MIXED"

    async def _calculate_stock_score(
        self,
        symbol: str,
        data: Dict[str, Any],
        volume_leaders: Dict,
        momentum_stocks: Dict,
        sector_performance: Dict,
    ) -> Dict[str, Any]:
        """Calculate comprehensive score for a stock"""
        try:
            score_components = {
                "price_score": 0,
                "volume_score": 0,
                "momentum_score": 0,
                "sector_score": 0,
                "technical_score": 0,
                "liquidity_score": 0,
                "risk_score": 0,
                "total_score": 0,
                "primary_reason": "UNKNOWN",
            }

            # Extract basic data
            price = data.get("ltp", 0)
            volume = data.get("volume", 0)
            change_percent = data.get("change_percent", 0)
            sector = self.queue_service.sector_mapping.get(symbol, "OTHER")

            # Apply basic filters first
            if not self._passes_basic_filters(symbol, price, volume, sector):
                return score_components

            # 1. Price Score (15 points max)
            if self.criteria.min_price <= price <= self.criteria.max_price:
                if 100 <= price <= 2000:  # Sweet spot
                    score_components["price_score"] = 15
                elif 50 <= price <= 100 or 2000 <= price <= 3000:
                    score_components["price_score"] = 10
                else:
                    score_components["price_score"] = 5

            # 2. Volume Score (20 points max)
            volume_leaders_list = volume_leaders.get("volume_leaders", [])
            volume_leader_symbols = [v.get("symbol") for v in volume_leaders_list]

            if symbol in volume_leader_symbols:
                vol_data = next(
                    (v for v in volume_leaders_list if v.get("symbol") == symbol), None
                )
                if vol_data:
                    volume_ratio = vol_data.get("volume_ratio", 1)
                    if volume_ratio > 3:
                        score_components["volume_score"] = 20
                    elif volume_ratio > 2:
                        score_components["volume_score"] = 15
                    elif volume_ratio > 1.5:
                        score_components["volume_score"] = 10
                    else:
                        score_components["volume_score"] = 5
            elif volume > self.criteria.min_volume:
                score_components["volume_score"] = 5

            # 3. Momentum Score (25 points max)
            momentum_stocks_list = momentum_stocks.get("momentum_stocks", [])
            momentum_symbols = [m.get("symbol") for m in momentum_stocks_list]

            if symbol in momentum_symbols:
                mom_data = next(
                    (m for m in momentum_stocks_list if m.get("symbol") == symbol), None
                )
                if mom_data:
                    momentum_score_val = mom_data.get("momentum_score", 0)
                    if momentum_score_val > 15:
                        score_components["momentum_score"] = 25
                        score_components["primary_reason"] = "HIGH_MOMENTUM"
                    elif momentum_score_val > 10:
                        score_components["momentum_score"] = 20
                        score_components["primary_reason"] = "MEDIUM_MOMENTUM"
                    elif momentum_score_val > 5:
                        score_components["momentum_score"] = 15
                    else:
                        score_components["momentum_score"] = 10
            elif abs(change_percent) > 2:
                score_components["momentum_score"] = 10

            # 4. Sector Score (15 points max)
            sectors_data = sector_performance.get("sectors", {})
            if sector in sectors_data:
                sector_data = sectors_data[sector]
                sector_avg_change = sector_data.get("avg_change", 0)

                if sector_avg_change > 2:
                    score_components["sector_score"] = 15
                elif sector_avg_change > 1:
                    score_components["sector_score"] = 10
                elif sector_avg_change > 0:
                    score_components["sector_score"] = 5
                else:
                    score_components["sector_score"] = 2
            else:
                score_components["sector_score"] = 5  # Default for unknown sector

            # 5. Technical Score (15 points max)
            if abs(change_percent) > 3:
                if change_percent > 0:
                    score_components["technical_score"] = 15
                    if score_components["primary_reason"] == "UNKNOWN":
                        score_components["primary_reason"] = "BREAKOUT"
                else:
                    score_components["technical_score"] = 8
                    if score_components["primary_reason"] == "UNKNOWN":
                        score_components["primary_reason"] = "OVERSOLD_BOUNCE"
            elif abs(change_percent) > 1:
                score_components["technical_score"] = 10
            else:
                score_components["technical_score"] = 5

            # 6. Liquidity Score (10 points max)
            if volume > 1000000:  # 10 lakh+ volume
                score_components["liquidity_score"] = 10
            elif volume > 500000:  # 5 lakh+ volume
                score_components["liquidity_score"] = 8
            elif volume > 200000:  # 2 lakh+ volume
                score_components["liquidity_score"] = 6
            elif volume > 100000:  # 1 lakh+ volume
                score_components["liquidity_score"] = 4
            else:
                score_components["liquidity_score"] = 2

            # Calculate total score
            score_components["total_score"] = (
                score_components["price_score"]
                + score_components["volume_score"]
                + score_components["momentum_score"]
                + score_components["sector_score"]
                + score_components["technical_score"]
                + score_components["liquidity_score"]
            )

            # Set primary reason if still unknown
            if score_components["primary_reason"] == "UNKNOWN":
                if score_components["volume_score"] > 15:
                    score_components["primary_reason"] = "HIGH_VOLUME"
                elif score_components["sector_score"] > 10:
                    score_components["primary_reason"] = "SECTOR_STRENGTH"
                elif score_components["technical_score"] > 10:
                    score_components["primary_reason"] = "TECHNICAL_SETUP"
                else:
                    score_components["primary_reason"] = "BALANCED_SCORE"

            return score_components

        except Exception as e:
            logger.error(f"Error calculating score for {symbol}: {e}")
            return score_components

    def _passes_basic_filters(
        self, symbol: str, price: float, volume: int, sector: str
    ) -> bool:
        """Check if stock passes basic filters"""
        try:
            # Price filter
            if not (self.criteria.min_price <= price <= self.criteria.max_price):
                return False

            # Volume filter
            if volume < self.criteria.min_volume:
                return False

            # Sector filter
            if sector in self.criteria.exclude_sectors:
                return False

            # Exclude penny stocks
            if price < 10:
                return False

            return True

        except Exception as e:
            logger.error(f"Error in basic filters for {symbol}: {e}")
            return False

    def _apply_diversification_rules(
        self, scored_stocks: List[Dict], target_count: int, sector_performance: Dict
    ) -> List[Dict]:
        """Apply diversification rules to stock selection"""
        try:
            selected = []
            sector_counts = {}
            max_per_sector = max(2, target_count // 8)  # Max 2-3 stocks per sector

            # First pass: Select top stocks with sector limits
            for stock in scored_stocks:
                if len(selected) >= target_count:
                    break

                symbol = stock["symbol"]
                sector = self.queue_service.sector_mapping.get(symbol, "OTHER")

                # Check sector limit
                if sector_counts.get(sector, 0) >= max_per_sector:
                    continue

                # Add to selection
                selected.append(stock)
                sector_counts[sector] = sector_counts.get(sector, 0) + 1

            # Second pass: Fill remaining slots if needed
            if len(selected) < target_count:
                remaining_slots = target_count - len(selected)
                selected_symbols = {s["symbol"] for s in selected}

                for stock in scored_stocks:
                    if len(selected) >= target_count:
                        break

                    if stock["symbol"] not in selected_symbols:
                        selected.append(stock)

            logger.info(
                f"Applied diversification: {len(selected)} stocks across {len(sector_counts)} sectors"
            )
            logger.info(f"Sector distribution: {sector_counts}")

            return selected[:target_count]

        except Exception as e:
            logger.error(f"Error applying diversification: {e}")
            return scored_stocks[:target_count]

    async def _store_selected_stocks(self, selected_stocks: List[Dict]):
        """Store selected stocks in database"""
        try:
            db = next(get_db())

            # Clear previous selections for today
            today = datetime.now().date()
            db.execute(
                text("DELETE FROM selected_stocks WHERE DATE(created_at) = :today"),
                {"today": today},
            )

            # Store new selections
            for stock in selected_stocks:
                # include bias in the JSON breakdown so you don't need to alter schema
                score_breakdown = stock.get("score_details", {})
                score_breakdown["bias"] = stock.get("bias")

                selected_stock = SelectedStock(
                    symbol=stock["symbol"],
                    instrument_key=stock.get("instrument_key") or "",
                    selection_score=stock["total_score"],
                    selection_reason=stock["score_details"].get(
                        "primary_reason", "scanner"
                    ),
                    price_at_selection=stock["market_data"].get("ltp", 0),
                    volume_at_selection=stock["market_data"].get("volume", 0),
                    change_percent_at_selection=stock["market_data"].get(
                        "change_percent", 0
                    ),
                    sector=self.queue_service.sector_mapping.get(
                        stock["symbol"], "OTHER"
                    ),
                    score_breakdown=json.dumps(score_breakdown),
                    is_active=True,
                    created_at=datetime.now(),
                )
                db.add(selected_stock)

            db.commit()
            db.close()

            logger.info(f"✅ Stored {len(selected_stocks)} selected stocks in database")

        except Exception as e:
            logger.exception(f"❌ Error storing selected stocks: {e}")
            if "db" in locals():
                db.rollback()
                db.close()

    def _dispatch_to_downstream(self, selected_stocks: List[Dict[str, Any]]):
        """
        Dispatch final picks to downstream processing (strategy/execution).
        Prefer queue service enqueue if available; else log and leave for manual processing.
        """
        try:
            if hasattr(self.queue_service, "enqueue_selected_stock"):
                for stock in selected_stocks:
                    try:
                        payload = {
                            "symbol": stock["symbol"],
                            "instrument_key": stock.get("instrument_key"),
                            "bias": stock.get("bias"),
                            "score": stock.get("total_score"),
                            "market_data": stock.get("market_data"),
                            "score_details": stock.get("score_details"),
                            "selected_at": datetime.utcnow().isoformat(),
                        }
                        # enqueue in downstream queue for strategy processing
                        self.queue_service.enqueue_selected_stock(payload)
                    except Exception:
                        logger.exception(
                            "Failed to enqueue stock to queue_service for %s",
                            stock["symbol"],
                        )
            else:
                # As a fallback, emit log and leave selection for manual or API pickup
                for stock in selected_stocks:
                    logger.info(
                        "Selected: %s bias=%s score=%s",
                        stock["symbol"],
                        stock.get("bias"),
                        stock["total_score"],
                    )

        except Exception as e:
            logger.exception("Error dispatching to downstream: %s", e)

    def _cleanup_old_selections(self):
        """Cleanup old stock selections"""
        try:
            db = next(get_db())

            # Mark old selections as inactive
            cutoff_date = datetime.now() - timedelta(days=7)
            db.execute(
                text(
                    "UPDATE selected_stocks SET is_active = FALSE WHERE created_at < :cutoff"
                ),
                {"cutoff": cutoff_date},
            )

            db.commit()
            db.close()

            logger.info("🧹 Cleaned up old stock selections")

        except Exception as e:
            logger.exception(f"Error cleaning up old selections: {e}")
            if "db" in locals():
                db.rollback()
                db.close()

    def _get_criteria_summary(self) -> Dict[str, Any]:
        """Get summary of selection criteria"""
        return {
            "min_price": self.criteria.min_price,
            "max_price": self.criteria.max_price,
            "min_volume": self.criteria.min_volume,
            "min_market_cap": self.criteria.min_market_cap,
            "max_volatility": self.criteria.max_volatility,
            "exclude_sectors": self.criteria.exclude_sectors,
            "preferred_exchanges": self.criteria.preferred_exchanges,
            "scoring_weights": {
                "price": 15,
                "volume": 20,
                "momentum": 25,
                "sector": 15,
                "technical": 15,
                "liquidity": 10,
            },
        }

    async def get_current_selected_stocks(self) -> List[Dict[str, Any]]:
        """Get today's selected stocks from database"""
        try:
            db = next(get_db())

            today = datetime.now().date()
            results = db.execute(
                text(
                    """
                    SELECT symbol, instrument_key, selection_score, selection_reason,
                           price_at_selection, volume_at_selection, change_percent_at_selection,
                           sector, score_breakdown, created_at
                    FROM selected_stocks 
                    WHERE DATE(created_at) = :today AND is_active = TRUE
                    ORDER BY selection_score DESC
                """
                ),
                {"today": today},
            ).fetchall()

            db.close()

            selected_stocks = []
            for row in results:
                try:
                    score_breakdown = (
                        json.loads(row.score_breakdown) if row.score_breakdown else {}
                    )
                except:
                    score_breakdown = {}

                selected_stocks.append(
                    {
                        "symbol": row.symbol,
                        "instrument_key": row.instrument_key,
                        "selection_score": float(row.selection_score),
                        "selection_reason": row.selection_reason,
                        "price_at_selection": float(row.price_at_selection),
                        "volume_at_selection": int(row.volume_at_selection),
                        "change_percent_at_selection": float(
                            row.change_percent_at_selection
                        ),
                        "sector": row.sector,
                        "score_breakdown": score_breakdown,
                        "selected_at": row.created_at.isoformat(),
                    }
                )

            return selected_stocks

        except Exception as e:
            logger.exception(f"Error getting current selected stocks: {e}")
            return []

    async def manual_stock_selection(self, target_count: int = 20) -> Dict[str, Any]:
        """Manually trigger stock selection"""
        logger.info(f"🔧 Manual stock selection triggered (target: {target_count})")
        return await self.select_daily_stocks(target_count)


# Global instance
auto_stock_selection_service = AutoStockSelectionService()


# Helper functions
def start_auto_stock_selection():
    """Start the auto stock selection service"""
    auto_stock_selection_service.start_service()


def stop_auto_stock_selection():
    """Stop the auto stock selection service"""
    auto_stock_selection_service.stop_service()


async def get_selected_stocks_for_today() -> List[Dict[str, Any]]:
    """Get today's selected stocks"""
    return await auto_stock_selection_service.get_current_selected_stocks()


async def trigger_manual_selection(count: int = 20) -> Dict[str, Any]:
    """Trigger manual stock selection"""
    return await auto_stock_selection_service.manual_stock_selection(count)
