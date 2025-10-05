# Auto-Trading System - Complete Flow Explanation

**SIMPLIFIED & ACCURATE** - How Auto-Trading Works from Stock Selection to Trade Exit

---

## Quick Overview

```
Stock Selection (9 AM) → Live Feed Monitoring → Strategy Runs → Entry Signal →
Trade Execution (Paper/Live) → Position Monitoring → Trailing SL → Exit → Book Profit/Loss
```

---

## Phase 1: Stock Selection (9:00-9:15 AM)

### What Happens?
**Automated service runs at 9 AM daily to select 2 best stocks for trading**

### How It Works:

1. **Service**: `AutoStockSelectionService` runs automatically
2. **Analysis Steps**:
   - Analyzes market sentiment (Bullish/Bearish)
   - Checks ADR (global market cues)
   - Finds top performing sector
   - Filters stocks with high volume (>100K)
   - Selects 2 best F&O stocks

3. **Option Contract Selection**:
   - Calculates ATM (At The Money) strike price
   - If market is BULLISH → Selects CE (Call Option)
   - If market is BEARISH → Selects PE (Put Option)
   - Finds liquid option contract (high open interest)

4. **Stores in Database**:
   ```sql
   SelectedStock table:
   - symbol: "RELIANCE"
   - option_type: "CE"
   - strike_price: 3100
   - expiry_date: "2024-12-26"
   - option_instrument_key: "NSE_FO|RELIANCE24DEC3100CE"
   - premium: 45.50
   - lot_size: 250
   ```

**Result**: 2 stocks saved in database, ready for auto-execution

---

## Phase 2: User Initiates Auto-Execute

### What User Does:
1. Opens Auto Trading Page
2. Sees selected stocks (2 stocks)
3. Selects Trading Mode:
   - **Paper Trading** (default) - Virtual money, no real trades
   - **Live Trading** - Real broker API, real money
4. Selects Execution Mode:
   - **Single-Demat** - Execute on one broker
   - **Multi-Demat** - Execute across all active brokers
5. Clicks **"Execute All Selected Stocks"** button

---

## Phase 3: Trade Preparation (Per Stock)

### What Happens Internally:

#### **File**: `trade_prep.py` → `prepare_trade()` function

### Steps:

**Step 1: Get Broker Configuration**
```python
# Fetches active broker with valid access token
broker_config = db.query(BrokerConfig).filter(
    BrokerConfig.user_id == user_id,
    BrokerConfig.is_active == True,
    BrokerConfig.access_token.isnot(None)
).first()
```

**Step 2: Check Available Capital**
```python
capital_allocation = capital_manager.allocate_capital_for_trade(
    user_id=user_id,
    required_capital_estimate=premium * lot_size,
    trading_mode=trading_mode,  # paper or live
    db=db
)

# Returns:
# - available_capital: 100000
# - allocated_capital: 11375 (for this trade)
# - max_position_size_lots: 1
# - risk_per_trade_percent: 2.0
```

**Step 3: Get Live Option Premium**
```python
# Fetches current market price from Upstox API
current_premium = await get_current_ltp(option_instrument_key, access_token)
# Returns: 45.50 (current premium)
```

**Step 4: Run Strategy & Generate Signal**

Two strategy modes available:

#### **A. Spot Strategy (NEW - Default)**
```python
# Runs SuperTrend + EMA on SPOT price (not option premium)
signal = await spot_strategy_executor.generate_spot_based_signal(
    spot_instrument_key="NSE_EQ|INE002A01018",  # RELIANCE spot
    access_token=access_token,
    option_type="CE"
)

# Fetches:
# 1. Spot historical data (100 candles, 1-minute interval)
# 2. Current spot price (LTP)
# 3. Calculates SuperTrend (period=10, multiplier=3.0)
# 4. Calculates EMA (period=20)

# Signal Logic:
# BUY (CE): spot_price > supertrend AND spot_price > ema
# BUY (PE): spot_price < supertrend AND spot_price < ema

# Returns:
signal = {
    "signal_type": "BUY",
    "entry_price": 45.50,  # option premium
    "stop_loss": 3095.20,  # spot price level
    "target": 3115.40,     # spot price level
    "confidence": 0.85,
    "spot_price": 3105.60,
    "supertrend": 3095.20,
    "ema": 3100.30
}
```

#### **B. Option Premium Strategy (Fallback)**
```python
# If spot strategy fails, uses option premium-based strategy
signal = strategy_engine.generate_signal(
    current_price=current_premium,
    historical_data=option_premium_history,
    option_type="CE"
)
```

**Step 5: Calculate Position Size**
```python
# Based on risk management
max_loss_per_trade = allocated_capital * 0.02  # 2% risk
position_size_lots = 1  # calculated based on capital
total_investment = current_premium * lot_size * position_size_lots
# Example: 45.50 * 250 * 1 = 11,375
```

**Step 6: Calculate Risk-Reward Ratio**
```python
risk = entry_price - stop_loss  # 45.50 - 40.00 = 5.50
reward = target - entry_price   # 55.50 - 45.50 = 10.00
risk_reward_ratio = reward / risk  # 10.00 / 5.50 = 1.82 (Target: 1:2)
```

**Step 7: Prepare Trade Object**
```python
PreparedTrade(
    status="READY",
    stock_symbol="RELIANCE",
    option_instrument_key="NSE_FO|RELIANCE24DEC3100CE",
    option_type="CE",
    strike_price=3100,
    current_premium=45.50,
    entry_price=45.50,
    stop_loss=40.00,
    target_price=55.50,
    position_size_lots=1,
    total_investment=11375,
    max_loss_amount=1375,
    risk_reward_ratio=1.82,
    trading_mode="paper",
    broker_name="upstox"
)
```

---

## Phase 4: Trade Execution

### **File**: `execution_handler.py` → `execute_trade()` function

### Paper Trading Mode:
```python
if trading_mode == "paper":
    # Simulated execution - NO real broker API call
    order_result = {
        "order_id": f"PAPER_{uuid4()}",
        "status": "COMPLETED",
        "filled_price": entry_price + slippage,  # 45.50 + 0.10 = 45.60
        "filled_quantity": quantity
    }

    # Slippage calculation (realistic simulation):
    slippage = entry_price * 0.002  # 0.2% slippage
```

### Live Trading Mode:
```python
if trading_mode == "live":
    # Real broker API call
    order_result = await broker_client.place_order(
        instrument_key=option_instrument_key,
        quantity=quantity,
        order_type="MARKET",  # or "LIMIT"
        price=entry_price,
        transaction_type="BUY"
    )

    # Returns actual broker order ID and fill details
```

### Stores in Database:
```python
# Creates AutoTradeExecution record
trade_execution = AutoTradeExecution(
    trade_id="TRADE_123_20241226_001",
    user_id=user_id,
    symbol="RELIANCE",
    instrument_key="NSE_FO|RELIANCE24DEC3100CE",
    signal_type="BUY_CE",
    entry_price=45.60,  # with slippage
    quantity=250,
    lot_size=250,
    stop_loss=40.00,
    target_1=55.50,
    trailing_stop_config={"enabled": True, "trigger_at_profit_percent": 50},
    order_id="UPSTOX_241226001" or "PAPER_uuid",
    status="OPEN",
    trading_mode="paper",
    entry_time=datetime.now()
)

# Creates ActivePosition record for monitoring
active_position = ActivePosition(
    user_id=user_id,
    trade_execution_id=trade_execution.id,
    symbol="RELIANCE",
    instrument_key="NSE_FO|RELIANCE24DEC3100CE",
    entry_price=45.60,
    current_price=45.60,
    quantity=250,
    current_pnl=0,
    current_stop_loss=40.00,
    is_active=True
)
```

---

## Phase 5: Live Feed Data Monitoring

### How Live Data Flows:

**Data Source**: Upstox WebSocket (Real-time market feed)

1. **WebSocket Connection** (`services/upstox/ws_client.py`):
   ```python
   # Subscribes to option instrument for live prices
   ws.subscribe([
       "NSE_FO|RELIANCE24DEC3100CE"
   ])
   ```

2. **Receives Live Feed** (Every ~100ms-1sec):
   ```json
   {
       "type": "live_feed",
       "feeds": {
           "NSE_FO|RELIANCE24DEC3100CE": {
               "ltpc": {
                   "ltp": 46.20,  // Current premium
                   "ltt": "1757308567467"
               }
           }
       }
   }
   ```

3. **Centralized Manager Processes** (`centralized_ws_manager.py`):
   ```python
   # Updates instrument registry with latest price
   instrument_registry.update_price(
       instrument_key="NSE_FO|RELIANCE24DEC3100CE",
       ltp=46.20
   )
   ```

4. **Market Engine Stores** (`realtime_market_engine.py`):
   ```python
   # In-memory cache of all instrument prices
   market_engine.instruments = {
       "NSE_FO|RELIANCE24DEC3100CE": {
           "current_price": 46.20,
           "last_updated": datetime.now()
       }
   }
   ```

---

## Phase 6: Real-Time Position Monitoring

### **File**: `pnl_tracker.py` → Runs every 1 second

### Monitoring Loop:

```python
while is_running:
    # Step 1: Get all active positions
    active_positions = db.query(ActivePosition).filter(is_active=True).all()

    for position in active_positions:
        # Step 2: Get current price from market engine
        current_price = market_engine.get_price(position.instrument_key)
        # Returns: 46.20 (current premium)

        # Step 3: Calculate PnL
        pnl = (current_price - entry_price) * quantity
        # = (46.20 - 45.60) * 250 = 150

        pnl_percent = (pnl / total_investment) * 100
        # = (150 / 11400) * 100 = 1.32%

        # Step 4: Update highest price reached
        if current_price > position.highest_price_reached:
            position.highest_price_reached = current_price

        # Step 5: Check trailing stop loss
        updated_sl = check_trailing_stop_loss(position, current_price)

        # Step 6: Check exit conditions
        should_exit, exit_reason = check_exit_conditions(
            position,
            current_price
        )

        # Step 7: Update database
        position.current_price = current_price
        position.current_pnl = pnl
        position.current_stop_loss = updated_sl

        # Step 8: Broadcast update via WebSocket to UI
        broadcast_pnl_update({
            "position_id": position.id,
            "current_price": 46.20,
            "pnl": 150,
            "pnl_percent": 1.32,
            "stop_loss": updated_sl
        })

        # Step 9: Exit if conditions met
        if should_exit:
            close_position(position, current_price, exit_reason)

    await asyncio.sleep(1)  # Wait 1 second, repeat
```

---

## Phase 7: Trailing Stop Loss Logic

### How Trailing SL Works:

**Configuration** (Set during trade preparation):
```python
trailing_stop_config = {
    "enabled": True,
    "trigger_at_profit_percent": 50,  # Activate at 50% of target
    "trail_by_percent": 30,           # Trail 30% from highest
    "type": "percentage"
}
```

### Activation Logic:

```python
def check_trailing_stop_loss(position, current_price):
    trade = get_trade_execution(position.trade_execution_id)

    # Calculate current profit percent
    target_profit = trade.target_1 - trade.entry_price  # 55.50 - 45.60 = 9.90
    current_profit = current_price - trade.entry_price  # 46.20 - 45.60 = 0.60
    profit_percent = (current_profit / target_profit) * 100  # 6.06%

    # Trigger condition: Profit >= 50% of target
    if profit_percent >= 50:  # 6.06% < 50%, NOT ACTIVATED YET
        position.trailing_stop_triggered = True

        # Calculate trailing SL: 30% below highest price
        trailing_sl = position.highest_price_reached * 0.70

        # Use trailing SL if higher than original SL
        if trailing_sl > trade.stop_loss:
            return trailing_sl

    return trade.stop_loss  # Return original SL if trailing not active
```

### Example Scenario:

| Time | Current Price | Profit % | Highest | Trailing Active? | Stop Loss |
|------|---------------|----------|---------|------------------|-----------|
| 10:00 | 45.60 | 0% | 45.60 | No | 40.00 (original) |
| 10:05 | 46.20 | 6% | 46.20 | No | 40.00 |
| 10:15 | 48.50 | 29% | 48.50 | No | 40.00 |
| 10:30 | 50.55 | 50% | 50.55 | **YES** | 50.55 * 0.70 = **35.39** |
| 10:45 | 52.00 | 65% | 52.00 | YES | 52.00 * 0.70 = **36.40** |
| 11:00 | 50.80 | 52% | 52.00 | YES | 36.40 (locked) |
| 11:05 | 49.20 | 36% | 52.00 | YES | 36.40 |

**Trailing SL protects profits by locking in gains as price moves up**

---

## Phase 8: Exit Conditions Check

### **File**: `pnl_tracker.py` → `_check_exit_conditions()` function

### Exit Triggers:

```python
def check_exit_conditions(position, trade, current_price, pnl_data):
    """
    Checks multiple exit conditions every second

    Returns: (should_exit: bool, exit_reason: str)
    """

    # 1. Target Hit (Take Profit)
    if current_price >= trade.target_1:
        return (True, "TARGET_HIT")

    # 2. Stop Loss Hit
    if current_price <= position.current_stop_loss:
        return (True, "STOP_LOSS_HIT")

    # 3. Trailing Stop Loss Hit
    if position.trailing_stop_triggered:
        if current_price <= position.current_stop_loss:
            return (True, "TRAILING_SL_HIT")

    # 4. Maximum Holding Time (Safety net)
    holding_duration = (datetime.now() - trade.entry_time).total_seconds() / 60
    if holding_duration > 300:  # 5 hours = 300 minutes
        return (True, "MAX_HOLDING_TIME")

    # 5. End of Day (3:15 PM cutoff)
    if datetime.now().time() >= time(15, 15):
        return (True, "EOD_EXIT")

    # 6. Expiry Day Exit (11 AM cutoff on expiry)
    if is_expiry_day(trade.expiry_date):
        if datetime.now().time() >= time(11, 0):
            return (True, "EXPIRY_DAY_EXIT")

    return (False, None)  # No exit condition met, continue holding
```

---

## Phase 9: Position Exit & PnL Booking

### When Exit Condition Triggers:

```python
async def close_position(position, trade, current_price, exit_reason, db):
    """
    Closes position and books profit/loss
    """

    # Step 1: Execute exit trade
    if trade.trading_mode == "paper":
        # Simulated exit with slippage
        exit_price = current_price - (current_price * 0.002)  # -0.2% slippage
        order_id = f"PAPER_EXIT_{uuid4()}"

    else:  # live trading
        # Real broker API sell order
        exit_order = await broker_client.place_order(
            instrument_key=trade.instrument_key,
            quantity=trade.quantity,
            order_type="MARKET",
            transaction_type="SELL"
        )
        exit_price = exit_order.filled_price
        order_id = exit_order.order_id

    # Step 2: Calculate final PnL
    gross_pnl = (exit_price - trade.entry_price) * trade.quantity
    # = (52.00 - 45.60) * 250 = 1,600

    # Brokerage charges (only for live trading)
    if trade.trading_mode == "live":
        brokerage = calculate_brokerage(trade.quantity, exit_price)
        net_pnl = gross_pnl - brokerage
    else:
        net_pnl = gross_pnl  # No charges in paper trading

    pnl_percentage = (net_pnl / trade.total_investment) * 100
    # = (1600 / 11400) * 100 = 14.04%

    # Step 3: Update trade execution record
    trade.exit_price = exit_price
    trade.exit_time = datetime.now()
    trade.exit_order_id = order_id
    trade.exit_reason = exit_reason
    trade.gross_pnl = gross_pnl
    trade.net_pnl = net_pnl
    trade.pnl_percentage = pnl_percentage
    trade.status = "CLOSED"

    # Step 4: Update active position
    position.is_active = False
    position.exit_time = datetime.now()

    # Step 5: Update user's capital (return capital + PnL)
    capital_manager.update_capital_after_trade(
        user_id=trade.user_id,
        trade_investment=trade.total_investment,
        pnl=net_pnl,
        trading_mode=trade.trading_mode,
        db=db
    )

    # Step 6: Broadcast exit notification via WebSocket
    broadcast_position_closed({
        "position_id": position.id,
        "symbol": trade.symbol,
        "exit_price": exit_price,
        "pnl": net_pnl,
        "pnl_percent": pnl_percentage,
        "exit_reason": exit_reason
    })

    # Step 7: Log trade
    logger.info(
        f"✅ Position closed: {trade.symbol} | "
        f"Entry: {trade.entry_price} | Exit: {exit_price} | "
        f"PnL: {net_pnl} ({pnl_percentage:.2f}%) | "
        f"Reason: {exit_reason}"
    )

    db.commit()
```

---

## Phase 10: Capital Management & Risk-Reward

### Capital Allocation Logic:

**File**: `capital_manager.py`

```python
def allocate_capital_for_trade(user_id, required_capital_estimate, trading_mode, db):
    """
    Allocates capital with 2% max risk per trade
    """

    # Step 1: Get available capital
    if trading_mode == "paper":
        available_capital = get_paper_trading_balance(user_id, db)
        # Default: 100,000 virtual money
    else:
        available_capital = get_broker_available_margin(user_id, db)
        # From broker API: available funds

    # Step 2: Calculate max allocation (2% risk rule)
    max_risk_per_trade = available_capital * 0.02  # 2%
    # = 100,000 * 0.02 = 2,000

    # Step 3: Calculate position size
    risk_per_lot = (entry_price - stop_loss) * lot_size
    # = (45.60 - 40.00) * 250 = 1,400

    max_lots = int(max_risk_per_trade / risk_per_lot)
    # = 2000 / 1400 = 1 lot (rounded down)

    allocated_capital = required_capital_estimate * max_lots
    # = 11,400 * 1 = 11,400

    return CapitalAllocation(
        available_capital=100000,
        allocated_capital=11400,
        max_position_size_lots=1,
        risk_per_trade_amount=1400,
        risk_per_trade_percent=2.0
    )
```

### Risk-Reward Calculation:

```python
# Risk: Entry to Stop Loss distance
risk = entry_price - stop_loss
# = 45.60 - 40.00 = 5.60 per share
# = 5.60 * 250 = 1,400 total risk

# Reward: Entry to Target distance
reward = target_price - entry_price
# = 55.50 - 45.60 = 9.90 per share
# = 9.90 * 250 = 2,475 total reward

# Risk-Reward Ratio
rr_ratio = reward / risk
# = 2475 / 1400 = 1.77 ≈ 1:1.8

# Minimum required: 1:2
# If rr_ratio < 2.0:
#     Adjust target or reject trade
```

---

## Phase 11: UI Real-Time Updates

### WebSocket Communication Flow:

1. **Backend Broadcasts** (every 1 second):
   ```python
   # From pnl_tracker.py
   socketio.emit('pnl_update', {
       "position_id": 123,
       "symbol": "RELIANCE",
       "current_price": 46.20,
       "pnl": 150,
       "pnl_percent": 1.32,
       "stop_loss": 40.00,
       "trailing_sl_active": False
   })
   ```

2. **Frontend Receives** (AutoTradingPage.js):
   ```javascript
   ws.onmessage = (event) => {
       const message = JSON.parse(event.data);

       if (message.type === "pnl_update") {
           // Update specific position in UI
           setActivePositions(prev =>
               prev.map(pos =>
                   pos.position_id === message.data.position_id
                       ? { ...pos, ...message.data }
                       : pos
               )
           );
       }
   };
   ```

3. **UI Displays**:
   - Current Premium: ₹46.20 (green if profit, red if loss)
   - PnL: +₹150 (+1.32%) ✅
   - Stop Loss: ₹40.00
   - Target: ₹55.50
   - Live chart updating every second

---

## Complete Example Trade Flow

### **Stock: RELIANCE | Mode: Paper Trading | Execution: Multi-Demat**

### Timeline:

**9:00 AM** - Stock Selection
```
✅ RELIANCE selected
- Option: 3100 CE
- Premium: ₹45.50
- Lot Size: 250
- Expiry: 26-Dec-2024
```

**10:00 AM** - User Executes Trade
```
✅ Prepare Trade:
- Capital Available: ₹100,000
- Allocated Capital: ₹11,375
- Position Size: 1 lot (250 qty)
- Entry Price: ₹45.60 (with slippage)
- Stop Loss: ₹40.00
- Target: ₹55.50
- Risk: ₹1,400
- Reward: ₹2,475
- R:R: 1:1.77

✅ Trade Executed (PAPER)
- Order ID: PAPER_ABC123
- Status: OPEN
- Entry Time: 10:00:00
```

**10:00-11:30 AM** - Live Monitoring
```
Every 1 second:
✅ Get current premium from live feed
✅ Calculate PnL
✅ Check trailing SL activation (50% profit)
✅ Check exit conditions
✅ Broadcast to UI
```

**11:30 AM** - Target Hit!
```
✅ Current Price: ₹55.60
✅ Target Price: ₹55.50
✅ Exit Condition: TARGET_HIT

✅ Close Position:
- Exit Price: ₹55.50 (with -0.2% slippage)
- Gross PnL: (55.50 - 45.60) × 250 = ₹2,475
- Net PnL: ₹2,475 (no brokerage in paper)
- PnL %: 21.71%
- Duration: 90 minutes

✅ Capital Updated:
- Invested: ₹11,400
- Returned: ₹13,875
- Profit: ₹2,475
- New Balance: ₹102,475
```

**Result**: ✅ Profit booked at ₹2,475 (21.71% return)

---

## Paper Trading vs Live Trading

### Paper Trading (Default):
- **No real money**: Uses virtual ₹100,000
- **No broker API**: Simulated order execution
- **Realistic slippage**: 0.2% slippage added
- **Instant fills**: Orders fill immediately
- **No brokerage**: Zero charges
- **Purpose**: Strategy testing, learning
- **Risk**: ZERO financial risk

### Live Trading:
- **Real money**: Uses actual broker balance
- **Real broker API**: Upstox/Angel One/Dhan API
- **Actual slippage**: Market-dependent slippage
- **Real fills**: May have partial fills
- **Real brokerage**: Actual transaction charges
- **Purpose**: Actual profit generation
- **Risk**: Can lose real money

### How Slippage Works (Paper Trading):

```python
# Buy Order Slippage
if transaction_type == "BUY":
    slippage = entry_price * 0.002  # +0.2%
    filled_price = entry_price + slippage
    # 45.50 + 0.09 = 45.60

# Sell Order Slippage
if transaction_type == "SELL":
    slippage = exit_price * 0.002  # -0.2%
    filled_price = exit_price - slippage
    # 55.50 - 0.11 = 55.39
```

**Why Slippage?** Simulates real market conditions where you don't always get exact price.

---

## Summary - Simplified Flow

```
1. STOCK SELECTION (9 AM)
   ↓
   Automated service selects 2 best F&O stocks
   ↓
   Saves in database with option contracts

2. USER EXECUTES (Anytime during market hours)
   ↓
   Clicks "Execute All Selected Stocks"
   ↓
   System prepares each trade

3. TRADE PREPARATION
   ↓
   Check capital → Get live premium → Run strategy → Generate signal
   ↓
   Calculate SL/Target → Calculate position size → Risk check

4. TRADE EXECUTION
   ↓
   Paper: Simulated with slippage
   Live: Real broker API call
   ↓
   Creates database records

5. LIVE MONITORING (Every 1 second)
   ↓
   WebSocket receives live feed → Update current price
   ↓
   Calculate PnL → Check trailing SL → Check exit conditions
   ↓
   Broadcast updates to UI

6. TRAILING STOP LOSS
   ↓
   Activates at 50% profit
   ↓
   Trails 30% below highest price
   ↓
   Locks in profits as price rises

7. EXIT CONDITIONS
   ↓
   Target hit OR SL hit OR Trailing SL OR EOD
   ↓
   Execute exit trade → Book PnL → Update capital

8. UI UPDATES
   ↓
   Real-time WebSocket updates every second
   ↓
   Shows live PnL, current price, exit notifications
```

---

## Key Points

✅ **Fully Automated**: Stock selection to exit, minimal manual work
✅ **Risk Managed**: 2% max risk per trade, 1:2 risk-reward minimum
✅ **Real-Time**: Live feed monitoring, 1-second PnL updates
✅ **Trailing SL**: Protects profits automatically
✅ **Multi-Exit**: Multiple safety mechanisms (SL, Target, EOD, Expiry)
✅ **Paper/Live**: Safe testing before real money
✅ **Modular**: Clean separation of concerns
✅ **Accurate**: Real broker API integration, realistic slippage

---

**Total System Files Involved**: ~15 core services
**Real-Time Updates**: Every 1 second
**Capital Safety**: 2% max risk per trade
**Exit Conditions**: 6 different triggers
**Monitoring**: 24/7 during market hours
