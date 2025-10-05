# Auto-Trading Live Feed Implementation Guide

## 🎯 Overview

This document explains the **modular, simple auto-trading system** that connects live market data to strategy execution.

### **Core Concept:**
1. **Selected stocks** → Load from database
2. **WebSocket feed** → Get live data for SPOT (strategy) + OPTION (trading)
3. **Strategy runs** → On real-time spot price with historical OHLC
4. **Auto-execute** → When valid signal detected
5. **Manage position** → Trailing SL, PnL tracking, auto-exit

---

## 📁 File Structure

### **Main Service File:**
```
services/trading_execution/auto_trade_live_feed.py
```
- **Purpose:** Complete auto-trading orchestration
- **Dependencies:**
  - `ws_client.py` - WebSocket connection
  - `strategy_engine.py` - Strategy signals
  - `trade_prep.py` - Trade preparation
  - `execution_handler.py` - Trade execution

### **API Endpoints:**
```
router/trading_execution_router.py
```
- `POST /start-auto-trading` - Start auto-trading
- `POST /stop-auto-trading` - Stop auto-trading
- `GET /auto-trading-status` - Get current status

---

## 🔄 Data Flow

### **Step 1: Load Selected Instruments**
```python
# From database: SelectedStock table
{
    "symbol": "RELIANCE",
    "spot_instrument_key": "NSE_EQ|INE002A01018",     # For strategy
    "option_instrument_key": "NSE_FO|54321",          # For trading
    "option_type": "CE",
    "strike_price": 2800,
    "expiry_date": "2024-01-25",
    "lot_size": 250
}
```

### **Step 2: WebSocket Subscription**
```python
# Subscribe to BOTH keys for each stock
instrument_keys = [
    "NSE_EQ|INE002A01018",  # Spot for strategy
    "NSE_FO|54321"          # Option for premium
]
```

### **Step 3: Live Data Processing**

#### **A. Spot Data (for Strategy)**
```python
# Receive from WebSocket
{
    "NSE_EQ|INE002A01018": {
        "fullFeed": {
            "marketFF": {
                "ltpc": {"ltp": 2805.50},
                "marketOHLC": {
                    "ohlc": [
                        {
                            "interval": "I1",  # 1-minute candle
                            "open": 2800,
                            "high": 2810,
                            "low": 2795,
                            "close": 2805,
                            "vol": "15000"
                        }
                    ]
                }
            }
        }
    }
}

# Update instrument
instrument.live_spot_price = 2805.50
instrument.historical_spot_data['close'].append(2805.50)  # Rolling window of 50
```

#### **B. Option Data (for Premium)**
```python
# Receive from WebSocket
{
    "NSE_FO|54321": {
        "fullFeed": {
            "marketFF": {
                "ltpc": {"ltp": 125.50}
            }
        }
    }
}

# Update premium
instrument.live_option_premium = 125.50
```

### **Step 4: Strategy Execution**
```python
# Run strategy when we have 30+ candles
if len(instrument.historical_spot_data['close']) >= 30:
    signal = strategy_engine.generate_signal(
        current_price=instrument.live_spot_price,      # 2805.50
        historical_data=instrument.historical_spot_data,  # Last 50 candles
        option_type=instrument.option_type              # CE
    )

    # Signal validation
    if signal.signal_type == "BUY" and signal.confidence > 0.65:
        # AUTO-EXECUTE
        await execute_trade(instrument, signal)
```

### **Step 5: Trade Execution**
```python
# Prepare trade (capital, position size, SL, target)
prepared_trade = await trade_prep_service.prepare_trade(
    user_id=user_id,
    option_instrument_key="NSE_FO|54321",
    option_type="CE",
    strike_price=2800,
    lot_size=250,
    # ... other params
)

# Execute via broker
execution_result = execution_handler.execute_trade(prepared_trade, db)

# Update instrument state
instrument.state = POSITION_OPEN
instrument.entry_price = 125.50
instrument.current_stop_loss = 120.00  # From signal
instrument.target_price = 135.00       # From signal
```

### **Step 6: Position Management**

#### **A. Live PnL Tracking**
```python
# On every option premium update
current_price = 128.50  # Live premium
entry_price = 125.50
quantity = 250

pnl = (128.50 - 125.50) × 250 = ₹750
pnl_percent = (3.00 / 125.50) × 100 = 2.39%
```

#### **B. Trailing Stop Loss**
```python
# Update SL when in profit
if current_price > entry_price:
    trailing_percent = 0.02  # 2%
    new_sl = current_price × (1 - 0.02) = 128.50 × 0.98 = 125.93

    # Trail SL upward only
    instrument.current_stop_loss = max(120.00, 125.93) = 125.93
```

#### **C. Exit Conditions**
```python
# Check 1: Stop loss hit
if current_price <= current_stop_loss:
    close_position("STOP_LOSS_HIT")

# Check 2: Target hit
if current_price >= target_price:
    close_position("TARGET_HIT")

# Check 3: Time-based exit (3:20 PM)
if current_time >= "15:20":
    close_position("TIME_BASED_EXIT")
```

---

## 🚀 How to Use

### **1. Start Auto-Trading (API)**
```bash
POST /api/v1/trading/execution/start-auto-trading?trading_mode=paper
Authorization: Bearer <token>
```

**Response:**
```json
{
    "success": true,
    "message": "Auto-trading started successfully",
    "trading_mode": "paper",
    "broker": "Upstox",
    "monitored_stocks": 3,
    "stats": {
        "signals_generated": 0,
        "trades_executed": 0,
        "positions_closed": 0,
        "errors": 0
    }
}
```

### **2. Check Status**
```bash
GET /api/v1/trading/execution/auto-trading-status
```

**Response:**
```json
{
    "success": true,
    "is_running": true,
    "monitored_stocks_count": 3,
    "monitored_stocks": [
        {
            "symbol": "RELIANCE",
            "option_type": "CE",
            "strike_price": 2800,
            "state": "monitoring",
            "live_spot_price": 2805.50,
            "live_option_premium": 125.50,
            "last_signal": "BUY",
            "active_position_id": null
        }
    ],
    "stats": {
        "signals_generated": 15,
        "trades_executed": 2,
        "positions_closed": 1,
        "errors": 0
    }
}
```

### **3. Stop Auto-Trading**
```bash
POST /api/v1/trading/execution/stop-auto-trading
```

---

## 🔧 Configuration

### **Signal Validation Thresholds**
```python
# In auto_trade_live_feed.py
signal_confidence_threshold = 0.65  # 65% minimum confidence

# Validation logic
def _is_valid_signal(signal, option_type):
    # Must be BUY for CE, SELL for PE
    # Must have confidence > 65%
    # Cannot be HOLD signal
```

### **Trailing Stop Loss**
```python
# In auto_trade_live_feed.py
trailing_percent = 0.02  # 2% trailing

# For CE: Trail below current price when in profit
# For PE: Trail above current price when in profit
```

### **Exit Times**
```python
# Time-based exit
exit_time = "15:20"  # 3:20 PM daily

# Can be made dynamic based on expiry
if is_expiry_day:
    exit_time = "15:25"  # 3:25 PM on expiry
```

---

## 📊 State Machine

### **Instrument States:**
```
MONITORING → SIGNAL_FOUND → EXECUTING → POSITION_OPEN → POSITION_CLOSED
                                                ↓
                                             ERROR
```

### **State Transitions:**
1. **MONITORING:** Waiting for valid signal
   - Runs strategy on every spot price update
   - Validates signal type and confidence

2. **SIGNAL_FOUND:** Valid signal detected
   - Immediately moves to EXECUTING
   - Signal stored for reference

3. **EXECUTING:** Trade execution in progress
   - Prepares trade (capital, position size)
   - Executes via broker
   - On success → POSITION_OPEN
   - On failure → ERROR

4. **POSITION_OPEN:** Active position being managed
   - Updates PnL on every premium update
   - Calculates trailing SL
   - Checks exit conditions
   - On exit → POSITION_CLOSED

5. **POSITION_CLOSED:** Position closed
   - Final PnL calculated
   - Position deactivated
   - Returns to MONITORING for next signal

6. **ERROR:** Error state
   - Logs error
   - Can be manually reset to MONITORING

---

## 🎛️ Modular Components

### **1. WebSocket Layer**
- **File:** `services/upstox/ws_client.py`
- **Purpose:** Raw WebSocket connection to Upstox
- **Input:** Access token, instrument keys
- **Output:** Live market data via callback

### **2. Strategy Layer**
- **File:** `services/trading_execution/strategy_engine.py`
- **Purpose:** Generate trading signals
- **Input:** Current price, historical OHLC
- **Output:** Signal (BUY/SELL/HOLD) with SL and target

### **3. Execution Layer**
- **Files:**
  - `trade_prep.py` - Prepare trade with capital validation
  - `execution_handler.py` - Execute via broker
- **Input:** Prepared trade details
- **Output:** Execution result with trade ID

### **4. Position Management Layer**
- **File:** `auto_trade_live_feed.py` (position management methods)
- **Purpose:** Manage open positions
- **Features:**
  - Live PnL tracking
  - Trailing SL calculation
  - Exit condition checking
  - Position closing

---

## 🔍 Debugging & Monitoring

### **Check Logs:**
```bash
# Auto-trading service logs
grep "Auto-Trading" app.log

# WebSocket connection
grep "auto_trading WebSocket" app.log

# Strategy signals
grep "Valid signal for" app.log

# Trade execution
grep "Executing trade" app.log

# Position management
grep "Trailing SL updated" app.log
```

### **Monitor in Real-Time:**
```python
# Via API
GET /api/v1/trading/execution/auto-trading-status

# Check stats
{
    "signals_generated": 50,    # Total signals checked
    "trades_executed": 12,      # Trades executed
    "positions_closed": 8,      # Positions closed
    "errors": 2                 # Errors encountered
}
```

---

## ⚠️ Important Notes

### **1. Broker-Side Trailing SL:**
**Question:** Should trailing SL be handled here or broker-side?

**Answer:** **Handle here (application-side)** because:
- ✅ Most brokers don't support real-time trailing SL for options
- ✅ You have full control over trailing logic
- ✅ Can customize trailing % per stock/strategy
- ✅ Works across all brokers uniformly

**Alternative:** If broker supports trailing orders (like Zerodha GTT), you can:
```python
# Place bracket order with trailing SL
broker.place_bracket_order(
    symbol=instrument.option_instrument_key,
    quantity=250,
    price=125.50,
    stoploss=120.00,
    trailing_stoploss=2.0  # 2% trailing
)
```

### **2. Capital & Position Sizing:**
- All handled in `trade_prep.py`
- Uses 20% max capital per trade
- 2% max risk per trade
- Automatically calculates lots based on premium and lot size

### **3. Multiple Stocks:**
- Service handles multiple stocks simultaneously
- Each stock has independent state and position
- WebSocket feeds all stocks with single connection

### **4. Paper vs Live Trading:**
- Paper mode: Uses mock capital (₹10 lakhs)
- Live mode: Fetches real capital from broker
- Strategy and execution logic identical in both modes

---

## 🚦 Next Steps

### **1. Test with Paper Trading:**
```bash
# Start with paper mode
POST /start-auto-trading?trading_mode=paper

# Monitor status
GET /auto-trading-status

# Check positions
GET /active-positions
```

### **2. Enhance Strategy:**
- Add more indicators (RSI, MACD)
- Implement multiple strategy types
- Add strategy backtesting results

### **3. Add Frontend UI:**
- Auto-trading ON/OFF toggle
- Live monitoring dashboard
- Real-time signal notifications
- Position management controls

---

## 📝 Summary

**This implementation provides:**
✅ **Simple, modular architecture**
✅ **Live feed for spot (strategy) + option (trading)**
✅ **Real-time strategy execution**
✅ **Auto-execute on valid signals**
✅ **Trailing SL management**
✅ **Live PnL tracking**
✅ **Complete position lifecycle**

**No complexity, just focused auto-trading!**