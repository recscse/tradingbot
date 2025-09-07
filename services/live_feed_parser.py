#!/usr/bin/env python3
"""
Live Feed Parser - WebSocket Data Structure Helper

This module provides utilities for parsing the live WebSocket feed data structure
from brokers. It helps extract the correct fields for gap detection and candle building.

Live Feed Structure:
{
    "feeds": {
        "NSE_EQ|INE683A01023": {
            "fullFeed": {
                "marketFF": {
                    "ltpc": {
                        "ltp": 30.0,        # Last Traded Price
                        "ltt": "1752229776556",  # Last Trade Time
                        "ltq": "500",       # Last Trade Quantity
                        "cp": 30.05         # Previous Close (Closing Price)
                    },
                    "marketOHLC": {
                        "ohlc": [
                            {
                                "interval": "1d",    # Daily interval
                                "open": 30.0,        # Today's Opening
                                "high": 30.25,       # Today's High
                                "low": 29.8,         # Today's Low
                                "close": 30.0,       # Current Close
                                "vol": "7512716",    # Volume
                                "ts": "1752172200000"
                            },
                            {
                                "interval": "I1",    # 1-minute interval
                                "open": 30.06,
                                "high": 30.08,
                                "low": 30.04,
                                "close": 30.05,
                                "vol": "13129",
                                "ts": "1752227940000"
                            }
                        ]
                    }
                }
            }
        }
    },
    "currentTs": "1751780830087"
}
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from datetime import datetime

logger = logging.getLogger(__name__)

class LiveFeedParser:
    """Parser for live WebSocket feed data structure"""
    
    @staticmethod
    def extract_instrument_data(instrument_key: str, feed_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract data for a specific instrument from the feed
        
        Args:
            instrument_key: Instrument identifier (e.g., 'NSE_EQ|INE683A01023')
            feed_data: Full feed data from WebSocket
            
        Returns:
            Dictionary with extracted data or None if not found
        """
        try:
            feeds = feed_data.get('feeds', {})
            instrument_feed = feeds.get(instrument_key)
            
            if not instrument_feed:
                return None
                
            full_feed = instrument_feed.get('fullFeed', {})
            market_ff = full_feed.get('marketFF', {})
            
            if not market_ff:
                return None
                
            return market_ff
            
        except Exception as e:
            logger.error(f"❌ Error extracting instrument data for {instrument_key}: {e}")
            return None
    
    @staticmethod
    def extract_price_data(market_ff: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract price-related data from marketFF structure
        
        Args:
            market_ff: Market feed data for an instrument
            
        Returns:
            Dictionary with price data
        """
        try:
            ltpc_data = market_ff.get('ltpc', {})
            ohlc_data = market_ff.get('marketOHLC', {}).get('ohlc', [])
            
            # Get current price and previous close
            current_price = ltpc_data.get('ltp')
            previous_close = ltpc_data.get('cp')
            last_trade_time = ltpc_data.get('ltt')
            last_trade_qty = ltpc_data.get('ltq')
            
            # Extract daily OHLC
            daily_ohlc = None
            minute_ohlc = None
            
            for ohlc in ohlc_data:
                if ohlc.get('interval') == '1d':
                    daily_ohlc = ohlc
                elif ohlc.get('interval') == 'I1':
                    minute_ohlc = ohlc
            
            result = {
                # Current price data
                'current_price': current_price,
                'previous_close': previous_close,
                'last_trade_time': last_trade_time,
                'last_trade_qty': last_trade_qty,
                
                # Daily data
                'daily_open': daily_ohlc.get('open') if daily_ohlc else None,
                'daily_high': daily_ohlc.get('high') if daily_ohlc else None,
                'daily_low': daily_ohlc.get('low') if daily_ohlc else None,
                'daily_close': daily_ohlc.get('close') if daily_ohlc else None,
                'daily_volume': daily_ohlc.get('vol') if daily_ohlc else None,
                'daily_timestamp': daily_ohlc.get('ts') if daily_ohlc else None,
                
                # Minute data (if available)
                'minute_open': minute_ohlc.get('open') if minute_ohlc else None,
                'minute_high': minute_ohlc.get('high') if minute_ohlc else None,
                'minute_low': minute_ohlc.get('low') if minute_ohlc else None,
                'minute_close': minute_ohlc.get('close') if minute_ohlc else None,
                'minute_volume': minute_ohlc.get('vol') if minute_ohlc else None,
                'minute_timestamp': minute_ohlc.get('ts') if minute_ohlc else None,
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error extracting price data: {e}")
            return {}
    
    @staticmethod
    def calculate_gap_percentage(open_price: float, previous_close: float) -> Optional[float]:
        """
        Calculate gap percentage from opening and previous close
        
        Args:
            open_price: Today's opening price
            previous_close: Yesterday's closing price
            
        Returns:
            Gap percentage or None if calculation not possible
        """
        try:
            if not open_price or not previous_close or previous_close <= 0:
                return None
                
            gap_pct = ((open_price - previous_close) / previous_close) * 100
            return round(gap_pct, 4)
            
        except Exception as e:
            logger.error(f"❌ Error calculating gap percentage: {e}")
            return None
    
    @staticmethod
    def get_gap_type_and_strength(gap_percentage: float) -> Tuple[str, str]:
        """
        Determine gap type and strength
        
        Args:
            gap_percentage: Gap percentage value
            
        Returns:
            Tuple of (gap_type, gap_strength)
        """
        if gap_percentage > 0.5:
            gap_type = "GAP_UP"
        elif gap_percentage < -0.5:
            gap_type = "GAP_DOWN"
        else:
            gap_type = "NO_GAP"
        
        abs_gap = abs(gap_percentage)
        if abs_gap >= 8.0:
            gap_strength = "VERY_STRONG"
        elif abs_gap >= 5.0:
            gap_strength = "STRONG"
        elif abs_gap >= 2.5:
            gap_strength = "MODERATE"
        else:
            gap_strength = "WEAK"
            
        return gap_type, gap_strength
    
    @staticmethod
    def parse_feed_for_gap_detection(feed_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse entire feed data for gap detection
        
        Args:
            feed_data: Complete WebSocket feed data
            
        Returns:
            List of instruments with gap data
        """
        results = []
        
        try:
            feeds = feed_data.get('feeds', {})
            
            for instrument_key, instrument_data in feeds.items():
                # Skip non-equity instruments for gap detection
                if not instrument_key.startswith('NSE_EQ|'):
                    continue
                
                # Extract market data
                market_ff = LiveFeedParser.extract_instrument_data(instrument_key, feed_data)
                if not market_ff:
                    continue
                
                # Extract price data
                price_data = LiveFeedParser.extract_price_data(market_ff)
                if not price_data.get('current_price') or not price_data.get('previous_close'):
                    continue
                
                # Calculate gap
                gap_pct = LiveFeedParser.calculate_gap_percentage(
                    price_data['daily_open'], 
                    price_data['previous_close']
                )
                
                if gap_pct is None:
                    continue
                
                # Get gap type and strength
                gap_type, gap_strength = LiveFeedParser.get_gap_type_and_strength(gap_pct)
                
                # Only include significant gaps
                if abs(gap_pct) >= 1.0:  # 1% minimum gap
                    result = {
                        'instrument_key': instrument_key,
                        'current_price': price_data['current_price'],
                        'previous_close': price_data['previous_close'],
                        'daily_open': price_data['daily_open'],
                        'daily_volume': price_data['daily_volume'],
                        'gap_percentage': gap_pct,
                        'gap_type': gap_type,
                        'gap_strength': gap_strength,
                        'is_significant': abs(gap_pct) >= 1.0,
                        'timestamp': datetime.now().isoformat()
                    }
                    results.append(result)
                    
        except Exception as e:
            logger.error(f"❌ Error parsing feed for gap detection: {e}")
        
        # Sort by gap percentage (largest gaps first)
        results.sort(key=lambda x: abs(x['gap_percentage']), reverse=True)
        return results
    
    @staticmethod
    def store_feed_sample(feed_data: Dict[str, Any], filename: str = "feed_sample.json") -> bool:
        """
        Store a sample of feed data for reference
        
        Args:
            feed_data: Feed data to store
            filename: Output filename
            
        Returns:
            True if stored successfully
        """
        try:
            import json
            from pathlib import Path
            
            # Create logs directory if it doesn't exist
            logs_dir = Path("logs")
            logs_dir.mkdir(exist_ok=True)
            
            # Store sample with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            sample_file = logs_dir / f"feed_sample_{timestamp}.json"
            
            with open(sample_file, 'w') as f:
                json.dump(feed_data, f, indent=2)
            
            logger.info(f"📁 Feed sample stored in {sample_file}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error storing feed sample: {e}")
            return False

# Convenience function for quick gap detection
def quick_gap_analysis(feed_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Quick gap analysis from live feed data"""
    return LiveFeedParser.parse_feed_for_gap_detection(feed_data)

# Example usage and testing
if __name__ == "__main__":
    # Example feed data structure (as provided by user)
    sample_feed = {
        "feeds": {
            "NSE_EQ|INE683A01023": {
                "fullFeed": {
                    "marketFF": {
                        "ltpc": {
                            "ltp": 30.0,
                            "ltt": "1752229776556",
                            "ltq": "500",
                            "cp": 30.05
                        },
                        "marketOHLC": {
                            "ohlc": [
                                {
                                    "interval": "1d",
                                    "open": 31.5,  # Gap up scenario
                                    "high": 32.25,
                                    "low": 29.8,
                                    "close": 30.0,
                                    "vol": "7512716",
                                    "ts": "1752172200000"
                                }
                            ]
                        }
                    }
                }
            }
        }
    }
    
    # Test gap detection
    gaps = quick_gap_analysis(sample_feed)
    print(f"Found {len(gaps)} gaps:")
    for gap in gaps:
        print(f"  {gap['instrument_key']}: {gap['gap_percentage']:.2f}% ({gap['gap_type']})")