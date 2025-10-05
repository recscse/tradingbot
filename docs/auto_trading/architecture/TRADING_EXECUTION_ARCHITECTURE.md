# Trading Execution System - Complete Modular Architecture

## Overview
This document describes the complete modular trading execution system built for algorithmic options trading with real-time PnL tracking, strategy-based entries, and support for both paper and live trading.

---

## System Flow

```
1. STOCK SELECTION (intelligent_stock_selection_service.py)
   ↓
2. OPTIONS ENHANCEMENT (enhanced_intelligent_options_selection.py)
   - Fetches option chain
   - Selects ATM/best strike
   - Stores option instrument key
   ↓
3. TRADE PREPARATION (trading_execution/trade_prep.py)
   - Validates capital
   - Checks active broker
   - Fetches live premium
   - Generates trading signal (SuperTrend + EMA)
   - Calculates position size
   ↓
4. TRADE EXECUTION (paper vs live)
   - Paper: Virtual execution with mock orders
   - Live: Real execution via broker API
   ↓
5. REAL-TIME MONITORING
   - Live PnL tracking
   - Trailing stop loss updates
   - WebSocket updates to UI
   ↓
6. POSITION MANAGEMENT
   - Exit signals
   - Target/SL hit detection
   - Auto position squaring
```

---

## Module Breakdown

### 1. Capital Manager (`capital_manager.py`)

**Purpose:** Manages trading capital and validates fund availability

**Key Features:**
- ✅ Validates demat account with active access token
- ✅ Fetches available capital from broker API (Upstox, Angel One, Dhan)
- ✅ Supports paper trading with virtual capital (₹10 Lakhs)
- ✅ Calculates position sizes based on risk management (2% risk per trade)
- ✅ Prevents over-allocation (max 20% capital per trade)
- ✅ Maintains 10% capital buffer

**Key Methods:**
```python
# Get active broker with valid token
broker_config = capital_manager.get_active_broker_config(user_id, db)

# Get available capital (paper or live)
capital = capital_manager.get_available_capital(user_id, db, TradingMode.LIVE)

# Calculate position size
allocation = capital_manager.calculate_position_size(
    available_capital=100000,
    option_premium=50.0,
    lot_size=25
)

# Validate capital availability
validation = capital_manager.validate_capital_availability(
    user_id=1,
    required_capital=25000,
    db=db,
    trading_mode=TradingMode.LIVE
)
```

**Output:**
```python
CapitalAllocation(
    total_capital=100000,
    allocated_capital=25000,
    position_size_lots=20,
    position_value=25000,
    max_loss=25000,  # 100% premium loss
    margin_required=25000,
    capital_utilization_percent=25.0,
    risk_per_trade_percent=2.0
)
```

---

### 2. Strategy Engine (`strategy_engine.py`)

**Purpose:** Generates entry/exit signals using SuperTrend + EMA strategy

**Strategy Logic:**

**Entry Signals:**
- **LONG (CE)**: Price crosses above SuperTrend AND price > EMA
- **SHORT (PE)**: Price crosses below SuperTrend AND price < EMA

**Exit Signals:**
- SuperTrend reversal (trend changes)
- Price crosses EMA (opposite direction)

**Indicators:**
- **EMA**: 20-period Exponential Moving Average
- **SuperTrend**: ATR period 10, Multiplier 3.0 (1x) or 6.0 (2x)

**Trailing Stop Options:**
1. **SuperTrend 1x**: Uses 3.0 multiplier SuperTrend as trailing SL
2. **SuperTrend 2x**: Uses 6.0 multiplier SuperTrend as trailing SL (more conservative)
3. **Percentage**: Fixed 2% trailing stop below/above current price

**Key Methods:**
```python
# Generate trading signal
signal = strategy_engine.generate_signal(
    current_price=50.0,
    historical_data={
        'open': [...],
        'high': [...],
        'low': [...],
        'close': [...],
        'volume': [...]
    },
    option_type="CE"  # or "PE"
)

# Update trailing stop
new_sl = strategy_engine.update_trailing_stop(
    current_price=55.0,
    entry_price=50.0,
    current_stop_loss=48.0,
    trailing_type=TrailingStopType.SUPERTREND_1X,
    supertrend_value=52.0,
    position_type="LONG"
)
```

**Output:**
```python
TradingSignal(
    signal_type=SignalType.BUY,
    price=50.0,
    confidence=0.85,
    reason="SuperTrend reversal to uptrend + Price above EMA",
    indicators={
        "ema": 49.5,
        "supertrend_1x": 48.0,
        "supertrend_2x": 46.0,
        "trend_1x": 1,
        "trend_2x": 1
    },
    entry_price=50.0,
    stop_loss=48.0,  # SuperTrend 1x level
    target_price=54.0,  # 1:2 Risk-Reward
    trailing_stop_config={
        "type": "supertrend_1x",
        "supertrend_1x_value": 48.0,
        "supertrend_2x_value": 46.0,
        "multiplier_1x": 3.0,
        "multiplier_2x": 6.0
    },
    timestamp="2025-01-08T10:30:00"
)
```

---

### 3. Trade Preparation (`trade_prep.py`)

**Purpose:** Orchestrates complete trade preparation with validation

**Process:**
1. ✅ Validate user's active broker configuration
2. ✅ Check available capital (paper or live)
3. ✅ Fetch current option premium from live market data
4. ✅ Calculate position size based on capital and risk
5. ✅ Validate sufficient capital available
6. ✅ Fetch historical candle data for strategy
7. ✅ Generate trading signal using strategy engine
8. ✅ Calculate risk-reward ratio
9. ✅ Prepare complete trade execution details

**Key Methods:**
```python
prepared_trade = trade_prep_service.prepare_trade(
    user_id=1,
    stock_symbol="RELIANCE",
    option_instrument_key="NSE_FO|12345",
    option_type="CE",
    strike_price=2500,
    expiry_date="2025-01-16",
    lot_size=250,
    db=db,
    trading_mode=TradingMode.LIVE
)
```

**Output:**
```python
PreparedTrade(
    status=TradeStatus.READY,  # or PENDING_SIGNAL, INSUFFICIENT_CAPITAL, NO_ACTIVE_BROKER
    stock_symbol="RELIANCE",
    option_instrument_key="NSE_FO|12345",
    option_type="CE",
    strike_price=2500,
    expiry_date="2025-01-16",
    current_premium=50.25,
    lot_size=250,
    signal={...},  # TradingSignal details
    capital_allocation={...},  # CapitalAllocation details
    risk_reward_ratio=2.0,
    entry_price=50.25,
    stop_loss=48.00,
    target_price=54.50,
    trailing_stop_config={...},
    position_size_lots=20,
    total_investment=251250,  # 50.25 * 250 * 20
    max_loss_amount=251250,
    trading_mode="live",
    broker_name="Upstox",
    user_id=1,
    prepared_at="2025-01-08T10:30:00",
    valid_until="2025-01-08T10:45:00",  # 15 min validity
    metadata={
        "signal_confidence": 0.85,
        "signal_reason": "SuperTrend reversal to uptrend + Price above EMA",
        "capital_utilization_percent": 25.0,
        "risk_per_trade_percent": 2.0
    }
)
```

---

## Trading Modes

### Paper Trading
- **Capital**: Virtual ₹10,00,000 (10 Lakhs)
- **Execution**: Mock orders (no real broker API calls)
- **Purpose**: Testing, backtesting, learning
- **No capital risk**: All trades are simulated

### Live Trading
- **Capital**: Real funds from broker account
- **Execution**: Real orders via broker API (Upstox/Angel/Dhan)
- **Purpose**: Actual trading with real money
- **Requires**: Active broker with valid access token

---

## Configuration

### Capital Management
```python
# In capital_manager.py
paper_trading_capital = ₹10,00,000
max_capital_per_trade_percent = 20%  # Max 20% per position
max_risk_per_trade_percent = 2%      # Max 2% risk per trade
min_capital_buffer = 10%             # Keep 10% buffer
```

### Strategy Parameters
```python
# In strategy_engine.py
ema_period = 20                     # 20-period EMA
supertrend_period = 10              # ATR period
supertrend_multiplier_1x = 3.0      # Standard multiplier
supertrend_multiplier_2x = 6.0      # Conservative multiplier
default_risk_reward_ratio = 2.0     # 1:2 Risk-Reward
min_confidence_threshold = 0.60     # 60% minimum confidence
```

---

## Integration with Existing System

### After Stock Selection
```python
# In intelligent_stock_selection_service.py (already integrated)
# After final stock selection completes:

from services.enhanced_intelligent_options_selection import enhanced_options_service

options_result = await enhanced_options_service.enhance_selected_stocks_with_options(
    self.final_selections,
    selection_type="final"
)

# Now stocks have option contracts attached
```

### Prepare Trades from Enhanced Selections
```python
from services.trading_execution import trade_prep_service, TradingMode

# For each enhanced stock selection
for enhanced_stock in enhanced_selections:
    if enhanced_stock.selected_option_contract:
        prepared_trade = trade_prep_service.prepare_trade(
            user_id=current_user.id,
            stock_symbol=enhanced_stock.symbol,
            option_instrument_key=enhanced_stock.selected_option_contract.option_instrument_key,
            option_type=enhanced_stock.selected_option_contract.option_type,
            strike_price=enhanced_stock.selected_option_contract.strike_price,
            expiry_date=enhanced_stock.selected_option_contract.expiry_date,
            lot_size=enhanced_stock.selected_option_contract.lot_size,
            db=db,
            trading_mode=TradingMode.LIVE
        )

        if prepared_trade.status == TradeStatus.READY:
            # Execute trade (next step)
            pass
```

---

## Next Steps (To Be Implemented)

### 4. Trade Execution Handler
- Paper trading execution (mock orders)
- Live trading execution (real broker API)
- Order placement and tracking
- Position entry logging

### 5. Real-Time PnL Tracking
- Live position monitoring
- Real-time PnL calculation
- Mark-to-market updates
- WebSocket updates to UI

### 6. Position Manager
- Active position tracking
- Trailing stop loss updates
- Target/SL hit detection
- Auto position squaring
- Exit signal execution

### 7. UI Integration
- Real-time PnL display
- Position tracking dashboard
- Trade execution controls
- Paper vs Live mode toggle
- Active positions grid
- Trade history

---

## Database Schema (To Be Added)

### ActivePosition Table
```sql
CREATE TABLE active_positions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    stock_symbol VARCHAR(50),
    option_instrument_key VARCHAR(100),
    option_type VARCHAR(5),
    strike_price DECIMAL(10,2),
    expiry_date DATE,
    entry_price DECIMAL(10,2),
    entry_time TIMESTAMP,
    position_size_lots INTEGER,
    total_investment DECIMAL(15,2),
    current_price DECIMAL(10,2),
    current_pnl DECIMAL(15,2),
    current_pnl_percent DECIMAL(10,2),
    stop_loss DECIMAL(10,2),
    target_price DECIMAL(10,2),
    trailing_stop_type VARCHAR(50),
    status VARCHAR(20),  -- ACTIVE, CLOSED, SQUARED_OFF
    trading_mode VARCHAR(10),  -- PAPER, LIVE
    broker_name VARCHAR(50),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### TradeExecution Table
```sql
CREATE TABLE trade_executions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    position_id INTEGER REFERENCES active_positions(id),
    action VARCHAR(20),  -- ENTRY, EXIT, SL_HIT, TARGET_HIT
    price DECIMAL(10,2),
    quantity INTEGER,
    total_value DECIMAL(15,2),
    pnl DECIMAL(15,2),
    signal_type VARCHAR(20),
    signal_confidence DECIMAL(5,2),
    trading_mode VARCHAR(10),
    broker_order_id VARCHAR(100),
    executed_at TIMESTAMP
);
```

---

## Files Created

1. ✅ `services/trading_execution/capital_manager.py` - Capital and fund management
2. ✅ `services/trading_execution/strategy_engine.py` - SuperTrend + EMA strategy
3. ✅ `services/trading_execution/trade_prep.py` - Trade preparation and validation
4. ✅ `services/trading_execution/__init__.py` - Package initialization

## Files Modified

1. ✅ `services/enhanced_intelligent_options_selection.py` - Fixed import, simplified API
2. ✅ `services/intelligent_stock_selection_service.py` - Integrated automatic options enhancement

---

## Summary

The modular trading execution system is now ready with:

✅ **Capital Management**: Validates funds, calculates position sizes
✅ **Strategy Engine**: Generates SuperTrend + EMA signals with trailing stops
✅ **Trade Preparation**: Complete validation and preparation pipeline
✅ **Paper & Live Support**: Both modes supported
✅ **Risk Management**: 2% risk per trade, 20% max allocation
✅ **Integration Ready**: Works with stock selection and options enhancement

**Next**: Implement trade execution, real-time PnL tracking, and UI dashboard.
