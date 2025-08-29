# Auto Stock Selection & Trading System

## Overview

This comprehensive modular system automatically selects stocks at 9:00 AM premarket based on market sentiment, ADR analysis, and sector momentum, then executes options trades with real-time monitoring and risk management.

## 🎯 Key Features

### 1. **Automated Stock Selection (9:00 AM)**
- **ADR Analysis**: Analyzes American Depositary Receipts for global market cues
- **Market Sentiment**: Multi-factor sentiment analysis (Nifty, VIX, FII/DII flows)
- **Sector Momentum**: Identifies top-performing sectors
- **Middle Stock Selection**: Selects middle-performing stocks from top sectors
- **Options Integration**: Automatic ATM strike price calculation and option contract selection

### 2. **Intelligent Option Type Decision**
- **Bullish Market**: Selects CE (Call Options)
- **Bearish Market**: Selects PE (Put Options)  
- **Contrarian Analysis**: Considers stocks moving against market sentiment
- **Volume Analysis**: Minimum 1L+ volume requirement

### 3. **Real-Time Trade Execution**
- **Paper Trading**: Safe simulation environment
- **Risk Management**: 2% risk per trade, maximum 2 concurrent positions
- **Stop Loss/Target**: 30% stop loss, 50% target for options
- **Trailing Stop**: 10% trailing stop after 20% profit
- **Time-based Exit**: Auto square-off at 3:20 PM

### 4. **Live Data Processing**
- **NumPy/Pandas**: Fast vectorized data processing
- **Real-time Price Updates**: WebSocket-based live feed
- **Position Monitoring**: 5-second update intervals
- **Market Data Hub**: Optimized data pipeline

### 5. **Comprehensive UI**
- **Stock Selection Display**: Visual cards with selection reasons
- **Trading Session Control**: Start/stop trading with one click
- **Real-time P&L**: Live profit/loss updates
- **Performance Analytics**: Win rate, best/worst trades
- **WebSocket Integration**: Real-time UI updates

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    AUTO STOCK TRADING SYSTEM                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌──────────────────┐                   │
│  │ Market Scheduler│    │   Live Feed      │                   │
│  │   (9:00 AM)     │    │    Adapter       │                   │
│  └─────────────────┘    └──────────────────┘                   │
│           │                       │                            │
│           v                       v                            │
│  ┌─────────────────┐    ┌──────────────────┐                   │
│  │ Auto Stock      │    │ Trade Execution  │                   │
│  │ Selection       │────│    Service       │                   │
│  │ Service         │    │                  │                   │
│  └─────────────────┘    └──────────────────┘                   │
│           │                       │                            │
│           v                       v                            │
│  ┌─────────────────┐    ┌──────────────────┐                   │
│  │    Database     │    │   WebSocket      │                   │
│  │   (Selected     │    │   Broadcasting   │                   │
│  │    Stocks)      │    │                  │                   │
│  └─────────────────┘    └──────────────────┘                   │
│           │                       │                            │
│           v                       v                            │
│  ┌─────────────────┐    ┌──────────────────┐                   │
│  │   REST API      │    │    React UI      │                   │
│  │   Endpoints     │────│   Components     │                   │
│  │                 │    │                  │                   │
│  └─────────────────┘    └──────────────────┘                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 📁 File Structure

```
services/
├── auto_stock_selection_service.py      # Main stock selection logic
├── execution/
│   └── auto_trade_execution_service.py  # Trade execution & monitoring
├── websocket/
│   └── auto_trading_websocket.py        # Real-time WebSocket updates
├── live_adapter.py                      # Live market data adapter
├── market_schedule_service.py           # Updated with auto selection integration
└── trading_stock_selector.py            # Enhanced with options integration

router/
└── auto_trading_routes.py               # REST API endpoints

ui/trading-bot-ui/src/components/common/
└── AutoStockSelection.js                # React UI component

database/models.py                        # Updated with new models
└── AutoTradingSession, SelectedStock, TradeExecution
```

## 🔧 Configuration

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/trading_db

# Trading Configuration
TRADE_MODE=PAPER                    # PAPER or LIVE
DEFAULT_QTY=50                      # Default lot size
RISK_PER_TRADE=2.0                  # Risk percentage per trade
MAX_CONCURRENT_TRADES=2             # Maximum positions

# Broker APIs (for live trading)
UPSTOX_API_KEY=your_key
UPSTOX_ACCESS_TOKEN=your_token
```

### User Configuration
```python
# Database: user_trading_config table
{
    "trade_mode": "PAPER",
    "default_qty": 50,
    "stop_loss_percent": 2.0,
    "target_percent": 4.0,
    "max_positions": 2,
    "enable_option_trading": True,
    "enable_auto_square_off": True
}
```

## 🚀 Getting Started

### 1. Installation
```bash
# Backend dependencies
pip install -r requirements.txt

# Frontend dependencies
cd ui/trading-bot-ui
npm install
```

### 2. Database Setup
```bash
# Run migrations
alembic upgrade head
```

### 3. Start Services
```bash
# Start backend
python app.py

# Start frontend (in separate terminal)
cd ui/trading-bot-ui
npm start
```

### 4. Access Application
- **Backend API**: http://localhost:8000
- **Frontend UI**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs

### 5. Navigate to Auto Trading
1. Open the application
2. Go to "Auto Stock Selection" page
3. Monitor daily selection at 9:00 AM
4. Use start/stop controls for trading sessions

## 📊 Daily Workflow

### 8:00 AM - Early Preparation
- FNO stock list refresh (Mondays)
- Instrument service initialization
- Database preparation

### 9:00 AM - Stock Selection
1. **Market Sentiment Analysis**
   - Base sentiment from analytics
   - Nifty trend analysis
   - FII/DII flow data
   - VIX volatility analysis

2. **ADR Correlation Analysis**
   - US market overnight performance
   - Indian ADR movement correlation
   - Composite sentiment scoring

3. **Sector Selection**
   - Top performing sector identification
   - Volume ratio analysis
   - Momentum scoring

4. **Stock Filtering**
   - Middle-performer selection
   - Volume threshold (1L+ minimum)
   - Options availability check
   - ATM strike calculation

5. **Database Storage**
   - Selected stocks with metadata
   - Option contract details
   - Selection reasoning

### 9:15-9:30 AM - Trading Preparation
- Position sizing calculation
- Stop loss/target determination
- Real-time price validation
- WebSocket registration

### 9:30 AM-3:30 PM - Active Trading
- Real-time position monitoring
- Stop loss/target management
- Trailing stop implementation
- P&L calculation

### 3:30 PM+ - Post-Market
- Position square-off
- Performance analysis
- Database cleanup
- Report generation

## 🎛️ API Endpoints

### Stock Selection
```http
GET /api/v1/auto-trading/selected-stocks
# Returns today's selected stocks with market sentiment

POST /api/v1/auto-trading/run-stock-selection
# Manually trigger stock selection (Admin only)
```

### Trading Session
```http
GET /api/v1/auto-trading/session-status
# Get current trading session status

POST /api/v1/auto-trading/start-session
# Start automated trading session

POST /api/v1/auto-trading/stop-session
# Stop automated trading session
```

### Performance
```http
GET /api/v1/auto-trading/active-trades
# Get current active trades

GET /api/v1/auto-trading/trading-history?days=7
# Get trading history

GET /api/v1/auto-trading/performance-summary
# Get performance summary
```

## 🔌 WebSocket Events

### Client → Server
```javascript
// Connect to auto trading updates
socket.on('connect', () => {
    socket.emit('subscribe_auto_trading');
});
```

### Server → Client
```javascript
// Stock selection update
socket.on('auto_stock_update', (data) => {
    // data.stocks: Array of selected stocks
    // data.selection_date: Selection date
});

// Trading session update
socket.on('trading_session_update', (data) => {
    // data.is_active: Trading session status
    // data.daily_pnl: Current P&L
    // data.active_trades: Number of active positions
});

// Trade execution
socket.on('trade_executed', (data) => {
    // data.symbol: Stock symbol
    // data.option_type: CE/PE
    // data.entry_price: Entry price
});

// Position update
socket.on('position_update', (data) => {
    // data.symbol: Stock symbol
    // data.current_price: Live price
    // data.pnl_percent: Current P&L percentage
});
```

## 🧪 Testing

### Run Integration Tests
```bash
python test_auto_stock_system.py
```

### Test Coverage
- ✅ Stock selection algorithm
- ✅ Database integration
- ✅ API endpoints
- ✅ WebSocket broadcasting
- ✅ Trade execution logic
- ✅ Live feed integration

## 📈 Performance Metrics

### Selection Accuracy
- **Target**: 70%+ successful selections daily
- **Measurement**: Win rate of selected stocks
- **Optimization**: Continuous backtesting and refinement

### Execution Speed
- **Stock Selection**: <30 seconds at 9:00 AM
- **Trade Execution**: <5 seconds per trade
- **Position Updates**: 5-second intervals
- **WebSocket Latency**: <100ms

### Risk Management
- **Maximum Daily Loss**: 5% of capital
- **Position Sizing**: 2% risk per trade
- **Stop Loss**: 30% for options
- **Maximum Positions**: 2 concurrent trades

## 🚨 Risk Warnings

1. **Paper Trading Default**: System starts in paper trading mode
2. **Market Hours Only**: Trades only during market hours
3. **Position Limits**: Automatic position limits enforced
4. **Stop Loss Mandatory**: All positions have stop losses
5. **Daily Loss Limits**: Trading stops if daily limits exceeded

## 🔧 Troubleshooting

### Common Issues

1. **No Stocks Selected**
   - Check market schedule service
   - Verify sector heatmap data
   - Review volume thresholds

2. **WebSocket Not Working**
   - Check unified WebSocket manager
   - Verify client connection
   - Review browser console

3. **Trades Not Executing**
   - Verify broker connection
   - Check market hours
   - Review risk limits

4. **API Errors**
   - Check database connection
   - Verify user authentication
   - Review service logs

### Debug Tools
```bash
# Check service status
curl http://localhost:8000/health

# View selected stocks
curl http://localhost:8000/api/v1/auto-trading/selected-stocks

# Monitor logs
tail -f logs/trading.log
```

## 🎯 Future Enhancements

1. **Machine Learning Integration**
   - LSTM price prediction
   - Pattern recognition
   - Sentiment analysis from news

2. **Multi-Asset Support**
   - Futures trading
   - Index options
   - Commodity options

3. **Advanced Strategies**
   - Pairs trading
   - Arbitrage opportunities
   - Volatility trading

4. **Risk Analytics**
   - VaR calculations
   - Stress testing
   - Portfolio optimization

5. **Mobile App**
   - React Native app
   - Push notifications
   - Offline capabilities

## 📞 Support

For issues or questions:
1. Check the logs in `logs/` directory
2. Run integration tests: `python test_auto_stock_system.py`
3. Review API documentation at `/docs`
4. Check database models in `database/models.py`

---

**⚠️ DISCLAIMER**: This system is for educational purposes. Always test thoroughly before using with real money. Past performance does not guarantee future results.