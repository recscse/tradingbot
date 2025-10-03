# Troubleshooting Guide

## Common Issues and Solutions

### 1. No Stocks Selected

#### Symptoms
- API returns empty stocks array
- Database has no records for today
- Logs show "Selected 0 stocks"

#### Possible Causes & Solutions

**A. WebSocket Not Connected**

```bash
# Check centralized_ws_manager status
curl http://localhost:8000/api/v1/system/websocket-status
```

**Solution**: Restart WebSocket connection
```python
# In app.py or via admin endpoint
await centralized_ws_manager.connect_websocket()
```

**B. Realtime Market Engine Not Receiving Data**

```python
# Check if engine has instruments
from services.realtime_market_engine import get_market_engine
engine = get_market_engine()
print(f"Total instruments: {len(engine.instruments)}")
print(f"Last update: {engine.analytics.last_calculation}")
```

**Solution**: Initialize engine with instruments
```python
from services.realtime_market_engine import initialize_market_engine
await initialize_market_engine(instruments_metadata)
```

**C. Insufficient F&O Stocks**

Check logs for:
```
❌ No eligible stocks found in sector BANKING
```

**Solution**: Lower minimum volume requirement
```python
# In intelligent_stock_selection_service.py
self.selection_config["min_volume"] = 50000  # Lower from 100000
```

**D. Score Threshold Too High**

Check logs for:
```
Selected 0 stocks with score > 0.15
```

**Solution**: Lower score threshold
```python
self.selection_config["min_score_threshold"] = 0.10  # Lower from 0.15
```

---

### 2. Wrong Options Direction (CE/PE)

#### Symptoms
- Bullish market but PE selected
- Bearish market but CE selected
- `option_type` field incorrect in database

#### Diagnosis

```sql
SELECT
    symbol,
    market_sentiment,
    advance_decline_ratio,
    option_type
FROM selected_stocks
WHERE selection_date = CURRENT_DATE;
```

#### Possible Causes & Solutions

**A. Market Sentiment Calculation Error**

```python
# Check sentiment calculation
from services.realtime_market_engine import get_market_sentiment
sentiment_data = get_market_sentiment()
print(f"Sentiment: {sentiment_data['sentiment']}")
print(f"A/D Ratio: {sentiment_data['metrics']['advance_decline_ratio']}")
```

**Expected**:
- Bullish → A/D > 1.3
- Bearish → A/D < 0.8

**Solution**: Verify advancing/declining stock counts
```python
engine = get_market_engine()
print(f"Advancing: {engine.analytics.advancing_stocks}")
print(f"Declining: {engine.analytics.declining_stocks}")
```

**B. Options Direction Logic Error**

Check `_get_options_direction()` method:

```python
# Should return CE for bullish, PE for bearish
direction = service._get_options_direction()
print(f"Current sentiment: {service.current_sentiment}")
print(f"Options direction: {direction}")
```

**Solution**: Verify sentiment mapping
```python
if sentiment in ["bullish", "very_bullish"]:
    assert direction == "CE", "Should be CALL for bullish"
elif sentiment in ["bearish", "very_bearish"]:
    assert direction == "PE", "Should be PUT for bearish"
```

---

### 3. Market Sentiment Always Neutral

#### Symptoms
- Sentiment never changes from "neutral"
- A/D ratio always around 1.0
- Confidence always ~50%

#### Diagnosis

```python
from services.realtime_market_engine import get_market_engine
engine = get_market_engine()

print(f"Total instruments: {len(engine.instruments)}")
print(f"Advancing: {engine.analytics.advancing_stocks}")
print(f"Declining: {engine.analytics.declining_stocks}")
print(f"With price data: {sum(1 for i in engine.instruments.values() if i.current_price > 0)}")
```

#### Possible Causes & Solutions

**A. Insufficient Instrument Data**

```
Total instruments: 50
With price data: 10
```

**Solution**: Ensure instruments are initialized
```python
# Load instrument metadata
instruments = load_instruments_from_file()
await engine.initialize_instruments(instruments)
```

**B. No Live Updates**

```python
# Check last update time
last_update = engine.analytics.last_calculation
import time
age_seconds = time.time() - last_update
print(f"Analytics age: {age_seconds} seconds")
```

**Solution**: Restart WebSocket feed
```bash
# Restart centralized_ws_manager
curl -X POST http://localhost:8000/api/v1/system/restart-websocket
```

**C. All Prices Unchanged**

```python
# Check price changes
unchanged = sum(1 for i in engine.instruments.values() if i.change_percent == 0)
total = len(engine.instruments)
print(f"Unchanged: {unchanged}/{total} ({unchanged/total*100:.1f}%)")
```

**Solution**: Wait for market open or use test data

---

### 4. Premarket Selection Not Saved

#### Symptoms
- API returns success but database empty
- Logs show "Saved 5 stocks" but query returns 0

#### Diagnosis

```sql
SELECT COUNT(*) FROM selected_stocks
WHERE selection_date = CURRENT_DATE
  AND selection_phase = 'premarket';
```

#### Possible Causes & Solutions

**A. Database Connection Error**

Check logs for:
```
❌ Error saving selections to database: connection refused
```

**Solution**: Verify database connection
```python
from database.connection import SessionLocal
db = SessionLocal()
try:
    db.execute("SELECT 1")
    print("Database connected")
except Exception as e:
    print(f"Database error: {e}")
```

**B. Transaction Rollback**

Check logs for:
```
❌ Error saving selections to database: ...
Database rollback executed
```

**Solution**: Check for constraint violations
```sql
-- Check for duplicate entries
SELECT symbol, selection_date, COUNT(*)
FROM selected_stocks
WHERE selection_date = CURRENT_DATE
GROUP BY symbol, selection_date
HAVING COUNT(*) > 1;
```

**C. Migration Not Run**

```bash
# Check if new columns exist
mysql -u user -p database -e "DESCRIBE selected_stocks" | grep market_sentiment
```

**Solution**: Run migrations
```bash
alembic upgrade head
```

---

### 5. Market Open Validation Not Running

#### Symptoms
- Stuck in premarket phase at 9:30 AM
- `final_selection_done` still false
- No "final_selection" phase records

#### Diagnosis

```python
from services.intelligent_stock_selection_service import intelligent_stock_selector

print(f"Current phase: {intelligent_stock_selector.current_phase}")
print(f"Final selection done: {intelligent_stock_selector.final_selection_done}")
print(f"Premarket selections: {len(intelligent_stock_selector.premarket_selections)}")
```

#### Possible Causes & Solutions

**A. Premarket Not Run First**

**Solution**: Run premarket selection
```bash
curl -X POST http://localhost:8000/api/v1/auto-trading/run-stock-selection \
  -H "Authorization: Bearer $TOKEN"
```

**B. Wrong Time Window**

Check current time:
```python
from datetime import datetime
now = datetime.now().time()
print(f"Current time: {now}")
print(f"Market open window: 09:15:00 - 09:25:00")
```

**Solution**: Wait for market open or use manual trigger

**C. Service Not Initialized**

```python
# Check if service has market_engine
if not intelligent_stock_selector.market_engine:
    await intelligent_stock_selector.initialize_services()
```

---

### 6. Auto-Trading Not Executing

#### Symptoms
- Stocks selected but no trades executed
- Trading session active but no positions
- Logs show "0 trades executed"

#### Diagnosis

```bash
# Check trading session status
curl http://localhost:8000/api/v1/auto-trading/session-status \
  -H "Authorization: Bearer $TOKEN"
```

#### Possible Causes & Solutions

**A. Trading Session Not Started**

```json
{
  "is_active": false
}
```

**Solution**: Start trading session
```bash
curl -X POST http://localhost:8000/api/v1/auto-trading/start-session \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "PAPER_TRADING",
    "max_positions": 5,
    "max_daily_loss": 50000
  }'
```

**B. No Final Selections**

```sql
SELECT COUNT(*) FROM selected_stocks
WHERE selection_date = CURRENT_DATE
  AND selection_phase = 'final_selection'
  AND is_active = TRUE;
```

**Solution**: Run market open validation

**C. Risk Limits Exceeded**

Check logs for:
```
⚠️ Max daily loss reached: ₹50,000
⚠️ Max positions limit: 5/5
```

**Solution**: Adjust risk parameters or wait for next day

---

### 7. Database Migration Errors

#### Error: Column already exists

```
sqlalchemy.exc.OperationalError: (1060, "Duplicate column name 'market_sentiment'")
```

**Solution**: Skip this migration or drop column first
```bash
# Downgrade one revision
alembic downgrade -1

# Then upgrade again
alembic upgrade head
```

#### Error: No such table

```
sqlalchemy.exc.OperationalError: no such table: selected_stocks
```

**Solution**: Create all tables
```bash
# Run all migrations from scratch
alembic upgrade head
```

---

### 8. WebSocket Disconnections

#### Symptoms
- Frequent connection drops
- Logs show "WebSocket disconnected"
- No real-time data updates

#### Diagnosis

```bash
# Check WebSocket status
curl http://localhost:8000/api/v1/system/websocket-status
```

#### Solutions

**A. Network Issues**

```bash
# Test connectivity
ping ws-feed.upstox.com
```

**B. Token Expiry**

Check logs for:
```
❌ WebSocket authentication failed: token expired
```

**Solution**: Refresh access token
```python
from services.upstox.token_manager import refresh_upstox_token
await refresh_upstox_token()
```

**C. Rate Limiting**

Check logs for:
```
⚠️ Rate limit exceeded: 429 Too Many Requests
```

**Solution**: Implement backoff strategy or reduce subscription count

---

## Logging and Debugging

### Enable Debug Logging

```python
import logging
logging.getLogger("services.intelligent_stock_selection_service").setLevel(logging.DEBUG)
logging.getLogger("services.realtime_market_engine").setLevel(logging.DEBUG)
```

### Key Log Messages

```bash
# Successful stock selection
✅ Saved 5 intelligent stock selections to database
📊 Market Context: bullish sentiment, A/D ratio: 1.75
📈 Options Direction: CE (based on market sentiment)

# Market sentiment calculation
📊 Market sentiment: bullish (A/D ratio: 1.75)

# Sector analysis
🏢 Top sectors for bullish: ['BANKING', 'IT', 'ENERGY']

# Stock selection
📈 Selected 5 stocks: ['HDFC', 'INFY', 'RELIANCE', 'TCS', 'ICICIBANK']
```

### Database Queries for Debugging

```sql
-- Check today's selections
SELECT * FROM selected_stocks
WHERE selection_date = CURRENT_DATE
ORDER BY selection_score DESC;

-- Check market sentiment distribution
SELECT market_sentiment, COUNT(*) as count
FROM selected_stocks
WHERE selection_date >= DATE_SUB(CURRENT_DATE, INTERVAL 7 DAY)
GROUP BY market_sentiment;

-- Check options direction
SELECT option_type, COUNT(*) as count
FROM selected_stocks
WHERE selection_date = CURRENT_DATE
GROUP BY option_type;
```

---

## Getting Help

If issues persist:

1. **Check Logs**: Review application logs for error messages
2. **Verify Configuration**: Ensure environment variables are set
3. **Test Components**: Test each component individually
4. **Database State**: Query database to verify data
5. **API Status**: Check system health endpoints

---

**Previous**: [API Endpoints](07_api_endpoints.md)