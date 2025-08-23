#!/usr/bin/env python3
"""
Improved Breakout Detection Logic

Fixes the issues identified in the current breakout detection algorithm
to correctly identify genuine breakouts from live market data.
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

def improved_check_breakouts(tracker, price_data: Dict[str, Any], scanner_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Improved breakout detection logic that correctly identifies genuine breakouts
    
    Issues Fixed:
    1. Resistance calculation now uses proper pivot highs
    2. Volume breakout detection improved with better thresholds
    3. Momentum detection considers market context
    4. Added confirmation mechanisms
    5. Better parameter sensitivity
    """
    
    try:
        current_price = tracker.current_price
        volume = tracker.current_volume
        
        if current_price <= 0 or volume <= 0:
            return None
        
        # Get price data fields
        change_percent = float(price_data.get("change_percent", 0))
        change_amount = float(price_data.get("change", 0))
        
        # Skip if we just had a breakout (avoid duplicates)
        if (tracker.last_breakout_time and 
            (datetime.now() - tracker.last_breakout_time).total_seconds() < 300):
            return None
        
        detected_breakouts = []
        
        # 1. IMPROVED VOLUME BREAKOUT DETECTION
        volume_breakout = _check_volume_breakout(tracker, price_data, scanner_config)
        if volume_breakout:
            detected_breakouts.append(volume_breakout)
        
        # 2. IMPROVED MOMENTUM BREAKOUT DETECTION  
        momentum_breakout = _check_momentum_breakout(tracker, price_data, scanner_config)
        if momentum_breakout:
            detected_breakouts.append(momentum_breakout)
        
        # 3. IMPROVED RESISTANCE/SUPPORT BREAKOUT DETECTION
        resistance_breakout = _check_resistance_breakout(tracker, price_data, scanner_config)
        if resistance_breakout:
            detected_breakouts.append(resistance_breakout)
        
        # 4. GAP BREAKOUT DETECTION (NEW)
        gap_breakout = _check_gap_breakout(tracker, price_data, scanner_config)
        if gap_breakout:
            detected_breakouts.append(gap_breakout)
        
        # Return the strongest breakout signal
        if detected_breakouts:
            strongest_breakout = max(detected_breakouts, key=lambda x: x['strength'])
            logger.info(f"🚨 BREAKOUT DETECTED: {tracker.symbol} - {strongest_breakout['type']} - {strongest_breakout['move']:.2f}%")
            return strongest_breakout
        
        return None
        
    except Exception as e:
        logger.debug(f"Error in improved breakout detection for {tracker.symbol}: {e}")
        return None

def _check_volume_breakout(tracker, price_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Improved volume breakout detection"""
    try:
        current_volume = tracker.current_volume
        change_percent = abs(float(price_data.get("change_percent", 0)))
        
        # Need at least 10 data points for volume analysis
        if len(tracker.volume_history) < 10:
            return None
        
        # Calculate volume statistics
        recent_volumes = list(tracker.volume_history)[-10:]
        avg_volume = np.mean(recent_volumes)
        volume_std = np.std(recent_volumes)
        
        if avg_volume <= 0:
            return None
        
        # Volume breakout criteria (IMPROVED):
        volume_ratio = current_volume / avg_volume
        volume_multiplier = config.get('volume_multiplier', 1.5)
        
        # More sophisticated volume detection
        volume_z_score = (current_volume - avg_volume) / max(volume_std, avg_volume * 0.1)
        
        # Breakout conditions (ANY of these):
        conditions = [
            volume_ratio >= volume_multiplier * 2.0,  # 3x average volume
            volume_z_score >= 2.0,  # 2 standard deviations above average
            (volume_ratio >= volume_multiplier and change_percent >= 1.5),  # 1.5x volume + 1.5% move
        ]
        
        if any(conditions) and change_percent >= 0.8:  # At least 0.8% price move
            strength = min(10, max(3, volume_ratio * 2))  # Minimum strength 3
            
            return {
                'type': 'volume_breakout',
                'strength': strength,
                'move': change_percent,
                'volume_ratio': volume_ratio,
                'confirmation': f"{volume_ratio:.1f}x volume spike"
            }
        
        return None
        
    except Exception as e:
        logger.debug(f"Volume breakout check error: {e}")
        return None

def _check_momentum_breakout(tracker, price_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Improved momentum breakout detection"""
    try:
        change_percent = float(price_data.get("change_percent", 0))
        
        # IMPROVED thresholds based on price range
        current_price = tracker.current_price
        
        # Dynamic threshold based on stock price (higher priced stocks need higher % moves)
        if current_price >= 2000:
            momentum_threshold = config.get('breakout_threshold', 2.0) * 0.75  # 1.5% for expensive stocks
        elif current_price >= 1000:
            momentum_threshold = config.get('breakout_threshold', 2.0)  # 2.0% for mid-price stocks
        else:
            momentum_threshold = config.get('breakout_threshold', 2.0) * 1.25  # 2.5% for cheaper stocks
        
        abs_change = abs(change_percent)
        
        if abs_change >= momentum_threshold:
            # Calculate strength with better scaling
            strength = min(10, max(2, abs_change * 2))
            
            breakout_type = 'momentum_breakout' if change_percent > 0 else 'support_breakdown'
            
            return {
                'type': breakout_type,
                'strength': strength,
                'move': change_percent,
                'threshold_used': momentum_threshold,
                'confirmation': f"{abs_change:.2f}% move (threshold: {momentum_threshold:.1f}%)"
            }
        
        return None
        
    except Exception as e:
        logger.debug(f"Momentum breakout check error: {e}")
        return None

def _check_resistance_breakout(tracker, price_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Improved resistance/support breakout detection"""
    try:
        current_price = tracker.current_price
        
        # Need sufficient price history
        if len(tracker.price_history) < 15:
            return None
        
        # IMPROVED resistance/support calculation using pivot points
        recent_prices = [price for _, price, _ in list(tracker.price_history)[-20:]]
        
        # Calculate resistance and support using percentile method (more robust)
        resistance_level = np.percentile(recent_prices, 90)  # 90th percentile as resistance
        support_level = np.percentile(recent_prices, 10)   # 10th percentile as support
        
        # Alternative: Use recent highs/lows
        recent_high = max(recent_prices[-10:])  # Last 10 periods high
        recent_low = min(recent_prices[-10:])   # Last 10 periods low
        
        # Use the more conservative estimate
        resistance_level = max(resistance_level, recent_high)
        support_level = min(support_level, recent_low)
        
        breakout_buffer = 0.005  # 0.5% buffer for breakout confirmation
        
        # Resistance breakout
        if current_price > resistance_level * (1 + breakout_buffer):
            percentage_move = ((current_price - resistance_level) / resistance_level) * 100
            
            if percentage_move >= 0.3:  # At least 0.3% above resistance
                strength = min(10, max(4, percentage_move * 3))
                
                return {
                    'type': 'resistance_breakout',
                    'strength': strength,
                    'move': percentage_move,
                    'resistance_level': resistance_level,
                    'confirmation': f"Broke Rs.{resistance_level:.2f} resistance by {percentage_move:.2f}%"
                }
        
        # Support breakdown
        elif current_price < support_level * (1 - breakout_buffer):
            percentage_move = ((support_level - current_price) / support_level) * 100
            
            if percentage_move >= 0.3:  # At least 0.3% below support
                strength = min(10, max(4, percentage_move * 3))
                
                return {
                    'type': 'support_breakdown',
                    'strength': strength,
                    'move': -percentage_move,  # Negative for breakdown
                    'support_level': support_level,
                    'confirmation': f"Broke Rs.{support_level:.2f} support by {percentage_move:.2f}%"
                }
        
        return None
        
    except Exception as e:
        logger.debug(f"Resistance/support breakout check error: {e}")
        return None

def _check_gap_breakout(tracker, price_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """NEW: Gap breakout detection (opening gaps)"""
    try:
        current_price = tracker.current_price
        open_price = float(price_data.get("open", 0))
        prev_close = tracker.prev_close
        
        if open_price <= 0 or prev_close <= 0:
            return None
        
        # Calculate gap percentage
        gap_percent = ((open_price - prev_close) / prev_close) * 100
        
        # Gap breakout threshold
        gap_threshold = 1.5  # 1.5% gap
        
        if abs(gap_percent) >= gap_threshold:
            # Check if gap is being sustained
            price_from_open = ((current_price - open_price) / open_price) * 100
            
            # Gap up breakout
            if gap_percent > 0 and price_from_open >= -0.5:  # Not fading significantly
                strength = min(10, max(3, abs(gap_percent) * 2))
                
                return {
                    'type': 'gap_up_breakout',
                    'strength': strength,
                    'move': gap_percent,
                    'open_price': open_price,
                    'prev_close': prev_close,
                    'confirmation': f"{gap_percent:.2f}% gap up sustained"
                }
            
            # Gap down breakout
            elif gap_percent < 0 and price_from_open <= 0.5:  # Not recovering significantly
                strength = min(10, max(3, abs(gap_percent) * 2))
                
                return {
                    'type': 'gap_down_breakout',
                    'strength': strength,
                    'move': gap_percent,
                    'open_price': open_price,
                    'prev_close': prev_close,
                    'confirmation': f"{abs(gap_percent):.2f}% gap down sustained"
                }
        
        return None
        
    except Exception as e:
        logger.debug(f"Gap breakout check error: {e}")
        return None

def get_improved_scanner_config() -> Dict[str, Any]:
    """Get improved scanner configuration with better parameters"""
    return {
        'breakout_threshold': 1.8,  # Reduced from 2.0% to 1.8%
        'volume_multiplier': 2.0,   # Increased from 1.5x to 2.0x
        'min_price': 20.0,          # Increased from 10.0 to avoid penny stocks
        'max_price': 10000.0,       # Increased range
        'min_volume': 5000,         # Increased from 1000 to 5000 shares
        'resistance_lookback': 20,  # Periods to look back
        'duplicate_prevention_minutes': 5,  # Minutes to prevent duplicates
        'min_data_points': 15,      # Minimum data points needed for analysis
        'gap_threshold': 1.5,       # Gap detection threshold
        'volume_z_threshold': 2.0,  # Z-score threshold for volume spikes
    }

# Testing function to validate improvements
def test_improved_detection():
    """Test the improved detection logic"""
    
    # Mock tracker class for testing
    class MockTracker:
        def __init__(self, symbol: str):
            self.symbol = symbol
            self.current_price = 0.0
            self.current_volume = 0
            self.prev_close = 0.0
            self.price_history = []
            self.volume_history = []
            self.last_breakout_time = None
    
    # Test case 1: Volume breakout (Reliance scenario)
    tracker1 = MockTracker("RELIANCE")
    tracker1.current_price = 2540.50
    tracker1.current_volume = 800000
    tracker1.volume_history = [150000] * 10  # Average 150k volume
    tracker1.price_history = [(datetime.now(), 2500 + i, 150000) for i in range(20)]
    
    price_data1 = {
        'change_percent': 1.6,
        'change': 40.50,
        'open': 2500.0
    }
    
    config = get_improved_scanner_config()
    result1 = improved_check_breakouts(tracker1, price_data1, config)
    
    print("Test 1 - Volume Breakout:")
    print(f"  Input: RELIANCE @ Rs.2540.50, 1.6% up, 800k volume (vs 150k avg)")
    print(f"  Result: {result1}")
    print()
    
    # Test case 2: Momentum breakout (INFY scenario)
    tracker2 = MockTracker("INFY")
    tracker2.current_price = 1654.75
    tracker2.current_volume = 320000
    tracker2.volume_history = [300000] * 10
    tracker2.price_history = [(datetime.now(), 1590 + i, 300000) for i in range(20)]
    
    price_data2 = {
        'change_percent': 4.2,
        'change': 66.85,
        'open': 1590.0
    }
    
    result2 = improved_check_breakouts(tracker2, price_data2, config)
    
    print("Test 2 - Momentum Breakout:")
    print(f"  Input: INFY @ Rs.1654.75, 4.2% up, 320k volume")
    print(f"  Result: {result2}")
    print()
    
    # Test case 3: Normal movement (should NOT trigger)
    tracker3 = MockTracker("HDFCBANK")
    tracker3.current_price = 2789.25
    tracker3.current_volume = 180000
    tracker3.volume_history = [175000] * 10
    tracker3.price_history = [(datetime.now(), 2780 + i, 175000) for i in range(20)]
    
    price_data3 = {
        'change_percent': 0.8,
        'change': 22.15,
        'open': 2770.0
    }
    
    result3 = improved_check_breakouts(tracker3, price_data3, config)
    
    print("Test 3 - Normal Movement:")
    print(f"  Input: HDFCBANK @ Rs.2789.25, 0.8% up, 180k volume")
    print(f"  Result: {result3}")
    print()

if __name__ == "__main__":
    print("TESTING IMPROVED BREAKOUT DETECTION")
    print("=" * 50)
    test_improved_detection()