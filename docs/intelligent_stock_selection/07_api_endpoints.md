# API Endpoints

## Overview

REST API endpoints for triggering stock selection, retrieving results, and monitoring the system.

## Base URL

```
http://localhost:8000/api/v1/auto-trading
```

## Authentication

All endpoints require JWT authentication:

```http
Authorization: Bearer {your_jwt_token}
```

---

## Endpoints

### 1. Run Stock Selection

Trigger the intelligent stock selection process.

#### Request

```http
POST /api/v1/auto-trading/run-stock-selection
Authorization: Bearer {token}
```

#### Response

```json
{
  "success": true,
  "message": "Stock selection process started",
  "status": "running",
  "timestamp": "2025-01-10T09:00:00Z"
}
```

#### Behavior by Time

- **Before 9:15 AM**: Runs premarket selection
- **9:15-9:25 AM**: Runs market open validation
- **After 9:25 AM**: Returns error or existing selections

---

### 2. Get Selected Stocks

Retrieve today's selected stocks with market context.

#### Request

```http
GET /api/v1/auto-trading/selected-stocks
Authorization: Bearer {token}
```

#### Response

```json
{
  "success": true,
  "stocks": [
    {
      "id": 1,
      "symbol": "RELIANCE",
      "sector": "ENERGY",
      "selection_score": 0.75,
      "selection_reason": "High value (125Cr) in strong ENERGY sector",
      "price_at_selection": 2450.50,
      "option_type": "CE",
      "market_sentiment": "bullish",
      "advance_decline_ratio": 1.75,
      "market_breadth_percent": 15.2,
      "selection_date": "2025-01-10"
    }
  ],
  "market_sentiment": {
    "sentiment": "bullish",
    "confidence": 78.5,
    "option_bias": "CE",
    "factors": {
      "advancing_stocks": 1250,
      "declining_stocks": 715,
      "total_stocks": 2000
    }
  },
  "trading_session": {
    "is_active": true,
    "selected_stocks_count": 5,
    "trading_mode": "PAPER_TRADING"
  }
}
```

---

### 3. Get Session Status

Get current trading session status.

#### Request

```http
GET /api/v1/auto-trading/session-status
Authorization: Bearer {token}
```

#### Response

```json
{
  "is_active": true,
  "active_trades": 3,
  "trades_executed_today": 5,
  "daily_pnl": 2500.00,
  "session_date": "2025-01-10",
  "selected_stocks_count": 5,
  "trading_mode": "PAPER_TRADING",
  "session_id": "auto_session_123",
  "session_start_time": "2025-01-10T09:25:00Z",
  "system_health": "healthy"
}
```

---

### 4. Start Trading Session

Start automated trading with selected stocks.

#### Request

```http
POST /api/v1/auto-trading/start-session
Authorization: Bearer {token}
Content-Type: application/json

{
  "mode": "PAPER_TRADING",
  "selected_stocks": [],
  "risk_parameters": {
    "max_risk_per_trade": 0.02,
    "max_daily_loss": 50000
  },
  "strategy_config": {
    "min_signal_strength": 70
  },
  "max_positions": 5,
  "max_daily_loss": 50000
}
```

#### Response

```json
{
  "success": true,
  "message": "Trading session started successfully",
  "session_id": "session_123_1234567890",
  "is_active": true,
  "active_trades": 0,
  "trades_executed_today": 0,
  "daily_pnl": 0.0,
  "session_date": "2025-01-10",
  "selected_stocks_count": 5,
  "trading_mode": "PAPER_TRADING"
}
```

---

### 5. Stop Trading Session

Stop the active trading session.

#### Request

```http
POST /api/v1/auto-trading/stop-session
Authorization: Bearer {token}
```

#### Response

```json
{
  "success": true,
  "message": "Trading session stopped successfully",
  "is_active": false,
  "active_trades": 0,
  "trades_executed_today": 5,
  "daily_pnl": 3500.00,
  "session_date": "2025-01-10",
  "selected_stocks_count": 5
}
```

---

### 6. Get Active Trades

Get currently active trading positions.

#### Request

```http
GET /api/v1/auto-trading/active-trades
Authorization: Bearer {token}
```

#### Response

```json
{
  "active_trades": [
    {
      "id": "TR_001",
      "symbol": "RELIANCE",
      "option_type": "CE",
      "entry_price": 45.50,
      "current_price": 52.30,
      "quantity": 250,
      "lot_size": 250,
      "pnl": 1700.00,
      "pnl_percentage": 14.95,
      "stop_loss": 31.85,
      "target": 68.25,
      "entry_time": "2025-01-10T09:25:00Z",
      "status": "ACTIVE"
    }
  ],
  "total_active": 1,
  "daily_pnl": 1700.00
}
```

---

### 7. Get Trading History

Get historical trades for specified period.

#### Request

```http
GET /api/v1/auto-trading/trading-history?days=7
Authorization: Bearer {token}
```

#### Response

```json
{
  "trades": [
    {
      "symbol": "RELIANCE",
      "trade_type": "CE",
      "entry_price": 45.50,
      "exit_price": 68.25,
      "quantity": 250,
      "pnl": 5687.50,
      "pnl_percentage": 50.00,
      "entry_time": "2025-01-10T09:25:00Z",
      "exit_time": "2025-01-10T14:30:00Z",
      "status": "CLOSED",
      "exit_reason": "TARGET_HIT",
      "option_type": "CE",
      "strike_price": 2450,
      "stop_loss": 31.85,
      "target": 68.25
    }
  ],
  "total_trades": 1,
  "date_range": {
    "start": "2025-01-03",
    "end": "2025-01-10"
  }
}
```

---

### 8. Get Performance Summary

Get trading performance metrics.

#### Request

```http
GET /api/v1/auto-trading/performance-summary
Authorization: Bearer {token}
```

#### Response

```json
{
  "today": {
    "total_trades": 5,
    "winning_trades": 3,
    "losing_trades": 2,
    "win_rate": 60.0,
    "total_pnl": 3500.00,
    "avg_pnl": 700.00,
    "best_trade": 2500.00,
    "worst_trade": -500.00
  },
  "week": {
    "total_trades": 25,
    "winning_trades": 15,
    "losing_trades": 10,
    "win_rate": 60.0,
    "total_pnl": 12500.00,
    "avg_pnl": 500.00,
    "best_trade": 3000.00,
    "worst_trade": -800.00
  },
  "month": {
    "total_trades": 100,
    "winning_trades": 65,
    "losing_trades": 35,
    "win_rate": 65.0,
    "total_pnl": 45000.00,
    "avg_pnl": 450.00,
    "best_trade": 5000.00,
    "worst_trade": -1200.00
  }
}
```

---

### 9. Get System Stats

Get comprehensive system statistics.

#### Request

```http
GET /api/v1/auto-trading/system-stats
Authorization: Bearer {token}
```

#### Response

```json
{
  "success": true,
  "data": {
    "totalTrades": 5,
    "successRate": 60.0,
    "avgReturn": 700.00,
    "activeStrategies": 2,
    "portfolioValue": 500000,
    "dailyPnL": 3500.00,
    "monthlyReturn": 9.0,
    "totalReturn": 9.0,
    "activeTrades": 1,
    "selectedStocksCount": 5,
    "systemStatus": "ACTIVE",
    "winRate": 60.0,
    "signalsGenerated": 10,
    "signalsExecuted": 8,
    "avgExecutionTime": 150,
    "systemUptime": 99.5,
    "lastUpdated": "2025-01-10T15:30:00Z"
  }
}
```

---

## Error Responses

### 400 Bad Request

```json
{
  "detail": "Trading session is already active"
}
```

### 401 Unauthorized

```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden

```json
{
  "detail": "Only admin users can trigger emergency stop"
}
```

### 404 Not Found

```json
{
  "detail": "Selected stock not found"
}
```

### 500 Internal Server Error

```json
{
  "detail": "Failed to trigger emergency stop: Connection timeout"
}
```

---

## Usage Examples

### Python

```python
import requests

BASE_URL = "http://localhost:8000/api/v1/auto-trading"
TOKEN = "your_jwt_token_here"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Trigger stock selection
response = requests.post(
    f"{BASE_URL}/run-stock-selection",
    headers=headers
)
print(response.json())

# Get selected stocks
response = requests.get(
    f"{BASE_URL}/selected-stocks",
    headers=headers
)
stocks = response.json()["stocks"]
print(f"Selected {len(stocks)} stocks")

# Start trading session
session_config = {
    "mode": "PAPER_TRADING",
    "max_positions": 5,
    "max_daily_loss": 50000
}
response = requests.post(
    f"{BASE_URL}/start-session",
    headers=headers,
    json=session_config
)
print(response.json())
```

### cURL

```bash
# Get JWT token first
TOKEN="your_jwt_token"

# Run stock selection
curl -X POST http://localhost:8000/api/v1/auto-trading/run-stock-selection \
  -H "Authorization: Bearer $TOKEN"

# Get selected stocks
curl http://localhost:8000/api/v1/auto-trading/selected-stocks \
  -H "Authorization: Bearer $TOKEN"

# Start trading session
curl -X POST http://localhost:8000/api/v1/auto-trading/start-session \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "PAPER_TRADING",
    "max_positions": 5,
    "max_daily_loss": 50000
  }'
```

### JavaScript

```javascript
const BASE_URL = 'http://localhost:8000/api/v1/auto-trading';
const TOKEN = 'your_jwt_token';

const headers = {
  'Authorization': `Bearer ${TOKEN}`,
  'Content-Type': 'application/json'
};

// Trigger stock selection
async function runStockSelection() {
  const response = await fetch(`${BASE_URL}/run-stock-selection`, {
    method: 'POST',
    headers: headers
  });
  const data = await response.json();
  console.log(data);
}

// Get selected stocks
async function getSelectedStocks() {
  const response = await fetch(`${BASE_URL}/selected-stocks`, {
    headers: headers
  });
  const data = await response.json();
  console.log(`Selected ${data.stocks.length} stocks`);
  return data.stocks;
}

// Start trading session
async function startTradingSession() {
  const config = {
    mode: 'PAPER_TRADING',
    max_positions: 5,
    max_daily_loss: 50000
  };

  const response = await fetch(`${BASE_URL}/start-session`, {
    method: 'POST',
    headers: headers,
    body: JSON.stringify(config)
  });
  const data = await response.json();
  console.log(data);
}
```

---

**Next**: [Configuration](08_configuration.md)