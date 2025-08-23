# services/market_timing_service.py
"""
Market Timing Service - Determines market status and appropriate messages
"""

import logging
from datetime import datetime, time, date
from typing import Dict, Any
import pytz
from enum import Enum

logger = logging.getLogger(__name__)

class MarketStatus(Enum):
    """Market status enumeration"""
    CLOSED_WEEKEND = "closed_weekend"
    CLOSED_AFTER_HOURS = "closed_after_hours" 
    PRE_MARKET = "pre_market"
    MARKET_OPEN = "market_open"
    MARKET_CLOSED_TODAY = "market_closed_today"

class MarketTimingService:
    """Service to determine market status and provide appropriate messages"""
    
    def __init__(self):
        self.ist = pytz.timezone("Asia/Kolkata")
        
        # Market timings (IST)
        self.pre_market_start = time(9, 0)   # 9:00 AM
        self.market_open = time(9, 15)       # 9:15 AM  
        self.market_close = time(15, 30)     # 3:30 PM
        
        # Stock selection timing
        self.stock_selection_time = time(9, 0)  # 9:00 AM daily
    
    def get_current_market_status(self) -> MarketStatus:
        """Get current market status based on time"""
        
        now = datetime.now(self.ist)
        current_time = now.time()
        current_date = now.date()
        weekday = now.weekday()  # Monday=0, Sunday=6
        
        # Weekend check
        if weekday >= 5:  # Saturday or Sunday
            return MarketStatus.CLOSED_WEEKEND
        
        # Weekday timing checks
        if current_time < self.pre_market_start:
            return MarketStatus.CLOSED_AFTER_HOURS
        elif current_time < self.market_open:
            return MarketStatus.PRE_MARKET
        elif current_time <= self.market_close:
            return MarketStatus.MARKET_OPEN
        else:
            return MarketStatus.MARKET_CLOSED_TODAY
    
    def get_stock_selection_status(self) -> Dict[str, Any]:
        """Get stock selection status and appropriate message"""
        
        market_status = self.get_current_market_status()
        now = datetime.now(self.ist)
        today = now.date()
        
        # Check if we have stocks selected for today
        from database.connection import SessionLocal
        from database.models import SelectedStock
        
        db = SessionLocal()
        try:
            selected_stocks_count = db.query(SelectedStock).filter(
                SelectedStock.selection_date == today,
                SelectedStock.is_active == True
            ).count()
        finally:
            db.close()
        
        # Determine status and message
        if market_status == MarketStatus.CLOSED_WEEKEND:
            return {
                "status": "weekend",
                "message": "Market is closed on weekends. Stock selection will resume on Monday at 9:00 AM.",
                "show_stocks": False,
                "can_trade": False,
                "selected_count": 0,
                "next_selection": "Monday 9:00 AM"
            }
        
        elif market_status == MarketStatus.CLOSED_AFTER_HOURS:
            if selected_stocks_count > 0:
                return {
                    "status": "after_hours_with_stocks",
                    "message": f"Market opens at 9:15 AM. Today's {selected_stocks_count} selected stocks are ready for trading.",
                    "show_stocks": True,
                    "can_trade": False,  # Can't trade before market opens
                    "selected_count": selected_stocks_count,
                    "next_selection": "Today 9:00 AM (completed)"
                }
            else:
                return {
                    "status": "after_hours_no_stocks", 
                    "message": "Stock selection will run automatically at 9:00 AM when pre-market opens.",
                    "show_stocks": False,
                    "can_trade": False,
                    "selected_count": 0,
                    "next_selection": "Today 9:00 AM"
                }
        
        elif market_status == MarketStatus.PRE_MARKET:
            if selected_stocks_count > 0:
                return {
                    "status": "pre_market_ready",
                    "message": f"Pre-market active. {selected_stocks_count} stocks selected and ready. Trading starts at 9:15 AM.",
                    "show_stocks": True,
                    "can_trade": False,  # Can't trade in pre-market
                    "selected_count": selected_stocks_count,
                    "next_selection": "Tomorrow 9:00 AM"
                }
            else:
                # Should auto-run selection now
                return {
                    "status": "pre_market_selecting",
                    "message": "Pre-market open. Running stock selection algorithm...",
                    "show_stocks": False,
                    "can_trade": False,
                    "selected_count": 0,
                    "next_selection": "Running now..."
                }
        
        elif market_status == MarketStatus.MARKET_OPEN:
            if selected_stocks_count > 0:
                return {
                    "status": "market_open_ready",
                    "message": f"Market is open! {selected_stocks_count} stocks selected and ready for trading.",
                    "show_stocks": True,
                    "can_trade": True,  # Can trade during market hours
                    "selected_count": selected_stocks_count,
                    "next_selection": "Tomorrow 9:00 AM"
                }
            else:
                return {
                    "status": "market_open_no_stocks",
                    "message": "Market is open but no stocks selected today. Selection may have failed.",
                    "show_stocks": False,
                    "can_trade": False,
                    "selected_count": 0,
                    "next_selection": "Tomorrow 9:00 AM"
                }
        
        elif market_status == MarketStatus.MARKET_CLOSED_TODAY:
            if selected_stocks_count > 0:
                return {
                    "status": "market_closed_with_stocks",
                    "message": f"Market closed for today. {selected_stocks_count} stocks were selected for today's session.",
                    "show_stocks": True,  # Show for review
                    "can_trade": False,
                    "selected_count": selected_stocks_count,
                    "next_selection": "Tomorrow 9:00 AM"
                }
            else:
                return {
                    "status": "market_closed_no_stocks",
                    "message": "Market closed. No stocks were selected today.",
                    "show_stocks": False,
                    "can_trade": False,
                    "selected_count": 0,
                    "next_selection": "Tomorrow 9:00 AM"
                }
        
        # Fallback
        return {
            "status": "unknown",
            "message": "Unable to determine market status.",
            "show_stocks": False,
            "can_trade": False,
            "selected_count": 0,
            "next_selection": "Unknown"
        }
    
    def should_run_stock_selection(self) -> bool:
        """Check if stock selection should run now"""
        
        now = datetime.now(self.ist)
        current_time = now.time()
        weekday = now.weekday()
        
        # Only run on weekdays
        if weekday >= 5:
            return False
        
        # Only run during pre-market (9:00 AM - 9:15 AM)
        if not (self.stock_selection_time <= current_time < self.market_open):
            return False
        
        # Check if already run today
        from database.connection import SessionLocal
        from database.models import SelectedStock
        
        db = SessionLocal()
        try:
            existing_count = db.query(SelectedStock).filter(
                SelectedStock.selection_date == now.date(),
                SelectedStock.is_active == True
            ).count()
            
            # Don't run if already have stocks for today
            return existing_count == 0
            
        finally:
            db.close()
    
    def get_market_info_summary(self) -> Dict[str, Any]:
        """Get comprehensive market information"""
        
        now = datetime.now(self.ist)
        market_status = self.get_current_market_status()
        stock_status = self.get_stock_selection_status()
        
        return {
            "current_time": now.strftime("%Y-%m-%d %H:%M:%S IST"),
            "market_status": market_status.value,
            "stock_selection": stock_status,
            "trading_timings": {
                "pre_market": "9:00 AM - 9:15 AM",
                "market_open": "9:15 AM - 3:30 PM", 
                "stock_selection": "9:00 AM daily"
            },
            "is_trading_day": now.weekday() < 5,
            "should_auto_select": self.should_run_stock_selection()
        }


# Create singleton instance
market_timing_service = MarketTimingService()