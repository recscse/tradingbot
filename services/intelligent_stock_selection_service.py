"""
Intelligent Stock Selection Service
Uses optimized market data for sentiment-based trading decisions

Flow:
1. Premarket: Analyze previous day + gap analysis
2. Market Open (9:15-9:25): Validate sentiment + sector strength
3. Live Trading: Continuous monitoring + dynamic selection

Selection Logic:
Market Sentiment → Sector Analysis → Stock Selection → Value Ranking
"""

import logging
import time
from datetime import datetime, time as dt_time, date
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
from sqlalchemy.orm import Session
from database.connection import SessionLocal
from database.models import SelectedStock

logger = logging.getLogger(__name__)


class MarketSentiment(Enum):
    VERY_BULLISH = "very_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    VERY_BEARISH = "very_bearish"


class TradingPhase(Enum):
    PREMARKET = "premarket"        # Before 9:15
    MARKET_OPEN = "market_open"    # 9:15-9:25 validation
    LIVE_TRADING = "live_trading"  # 9:25+ active trading
    POST_MARKET = "post_market"    # After 3:30


@dataclass
class StockSelection:
    """Complete stock selection with metadata and scoring"""
    # Static metadata (from optimized service)
    symbol: str
    name: str
    instrument_key: str
    sector: str
    is_fno: bool
    lot_size: Optional[int]

    # Live market data
    ltp: float
    change_percent: float
    change: float
    volume: int
    value_crores: float
    high: float
    low: float
    previous_close: float

    # Selection scoring
    sentiment_score: float      # Market sentiment alignment
    sector_score: float        # Sector strength score
    technical_score: float     # Technical indicators
    volume_score: float        # Volume analysis
    value_score: float         # Trading value score
    final_score: float         # Combined weighted score

    # Selection metadata
    selection_reason: str
    confidence_level: float
    risk_level: str
    recommended_quantity: int
    target_value: float
    stop_loss: float

    # Options trading direction based on market sentiment
    options_direction: str  # "CE" (CALL) for positive market, "PE" (PUT) for negative market

    # Timestamps
    selected_at: str
    valid_until: str


class IntelligentStockSelectionService:
    """
    Intelligent stock selection using market sentiment + sector analysis + value ranking
    Built on optimized market data service for ultra-fast decisions
    """

    def __init__(self):
        # Core dependencies
        self.optimized_service = None
        self.analytics_service = None

        # Selection state - simplified workflow
        self.premarket_selections: List[StockSelection] = []
        self.final_selections: List[StockSelection] = []  # Final selections for the day - NO MORE CHANGES

        # Market state
        self.premarket_sentiment: MarketSentiment = MarketSentiment.NEUTRAL
        self.market_open_sentiment: MarketSentiment = MarketSentiment.NEUTRAL
        self.current_sentiment: MarketSentiment = MarketSentiment.NEUTRAL  # Current market sentiment
        self.current_phase: TradingPhase = TradingPhase.PREMARKET
        self.last_selection_time: Optional[datetime] = None
        self.sentiment_changed: bool = False
        self.final_selection_done: bool = False  # Once true, NO MORE stock selection changes

        # Configuration
        self.selection_config = {
            "max_stocks_per_selection": 5,
            "min_value_crores": 0.0,  # No minimum - pick highest value stocks from top sectors
            "min_volume": 100000,
            "max_risk_per_stock": 2.0,  # % of portfolio
            "min_score_threshold": 0.15,  # Testing threshold - realistic for scoring algorithm
            "sentiment_weight": 0.3,
            "sector_weight": 0.3,
            "technical_weight": 0.2,
            "volume_weight": 0.1,
            "value_weight": 0.1,
            "validation_window_minutes": 10,
        }

        # Sector weightings based on market sentiment
        self.sector_sentiment_weights = {
            MarketSentiment.VERY_BULLISH: {
                "BANKING_FINANCIAL_SERVICES": 0.9,
                "INFORMATION_TECHNOLOGY": 0.8,
                "AUTOMOTIVE": 0.8,
                "ENERGY": 0.7,
                "PHARMACEUTICAL": 0.6,
                "FMCG": 0.6,
                "METALS_MINING": 0.9,
                "TELECOMMUNICATIONS": 0.5,
                "REAL_ESTATE": 0.8,
            },
            MarketSentiment.BULLISH: {
                "BANKING_FINANCIAL_SERVICES": 0.8,
                "INFORMATION_TECHNOLOGY": 0.9,
                "AUTOMOTIVE": 0.7,
                "ENERGY": 0.6,
                "PHARMACEUTICAL": 0.7,
                "FMCG": 0.8,
                "METALS_MINING": 0.7,
                "TELECOMMUNICATIONS": 0.6,
                "REAL_ESTATE": 0.6,
            },
            MarketSentiment.NEUTRAL: {
                "BANKING_FINANCIAL_SERVICES": 0.6,
                "INFORMATION_TECHNOLOGY": 0.7,
                "AUTOMOTIVE": 0.5,
                "ENERGY": 0.5,
                "PHARMACEUTICAL": 0.8,
                "FMCG": 0.9,
                "METALS_MINING": 0.4,
                "TELECOMMUNICATIONS": 0.7,
                "REAL_ESTATE": 0.4,
            },
            MarketSentiment.BEARISH: {
                "BANKING_FINANCIAL_SERVICES": 0.4,
                "INFORMATION_TECHNOLOGY": 0.6,
                "AUTOMOTIVE": 0.3,
                "ENERGY": 0.4,
                "PHARMACEUTICAL": 0.9,
                "FMCG": 0.8,
                "METALS_MINING": 0.2,
                "TELECOMMUNICATIONS": 0.7,
                "REAL_ESTATE": 0.2,
            },
            MarketSentiment.VERY_BEARISH: {
                "BANKING_FINANCIAL_SERVICES": 0.2,
                "INFORMATION_TECHNOLOGY": 0.4,
                "AUTOMOTIVE": 0.1,
                "ENERGY": 0.2,
                "PHARMACEUTICAL": 0.8,
                "FMCG": 0.9,
                "METALS_MINING": 0.1,
                "TELECOMMUNICATIONS": 0.6,
                "REAL_ESTATE": 0.1,
            },
        }

        logger.info("🎯 Intelligent Stock Selection Service initialized")

    async def initialize_services(self):
        """Initialize required services"""
        try:
            # Get optimized market data service
            from services.optimized_market_data_service import optimized_market_service
            self.optimized_service = optimized_market_service

            # Get analytics service
            from services.enhanced_market_analytics import enhanced_analytics
            self.analytics_service = enhanced_analytics

            logger.info("✅ Stock selection services initialized")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to initialize stock selection services: {e}")
            return False

    def get_current_trading_phase(self) -> TradingPhase:
        """Determine current trading phase based on time"""
        now = datetime.now().time()

        if now < dt_time(9, 15):
            return TradingPhase.PREMARKET
        elif dt_time(9, 15) <= now <= dt_time(9, 25):
            return TradingPhase.MARKET_OPEN
        elif dt_time(9, 25) < now < dt_time(15, 30):
            return TradingPhase.LIVE_TRADING
        else:
            return TradingPhase.POST_MARKET

    async def analyze_market_sentiment(self) -> Tuple[MarketSentiment, Dict[str, Any]]:
        """Get market sentiment from optimized service - uses proper advance/decline calculation"""
        try:
            if not self.optimized_service:
                await self.initialize_services()

            # Get pre-calculated sentiment from optimized service
            sentiment_data = self.optimized_service.get_market_sentiment()

            if "error" in sentiment_data:
                logger.warning("⚠️ No market sentiment data available, using neutral")
                return MarketSentiment.NEUTRAL, sentiment_data

            # Map optimized service sentiment to our enum
            sentiment_mapping = {
                "very_bullish": MarketSentiment.VERY_BULLISH,
                "bullish": MarketSentiment.BULLISH,
                "neutral": MarketSentiment.NEUTRAL,
                "bearish": MarketSentiment.BEARISH,
                "very_bearish": MarketSentiment.VERY_BEARISH
            }

            sentiment_str = sentiment_data.get("sentiment", "neutral")
            sentiment = sentiment_mapping.get(sentiment_str, MarketSentiment.NEUTRAL)

            self.current_sentiment = sentiment

            # Enhanced analysis with advance/decline details
            sentiment_analysis = {
                "sentiment": sentiment.value,
                "confidence": sentiment_data.get("confidence", 50),
                "metrics": sentiment_data.get("metrics", {}),
                "advance_decline_ratio": sentiment_data.get("metrics", {}).get("advance_decline_ratio", 1.0),
                "market_breadth_percent": sentiment_data.get("metrics", {}).get("market_breadth_percent", 0),
                "advancing_stocks": sentiment_data.get("metrics", {}).get("advancing", 0),
                "declining_stocks": sentiment_data.get("metrics", {}).get("declining", 0),
                "total_stocks": sentiment_data.get("metrics", {}).get("total_stocks", 0),
                "recommendation": self._get_sentiment_recommendation(sentiment),
                "timestamp": datetime.now().isoformat(),
            }

            logger.info(f"📊 Market sentiment: {sentiment.value} (A/D ratio: {sentiment_analysis['advance_decline_ratio']:.2f})")
            return sentiment, sentiment_analysis

        except Exception as e:
            logger.error(f"❌ Error getting market sentiment: {e}")
            return MarketSentiment.NEUTRAL, {"error": str(e)}

    async def analyze_sector_strength(self, sentiment: MarketSentiment) -> Dict[str, float]:
        """Analyze sector strength based on market sentiment"""
        try:
            if not self.optimized_service:
                await self.initialize_services()

            # Get sector performance
            sector_performance = self.optimized_service.get_sector_performance()
            sentiment_weights = self.sector_sentiment_weights.get(sentiment, {})

            sector_scores = {}

            for sector, performance in sector_performance.items():
                # Base score from actual performance
                performance_score = (
                    performance.get("avg_change_percent", 0) / 100 +
                    performance.get("strength_score", 0) / 100 +
                    (performance.get("advancing", 0) / max(performance.get("total_stocks", 1), 1))
                )

                # Apply sentiment weight
                sentiment_weight = sentiment_weights.get(sector, 0.5)

                # Combined score
                final_score = performance_score * sentiment_weight
                sector_scores[sector] = round(final_score, 3)

            # Sort by score
            sorted_sectors = dict(sorted(sector_scores.items(), key=lambda x: x[1], reverse=True))

            logger.info(f"🏢 Top sectors for {sentiment.value}: {list(sorted_sectors.keys())[:3]}")
            return sorted_sectors

        except Exception as e:
            logger.error(f"❌ Error analyzing sector strength: {e}")
            return {}

    async def select_stocks_by_value(
        self,
        target_sectors: List[str],
        max_stocks: int = 5
    ) -> List[StockSelection]:
        """Select stocks based on highest value in target sectors"""
        try:
            if not self.optimized_service:
                await self.initialize_services()

            selected_stocks = []

            for sector in target_sectors:
                if len(selected_stocks) >= max_stocks:
                    break

                # Get sector stocks
                sector_stocks = self.optimized_service.get_sector_stocks(sector)
                stocks = sector_stocks.get(sector, [])

                if not stocks:
                    continue

                # Filter eligible stocks (F&O stocks only, no value filter)
                eligible_stocks = [
                    stock for stock in stocks
                    if (
                        stock.get("volume", 0) >= self.selection_config["min_volume"] and
                        stock.get("is_fno", False) and  # F&O stocks only
                        stock.get("ltp", 0) > 0
                    )
                ]

                # Sort by value (highest first)
                eligible_stocks.sort(key=lambda x: x.get("value_crores", 0), reverse=True)

                # Select top stock from this sector
                for stock in eligible_stocks[:2]:  # Max 2 per sector
                    if len(selected_stocks) >= max_stocks:
                        break

                    # Calculate selection scores
                    selection = await self._create_stock_selection(stock, sector)
                    if selection and selection.final_score > self.selection_config["min_score_threshold"]:
                        selected_stocks.append(selection)

            # Sort final selections by score
            selected_stocks.sort(key=lambda x: x.final_score, reverse=True)

            logger.info(f"📈 Selected {len(selected_stocks)} stocks: {[s.symbol for s in selected_stocks]}")
            return selected_stocks[:max_stocks]

        except Exception as e:
            logger.error(f"❌ Error selecting stocks by value: {e}")
            return []

    async def _create_stock_selection(self, stock_data: Dict[str, Any], sector: str) -> Optional[StockSelection]:
        """Create detailed stock selection with scoring"""
        try:
            # Calculate individual scores
            sentiment_score = self._calculate_sentiment_score(stock_data)
            sector_score = self._calculate_sector_score(stock_data, sector)
            technical_score = self._calculate_technical_score(stock_data)
            volume_score = self._calculate_volume_score(stock_data)
            value_score = self._calculate_value_score(stock_data)

            # Calculate weighted final score
            final_score = (
                sentiment_score * self.selection_config["sentiment_weight"] +
                sector_score * self.selection_config["sector_weight"] +
                technical_score * self.selection_config["technical_weight"] +
                volume_score * self.selection_config["volume_weight"] +
                value_score * self.selection_config["value_weight"]
            )

            # Risk assessment
            risk_level = self._assess_risk_level(stock_data, final_score)
            confidence_level = min(final_score, 1.0)

            # Position sizing
            recommended_quantity = self._calculate_position_size(stock_data)

            # Options trading direction based on market sentiment
            options_direction = self._get_options_direction()

            # Create selection
            selection = StockSelection(
                symbol=stock_data["symbol"],
                name=stock_data["name"],
                instrument_key=stock_data["instrument_key"],
                sector=sector,
                is_fno=stock_data.get("is_fno", False),
                lot_size=stock_data.get("lot_size"),

                ltp=stock_data["ltp"],
                change_percent=stock_data["change_percent"],
                change=stock_data["change"],
                volume=stock_data["volume"],
                value_crores=stock_data["value_crores"],
                high=stock_data["high"],
                low=stock_data["low"],
                previous_close=stock_data["previous_close"],

                sentiment_score=round(sentiment_score, 3),
                sector_score=round(sector_score, 3),
                technical_score=round(technical_score, 3),
                volume_score=round(volume_score, 3),
                value_score=round(value_score, 3),
                final_score=round(final_score, 3),

                selection_reason=f"High value ({stock_data['value_crores']:.1f}Cr) in strong {sector} sector",
                confidence_level=round(confidence_level, 2),
                risk_level=risk_level,
                recommended_quantity=recommended_quantity,
                target_value=stock_data["value_crores"],
                stop_loss=round(stock_data["ltp"] * 0.95, 2),  # 5% stop loss

                options_direction=options_direction,

                selected_at=datetime.now().isoformat(),
                valid_until=(datetime.now().replace(hour=15, minute=30)).isoformat(),
            )

            return selection

        except Exception as e:
            logger.error(f"❌ Error creating stock selection: {e}")
            return None

    def _calculate_sentiment_score(self, stock_data: Dict[str, Any]) -> float:
        """Calculate sentiment alignment score"""
        change_percent = stock_data.get("change_percent", 0)

        if self.current_sentiment in [MarketSentiment.BULLISH, MarketSentiment.VERY_BULLISH]:
            return min(max(change_percent / 5.0, 0), 1.0)  # Positive stocks score higher
        elif self.current_sentiment in [MarketSentiment.BEARISH, MarketSentiment.VERY_BEARISH]:
            return min(max(-change_percent / 5.0, 0), 1.0)  # Negative stocks score higher (short)
        else:
            return 0.5  # Neutral market

    def _calculate_sector_score(self, stock_data: Dict[str, Any], sector: str) -> float:
        """Calculate sector strength score"""
        try:
            sector_performance = self.optimized_service.get_sector_performance()
            performance = sector_performance.get(sector, {})

            # Sector strength factors
            avg_change = performance.get("avg_change_percent", 0) / 100
            strength_score = performance.get("strength_score", 0) / 100

            return min(max((avg_change + strength_score) / 2, 0), 1.0)

        except Exception:
            return 0.5

    def _calculate_technical_score(self, stock_data: Dict[str, Any]) -> float:
        """Calculate technical analysis score"""
        try:
            ltp = stock_data.get("ltp", 0)
            high = stock_data.get("high", 0)
            low = stock_data.get("low", 0)
            change_percent = stock_data.get("change_percent", 0)

            if high <= 0 or low <= 0:
                return 0.5

            # Price position in day's range
            price_position = (ltp - low) / (high - low) if (high - low) > 0 else 0.5

            # Momentum score
            momentum_score = min(abs(change_percent) / 10.0, 1.0)

            # Combined technical score
            return (price_position * 0.6 + momentum_score * 0.4)

        except Exception:
            return 0.5

    def _calculate_volume_score(self, stock_data: Dict[str, Any]) -> float:
        """Calculate volume strength score"""
        volume = stock_data.get("volume", 0)

        # Volume categories
        if volume >= 10000000:  # 1Cr+
            return 1.0
        elif volume >= 5000000:  # 50L+
            return 0.8
        elif volume >= 1000000:  # 10L+
            return 0.6
        elif volume >= 500000:   # 5L+
            return 0.4
        else:
            return 0.2

    def _calculate_value_score(self, stock_data: Dict[str, Any]) -> float:
        """Calculate trading value score"""
        value_crores = stock_data.get("value_crores", 0)

        # Value categories
        if value_crores >= 100:    # 100Cr+
            return 1.0
        elif value_crores >= 50:   # 50Cr+
            return 0.8
        elif value_crores >= 10:   # 10Cr+
            return 0.6
        elif value_crores >= 5:    # 5Cr+
            return 0.4
        else:
            return 0.2

    def _assess_risk_level(self, stock_data: Dict[str, Any], final_score: float) -> str:
        """Assess risk level for the stock"""
        change_percent = abs(stock_data.get("change_percent", 0))
        volume = stock_data.get("volume", 0)

        if final_score >= 0.8 and change_percent <= 3 and volume >= 1000000:
            return "LOW"
        elif final_score >= 0.6 and change_percent <= 5:
            return "MEDIUM"
        else:
            return "HIGH"

    def _calculate_position_size(self, stock_data: Dict[str, Any]) -> int:
        """Calculate recommended position size"""
        lot_size = stock_data.get("lot_size", 1)
        ltp = stock_data.get("ltp", 0)

        if not lot_size or ltp <= 0:
            return 0

        # Simple position sizing (can be enhanced)
        if ltp <= 100:
            return lot_size * 3
        elif ltp <= 500:
            return lot_size * 2
        else:
            return lot_size

    def _get_sentiment_recommendation(self, sentiment: MarketSentiment) -> str:
        """Get trading recommendation based on sentiment"""
        recommendations = {
            MarketSentiment.VERY_BULLISH: "Strong BUY - Focus on momentum and growth stocks",
            MarketSentiment.BULLISH: "BUY - Select quality stocks with good fundamentals",
            MarketSentiment.NEUTRAL: "HOLD - Maintain positions, avoid new large positions",
            MarketSentiment.BEARISH: "SELL/SHORT - Reduce positions, consider defensive stocks",
            MarketSentiment.VERY_BEARISH: "STRONG SELL - Exit positions, consider short selling",
        }
        return recommendations.get(sentiment, "NEUTRAL - Monitor closely")

    def _get_options_direction(self) -> str:
        """Determine options trading direction based on market sentiment"""
        # Use current sentiment (premarket or market open)
        current_sentiment = getattr(self, 'market_open_sentiment', self.premarket_sentiment)

        if current_sentiment in [MarketSentiment.BULLISH, MarketSentiment.VERY_BULLISH]:
            return "CE"  # CALL options for positive market
        elif current_sentiment in [MarketSentiment.BEARISH, MarketSentiment.VERY_BEARISH]:
            return "PE"  # PUT options for negative market
        else:
            return "CE"  # Default to CALL for neutral market

    # Public API Methods

    async def run_premarket_selection(self) -> Dict[str, Any]:
        """Run premarket stock selection (before 9:15 AM) - ONLY ONCE"""
        try:
            # Check if premarket selection already done
            if self.premarket_selections:
                logger.warning("⚠️ Premarket selection already completed today")
                return {
                    "success": False,
                    "message": "Premarket selection already done today",
                    "existing_selections": [asdict(stock) for stock in self.premarket_selections],
                    "phase": "premarket"
                }

            logger.info("🌅 Starting premarket stock selection...")

            # Analyze market sentiment and store it
            sentiment, sentiment_analysis = await self.analyze_market_sentiment()
            self.premarket_sentiment = sentiment

            # Analyze sector strength
            sector_scores = await self.analyze_sector_strength(sentiment)
            top_sectors = list(sector_scores.keys())[:3]

            # Select stocks
            selected_stocks = await self.select_stocks_by_value(top_sectors)

            # Store premarket selections
            self.premarket_selections = selected_stocks
            self.current_phase = TradingPhase.PREMARKET
            self.last_selection_time = datetime.now()

            logger.info(f"📊 Premarket sentiment: {sentiment.value}")

            result = {
                "phase": "premarket",
                "sentiment_analysis": sentiment_analysis,
                "top_sectors": {sector: sector_scores[sector] for sector in top_sectors},
                "selected_stocks": [asdict(stock) for stock in selected_stocks],
                "selection_count": len(selected_stocks),
                "next_validation": "09:15:00",
                "timestamp": datetime.now().isoformat(),
            }

            # Save to database for auto-trading integration
            try:
                saved = await self.save_selections_to_database(selected_stocks, "premarket")
                if saved:
                    result["database_saved"] = True
                    result["available_for_autotrading"] = True
                    logger.info("✅ Premarket selections saved to database for auto-trading")
                else:
                    result["database_saved"] = False
                    logger.warning("⚠️ Failed to save premarket selections to database")
            except Exception as db_error:
                logger.error(f"❌ Database save error: {db_error}")
                result["database_saved"] = False

            # Broadcast update via WebSocket
            try:
                from services.unified_websocket_manager import emit_intelligent_stock_selection_update
                emit_intelligent_stock_selection_update({
                    "type": "premarket_selection_completed",
                    "data": result,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as ws_error:
                logger.warning(f"⚠️ Failed to broadcast premarket selection: {ws_error}")

            logger.info(f"✅ Premarket selection complete: {len(selected_stocks)} stocks selected")
            return result

        except Exception as e:
            logger.error(f"❌ Error in premarket selection: {e}")
            return {"error": str(e), "phase": "premarket"}

    async def validate_market_open_selection(self) -> Dict[str, Any]:
        """Market open validation - Check sentiment and finalize selections (9:15-9:25) - FINAL DECISION"""
        try:
            logger.info("🔍 Market open validation - Making FINAL stock selection for the day...")

            # Check if final selection already done
            if self.final_selection_done:
                logger.warning("⚠️ Final selection already completed - no more changes today")
                return {
                    "success": False,
                    "message": "Final selections already done today - no more changes allowed",
                    "final_selections": [asdict(stock) for stock in self.final_selections],
                    "phase": "final_selection_done"
                }

            if not self.premarket_selections:
                return {
                    "error": "No premarket selections found. Run premarket selection first.",
                    "phase": "market_open_validation"
                }

            # Check current market sentiment at market open
            market_sentiment, sentiment_analysis = await self.analyze_market_sentiment()
            self.market_open_sentiment = market_sentiment

            # Compare sentiments
            self.sentiment_changed = (market_sentiment != self.premarket_sentiment)

            logger.info(f"📊 Premarket sentiment: {self.premarket_sentiment.value}")
            logger.info(f"📊 Market open sentiment: {market_sentiment.value}")
            logger.info(f"📊 Sentiment changed: {self.sentiment_changed}")

            # FINAL DECISION LOGIC
            if self.sentiment_changed:
                logger.info("🔄 Sentiment changed - Running NEW stock selection (FINAL)")

                # Run completely fresh selection with new sentiment
                sector_scores = await self.analyze_sector_strength(market_sentiment)
                top_sectors = list(sector_scores.keys())[:3]
                final_selections = await self.select_stocks_by_value(top_sectors)

                self.final_selections = final_selections
                validation_action = "NEW_SELECTION_DUE_TO_SENTIMENT_CHANGE"
                selection_source = "market_open_fresh"

            else:
                logger.info("✅ Sentiment unchanged - Using premarket selections (FINAL)")

                # Use premarket selections as final (no changes needed)
                self.final_selections = self.premarket_selections.copy()
                validation_action = "PREMARKET_SELECTIONS_CONFIRMED"
                selection_source = "premarket_confirmed"

            # MARK AS FINAL - NO MORE CHANGES ALLOWED
            self.final_selection_done = True
            self.current_phase = TradingPhase.MARKET_OPEN
            self.last_selection_time = datetime.now()

            logger.info(f"🎯 FINAL SELECTIONS CONFIRMED: {len(self.final_selections)} stocks selected for the day")

            result = {
                "phase": "market_open_validation",
                "validation_action": validation_action,
                "selection_source": selection_source,
                "sentiment_changed": self.sentiment_changed,
                "premarket_sentiment": self.premarket_sentiment.value,
                "market_open_sentiment": self.market_open_sentiment.value,
                "sentiment_analysis": sentiment_analysis,
                "premarket_count": len(self.premarket_selections),
                "final_count": len(self.final_selections),
                "final_stocks": [asdict(stock) for stock in self.final_selections],
                "final_selection_done": True,
                "ready_for_trading": len(self.final_selections) > 0,
                "timestamp": datetime.now().isoformat(),
            }

            # Save FINAL selections to database for auto-trading
            try:
                saved = await self.save_selections_to_database(self.final_selections, "final_selection")
                if saved:
                    result["database_saved"] = True
                    result["available_for_autotrading"] = True
                    logger.info("✅ Validated selections saved to database for auto-trading")
                else:
                    result["database_saved"] = False
                    logger.warning("⚠️ Failed to save validated selections to database")
            except Exception as db_error:
                logger.error(f"❌ Database save error: {db_error}")
                result["database_saved"] = False

            # Broadcast update via WebSocket
            try:
                from services.unified_websocket_manager import emit_intelligent_stock_selection_update
                emit_intelligent_stock_selection_update({
                    "type": "market_open_validation_completed",
                    "data": result,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as ws_error:
                logger.warning(f"⚠️ Failed to broadcast market open validation: {ws_error}")

            logger.info(f"✅ Market open validation complete: {validation_action}")
            return result

        except Exception as e:
            logger.error(f"❌ Error in market open validation: {e}")
            return {"error": str(e), "phase": "market_open_validation"}

    async def get_live_trading_recommendations(self) -> Dict[str, Any]:
        """Get live trading recommendations - Returns FINAL selections (NO MORE CHANGES)"""
        try:
            # Check if final selections are available
            if not self.final_selection_done or not self.final_selections:
                return {
                    "error": "No final selections available. Complete market open validation first.",
                    "phase": "awaiting_final_selection",
                    "message": "Final stock selection not completed yet. Run premarket selection and market open validation first.",
                    "timestamp": datetime.now().isoformat()
                }

            # Return final selections (no more changes allowed)
            self.current_phase = TradingPhase.LIVE_TRADING

            result = {
                "phase": "live_trading",
                "selection_source": "final_selections",
                "recommendations": [asdict(stock) for stock in self.final_selections],
                "recommendation_count": len(self.final_selections),
                "final_selection_done": True,
                "sentiment_used": self.market_open_sentiment.value,
                "message": "These are the FINAL selections for today - no more changes allowed",
                "last_updated": datetime.now().isoformat(),
            }

            logger.info(f"📊 Returning FINAL selections: {len(self.final_selections)} stocks")
            return result

        except Exception as e:
            logger.error(f"❌ Error getting live trading recommendations: {e}")
            return {"error": str(e), "phase": "live_trading"}

    def get_selection_status(self) -> Dict[str, Any]:
        """Get current selection status"""
        current_phase = self.get_current_trading_phase()

        return {
            "current_phase": current_phase.value,
            "premarket_sentiment": self.premarket_sentiment.value,
            "market_open_sentiment": self.market_open_sentiment.value,
            "sentiment_changed": self.sentiment_changed,
            "premarket_selections": len(self.premarket_selections),
            "final_selections": len(self.final_selections),
            "final_selection_done": self.final_selection_done,
            "last_selection_time": self.last_selection_time.isoformat() if self.last_selection_time else None,
            "next_action": self._get_next_action_recommendation(current_phase),
            "workflow_complete": self.final_selection_done,
            "timestamp": datetime.now().isoformat(),
        }

    async def save_selections_to_database(self, selections: List[StockSelection], selection_type: str = "intelligent") -> bool:
        """Save selected stocks to database for auto-trading integration"""
        try:
            db = SessionLocal()
            today = date.today()

            # Clear existing intelligent selections for today (if any)
            db.query(SelectedStock).filter(
                SelectedStock.selection_date == today,
                SelectedStock.selection_reason.like(f"{selection_type}%")
            ).delete()

            # Save new selections
            for stock in selections:
                selected_stock = SelectedStock(
                    symbol=stock.symbol,
                    instrument_key=stock.instrument_key or f"NSE_EQ|{stock.symbol}",
                    selection_date=today,
                    selection_score=float(stock.final_score),
                    selection_reason=f"{selection_type}_selection_{stock.selection_reason or 'ai_based'}",
                    price_at_selection=float(stock.ltp),
                    volume_at_selection=int(stock.volume or 0),
                    change_percent_at_selection=float(stock.change_percent or 0),
                    sector=stock.sector,
                    score_breakdown=str({
                        "sentiment_score": stock.sentiment_score,
                        "sector_score": stock.sector_score,
                        "technical_score": stock.technical_score,
                        "volume_score": stock.volume_score,
                        "value_score": stock.value_score,
                        "final_score": stock.final_score,
                        "confidence_level": stock.confidence_level,
                        "risk_level": stock.risk_level
                    }),
                    is_active=True
                )
                db.add(selected_stock)

            db.commit()
            logger.info(f"✅ Saved {len(selections)} intelligent stock selections to database")
            return True

        except Exception as e:
            logger.error(f"❌ Error saving selections to database: {e}")
            if db:
                db.rollback()
            return False
        finally:
            if db:
                db.close()

    def _get_next_action_recommendation(self, phase: TradingPhase) -> str:
        """Get next recommended action based on current phase and workflow status"""
        if self.final_selection_done:
            return "✅ Workflow complete - Final selections ready for trading (no more changes today)"

        if not self.premarket_selections:
            return "🌅 Run premarket selection before 9:15 AM"

        if self.premarket_selections and not self.final_selection_done:
            return "🔍 Run market open validation (9:15-9:25 AM) to finalize selections"

        recommendations = {
            TradingPhase.PREMARKET: "🌅 Run premarket selection",
            TradingPhase.MARKET_OPEN: "🔍 Complete market open validation",
            TradingPhase.LIVE_TRADING: "📊 Use final selections for trading",
            TradingPhase.POST_MARKET: "💤 Wait for next trading day"
        }
        return recommendations.get(phase, "Monitor market conditions")


# Create singleton instance
intelligent_stock_selector = IntelligentStockSelectionService()