"""
Strategy Data Service - Real-Time Price Access for Trading Strategies

This service provides zero-delay access to live market data for algorithmic trading strategies.
It integrates with the enhanced Instrument Registry for ultra-fast price access.

Key Features:
- Zero-delay real-time price access
- Strategy-specific callback registration  
- Portfolio-level data access
- Price freshness validation
- Performance optimization for trading

Usage:
    from services.strategy_data_service import get_strategy_data_service
    
    # Create service for your strategy
    data_service = get_strategy_data_service("momentum_strategy_v1")
    
    # Subscribe to instruments
    instruments = ["NSE_EQ|INE002A01018", "NSE_EQ|INE467B01029"]
    data_service.subscribe_to_instruments(instruments)
    
    # Set real-time callback
    def on_price_update(instrument_key: str, price_data: dict):
        current_price = price_data.get('ltp', 0)
        # Apply your trading logic here
        
    data_service.set_price_callback(on_price_update)
    
    # Get current prices
    current_price = data_service.get_current_price("NSE_EQ|INE002A01018")
    portfolio_prices = data_service.get_portfolio_prices(instruments)
"""

import asyncio
import logging
import time
from typing import List, Dict, Any, Optional, Callable, Union
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class StrategyDataService:
    """
    High-performance data access service for trading strategies
    Provides zero-delay access to real-time market data
    """
    
    def __init__(self, strategy_name: str):
        self.strategy_name = strategy_name
        self.subscribed_instruments = set()
        self.callback_function = None
        self.is_active = False
        
        # Performance tracking
        self.price_requests = 0
        self.cache_hits = 0
        self.callback_executions = 0
        self.last_performance_log = time.time()
        
        # Get instrument registry instance
        try:
            from services.instrument_registry import instrument_registry
            self.registry = instrument_registry
            logger.info(f"✅ Strategy Data Service '{strategy_name}' initialized")
        except ImportError as e:
            logger.error(f"❌ Failed to import instrument_registry: {e}")
            raise
    
    def subscribe_to_instruments(self, instrument_keys: List[str]) -> bool:
        """
        Subscribe to real-time price updates for specific instruments
        
        Args:
            instrument_keys: List of instrument keys to subscribe to
            
        Returns:
            bool: True if subscription successful
        """
        try:
            if not instrument_keys:
                logger.warning(f"No instruments provided for strategy {self.strategy_name}")
                return False
            
            # Add new instruments to subscription set
            new_instruments = set(instrument_keys) - self.subscribed_instruments
            self.subscribed_instruments.update(instrument_keys)
            
            # Register with instrument registry for callbacks
            if self.callback_function and new_instruments:
                success = self.registry.register_strategy_callback(
                    self.strategy_name,
                    list(self.subscribed_instruments),
                    self._internal_callback
                )
                
                if success:
                    self.is_active = True
                    logger.info(
                        f"✅ Strategy '{self.strategy_name}' subscribed to "
                        f"{len(self.subscribed_instruments)} instruments "
                        f"({len(new_instruments)} new)"
                    )
                    return True
                else:
                    logger.error(f"❌ Failed to register strategy callback for {self.strategy_name}")
                    return False
            else:
                # Store instruments but wait for callback to be set
                logger.info(
                    f"📊 Strategy '{self.strategy_name}' will subscribe to "
                    f"{len(self.subscribed_instruments)} instruments when callback is set"
                )
                return True
                
        except Exception as e:
            logger.error(f"❌ Error subscribing to instruments for {self.strategy_name}: {e}")
            return False
    
    def set_price_callback(self, callback: Callable[[str, Dict[str, Any]], None]) -> bool:
        """
        Set callback function for real-time price updates
        
        Args:
            callback: Function to call when price updates (instrument_key, price_data)
            
        Returns:
            bool: True if callback registration successful
        """
        try:
            if not callable(callback):
                logger.error(f"❌ Invalid callback provided for strategy {self.strategy_name}")
                return False
            
            self.callback_function = callback
            
            # If instruments are already subscribed, register with registry
            if self.subscribed_instruments:
                success = self.registry.register_strategy_callback(
                    self.strategy_name,
                    list(self.subscribed_instruments), 
                    self._internal_callback
                )
                
                if success:
                    self.is_active = True
                    logger.info(
                        f"✅ Strategy '{self.strategy_name}' callback registered for "
                        f"{len(self.subscribed_instruments)} instruments"
                    )
                    return True
                else:
                    logger.error(f"❌ Failed to register strategy callback for {self.strategy_name}")
                    return False
            else:
                logger.info(f"📊 Strategy '{self.strategy_name}' callback set, waiting for instruments")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error setting callback for strategy {self.strategy_name}: {e}")
            return False
    
    def _internal_callback(self, instrument_key: str, price_data: Dict[str, Any]):
        """Internal callback that wraps user callback with error handling and performance tracking"""
        try:
            self.callback_executions += 1
            
            if self.callback_function:
                # Call user's callback function
                self.callback_function(instrument_key, price_data)
            
            # Performance logging every 100 callbacks
            if self.callback_executions % 100 == 0:
                current_time = time.time()
                time_diff = current_time - self.last_performance_log
                
                if time_diff > 0:
                    callbacks_per_second = 100 / time_diff
                    logger.debug(
                        f"🚀 Strategy '{self.strategy_name}' performance: "
                        f"{callbacks_per_second:.1f} callbacks/sec"
                    )
                    self.last_performance_log = current_time
                    
        except Exception as e:
            logger.error(
                f"❌ Error in strategy callback for {self.strategy_name}: {e}"
            )
    
    def get_current_price(self, instrument_key: str) -> Optional[float]:
        """
        Get current live price for an instrument - ultra fast access
        
        Args:
            instrument_key: Instrument identifier
            
        Returns:
            float: Current LTP or None if not available
        """
        try:
            self.price_requests += 1
            return self.registry.get_real_time_price(instrument_key)
            
        except Exception as e:
            logger.error(f"❌ Error getting price for {instrument_key}: {e}")
            return None
    
    def get_current_data(self, instrument_key: str) -> Optional[Dict[str, Any]]:
        """
        Get complete current data for an instrument
        
        Args:
            instrument_key: Instrument identifier
            
        Returns:
            dict: Complete price data or None if not available
        """
        try:
            self.price_requests += 1
            price_data = self.registry.get_spot_price_by_key(instrument_key)
            return price_data
            
        except Exception as e:
            logger.error(f"❌ Error getting data for {instrument_key}: {e}")
            return None
    
    def get_portfolio_prices(self, instrument_keys: List[str] = None) -> Dict[str, float]:
        """
        Get current prices for multiple instruments - batch optimized
        
        Args:
            instrument_keys: List of instruments (defaults to subscribed instruments)
            
        Returns:
            dict: {instrument_key: price} mapping
        """
        try:
            self.price_requests += 1
            
            if instrument_keys is None:
                instrument_keys = list(self.subscribed_instruments)
            
            if not instrument_keys:
                return {}
            
            return self.registry.get_strategy_prices(instrument_keys)
            
        except Exception as e:
            logger.error(f"❌ Error getting portfolio prices: {e}")
            return {}
    
    def is_instrument_active(self, instrument_key: str, max_age_seconds: int = 30) -> bool:
        """
        Check if instrument is receiving live updates
        
        Args:
            instrument_key: Instrument identifier
            max_age_seconds: Maximum age for fresh data
            
        Returns:
            bool: True if data is fresh
        """
        try:
            return self.registry.is_price_fresh(instrument_key, max_age_seconds)
            
        except Exception as e:
            logger.error(f"❌ Error checking instrument activity for {instrument_key}: {e}")
            return False
    
    def get_portfolio_status(self) -> Dict[str, Any]:
        """
        Get comprehensive status of subscribed portfolio
        
        Returns:
            dict: Portfolio status including active instruments, prices, etc.
        """
        try:
            portfolio_prices = self.get_portfolio_prices()
            active_instruments = []
            inactive_instruments = []
            
            for instrument_key in self.subscribed_instruments:
                if self.is_instrument_active(instrument_key):
                    active_instruments.append(instrument_key)
                else:
                    inactive_instruments.append(instrument_key)
            
            return {
                'strategy_name': self.strategy_name,
                'total_instruments': len(self.subscribed_instruments),
                'active_instruments': len(active_instruments),
                'inactive_instruments': len(inactive_instruments),
                'price_coverage': len(portfolio_prices) / len(self.subscribed_instruments) if self.subscribed_instruments else 0,
                'is_active': self.is_active,
                'callback_executions': self.callback_executions,
                'price_requests': self.price_requests,
                'cache_hit_rate': self.cache_hits / max(self.price_requests, 1),
                'active_instrument_keys': active_instruments,
                'inactive_instrument_keys': inactive_instruments,
                'portfolio_prices': portfolio_prices,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting portfolio status for {self.strategy_name}: {e}")
            return {'error': str(e)}
    
    def add_instruments(self, instrument_keys: List[str]) -> bool:
        """Add more instruments to existing subscription"""
        return self.subscribe_to_instruments(instrument_keys)
    
    def remove_instruments(self, instrument_keys: List[str]) -> bool:
        """Remove instruments from subscription"""
        try:
            self.subscribed_instruments -= set(instrument_keys)
            logger.info(
                f"✅ Removed {len(instrument_keys)} instruments from strategy '{self.strategy_name}'"
            )
            return True
            
        except Exception as e:
            logger.error(f"❌ Error removing instruments from {self.strategy_name}: {e}")
            return False
    
    def stop(self) -> bool:
        """Stop the strategy data service and cleanup resources"""
        try:
            self.is_active = False
            self.subscribed_instruments.clear()
            self.callback_function = None
            
            logger.info(f"✅ Strategy Data Service '{self.strategy_name}' stopped")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error stopping strategy {self.strategy_name}: {e}")
            return False


# Factory function and registry for strategy services
_strategy_services: Dict[str, StrategyDataService] = {}

def get_strategy_data_service(strategy_name: str) -> StrategyDataService:
    """
    Factory function to get or create a strategy data service
    
    Args:
        strategy_name: Unique name for the strategy
        
    Returns:
        StrategyDataService: Service instance for the strategy
    """
    if strategy_name not in _strategy_services:
        _strategy_services[strategy_name] = StrategyDataService(strategy_name)
        logger.info(f"🏭 Created new strategy data service: {strategy_name}")
    
    return _strategy_services[strategy_name]

def get_all_strategy_services() -> Dict[str, StrategyDataService]:
    """Get all active strategy services"""
    return dict(_strategy_services)

def stop_strategy_service(strategy_name: str) -> bool:
    """Stop and remove a strategy service"""
    if strategy_name in _strategy_services:
        service = _strategy_services[strategy_name]
        success = service.stop()
        if success:
            del _strategy_services[strategy_name]
            logger.info(f"🛑 Strategy service '{strategy_name}' stopped and removed")
        return success
    
    logger.warning(f"⚠️ Strategy service '{strategy_name}' not found")
    return False

def stop_all_strategy_services() -> int:
    """Stop all strategy services"""
    stopped_count = 0
    
    for strategy_name in list(_strategy_services.keys()):
        if stop_strategy_service(strategy_name):
            stopped_count += 1
    
    logger.info(f"🛑 Stopped {stopped_count} strategy services")
    return stopped_count

def get_strategy_performance_summary() -> Dict[str, Any]:
    """Get performance summary for all strategies"""
    try:
        summary = {
            'total_strategies': len(_strategy_services),
            'active_strategies': 0,
            'total_instruments': 0,
            'total_callbacks': 0,
            'total_price_requests': 0,
            'strategies': {}
        }
        
        for name, service in _strategy_services.items():
            status = service.get_portfolio_status()
            
            if status.get('is_active'):
                summary['active_strategies'] += 1
            
            summary['total_instruments'] += status.get('total_instruments', 0)
            summary['total_callbacks'] += status.get('callback_executions', 0)
            summary['total_price_requests'] += status.get('price_requests', 0)
            summary['strategies'][name] = status
        
        return summary
        
    except Exception as e:
        logger.error(f"❌ Error getting strategy performance summary: {e}")
        return {'error': str(e)}


# Utility functions for common strategy patterns

def create_momentum_strategy_service(
    strategy_name: str,
    fno_symbols: List[str] = None,
    callback: Callable = None
) -> StrategyDataService:
    """
    Create a momentum strategy service with FNO stocks
    
    Args:
        strategy_name: Name for the strategy
        fno_symbols: List of FNO stock symbols (will convert to instrument keys)
        callback: Price update callback function
        
    Returns:
        StrategyDataService: Configured service
    """
    try:
        service = get_strategy_data_service(strategy_name)
        
        # Default FNO stocks if none provided
        if fno_symbols is None:
            fno_symbols = [
                "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY",
                "SBIN", "BAJFINANCE", "HINDUNILVR", "ITC", "KOTAKBANK"
            ]
        
        # Convert symbols to instrument keys (this would need actual mapping)
        # For now, assuming they're already instrument keys
        instrument_keys = fno_symbols
        
        # Subscribe to instruments
        service.subscribe_to_instruments(instrument_keys)
        
        # Set callback if provided
        if callback:
            service.set_price_callback(callback)
        
        logger.info(
            f"✅ Momentum strategy '{strategy_name}' created with "
            f"{len(instrument_keys)} FNO instruments"
        )
        return service
        
    except Exception as e:
        logger.error(f"❌ Error creating momentum strategy service: {e}")
        raise

def create_arbitrage_strategy_service(
    strategy_name: str,
    stock_option_pairs: List[tuple],
    callback: Callable = None
) -> StrategyDataService:
    """
    Create an arbitrage strategy service for stock-option pairs
    
    Args:
        strategy_name: Name for the strategy  
        stock_option_pairs: List of (stock_key, option_key) tuples
        callback: Price update callback function
        
    Returns:
        StrategyDataService: Configured service
    """
    try:
        service = get_strategy_data_service(strategy_name)
        
        # Extract all instrument keys from pairs
        instrument_keys = []
        for stock_key, option_key in stock_option_pairs:
            instrument_keys.extend([stock_key, option_key])
        
        # Subscribe to all instruments
        service.subscribe_to_instruments(instrument_keys)
        
        # Set callback if provided
        if callback:
            service.set_price_callback(callback)
        
        logger.info(
            f"✅ Arbitrage strategy '{strategy_name}' created with "
            f"{len(stock_option_pairs)} pairs ({len(instrument_keys)} instruments)"
        )
        return service
        
    except Exception as e:
        logger.error(f"❌ Error creating arbitrage strategy service: {e}")
        raise


if __name__ == "__main__":
    # Example usage and testing
    logging.basicConfig(level=logging.INFO)
    
    def example_callback(instrument_key: str, price_data: Dict[str, Any]):
        """Example callback function"""
        ltp = price_data.get('ltp', 0)
        change_pct = price_data.get('change_percent', 0)
        print(f"📊 {instrument_key}: ₹{ltp} ({change_pct:+.2f}%)")
    
    # Create example strategy
    strategy = get_strategy_data_service("example_strategy")
    
    # Example instrument keys (you'd use real ones)
    instruments = ["NSE_EQ|INE002A01018", "NSE_EQ|INE467B01029"]
    
    # Subscribe and set callback
    strategy.subscribe_to_instruments(instruments)
    strategy.set_price_callback(example_callback)
    
    # Get portfolio status
    status = strategy.get_portfolio_status()
    print(f"📈 Strategy Status: {status}")