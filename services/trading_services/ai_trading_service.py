"""
Enhanced AI Trading Service with Centralized WebSocket Support

This service handles AI-based trading strategies, now with support
for the centralized WebSocket manager.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class AITradingService:
    """AI Trading Service with enhanced real-time data capabilities"""

    def __init__(self):
        """Initialize AI Trading Service"""
        self.is_running = False
        self.selected_stocks = {}
        self.data_service = None
        self.centralized_manager = None
        self.strategy_engines = {}
        self.price_history = {}  # Symbol -> [prices]
        self.strategy_results = {}  # Symbol -> latest result

    async def start_trading(
        self, selected_stocks: Dict, data_service=None, centralized_manager=None
    ):
        """
        Start AI trading with selected stocks

        Now supports both legacy data service and centralized WebSocket manager
        """
        try:
            logger.info("🤖 Starting AI Trading Service...")

            # Store references
            self.selected_stocks = selected_stocks
            self.data_service = data_service
            self.centralized_manager = centralized_manager
            self.is_running = True

            # Initialize price history
            for symbol in selected_stocks:
                self.price_history[symbol] = []
                self.strategy_results[symbol] = {
                    "recommendation": "HOLD",
                    "confidence": 0.0,
                    "last_update": datetime.now().isoformat(),
                }

            # Log data source
            if centralized_manager:
                logger.info("📊 Using centralized WebSocket manager for real-time data")

                # If using centralized manager, we don't need to register any callbacks
                # as the TradingEngine will forward price updates to us
            else:
                logger.info("📊 Using legacy data service for real-time data")

            logger.info(f"🚀 AI Trading started for {len(selected_stocks)} stocks")
            return {"status": "success", "stocks_count": len(selected_stocks)}

        except Exception as e:
            logger.error(f"❌ Failed to start AI trading: {e}")
            return {"status": "error", "message": str(e)}

    async def process_price_update(self, symbol: str, price: float, price_data: Dict):
        """
        Process price update from centralized WebSocket manager

        This method is called by the TradingEngine when it receives a price update
        """
        try:
            if not self.is_running or symbol not in self.selected_stocks:
                return

            # Update price history
            self.price_history[symbol].append(
                {"price": price, "timestamp": datetime.now().isoformat()}
            )

            # Keep history size manageable
            if len(self.price_history[symbol]) > 1000:
                self.price_history[symbol] = self.price_history[symbol][-1000:]

            # Execute AI strategy on price update (not every update)
            # Only run strategies periodically to avoid excessive CPU usage
            if len(self.price_history[symbol]) % 20 == 0:  # Every 20th update
                await self._execute_ai_strategy(symbol, price, price_data)

        except Exception as e:
            logger.error(f"❌ Error processing price update for {symbol}: {e}")

    async def _execute_ai_strategy(self, symbol: str, price: float, price_data: Dict):
        """Execute AI trading strategy for a stock"""
        try:
            # Get stock data
            stock_data = self.selected_stocks.get(symbol, {})

            # Execute strategy
            # This is a placeholder - implement your actual strategy here
            result = await self._run_strategy(symbol, price, stock_data, price_data)

            # Store result
            self.strategy_results[symbol] = {
                "recommendation": result.get("recommendation", "HOLD"),
                "confidence": result.get("confidence", 0.0),
                "signals": result.get("signals", {}),
                "last_update": datetime.now().isoformat(),
            }

            # Log significant recommendations
            if result.get("confidence", 0) > 0.7:
                logger.info(
                    f"🤖 AI {result['recommendation']} signal for {symbol} with {result['confidence']:.2f} confidence"
                )

        except Exception as e:
            logger.error(f"❌ Strategy execution error for {symbol}: {e}")

    async def _run_strategy(
        self, symbol: str, price: float, stock_data: Dict, price_data: Dict
    ):
        """
        Run AI trading strategy (placeholder)

        This is where you would implement your actual trading strategy
        """
        # Placeholder for actual AI strategy
        # In a real implementation, this would use ML models, technical indicators, etc.

        # Simple moving average example
        prices = [entry["price"] for entry in self.price_history[symbol][-50:]]
        if len(prices) < 50:
            return {
                "recommendation": "HOLD",
                "confidence": 0.5,
                "signals": {"insufficient_data": True},
            }

        # Calculate short and long moving averages
        short_ma = sum(prices[-20:]) / 20
        long_ma = sum(prices) / len(prices)

        # Simple strategy based on MA crossover
        confidence = min(0.5 + abs(short_ma - long_ma) / price * 10, 0.95)

        if short_ma > long_ma:
            # Bullish
            return {
                "recommendation": "BUY",
                "confidence": confidence,
                "signals": {
                    "short_ma": short_ma,
                    "long_ma": long_ma,
                    "price": price,
                    "trend": "bullish",
                },
            }
        else:
            # Bearish
            return {
                "recommendation": "SELL",
                "confidence": confidence,
                "signals": {
                    "short_ma": short_ma,
                    "long_ma": long_ma,
                    "price": price,
                    "trend": "bearish",
                },
            }

    async def get_trading_recommendations(self) -> Dict[str, Dict]:
        """Get current AI trading recommendations"""
        return {
            symbol: self.strategy_results.get(
                symbol, {"recommendation": "HOLD", "confidence": 0.0}
            )
            for symbol in self.selected_stocks
        }

    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get latest price for a symbol"""
        # First try price history
        if symbol in self.price_history and self.price_history[symbol]:
            return self.price_history[symbol][-1]["price"]

        # Then try centralized manager
        if self.centralized_manager and symbol in self.selected_stocks:
            instrument_key = (
                self.selected_stocks[symbol].get("stock_data", {}).get("instrument_key")
            )
            if instrument_key:
                return self.centralized_manager.get_latest_price(instrument_key)

        # Finally try legacy service
        if self.data_service:
            return self.data_service.get_latest_price(symbol)

        return None

    async def stop_trading(self):
        """Stop AI trading"""
        logger.info("🛑 Stopping AI Trading Service...")
        self.is_running = False
        # Cleanup resources
        self.selected_stocks = {}
        self.data_service = None
        self.centralized_manager = None
        logger.info("✅ AI Trading Service stopped")
        return {"status": "success"}
