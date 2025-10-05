# Data Flow: Stock Selection → Strategy Execution

## 📊 Complete Data Flow Visualization

```
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 1: STOCK SELECTION (Before 9:15 AM)                           │
│  File: services/enhanced_intelligent_options_selection.py           │
└─────────────────────────────────────────────────────────────────────┘
                            ↓
            Stores in Database: SelectedStock Table
                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│  Database Record Example:                                            │
│  {                                                                   │
│      "symbol": "RELIANCE",                                          │
│      "instrument_key": "NSE_EQ|INE002A01018",  ← SPOT for strategy  │
│      "option_type": "CE",                                           │
│      "option_contract": {                      ← JSON field         │
│          "option_instrument_key": "NSE_FO|54321",  ← For trading    │
│          "strike_price": 2800,                                      │
│          "expiry_date": "2024-01-25",                              │
│          "premium": 125.50,                                        │
│          "lot_size": 250,                                          │
│          "delta": 0.65,                                            │
│          "gamma": 0.02,                                            │
│          "theta": -15.5                                            │
│      }                                                              │
│  }                                                                  │
└─────────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 2: AUTO-START AT 9:15 AM                                      │
│  File: services/trading_execution/auto_trade_scheduler.py           │
│                                                                      │
│  Scheduler detects:                                                 │
│  ✅ Market hours: 9:15 AM                                           │
│  ✅ Stocks selected: 3 found in DB                                  │
│  ✅ Broker token: Valid                                             │
│  → Triggers: start_auto_trading()                                   │
└─────────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 3: LOAD SELECTED INSTRUMENTS                                  │
│  File: auto_trade_live_feed.py → _load_selected_instruments()      │
│                                                                      │
│  Code:                                                              │
│  selected_stocks = db.query(SelectedStock).filter(                 │
│      selection_date == today,                                      │
│      is_active == True,                                            │
│      option_contract.isnot(None)  ← Must have option               │
│  ).all()                                                           │
│                                                                      │
│  For each stock:                                                    │
│  1. Parse option_contract JSON                                      │
│  2. Get spot_instrument_key (for strategy)                         │
│  3. Get option_instrument_key (for trading)                        │
│  4. Create AutoTradeInstrument object                              │
└─────────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 4: CREATE AUTO-TRADE INSTRUMENT                               │
│                                                                      │
│  instrument = AutoTradeInstrument(                                  │
│      stock_symbol="RELIANCE",                                       │
│      spot_instrument_key="NSE_EQ|INE002A01018",  ← For strategy    │
│      option_instrument_key="NSE_FO|54321",       ← For trading     │
│      option_type="CE",                                             │
│      strike_price=2800,                                            │
│      expiry_date="2024-01-25",                                     │
│      lot_size=250,                                                 │
│      historical_spot_data={           ← Will be filled by WS       │
│          'open': [],                                               │
│          'high': [],                                               │
│          'low': [],                                                │
│          'close': [],                                              │
│          'volume': []                                              │
│      }                                                             │
│  )                                                                 │
│                                                                      │
│  Store: monitored_instruments[option_key] = instrument             │
└─────────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 5: PREPARE WEBSOCKET SUBSCRIPTION                             │
│  File: auto_trade_live_feed.py → _prepare_subscription_keys()      │
│                                                                      │
│  For each instrument:                                               │
│      keys.add(instrument.spot_instrument_key)   ← SPOT for strategy│
│      keys.add(instrument.option_instrument_key) ← OPTION for PnL   │
│                                                                      │
│  Result for 3 stocks:                                               │
│  [                                                                  │
│      "NSE_EQ|INE002A01018",  ← RELIANCE spot                       │
│      "NSE_FO|54321",         ← RELIANCE option                     │
│      "NSE_EQ|INE009A01021",  ← INFY spot                           │
│      "NSE_FO|54322",         ← INFY option                         │
│      "NSE_EQ|INE467B01029",  ← TCS spot                            │
│      "NSE_FO|54323"          ← TCS option                          │
│  ]                                                                  │
│  Total: 6 instrument keys (3 stocks × 2 keys each)                │
└─────────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 6: START WEBSOCKET CONNECTION                                 │
│  File: services/upstox/ws_client.py                                │
│                                                                      │
│  ws_client = UpstoxWebSocketClient(                                │
│      access_token=broker_token,                                    │
│      instrument_keys=[6 keys],                                     │
│      callback=_handle_market_data,  ← Data comes here              │
│      subscription_mode="full"       ← Get full OHLC data           │
│  )                                                                 │
│                                                                      │
│  Connects to: wss://api.upstox.com/v3/feed/market-data-feed        │
│  Subscribes to: 6 instruments                                      │
└─────────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 7: RECEIVE LIVE FEED DATA                                     │
│  WebSocket sends data every tick (real-time)                        │
│                                                                      │
│  Raw WebSocket Data:                                                │
│  {                                                                  │
│      "type": "live_feed",                                          │
│      "feeds": {                                                    │
│          "NSE_EQ|INE002A01018": {     ← SPOT DATA                  │
│              "fullFeed": {                                         │
│                  "marketFF": {                                     │
│                      "ltpc": {                                     │
│                          "ltp": 2805.50  ← Live spot price         │
│                      },                                            │
│                      "marketOHLC": {                               │
│                          "ohlc": [                                 │
│                              {                                     │
│                                  "interval": "I1",  ← 1-min candle │
│                                  "open": 2800,                     │
│                                  "high": 2810,                     │
│                                  "low": 2795,                      │
│                                  "close": 2805,                    │
│                                  "vol": "15000"                    │
│                              }                                     │
│                          ]                                         │
│                      }                                             │
│                  }                                                 │
│              }                                                     │
│          },                                                        │
│          "NSE_FO|54321": {            ← OPTION DATA                │
│              "fullFeed": {                                         │
│                  "marketFF": {                                     │
│                      "ltpc": {                                     │
│                          "ltp": 125.50  ← Live option premium      │
│                      }                                             │
│                  }                                                 │
│              }                                                     │
│          }                                                         │
│      }                                                             │
│  }                                                                  │
└─────────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 8: PROCESS SPOT DATA FOR STRATEGY                             │
│  File: auto_trade_live_feed.py → _update_spot_data()               │
│                                                                      │
│  1. Identify instrument by spot_instrument_key                      │
│     if inst.spot_instrument_key == "NSE_EQ|INE002A01018":          │
│         instrument = inst  (RELIANCE)                              │
│                                                                      │
│  2. Extract live spot price                                         │
│     ltp = 2805.50                                                  │
│     instrument.live_spot_price = Decimal('2805.50')               │
│                                                                      │
│  3. Extract 1-minute OHLC candle                                    │
│     for candle in ohlc_data:                                       │
│         if candle['interval'] == 'I1':  ← Find 1-min candle       │
│             instrument.historical_spot_data['open'].append(2800)   │
│             instrument.historical_spot_data['high'].append(2810)   │
│             instrument.historical_spot_data['low'].append(2795)    │
│             instrument.historical_spot_data['close'].append(2805)  │
│             instrument.historical_spot_data['volume'].append(15000)│
│                                                                      │
│  4. Maintain rolling window (last 50 candles)                       │
│     if len(historical_spot_data['close']) > 50:                   │
│         Keep only last 50                                          │
│                                                                      │
│  5. Check if ready for strategy                                     │
│     if len(historical_spot_data['close']) >= 30:                  │
│         ✅ Have enough data → Run strategy                         │
└─────────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 9: RUN STRATEGY ON LIVE DATA                                  │
│  File: auto_trade_live_feed.py → _run_strategy()                   │
│                                                                      │
│  Code Flow:                                                         │
│  if instrument.state == TradeState.MONITORING:                     │
│                                                                      │
│      # Generate signal using strategy engine                        │
│      signal = strategy_engine.generate_signal(                     │
│          current_price=instrument.live_spot_price,  ← 2805.50      │
│          historical_data=instrument.historical_spot_data,  ← OHLC  │
│          option_type=instrument.option_type  ← CE                  │
│      )                                                             │
│                                                                      │
│  Historical Data Passed to Strategy:                                │
│  {                                                                  │
│      'open': [2800, 2802, 2805, ...],    ← 50 candles             │
│      'high': [2810, 2812, 2815, ...],                             │
│      'low': [2795, 2797, 2800, ...],                              │
│      'close': [2805, 2808, 2810, ...],                            │
│      'volume': [15000, 16000, 14500, ...]                         │
│  }                                                                  │
└─────────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 10: STRATEGY ENGINE CALCULATION                               │
│  File: services/trading_execution/strategy_engine.py                │
│                                                                      │
│  def generate_signal(current_price, historical_data, option_type): │
│                                                                      │
│      # 1. Calculate SuperTrend indicator                            │
│      supertrend = calculate_supertrend(                            │
│          high=historical_data['high'],                             │
│          low=historical_data['low'],                               │
│          close=historical_data['close'],                           │
│          period=10,                                                │
│          multiplier=3.0                                            │
│      )                                                             │
│                                                                      │
│      # 2. Calculate EMA                                             │
│      ema = calculate_ema(                                          │
│          close=historical_data['close'],                           │
│          period=20                                                 │
│      )                                                             │
│                                                                      │
│      # 3. Generate signal                                           │
│      if current_price > supertrend and current_price > ema:       │
│          signal_type = SignalType.BUY                              │
│          confidence = 0.75                                         │
│                                                                      │
│      # 4. Calculate entry, SL, target                               │
│      entry_price = current_price                                   │
│      stop_loss = supertrend  (or current_price * 0.95)            │
│      target_price = entry_price + (entry_price - stop_loss) * 2   │
│                                                                      │
│      return TradingSignal(                                         │
│          signal_type=BUY,                                          │
│          entry_price=2805.50,                                      │
│          stop_loss=2680.00,                                        │
│          target_price=3056.50,                                     │
│          confidence=0.75,                                          │
│          reason="SuperTrend + EMA bullish"                         │
│      )                                                             │
│  }                                                                  │
└─────────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 11: VALIDATE SIGNAL                                           │
│  File: auto_trade_live_feed.py → _is_valid_signal()                │
│                                                                      │
│  def _is_valid_signal(signal, option_type):                        │
│                                                                      │
│      # Check 1: Not HOLD signal                                     │
│      if signal.signal_type == SignalType.HOLD:                     │
│          return False  ❌                                           │
│                                                                      │
│      # Check 2: Signal matches option direction                     │
│      if option_type == "CE" and signal.signal_type != BUY:         │
│          return False  ❌                                           │
│                                                                      │
│      if option_type == "PE" and signal.signal_type != SELL:        │
│          return False  ❌                                           │
│                                                                      │
│      # Check 3: Confidence threshold                                │
│      if signal.confidence < 0.65:  # 65% minimum                   │
│          return False  ❌                                           │
│                                                                      │
│      return True  ✅                                                │
│                                                                      │
│  Result: ✅ VALID (BUY signal, CE option, 75% confidence)           │
└─────────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 12: AUTO-EXECUTE TRADE                                        │
│  File: auto_trade_live_feed.py → _execute_trade()                  │
│                                                                      │
│  instrument.state = TradeState.EXECUTING                           │
│                                                                      │
│  # Prepare trade (capital validation, position sizing)              │
│  prepared_trade = await trade_prep_service.prepare_trade(          │
│      user_id=user_id,                                              │
│      option_instrument_key="NSE_FO|54321",  ← Option key           │
│      option_type="CE",                                             │
│      strike_price=2800,                                            │
│      lot_size=250,                                                 │
│      ...                                                           │
│  )                                                                  │
│                                                                      │
│  # Execute via broker                                               │
│  execution_result = execution_handler.execute_trade(               │
│      prepared_trade,                                               │
│      db                                                            │
│  )                                                                  │
│                                                                      │
│  # Update instrument state                                          │
│  instrument.state = TradeState.POSITION_OPEN                       │
│  instrument.entry_price = 125.50                                   │
│  instrument.current_stop_loss = 120.00                             │
│  instrument.target_price = 135.00                                  │
└─────────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 13: PROCESS OPTION DATA FOR PNL                               │
│  File: auto_trade_live_feed.py → _update_option_data()             │
│                                                                      │
│  Every tick, WebSocket sends option premium:                        │
│  "NSE_FO|54321": { "ltpc": { "ltp": 128.50 } }                     │
│                                                                      │
│  instrument.live_option_premium = Decimal('128.50')                │
│                                                                      │
│  # Calculate PnL                                                    │
│  current_price = 128.50                                            │
│  entry_price = 125.50                                              │
│  quantity = 250 (1 lot)                                            │
│  pnl = (128.50 - 125.50) × 250 = ₹750                              │
│  pnl_percent = (3.00 / 125.50) × 100 = 2.39%                       │
│                                                                      │
│  # Update trailing SL                                               │
│  if current_price > entry_price:                                   │
│      new_sl = current_price × 0.98 = 125.93                        │
│      current_stop_loss = max(120.00, 125.93) = 125.93             │
│                                                                      │
│  # Check exit conditions                                            │
│  if current_price <= current_stop_loss: → Exit                    │
│  if current_price >= target_price: → Exit                         │
│  if time >= 3:20 PM: → Exit                                        │
└─────────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│  CONTINUOUS MONITORING                                              │
│                                                                      │
│  SPOT Data (every tick):                                            │
│    → Update live_spot_price                                        │
│    → Update historical_spot_data (1-min candles)                   │
│    → Run strategy (if monitoring or position_open)                 │
│    → Generate new signals                                          │
│                                                                      │
│  OPTION Data (every tick):                                          │
│    → Update live_option_premium                                    │
│    → Calculate PnL                                                 │
│    → Update trailing SL                                            │
│    → Check exit conditions                                         │
│                                                                      │
│  Position Management:                                               │
│    → SL hit → Close position → Auto-stop if all closed             │
│    → Target hit → Close position → Auto-stop if all closed         │
│    → Time exit → Close position → Auto-stop if all closed          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📝 Key Points

### **1. Data Sources:**
- **SPOT instrument** → For strategy calculation (SuperTrend + EMA on clean price)
- **OPTION instrument** → For premium and PnL calculation

### **2. Historical Data:**
- Comes from WebSocket (marketOHLC with I1 interval = 1-minute candles)
- Rolling window of 50 candles stored in memory
- Updated every minute with new candle

### **3. Strategy Runs When:**
- ✅ Instrument in MONITORING state (not in position)
- ✅ Have 30+ historical candles (enough for indicators)
- ✅ Every spot price update (real-time)

### **4. Trade Executes When:**
- ✅ Signal type matches option direction (BUY for CE, SELL for PE)
- ✅ Confidence >= 65%
- ✅ Not HOLD signal
- ✅ Instrument in MONITORING state

### **5. Position Managed By:**
- Live option premium updates (every tick)
- Trailing SL calculation (2% default)
- Exit condition checks (SL/Target/Time)
- Auto-stops WebSocket when all closed

---

**This is the complete data flow from stock selection to strategy execution!** 🚀