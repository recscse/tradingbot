# Market Sentiment Analysis

## Overview

Market sentiment is calculated in real-time using the **Advance/Decline Ratio** and **Market Breadth** from live WebSocket feed data. This sentiment directly determines whether to trade CALL (CE) or PUT (PE) options.

## Calculation Method

### Source Data

From `realtime_market_engine.py`:

```python
# Count stocks by price movement
advancing_stocks = count(stocks where change_percent > 0)
declining_stocks = count(stocks where change_percent < 0)
unchanged_stocks = count(stocks where change_percent == 0)
total_stocks = advancing + declining + unchanged
```

### Core Metrics

#### 1. Advance/Decline Ratio (A/D Ratio)

```python
ad_ratio = advancing_stocks / declining_stocks
```

**Examples**:
- `ad_ratio = 2.0` → 2x more stocks advancing than declining (BULLISH)
- `ad_ratio = 1.0` → Equal advancing and declining (NEUTRAL)
- `ad_ratio = 0.5` → 2x more stocks declining than advancing (BEARISH)

#### 2. Market Breadth Percentage

```python
market_breadth_percent = ((advancing - declining) / total_stocks) * 100
```

**Examples**:
- `breadth = +20%` → 20% net positive (STRONG BULLISH)
- `breadth = 0%` → Equal distribution (NEUTRAL)
- `breadth = -15%` → 15% net negative (STRONG BEARISH)

## Sentiment Classification

### Algorithm

From `realtime_market_engine.py` → `get_market_sentiment()`:

```python
def get_market_sentiment() -> Dict[str, Any]:
    """Calculate market sentiment from advance/decline data"""

    advancing = analytics.advancing_stocks
    declining = analytics.declining_stocks
    total_stocks = analytics.total_stocks

    # Calculate metrics
    ad_ratio = advancing / declining if declining > 0 else 1.0
    market_breadth_percent = ((advancing - declining) / total_stocks) * 100

    # Determine sentiment
    if market_breadth_percent > 15 and ad_ratio > 2.0:
        sentiment = "very_bullish"
        confidence = min(95, abs(market_breadth_percent) * 4)

    elif market_breadth_percent > 5 and ad_ratio > 1.3:
        sentiment = "bullish"
        confidence = min(85, abs(market_breadth_percent) * 5)

    elif market_breadth_percent < -15 and ad_ratio < 0.5:
        sentiment = "very_bearish"
        confidence = min(95, abs(market_breadth_percent) * 4)

    elif market_breadth_percent < -5 and ad_ratio < 0.8:
        sentiment = "bearish"
        confidence = min(85, abs(market_breadth_percent) * 5)

    else:
        sentiment = "neutral"
        confidence = 50 + abs(market_breadth_percent)

    return {
        "sentiment": sentiment,
        "confidence": round(confidence, 1),
        "metrics": {
            "advance_decline_ratio": round(ad_ratio, 2),
            "market_breadth_percent": round(market_breadth_percent, 2),
            "advancing": advancing,
            "declining": declining,
            "total_stocks": total_stocks
        }
    }
```

### Sentiment Levels

| Sentiment | Conditions | Confidence | Market Condition |
|-----------|-----------|------------|------------------|
| **very_bullish** | Breadth > 15% AND A/D > 2.0 | 90-95% | Strong rally, broad participation |
| **bullish** | Breadth > 5% AND A/D > 1.3 | 75-85% | Uptrend, positive momentum |
| **neutral** | Breadth -5% to 5% | 50-60% | Sideways, mixed signals |
| **bearish** | Breadth < -5% AND A/D < 0.8 | 75-85% | Downtrend, selling pressure |
| **very_bearish** | Breadth < -15% AND A/D < 0.5 | 90-95% | Sharp selloff, panic selling |

## Real-World Examples

### Example 1: Strong Bullish Market

**Market Data at 9:20 AM**:
```
Total stocks analyzed: 2000
Advancing stocks: 1500
Declining stocks: 400
Unchanged stocks: 100
```

**Calculation**:
```python
ad_ratio = 1500 / 400 = 3.75
market_breadth_percent = ((1500 - 400) / 2000) * 100 = 55%
```

**Result**:
```json
{
  "sentiment": "very_bullish",
  "confidence": 95,
  "metrics": {
    "advance_decline_ratio": 3.75,
    "market_breadth_percent": 55.0,
    "advancing": 1500,
    "declining": 400,
    "total_stocks": 2000
  }
}
```

**Interpretation**:
- 75% of stocks advancing (extremely strong)
- A/D ratio 3.75 (almost 4:1 in favor of bulls)
- **Trade Direction**: BUY CALL OPTIONS (CE)

### Example 2: Moderate Bullish Market

**Market Data at 9:20 AM**:
```
Total stocks analyzed: 2000
Advancing stocks: 1100
Declining stocks: 800
Unchanged stocks: 100
```

**Calculation**:
```python
ad_ratio = 1100 / 800 = 1.375
market_breadth_percent = ((1100 - 800) / 2000) * 100 = 15%
```

**Result**:
```json
{
  "sentiment": "bullish",
  "confidence": 75,
  "metrics": {
    "advance_decline_ratio": 1.38,
    "market_breadth_percent": 15.0,
    "advancing": 1100,
    "declining": 800,
    "total_stocks": 2000
  }
}
```

**Interpretation**:
- 55% advancing vs 40% declining
- Positive but not overwhelming strength
- **Trade Direction**: BUY CALL OPTIONS (CE)

### Example 3: Neutral Market

**Market Data at 9:20 AM**:
```
Total stocks analyzed: 2000
Advancing stocks: 950
Declining stocks: 900
Unchanged stocks: 150
```

**Calculation**:
```python
ad_ratio = 950 / 900 = 1.055
market_breadth_percent = ((950 - 900) / 2000) * 100 = 2.5%
```

**Result**:
```json
{
  "sentiment": "neutral",
  "confidence": 52.5,
  "metrics": {
    "advance_decline_ratio": 1.06,
    "market_breadth_percent": 2.5,
    "advancing": 950,
    "declining": 900,
    "total_stocks": 2000
  }
}
```

**Interpretation**:
- Almost equal advancing and declining
- No clear directional bias
- **Trade Direction**: BUY CALL OPTIONS (CE) by default

### Example 4: Bearish Market

**Market Data at 9:20 AM**:
```
Total stocks analyzed: 2000
Advancing stocks: 650
Declining stocks: 1250
Unchanged stocks: 100
```

**Calculation**:
```python
ad_ratio = 650 / 1250 = 0.52
market_breadth_percent = ((650 - 1250) / 2000) * 100 = -30%
```

**Result**:
```json
{
  "sentiment": "very_bearish",
  "confidence": 95,
  "metrics": {
    "advance_decline_ratio": 0.52,
    "market_breadth_percent": -30.0,
    "advancing": 650,
    "declining": 1250,
    "total_stocks": 2000
  }
}
```

**Interpretation**:
- 62.5% declining vs 32.5% advancing
- Broad-based selling pressure
- **Trade Direction**: BUY PUT OPTIONS (PE)

## Confidence Score Calculation

### Formula

```python
if sentiment in ["very_bullish", "very_bearish"]:
    confidence = min(95, abs(market_breadth_percent) * 4)
elif sentiment in ["bullish", "bearish"]:
    confidence = min(85, abs(market_breadth_percent) * 5)
else:  # neutral
    confidence = 50 + abs(market_breadth_percent)
```

### Confidence Ranges

| Sentiment | Min Confidence | Max Confidence |
|-----------|----------------|----------------|
| very_bullish | 60% | 95% |
| bullish | 25% | 85% |
| neutral | 50% | 60% |
| bearish | 25% | 85% |
| very_bearish | 60% | 95% |

### Interpretation

- **90-95%**: Extremely high confidence, strong directional move
- **75-85%**: High confidence, clear trend
- **60-75%**: Moderate confidence, developing trend
- **50-60%**: Low confidence, mixed signals

## Integration with Stock Selection

### Usage in Selection Service

From `intelligent_stock_selection_service.py`:

```python
async def run_premarket_selection():
    """Select stocks based on market sentiment"""

    # Step 1: Get market sentiment
    from services.realtime_market_engine import get_market_sentiment
    sentiment_data = get_market_sentiment()

    sentiment = sentiment_data["sentiment"]  # e.g., "bullish"
    confidence = sentiment_data["confidence"]  # e.g., 78.5
    ad_ratio = sentiment_data["metrics"]["advance_decline_ratio"]  # e.g., 1.75

    # Step 2: Use sentiment for sector weighting
    if sentiment in ["bullish", "very_bullish"]:
        # Prioritize growth sectors
        sector_weights = {
            "BANKING": 0.9,
            "IT": 0.8,
            "ENERGY": 0.7
        }
    elif sentiment in ["bearish", "very_bearish"]:
        # Prioritize defensive sectors
        sector_weights = {
            "PHARMA": 0.9,
            "FMCG": 0.8,
            "UTILITIES": 0.7
        }

    # Step 3: Select stocks and determine options direction
    selected_stocks = await select_stocks_by_value(top_sectors)

    for stock in selected_stocks:
        if sentiment in ["bullish", "very_bullish"]:
            stock.options_direction = "CE"  # CALL
        elif sentiment in ["bearish", "very_bearish"]:
            stock.options_direction = "PE"  # PUT
        else:
            stock.options_direction = "CE"  # Default CALL

    # Step 4: Save with market sentiment
    await save_selections_to_database(selected_stocks)
```

## Real-Time Updates

### Update Frequency

```python
# From realtime_market_engine.py
analytics_update_interval = 1.0  # 1 second
```

Sentiment is recalculated every second as new price data arrives via WebSocket.

### Event Broadcasting

```python
# Event emitted when sentiment changes
event_emitter.emit("analytics_update", {
    "sentiment": "bullish",
    "advance_decline_ratio": 1.75,
    "market_breadth_percent": 15.2,
    "timestamp": "2025-01-10T09:20:00Z"
})
```

## Historical Analysis

### Query Sentiment History

```sql
SELECT
    selection_date,
    market_sentiment,
    AVG(advance_decline_ratio) as avg_ad_ratio,
    AVG(market_breadth_percent) as avg_breadth,
    AVG(market_sentiment_confidence) as avg_confidence,
    COUNT(*) as stock_count
FROM selected_stocks
WHERE selection_date >= DATE_SUB(CURRENT_DATE, INTERVAL 30 DAY)
  AND selection_phase = 'final_selection'
GROUP BY selection_date, market_sentiment
ORDER BY selection_date DESC;
```

### Sentiment Distribution

```sql
SELECT
    market_sentiment,
    COUNT(*) as days_count,
    AVG(advance_decline_ratio) as avg_ad_ratio,
    MIN(advance_decline_ratio) as min_ad_ratio,
    MAX(advance_decline_ratio) as max_ad_ratio
FROM selected_stocks
WHERE selection_date >= DATE_SUB(CURRENT_DATE, INTERVAL 90 DAY)
  AND selection_phase = 'final_selection'
GROUP BY market_sentiment
ORDER BY market_sentiment;
```

---

**Next**: [Options Trading Direction](05_options_trading_direction.md)