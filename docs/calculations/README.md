# Calculations & Logic

This section defines the mathematical formulas and logic used for key trading metrics.

## Profit & Loss (PnL)

### Unrealized PnL (Open Positions)
For an active position, PnL is calculated in real-time based on current market price.

**Formula (Long/Buy):**
$$ PnL = (Current Price - Entry Price) 	imes Quantity $$

**Formula (Short/Sell):**
$$ PnL = (Entry Price - Current Price) 	imes Quantity $$

### Realized PnL (Closed Positions)
Once a trade is closed, the PnL is finalized.

**Formula:**
$$ Realized PnL = (Exit Price - Entry Price) 	imes Quantity 	imes Direction $$
*(Where Direction is 1 for Long, -1 for Short)*

### Total Portfolio PnL
$$ Total PnL = \sum (Realized PnL) + \sum (Unrealized PnL) $$

## Risk Management

### Position Sizing
Determines the quantity to trade based on risk tolerance.

**Formula:**
$$ Quantity = \frac{Account Balance 	imes Risk Per Trade \%}{Stop Loss Amount Per Unit} $$

*   **Risk Per Trade %:** Defined in `UserTradingConfig` (default 1-2%).
*   **Stop Loss Amount:** `|Entry Price - Stop Loss Price|`.

### Margin Requirements
(Paper Trading Approximation)

$$ Used Margin = Entry Price 	imes Quantity 	imes Margin Factor $$

*   **Intraday Margin Factor:** Typically 0.2 (5x leverage) for equities, subject to broker settings.
*   **Delivery Margin Factor:** 1.0 (1x leverage).

## Technical Indicators

### Moving Averages (SMA/EMA)
Used in `Breakout Strategy`.

*   **SMA (Simple Moving Average):** Average of closing prices over $N$ periods.
*   **EMA (Exponential Moving Average):** Weighted average giving more importance to recent prices.

### Relative Strength Index (RSI)
Momentum oscillator used to identify overbought/oversold conditions.

*   **Range:** 0 to 100
*   **Overbought:** > 70
*   **Oversold:** < 30
