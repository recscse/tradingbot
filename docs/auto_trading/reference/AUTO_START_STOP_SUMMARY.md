# Auto-Start/Stop Implementation Summary

## ✅ What Was Implemented

### **Problem Solved:**
You wanted the WebSocket to:
1. **Auto-start** when stocks are selected at 9:15 AM
2. **Auto-stop** when all positions are closed
3. Run automatically without manual intervention

### **Solution Created:**

#### **1. Auto-Trade Scheduler** (`auto_trade_scheduler.py`)
A background service that:
- ✅ Monitors market hours (9:15 AM - 3:30 PM)
- ✅ Checks if stocks are selected
- ✅ Validates broker token
- ✅ Auto-starts WebSocket at 9:15 AM
- ✅ Auto-stops when all positions closed
- ✅ Resets daily at midnight

#### **2. Updated Auto-Trade Live Feed**
Added:
- ✅ `check_all_positions_closed()` method
- ✅ Better cleanup on stop
- ✅ Position state tracking

#### **3. New API Endpoints**
- ✅ `POST /enable-auto-mode` - Start scheduler
- ✅ `POST /disable-auto-mode` - Stop scheduler
- ✅ `GET /auto-trading-status` - Enhanced status with scheduler info

---

## 🔄 Complete Flow

```
┌─────────────────────────────────────────────────────────────┐
│  1. User Enables Auto-Mode (One-Time)                       │
│     POST /enable-auto-mode?trading_mode=paper               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  2. Scheduler Starts Background Monitoring                  │
│     - Checks every 60 seconds                               │
│     - Monitors market hours                                 │
│     - Checks stock selection status                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  3. Stock Selection Completes (before 9:15 AM)              │
│     - Stocks selected and stored in database                │
│     - Option contracts assigned                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  4. At 9:15 AM - Auto-Start Triggered                       │
│     ✅ Market hours check: Pass                             │
│     ✅ Stocks selected: 3 stocks found                      │
│     ✅ Broker config: Active with valid token               │
│     🚀 AUTO-START WebSocket                                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  5. WebSocket Connects                                      │
│     - Subscribes to SPOT instruments (for strategy)         │
│     - Subscribes to OPTION instruments (for premium)        │
│     - Total: 6 instruments (3 stocks × 2 keys each)         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  6. Live Data Processing                                    │
│     - Receives spot prices → Updates historical OHLC        │
│     - Receives option premiums → Updates live premium       │
│     - Strategy runs on every spot update                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  7. Strategy Generates Signals                              │
│     Stock 1: BUY signal (confidence 72%) → EXECUTE          │
│     Stock 2: HOLD signal → Wait                             │
│     Stock 3: BUY signal (confidence 68%) → EXECUTE          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  8. Positions Managed                                       │
│     - Live PnL tracking                                     │
│     - Trailing SL updates                                   │
│     - Exit condition monitoring                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  9. Positions Close                                         │
│     Stock 1: Target hit → CLOSED                            │
│     Stock 2: Never entered → MONITORING                     │
│     Stock 3: SL hit → CLOSED                                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  10. Auto-Stop Triggered                                    │
│      ✅ All positions closed                                │
│      ✅ No stocks in monitoring state                       │
│      🛑 AUTO-STOP WebSocket                                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  11. Next Day                                               │
│      - Scheduler resets at midnight                         │
│      - Waits for new stock selection                        │
│      - Cycle repeats from step 3                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Key Components

### **Auto-Start Logic:**
```python
# Scheduler checks every 60 seconds
while is_running:
    current_time = datetime.now().time()

    # 1. Check market hours
    if 9:15 AM <= current_time <= 3:30 PM:

        # 2. Check if already started today
        if not auto_started_today:

            # 3. Check stocks selected
            selected_stocks = db.query(SelectedStock).filter(
                selection_date == today,
                is_active == True
            ).count()

            if selected_stocks > 0:

                # 4. Validate broker token
                if broker_config.access_token_valid:

                    # 5. AUTO-START
                    start_auto_trading()
                    auto_started_today = True

    await asyncio.sleep(60)
```

### **Auto-Stop Logic:**
```python
# Scheduler checks if should stop
if auto_trade_live_feed.is_running:

    # 1. Check active positions
    active_positions = db.query(ActivePosition).filter(
        is_active == True
    ).count()

    # 2. Check monitoring state
    monitoring_count = 0
    for instrument in monitored_instruments.values():
        if instrument.state in ['monitoring', 'signal_found']:
            monitoring_count += 1

    # 3. Auto-stop conditions
    if active_positions == 0 and monitoring_count == 0:
        # All done - stop WebSocket
        await auto_trade_live_feed.stop()
```

---

## 🎯 Usage

### **Method 1: Enable Auto-Mode (Recommended)**
```bash
# 1. Enable once at start of day (or keep enabled)
curl -X POST "http://localhost:8000/api/v1/trading/execution/enable-auto-mode?trading_mode=paper" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response:
{
    "success": true,
    "message": "Auto-mode enabled - WebSocket will start automatically at 9:15 AM when stocks are selected",
    "trading_mode": "paper",
    "auto_start_time": "09:15 AM",
    "auto_stop": "When all positions closed"
}

# 2. That's it! System will:
#    - Auto-start at 9:15 AM when stocks ready
#    - Auto-execute trades on signals
#    - Auto-stop when all positions closed
```

### **Method 2: Manual Control (Optional)**
```bash
# Manual start (if auto-mode not enabled)
POST /api/v1/trading/execution/start-auto-trading?trading_mode=paper

# Manual stop
POST /api/v1/trading/execution/stop-auto-trading
```

### **Check Status:**
```bash
curl "http://localhost:8000/api/v1/trading/execution/auto-trading-status" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response:
{
    "success": true,
    "auto_mode_enabled": true,          // Scheduler running
    "websocket_running": true,          // WebSocket active
    "auto_started_today": true,         // Started today
    "monitored_stocks_count": 3,
    "monitored_stocks": [
        {
            "symbol": "RELIANCE",
            "state": "position_open",
            "live_spot_price": 2805.50,
            "live_option_premium": 128.50,
            "active_position_id": 123
        }
    ],
    "stats": {
        "signals_generated": 25,
        "trades_executed": 8,
        "positions_closed": 5,
        "errors": 0
    }
}
```

---

## 📁 Files Created/Modified

### **New Files:**
1. ✅ `services/trading_execution/auto_trade_scheduler.py`
   - Scheduler service for auto-start/stop
   - Market hours monitoring
   - Stock selection checking

2. ✅ `AUTO_START_STOP_GUIDE.md`
   - Complete guide with examples
   - Flow diagrams
   - Configuration details

3. ✅ `AUTO_START_STOP_SUMMARY.md` (this file)
   - Quick reference
   - Implementation summary

### **Modified Files:**
1. ✅ `services/trading_execution/auto_trade_live_feed.py`
   - Added `check_all_positions_closed()` method
   - Enhanced `stop()` method with cleanup

2. ✅ `router/trading_execution_router.py`
   - Added `/enable-auto-mode` endpoint
   - Added `/disable-auto-mode` endpoint
   - Enhanced `/auto-trading-status` endpoint

---

## ⏰ Timing

### **Auto-Start:**
- **Trigger Time:** 9:15 AM (configurable)
- **Check Interval:** Every 60 seconds
- **First Start:** At or after 9:15 AM when stocks ready
- **Daily Limit:** Once per day

### **Auto-Stop:**
- **Trigger:** When all positions closed
- **Check Interval:** Every 60 seconds
- **Conditions:**
  - No active positions
  - No stocks in monitoring state
  - WebSocket currently running

### **Daily Reset:**
- **Reset Time:** 12:00 AM (midnight)
- **What Resets:** `auto_started_today` flag
- **Effect:** Allows fresh auto-start next day

---

## 🧪 Testing Checklist

### **Pre-Test Setup:**
1. ✅ Enable auto-mode
2. ✅ Ensure broker token valid
3. ✅ Select stocks (via stock selection service)

### **Test Auto-Start:**
1. ✅ Wait for 9:15 AM (or modify time for testing)
2. ✅ Check logs for "AUTO-STARTING" message
3. ✅ Verify WebSocket connected
4. ✅ Confirm stocks being monitored

### **Test Auto-Stop:**
1. ✅ Wait for all positions to close
2. ✅ Check logs for "AUTO-STOPPING" message
3. ✅ Verify WebSocket stopped
4. ✅ Confirm stats show final counts

### **Test Daily Cycle:**
1. ✅ Run overnight (or modify midnight time)
2. ✅ Verify flag resets
3. ✅ Confirm auto-start works next day

---

## 🔍 Monitoring

### **Logs to Watch:**
```bash
# Auto-start
tail -f app.log | grep "AUTO-STARTING"

# Auto-stop
tail -f app.log | grep "AUTO-STOPPING"

# Scheduler activity
tail -f app.log | grep "Auto-trade scheduler"

# Position changes
tail -f app.log | grep "Position closed"
```

### **Key Indicators:**
- `auto_mode_enabled`: Scheduler status
- `websocket_running`: WebSocket status
- `auto_started_today`: Daily start flag
- `monitored_stocks_count`: Active monitoring
- `stats`: Performance metrics

---

## 🚨 Important Notes

### **1. Stock Selection Timing:**
- Stocks should be selected BEFORE 9:15 AM
- If selected after, next check will trigger auto-start
- Stock selection typically completes by 9:00 AM

### **2. Broker Token:**
- Must be valid at 9:15 AM for auto-start
- Refresh token before market open
- Scheduler validates before starting

### **3. Position Management:**
- WebSocket stops ONLY when ALL positions closed
- If any position open, continues running
- Manual stop available anytime

### **4. Market Hours:**
- Configurable in `auto_trade_scheduler.py`
- Default: 9:15 AM - 3:30 PM
- After hours: WebSocket auto-stops

---

## ✅ Summary

**What You Have Now:**

1. ✅ **Fully Automated System:**
   - Enable auto-mode once
   - WebSocket starts automatically
   - Trades execute automatically
   - Positions managed automatically
   - WebSocket stops automatically

2. ✅ **Smart Scheduling:**
   - Monitors market hours
   - Checks stock selection
   - Validates broker config
   - Resets daily

3. ✅ **Position-Aware:**
   - Knows when to stop
   - Waits for all closures
   - Clean shutdown

4. ✅ **Easy Control:**
   - Simple enable/disable
   - Real-time status
   - Manual override available

**How to Use:**
```bash
# One command to rule them all:
POST /enable-auto-mode?trading_mode=paper

# Then sit back and let it run!
```

**The system is now fully hands-free!** 🚀