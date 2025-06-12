import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import logging

from database.models import Stock, User, TradeSignal
from database.connection import get_db

logger = logging.getLogger(__name__)


class StockScreeningService:
    def __init__(self):
        self.screening_criteria = {
            "min_volume": 100000,
            "min_price": 10,
            "max_price": 5000,
            "min_market_cap": 1000,  # Crores
            "volatility_threshold": 0.02,
        }

    def screen_stocks(self, sector: Optional[str] = None) -> List[Dict]:
        """Screen stocks based on technical and fundamental criteria"""
        db = next(get_db())
        try:
            # Get stocks from database
            query = db.query(Stock)
            if sector:
                # Add sector filter if available in your Stock model
                pass

            stocks = query.filter(Stock.exchange == "NSE").all()
            screened_stocks = []

            for stock in stocks:
                try:
                    analysis = self._analyze_stock(stock.symbol)
                    if analysis and analysis["score"] > 60:  # 60% threshold
                        screened_stocks.append(
                            {
                                "symbol": stock.symbol,
                                "name": stock.name,
                                "exchange": stock.exchange,
                                "analysis": analysis,
                                "recommendation": self._get_recommendation(analysis),
                            }
                        )
                except Exception as e:
                    logger.warning(f"Error analyzing {stock.symbol}: {e}")
                    continue

            # Sort by score
            screened_stocks.sort(key=lambda x: x["analysis"]["score"], reverse=True)
            return screened_stocks[:20]  # Top 20 stocks

        finally:
            db.close()

    def _analyze_stock(self, symbol: str) -> Optional[Dict]:
        """Comprehensive stock analysis"""
        try:
            # Fetch data
            ticker = yf.Ticker(f"{symbol}.NS")
            data = ticker.history(period="90d")
            info = ticker.info

            if len(data) < 30:
                return None

            # Technical Analysis
            technical_score = self._technical_analysis(data)

            # Fundamental Analysis
            fundamental_score = self._fundamental_analysis(info, data)

            # Volume Analysis
            volume_score = self._volume_analysis(data)

            # Overall Score
            overall_score = (
                technical_score * 0.5 + fundamental_score * 0.3 + volume_score * 0.2
            )

            current_price = data["Close"].iloc[-1]

            return {
                "symbol": symbol,
                "current_price": round(float(current_price), 2),
                "technical_score": round(technical_score, 2),
                "fundamental_score": round(fundamental_score, 2),
                "volume_score": round(volume_score, 2),
                "score": round(overall_score, 2),
                "indicators": self._get_technical_indicators(data),
                "risk_metrics": self._calculate_risk_metrics(data),
                "support_resistance": self._find_support_resistance(data),
                "trend": self._identify_trend(data),
                "volatility": round(float(data["Close"].pct_change().std() * 100), 2),
            }

        except Exception as e:
            logger.error(f"Error in stock analysis for {symbol}: {e}")
            return None

    def _technical_analysis(self, data: pd.DataFrame) -> float:
        """Technical analysis scoring"""
        score = 0

        # Moving Averages
        data["SMA_20"] = data["Close"].rolling(20).mean()
        data["SMA_50"] = data["Close"].rolling(50).mean()
        data["EMA_12"] = data["Close"].ewm(span=12).mean()
        data["EMA_26"] = data["Close"].ewm(span=26).mean()

        current_price = data["Close"].iloc[-1]
        sma_20 = data["SMA_20"].iloc[-1]
        sma_50 = data["SMA_50"].iloc[-1]

        # Price above moving averages
        if current_price > sma_20:
            score += 20
        if current_price > sma_50:
            score += 15
        if sma_20 > sma_50:
            score += 15

        # RSI Analysis
        rsi = self._calculate_rsi(data["Close"])
        current_rsi = rsi.iloc[-1]
        if 30 < current_rsi < 70:
            score += 20
        elif current_rsi < 30:
            score += 10  # Oversold - potential buy

        # MACD Analysis
        macd_line = data["EMA_12"] - data["EMA_26"]
        signal_line = macd_line.ewm(span=9).mean()
        if macd_line.iloc[-1] > signal_line.iloc[-1]:
            score += 15

        # Volume confirmation
        avg_volume = data["Volume"].rolling(20).mean().iloc[-1]
        recent_volume = data["Volume"].iloc[-1]
        if recent_volume > avg_volume * 1.2:
            score += 15

        return min(score, 100)

    def _fundamental_analysis(self, info: Dict, data: pd.DataFrame) -> float:
        """Fundamental analysis scoring"""
        score = 0

        try:
            # Market Cap
            market_cap = info.get("marketCap", 0)
            if market_cap > 10000000000:  # > 1000 Cr
                score += 20
            elif market_cap > 1000000000:  # > 100 Cr
                score += 10

            # P/E Ratio
            pe_ratio = info.get("forwardPE", info.get("trailingPE", 0))
            if 10 < pe_ratio < 25:
                score += 20
            elif 5 < pe_ratio < 35:
                score += 10

            # Debt to Equity
            debt_to_equity = info.get("debtToEquity", 0)
            if debt_to_equity < 0.5:
                score += 15
            elif debt_to_equity < 1.0:
                score += 10

            # Return on Equity
            roe = info.get("returnOnEquity", 0)
            if roe > 0.15:
                score += 15
            elif roe > 0.10:
                score += 10

            # Profit Margins
            profit_margin = info.get("profitMargins", 0)
            if profit_margin > 0.10:
                score += 15
            elif profit_margin > 0.05:
                score += 10

            # 52-week performance
            current_price = data["Close"].iloc[-1]
            high_52w = info.get("fiftyTwoWeekHigh", current_price)
            low_52w = info.get("fiftyTwoWeekLow", current_price)

            position_in_range = (current_price - low_52w) / (high_52w - low_52w)
            if 0.3 < position_in_range < 0.8:
                score += 10

        except Exception as e:
            logger.warning(f"Fundamental analysis error: {e}")

        return min(score, 100)

    def _volume_analysis(self, data: pd.DataFrame) -> float:
        """Volume analysis scoring"""
        score = 0

        # Average volume
        avg_volume_20 = data["Volume"].rolling(20).mean()
        recent_volume = data["Volume"].iloc[-5:].mean()

        if recent_volume > avg_volume_20.iloc[-1] * 1.5:
            score += 30  # High volume surge
        elif recent_volume > avg_volume_20.iloc[-1] * 1.2:
            score += 20  # Good volume
        elif recent_volume > avg_volume_20.iloc[-1]:
            score += 10  # Above average

        # Volume trend
        volume_trend = data["Volume"].rolling(5).mean().pct_change().iloc[-1]
        if volume_trend > 0.1:
            score += 20
        elif volume_trend > 0:
            score += 10

        # Price-Volume correlation
        price_change = data["Close"].pct_change().iloc[-5:].mean()
        volume_change = data["Volume"].pct_change().iloc[-5:].mean()

        if (price_change > 0 and volume_change > 0) or (
            price_change < 0 and volume_change < 0
        ):
            score += 30  # Good correlation

        return min(score, 100)

    def _get_technical_indicators(self, data: pd.DataFrame) -> Dict:
        """Calculate all technical indicators"""
        current_price = data["Close"].iloc[-1]

        # Moving Averages
        sma_20 = data["Close"].rolling(20).mean().iloc[-1]
        sma_50 = data["Close"].rolling(50).mean().iloc[-1]
        ema_12 = data["Close"].ewm(span=12).mean().iloc[-1]

        # RSI
        rsi = self._calculate_rsi(data["Close"]).iloc[-1]

        # MACD
        ema_26 = data["Close"].ewm(span=26).mean()
        macd_line = ema_12 - ema_26.iloc[-1]
        signal_line = (ema_12 - ema_26).ewm(span=9).mean().iloc[-1]

        # Bollinger Bands
        bb_middle = data["Close"].rolling(20).mean().iloc[-1]
        bb_std = data["Close"].rolling(20).std().iloc[-1]
        bb_upper = bb_middle + (bb_std * 2)
        bb_lower = bb_middle - (bb_std * 2)

        return {
            "sma_20": round(float(sma_20), 2),
            "sma_50": round(float(sma_50), 2),
            "ema_12": round(float(ema_12), 2),
            "rsi": round(float(rsi), 2),
            "macd": round(float(macd_line), 2),
            "macd_signal": round(float(signal_line), 2),
            "bb_upper": round(float(bb_upper), 2),
            "bb_middle": round(float(bb_middle), 2),
            "bb_lower": round(float(bb_lower), 2),
            "bb_position": round(
                float((current_price - bb_lower) / (bb_upper - bb_lower) * 100), 2
            ),
        }

    def _calculate_risk_metrics(self, data: pd.DataFrame) -> Dict:
        """Calculate risk metrics"""
        returns = data["Close"].pct_change().dropna()

        # Volatility (annualized)
        volatility = returns.std() * np.sqrt(252) * 100

        # Value at Risk (95% confidence)
        var_95 = np.percentile(returns, 5) * 100

        # Maximum Drawdown
        rolling_max = data["Close"].expanding().max()
        drawdown = (data["Close"] - rolling_max) / rolling_max
        max_drawdown = drawdown.min() * 100

        # Sharpe Ratio (assuming risk-free rate of 6%)
        excess_returns = returns.mean() * 252 - 0.06
        sharpe_ratio = (
            excess_returns / (returns.std() * np.sqrt(252)) if returns.std() != 0 else 0
        )

        return {
            "volatility": round(float(volatility), 2),
            "var_95": round(float(var_95), 2),
            "max_drawdown": round(float(max_drawdown), 2),
            "sharpe_ratio": round(float(sharpe_ratio), 2),
        }

    def _find_support_resistance(self, data: pd.DataFrame) -> Dict:
        """Find support and resistance levels"""
        highs = data["High"].rolling(window=10, center=True).max()
        lows = data["Low"].rolling(window=10, center=True).min()

        # Resistance levels (recent highs)
        resistance_levels = data[data["High"] == highs]["High"].tail(3).tolist()

        # Support levels (recent lows)
        support_levels = data[data["Low"] == lows]["Low"].tail(3).tolist()

        return {
            "resistance": [round(float(r), 2) for r in resistance_levels],
            "support": [round(float(s), 2) for s in support_levels],
        }

    def _identify_trend(self, data: pd.DataFrame) -> str:
        """Identify current trend"""
        sma_20 = data["Close"].rolling(20).mean()
        sma_50 = data["Close"].rolling(50).mean()

        current_price = data["Close"].iloc[-1]
        sma_20_current = sma_20.iloc[-1]
        sma_50_current = sma_50.iloc[-1]

        if current_price > sma_20_current > sma_50_current:
            return "STRONG_UPTREND"
        elif current_price > sma_20_current:
            return "UPTREND"
        elif current_price < sma_20_current < sma_50_current:
            return "STRONG_DOWNTREND"
        elif current_price < sma_20_current:
            return "DOWNTREND"
        else:
            return "SIDEWAYS"

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _get_recommendation(self, analysis: Dict) -> Dict:
        """Get trading recommendation based on analysis"""
        score = analysis["score"]
        trend = analysis["trend"]
        rsi = analysis["indicators"]["rsi"]

        if score > 75 and trend in ["UPTREND", "STRONG_UPTREND"] and rsi < 70:
            action = "STRONG_BUY"
            confidence = 90
        elif score > 60 and trend in ["UPTREND", "STRONG_UPTREND"] and rsi < 75:
            action = "BUY"
            confidence = 75
        elif score > 40 and trend == "SIDEWAYS":
            action = "HOLD"
            confidence = 50
        elif score < 40 and trend in ["DOWNTREND", "STRONG_DOWNTREND"]:
            action = "SELL"
            confidence = 70
        else:
            action = "HOLD"
            confidence = 40

        return {
            "action": action,
            "confidence": confidence,
            "reasoning": self._get_reasoning(analysis),
        }

    def _get_reasoning(self, analysis: Dict) -> List[str]:
        """Get reasoning for recommendation"""
        reasons = []

        if analysis["score"] > 70:
            reasons.append(f"High overall score ({analysis['score']}/100)")

        if analysis["trend"] in ["UPTREND", "STRONG_UPTREND"]:
            reasons.append(f"Stock in {analysis['trend'].lower().replace('_', ' ')}")

        rsi = analysis["indicators"]["rsi"]
        if rsi < 30:
            reasons.append("RSI indicates oversold condition")
        elif rsi > 70:
            reasons.append("RSI indicates overbought condition")

        if analysis["volatility"] < 2:
            reasons.append("Low volatility - stable stock")
        elif analysis["volatility"] > 5:
            reasons.append("High volatility - risky but potential for high returns")

        return reasons
