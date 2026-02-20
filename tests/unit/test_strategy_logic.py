import pytest
from decimal import Decimal
from services.trading_execution.strategy_engine import strategy_engine, SignalType

def test_supertrend_bullish_signal():
    """Verify strategy generates BUY for clear uptrend with reversal"""
    # 100 Bearish (500 -> 400)
    prices = [500 - i for i in range(100)]
    # 100 Bullish (400 -> 600)
    prices.extend([400 + i*2 for i in range(1, 101)])
    
    historical_data = {
        "open": [p for p in prices],
        "high": [p + 10 for p in prices], # Add volatility
        "low": [p - 10 for p in prices],  # Add volatility
        "close": prices,
        "volume": [1000] * 200
    }
    # Current price significantly above the recovery peak
    current_price = Decimal(str(prices[-1] + 50))
    
    signal = strategy_engine.generate_signal(current_price, historical_data, "CE")
    
    assert signal.signal_type == SignalType.BUY
    assert signal.entry_price == current_price
    assert signal.stop_loss < current_price
    assert signal.target_price > current_price

def test_supertrend_bearish_signal():
    """Verify strategy generates BUY PE for clear downtrend"""
    # Create 40 candles of a downtrend
    historical_data = {
        "open": [200 - i for i in range(40)],
        "high": [201 - i for i in range(40)],
        "low": [198 - i for i in range(40)],
        "close": [199 - i for i in range(40)],
        "volume": [1000] * 40
    }
    current_price = Decimal("159.0")
    
    signal = strategy_engine.generate_signal(current_price, historical_data, "PE")
    
    # In a clear downtrend for PE, we expect a BUY (buying the put)
    assert signal.signal_type == SignalType.BUY
    assert signal.reason.find("Buy Put") != -1 or signal.reason.find("downtrend") != -1

def test_lock_profit_trailing():
    """Verify trailing SL moves to breakeven when target is 35% reached"""
    entry_price = Decimal("100.0")
    target_price = Decimal("110.0") # 10 point profit target
    current_sl = Decimal("95.0")
    
    # Case 1: Price moved 4 points up (40% of target)
    # Threshold is 35%, so it should move to breakeven (100.0)
    new_sl = strategy_engine.update_trailing_stop(
        current_price=Decimal("104.0"),
        entry_price=entry_price,
        current_stop_loss=current_sl,
        trailing_type=None, # Use lock profit logic
        target_price=target_price
    )
    
    assert new_sl == entry_price
    
    # Case 2: Target hit! Should lock 80% of profit
    # Profit = 10 points. 80% = 8 points. New SL = 100 + 8 = 108.0
    final_sl = strategy_engine.update_trailing_stop(
        current_price=Decimal("110.5"),
        entry_price=entry_price,
        current_stop_loss=new_sl,
        trailing_type=None,
        target_price=target_price
    )
    
    assert final_sl >= Decimal("108.0")
