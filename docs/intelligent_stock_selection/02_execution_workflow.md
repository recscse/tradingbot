# Execution Workflow

## When Does the System Run?

The Intelligent Stock Selection System operates in three distinct phases throughout the trading day:

```
8:00 AM ────────── 9:15 AM ────────── 9:25 AM ────────── 3:30 PM
   │                  │                  │                  │
Premarket         Market Open       Live Trading       Market Close
Selection         Validation        (Final Selections)
```

## Phase 1: Premarket Selection (9:00 AM)

### Trigger

**AUTOMATIC** - MarketScheduleService triggers at 9:00 AM

```python
# Runs automatically via MarketScheduleService
# services/market_schedule_service.py
async def _run_premarket_analysis():
    """Triggers at 9:00 AM automatically"""
    result = await intelligent_stock_selector.run_premarket_selection()
```

**Alternative**: Manual API call
```http
POST /api/v1/auto-trading/run-stock-selection
Authorization: Bearer {token}
```

### Timing
- **Automatic Trigger**: 9:00 AM (Monday-Friday)
- **Execution Time**: ~15-30 seconds
- **Completes Before**: 9:15 AM (market open)

### What Happens

```python
async def run_premarket_selection():
    """
    Premarket stock selection workflow
    """
    # Step 1: Get current market sentiment
    sentiment, sentiment_analysis = await analyze_market_sentiment()
    # Uses previous day data + premarket indicators

    # Step 2: Analyze sector strength
    sector_scores = await analyze_sector_strength(sentiment)
    # Ranks all sectors based on sentiment alignment

    # Step 3: Select top sectors
    top_sectors = list(sector_scores.keys())[:3]
    # Example: ['BANKING', 'IT', 'ENERGY']

    # Step 4: Select stocks from top sectors
    selected_stocks = await select_stocks_by_value(top_sectors)
    # Max 5 F&O stocks with highest trading value

    # Step 5: Store in database
    await save_selections_to_database(
        selected_stocks,
        selection_type="premarket"
    )
    # Stores with selection_phase = "premarket"
```

### Database State After Premarket

| Field | Value |
|-------|-------|
| `selection_phase` | "premarket" |
| `market_sentiment` | e.g., "bullish" |
| `advance_decline_ratio` | e.g., 1.45 |
| `option_type` | "CE" or "PE" |
| `is_active` | `true` |

### Output Example

```json
{
  "phase": "premarket",
  "sentiment_analysis": {
    "sentiment": "bullish",
    "confidence": 72.5,
    "advance_decline_ratio": 1.45,
    "market_breadth_percent": 12.3
  },
  "selected_stocks": [
    {
      "symbol": "HDFCBANK",
      "sector": "BANKING",
      "selection_score": 0.78,
      "options_direction": "CE"
    }
  ],
  "selection_count": 5,
  "next_validation": "09:15:00"
}
```

### Can Run Multiple Times?
**YES** - Until market opens (9:15 AM), you can re-run premarket selection. Each run replaces previous premarket selections.

---

## Phase 2: Market Open Validation (9:15 AM - 9:25 AM)

### Trigger

**Same API Call** during market open window

```http
POST /api/v1/auto-trading/run-stock-selection
```

Or automatically triggered by coordinator at 9:20 AM.

### Timing
- **Window**: 9:15 AM - 9:25 AM (10-minute window)
- **Recommended**: 9:20 AM (5 minutes after open)

### What Happens

```python
async def validate_market_open_selection():
    """
    Market open validation - FINAL DECISION
    """
    # Step 1: Check if premarket selections exist
    if not self.premarket_selections:
        return {"error": "Run premarket selection first"}

    # Step 2: Get LIVE market sentiment
    market_sentiment, analysis = await analyze_market_sentiment()
    # Uses real opening data, live A/D ratio

    # Step 3: Compare with premarket sentiment
    sentiment_changed = (market_sentiment != premarket_sentiment)

    if sentiment_changed:
        # SCENARIO A: Sentiment changed
        logger.info("Sentiment changed - Running NEW selection")

        # Run fresh selection with new sentiment
        sector_scores = await analyze_sector_strength(market_sentiment)
        top_sectors = list(sector_scores.keys())[:3]
        final_selections = await select_stocks_by_value(top_sectors)

    else:
        # SCENARIO B: Sentiment unchanged
        logger.info("Sentiment unchanged - Confirming premarket")

        # Use premarket selections as-is
        final_selections = self.premarket_selections.copy()

    # Step 4: Mark as FINAL and LOCK
    self.final_selections = final_selections
    self.final_selection_done = True  # NO MORE CHANGES

    # Step 5: Save to database
    await save_selections_to_database(
        final_selections,
        selection_type="final_selection"
    )
```

### Decision Matrix

| Premarket Sentiment | Market Open Sentiment | Action |
|---------------------|----------------------|--------|
| bullish | bullish | ✅ Confirm premarket selections |
| bullish | very_bullish | 🔄 Run NEW selection (stronger sentiment) |
| bullish | neutral | 🔄 Run NEW selection (sentiment weakened) |
| bullish | bearish | 🔄 Run NEW selection (sentiment reversed) |
| bearish | bearish | ✅ Confirm premarket selections |
| bearish | bullish | 🔄 Run NEW selection (sentiment reversed) |
| neutral | bullish | 🔄 Run NEW selection (sentiment strengthened) |
| neutral | bearish | 🔄 Run NEW selection (sentiment strengthened) |

### Database State After Validation

| Field | Value |
|-------|-------|
| `selection_phase` | **"final_selection"** |
| `market_sentiment` | Updated with live data |
| `advance_decline_ratio` | Live A/D ratio at 9:20 AM |
| `option_type` | "CE" or "PE" (may change) |
| `is_active` | `true` |

### Output Example

```json
{
  "phase": "market_open_validation",
  "validation_action": "PREMARKET_SELECTIONS_CONFIRMED",
  "sentiment_changed": false,
  "premarket_sentiment": "bullish",
  "market_open_sentiment": "bullish",
  "final_stocks": [
    {
      "symbol": "HDFCBANK",
      "sector": "BANKING",
      "selection_score": 0.78,
      "options_direction": "CE"
    }
  ],
  "final_selection_done": true,
  "ready_for_trading": true
}
```

### Can Run Multiple Times?
**NO** - Once final selections are made and locked (`final_selection_done = true`), no more changes are allowed for the day.

---

## Phase 3: Live Trading (9:25 AM - 3:30 PM)

### Trigger

**Auto-trading system** or **API queries**

```http
GET /api/v1/auto-trading/selected-stocks
```

### What Happens

```python
async def get_live_trading_recommendations():
    """
    Returns FINAL selections - NO NEW SELECTION
    """
    if not self.final_selection_done:
        return {
            "error": "Final selections not ready",
            "message": "Run market open validation first"
        }

    # Return locked final selections
    return {
        "phase": "live_trading",
        "recommendations": [asdict(stock) for stock in self.final_selections],
        "final_selection_done": true,
        "message": "These are FINAL selections - no more changes today"
    }
```

### Auto-Trading Integration

```python
# Auto-trading system reads selections
selected_stocks = get_selected_stocks_from_db()

for stock in selected_stocks:
    if stock.market_sentiment in ['bullish', 'very_bullish']:
        # Buy CALL options
        execute_trade(
            symbol=stock.symbol,
            option_type="CE",  # CALL
            strategy="bullish_market"
        )
    elif stock.market_sentiment in ['bearish', 'very_bearish']:
        # Buy PUT options
        execute_trade(
            symbol=stock.symbol,
            option_type="PE",  # PUT
            strategy="bearish_market"
        )
```

### Database Queries During Live Trading

```sql
-- Get today's final selections
SELECT
    symbol,
    sector,
    option_type,
    market_sentiment,
    advance_decline_ratio,
    selection_score
FROM selected_stocks
WHERE selection_date = CURRENT_DATE
  AND selection_phase = 'final_selection'
  AND is_active = true
ORDER BY selection_score DESC;
```

---

## Complete Daily Workflow Example

### Timeline

```
08:30 AM - Premarket Selection Triggered
─────────────────────────────────────────────
📊 Analyzing premarket sentiment...
   Sentiment: bullish (A/D: 1.45)

🏢 Analyzing sectors...
   Top sectors: BANKING (0.85), IT (0.78), ENERGY (0.72)

📈 Selecting stocks...
   Selected: HDFC, INFY, RELIANCE, TCS, ICICIBANK

💾 Saving to database...
   ✅ 5 stocks saved with phase = "premarket"

📣 Broadcasting via WebSocket...
   ✅ Premarket selection completed


09:15 AM - Market Opens
─────────────────────────────────────────────
📡 Live prices flowing in...
   Real-time A/D calculation: 1.62


09:20 AM - Market Open Validation Triggered
─────────────────────────────────────────────
📊 Analyzing live market sentiment...
   Premarket sentiment: bullish (A/D: 1.45)
   Live sentiment: bullish (A/D: 1.62)

✅ Sentiment UNCHANGED - Confirming premarket selections

🔒 Locking final selections...
   final_selection_done = true

💾 Updating database...
   ✅ 5 stocks updated with phase = "final_selection"
   ✅ Live A/D ratio: 1.62

📣 Broadcasting via WebSocket...
   ✅ Final selections ready for trading


09:25 AM - Auto-Trading Starts
─────────────────────────────────────────────
📖 Reading final selections from database...
   5 stocks retrieved

📈 Executing trades...
   HDFC: Buying CE (CALL) options - bullish market
   INFY: Buying CE (CALL) options - bullish market
   RELIANCE: Buying CE (CALL) options - bullish market
   TCS: Buying CE (CALL) options - bullish market
   ICICIBANK: Buying CE (CALL) options - bullish market

✅ All positions opened


10:00 AM - 3:30 PM - Position Monitoring
─────────────────────────────────────────────
📊 Monitoring positions in real-time...
   Applying stop-loss and target management

✅ Trading continues until market close
```

---

## Workflow State Machine

```
┌─────────────┐
│   IDLE      │
└──────┬──────┘
       │
       │ Trigger: run_premarket_selection()
       ▼
┌─────────────────────┐
│  PREMARKET_RUNNING  │
└──────┬──────────────┘
       │
       │ Complete
       ▼
┌─────────────────────┐
│ PREMARKET_COMPLETED │◄─── Can re-run until 9:15 AM
└──────┬──────────────┘
       │
       │ Trigger: validate_market_open() (9:15-9:25 AM)
       ▼
┌──────────────────────┐
│  VALIDATION_RUNNING  │
└──────┬───────────────┘
       │
       │ Complete
       ▼
┌──────────────────────┐
│  FINAL_SELECTIONS    │◄─── LOCKED - No more changes
└──────┬───────────────┘
       │
       │ Auto-trading reads selections
       ▼
┌──────────────────────┐
│   LIVE_TRADING       │
└──────┬───────────────┘
       │
       │ Market close (3:30 PM)
       ▼
┌─────────────┐
│  COMPLETED  │
└─────────────┘
```

---

## Error Scenarios

### Scenario 1: Premarket Not Run
```
User tries market open validation without premarket selection
→ Error: "Run premarket selection first"
→ Action: Trigger premarket selection API
```

### Scenario 2: Validation After 9:25 AM
```
User tries validation at 9:30 AM
→ System allows (manual override)
→ Warning: "Outside validation window"
→ Proceeds with validation
```

### Scenario 3: Re-running After Final Lock
```
User tries to re-run selection at 10:00 AM
→ Error: "Final selections already locked"
→ Returns existing final selections
→ No database changes
```

---

**Next**: [Database Schema](03_database_schema.md)