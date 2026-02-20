# Trading Execution System - Complete Modular Architecture

## Overview
This document describes the complete modular trading execution system built for algorithmic options trading. The system is designed for deterministic execution, single-point risk authority, and support for both paper and live trading with full parity.

---

## System Flow (Stabilized February 2026)

```
1. STOCK SELECTION (intelligent_stock_selection_service.py)
   ↓
2. OPTIONS ENHANCEMENT (enhanced_intelligent_options_selection.py)
   ↓
3. MARKET DATA FEED (AutoTradeLiveFeed)
   - Candle-Gating (last_processed_candle_count)
   - Triggers Strategy ONLY on NEW completed candle
   ↓
4. STRATEGY SIGNAL (StrategyEngine)
   - Generates Spot-based signal
   - 2-candle trend confirmation
   ↓
5. TRADE PREPARATION (TradePrepService)
   - Receives signal
   - Validates position limits
   - Calculates charges-aware target (Net Profit guaranteed)
   ↓
6. TRADE ENTRY (AutoTradeLiveFeed + execution_handler)
   - Paper: Mock with 0.05% entry slippage
   - Live: Upstox V3 API
   ↓
7. REAL-TIME MONITORING (pnl_tracker.py)
   - SINGLE EXIT AUTHORITY
   - Manages SL, Target, Trailing, and Time-based exits
   - Captures Post-Trade Diagnostics
```

---

## Module Breakdown

### 1. Capital Manager (`capital_manager.py`)

**Purpose:** Manages trading capital and validates fund availability.

**Key Features:**
- ✅ Validates demat account with active access token (using IST consistency)
- ✅ Derives allocation strictly from `ActivePosition.is_active` status.
- ✅ Position Size Floor: Rejects trades if calculated lots <= 0 (Risk Protection).
- ✅ Maintains 10% capital buffer.

---

### 2. Strategy Engine (`strategy_engine.py`)

**Purpose:** Pure signal generator using SuperTrend + EMA.

**Key Features:**
- ✅ **Deterministic Signals**: Requires 2-candle trend confirmation.
- ✅ **Pure Long Bias**: Both CE and PE are handled as long premium trades.
- ✅ **Neutralized Exits**: Does NOT block exits; authority is delegated to PnL Tracker.

---

### 3. PnL Tracker (`pnl_tracker.py`)

**Purpose:** Sole authority for position lifecycle and risk control.

**Key Features:**
- ✅ **Single Exit Authority**: Manages SL hits, Target hits, and 3:20 PM Square-off.
- ✅ **Global Kill-Switch**: Monitors daily loss thresholds and halts new entries.
- ✅ **Post-Trade Diagnostics**: Every trade captures `realized_rr`, `time_in_trade`, and `exit_truth`.
- ✅ **Soft Guards**: Prevents loop crashes by correcting logic errors (e.g., target <= entry) with logging.

---

### 4. Auto-Trading Live Feed (`auto_trade_live_feed.py`)

**Purpose:** High-speed data ingestion and deterministic entry execution.

**Key Features:**
- ✅ **Candle-Gating**: Prevents over-trading by ensuring strategy runs only once per completed candle.
- ✅ **Restart Safety**: Initializes candle tracking on startup to prevent historical data bursts.
- ✅ **Entry-Only**: Zero exit authority. Handled purely via UI broadcasts for active positions.

---

## Post-Trade Diagnostics

Every closed trade stores mandatory metadata:
- `realized_rr`: Actual risk-reward ratio.
- `time_in_trade_min`: Duration from entry to exit.
- `exit_truth`: The raw reason for closure (e.g., STOP_LOSS_HIT).
- `diagnostic_check`: Health status of the trade data.

---

## Paper & Live Parity

The system ensures that paper trading results are conservative and realistic indicators of live performance.
- **Symmetry**: Identical risk rules and logic paths.
- **Slippage**: 0.05% applied to both Entry and Exit in Paper mode.

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
