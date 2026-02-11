from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseStrategy(ABC):
    """
    Abstract Base Class for Hot-Swappable Strategies.
    All new strategies must inherit from this to be compatible with the Registry.
    """

    @abstractmethod
    def get_name(self) -> str:
        """Return the unique name of the strategy (e.g., 'supertrend_ema')"""
        pass

    @abstractmethod
    def generate_signal(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Core logic to generate a BUY/SELL/HOLD signal.
        
        Args:
            market_data: Dictionary containing 'ohlc', 'ltp', 'volume', etc.
            
        Returns:
            Dict containing:
            - signal: "BUY" | "SELL" | "HOLD"
            - confidence: float (0.0 to 1.0)
            - metadata: Dict (indicators used, reasoning)
        """
        pass

    @abstractmethod
    def get_required_indicators(self) -> list:
        """Return list of indicators this strategy needs (e.g., ['rsi', 'ema'])"""
        pass
