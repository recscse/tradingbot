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

# Import services at module level for better performance
from services.realtime_market_engine import (
    get_market_engine,
    get_market_sentiment,
    get_sector_performance,
    get_sector_stocks,
)

logger = logging.getLogger(__name__)


class MarketSentiment(Enum):
    VERY_BULLISH = "very_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    VERY_BEARISH = "very_bearish"


class TradingPhase(Enum):
    PREMARKET = "premarket"  # Before 9:15
    MARKET_OPEN = "market_open"  # 9:15-9:25 validation
    LIVE_TRADING = "live_trading"  # 9:25+ active trading
    POST_MARKET = "post_market"  # After 3:30


@dataclass
class StockSelection:
    """Complete stock selection with metadata and scoring"""

    # Static metadata (from optimized service)
    symbol: str
    name: str
    instrument_key: str
    sector: str
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
    sentiment_score: float  # Market sentiment alignment
    sector_score: float  # Sector strength score
    technical_score: float  # Technical indicators
    volume_score: float  # Volume analysis
    value_score: float  # Trading value score
    final_score: float  # Combined weighted score

    # Selection metadata
    selection_reason: str
    confidence_level: float
    risk_level: str
    recommended_quantity: int
    target_value: float
    stop_loss: float

    # Options trading direction based on market sentiment
    options_direction: (
        str  # "CE" (CALL) for positive market, "PE" (PUT) for negative market
    )

    # Timestamps
    selected_at: str
    valid_until: str


class IntelligentStockSelectionService:
    """
    Intelligent stock selection using market sentiment + sector analysis + value ranking.

    UPDATED: Now uses realtime_market_engine for live market data instead of optimized_market_data_service.

    Data Flow:
    1. centralized_ws_manager receives live feed from Upstox WebSocket
    2. Data is forwarded to realtime_market_engine for processing
    3. This service queries realtime_market_engine for:
       - Market sentiment (advance/decline ratio, breadth)
       - Sector performance (avg change%, strength score)
       - Sector stocks (with live LTP, volume, value)
    4. Selection algorithm uses real-time data for stock scoring
    """

    def __init__(self):
        # Core dependencies - UPDATED to use realtime_market_engine
        self.market_engine = None  # Real-time market engine for live data
        self.analytics_service = None

        # Selection state - simplified workflow
        self.premarket_selections: List[StockSelection] = []
        self.final_selections: List[StockSelection] = (
            []
        )  # Final selections for the day - NO MORE CHANGES

        # Market state
        self.premarket_sentiment: MarketSentiment = MarketSentiment.NEUTRAL
        self.market_open_sentiment: MarketSentiment = MarketSentiment.NEUTRAL
        self.current_sentiment: MarketSentiment = (
            MarketSentiment.NEUTRAL
        )  # Current market sentiment
        self.current_phase: TradingPhase = TradingPhase.PREMARKET
        self.last_selection_time: Optional[datetime] = None
        self.sentiment_changed: bool = False
        self.final_selection_done: bool = (
            False  # Once true, NO MORE stock selection changes
        )

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
        # Using EXACT sector names from config/sector_mapping.json
        # Now compatible with dynamic sector discovery from realtime_market_engine
        # Any sector not listed here will use default weight of 0.6
        self.sector_sentiment_weights = {
            MarketSentiment.VERY_BULLISH: {
                "BANKING_FINANCIAL_SERVICES": 0.9,
                "INFORMATION_TECHNOLOGY": 0.8,
                "AUTOMOBILE": 0.8,
                "OIL_GAS": 0.7,
                "POWER_UTILITIES": 0.75,
                "PHARMACEUTICALS": 0.6,
                "CONSUMER_GOODS_FMCG": 0.6,
                "METALS_MINING": 0.9,
                "CEMENT_CONSTRUCTION": 0.85,
                "REAL_ESTATE": 0.8,
                "INDUSTRIAL_MANUFACTURING": 0.75,
                "CONSUMER_SERVICES": 0.7,
                "DIVERSIFIED_CONGLOMERATES": 0.85,
                "TELECOMMUNICATIONS": 0.75,
                "CHEMICALS_FERTILIZERS": 0.8,
                "ELECTRICAL_EQUIPMENT": 0.75,
                "SPECIALTY_RETAIL": 0.7,
                "LOGISTICS_TRANSPORTATION": 0.75,
                "CAPITAL_MARKETS": 0.8,
                "ECOMMERCE_FINTECH": 0.75,
                "TEXTILES_APPAREL": 0.65,
            },
            MarketSentiment.BULLISH: {
                "BANKING_FINANCIAL_SERVICES": 0.8,
                "INFORMATION_TECHNOLOGY": 0.9,
                "AUTOMOBILE": 0.7,
                "OIL_GAS": 0.6,
                "POWER_UTILITIES": 0.65,
                "PHARMACEUTICALS": 0.7,
                "CONSUMER_GOODS_FMCG": 0.8,
                "METALS_MINING": 0.7,
                "CEMENT_CONSTRUCTION": 0.7,
                "REAL_ESTATE": 0.6,
                "INDUSTRIAL_MANUFACTURING": 0.7,
                "CONSUMER_SERVICES": 0.75,
                "DIVERSIFIED_CONGLOMERATES": 0.8,
                "TELECOMMUNICATIONS": 0.7,
                "CHEMICALS_FERTILIZERS": 0.75,
                "ELECTRICAL_EQUIPMENT": 0.7,
                "SPECIALTY_RETAIL": 0.75,
                "LOGISTICS_TRANSPORTATION": 0.7,
                "CAPITAL_MARKETS": 0.75,
                "ECOMMERCE_FINTECH": 0.8,
                "TEXTILES_APPAREL": 0.65,
            },
            MarketSentiment.NEUTRAL: {
                "BANKING_FINANCIAL_SERVICES": 0.6,
                "INFORMATION_TECHNOLOGY": 0.7,
                "AUTOMOBILE": 0.5,
                "OIL_GAS": 0.5,
                "POWER_UTILITIES": 0.5,
                "PHARMACEUTICALS": 0.8,
                "CONSUMER_GOODS_FMCG": 0.9,
                "METALS_MINING": 0.4,
                "CEMENT_CONSTRUCTION": 0.5,
                "REAL_ESTATE": 0.4,
                "INDUSTRIAL_MANUFACTURING": 0.6,
                "CONSUMER_SERVICES": 0.7,
                "DIVERSIFIED_CONGLOMERATES": 0.65,
                "TELECOMMUNICATIONS": 0.6,
                "CHEMICALS_FERTILIZERS": 0.55,
                "ELECTRICAL_EQUIPMENT": 0.6,
                "SPECIALTY_RETAIL": 0.7,
                "LOGISTICS_TRANSPORTATION": 0.6,
                "CAPITAL_MARKETS": 0.65,
                "ECOMMERCE_FINTECH": 0.7,
                "TEXTILES_APPAREL": 0.6,
            },
            MarketSentiment.BEARISH: {
                "BANKING_FINANCIAL_SERVICES": 0.4,
                "INFORMATION_TECHNOLOGY": 0.6,
                "AUTOMOBILE": 0.3,
                "OIL_GAS": 0.4,
                "POWER_UTILITIES": 0.4,
                "PHARMACEUTICALS": 0.9,
                "CONSUMER_GOODS_FMCG": 0.8,
                "METALS_MINING": 0.2,
                "CEMENT_CONSTRUCTION": 0.3,
                "REAL_ESTATE": 0.2,
                "INDUSTRIAL_MANUFACTURING": 0.4,
                "CONSUMER_SERVICES": 0.5,
                "DIVERSIFIED_CONGLOMERATES": 0.45,
                "TELECOMMUNICATIONS": 0.5,
                "CHEMICALS_FERTILIZERS": 0.4,
                "ELECTRICAL_EQUIPMENT": 0.4,
                "SPECIALTY_RETAIL": 0.5,
                "LOGISTICS_TRANSPORTATION": 0.4,
                "CAPITAL_MARKETS": 0.45,
                "ECOMMERCE_FINTECH": 0.5,
                "TEXTILES_APPAREL": 0.4,
            },
            MarketSentiment.VERY_BEARISH: {
                "BANKING_FINANCIAL_SERVICES": 0.2,
                "INFORMATION_TECHNOLOGY": 0.4,
                "AUTOMOBILE": 0.1,
                "OIL_GAS": 0.2,
                "POWER_UTILITIES": 0.2,
                "PHARMACEUTICALS": 0.8,
                "CONSUMER_GOODS_FMCG": 0.9,
                "METALS_MINING": 0.1,
                "CEMENT_CONSTRUCTION": 0.15,
                "REAL_ESTATE": 0.1,
                "INDUSTRIAL_MANUFACTURING": 0.3,
                "CONSUMER_SERVICES": 0.4,
                "DIVERSIFIED_CONGLOMERATES": 0.3,
                "TELECOMMUNICATIONS": 0.4,
                "CHEMICALS_FERTILIZERS": 0.25,
                "ELECTRICAL_EQUIPMENT": 0.3,
                "SPECIALTY_RETAIL": 0.4,
                "LOGISTICS_TRANSPORTATION": 0.3,
                "CAPITAL_MARKETS": 0.3,
                "ECOMMERCE_FINTECH": 0.35,
                "TEXTILES_APPAREL": 0.3,
            },
        }

        logger.info("Intelligent Stock Selection Service initialized")

    async def initialize_services(self):
        """Initialize required services - UPDATED to use realtime_market_engine"""
        try:
            # Get real-time market engine for live market data
            self.market_engine = get_market_engine()

            # Get analytics service

            logger.info(
                "✅ Stock selection services initialized with realtime_market_engine"
            )
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
        """Get market sentiment from realtime_market_engine - uses proper advance/decline calculation"""
        try:
            if not self.market_engine:
                await self.initialize_services()

            # Get real-time sentiment from market engine
            sentiment_data = get_market_sentiment()

            if "error" in sentiment_data:
                logger.warning("⚠️ No market sentiment data available, using neutral")
                return MarketSentiment.NEUTRAL, sentiment_data

            # Check if market data is available
            total_stocks = sentiment_data.get("metrics", {}).get("total_stocks", 0)
            if total_stocks == 0:
                logger.warning(
                    "⚠️ No market data available yet - waiting for WebSocket feed to populate data"
                )
                return MarketSentiment.NEUTRAL, {
                    **sentiment_data,
                    "warning": "No market data available - service waiting for live feed"
                }

            # Map realtime engine sentiment to our enum
            sentiment_mapping = {
                "very_bullish": MarketSentiment.VERY_BULLISH,
                "bullish": MarketSentiment.BULLISH,
                "neutral": MarketSentiment.NEUTRAL,
                "bearish": MarketSentiment.BEARISH,
                "very_bearish": MarketSentiment.VERY_BEARISH,
            }

            sentiment_str = sentiment_data.get("sentiment", "neutral")
            sentiment = sentiment_mapping.get(sentiment_str, MarketSentiment.NEUTRAL)

            self.current_sentiment = sentiment

            # Enhanced analysis with advance/decline details from real-time engine
            sentiment_analysis = {
                "sentiment": sentiment.value,
                "confidence": sentiment_data.get("confidence", 50),
                "metrics": sentiment_data.get("metrics", {}),
                "advance_decline_ratio": sentiment_data.get("metrics", {}).get(
                    "advance_decline_ratio", 1.0
                ),
                "market_breadth_percent": sentiment_data.get("metrics", {}).get(
                    "market_breadth_percent", 0
                ),
                "advancing_stocks": sentiment_data.get("metrics", {}).get(
                    "advancing", 0
                ),
                "declining_stocks": sentiment_data.get("metrics", {}).get(
                    "declining", 0
                ),
                "total_stocks": sentiment_data.get("metrics", {}).get(
                    "total_stocks", 0
                ),
                "recommendation": self._get_sentiment_recommendation(sentiment),
                "timestamp": datetime.now().isoformat(),
            }

            logger.info(
                f"📊 Market sentiment: {sentiment.value} (A/D ratio: {sentiment_analysis['advance_decline_ratio']:.2f})"
            )
            return sentiment, sentiment_analysis

        except Exception as e:
            logger.error(f"❌ Error getting market sentiment: {e}")
            return MarketSentiment.NEUTRAL, {"error": str(e)}

    async def analyze_sector_strength(
        self, sentiment: MarketSentiment
    ) -> Dict[str, float]:
        """
        Analyze sector strength based on market sentiment - UPDATED to use realtime_market_engine.

        Uses dynamic sector weights based on sentiment and actual sector performance from analytics.
        """
        try:
            if not self.market_engine:
                await self.initialize_services()

            # Get sector performance from real-time market engine (uses actual sector names from config)
            sector_performance = get_sector_performance()

            if not sector_performance:
                logger.warning("⚠️ No sector performance data available")
                return {}

            sector_scores = {}

            for sector, performance in sector_performance.items():
                # Base score from actual real-time performance
                avg_change = performance.get("avg_change_percent", 0)
                strength = performance.get("strength_score", 0)
                advancing_ratio = (
                    performance.get("advancing", 0) / max(performance.get("total_stocks", 1), 1)
                )

                # Performance score (0-1 scale)
                performance_score = (
                    min(max(avg_change / 5.0, -1), 1) * 0.5  # Normalize avg_change to -1 to 1
                    + min(max(strength / 50.0, -1), 1) * 0.3   # Normalize strength_score
                    + advancing_ratio * 0.2                      # Advancing ratio already 0-1
                )

                # Get sentiment weight for this sector (default 0.6 if not in predefined weights)
                sentiment_weights = self.sector_sentiment_weights.get(sentiment, {})
                sentiment_weight = sentiment_weights.get(sector, 0.6)  # Default 0.6 for unknown sectors

                # Combined score with sentiment adjustment
                final_score = max(performance_score * sentiment_weight, 0)  # Ensure non-negative
                sector_scores[sector] = round(final_score, 4)

            # Sort by score (highest first)
            sorted_sectors = dict(
                sorted(sector_scores.items(), key=lambda x: x[1], reverse=True)
            )

            logger.info(
                f"🏢 Analyzed {len(sector_scores)} sectors for {sentiment.value}"
            )
            logger.info(
                f"🏢 Top 3 sectors: {list(sorted_sectors.keys())[:3]}"
            )
            return sorted_sectors

        except Exception as e:
            logger.error(f"❌ Error analyzing sector strength: {e}")
            return {}

    async def select_stocks_by_value(
        self, target_sectors: List[str], max_stocks: int = 5
    ) -> List[StockSelection]:
        """Select stocks based on highest value in target sectors - UPDATED to use realtime_market_engine"""
        try:
            if not self.market_engine:
                await self.initialize_services()

            selected_stocks = []

            for sector in target_sectors:
                if len(selected_stocks) >= max_stocks:
                    break

                # Get sector stocks from real-time market engine
                sector_stocks = get_sector_stocks(sector)
                stocks = sector_stocks.get(sector, [])

                if not stocks:
                    continue

                # Filter eligible stocks (F&O stocks only, no value filter)
                eligible_stocks = [
                    stock
                    for stock in stocks
                    if (
                        stock.get("volume", 0) >= self.selection_config["min_volume"]
                        and stock.get("ltp", 0) > 0
                        and stock.get("lot_size") is not None
                        and stock.get("lot_size", 0) > 0
                    )
                ]

                # Sort by value (highest first)
                eligible_stocks.sort(
                    key=lambda x: x.get("value_crores", 0), reverse=True
                )

                # Select top stock from this sector
                for stock in eligible_stocks[:2]:  # Max 2 per sector
                    if len(selected_stocks) >= max_stocks:
                        break

                    # Calculate selection scores
                    selection = await self._create_stock_selection(stock, sector)
                    if (
                        selection
                        and selection.final_score
                        > self.selection_config["min_score_threshold"]
                    ):
                        selected_stocks.append(selection)

            # Sort final selections by score
            selected_stocks.sort(key=lambda x: x.final_score, reverse=True)

            logger.info(
                f"📈 Selected {len(selected_stocks)} stocks: {[s.symbol for s in selected_stocks]}"
            )
            return selected_stocks[:max_stocks]

        except Exception as e:
            logger.error(f"❌ Error selecting stocks by value: {e}")
            return []

    async def _create_stock_selection(
        self, stock_data: Dict[str, Any], sector: str
    ) -> Optional[StockSelection]:
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
                sentiment_score * self.selection_config["sentiment_weight"]
                + sector_score * self.selection_config["sector_weight"]
                + technical_score * self.selection_config["technical_weight"]
                + volume_score * self.selection_config["volume_weight"]
                + value_score * self.selection_config["value_weight"]
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

        if self.current_sentiment in [
            MarketSentiment.BULLISH,
            MarketSentiment.VERY_BULLISH,
        ]:
            return min(
                max(change_percent / 5.0, 0), 1.0
            )  # Positive stocks score higher
        elif self.current_sentiment in [
            MarketSentiment.BEARISH,
            MarketSentiment.VERY_BEARISH,
        ]:
            return min(
                max(-change_percent / 5.0, 0), 1.0
            )  # Negative stocks score higher (short)
        else:
            return 0.5  # Neutral market

    def _calculate_sector_score(self, stock_data: Dict[str, Any], sector: str) -> float:
        """Calculate sector strength score - UPDATED to use realtime_market_engine"""
        try:
            sector_performance = get_sector_performance()
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
            return price_position * 0.6 + momentum_score * 0.4

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
        elif volume >= 500000:  # 5L+
            return 0.4
        else:
            return 0.2

    def _calculate_value_score(self, stock_data: Dict[str, Any]) -> float:
        """Calculate trading value score"""
        value_crores = stock_data.get("value_crores", 0)

        # Value categories
        if value_crores >= 100:  # 100Cr+
            return 1.0
        elif value_crores >= 50:  # 50Cr+
            return 0.8
        elif value_crores >= 10:  # 10Cr+
            return 0.6
        elif value_crores >= 5:  # 5Cr+
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
        current_sentiment = getattr(
            self, "market_open_sentiment", self.premarket_sentiment
        )

        if current_sentiment in [MarketSentiment.BULLISH, MarketSentiment.VERY_BULLISH]:
            return "CE"  # CALL options for positive market
        elif current_sentiment in [
            MarketSentiment.BEARISH,
            MarketSentiment.VERY_BEARISH,
        ]:
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
                    "existing_selections": [
                        asdict(stock) for stock in self.premarket_selections
                    ],
                    "phase": "premarket",
                }

            logger.info("🌅 Starting premarket stock selection...")

            # Analyze market sentiment and store it
            sentiment, sentiment_analysis = await self.analyze_market_sentiment()
            self.premarket_sentiment = sentiment

            # Analyze sector strength
            sector_scores = await self.analyze_sector_strength(sentiment)
            top_sectors = list(sector_scores.keys())[:3]

            # Check if we have any sectors with data
            if not top_sectors:
                logger.warning(
                    "⚠️ No sector data available - market engine waiting for live WebSocket feed"
                )
                return {
                    "error": "No market data available",
                    "phase": "premarket",
                    "message": "Realtime market engine has no data yet. Ensure WebSocket feed is connected and streaming.",
                    "timestamp": datetime.now().isoformat(),
                }

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
                "top_sectors": {
                    sector: sector_scores[sector] for sector in top_sectors
                },
                "selected_stocks": [asdict(stock) for stock in selected_stocks],
                "selection_count": len(selected_stocks),
                "next_validation": "09:15:00",
                "timestamp": datetime.now().isoformat(),
            }

            # Save to database for auto-trading integration
            try:
                saved = await self.save_selections_to_database(
                    selected_stocks, "premarket"
                )
                if saved:
                    result["database_saved"] = True
                    result["available_for_autotrading"] = True
                    logger.info(
                        "✅ Premarket selections saved to database for auto-trading"
                    )
                else:
                    result["database_saved"] = False
                    logger.warning("⚠️ Failed to save premarket selections to database")
            except Exception as db_error:
                logger.error(f"❌ Database save error: {db_error}")
                result["database_saved"] = False

            # Broadcast update via WebSocket
            # try:
            # from services.unified_websocket_manager import (
            #     emit_intelligent_stock_selection_update,
            # )

            # emit_intelligent_stock_selection_update(
            #     {
            #         "type": "premarket_selection_completed",
            #         "data": result,
            #         "timestamp": datetime.now().isoformat(),
            #     }
            # )
            # except Exception as ws_error:
            #     logger.warning(f"⚠️ Failed to broadcast premarket selection: {ws_error}")

            logger.info(
                f"✅ Premarket selection complete: {len(selected_stocks)} stocks selected"
            )
            return result

        except Exception as e:
            logger.error(f"❌ Error in premarket selection: {e}")
            return {"error": str(e), "phase": "premarket"}

    async def validate_market_open_selection(self) -> Dict[str, Any]:
        """Market open validation - Check sentiment and finalize selections (9:15-9:25) - FINAL DECISION"""
        try:
            logger.info(
                "🔍 Market open validation - Making FINAL stock selection for the day..."
            )

            # Check if final selection already done
            if self.final_selection_done:
                logger.warning(
                    "⚠️ Final selection already completed - no more changes today"
                )
                return {
                    "success": False,
                    "message": "Final selections already done today - no more changes allowed",
                    "final_selections": [
                        asdict(stock) for stock in self.final_selections
                    ],
                    "phase": "final_selection_done",
                }

            if not self.premarket_selections:
                return {
                    "error": "No premarket selections found. Run premarket selection first.",
                    "phase": "market_open_validation",
                }

            # Check current market sentiment at market open
            market_sentiment, sentiment_analysis = await self.analyze_market_sentiment()
            self.market_open_sentiment = market_sentiment

            # Compare sentiments
            self.sentiment_changed = market_sentiment != self.premarket_sentiment

            logger.info(f"📊 Premarket sentiment: {self.premarket_sentiment.value}")
            logger.info(f"📊 Market open sentiment: {market_sentiment.value}")
            logger.info(f"📊 Sentiment changed: {self.sentiment_changed}")

            # FINAL DECISION LOGIC
            if self.sentiment_changed:
                logger.info(
                    "🔄 Sentiment changed - Running NEW stock selection (FINAL)"
                )

                # Run completely fresh selection with new sentiment
                sector_scores = await self.analyze_sector_strength(market_sentiment)
                top_sectors = list(sector_scores.keys())[:3]
                final_selections = await self.select_stocks_by_value(top_sectors)

                self.final_selections = final_selections
                validation_action = "NEW_SELECTION_DUE_TO_SENTIMENT_CHANGE"
                selection_source = "market_open_fresh"

            else:
                logger.info(
                    "✅ Sentiment unchanged - Using premarket selections (FINAL)"
                )

                # Use premarket selections as final (no changes needed)
                self.final_selections = self.premarket_selections.copy()
                validation_action = "PREMARKET_SELECTIONS_CONFIRMED"
                selection_source = "premarket_confirmed"

            # MARK AS FINAL - NO MORE CHANGES ALLOWED
            self.final_selection_done = True
            self.current_phase = TradingPhase.MARKET_OPEN
            self.last_selection_time = datetime.now()

            logger.info(
                f"🎯 FINAL SELECTIONS CONFIRMED: {len(self.final_selections)} stocks selected for the day"
            )

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
                saved = await self.save_selections_to_database(
                    self.final_selections, "final_selection"
                )
                if saved:
                    result["database_saved"] = True
                    result["available_for_autotrading"] = True
                    logger.info(
                        "✅ Validated selections saved to database for auto-trading"
                    )
                else:
                    result["database_saved"] = False
                    logger.warning("⚠️ Failed to save validated selections to database")
            except Exception as db_error:
                logger.error(f"❌ Database save error: {db_error}")
                result["database_saved"] = False

            # Enhance final selections with option contracts
            try:
                logger.info("🎯 Enhancing final selections with option contracts...")
                from services.enhanced_intelligent_options_selection import (
                    enhanced_options_service,
                )

                options_result = (
                    await enhanced_options_service.enhance_selected_stocks_with_options(
                        self.final_selections, selection_type="final"
                    )
                )

                if options_result.get("success"):
                    result["options_enhancement"] = {
                        "enhanced_count": options_result.get(
                            "options_contracts_found", 0
                        ),
                        "total_capital_required": options_result.get(
                            "total_capital_required", 0
                        ),
                        "options_ready": options_result.get("options_ready", False),
                    }
                    logger.info(
                        f"✅ Options enhancement complete: {options_result.get('options_contracts_found', 0)} stocks enhanced"
                    )
                else:
                    logger.warning(
                        f"⚠️ Options enhancement failed: {options_result.get('error')}"
                    )
                    result["options_enhancement"] = {
                        "error": options_result.get("error")
                    }
            except Exception as opt_error:
                logger.error(f"❌ Error enhancing with options: {opt_error}")
                result["options_enhancement"] = {"error": str(opt_error)}

            # Broadcast update via WebSocket
            try:
                from services.unified_websocket_manager import (
                    emit_intelligent_stock_selection_update,
                )

                emit_intelligent_stock_selection_update(
                    {
                        "type": "market_open_validation_completed",
                        "data": result,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            except Exception as ws_error:
                logger.warning(
                    f"⚠️ Failed to broadcast market open validation: {ws_error}"
                )

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
                    "timestamp": datetime.now().isoformat(),
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

            logger.info(
                f"📊 Returning FINAL selections: {len(self.final_selections)} stocks"
            )
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
            "last_selection_time": (
                self.last_selection_time.isoformat()
                if self.last_selection_time
                else None
            ),
            "next_action": self._get_next_action_recommendation(current_phase),
            "workflow_complete": self.final_selection_done,
            "timestamp": datetime.now().isoformat(),
        }

    async def save_selections_to_database(
        self, selections: List[StockSelection], selection_type: str = "intelligent"
    ) -> bool:
        """
        Save selected stocks to database with complete market sentiment and advance/decline data.

        Stores:
        - Stock selection details (symbol, score, sector)
        - Market sentiment at time of selection (bullish/bearish/neutral)
        - Advance/decline ratio and market breadth
        - Options trading direction (CE for bullish, PE for bearish)
        """
        try:
            db = SessionLocal()
            today = date.today()

            # Get current market sentiment for database storage
            sentiment_data = get_market_sentiment()

            # Clear existing intelligent selections for today (if any)
            db.query(SelectedStock).filter(
                SelectedStock.selection_date == today,
                SelectedStock.selection_reason.like(f"{selection_type}%"),
            ).delete()

            # Determine selection phase
            selection_phase = (
                "premarket" if selection_type == "premarket" else "final_selection"
            )

            # Save new selections with complete market context
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
                    # Market Sentiment Data - CRITICAL for options trading direction
                    market_sentiment=sentiment_data.get("sentiment", "neutral"),
                    market_sentiment_confidence=sentiment_data.get("confidence", 50),
                    advance_decline_ratio=sentiment_data.get("metrics", {}).get(
                        "advance_decline_ratio", 1.0
                    ),
                    market_breadth_percent=sentiment_data.get("metrics", {}).get(
                        "market_breadth_percent", 0
                    ),
                    advancing_stocks=sentiment_data.get("metrics", {}).get(
                        "advancing", 0
                    ),
                    declining_stocks=sentiment_data.get("metrics", {}).get(
                        "declining", 0
                    ),
                    total_stocks_analyzed=sentiment_data.get("metrics", {}).get(
                        "total_stocks", 0
                    ),
                    selection_phase=selection_phase,
                    # Options Direction - CE for bullish market, PE for bearish market
                    option_type=stock.options_direction,  # CE or PE based on market sentiment
                    score_breakdown=str(
                        {
                            "sentiment_score": stock.sentiment_score,
                            "sector_score": stock.sector_score,
                            "technical_score": stock.technical_score,
                            "volume_score": stock.volume_score,
                            "value_score": stock.value_score,
                            "final_score": stock.final_score,
                            "confidence_level": stock.confidence_level,
                            "risk_level": stock.risk_level,
                            "options_direction": stock.options_direction,  # CE or PE
                            "market_sentiment_at_selection": sentiment_data.get(
                                "sentiment", "neutral"
                            ),
                        }
                    ),
                    is_active=True,
                )
                db.add(selected_stock)

            db.commit()
            logger.info(
                f"✅ Saved {len(selections)} intelligent stock selections to database"
            )
            logger.info(
                f"📊 Market Context: {sentiment_data.get('sentiment')} sentiment, A/D ratio: {sentiment_data.get('metrics', {}).get('advance_decline_ratio', 1.0):.2f}"
            )
            logger.info(
                f"📈 Options Direction: {selections[0].options_direction if selections else 'N/A'} (based on market sentiment)"
            )
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
            TradingPhase.POST_MARKET: "💤 Wait for next trading day",
        }
        return recommendations.get(phase, "Monitor market conditions")


# Create singleton instance
intelligent_stock_selector = IntelligentStockSelectionService()
