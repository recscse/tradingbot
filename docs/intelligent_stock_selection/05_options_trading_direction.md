# Options Trading Direction (CE/PE Selection)

## Overview

The system automatically determines whether to trade **CALL options (CE)** or **PUT options (PE)** based on real-time market sentiment calculated from advance/decline ratios.

## Decision Matrix

### Complete Mapping

| Market Sentiment | A/D Ratio | Breadth % | Options Type | Strategy |
|------------------|-----------|-----------|--------------|----------|
| **very_bullish** | > 2.0 | > 15% | **CE (CALL)** | Aggressive long calls |
| **bullish** | > 1.3 | > 5% | **CE (CALL)** | Standard long calls |
| **neutral** | 0.8-1.3 | -5% to 5% | **CE (CALL)** | Conservative calls |
| **bearish** | < 0.8 | < -5% | **PE (PUT)** | Standard long puts |
| **very_bearish** | < 0.5 | < -15% | **PE (PUT)** | Aggressive long puts |

## Implementation

### Code Logic

From `intelligent_stock_selection_service.py`:

```python
def _get_options_direction(self) -> str:
    """
    Determine options trading direction based on market sentiment.

    Returns:
        str: "CE" for CALL options, "PE" for PUT options
    """
    current_sentiment = self.current_sentiment

    # Bullish markets → CALL options
    if current_sentiment in [MarketSentiment.VERY_BULLISH, MarketSentiment.BULLISH]:
        return "CE"

    # Bearish markets → PUT options
    elif current_sentiment in [MarketSentiment.VERY_BEARISH, MarketSentiment.BEARISH]:
        return "PE"

    # Neutral or unknown → Default to CALL
    else:
        return "CE"  # Conservative default
```

### Storage in Database

```python
async def save_selections_to_database(selections):
    """Save with options direction based on sentiment"""

    for stock in selections:
        selected_stock = SelectedStock(
            symbol=stock.symbol,
            market_sentiment="bullish",  # From market analysis
            option_type=stock.options_direction,  # "CE" or "PE"
            # ... other fields
        )
        db.add(selected_stock)
```

## Trading Scenarios

### Scenario 1: Very Bullish Market

**Market Conditions**:
```json
{
  "sentiment": "very_bullish",
  "advance_decline_ratio": 3.5,
  "market_breadth_percent": 45.0,
  "advancing_stocks": 1600,
  "declining_stocks": 400
}
```

**Selected Stocks**:
```json
[
  {
    "symbol": "RELIANCE",
    "sector": "ENERGY",
    "market_sentiment": "very_bullish",
    "option_type": "CE",
    "price_at_selection": 2450.50
  },
  {
    "symbol": "HDFCBANK",
    "sector": "BANKING",
    "market_sentiment": "very_bullish",
    "option_type": "CE",
    "price_at_selection": 1620.00
  }
]
```

**Auto-Trading Execution**:
```python
for stock in selected_stocks:
    if stock.option_type == "CE":
        # Buy CALL options
        atm_strike = round_to_nearest_strike(stock.price_at_selection)
        execute_trade(
            symbol=stock.symbol,
            option_type="CE",
            strike=atm_strike,  # e.g., 2450 for RELIANCE
            quantity=stock.lot_size,
            strategy="bullish_market_call"
        )
```

**Expected Outcome**:
- RELIANCE 2450 CE bought
- HDFCBANK 1620 CE bought
- Profit if stocks rally

### Scenario 2: Bearish Market

**Market Conditions**:
```json
{
  "sentiment": "bearish",
  "advance_decline_ratio": 0.6,
  "market_breadth_percent": -12.0,
  "advancing_stocks": 750,
  "declining_stocks": 1250
}
```

**Selected Stocks**:
```json
[
  {
    "symbol": "TATASTEEL",
    "sector": "METALS",
    "market_sentiment": "bearish",
    "option_type": "PE",
    "price_at_selection": 850.00
  },
  {
    "symbol": "BAJFINANCE",
    "sector": "BANKING",
    "market_sentiment": "bearish",
    "option_type": "PE",
    "price_at_selection": 6500.00
  }
]
```

**Auto-Trading Execution**:
```python
for stock in selected_stocks:
    if stock.option_type == "PE":
        # Buy PUT options
        atm_strike = round_to_nearest_strike(stock.price_at_selection)
        execute_trade(
            symbol=stock.symbol,
            option_type="PE",
            strike=atm_strike,  # e.g., 850 for TATASTEEL
            quantity=stock.lot_size,
            strategy="bearish_market_put"
        )
```

**Expected Outcome**:
- TATASTEEL 850 PE bought
- BAJFINANCE 6500 PE bought
- Profit if stocks decline

### Scenario 3: Neutral Market

**Market Conditions**:
```json
{
  "sentiment": "neutral",
  "advance_decline_ratio": 1.05,
  "market_breadth_percent": 2.0,
  "advancing_stocks": 1020,
  "declining_stocks": 970
}
```

**Selected Stocks**:
```json
[
  {
    "symbol": "INFY",
    "sector": "IT",
    "market_sentiment": "neutral",
    "option_type": "CE",
    "price_at_selection": 1450.00
  }
]
```

**Auto-Trading Execution**:
```python
# Neutral defaults to CALL (conservative)
execute_trade(
    symbol="INFY",
    option_type="CE",
    strike=1450,
    quantity=lot_size,
    strategy="neutral_market_call"
)
```

**Rationale**: In neutral markets, slight bullish bias (buying calls) is safer than shorting.

## Strike Selection

### ATM (At-The-Money) Strategy

```python
def select_atm_strike(current_price: float, strike_interval: int = 50) -> int:
    """
    Select ATM strike closest to current price.

    Args:
        current_price: Current stock LTP
        strike_interval: Strike price interval (50 for most stocks)

    Returns:
        ATM strike price
    """
    return round(current_price / strike_interval) * strike_interval
```

**Examples**:
- Current Price: 2447.50 → ATM Strike: 2450
- Current Price: 1618.20 → ATM Strike: 1600 (or 1650 depending on interval)
- Current Price: 845.60 → ATM Strike: 850

### Premium Collection

```python
# For CALL options (CE)
if market_sentiment in ["bullish", "very_bullish"]:
    # Buy ATM or slightly OTM calls
    strike = atm_strike  # or atm_strike + strike_interval

# For PUT options (PE)
if market_sentiment in ["bearish", "very_bearish"]:
    # Buy ATM or slightly OTM puts
    strike = atm_strike  # or atm_strike - strike_interval
```

## Expiry Selection

### Weekly vs Monthly

```python
def select_expiry(market_sentiment: str) -> str:
    """
    Select option expiry based on sentiment strength.

    Strong sentiment → Weekly expiry (higher returns, higher risk)
    Weak sentiment → Monthly expiry (lower returns, lower risk)
    """
    if market_sentiment in ["very_bullish", "very_bearish"]:
        # Strong directional move expected
        return "nearest_weekly"  # e.g., this Thursday

    elif market_sentiment in ["bullish", "bearish"]:
        # Moderate move expected
        return "next_weekly"  # e.g., next Thursday

    else:  # neutral
        # Slow move expected
        return "monthly"  # e.g., last Thursday of month
```

## Risk Management

### Position Sizing

```python
def calculate_position_size(
    capital: float,
    risk_per_trade: float,
    option_premium: float,
    lot_size: int
) -> int:
    """
    Calculate number of lots to trade based on risk.

    Args:
        capital: Total trading capital
        risk_per_trade: Risk per trade (e.g., 0.02 for 2%)
        option_premium: Premium per option
        lot_size: Lot size for the stock

    Returns:
        Number of lots to trade
    """
    max_risk_amount = capital * risk_per_trade
    cost_per_lot = option_premium * lot_size
    max_lots = int(max_risk_amount / cost_per_lot)

    return max(1, max_lots)  # At least 1 lot
```

**Example**:
```python
capital = 500000  # ₹5 lakhs
risk_per_trade = 0.02  # 2%
option_premium = 45.50  # RELIANCE 2450 CE
lot_size = 250  # RELIANCE lot size

max_risk = 500000 * 0.02 = 10000
cost_per_lot = 45.50 * 250 = 11375
max_lots = 10000 / 11375 = 0.87 ≈ 0 lots

# Adjust: Use 1 lot (risk = ₹11,375 or 2.28%)
```

### Stop-Loss

```python
def set_stop_loss(option_type: str, entry_price: float) -> float:
    """
    Set stop-loss for options position.

    Args:
        option_type: "CE" or "PE"
        entry_price: Entry premium

    Returns:
        Stop-loss price
    """
    # 30% stop-loss for options
    stop_loss_percent = 0.30

    stop_loss = entry_price * (1 - stop_loss_percent)

    return round(stop_loss, 2)
```

**Example**:
```python
entry_premium = 45.50  # RELIANCE 2450 CE
stop_loss = 45.50 * (1 - 0.30) = 31.85

# Exit if premium falls to ₹31.85
```

### Target

```python
def set_target(option_type: str, entry_price: float) -> float:
    """
    Set profit target for options position.

    Args:
        option_type: "CE" or "PE"
        entry_price: Entry premium

    Returns:
        Target price
    """
    # 50% profit target for options
    target_percent = 0.50

    target = entry_price * (1 + target_percent)

    return round(target, 2)
```

**Example**:
```python
entry_premium = 45.50  # RELIANCE 2450 CE
target = 45.50 * (1 + 0.50) = 68.25

# Exit if premium rises to ₹68.25
```

## Complete Trading Example

### Input: Market Open at 9:20 AM

```json
{
  "market_data": {
    "sentiment": "bullish",
    "advance_decline_ratio": 1.75,
    "market_breadth_percent": 15.2,
    "confidence": 78.5
  },
  "selected_stocks": [
    {
      "symbol": "RELIANCE",
      "ltp": 2447.50,
      "lot_size": 250
    }
  ]
}
```

### Decision: Buy CALL Option

```python
# System determines CE (CALL) based on bullish sentiment
option_type = "CE"

# Select ATM strike
atm_strike = round(2447.50 / 50) * 50 = 2450

# Get option chain
option_data = get_option_chain("RELIANCE", expiry="2025-01-31")
call_option = option_data["CE"][2450]

# Option details
premium = call_option["ltp"]  # e.g., 45.50
iv = call_option["iv"]  # e.g., 28.5%
delta = call_option["delta"]  # e.g., 0.52

# Calculate position
capital = 500000
risk_per_trade = 0.02
lots = calculate_position_size(capital, risk_per_trade, premium, 250)

# Set risk parameters
stop_loss = set_stop_loss("CE", premium)  # 31.85
target = set_target("CE", premium)  # 68.25

# Execute trade
execute_trade(
    symbol="RELIANCE",
    option_type="CE",
    strike=2450,
    expiry="2025-01-31",
    quantity=250 * lots,
    entry_price=45.50,
    stop_loss=31.85,
    target=68.25
)
```

### Output: Trade Executed

```json
{
  "trade_id": "TR_20250110_001",
  "symbol": "RELIANCE",
  "instrument": "RELIANCE 2450 CE 31-Jan-2025",
  "option_type": "CE",
  "strike": 2450,
  "expiry": "2025-01-31",
  "entry_price": 45.50,
  "quantity": 250,
  "lot_size": 250,
  "lots": 1,
  "total_cost": 11375,
  "stop_loss": 31.85,
  "target": 68.25,
  "market_sentiment": "bullish",
  "advance_decline_ratio": 1.75,
  "timestamp": "2025-01-10T09:25:00Z"
}
```

---

**Next**: [Stock Selection Criteria](06_stock_selection_criteria.md)