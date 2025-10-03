# Overview & Architecture

## System Overview

The Intelligent Stock Selection System is a real-time stock selection engine that analyzes market conditions, calculates sentiment, and automatically selects the best F&O stocks for options trading.

## Core Capabilities

- **Real-time Market Analysis**: Live WebSocket feed processing
- **Sentiment-Based Selection**: Advance/Decline ratio analysis
- **Automatic Options Direction**: CE (CALL) or PE (PUT) based on market sentiment
- **Multi-Phase Workflow**: Premarket → Validation → Final Selection
- **Complete Audit Trail**: All market context stored in database

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     UPSTOX WEBSOCKET FEED                       │
│                    (Live Market Data Stream)                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              CENTRALIZED WEBSOCKET MANAGER                      │
│         (Receives & Normalizes Upstox Feed Format)              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              REALTIME MARKET ENGINE                             │
│  - Maintains instrument data                                    │
│  - Calculates Advance/Decline ratio                             │
│  - Determines market sentiment                                  │
│  - Computes sector performance                                  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│       INTELLIGENT STOCK SELECTION SERVICE                       │
│  1. Query market sentiment                                      │
│  2. Analyze sector strength                                     │
│  3. Select top F&O stocks                                       │
│  4. Determine options direction (CE/PE)                         │
│  5. Calculate selection scores                                  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   DATABASE (SelectedStock)                      │
│  - Stock selections with scores                                 │
│  - Market sentiment at selection time                           │
│  - Advance/Decline ratio & breadth                              │
│  - Options direction (CE/PE)                                    │
│  - Complete market context                                      │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              AUTO-TRADING SYSTEM                                │
│  - Reads final selections from database                         │
│  - Executes trades based on options direction                   │
│  - Monitors positions in real-time                              │
└─────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### 1. Centralized WebSocket Manager
**File**: `services/centralized_ws_manager.py`

**Responsibilities**:
- Maintains single admin WebSocket connection to Upstox
- Receives live market feed for up to 1500 instruments
- Normalizes Upstox feed format to standard structure
- Forwards data to realtime_market_engine

**Key Methods**:
- `connect_websocket()` - Establish connection
- `_process_live_feed()` - Process incoming data
- `_forward_to_realtime_engine()` - Forward normalized data

### 2. Realtime Market Engine
**File**: `services/realtime_market_engine.py`

**Responsibilities**:
- Maintains in-memory instrument registry
- Updates live prices from WebSocket feed
- Calculates advance/decline metrics
- Determines market sentiment
- Computes sector performance

**Key Methods**:
- `update_market_data(updates)` - Update instrument prices
- `get_market_sentiment()` - Returns sentiment with A/D ratio
- `get_sector_performance()` - Returns sector metrics
- `get_sector_stocks(sector)` - Returns stocks by sector

**Data Structure**:
```python
class Instrument:
    instrument_key: str
    symbol: str
    current_price: float
    change_percent: float
    volume: int
    sector: str
    # ... more fields
```

### 3. Intelligent Stock Selection Service
**File**: `services/intelligent_stock_selection_service.py`

**Responsibilities**:
- Queries market sentiment from realtime engine
- Analyzes sector strength based on sentiment
- Selects top F&O stocks using multi-factor scoring
- Determines options direction (CE/PE)
- Stores selections with complete market context

**Key Methods**:
- `run_premarket_selection()` - Premarket analysis
- `validate_market_open_selection()` - Market open validation
- `get_live_trading_recommendations()` - Returns final selections
- `save_selections_to_database()` - Stores with market context

**Selection Workflow**:
```python
async def run_premarket_selection():
    1. Get market sentiment from realtime_engine
    2. Analyze sector strength
    3. Select top stocks from strong sectors
    4. Calculate selection scores
    5. Determine options direction
    6. Save to database with phase = "premarket"
```

### 4. Database Layer
**File**: `database/models.py`

**Responsibilities**:
- Stores selected stocks with complete context
- Maintains market sentiment history
- Provides audit trail for selections
- Supports querying by date, sentiment, phase

**Key Model**: `SelectedStock`
- Stock details (symbol, sector, scores)
- Market sentiment at selection time
- Advance/Decline ratio & breadth
- Options direction (CE/PE)
- Selection phase tracking

## Data Flow

### 1. Live Feed Ingestion
```
Upstox WebSocket → centralized_ws_manager → realtime_market_engine
```

**Data Format**:
```json
{
  "NSE_EQ|INE002A01018": {
    "ltp": 2450.50,
    "volume": 1250000,
    "change_percent": 2.35,
    "high": 2465.00,
    "low": 2430.00
  }
}
```

### 2. Market Analysis
```
realtime_market_engine → Calculate A/D ratio → Determine sentiment
```

**Calculation**:
```python
advancing = count(stocks with change_percent > 0)
declining = count(stocks with change_percent < 0)
ad_ratio = advancing / declining
market_breadth_percent = ((advancing - declining) / total) * 100
```

### 3. Stock Selection
```
intelligent_stock_selection_service → Query engine → Select stocks → Save to DB
```

**Selection Flow**:
```python
1. Get market sentiment (bullish/bearish/neutral)
2. Get sector performance for all sectors
3. Rank sectors by strength score
4. For each top sector:
   - Get all F&O stocks
   - Filter by volume (>100k)
   - Sort by trading value
   - Select top 2 stocks
5. Score all selected stocks
6. Sort by final score
7. Keep top 5
8. Determine CE/PE direction
9. Save to database
```

### 4. Trading Execution
```
Auto-trading system → Read DB → Execute CE/PE options → Monitor
```

## Integration Points

### API Layer
**File**: `router/auto_trading_routes.py`

**Endpoints**:
- `POST /api/v1/auto-trading/run-stock-selection` - Trigger selection
- `GET /api/v1/auto-trading/selected-stocks` - Get selections

### WebSocket Broadcasting
**File**: `services/unified_websocket_manager.py`

**Events**:
- `stock_selection_started` - Selection process initiated
- `stock_selection_completed` - Results available
- `market_sentiment_update` - Sentiment changed

## Performance Characteristics

### Latency Targets
- Market data ingestion: < 10ms
- Sentiment calculation: < 50ms
- Stock selection: < 500ms
- Database storage: < 100ms
- **Total end-to-end: < 1 second**

### Scalability
- Handles 2000+ instruments simultaneously
- Real-time updates every 100ms
- Supports concurrent API requests
- Efficient in-memory caching

## Error Handling

### Fallback Mechanisms
1. **No market data**: Returns neutral sentiment
2. **WebSocket disconnect**: Automatic reconnection
3. **Database error**: Rollback transaction, log error
4. **API timeout**: Returns cached data if available

### Validation
- Input validation for all API parameters
- Data sanity checks (prices, volumes)
- Sentiment calculation verification
- Score range validation (0-1)

## Security Considerations

### Authentication
- JWT token required for all API calls
- User role verification for admin operations

### Data Protection
- No sensitive data in logs
- Database credentials encrypted
- API keys stored in environment variables

## Monitoring & Logging

### Log Levels
- **INFO**: Selection process milestones
- **DEBUG**: Detailed scoring information
- **WARNING**: Unusual market conditions
- **ERROR**: Selection failures

### Key Metrics
- Stocks selected per day
- Average selection score
- Market sentiment distribution
- Options direction ratio (CE vs PE)

---

**Next**: [Execution Workflow](02_execution_workflow.md)