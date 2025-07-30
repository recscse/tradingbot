from datetime import datetime
import logging
from typing import Any, Dict, List


logger = logging.getLogger(__name__)


class EnhancedMarketAnalyticsService:
    def __init__(self):
        self.cache = {}
        self.last_calculated = {}
        self.cache_ttl = 30  # 30 seconds cache

    def get_complete_analytics(self) -> Dict[str, Any]:
        """COMPLETE: Get all analytics with enriched data"""
        try:
            start_time = datetime.now()

            analytics = {
                "top_movers": self.get_top_gainers_losers(),
                "market_sentiment": self.get_market_sentiment(),
                "sector_heatmap": self.get_sector_heatmap(),
                "volume_analysis": self.get_volume_analysis(),
                "gap_analysis": self.get_gap_analysis(),
                "breakout_analysis": self.get_breakout_analysis(),
                "market_breadth": self.get_market_breadth(),
                "intraday_highlights": self.get_intraday_highlights(),
                "intraday_stocks": self.get_intraday_stocks(),  # Added alias
                "performance_summary": self.get_performance_summary(),
                "record_movers": self.get_record_movers(),  # Added
                "generated_at": datetime.now().isoformat(),
                "processing_time_ms": (datetime.now() - start_time).total_seconds()
                * 1000,
                "cache_status": self._get_cache_status(),
            }

            logger.info(
                f"📊 Complete analytics generated in {analytics['processing_time_ms']:.2f}ms"
            )
            return analytics

        except Exception as e:
            logger.error(f"Error generating complete analytics: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    def get_all_live_stocks(self) -> List[Dict[str, Any]]:
        """COMPLETE: Get enriched stock data"""
        try:
            from services.instrument_registry import instrument_registry

            # Get enriched data directly
            enriched_data = instrument_registry.get_enriched_prices()

            stocks = []
            for instrument_key, data in enriched_data.items():
                if data.get("ltp") and data.get("symbol"):
                    # Data is already enriched with all metadata
                    stock_entry = {
                        "symbol": data["symbol"],
                        "name": data.get("name", data["symbol"]),
                        "sector": data.get("sector", "OTHER"),
                        "instrument_key": instrument_key,
                        "trading_symbol": data.get("trading_symbol", data["symbol"]),
                        "exchange": data.get("exchange", "NSE"),
                        "instrument_type": data.get("instrument_type", "EQ"),
                        # Price data
                        "last_price": data["ltp"],
                        "change": data.get("change", 0),
                        "change_percent": data.get("change_percent", 0),
                        "previous_close": data.get("cp", 0),
                        # OHLC
                        "open": data.get("open", 0),
                        "high": data.get("high", 0),
                        "low": data.get("low", 0),
                        "close": data.get("close", 0),
                        # Volume
                        "volume": data.get("volume", 0),
                        "avg_trade_price": data.get("avg_trade_price"),
                        # Advanced metrics
                        "trend": data.get("trend", "neutral"),
                        "volatility": data.get("volatility", "normal"),
                        "has_derivatives": data.get("has_derivatives", False),
                        # Computed fields
                        "market_cap_category": self._categorize_by_price(data["ltp"]),
                        "volume_category": self._categorize_volume(
                            data.get("volume", 0)
                        ),
                        "performance_category": self._categorize_performance(
                            data.get("change_percent", 0)
                        ),
                        # Metadata
                        "last_updated": data.get("last_updated"),
                        "update_count": data.get("update_count", 0),
                    }

                    # Calculate additional metrics
                    if stock_entry["open"] > 0 and stock_entry["close"] > 0:
                        stock_entry["gap_percent"] = (
                            (stock_entry["open"] - stock_entry["close"])
                            / stock_entry["close"]
                            * 100
                        )

                    stocks.append(stock_entry)

            logger.info(
                f"📊 Retrieved {len(stocks)} enriched stocks with complete metadata"
            )
            return stocks

        except Exception as e:
            logger.error(f"Error getting live stocks: {e}")
            return []

    def get_top_gainers_losers(self, limit: int = 20) -> Dict[str, Any]:
        """COMPLETE: Top movers with enriched data"""
        if not self._should_recalculate("top_movers"):
            return self.cache.get("top_movers", {"gainers": [], "losers": []})

        try:
            from services.instrument_registry import instrument_registry

            # Use optimized registry method if available, otherwise calculate manually
            try:
                movers_data = instrument_registry.get_top_movers(limit)
            except AttributeError:
                # Fallback: calculate manually
                movers_data = self._calculate_top_movers_manually(limit)

            # Add additional analysis
            gainers = movers_data.get("gainers", [])
            losers = movers_data.get("losers", [])

            # Analyze sectors in top movers
            gainer_sectors = {}
            loser_sectors = {}

            for stock in gainers:
                sector = stock.get("sector", "OTHER")
                gainer_sectors[sector] = gainer_sectors.get(sector, 0) + 1

            for stock in losers:
                sector = stock.get("sector", "OTHER")
                loser_sectors[sector] = loser_sectors.get(sector, 0) + 1

            result = {
                "gainers": gainers,
                "losers": losers,
                "analysis": {
                    "avg_gainer_change": (
                        sum(s.get("change_percent", 0) for s in gainers) / len(gainers)
                        if gainers
                        else 0
                    ),
                    "avg_loser_change": (
                        sum(s.get("change_percent", 0) for s in losers) / len(losers)
                        if losers
                        else 0
                    ),
                    "gainer_sectors": gainer_sectors,
                    "loser_sectors": loser_sectors,
                    "total_analyzed": movers_data.get("total_stocks_analyzed", 0),
                },
                "timestamp": datetime.now().isoformat(),
            }

            self.cache["top_movers"] = result
            self._mark_calculated("top_movers")
            return result

        except Exception as e:
            logger.error(f"Error calculating top movers: {e}")
            return {"gainers": [], "losers": [], "error": str(e)}

    def get_sector_heatmap(self) -> Dict[str, Any]:
        """COMPLETE: Sector heatmap with detailed analysis - FIXED VERSION"""
        if not self._should_recalculate("sector_heatmap"):
            return self.cache.get("sector_heatmap", {"sectors": []})

        try:
            from services.instrument_registry import instrument_registry

            # FIXED: Use direct enriched prices instead of registry method
            logger.info("📊 Starting sector heatmap calculation")

            # Get all enriched data directly
            enriched_data = instrument_registry.get_enriched_prices()

            if not enriched_data:
                logger.warning("⚠️ No enriched data available for sector heatmap")
                return {
                    "sectors": [],
                    "summary": {
                        "total_sectors": 0,
                        "bullish_sectors": 0,
                        "bearish_sectors": 0,
                        "neutral_sectors": 0,
                    },
                    "error": "No enriched data available",
                    "timestamp": datetime.now().isoformat(),
                }

            # Group stocks by sector
            sectors_data = {}
            total_stocks_processed = 0

            for instrument_key, stock_data in enriched_data.items():
                try:
                    sector = stock_data.get("sector", "OTHER")
                    if sector not in sectors_data:
                        sectors_data[sector] = {
                            "stocks": [],
                            "total_stocks": 0,
                            "advancing": 0,
                            "declining": 0,
                            "unchanged": 0,
                            "total_volume": 0,
                            "changes": [],
                        }

                    # Add stock to sector
                    sectors_data[sector]["stocks"].append(stock_data)
                    sectors_data[sector]["total_stocks"] += 1
                    sectors_data[sector]["total_volume"] += stock_data.get("volume", 0)

                    # Track change percentage
                    change_pct = stock_data.get("change_percent", 0)
                    if change_pct is not None:
                        sectors_data[sector]["changes"].append(change_pct)

                        if change_pct > 0:
                            sectors_data[sector]["advancing"] += 1
                        elif change_pct < 0:
                            sectors_data[sector]["declining"] += 1
                        else:
                            sectors_data[sector]["unchanged"] += 1

                    total_stocks_processed += 1

                except Exception as e:
                    logger.warning(f"⚠️ Error processing stock for sector heatmap: {e}")
                    continue

            logger.info(
                f"📊 Processed {total_stocks_processed} stocks across {len(sectors_data)} sectors"
            )

            # Build sector analysis
            sectors = []
            for sector_name, data in sectors_data.items():
                if data["total_stocks"] == 0:
                    continue

                # Calculate average change
                changes = data["changes"]
                avg_change = sum(changes) / len(changes) if changes else 0

                # Find top and worst performers
                top_performer = max(
                    data["stocks"], key=lambda x: x.get("change_percent", 0)
                )
                worst_performer = min(
                    data["stocks"], key=lambda x: x.get("change_percent", 0)
                )

                sector_entry = {
                    "sector": sector_name,
                    "stocks_count": data["total_stocks"],
                    "avg_change_percent": round(avg_change, 2),
                    "advancing": data["advancing"],
                    "declining": data["declining"],
                    "unchanged": data["unchanged"],
                    "strength_score": (
                        round(
                            (data["advancing"] - data["declining"])
                            / data["total_stocks"]
                            * 100,
                            2,
                        )
                        if data["total_stocks"] > 0
                        else 0
                    ),
                    "total_volume": data["total_volume"],
                    # Performance categorization
                    "performance_category": self._categorize_sector_performance(
                        avg_change
                    ),
                    "momentum": self._calculate_sector_momentum(
                        {
                            "strength_score": (
                                (data["advancing"] - data["declining"])
                                / data["total_stocks"]
                                * 100
                                if data["total_stocks"] > 0
                                else 0
                            )
                        }
                    ),
                    # Top/worst performers
                    "top_performer": {
                        "symbol": top_performer.get("symbol", "N/A"),
                        "name": top_performer.get("name", "N/A"),
                        "change_percent": top_performer.get("change_percent", 0),
                    },
                    "worst_performer": {
                        "symbol": worst_performer.get("symbol", "N/A"),
                        "name": worst_performer.get("name", "N/A"),
                        "change_percent": worst_performer.get("change_percent", 0),
                    },
                    # Advanced metrics
                    "breadth_ratio": self._calculate_breadth_ratio(data),
                    "participation_rate": self._calculate_participation_rate(data),
                }

                sectors.append(sector_entry)

            # Sort by performance
            sectors.sort(key=lambda x: x["avg_change_percent"], reverse=True)

            # Build summary
            best_performing = sectors[0]["sector"] if sectors else None
            worst_performing = sectors[-1]["sector"] if sectors else None

            result = {
                "sectors": sectors,
                "summary": {
                    "best_performing": best_performing,
                    "worst_performing": worst_performing,
                    "total_sectors": len(sectors),
                    "bullish_sectors": len(
                        [s for s in sectors if s["avg_change_percent"] > 0.5]
                    ),
                    "bearish_sectors": len(
                        [s for s in sectors if s["avg_change_percent"] < -0.5]
                    ),
                    "neutral_sectors": len(
                        [s for s in sectors if -0.5 <= s["avg_change_percent"] <= 0.5]
                    ),
                },
                "timestamp": datetime.now().isoformat(),
                "debug_info": {
                    "total_stocks_processed": total_stocks_processed,
                    "enriched_data_count": len(enriched_data),
                    "sectors_found": list(sectors_data.keys()),
                },
            }

            self.cache["sector_heatmap"] = result
            self._mark_calculated("sector_heatmap")

            logger.info(
                f"✅ Sector heatmap calculated successfully with {len(sectors)} sectors"
            )
            return result

        except Exception as e:
            logger.error(f"❌ Error calculating sector heatmap: {e}")
            import traceback

            logger.error(f"Full traceback: {traceback.format_exc()}")
            return {
                "sectors": [],
                "summary": {
                    "total_sectors": 0,
                    "bullish_sectors": 0,
                    "bearish_sectors": 0,
                    "neutral_sectors": 0,
                },
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def _calculate_participation_rate(self, sector_data: dict) -> float:
        """Calculate participation rate for a sector"""
        advancing = sector_data.get("advancing", 0)
        declining = sector_data.get("declining", 0)
        total_stocks = sector_data.get("total_stocks", 1)

        if total_stocks == 0:
            return 0.0

        return round((advancing + declining) / total_stocks, 3)

    def get_market_sentiment(self) -> Dict[str, Any]:
        """COMPLETE: Market sentiment analysis"""
        if not self._should_recalculate("market_sentiment"):
            return self.cache.get("market_sentiment", {"sentiment": "neutral"})

        try:
            from services.instrument_registry import instrument_registry

            # Get comprehensive market summary
            try:
                market_summary = instrument_registry.get_market_summary()
            except AttributeError:
                # Fallback: calculate manually
                market_summary = self._calculate_market_summary_manually()

            if "error" in market_summary:
                return {"sentiment": "unknown", "error": market_summary["error"]}

            # Calculate sentiment metrics
            breadth_pct = market_summary.get("market_breadth_percent", 0)
            adv_dec_ratio = market_summary.get("advance_decline_ratio", 1)

            # Determine sentiment
            if breadth_pct >= 30:
                sentiment = "very_bullish"
                confidence = min(100, breadth_pct + 30)
            elif breadth_pct >= 10:
                sentiment = "bullish"
                confidence = min(100, breadth_pct + 40)
            elif breadth_pct >= -10:
                sentiment = "neutral"
                confidence = 100 - abs(breadth_pct) * 3
            elif breadth_pct >= -30:
                sentiment = "bearish"
                confidence = min(100, abs(breadth_pct) + 40)
            else:
                sentiment = "very_bearish"
                confidence = min(100, abs(breadth_pct) + 30)

            # Volume analysis
            volume_stats = market_summary.get("volume_stats", {})
            high_volume_participation = volume_stats.get("high_volume_stocks", 0)

            # Sector analysis
            sector_performance = market_summary.get("sector_performance", {})
            bullish_sectors = len(
                [
                    s
                    for s in sector_performance.values()
                    if s.get("avg_change_percent", 0) > 1
                ]
            )
            bearish_sectors = len(
                [
                    s
                    for s in sector_performance.values()
                    if s.get("avg_change_percent", 0) < -1
                ]
            )

            result = {
                "sentiment": sentiment,
                "confidence": round(confidence, 1),
                "sentiment_score": breadth_pct,
                "market_breadth": {
                    "total_stocks": market_summary.get("total_stocks", 0),
                    "advancing": market_summary.get("advancing", 0),
                    "declining": market_summary.get("declining", 0),
                    "unchanged": market_summary.get("unchanged", 0),
                    "advance_decline_ratio": adv_dec_ratio,
                    "breadth_percentage": breadth_pct,
                },
                "volume_analysis": {
                    "total_volume": volume_stats.get("total_volume", 0),
                    "average_volume": volume_stats.get("average_volume", 0),
                    "high_volume_stocks": high_volume_participation,
                    "volume_trend": (
                        "high" if high_volume_participation > 50 else "normal"
                    ),
                },
                "sector_sentiment": {
                    "bullish_sectors": bullish_sectors,
                    "bearish_sectors": bearish_sectors,
                    "total_sectors": len(sector_performance),
                    "sector_breadth": (
                        (bullish_sectors - bearish_sectors) / len(sector_performance)
                        if sector_performance
                        else 0
                    ),
                },
                "market_indicators": market_summary.get("market_indicators", {}),
                "interpretation": self._interpret_sentiment(
                    sentiment, confidence, breadth_pct
                ),
                "timestamp": datetime.now().isoformat(),
            }

            self.cache["market_sentiment"] = result
            self._mark_calculated("market_sentiment")
            return result

        except Exception as e:
            logger.error(f"Error calculating market sentiment: {e}")
            return {"sentiment": "unknown", "error": str(e)}

    def get_volume_analysis(self) -> Dict[str, Any]:
        """COMPLETE: Volume analysis with enriched data"""
        if not self._should_recalculate("volume_analysis"):
            return self.cache.get("volume_analysis", {"volume_leaders": []})

        try:
            from services.instrument_registry import instrument_registry

            # Get volume leaders
            try:
                volume_leaders = instrument_registry.get_volume_leaders(20)
            except AttributeError:
                # Fallback: calculate manually
                volume_leaders = self._calculate_volume_leaders_manually(20)

            # Analyze volume patterns
            try:
                all_stocks = list(instrument_registry.get_enriched_prices().values())
            except AttributeError:
                all_stocks = []

            volumes = [s.get("volume", 0) for s in all_stocks if s.get("volume", 0) > 0]

            if not volumes:
                return {"volume_leaders": [], "error": "No volume data available"}

            # Calculate volume statistics
            total_volume = sum(volumes)
            avg_volume = total_volume / len(volumes)
            max_volume = max(volumes)

            # Categorize by volume
            high_volume_threshold = avg_volume * 3
            unusual_volume_stocks = [
                s for s in all_stocks if s.get("volume", 0) > high_volume_threshold
            ]

            # Sector volume analysis
            sector_volumes = {}
            try:
                sector_data = instrument_registry.get_stocks_by_sector()
            except AttributeError:
                sector_data = {}

            for sector, stocks in sector_data.items():
                sector_volume = sum(s.get("volume", 0) for s in stocks)
                if sector_volume > 0:
                    sector_volumes[sector] = {
                        "total_volume": sector_volume,
                        "avg_volume": sector_volume / len(stocks),
                        "stock_count": len(stocks),
                        "high_volume_stocks": len(
                            [
                                s
                                for s in stocks
                                if s.get("volume", 0) > high_volume_threshold
                            ]
                        ),
                    }

            result = {
                "volume_leaders": volume_leaders[:15],
                "unusual_volume": unusual_volume_stocks[:10],
                "volume_statistics": {
                    "total_market_volume": total_volume,
                    "average_volume": round(avg_volume, 0),
                    "max_volume": max_volume,
                    "high_volume_threshold": round(high_volume_threshold, 0),
                    "stocks_with_volume": len(volumes),
                    "high_volume_stocks": len(unusual_volume_stocks),
                },
                "sector_volumes": dict(
                    sorted(
                        sector_volumes.items(),
                        key=lambda x: x[1]["total_volume"],
                        reverse=True,
                    )
                ),
                "volume_insights": {
                    "market_participation": (
                        "high" if len(unusual_volume_stocks) > 100 else "normal"
                    ),
                    "volume_concentration": (
                        round(
                            sum(s.get("volume", 0) for s in volume_leaders[:10])
                            / total_volume
                            * 100,
                            1,
                        )
                        if total_volume > 0
                        else 0
                    ),
                    "breadth_indicator": (
                        len([s for s in all_stocks if s.get("volume", 0) > avg_volume])
                        / len(all_stocks)
                        if all_stocks
                        else 0
                    ),
                },
                "timestamp": datetime.now().isoformat(),
            }

            self.cache["volume_analysis"] = result
            self._mark_calculated("volume_analysis")
            return result

        except Exception as e:
            logger.error(f"Error calculating volume analysis: {e}")
            return {"volume_leaders": [], "error": str(e)}

    # MISSING METHODS - ADD THESE:

    def get_gap_analysis(self) -> Dict[str, Any]:
        """Gap analysis for stocks"""
        if not self._should_recalculate("gap_analysis"):
            return self.cache.get("gap_analysis", {"gap_up": [], "gap_down": []})

        try:
            stocks = self.get_all_live_stocks()
            gap_up = []
            gap_down = []

            for stock in stocks:
                gap_percent = stock.get("gap_percent", 0)
                if gap_percent > 2:  # Gap up > 2%
                    gap_up.append(stock)
                elif gap_percent < -2:  # Gap down < -2%
                    gap_down.append(stock)

            # Sort by gap percentage
            gap_up.sort(key=lambda x: x.get("gap_percent", 0), reverse=True)
            gap_down.sort(key=lambda x: x.get("gap_percent", 0))

            result = {
                "gap_up": gap_up[:20],
                "gap_down": gap_down[:20],
                "summary": {
                    "total_gap_up": len(gap_up),
                    "total_gap_down": len(gap_down),
                    "avg_gap_up": (
                        sum(s.get("gap_percent", 0) for s in gap_up) / len(gap_up)
                        if gap_up
                        else 0
                    ),
                    "avg_gap_down": (
                        sum(s.get("gap_percent", 0) for s in gap_down) / len(gap_down)
                        if gap_down
                        else 0
                    ),
                },
                "timestamp": datetime.now().isoformat(),
            }

            self.cache["gap_analysis"] = result
            self._mark_calculated("gap_analysis")
            return result

        except Exception as e:
            logger.error(f"Error calculating gap analysis: {e}")
            return {"gap_up": [], "gap_down": [], "error": str(e)}

    def get_breakout_analysis(self) -> Dict[str, Any]:
        """Breakout analysis for stocks"""
        if not self._should_recalculate("breakout_analysis"):
            return self.cache.get(
                "breakout_analysis", {"breakouts": [], "breakdowns": []}
            )

        try:
            stocks = self.get_all_live_stocks()
            breakouts = []
            breakdowns = []

            for stock in stocks:
                # Simple breakout logic: price at/near high with good volume
                high = stock.get("high", 0)
                ltp = stock.get("last_price", 0)
                volume = stock.get("volume", 0)
                avg_volume = 100000  # Placeholder

                if high > 0 and ltp > 0:
                    near_high_pct = (ltp / high) * 100

                    if (
                        near_high_pct >= 98 and volume > avg_volume * 1.5
                    ):  # Near high with volume
                        breakouts.append(stock)
                    elif (
                        near_high_pct <= 60 and volume > avg_volume * 1.5
                    ):  # Near low with volume
                        breakdowns.append(stock)

            # Sort by performance
            breakouts.sort(key=lambda x: x.get("change_percent", 0), reverse=True)
            breakdowns.sort(key=lambda x: x.get("change_percent", 0))

            result = {
                "breakouts": breakouts[:20],
                "breakdowns": breakdowns[:20],
                "summary": {
                    "total_breakouts": len(breakouts),
                    "total_breakdowns": len(breakdowns),
                },
                "timestamp": datetime.now().isoformat(),
            }

            self.cache["breakout_analysis"] = result
            self._mark_calculated("breakout_analysis")
            return result

        except Exception as e:
            logger.error(f"Error calculating breakout analysis: {e}")
            return {"breakouts": [], "breakdowns": [], "error": str(e)}

    def get_market_breadth(self) -> Dict[str, Any]:
        """Market breadth analysis"""
        try:
            stocks = self.get_all_live_stocks()

            advancing = len([s for s in stocks if s.get("change_percent", 0) > 0])
            declining = len([s for s in stocks if s.get("change_percent", 0) < 0])
            unchanged = len(stocks) - advancing - declining

            return {
                "total_stocks": len(stocks),
                "advancing": advancing,
                "declining": declining,
                "unchanged": unchanged,
                "advance_decline_ratio": (
                    advancing / declining if declining > 0 else float("inf")
                ),
                "breadth_percentage": (
                    ((advancing - declining) / len(stocks)) * 100 if stocks else 0
                ),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error calculating market breadth: {e}")
            return {"error": str(e)}

    def get_intraday_highlights(self) -> Dict[str, Any]:
        """Intraday highlights and opportunities"""
        return self.get_intraday_stocks()

    def get_intraday_stocks(self) -> Dict[str, Any]:
        """Intraday stock opportunities"""
        try:
            stocks = self.get_all_live_stocks()

            # Filter for high momentum and high volume stocks
            high_momentum = [s for s in stocks if abs(s.get("change_percent", 0)) > 3]
            high_volume = [s for s in stocks if s.get("volume", 0) > 1000000]

            # Combine and deduplicate
            all_candidates = []
            seen = set()

            for stock in high_momentum + high_volume:
                symbol = stock.get("symbol")
                if symbol not in seen:
                    all_candidates.append(stock)
                    seen.add(symbol)

            return {
                "high_momentum": high_momentum[:15],
                "high_volume": high_volume[:15],
                "all_candidates": all_candidates[:25],
                "summary": {
                    "total_high_momentum": len(high_momentum),
                    "total_high_volume": len(high_volume),
                    "total_candidates": len(all_candidates),
                },
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error calculating intraday stocks: {e}")
            return {"all_candidates": [], "error": str(e)}

    def get_performance_summary(self) -> Dict[str, Any]:
        """Performance summary statistics"""
        try:
            stocks = self.get_all_live_stocks()

            if not stocks:
                return {"error": "No stocks data available"}

            changes = [s.get("change_percent", 0) for s in stocks]

            return {
                "total_stocks": len(stocks),
                "avg_change": sum(changes) / len(changes),
                "max_gainer": max(changes),
                "max_loser": min(changes),
                "positive_stocks": len([c for c in changes if c > 0]),
                "negative_stocks": len([c for c in changes if c < 0]),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error calculating performance summary: {e}")
            return {"error": str(e)}

    def get_record_movers(self) -> Dict[str, Any]:
        """Stocks making new highs and lows"""
        try:
            stocks = self.get_all_live_stocks()

            new_highs = []
            new_lows = []

            for stock in stocks:
                ltp = stock.get("last_price", 0)
                high = stock.get("high", 0)
                low = stock.get("low", 0)

                if ltp > 0 and high > 0:
                    # Near 52-week high (simplified)
                    if (ltp / high) >= 0.99:
                        new_highs.append(stock)
                    elif low > 0 and (ltp / low) <= 1.01:
                        new_lows.append(stock)

            return {
                "new_highs": new_highs[:20],
                "new_lows": new_lows[:20],
                "summary": {
                    "total_new_highs": len(new_highs),
                    "total_new_lows": len(new_lows),
                },
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error calculating record movers: {e}")
            return {"new_highs": [], "new_lows": [], "error": str(e)}

    # FALLBACK CALCULATION METHODS:

    def _calculate_top_movers_manually(self, limit: int = 20) -> Dict[str, Any]:
        """Manual calculation of top movers"""
        try:
            stocks = self.get_all_live_stocks()

            # Sort by change percentage
            gainers = sorted(
                stocks, key=lambda x: x.get("change_percent", 0), reverse=True
            )[:limit]
            losers = sorted(stocks, key=lambda x: x.get("change_percent", 0))[:limit]

            return {
                "gainers": gainers,
                "losers": losers,
                "total_stocks_analyzed": len(stocks),
            }
        except Exception as e:
            logger.error(f"Error in manual top movers calculation: {e}")
            return {"gainers": [], "losers": [], "total_stocks_analyzed": 0}

    def _calculate_sector_analysis_manually(self) -> Dict[str, Any]:
        """FIXED: Manual calculation of sector analysis using enriched prices"""
        try:
            # Get all enriched prices from registry
            from services.instrument_registry import instrument_registry

            all_stocks = list(instrument_registry.get_enriched_prices().values())

            if not all_stocks:
                logger.warning("⚠️ No enriched prices available for sector analysis")
                return {"sector_analysis": {}}

            logger.info(f"📊 Analyzing {len(all_stocks)} stocks for sector breakdown")

            sectors = {}

            for stock in all_stocks:
                try:
                    sector = stock.get("sector", "OTHER")
                    if sector not in sectors:
                        sectors[sector] = {
                            "stocks": [],
                            "total_stocks": 0,
                            "advancing": 0,
                            "declining": 0,
                            "unchanged": 0,
                            "total_volume": 0,
                        }

                    sectors[sector]["stocks"].append(stock)
                    sectors[sector]["total_stocks"] += 1
                    sectors[sector]["total_volume"] += stock.get("volume", 0)

                    change_pct = stock.get("change_percent", 0)
                    if change_pct > 0:
                        sectors[sector]["advancing"] += 1
                    elif change_pct < 0:
                        sectors[sector]["declining"] += 1
                    else:
                        sectors[sector]["unchanged"] += 1

                except Exception as e:
                    logger.warning(f"⚠️ Error processing stock for sector analysis: {e}")
                    continue

            # Calculate averages and build final analysis
            sector_analysis = {}
            for sector, data in sectors.items():
                if data["stocks"]:
                    stock_changes = [s.get("change_percent", 0) for s in data["stocks"]]
                    avg_change = sum(stock_changes) / len(stock_changes)

                    # Find top and worst performers
                    top_performer = max(
                        data["stocks"], key=lambda x: x.get("change_percent", 0)
                    )
                    worst_performer = min(
                        data["stocks"], key=lambda x: x.get("change_percent", 0)
                    )

                    sector_analysis[sector] = {
                        "total_stocks": data["total_stocks"],
                        "avg_change_percent": round(avg_change, 2),
                        "advancing": data["advancing"],
                        "declining": data["declining"],
                        "unchanged": data["unchanged"],
                        "strength_score": round(
                            (data["advancing"] - data["declining"])
                            / data["total_stocks"]
                            * 100,
                            2,
                        ),
                        "total_volume": data["total_volume"],
                        "top_performer": {
                            "symbol": top_performer.get("symbol", "N/A"),
                            "name": top_performer.get("name", "N/A"),
                            "change_percent": top_performer.get("change_percent", 0),
                        },
                        "worst_performer": {
                            "symbol": worst_performer.get("symbol", "N/A"),
                            "name": worst_performer.get("name", "N/A"),
                            "change_percent": worst_performer.get("change_percent", 0),
                        },
                    }

            logger.info(
                f"📊 Manual sector analysis completed for {len(sector_analysis)} sectors"
            )
            return {"sector_analysis": sector_analysis}

        except Exception as e:
            logger.error(f"Error in manual sector analysis: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            return {"sector_analysis": {}}

    def _calculate_breadth_ratio(self, sector_data: dict) -> float:
        """Calculate breadth ratio for a sector"""
        advancing = sector_data.get("advancing", 0)
        declining = sector_data.get("declining", 0)

        if advancing + declining == 0:
            return 0.5  # Neutral when no movement

        return round(advancing / (advancing + declining), 3)

    def _calculate_market_summary_manually(self) -> Dict[str, Any]:
        """Manual calculation of market summary"""
        try:
            stocks = self.get_all_live_stocks()

            if not stocks:
                return {"error": "No stocks data available"}

            advancing = len([s for s in stocks if s.get("change_percent", 0) > 0])
            declining = len([s for s in stocks if s.get("change_percent", 0) < 0])
            unchanged = len(stocks) - advancing - declining

            total_volume = sum(s.get("volume", 0) for s in stocks)
            avg_volume = total_volume / len(stocks) if stocks else 0
            high_volume_stocks = len(
                [s for s in stocks if s.get("volume", 0) > avg_volume * 2]
            )

            adv_dec_ratio = advancing / declining if declining > 0 else float("inf")
            breadth_pct = ((advancing - declining) / len(stocks)) * 100 if stocks else 0

            return {
                "total_stocks": len(stocks),
                "advancing": advancing,
                "declining": declining,
                "unchanged": unchanged,
                "advance_decline_ratio": adv_dec_ratio,
                "market_breadth_percent": breadth_pct,
                "volume_stats": {
                    "total_volume": total_volume,
                    "average_volume": avg_volume,
                    "high_volume_stocks": high_volume_stocks,
                },
                "sector_performance": {},  # Would need more complex calculation
                "market_indicators": {
                    "trend": (
                        "bullish"
                        if breadth_pct > 10
                        else "bearish" if breadth_pct < -10 else "neutral"
                    ),
                    "volatility": "normal",  # Placeholder
                },
            }
        except Exception as e:
            logger.error(f"Error in manual market summary: {e}")
            return {"error": str(e)}

    def _calculate_volume_leaders_manually(
        self, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Manual calculation of volume leaders"""
        try:
            stocks = self.get_all_live_stocks()

            # Filter stocks with volume data and sort by volume
            volume_stocks = [s for s in stocks if s.get("volume", 0) > 0]
            volume_leaders = sorted(
                volume_stocks, key=lambda x: x.get("volume", 0), reverse=True
            )

            return volume_leaders[:limit]
        except Exception as e:
            logger.error(f"Error in manual volume leaders calculation: {e}")
            return []

    # HELPER METHODS
    def _categorize_by_price(self, price: float) -> str:
        """Categorize stock by price range"""
        if price >= 1000:
            return "high_price"
        elif price >= 100:
            return "medium_price"
        else:
            return "low_price"

    def _categorize_volume(self, volume: int) -> str:
        """Categorize volume level"""
        if volume >= 1000000:
            return "very_high"
        elif volume >= 100000:
            return "high"
        elif volume >= 10000:
            return "medium"
        else:
            return "low"

    def _categorize_performance(self, change_percent: float) -> str:
        """Categorize performance"""
        if change_percent >= 5:
            return "strong_gainer"
        elif change_percent >= 1:
            return "gainer"
        elif change_percent <= -5:
            return "strong_loser"
        elif change_percent <= -1:
            return "loser"
        else:
            return "neutral"

    def _categorize_sector_performance(self, avg_change: float) -> str:
        """Categorize sector performance"""
        if avg_change >= 2:
            return "outperforming"
        elif avg_change >= 0.5:
            return "positive"
        elif avg_change <= -2:
            return "underperforming"
        elif avg_change <= -0.5:
            return "negative"
        else:
            return "neutral"

    def _calculate_sector_momentum(self, sector_data: dict) -> str:
        """Calculate sector momentum"""
        strength_score = sector_data.get("strength_score", 0)
        if strength_score >= 60:
            return "strong_bullish"
        elif strength_score >= 20:
            return "bullish"
        elif strength_score <= -60:
            return "strong_bearish"
        elif strength_score <= -20:
            return "bearish"
        else:
            return "sideways"

    def _interpret_sentiment(
        self, sentiment: str, confidence: float, breadth: float
    ) -> str:
        """Provide sentiment interpretation"""
        interpretations = {
            "very_bullish": f"Strong bullish sentiment with {breadth:.1f}% market breadth. Broad-based buying across sectors.",
            "bullish": f"Positive market sentiment with {breadth:.1f}% breadth. More stocks advancing than declining.",
            "neutral": f"Neutral market with {breadth:.1f}% breadth. Mixed signals across sectors.",
            "bearish": f"Negative sentiment with {breadth:.1f}% breadth. Selling pressure evident.",
            "very_bearish": f"Strong bearish sentiment with {breadth:.1f}% breadth. Broad-based selling.",
        }
        return interpretations.get(sentiment, "Market sentiment unclear.")

    def _should_recalculate(self, feature: str) -> bool:
        """Check if feature should be recalculated"""
        if feature not in self.last_calculated:
            return True

        last_calc = self.last_calculated[feature]
        return (datetime.now() - last_calc).total_seconds() > self.cache_ttl

    def _mark_calculated(self, feature: str):
        """Mark feature as calculated"""
        self.last_calculated[feature] = datetime.now()

    def _get_cache_status(self) -> Dict[str, str]:
        """Get cache status for all features"""
        features = [
            "top_movers",
            "sector_heatmap",
            "market_sentiment",
            "volume_analysis",
            "gap_analysis",
            "breakout_analysis",
        ]
        status = {}

        for feature in features:
            if feature in self.last_calculated:
                age = (datetime.now() - self.last_calculated[feature]).total_seconds()
                status[feature] = f"cached_{int(age)}s_ago"
            else:
                status[feature] = "not_calculated"

        return status

    # ADD to END of enhanced_market_analytics_service.py


# Add this function at the end of enhanced_market_analytics_service.py
def setup_analytics_events():
    """Connect enhanced analytics to price updates"""
    try:
        from services.instrument_registry import instrument_registry

        def on_price_update(data):
            # Clear cache for fresh calculation
            enhanced_analytics.cache.clear()
            enhanced_analytics.last_calculated.clear()

            # OPTIONAL: Generate fresh analytics if needed
            try:
                logger.info("🔄 Refreshing analytics after price update")
                enhanced_analytics.get_complete_analytics()
            except Exception as e:
                logger.error(f"❌ Error refreshing analytics: {e}")

        # Subscribe to both instrument registry and unified manager events
        instrument_registry.subscribe("price_update", on_price_update)

        try:
            from services.unified_websocket_manager import unified_manager

            # Also subscribe to direct trigger events
            def on_trigger_analytics(data):
                logger.info("🔄 Manually triggered analytics refresh")
                enhanced_analytics.cache.clear()
                enhanced_analytics.last_calculated.clear()
                enhanced_analytics.get_complete_analytics()

            unified_manager.register_handler("trigger_analytics", on_trigger_analytics)
            logger.info("✅ Enhanced analytics connected to unified events")
        except Exception as e:
            logger.error(f"❌ Error connecting to unified manager: {e}")

        logger.info("✅ Enhanced analytics connected to price events")
    except Exception as e:
        logger.error(f"❌ Analytics event setup failed: {e}")


# Actually call the setup function to connect events
enhanced_analytics = EnhancedMarketAnalyticsService()


setup_analytics_events()
