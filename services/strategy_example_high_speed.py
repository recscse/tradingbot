"""
Example Trading Strategy using High-Speed Market Data
====================================================

This demonstrates how trading strategies can access live market data
with zero delay using the high-speed market data system.

Features:
- Sub-millisecond price access
- Vectorized indicator calculations
- Real-time callbacks
- Selected stocks optimization
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any

from services.high_speed_market_data import high_speed_market_data

logger = logging.getLogger(__name__)

class ExampleMomentumStrategy:
    """
    Example momentum trading strategy using high-speed market data.
    
    Strategy Logic:
    - Monitor selected stocks for momentum breakouts
    - Use RSI and moving averages for entry signals
    - Fast execution using zero-copy data access
    """
    
    def __init__(self, strategy_name: str = "momentum_v1"):
        self.strategy_name = strategy_name
        self.positions = {}
        self.entry_signals = {}
        
        # Strategy parameters
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        self.volume_threshold_multiplier = 1.5
        
        logger.info(f"🎯 {strategy_name} strategy initialized")
    
    async def start(self):
        """Start the strategy by registering for live data callbacks"""
        try:
            # Get currently selected stocks
            selected_data = high_speed_market_data.get_selected_stocks_data()
            
            if not selected_data:
                logger.warning("⚠️ No selected stocks available. Strategy will wait for selection.")
                return
            
            # Extract instrument keys for monitoring
            instruments = []
            for symbol, stock_data in selected_data.items():
                instrument_key = stock_data.get('instrument_key')
                if instrument_key:
                    instruments.append(instrument_key)
                    logger.info(f"📊 Monitoring {symbol} ({instrument_key})")
            
            # Register high-speed callback
            high_speed_market_data.register_strategy_callback(
                strategy_name=self.strategy_name,
                instruments=instruments,
                callback=self._on_tick_update
            )
            
            logger.info(f"✅ Strategy started monitoring {len(instruments)} instruments")
            
            # Start periodic analysis
            asyncio.create_task(self._periodic_analysis())
            
        except Exception as e:
            logger.error(f"❌ Error starting strategy: {e}")
    
    def _on_tick_update(self, instrument_key: str, price_data: Dict[str, Any]):
        """
        Real-time tick callback - called for every price update
        This runs with minimal latency for fastest possible response
        """
        try:
            symbol = self._get_symbol_from_instrument(instrument_key)
            if not symbol:
                return
            
            current_price = price_data.get('ltp', 0.0)
            volume = price_data.get('volume', 0)
            
            # Store latest data for analysis
            if symbol not in self.entry_signals:
                self.entry_signals[symbol] = {
                    'prices': [],
                    'volumes': [],
                    'last_signal_time': None
                }
            
            # Keep rolling window of recent prices for fast analysis
            signal_data = self.entry_signals[symbol]
            signal_data['prices'].append(current_price)
            signal_data['volumes'].append(volume)
            
            # Keep only last 50 ticks for speed
            if len(signal_data['prices']) > 50:
                signal_data['prices'] = signal_data['prices'][-50:]
                signal_data['volumes'] = signal_data['volumes'][-50:]
            
            # Check for immediate signals (very fast)
            self._check_immediate_signals(symbol, current_price, volume)
            
        except Exception as e:
            logger.error(f"❌ Error in tick callback: {e}")
    
    def _check_immediate_signals(self, symbol: str, price: float, volume: int):
        """Check for immediate trading signals - optimized for speed"""
        try:
            signal_data = self.entry_signals[symbol]
            prices = signal_data['prices']
            volumes = signal_data['volumes']
            
            if len(prices) < 10:  # Need minimum data
                return
            
            # Quick volume spike check
            recent_avg_volume = np.mean(volumes[-10:]) if len(volumes) >= 10 else 0
            if recent_avg_volume > 0:
                current_volume_ratio = volume / recent_avg_volume
                
                if current_volume_ratio > self.volume_threshold_multiplier:
                    logger.info(f"🚨 {symbol}: Volume spike detected! Ratio: {current_volume_ratio:.2f}")
                    
                    # Quick price momentum check
                    if len(prices) >= 5:
                        price_change = (price - prices[-5]) / prices[-5] * 100
                        if abs(price_change) > 1.0:  # 1% move
                            self._generate_signal(symbol, 'MOMENTUM', {
                                'price_change': price_change,
                                'volume_ratio': current_volume_ratio,
                                'price': price
                            })
        
        except Exception as e:
            logger.error(f"❌ Error checking immediate signals: {e}")
    
    async def _periodic_analysis(self):
        """Periodic deep analysis using indicators - runs every 30 seconds"""
        while True:
            try:
                await asyncio.sleep(30)
                
                # Get all selected stocks data
                selected_data = high_speed_market_data.get_selected_stocks_data()
                
                for symbol in selected_data.keys():
                    await self._analyze_stock_deeply(symbol)
                
            except Exception as e:
                logger.error(f"❌ Error in periodic analysis: {e}")
    
    async def _analyze_stock_deeply(self, symbol: str):
        """Deep analysis using technical indicators"""
        try:
            # Get stock data
            stock_data = high_speed_market_data.get_selected_stocks_data().get(symbol)
            if not stock_data:
                return
            
            instrument_key = stock_data.get('instrument_key')
            if not instrument_key:
                return
            
            # Get indicators using high-speed calculation
            indicators = high_speed_market_data.get_indicators_fast(instrument_key, 100)
            
            if not indicators:
                return
            
            # Get current price
            current_price = high_speed_market_data.get_latest_price(instrument_key)
            if not current_price:
                return
            
            # Analysis using vectorized operations
            rsi = indicators.get('rsi_14')
            sma_20 = indicators.get('sma_20')
            bb_upper = indicators.get('bb_upper')
            bb_lower = indicators.get('bb_lower')
            
            if rsi is not None and len(rsi) > 0:
                current_rsi = rsi[-1]
                
                # RSI-based signals
                if current_rsi < self.rsi_oversold:
                    if sma_20 is not None and len(sma_20) > 0:
                        current_sma = sma_20[-1]
                        if current_price > current_sma:  # Price above SMA
                            self._generate_signal(symbol, 'BUY_RSI_OVERSOLD', {
                                'rsi': current_rsi,
                                'price': current_price,
                                'sma_20': current_sma
                            })
                
                elif current_rsi > self.rsi_overbought:
                    self._generate_signal(symbol, 'SELL_RSI_OVERBOUGHT', {
                        'rsi': current_rsi,
                        'price': current_price
                    })
            
            # Bollinger Bands analysis
            if bb_upper is not None and bb_lower is not None and len(bb_lower) > 0:
                current_bb_lower = bb_lower[-1]
                current_bb_upper = bb_upper[-1]
                
                if current_price <= current_bb_lower:
                    self._generate_signal(symbol, 'BUY_BB_LOWER', {
                        'price': current_price,
                        'bb_lower': current_bb_lower
                    })
                elif current_price >= current_bb_upper:
                    self._generate_signal(symbol, 'SELL_BB_UPPER', {
                        'price': current_price,
                        'bb_upper': current_bb_upper
                    })
            
            # Log analysis for monitoring
            logger.info(
                f"📈 {symbol}: Price={current_price:.2f}, "
                f"RSI={current_rsi:.1f if rsi is not None and len(rsi) > 0 else 'N/A'}"
            )
            
        except Exception as e:
            logger.error(f"❌ Error in deep analysis for {symbol}: {e}")
    
    def _generate_signal(self, symbol: str, signal_type: str, data: Dict[str, Any]):
        """Generate trading signal"""
        signal = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'signal_type': signal_type,
            'data': data,
            'strategy': self.strategy_name
        }
        
        logger.info(f"🎯 TRADING SIGNAL: {signal}")
        
        # Here you would integrate with execution engine
        # For example: await execution_engine.execute_signal(signal)
    
    def _get_symbol_from_instrument(self, instrument_key: str) -> str:
        """Get symbol from instrument key - fast lookup"""
        selected_data = high_speed_market_data.get_selected_stocks_data()
        for symbol, stock_data in selected_data.items():
            if stock_data.get('instrument_key') == instrument_key:
                return symbol
        return None
    
    def get_strategy_stats(self) -> Dict[str, Any]:
        """Get strategy performance statistics"""
        return {
            'strategy_name': self.strategy_name,
            'instruments_monitored': len(self.entry_signals),
            'positions': len(self.positions),
            'signals_generated': sum(
                1 for data in self.entry_signals.values() 
                if data.get('last_signal_time') is not None
            )
        }

# Usage example
async def run_example_strategy():
    """Example of how to run a trading strategy"""
    strategy = ExampleMomentumStrategy("momentum_example")
    
    # Start the strategy
    await strategy.start()
    
    # Let it run and monitor performance
    while True:
        await asyncio.sleep(60)  # Check every minute
        
        stats = strategy.get_strategy_stats()
        logger.info(f"📊 Strategy stats: {stats}")
        
        # Get market data system performance
        market_stats = high_speed_market_data.get_performance_stats()
        logger.info(f"🚀 Market data stats: {market_stats}")

# Fast utility functions for strategy development
class StrategyUtils:
    """Utility functions for strategy development"""
    
    @staticmethod
    def get_all_selected_prices() -> Dict[str, float]:
        """Get all selected stock prices in one call"""
        return high_speed_market_data.get_selected_stock_prices()
    
    @staticmethod
    def get_indicators_batch() -> Dict[str, Dict[str, np.ndarray]]:
        """Get indicators for all selected stocks in one batch"""
        return high_speed_market_data.get_selected_stock_indicators_batch()
    
    @staticmethod
    def is_market_data_available() -> bool:
        """Check if high-speed market data is available"""
        summary = high_speed_market_data.get_auto_trading_summary()
        return summary['current_prices_available'] > 0
    
    @staticmethod
    def get_option_prices(symbol: str) -> Dict[str, float]:
        """Get option prices for a selected stock"""
        return high_speed_market_data.get_option_chain_prices(symbol)

if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Run the strategy
    asyncio.run(run_example_strategy())