# Database Schema

## SelectedStock Table

Complete database schema for storing intelligent stock selections with market sentiment context.

### Table Definition

```sql
CREATE TABLE selected_stocks (
    -- Primary Key
    id INTEGER PRIMARY KEY AUTO_INCREMENT,

    -- Stock Identification
    symbol VARCHAR(50) NOT NULL,
    instrument_key VARCHAR(100) NOT NULL,
    selection_date DATE NOT NULL,

    -- Selection Metrics
    selection_score FLOAT NOT NULL,
    selection_reason VARCHAR(100) NOT NULL,

    -- Price Data at Selection Time
    price_at_selection FLOAT NOT NULL,
    volume_at_selection INTEGER DEFAULT 0,
    change_percent_at_selection FLOAT DEFAULT 0.0,

    -- Classification
    sector VARCHAR(50) DEFAULT 'OTHER',
    score_breakdown TEXT,  -- JSON

    -- Market Sentiment at Selection Time (NEW FIELDS)
    market_sentiment VARCHAR(20),  -- very_bullish, bullish, neutral, bearish, very_bearish
    market_sentiment_confidence FLOAT,  -- 0-100
    advance_decline_ratio FLOAT,  -- e.g., 1.75
    market_breadth_percent FLOAT,  -- e.g., 15.2
    advancing_stocks INTEGER,  -- e.g., 1250
    declining_stocks INTEGER,  -- e.g., 715
    total_stocks_analyzed INTEGER,  -- e.g., 2000
    selection_phase VARCHAR(30),  -- premarket, final_selection

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Options Trading Direction
    option_type VARCHAR(10),  -- CE (CALL) / PE (PUT) / NEUTRAL
    option_contract TEXT,  -- JSON
    option_contracts_available INTEGER DEFAULT 0,
    option_chain_data TEXT,  -- JSON
    option_expiry_date VARCHAR(20),
    option_expiry_dates TEXT,  -- JSON

    -- Performance Tracking
    max_price_achieved FLOAT,
    min_price_achieved FLOAT,
    exit_price FLOAT,
    exit_reason VARCHAR(100),

    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Indexes
    INDEX idx_symbol_selection_date (symbol, selection_date),
    INDEX idx_selection_date_active (selection_date, is_active),
    INDEX idx_selection_score (selection_score),
    INDEX idx_market_sentiment_date (market_sentiment, selection_date)
);
```

## Field Descriptions

### Stock Identification

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | INTEGER | Auto-increment primary key | 1 |
| `symbol` | VARCHAR(50) | Stock symbol | "RELIANCE" |
| `instrument_key` | VARCHAR(100) | Upstox instrument key | "NSE_EQ\|INE002A01018" |
| `selection_date` | DATE | Date when selected | "2025-01-10" |

### Selection Metrics

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `selection_score` | FLOAT | Final selection score (0-1) | 0.75 |
| `selection_reason` | VARCHAR(100) | Why this stock was selected | "High value (125Cr) in strong ENERGY sector" |

### Price Data

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `price_at_selection` | FLOAT | LTP when selected | 2450.50 |
| `volume_at_selection` | INTEGER | Volume when selected | 1250000 |
| `change_percent_at_selection` | FLOAT | Change % when selected | 2.35 |

### Classification

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `sector` | VARCHAR(50) | Stock sector | "ENERGY" |
| `score_breakdown` | TEXT (JSON) | Detailed scoring breakdown | See below |

**score_breakdown JSON Structure**:
```json
{
  "sentiment_score": 0.8,
  "sector_score": 0.75,
  "technical_score": 0.65,
  "volume_score": 0.9,
  "value_score": 0.85,
  "final_score": 0.75,
  "confidence_level": 0.78,
  "risk_level": "MEDIUM",
  "options_direction": "CE",
  "market_sentiment_at_selection": "bullish"
}
```

### Market Sentiment Data (NEW)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `market_sentiment` | VARCHAR(20) | Sentiment classification | "bullish" |
| `market_sentiment_confidence` | FLOAT | Confidence level (0-100) | 78.5 |
| `advance_decline_ratio` | FLOAT | Advancing/Declining ratio | 1.75 |
| `market_breadth_percent` | FLOAT | Market breadth percentage | 15.2 |
| `advancing_stocks` | INTEGER | Number of advancing stocks | 1250 |
| `declining_stocks` | INTEGER | Number of declining stocks | 715 |
| `total_stocks_analyzed` | INTEGER | Total stocks in analysis | 2000 |
| `selection_phase` | VARCHAR(30) | Selection phase | "final_selection" |

### Options Trading

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `option_type` | VARCHAR(10) | CE (CALL) or PE (PUT) | "CE" |
| `option_contract` | TEXT (JSON) | Selected option contract | See below |
| `option_contracts_available` | INTEGER | Available contracts count | 5 |
| `option_chain_data` | TEXT (JSON) | Complete option chain | See below |
| `option_expiry_date` | VARCHAR(20) | Selected expiry | "2025-01-31" |
| `option_expiry_dates` | TEXT (JSON) | All available expiries | `["2025-01-31", "2025-02-28"]` |

**option_contract JSON Structure**:
```json
{
  "strike": 2500,
  "option_type": "CE",
  "expiry_date": "2025-01-31",
  "ltp": 45.50,
  "iv": 28.5,
  "delta": 0.52,
  "theta": -0.08,
  "lot_size": 250
}
```

### Performance Tracking

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `max_price_achieved` | FLOAT | Highest price after selection | 2520.00 |
| `min_price_achieved` | FLOAT | Lowest price after selection | 2430.00 |
| `exit_price` | FLOAT | Exit price if closed | 2485.00 |
| `exit_reason` | VARCHAR(100) | Why position closed | "TARGET_HIT" |

### Status & Timestamps

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `is_active` | BOOLEAN | Currently active selection | true |
| `created_at` | DATETIME | When record created | "2025-01-10 08:30:00" |
| `updated_at` | DATETIME | Last update time | "2025-01-10 09:20:00" |

## Indexes

### Performance Indexes

```sql
-- Query by symbol and date
INDEX idx_symbol_selection_date (symbol, selection_date)

-- Query active selections by date
INDEX idx_selection_date_active (selection_date, is_active)

-- Sort by selection score
INDEX idx_selection_score (selection_score)

-- Query by market sentiment and date
INDEX idx_market_sentiment_date (market_sentiment, selection_date)
```

### Index Usage Examples

```sql
-- Fast: Uses idx_selection_date_active
SELECT * FROM selected_stocks
WHERE selection_date = '2025-01-10' AND is_active = TRUE;

-- Fast: Uses idx_market_sentiment_date
SELECT * FROM selected_stocks
WHERE market_sentiment = 'bullish' AND selection_date >= '2025-01-01';

-- Fast: Uses idx_symbol_selection_date
SELECT * FROM selected_stocks
WHERE symbol = 'RELIANCE' AND selection_date = '2025-01-10';
```

## Sample Data

### Example Record - Bullish Market Selection

```sql
INSERT INTO selected_stocks (
    symbol, instrument_key, selection_date,
    selection_score, selection_reason,
    price_at_selection, volume_at_selection, change_percent_at_selection,
    sector, score_breakdown,
    market_sentiment, market_sentiment_confidence,
    advance_decline_ratio, market_breadth_percent,
    advancing_stocks, declining_stocks, total_stocks_analyzed,
    selection_phase, is_active, option_type
) VALUES (
    'RELIANCE', 'NSE_EQ|INE002A01018', '2025-01-10',
    0.75, 'High value (125Cr) in strong ENERGY sector',
    2450.50, 1250000, 2.35,
    'ENERGY', '{"sentiment_score":0.8,"sector_score":0.75,"final_score":0.75}',
    'bullish', 78.5,
    1.75, 15.2,
    1250, 715, 2000,
    'final_selection', TRUE, 'CE'
);
```

### Example Record - Bearish Market Selection

```sql
INSERT INTO selected_stocks (
    symbol, instrument_key, selection_date,
    selection_score, selection_reason,
    price_at_selection, volume_at_selection, change_percent_at_selection,
    sector, score_breakdown,
    market_sentiment, market_sentiment_confidence,
    advance_decline_ratio, market_breadth_percent,
    advancing_stocks, declining_stocks, total_stocks_analyzed,
    selection_phase, is_active, option_type
) VALUES (
    'TATASTEEL', 'NSE_EQ|INE081A01012', '2025-01-10',
    0.68, 'Defensive stock in bearish market',
    850.00, 2500000, -1.25,
    'METALS', '{"sentiment_score":0.7,"sector_score":0.65,"final_score":0.68}',
    'bearish', 82.0,
    0.65, -8.5,
    850, 1310, 2160,
    'final_selection', TRUE, 'PE'
);
```

## Common Queries

### Get Today's Final Selections

```sql
SELECT
    symbol,
    sector,
    selection_score,
    market_sentiment,
    advance_decline_ratio,
    market_breadth_percent,
    option_type,
    price_at_selection
FROM selected_stocks
WHERE selection_date = CURRENT_DATE
  AND selection_phase = 'final_selection'
  AND is_active = TRUE
ORDER BY selection_score DESC;
```

### Get Bullish Selections with High Confidence

```sql
SELECT
    symbol,
    sector,
    market_sentiment,
    market_sentiment_confidence,
    advance_decline_ratio,
    option_type
FROM selected_stocks
WHERE selection_date = CURRENT_DATE
  AND market_sentiment IN ('bullish', 'very_bullish')
  AND market_sentiment_confidence > 75
  AND is_active = TRUE
ORDER BY market_sentiment_confidence DESC;
```

### Get Market Sentiment History

```sql
SELECT
    selection_date,
    market_sentiment,
    AVG(advance_decline_ratio) as avg_ad_ratio,
    AVG(market_breadth_percent) as avg_breadth,
    COUNT(*) as stocks_selected,
    SUM(CASE WHEN option_type = 'CE' THEN 1 ELSE 0 END) as call_count,
    SUM(CASE WHEN option_type = 'PE' THEN 1 ELSE 0 END) as put_count
FROM selected_stocks
WHERE selection_date >= DATE_SUB(CURRENT_DATE, INTERVAL 30 DAY)
  AND selection_phase = 'final_selection'
GROUP BY selection_date, market_sentiment
ORDER BY selection_date DESC;
```

### Get Performance Tracking

```sql
SELECT
    symbol,
    price_at_selection,
    max_price_achieved,
    min_price_achieved,
    exit_price,
    ((exit_price - price_at_selection) / price_at_selection * 100) as return_percent,
    exit_reason
FROM selected_stocks
WHERE selection_date = CURRENT_DATE
  AND exit_price IS NOT NULL
ORDER BY return_percent DESC;
```

## Database Migration

### Migration File Location
```
alembic/versions/add_market_sentiment_to_selected_stocks.py
```

### Run Migration

```bash
cd c:\Work\P\app\tradingapp-main\tradingapp-main
alembic upgrade head
```

### Verify Migration

```sql
-- Check if new columns exist
DESCRIBE selected_stocks;

-- Check if index was created
SHOW INDEXES FROM selected_stocks
WHERE Key_name = 'idx_market_sentiment_date';
```

---

**Next**: [Market Sentiment Analysis](04_market_sentiment_analysis.md)