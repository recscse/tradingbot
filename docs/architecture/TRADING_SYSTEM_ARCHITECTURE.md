# 🎯 TRADING SYSTEM ARCHITECTURE DOCUMENTATION

## Overview

This document provides a comprehensive overview of the HFT-grade auto-trading system architecture, covering all components from strategy execution to trade monitoring and risk management.

## Table of Contents

1. [System Overview](#system-overview)
2. [Strategy Execution & Stock Selection](#strategy-execution--stock-selection)
3. [Stock Storage & Management](#stock-storage--management)
4. [Option Contracts & Option Chain Storage](#option-contracts--option-chain-storage)
5. [Trade Execution & Live Feed Data](#trade-execution--live-feed-data)
6. [Dynamic Capital Allocation & Risk-Reward](#dynamic-capital-allocation--risk-reward)
7. [Price Capture & Strategy Alignment](#price-capture--strategy-alignment)
8. [Trailing Stop Loss & Trade Monitoring](#trailing-stop-loss--trade-monitoring)
9. [Target-Based Position Exit](#target-based-position-exit)
10. [System Integration Flow](#system-integration-flow)
11. [Database Schema](#database-schema)
12. [API Endpoints](#api-endpoints)

---

## System Overview

The trading system is an enterprise-grade **HFT (High-Frequency Trading) auto-trading platform** designed for F&O (Futures & Options) trading in the Indian stock market. It provides:

- **Sub-50ms execution latency**
- **Real-time market data processing**
- **Advanced risk management**
- **Multi-strategy support**
- **Comprehensive position monitoring**
- **Emergency safety controls**

### Key Performance Metrics
- **Signal Generation**: < 5ms from tick to signal
- **Order Execution**: < 20ms from signal to broker
- **Total Latency**: < 50ms tick-to-execution
- **System Uptime**: > 99.5% during market hours
- **Win Rate Target**: > 60% for Fibonacci strategy

---

## 1. Strategy Execution & Stock Selection

### 1.1 Strategy Execution Mechanism

#### **Fibonacci + EMA Strategy**
**File**: `services/strategies/fibonacci_ema_strategy.py`
**Lines**: 90-168

**Core Algorithm**:
```python
# Multi-timeframe analysis (1m primary, 5m confirmation)
signal_1m = analyze_timeframe(ohlc_1m, indicators_1m, fib_levels, current_price, '1m')
signal_5m = analyze_timeframe(ohlc_5m, indicators_5m, fib_levels, current_price, '5m')
confirmed_signal = confirm_multi_timeframe(signal_1m, signal_5m)
```

**Signal Generation Criteria**:
- **Bullish (BUY CE)**: Price at Fibonacci 38.2%-50% retracement + EMA bullish alignment
- **Bearish (BUY PE)**: Price at Fibonacci 61.8%-78.6% rejection + EMA bearish alignment
- **Volume Confirmation**: Current volume > 1.2x average volume
- **RSI Filter**: RSI between 30-70 (not overbought/oversold)
- **Signal Strength**: 0-100 scale, minimum 65% required for execution

#### **NIFTY 09:40 Strategy**
**File**: `services/strategies/nifty_09_40_integration.py`

**Features**:
- **Time-based activation**: Automatically starts at 9:40 AM daily
- **Real-time NIFTY data**: Direct index subscription via instrument registry
- **5-minute timeframe**: EMA + Candle Strength indicators
- **Daily trade limits**: Risk management with performance tracking

### 1.2 Stock Selection Process

#### **Auto Stock Selection Service**
**File**: `services/auto_stock_selection_service.py`
**Lines**: 116-153

**Daily 9:00 AM Execution Flow**:
1. **Market Sentiment Analysis**: Multi-factor sentiment scoring
2. **ADR Analysis**: American Depositary Receipt correlation
3. **Sector Momentum Analysis**: Top performing sector identification
4. **F&O Stock Filtering**: Only stocks from 5 major indices
5. **Option Liquidity Validation**: Minimum OI and bid-ask spread checks
6. **Database Storage**: Complete metadata storage for selected stocks

#### **F&O Stock Selection Criteria**
**File**: `services/auto_stock_selection_service.py`
**Lines**: 89-112

```python
fno_selection_config = {
    'volume_threshold': 100000,  # Daily volume > 1L
    'option_liquidity': {
        'min_oi': 10000,  # Open Interest > 10K
        'bid_ask_spread': 0.05  # Max 5 paisa spread
    },
    'price_range': {
        'min_price': 50,
        'max_price': 5000
    },
    'fibonacci_criteria': {
        'min_swing_clarity': 0.6,  # Clear swing highs/lows
        'min_ema_alignment': 0.5,   # EMA trend strength
        'min_fib_respect': 0.4      # Historical Fibonacci respect
    }
}
```

#### **Scoring Algorithm**
**File**: `services/auto_stock_selection_service.py`
**Lines**: 861-917

**Multi-Factor Scoring System**:
- **Technical Score (40%)**: 
  - Swing clarity analysis
  - EMA alignment strength
  - Historical Fibonacci level respect
- **Liquidity Score (30%)**:
  - Average volume ratio
  - Option liquidity score
- **Market Score (30%)**:
  - Index correlation strength
  - Sector momentum analysis

**Final Selection**: Top 2 stocks with highest composite scores

---

## 2. Stock Storage & Management

### 2.1 Database Models

#### **SelectedStock Model**
**File**: `database/models.py`
**Line**: 774

```python
class SelectedStock(Base):
    __tablename__ = "selected_stocks"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False, index=True)
    instrument_key = Column(String, nullable=False)
    selection_date = Column(Date, nullable=False, index=True)
    selection_score = Column(Float, nullable=False)
    selection_reason = Column(Text, nullable=True)
    price_at_selection = Column(Float, nullable=False)
    sector = Column(String, nullable=True)
    option_type = Column(String, nullable=True)  # CE/PE/NEUTRAL
    option_contract = Column(JSON, nullable=True)
    option_expiry_date = Column(String, nullable=True)
    score_breakdown = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
```

#### **AutoTradingSession Model**
**File**: `database/models.py`
**Line**: 926

```python
class AutoTradingSession(Base):
    __tablename__ = "auto_trading_sessions"
    
    session_id = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_date = Column(Date, nullable=False)
    selected_stocks = Column(JSON, nullable=False)
    screening_config = Column(JSON, nullable=True)
    stocks_screened = Column(Integer, default=0)
    session_type = Column(String, default="AUTO_PREMARKET_SELECTION")
    status = Column(String, default="ACTIVE")
```

### 2.2 Storage Workflow

**File**: `services/auto_stock_selection_service.py`
**Lines**: 453-522

**Storage Process**:
1. **Session Creation**: Create AutoTradingSession record
2. **Stock Storage**: Individual SelectedStock records with complete metadata
3. **High-Speed Data Update**: Priority market data access for selected stocks
4. **WebSocket Registration**: Real-time price monitoring initiation

```python
# High-speed market data integration
selected_stocks_data = []
for result in results:
    stock_data = {
        'symbol': result.symbol,
        'instrument_key': result.instrument_key,
        'option_type': result.option_type,
        'atm_strike': result.atm_strike,
        'price_at_selection': result.price_at_selection,
        'selection_score': result.selection_score
    }
    selected_stocks_data.append(stock_data)

high_speed_market_data.update_selected_stocks(selected_stocks_data)
```

---

## 3. Option Contracts & Option Chain Storage

### 3.1 Option Chain Data Sources

#### **Primary: Upstox Option Service**
**File**: `services/upstox_option_service.py`
**Lines**: 22-100

**Features**:
- **Admin Token Authentication**: Uses admin Upstox token for API calls
- **Real-time Option Chain**: Live CE/PE data with Greeks
- **Caching System**: 5-minute cache for performance optimization
- **Error Handling**: Comprehensive error handling with fallback mechanisms

#### **Backup: NSE Options Chain**
**File**: `services/options_chain.py`
**Lines**: 1-16

**Direct NSE API Integration**:
```python
def get_options_chain(symbol: str):
    url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    return response.json()["records"]["data"]
```

### 3.2 ATM Strike Calculation

**File**: `services/auto_stock_selection_service.py`
**Lines**: 635-648

**Dynamic Strike Selection Logic**:
```python
def _calculate_atm_strike(self, current_price: float) -> float:
    if current_price <= 50:
        return round(current_price / 2.5) * 2.5      # ₹2.5 interval
    elif current_price <= 200:
        return round(current_price / 5) * 5          # ₹5 interval
    elif current_price <= 1000:
        return round(current_price / 10) * 10        # ₹10 interval
    else:
        return round(current_price / 50) * 50        # ₹50 interval
```

### 3.3 Option Liquidity Validation

**File**: `services/auto_stock_selection_service.py`
**Lines**: 918-997

**Validation Criteria**:
```python
# Option liquidity requirements
- Minimum Open Interest: 10,000
- Maximum Bid-Ask Spread: 0.05 (5 paisa)
- Minimum Liquid Strikes: 3 CE + 3 PE
- Strike Range: ATM ± 10%
```

**Validation Process**:
1. **Option Chain Retrieval**: Get complete option chain data
2. **Strike Range Analysis**: Check ATM ± 10% strikes
3. **Liquidity Metrics**: Calculate OI, volume, bid-ask spread
4. **Pass/Fail Decision**: Minimum criteria validation

---

## 4. Trade Execution & Live Feed Data

### 4.1 Real-Time Execution Engine

**File**: `services/execution/real_time_execution_engine.py`
**Lines**: 89-200

**HFT-Grade Architecture**:
```python
class RealTimeExecutionEngine:
    def __init__(self):
        self.max_execution_time = 50  # milliseconds
        self.retry_attempts = 3
        self.order_queue = asyncio.Queue()
        self.circuit_breakers = {}
```

**Key Features**:
- **Sub-50ms Execution**: Optimized order placement pipeline
- **Multi-Broker Support**: Upstox, Angel One, Dhan integration
- **Circuit Breakers**: Automatic failure detection and recovery
- **Order Management**: Intelligent retry strategies with exponential backoff

### 4.2 Live Feed Architecture

#### **Centralized WebSocket Manager**
**File**: `services/centralized_ws_manager.py`
**Lines**: 1-100

**Single Connection Strategy**:
- **One Persistent Connection**: Single WebSocket to Upstox
- **Data Broadcasting**: Real-time distribution to all components
- **Priority Subscription**: Higher frequency for selected stocks
- **Fallback Mechanisms**: Redis caching with in-memory backup

#### **Market Data Pipeline**
```
Broker WebSocket → Tick Processing → OHLC Construction → Strategy Analysis → Signal Generation
```

**Data Flow Optimization**:
- **Sub-2ms Tick Processing**: NumPy optimized calculations
- **Circular Buffers**: Memory-efficient real-time data storage
- **Multi-Timeframe Construction**: 1m, 5m, 15m, 1h bars
- **Live Adapter Service**: Real-time data transformation

### 4.3 Order Execution Workflow

**File**: `services/execution/real_time_execution_engine.py`

**Execution Pipeline**:
1. **Signal Validation**: Risk checks and position limits
2. **Order Preparation**: Instrument details and quantity calculation
3. **Broker Selection**: Smart broker routing
4. **Order Placement**: Market orders for speed
5. **Confirmation Tracking**: Real-time order status monitoring
6. **Position Registration**: Live position tracking initiation

---

## 5. Dynamic Capital Allocation & Risk-Reward

### 5.1 Dynamic Risk Reward System

**File**: `services/strategies/dynamic_risk_reward.py`
**Lines**: 64-150

**Risk Management Framework**:
```python
class DynamicRiskReward:
    def __init__(self, account_balance: float = 100000):
        self.max_risk_per_trade = 0.02  # 2% maximum risk per trade
        self.max_portfolio_risk = 0.10  # 10% maximum total portfolio risk
        self.min_risk_reward_ratio = 1.5
        self.max_risk_reward_ratio = 3.0
```

### 5.2 Position Sizing Algorithm

**Key Parameters**:
- **Base Risk Amount**: 2% of account balance per trade
- **Confidence Adjustment**: Signal strength affects position size
- **Consecutive Loss Protection**: Reduces size after 3 consecutive losses
- **Portfolio Heat Management**: Maximum 10% total exposure

**Calculation Process**:
```python
# Base risk calculation
base_risk_amount = account_balance * max_risk_per_trade

# Adjust for signal confidence and loss streak
confidence_factor = signal_strength / 100
loss_adjustment = max(0.5, 1 - (consecutive_losses * 0.15))
adjusted_risk_amount = base_risk_amount * confidence_factor * loss_adjustment

# For options: risk = premium paid (max loss)
recommended_lots = int(adjusted_risk_amount / (option_premium * lot_size))
```

### 5.3 Risk Management Rules

**Position Limits**:
- **Maximum Positions**: 5 simultaneous positions
- **Sector Concentration**: Maximum 25% in any single sector
- **Correlated Positions**: Maximum 3 positions in correlated stocks
- **Daily Loss Limit**: 5% of account balance

**Emergency Controls**:
- **Kill Switch**: Immediate system shutdown capability
- **Circuit Breakers**: Automatic trading suspension on failures
- **Risk Limit Breaches**: Automatic position closure

---

## 6. Price Capture & Strategy Alignment

### 6.1 Real-Time Price Data Flow

**Data Sources**:
- **Primary**: Upstox WebSocket (live ticks)
- **Secondary**: Market data queue service
- **Fallback**: Redis cached data

**Processing Pipeline**:
```
Live Ticks → Tick Validation → OHLC Construction → Technical Analysis → Signal Generation
```

### 6.2 Strategy Alignment Process

**File**: `services/strategies/fibonacci_ema_strategy.py`
**Lines**: 90-168

**Multi-Timeframe Analysis**:
1. **Data Validation**: Ensure minimum data requirements (60x 1m, 20x 5m bars)
2. **Indicator Calculation**: EMAs, RSI, volume analysis for both timeframes
3. **Fibonacci Level Calculation**: Swing point detection and level computation
4. **Signal Generation**: Individual timeframe analysis
5. **Multi-Timeframe Confirmation**: Cross-validation between timeframes
6. **Risk-Reward Calculation**: Stop loss and target determination

**Signal Validation Criteria**:
```python
# Bullish Signal (BUY CE)
conditions = [
    current_price > ema_21,  # Above EMA21
    ema_9 > ema_21 > ema_50,  # EMA bullish alignment
    fib_38_2 <= current_price <= fib_50_0,  # Fibonacci retracement zone
    volume_ratio >= 1.2,  # Volume confirmation
    30 < rsi < 70  # RSI healthy range
]
```

---

## 7. Trailing Stop Loss & Trade Monitoring

### 7.1 Position Monitor System

**File**: `services/execution/position_monitor.py`
**Lines**: 100-200

**Real-Time Monitoring Features**:
```python
@dataclass
class PositionSnapshot:
    # P&L Tracking
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    day_pnl: float = 0.0
    total_pnl: float = 0.0
    
    # Risk Management
    stop_loss: float = 0.0
    target: float = 0.0
    trailing_stop: Optional[float] = None
    
    # Options Greeks
    greeks: Optional[GreeksData] = None
    
    # Risk Metrics
    risk_metrics: RiskMetrics = field(default_factory=RiskMetrics)
```

**Monitoring Frequency**:
- **Position Updates**: 5-second intervals
- **P&L Calculations**: Real-time with every tick
- **Risk Metrics**: 30-second calculations
- **Options Greeks**: 10-second updates

### 7.2 Trailing Stop Implementation

**Fibonacci-Based Trailing Algorithm**:
```python
def fibonacci_trailing_stop(self, entry_price, current_price, signal_type, fib_levels):
    if signal_type == 'BUY_CE':
        if current_price > entry_price * 1.15:  # 15% profit
            trail_stop = fib_levels['fib_38_2']
        elif current_price > entry_price * 1.25:  # 25% profit
            trail_stop = fib_levels['fib_23_6']
    else:  # BUY_PE
        if current_price > entry_price * 1.15:
            trail_stop = fib_levels['fib_61_8']
        elif current_price > entry_price * 1.25:
            trail_stop = fib_levels['fib_78_6']
```

**Trailing Stop Features**:
- **Dynamic Adjustment**: Moves with profit progression
- **Fibonacci Levels**: Uses key retracement levels
- **Breakeven Protection**: Moves to breakeven after 15% profit
- **Maximum Profit Tracking**: Records highest profit achieved

---

## 8. Target-Based Position Exit

### 8.1 Exit Conditions

**Primary Exit Triggers**:
1. **Target Achievement**: Fibonacci extension levels (1.618x, 2.618x price range)
2. **Stop Loss Hit**: Below/above key Fibonacci support/resistance
3. **Trailing Stop Activation**: Dynamic Fibonacci trailing algorithm
4. **Time-Based Exit**: Maximum 2 hours for options positions
5. **Emergency Exits**: Risk limit breaches or kill switch activation

### 8.2 Exit Execution Workflow

**File**: `services/execution/position_monitor.py`

**Continuous Monitoring Loop**:
```python
async def monitor_positions(self):
    for position in self.active_positions:
        current_price = get_current_price(position.instrument_key)
        
        # Check exit conditions
        if check_profit_targets(position, current_price):
            await execute_partial_exit(position)
        elif check_stop_loss(position, current_price):
            await execute_full_exit(position, 'STOP_LOSS')
        elif check_trailing_stop(position, current_price):
            await update_trailing_stop(position)
        elif check_time_exit(position):
            await execute_full_exit(position, 'TIME_EXIT')
```

### 8.3 Exit Types

**Partial Exits**:
- **50% at Target 1**: First Fibonacci extension level
- **Remaining 50% at Target 2**: Second Fibonacci extension level
- **Trailing Stop Activation**: After first target achievement

**Full Exits**:
- **Stop Loss**: Immediate market order execution
- **Time Exit**: 3:20 PM square-off for options
- **Emergency Exit**: Kill switch or risk limit breach

---

## 9. System Integration Flow

### 9.1 Daily Trading Workflow

```mermaid
graph TD
    A[9:00 AM - Stock Selection] --> B[Market Sentiment Analysis]
    B --> C[F&O Stock Filtering]
    C --> D[Option Liquidity Validation]
    D --> E[Database Storage]
    E --> F[Market Data Subscription]
    F --> G[9:15 AM - Trading Session Start]
    G --> H[Real-Time Signal Generation]
    H --> I[Risk Validation]
    I --> J[Order Execution]
    J --> K[Position Monitoring]
    K --> L[Exit Condition Checks]
    L --> M[Trade Closure]
    M --> N[Performance Tracking]
```

### 9.2 Real-Time Trading Loop

```mermaid
graph LR
    A[Live Tick Data] --> B[OHLC Construction]
    B --> C[Technical Analysis]
    C --> D[Signal Generation]
    D --> E{Signal Strength >= 65%?}
    E -->|Yes| F[Risk Validation]
    E -->|No| A
    F --> G{Risk Limits OK?}
    G -->|Yes| H[Order Execution]
    G -->|No| A
    H --> I[Position Monitoring]
    I --> J{Exit Conditions?}
    J -->|Yes| K[Position Exit]
    J -->|No| I
    K --> L[Performance Update]
    L --> A
```

### 9.3 Component Integration Architecture

```mermaid
graph TB
    subgraph "Data Layer"
        WS[WebSocket Manager]
        DB[(Database)]
        Redis[(Redis Cache)]
    end
    
    subgraph "Strategy Layer"
        SS[Stock Selection Service]
        FS[Fibonacci Strategy]
        NS[NIFTY Strategy]
        RR[Risk Reward Manager]
    end
    
    subgraph "Execution Layer"
        EE[Execution Engine]
        OM[Order Manager]
        PM[Position Monitor]
        BM[Broker Manager]
    end
    
    subgraph "Control Layer"
        AC[Auto Coordinator]
        EC[Emergency Controls]
        WM[WebSocket Broadcaster]
    end
    
    WS --> SS
    SS --> DB
    SS --> FS
    FS --> RR
    RR --> EE
    EE --> OM
    OM --> BM
    BM --> PM
    PM --> DB
    PM --> WM
    AC --> SS
    AC --> EE
    AC --> EC
```

---

## 10. Database Schema

### 10.1 Core Trading Tables

#### **SelectedStock**
```sql
CREATE TABLE selected_stocks (
    id INTEGER PRIMARY KEY,
    symbol VARCHAR NOT NULL,
    instrument_key VARCHAR NOT NULL,
    selection_date DATE NOT NULL,
    selection_score FLOAT NOT NULL,
    price_at_selection FLOAT NOT NULL,
    option_type VARCHAR,
    option_contract JSON,
    score_breakdown JSON,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### **AutoTradeExecution**
```sql
CREATE TABLE auto_trade_executions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    symbol VARCHAR NOT NULL,
    trade_type VARCHAR NOT NULL,
    entry_price DECIMAL(10,2),
    exit_price DECIMAL(10,2),
    quantity INTEGER NOT NULL,
    profit_loss DECIMAL(12,2),
    strategy_used VARCHAR,
    fibonacci_data JSON,
    risk_reward_ratio DECIMAL(5,2),
    execution_latency_ms INTEGER,
    trade_duration_minutes INTEGER,
    exit_reason VARCHAR,
    timestamp TIMESTAMP DEFAULT NOW()
);
```

#### **ActivePosition**
```sql
CREATE TABLE active_positions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    symbol VARCHAR NOT NULL,
    instrument_key VARCHAR NOT NULL,
    position_type VARCHAR NOT NULL,
    quantity INTEGER NOT NULL,
    entry_price DECIMAL(10,2),
    current_price DECIMAL(10,2),
    unrealized_pnl DECIMAL(12,2),
    stop_loss DECIMAL(10,2),
    target_price DECIMAL(10,2),
    trailing_stop DECIMAL(10,2),
    strategy_id VARCHAR,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 10.2 Performance Tracking Tables

#### **DailyTradingPerformance**
```sql
CREATE TABLE daily_trading_performance (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    trading_date DATE NOT NULL,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    gross_profit DECIMAL(12,2) DEFAULT 0,
    gross_loss DECIMAL(12,2) DEFAULT 0,
    net_pnl DECIMAL(12,2) DEFAULT 0,
    win_rate DECIMAL(5,2) DEFAULT 0,
    profit_factor DECIMAL(5,2) DEFAULT 0,
    avg_win DECIMAL(10,2) DEFAULT 0,
    avg_loss DECIMAL(10,2) DEFAULT 0,
    max_drawdown DECIMAL(12,2) DEFAULT 0,
    sharpe_ratio DECIMAL(5,2) DEFAULT 0,
    strategy_breakdown JSON,
    UNIQUE(user_id, trading_date)
);
```

---

## 11. API Endpoints

### 11.1 Stock Selection APIs

#### **Get Selected Stocks**
```http
GET /api/v1/auto-trading/selected-stocks
```
**Response**:
```json
{
    "success": true,
    "data": [
        {
            "symbol": "RELIANCE",
            "selection_score": 0.85,
            "option_type": "CE",
            "atm_strike": 2500,
            "selection_reason": "Strong Fibonacci retracement setup",
            "price_at_selection": 2485.50
        }
    ]
}
```

#### **Run Stock Selection**
```http
POST /api/v1/auto-trading/run-stock-selection
```
**Request**:
```json
{
    "user_id": 1,
    "force_selection": false,
    "max_stocks": 2
}
```

### 11.2 Trading Session APIs

#### **Start Trading Session**
```http
POST /api/v1/auto-trading/start-session
```
**Request**:
```json
{
    "user_id": 1,
    "mode": "PAPER_TRADING",
    "selected_stocks": [],
    "risk_parameters": {
        "max_risk_per_trade": 0.02,
        "max_daily_loss": 50000
    },
    "strategy_config": {
        "min_signal_strength": 70
    }
}
```

#### **Get Trading Session Status**
```http
GET /api/v1/auto-trading/session-status/{session_id}
```

### 11.3 Performance APIs

#### **Get Active Trades**
```http
GET /api/v1/auto-trading/active-trades
```

#### **Get Performance Summary**
```http
GET /api/v1/auto-trading/performance-summary?days=30
```

---

## 12. WebSocket Events

### 12.1 Real-Time Events

#### **Stock Selection Update**
```javascript
socket.on('auto_stock_update', (data) => {
    console.log('Selected stocks:', data.stocks);
    console.log('Selection date:', data.selection_date);
});
```

#### **Fibonacci Signal**
```javascript
socket.on('fibonacci_signal', (data) => {
    console.log('Signal type:', data.signal_type);
    console.log('Strength:', data.strength);
    console.log('Entry price:', data.entry_price);
    console.log('Stop loss:', data.stop_loss);
    console.log('Targets:', data.targets);
});
```

#### **Position Update**
```javascript
socket.on('position_update', (data) => {
    console.log('Symbol:', data.symbol);
    console.log('Current P&L:', data.unrealized_pnl);
    console.log('Current price:', data.current_price);
});
```

#### **Trade Execution**
```javascript
socket.on('trade_executed', (data) => {
    console.log('Trade executed:', data.symbol);
    console.log('Option type:', data.option_type);
    console.log('Execution time:', data.execution_time_ms);
});
```

---

## System Configuration

### Environment Variables

```bash
# Database Configuration
DATABASE_URL=postgresql://user:pass@localhost/trading_db

# Trading Configuration
TRADE_MODE=PAPER                    # PAPER or LIVE
DEFAULT_QTY=50                      # Default lot size
RISK_PER_TRADE=2.0                  # Risk percentage per trade
MAX_CONCURRENT_TRADES=5             # Maximum positions

# Broker API Configuration
UPSTOX_API_KEY=your_key
UPSTOX_ACCESS_TOKEN=your_token
UPSTOX_MOBILE=your_mobile
UPSTOX_PIN=your_pin
UPSTOX_TOTP_KEY=your_totp_key

# System Configuration
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
JWT_SECRET_KEY=your_secret_key
```

---

## Performance Monitoring

### Key Metrics

#### **Latency Metrics**
- **Signal Generation**: Target < 5ms
- **Order Execution**: Target < 20ms
- **Total Latency**: Target < 50ms
- **WebSocket Updates**: Target < 100ms

#### **Trading Performance**
- **Win Rate**: Target > 60%
- **Risk-Reward Ratio**: 1.5:1 minimum, 3:1 maximum
- **Daily Return**: 1-3% of capital target
- **Maximum Drawdown**: < 10% threshold

#### **System Performance**
- **Uptime**: > 99.5% during market hours
- **Order Success Rate**: > 95%
- **Data Feed Reliability**: > 99.9%
- **Memory Usage**: < 2GB per service

---

## Security & Risk Management

### Security Measures
- **JWT Authentication**: All API endpoints secured
- **Broker Credential Encryption**: Sensitive data encrypted at rest
- **Rate Limiting**: API rate limiting to prevent abuse
- **Input Validation**: Comprehensive input validation and sanitization

### Risk Management
- **Kill Switch**: Emergency stop functionality
- **Circuit Breakers**: Automatic trading suspension on failures
- **Position Limits**: Hard limits on position sizes and counts
- **Daily Loss Limits**: Automatic trading halt on loss thresholds

---

## Troubleshooting Guide

### Common Issues

#### **No Stocks Selected**
- Check market schedule service status
- Verify sector heatmap data availability
- Review volume threshold configuration

#### **Signal Generation Failures**
- Validate OHLC data quality
- Check technical indicator calculations
- Verify Fibonacci level computations

#### **Order Execution Failures**
- Check broker API connectivity
- Verify token validity and expiration
- Review risk limit validations

#### **WebSocket Connection Issues**
- Check centralized WebSocket manager status
- Verify instrument key subscriptions
- Review connection authentication

---

## Conclusion

This HFT-grade auto-trading system provides enterprise-level capabilities for F&O trading with comprehensive risk management, real-time monitoring, and sophisticated strategy execution. The system is designed for high performance, reliability, and scalability while maintaining strict risk controls and safety measures.

The architecture supports multiple trading strategies, real-time market data processing, and advanced position management, making it suitable for professional trading operations in the Indian stock market.

---

**Document Version**: 1.0  
**Last Updated**: December 2024  
**Maintainer**: Trading System Team