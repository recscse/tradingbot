# Auto-Start/Stop WebSocket Guide

## 🎯 Overview

The auto-trading system now has **intelligent auto-start and auto-stop** capabilities:

1. **Auto-Start:** WebSocket automatically starts at 9:15 AM when stocks are selected
2. **Auto-Stop:** WebSocket automatically stops when all positions are closed
3. **Scheduler:** Background service monitors market hours and stock selection

---

## 🔄 How It Works

### **Complete Flow:**

```
1. Enable Auto-Mode (One-Time)
   ↓
2. Scheduler Starts Monitoring
   ↓
3. At 9:15 AM: Check if stocks are selected
   ↓
4. If stocks selected → Auto-Start WebSocket
   ↓
5. WebSocket gets live feed for selected stocks
   ↓
6. Strategy runs on live data
   ↓
7. Auto-executes trades on signals
   ↓
8. Manages positions with trailing SL
   ↓
9. When all positions closed → Auto-Stop WebSocket
   ↓
10. Next day: Repeats from step 3
```

---

## 📁 New Files Created

### **1. Auto-Trade Scheduler**
**File:** `services/trading_execution/auto_trade_scheduler.py`

**Key Features:**
- ✅ Monitors market hours (9:15 AM - 3:30 PM)
- ✅ Checks stock selection status
- ✅ Auto-starts WebSocket at 9:15 AM when stocks are ready
- ✅ Auto-stops WebSocket when all positions closed
- ✅ Resets daily at midnight

**How It Works:**
```python
# Every 60 seconds, the scheduler checks:

# 1. Is it market hours?
if 9:15 AM <= current_time <= 3:30 PM:

    # 2. Are stocks selected?
    if stocks_selected_today and not auto_started_today:

        # 3. Is broker config active?
        if broker_config.access_token valid:

            # 4. Auto-start WebSocket
            start_auto_trading()
            auto_started_today = True

    # 5. Check if should stop
    if websocket_running:
        if all_positions_closed and no_stocks_monitoring:
            stop_auto_trading()
```

---

## 🚀 API Endpoints

### **1. Enable Auto-Mode (Start Scheduler)**
```bash
POST /api/v1/trading/execution/enable-auto-mode?trading_mode=paper
Authorization: Bearer <token>
```

**What It Does:**
- Starts the scheduler service
- Begins monitoring stock selection
- Will auto-start WebSocket at 9:15 AM when stocks are selected

**Response:**
```json
{
    "success": true,
    "message": "Auto-mode enabled - WebSocket will start automatically at 9:15 AM when stocks are selected",
    "trading_mode": "paper",
    "auto_start_time": "09:15 AM",
    "auto_stop": "When all positions closed"
}
```

### **2. Disable Auto-Mode (Stop Scheduler)**
```bash
POST /api/v1/trading/execution/disable-auto-mode
Authorization: Bearer <token>
```

**What It Does:**
- Stops the scheduler
- Stops auto-trading if running
- Disables auto-start functionality

**Response:**
```json
{
    "success": true,
    "message": "Auto-mode disabled successfully"
}
```

### **3. Get Status**
```bash
GET /api/v1/trading/execution/auto-trading-status
Authorization: Bearer <token>
```

**Response:**
```json
{
    "success": true,
    "auto_mode_enabled": true,          // Scheduler running
    "websocket_running": true,          // WebSocket active
    "auto_started_today": true,         // Already auto-started today
    "monitored_stocks_count": 3,
    "monitored_stocks": [...],
    "stats": {
        "signals_generated": 15,
        "trades_executed": 5,
        "positions_closed": 3,
        "errors": 0
    }
}
```

---

## 📊 Auto-Start Logic

### **Conditions for Auto-Start:**

All conditions must be met:
1. ✅ **Market hours:** Between 9:15 AM - 3:30 PM
2. ✅ **Not already started:** `auto_started_today == False`
3. ✅ **Stocks selected:** At least 1 stock in `SelectedStock` table for today
4. ✅ **Broker active:** User has active broker with valid access token
5. ✅ **Token valid:** Access token not expired

### **Auto-Start Timing:**
- Scheduler checks every 60 seconds
- First check at 9:15 AM will trigger auto-start
- Only starts once per day

### **Example Log:**
```
09:15:01 - Checking auto-start conditions...
09:15:01 - ✅ Market hours: Yes
09:15:01 - ✅ Stocks selected: 3 stocks
09:15:01 - ✅ Broker config: Upstox (token valid)
09:15:01 - 🚀 AUTO-STARTING auto-trading: 3 stocks selected
09:15:02 - ✅ Auto-trading started at 09:15:02
```

---

## 🛑 Auto-Stop Logic

### **Conditions for Auto-Stop:**

All conditions must be met:
1. ✅ **No active positions:** All positions are closed
2. ✅ **No stocks monitoring:** No stocks waiting for signals
3. ✅ **WebSocket running:** WebSocket is currently active

### **Auto-Stop Scenarios:**

**Scenario 1: All Targets Hit**
```
Stock 1: Position OPEN → Target HIT → Position CLOSED
Stock 2: Position OPEN → Target HIT → Position CLOSED
Stock 3: Position OPEN → Target HIT → Position CLOSED

✅ All positions closed → Auto-stop WebSocket
```

**Scenario 2: All Stop Loss Hit**
```
Stock 1: Position OPEN → SL HIT → Position CLOSED
Stock 2: Position OPEN → SL HIT → Position CLOSED
Stock 3: Position OPEN → SL HIT → Position CLOSED

✅ All positions closed → Auto-stop WebSocket
```

**Scenario 3: Time-Based Exit**
```
3:20 PM reached
Stock 1: Position OPEN → TIME EXIT → Position CLOSED
Stock 2: Position OPEN → TIME EXIT → Position CLOSED
Stock 3: Position OPEN → TIME EXIT → Position CLOSED

✅ All positions closed → Auto-stop WebSocket
```

### **Example Log:**
```
15:20:01 - Time-based exit triggered
15:20:01 - Closing position: RELIANCE - TIME_BASED_EXIT
15:20:01 - Closing position: INFY - TIME_BASED_EXIT
15:20:02 - ✅ Position closed: PnL = ₹2,500 (2.0%)
15:20:02 - ✅ Position closed: PnL = ₹1,200 (1.5%)
15:20:03 - Checking auto-stop...
15:20:03 - ✅ All positions closed
15:20:03 - ✅ No stocks monitoring
15:20:03 - 🛑 AUTO-STOPPING: All positions closed, no stocks monitoring
15:20:04 - ✅ Auto-trading stopped at 15:20:04
```

---

## ⏰ Daily Cycle

### **Typical Day Flow:**

```
12:00 AM - Scheduler resets auto_started_today flag
         ↓
09:00 AM - Stock selection completes (3 stocks selected)
         ↓
09:15 AM - Scheduler checks → Stocks found → Auto-start WebSocket
         ↓
09:15:30 - WebSocket connected, monitoring 3 stocks
         ↓
09:45:00 - Signal found for Stock 1 → Auto-execute
         ↓
10:30:00 - Signal found for Stock 2 → Auto-execute
         ↓
11:00:00 - Signal found for Stock 3 → Auto-execute
         ↓
14:00:00 - Stock 1 hits target → Position closed
         ↓
14:30:00 - Stock 2 hits SL → Position closed
         ↓
15:20:00 - Stock 3 time-based exit → Position closed
         ↓
15:20:05 - All positions closed → Auto-stop WebSocket
         ↓
15:30:00 - Market closes
         ↓
Next Day - Cycle repeats
```

---

## 🔧 Configuration

### **Market Hours:**
```python
# In auto_trade_scheduler.py
market_start_time = dt_time(9, 15)  # 9:15 AM
market_end_time = dt_time(15, 30)   # 3:30 PM
```

### **Check Interval:**
```python
# Scheduler checks every 60 seconds
check_interval = 60
```

### **Customization:**
You can modify market hours for different exchanges:
```python
# For international markets
market_start_time = dt_time(14, 30)  # 2:30 PM IST (US market open)
market_end_time = dt_time(21, 0)     # 9:00 PM IST
```

---

## 🎛️ State Machine

### **Scheduler States:**
```
STOPPED
   ↓ (enable-auto-mode)
RUNNING → Monitoring stock selection
   ↓
   ├─→ Stocks selected at 9:15 AM → Auto-start WebSocket
   │                                         ↓
   │                                  WebSocket RUNNING
   │                                         ↓
   │                                  Positions managed
   │                                         ↓
   │                                  All positions closed
   │                                         ↓
   └─────────────────────────────────→ Auto-stop WebSocket
   ↓
RUNNING → Wait for next day
```

---

## 🧪 Testing

### **Test Auto-Start:**

1. **Enable auto-mode:**
```bash
curl -X POST "http://localhost:8000/api/v1/trading/execution/enable-auto-mode?trading_mode=paper" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

2. **Select stocks** (via stock selection API or UI)

3. **Wait for 9:15 AM** (or change time for testing)

4. **Check logs:**
```bash
tail -f app.log | grep "AUTO-STARTING"
```

5. **Verify status:**
```bash
curl "http://localhost:8000/api/v1/trading/execution/auto-trading-status" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### **Test Auto-Stop:**

1. **Wait for all positions to close** (via SL/target/time)

2. **Check logs:**
```bash
tail -f app.log | grep "AUTO-STOPPING"
```

3. **Verify WebSocket stopped:**
```bash
curl "http://localhost:8000/api/v1/trading/execution/auto-trading-status" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Expected response:
```json
{
    "auto_mode_enabled": true,
    "websocket_running": false,  // ← Stopped
    "monitored_stocks_count": 0
}
```

---

## 🚨 Important Notes

### **1. Token Management:**
- Scheduler validates broker token before auto-start
- If token expired, auto-start will NOT happen
- Refresh token before 9:15 AM for auto-start

### **2. Stock Selection:**
- Stocks must be selected BEFORE 9:15 AM
- If stocks selected after 9:15 AM, next check (9:16 AM) will trigger auto-start
- Stock selection phase completes around 9:00 AM typically

### **3. Position Management:**
- WebSocket stops ONLY when ALL positions closed
- If 1 position still open, WebSocket continues
- Manual stop available via `/stop-auto-trading` endpoint

### **4. Daily Reset:**
- `auto_started_today` flag resets at midnight
- Allows fresh auto-start next trading day
- Scheduler continues running across days

---

## 📈 Monitoring

### **Key Metrics to Monitor:**

1. **Scheduler Status:**
   - `auto_mode_enabled`: Is scheduler running?
   - `auto_started_today`: Did auto-start happen today?

2. **WebSocket Status:**
   - `websocket_running`: Is WebSocket active?
   - `monitored_stocks_count`: How many stocks being tracked?

3. **Position Status:**
   - Active positions count
   - States: monitoring, signal_found, executing, position_open, position_closed

4. **Performance:**
   - `signals_generated`: Total signals checked
   - `trades_executed`: Auto-executed trades
   - `positions_closed`: Completed trades

---

## ✅ Summary

**What Was Implemented:**

1. ✅ **Auto-Start Scheduler** (`auto_trade_scheduler.py`)
   - Monitors market hours
   - Checks stock selection
   - Auto-starts at 9:15 AM when ready

2. ✅ **Auto-Stop Logic**
   - Checks position status
   - Auto-stops when all closed
   - No manual intervention needed

3. ✅ **API Endpoints**
   - `/enable-auto-mode` - Start scheduler
   - `/disable-auto-mode` - Stop scheduler
   - `/auto-trading-status` - Check status (updated with scheduler info)

4. ✅ **Daily Cycle Management**
   - Resets at midnight
   - Handles market hours
   - Continues across days

**How to Use:**

```bash
# 1. Enable auto-mode (one-time)
POST /enable-auto-mode?trading_mode=paper

# 2. Select stocks (before 9:15 AM)
# (via stock selection service)

# 3. Sit back and relax!
# WebSocket will:
#   - Auto-start at 9:15 AM
#   - Run strategy on live data
#   - Auto-execute trades
#   - Manage positions
#   - Auto-stop when done

# 4. Check status anytime
GET /auto-trading-status
```

**The system is now fully automated!** 🚀