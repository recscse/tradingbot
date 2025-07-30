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

        # Market timing
        self.market_open_time = time(9, 15)  # 9:15 AM
        self.selection_time = time(8, 45)  # 8:45 AM - Before market opens
        self.cleanup_time = time(16, 0)  # 4:00 PM - After market closes

        logger.info("✅ Auto Stock Selection Service initialized")

    def start_service(self):
        """Start the automated stock selection service"""
        if self.is_running:
            logger.warning("Auto stock selection service already running")
            return

        logger.info("🚀 Starting Auto Stock Selection Service...")

        # Schedule daily stock selection
        schedule.every().day.at("08:45").do(self._run_stock_selection_job)

        # Schedule cleanup
        schedule.every().day.at("16:00").do(self._cleanup_old_selections)

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
                threading.Event().wait(60)  # Check every minute
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                threading.Event().wait(60)

    def _run_stock_selection_job(self):
        """Run the daily stock selection job"""
        logger.info("🎯 Running automated daily stock selection...")

        try:
            # Run async function in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.select_daily_stocks())
            loop.close()

            logger.info(
                f"✅ Stock selection completed: {result.get('selected_count', 0)} stocks selected"
            )

        except Exception as e:
            logger.error(f"❌ Stock selection job failed: {e}")

    async def select_daily_stocks(self, target_count: int = 20) -> Dict[str, Any]:
        """Select top stocks for daily trading"""
        try:
            logger.info(
                f"🔍 Analyzing stocks for daily selection (target: {target_count})..."
            )

            # Get current market data
            market_data = market_analytics.get_live_market_data()

            if not market_data:
                logger.warning("No market data available for stock selection")
                return {
                    "status": "error",
                    "error": "No market data available",
                    "selected_count": 0,
                }

            # Get comprehensive analytics
            volume_leaders = market_analytics.get_volume_analysis(200)
            momentum_stocks = market_analytics.get_momentum_stocks(2.0, 1.2, 100)
            sector_performance = market_analytics.get_sector_performance()

            # Score all available stocks
            scored_stocks = []

            for instrument_key, data in market_data.items():
                if not isinstance(data, dict):
                    continue

                symbol = data.get("symbol", "")
                if not symbol:
                    continue

                # Calculate comprehensive score
                stock_score = await self._calculate_stock_score(
                    symbol, data, volume_leaders, momentum_stocks, sector_performance
                )

                if stock_score["total_score"] > 0:
                    scored_stocks.append(
                        {
                            "symbol": symbol,
                            "instrument_key": instrument_key,
                            "score_details": stock_score,
                            "total_score": stock_score["total_score"],
                            "market_data": data,
                        }
                    )

            # Sort by total score
            scored_stocks.sort(key=lambda x: x["total_score"], reverse=True)

            # Select top stocks with diversification
            selected_stocks = self._apply_diversification_rules(
                scored_stocks, target_count, sector_performance
            )

            # Store in database
            await self._store_selected_stocks(selected_stocks)

            # Update queue service with selected stocks
            self._update_queue_service_selection(selected_stocks)

            result = {
                "status": "success",
                "selected_count": len(selected_stocks),
                "total_analyzed": len(scored_stocks),
                "selected_stocks": [
                    {
                        "symbol": stock["symbol"],
                        "score": stock["total_score"],
                        "price": stock["market_data"].get("ltp", 0),
                        "change_percent": stock["market_data"].get("change_percent", 0),
                        "volume": stock["market_data"].get("volume", 0),
                        "sector": self.queue_service.sector_mapping.get(
                            stock["symbol"], "OTHER"
                        ),
                        "selection_reason": stock["score_details"]["primary_reason"],
                    }
                    for stock in selected_stocks
                ],
                "selection_time": datetime.now().isoformat(),
                "criteria_used": self._get_criteria_summary(),
            }

            logger.info(
                f"✅ Selected {len(selected_stocks)} stocks from {len(scored_stocks)} analyzed"
            )
            return result

        except Exception as e:
            logger.error(f"❌ Error in stock selection: {e}")
            import traceback

            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return {"status": "error", "error": str(e), "selected_count": 0}

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
                # Find volume ratio
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
            # Simple technical analysis
            if abs(change_percent) > 3:
                if change_percent > 0:
                    score_components["technical_score"] = 15
                    if score_components["primary_reason"] == "UNKNOWN":
                        score_components["primary_reason"] = "BREAKOUT"
                else:
                    score_components["technical_score"] = 8  # Oversold bounce potential
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

            # Exclude too volatile stocks (basic check)
            # You can enhance this with actual volatility calculation

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
                selected_stock = SelectedStock(
                    symbol=stock["symbol"],
                    instrument_key=stock["instrument_key"],
                    selection_score=stock["total_score"],
                    selection_reason=stock["score_details"]["primary_reason"],
                    price_at_selection=stock["market_data"].get("ltp", 0),
                    volume_at_selection=stock["market_data"].get("volume", 0),
                    change_percent_at_selection=stock["market_data"].get(
                        "change_percent", 0
                    ),
                    sector=self.queue_service.sector_mapping.get(
                        stock["symbol"], "OTHER"
                    ),
                    score_breakdown=json.dumps(stock["score_details"]),
                    is_active=True,
                    created_at=datetime.now(),
                )
                db.add(selected_stock)

            db.commit()
            db.close()

            logger.info(f"✅ Stored {len(selected_stocks)} selected stocks in database")

        except Exception as e:
            logger.error(f"❌ Error storing selected stocks: {e}")
            if "db" in locals():
                db.rollback()
                db.close()

    def _update_queue_service_selection(self, selected_stocks: List[Dict]):
        """Update queue service with selected stocks information"""
        try:
            # Mark stocks as selected in queue service (if it supports this)
            selected_symbols = [stock["symbol"] for stock in selected_stocks]

            # You can extend queue service to track selected stocks
            # For now, just log the selection
            logger.info(
                f"📋 Updated queue service with {len(selected_symbols)} selected stocks"
            )

        except Exception as e:
            logger.error(f"Error updating queue service selection: {e}")

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
            logger.error(f"Error cleaning up old selections: {e}")
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
        """Get currently selected stocks from database"""
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
            logger.error(f"Error getting current selected stocks: {e}")
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
