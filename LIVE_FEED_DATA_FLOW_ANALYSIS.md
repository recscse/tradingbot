# Live Feed Data Flow Analysis

## Complete Data Flow Architecture

### 🔄 **Data Source Chain**
```
1. Upstox WebSocket (ws_client.py) → Raw Market Data
2. Centralized WS Manager → Data Processing & Validation  
3. Live Feed Manager → ZERO-DELAY Distribution
4. Trading Services → Real-time Processing
5. Unified WS Manager → UI Updates (Parallel)
```

## 📊 **Service-Specific Data Flow**

### **1. Gap Analysis (Premarket Candle Builder)**

**Data Source:** 
- Major liquid stocks (NIFTY 50, BANKNIFTY constituents)
- Activated only during premarket hours (9:00 AM - 9:08 AM IST)

**How it gets data:**
```python
# In premarket_candle_builder.py
await subscribe_to_live_feed(
    service_name="premarket_candle_builder",
    callback=self._process_live_feed_tick,
    instrument_keys=self._get_premarket_watchlist(),  # Major liquid stocks
    priority=2,  # High priority
    filter_func=self._filter_premarket_data  # Only premarket hours
)
```

**Watchlist Instruments:**
- RELIANCE, TCS, INFY, HDFCBANK, ICICIBANK, HDFC, ITC, LT, SBIN
- BHARTIARTL, KOTAKBANK, ASIANPAINT, MARUTI, HINDUNILVR, AXISBANK
- WIPRO, ULTRACEMCO, NESTLEIND, TITAN, POWERGRID, NTPC, ONGC
- COALINDIA, BAJFINANCE, M&M, SUNPHARMA, TECHM, HCLTECH, DRREDDY

**Data Processing:**
- Converts live data to `TickData` format
- Builds OHLC candles incrementally
- Calculates gaps vs previous day close
- Generates gap alerts for >1% movements

**Database Storage:**
- `PremarketCandle` table with OHLC data
- `GapDetectionAlert` table for significant gaps
- Auto-cleanup data older than 2 days

### **2. Breakout Detection (Enhanced Breakout Engine)**

**Data Source:**
- All F&O instruments from major indices (NIFTY50, BANKNIFTY, FINNIFTY, MIDCPNIFTY, SENSEX)
- Real-time processing during market hours

**How it gets data:**
```python
# In enhanced_breakout_engine.py
await subscribe_to_live_feed(
    service_name="enhanced_breakout_engine",
    callback=self._process_live_feed_data,
    instrument_keys=get_selected_fo_instruments(),  # F&O stocks
    priority=1,  # Highest priority
    filter_func=self._filter_breakout_candidates  # >0.5% moves, >1000 volume
)
```

**Instrument Sources:**
- From `data/fno_stock_list.json` - All F&O enabled stocks
- From `auto_stock_selection_service` - Selected trading stocks
- Ring buffer storage for ultra-fast processing (100 price points per stock)

**Breakout Types Detected:**
- Volume breakouts (volume_surge, unusual_volume)
- Momentum breakouts (strong_momentum, acceleration)  
- Technical breakouts (resistance_breakout, support_breakdown)
- Pattern breakouts (gap_up, gap_down, triangular_breakout)

**Real-time Processing:**
- Updates ring buffer with every tick
- Triggers analysis for >2% price movements
- Calculates breakout strength and confidence scores
- Broadcasts signals to UI immediately

### **3. Auto Trading Coordinator**

**Data Source:**
- Selected F&O stocks from stock selection service
- User-configured instruments for active trading sessions

**How it gets data:**
```python
# In auto_trading_coordinator.py
await subscribe_to_live_feed(
    service_name="auto_trading_coordinator", 
    callback=self._process_live_market_data,
    instrument_keys=[stock['instrument_key'] for stock in selected_stocks],
    priority=1,  # Highest priority for trading
    filter_func=self._filter_trading_data  # >0.1% moves, >1000 volume
)
```

**Real-time Trading Flow:**
1. **Live Data Processing:**
   - Updates current price cache
   - Calculates real-time P&L for positions
   - Monitors position risk metrics

2. **Strategy Execution:**
   - Processes data through Fibonacci + EMA strategy
   - Generates BUY/SELL signals
   - Executes trades via unified trading executor

3. **Risk Management:**
   - Checks position limits (max 5 positions)
   - Monitors daily loss limits
   - Updates margin utilization

4. **Trade Execution:**
   - Places orders through broker APIs
   - Updates position monitor
   - Logs trade history to database

### **4. UI Data Flow (Real-time Dashboard)**

**Parallel Data Stream:**
- UI gets data through `unified_websocket_manager.py` (separate from trading)
- No interference with trading data processing

**How UI gets data:**
```javascript
// In React components
const socket = io('/api/v1/ws/dashboard');

socket.on('live_prices_update', (data) => {
    // Update live prices in UI
    updateMarketData(data);
});

socket.on('breakout_signal', (data) => {
    // Show breakout alerts
    showBreakoutAlert(data.signal);
});

socket.on('trade_update', (data) => {
    // Update positions and P&L
    updateTradingDashboard(data);
});
```

**UI Updates Include:**
- Live price updates for watchlist
- Real-time P&L calculations
- Position monitoring
- Breakout alerts and signals
- Trade execution status
- Risk metrics and margin usage

## 🚀 **Performance Optimizations**

### **ZERO-DELAY Architecture:**
```python
# Direct callback execution in centralized_ws_manager.py
async def _handle_market_data(self, data: dict):
    # 🚀 EXECUTE DIRECT CALLBACKS FIRST (ZERO-DELAY)
    await self._execute_direct_callbacks(data)
    
    # Then process for UI (parallel, no delay to trading)
    await self._handle_feeds_data(data)
```

### **Priority System:**
1. **Priority 1:** Auto Trading Coordinator (fastest execution)
2. **Priority 1:** Enhanced Breakout Engine (breakout detection)  
3. **Priority 2:** Premarket Candle Builder (gap analysis)
4. **Separate:** UI updates via unified manager (no trading impact)

### **Data Filtering:**
- Each service gets only relevant instrument data
- Volume and price movement filters reduce unnecessary processing
- Time-based filters (premarket hours for gap analysis)

## 📈 **Real-time Features**

### **For Trading:**
- **Sub-millisecond latency** for price updates
- **Real-time P&L** calculations
- **Instant strategy signals** 
- **Immediate trade execution**
- **Live risk monitoring**

### **For UI:**
- **Live price updates** (1-2 second delay acceptable)
- **Real-time breakout alerts**
- **Position monitoring dashboard**
- **Live P&L charts**
- **Trade execution notifications**

### **For Analysis:**
- **Real-time gap detection** (premarket)
- **Breakout pattern recognition**
- **Volume surge alerts**
- **Technical level breaks**

## 🔧 **Configuration and Setup**

### **Service Initialization:**
```python
# In app.py lifespan events
async def startup_event():
    # 1. Initialize centralized WebSocket manager
    await centralized_manager.initialize()
    
    # 2. Initialize live feed manager  
    await live_feed_manager.initialize()
    
    # 3. Start trading services
    await enhanced_breakout_engine.start()
    await premarket_candle_service.start_monitoring()
    
    # 4. Initialize auto trading (when session active)
    # await auto_trading_coordinator.start_trading_session(...)
```

### **Instrument Data Sources:**
- **F&O Stocks:** `data/fno_stock_list.json` (500+ instruments)
- **Premarket Watchlist:** Top 30 liquid stocks hardcoded
- **Trading Stocks:** User selection + auto selection service
- **Index Data:** NIFTY50, BANKNIFTY, FINNIFTY constituents

### **Database Integration:**
- **Live prices** cached in memory (not persisted)
- **Breakout signals** stored in breakout tables  
- **Gap data** stored in premarket candle tables
- **Trade data** stored in trading session tables
- **P&L data** calculated real-time, stored periodically

## 🚨 **Error Handling & Fallbacks**

### **Connection Issues:**
- Automatic reconnection with exponential backoff
- Fallback to legacy WebSocket systems if live feed fails
- Data service integration as final fallback

### **Data Quality:**
- Price validation (non-zero, realistic ranges)
- Volume validation (minimum thresholds)
- Timestamp validation (market hours)
- Duplicate data filtering

### **Performance Monitoring:**
- Callback execution time tracking
- Message processing latency monitoring
- Error rate tracking per service
- Performance metrics exposed via `/health` endpoint

This architecture ensures that each service gets the most relevant data with optimal performance, while maintaining separation between trading execution and UI updates.