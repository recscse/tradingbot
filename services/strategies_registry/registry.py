from typing import Dict, Type
from .base_strategy import BaseStrategy
import logging

logger = logging.getLogger(__name__)

class StrategyRegistry:
    """
    Central Registry for managing Hot-Swappable Strategies.
    Allows registering, retrieving, and listing available strategies at runtime.
    """
    _instance = None
    _strategies: Dict[str, BaseStrategy] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StrategyRegistry, cls).__new__(cls)
        return cls._instance

    def register(self, strategy: BaseStrategy):
        """Register a new strategy instance"""
        if not isinstance(strategy, BaseStrategy):
            raise ValueError("Strategy must inherit from BaseStrategy")
        
        name = strategy.get_name()
        self._strategies[name] = strategy
        logger.info(f"✅ Strategy Registered: {name}")

    def get_strategy(self, name: str) -> BaseStrategy:
        """Get a strategy by name"""
        return self._strategies.get(name)

    def list_strategies(self) -> list:
        """List all available strategy names"""
        return list(self._strategies.keys())

    def execute_strategy(self, name: str, market_data: Dict) -> Dict:
        """Execute a specific strategy safely"""
        strategy = self.get_strategy(name)
        if not strategy:
            return {"error": f"Strategy '{name}' not found"}
        
        try:
            return strategy.generate_signal(market_data)
        except Exception as e:
            logger.error(f"❌ Error executing strategy {name}: {e}")
            return {"error": str(e)}

# Global Instance
strategy_registry = StrategyRegistry()
