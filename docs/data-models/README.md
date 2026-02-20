# Data Models

This section details the core data structures used in the trading platform. These models map directly to the database tables and are used throughout the application's backend and frontend.

## User & Authentication

### User (`users`)
Represents a registered user of the platform.

| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Unique identifier |
| `email` | String | User's email address (unique) |
| `role` | String | User role (e.g., 'trader', 'admin') |
| `isVerified` | Boolean | Whether email is verified |
| `trading_config` | Relationship | Link to `UserTradingConfig` |

### UserTradingConfig (`user_trading_config`)
Stores user-specific trading preferences and risk settings.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `trade_mode` | String | 'PAPER' | Current mode: LIVE, PAPER, or SIMULATION |
| `execution_mode` | String | 'multi_demat' | Strategy for order placement |
| `stop_loss_percent` | Float | 2.0 | Default Stop Loss % |
| `target_percent` | Float | 4.0 | Default Target % |
| `max_positions` | Integer | 3 | Max concurrent open positions |

## Trading Data

### PaperTradingAccount (`paper_trading_accounts`)
Virtual account for paper trading.

| Field | Type | Description |
|-------|------|-------------|
| `initial_capital` | Float | Starting virtual cash (default ₹5L) |
| `current_balance` | Float | Real-time available balance |
| `used_margin` | Float | Funds currently locked in positions |
| `total_pnl` | Float | Aggregate Profit/Loss |
| `max_risk_per_trade` | Float | Max risk allowed per trade (default 2%) |

### PaperTradingPosition (`paper_trading_positions`)
Represents an individual open or closed trade in paper mode.

| Field | Type | Description |
|-------|------|-------------|
| `symbol` | String | Trading symbol (e.g., 'NIFTY 50') |
| `side` | String | 'BUY' or 'SELL' |
| `quantity` | Integer | Number of units/lots |
| `entry_price` | Float | Price at execution |
| `current_price` | Float | Real-time market price |
| `pnl` | Float | Current Profit/Loss |
| `status` | String | 'ACTIVE', 'CLOSED' |

### TradeSignal (`trade_signals`)
Generated trading opportunities from strategies.

| Field | Type | Description |
|-------|------|-------------|
| `symbol` | String | Target asset |
| `trade_type` | String | Signal direction (BUY/SELL) |
| `confidence` | Float | AI/Algo confidence score |
| `execution_status` | String | 'PENDING', 'EXECUTED', 'FAILED' |

## Market Data

### HistoricalData (`historical_data`)
OHLCV data for backtesting and charts.

| Field | Type | Description |
|-------|------|-------------|
| `symbol` | String | Asset symbol |
| `date` | DateTime | Candle timestamp |
| `open` | Float | Opening price |
| `high` | Float | Highest price |
| `low` | Float | Lowest price |
| `close` | Float | Closing price |
| `volume` | Float | Traded volume |

## Order & Trade Management

### Order (`orders`)
Represents an instruction sent to a broker to buy or sell.

| Field | Type | Description |
|-------|------|-------------|
| `symbol` | String | Asset symbol |
| `order_type` | String | 'LIMIT', 'MARKET', 'STOP-LOSS' |
| `price` | Float | Limit price (if applicable) |
| `quantity` | Integer | Order size |
| `status` | String | 'PENDING', 'FILLED', 'CANCELED' |

### Trade (`trades`)
Represents a completed or active trade execution (Live).

| Field | Type | Description |
|-------|------|-------------|
| `trade_type` | String | 'BUY' or 'SELL' |
| `entry_price` | Float | Execution price |
| `exit_price` | Float | Close price (if closed) |
| `status` | String | 'OPEN', 'FILLED', 'CANCELED' |
| `profit_loss` | Float | Realized PnL |

## AI & Machine Learning

### AIModel (`ai_models`)
Metadata about trained machine learning models used for predictions.

| Field | Type | Description |
|-------|------|-------------|
| `model_name` | String | Unique name of the model |
| `model_version` | String | Version identifier |
| `model_type` | String | Type (e.g., 'LSTM', 'RandomForest') |
| `parameters` | JSON | Hyperparameters used |
| `accuracy` | Float | Validation accuracy score |
| `last_trained_at` | DateTime | Timestamp of last training |

### AIPredictionLog (`ai_prediction_logs`)
Log of individual predictions for performance tracking.

| Field | Type | Description |
|-------|------|-------------|
| `symbol` | String | Target asset |
| `predicted_price` | Float | Forecasted value |
| `actual_price` | Float | Real value (updated later) |
| `accuracy` | Float | Deviation from actual |

