# Trade Execution Workflow (Stabilized Feb 2026)

## Overview
This document details the deterministic logic flow from signal detection to position closure. The system is designed to eliminate race conditions through strict ownership separation.

---

## 🏛️ Responsibility Separation

### 1. Entry Authority: `AutoTradeLiveFeed`
- Responsible for market data ingestion and order placement for **NEW** positions.
- Checks global risk halt status before entry.
- Triggers strategy calculation only on completed candles.

### 2. Exit Authority: `pnl_tracker.py`
- Sole component allowed to close positions.
- Owns all Stop Loss (SL), Target, and Trailing logic.
- Executes 3:20 PM intraday square-off.

---

## 📈 Step-by-Step Execution Flow

### Step 1: Signal Detection (Candle-Gated)
- `AutoTradeLiveFeed` receives ticks but calculates strategy **ONLY** when a new completed candle is detected.
- Uses `last_processed_candle_count` to ensure exactly one signal per candle per symbol.

### Step 2: Signal Validation
- `StrategyEngine` generates a Spot-based signal using SuperTrend + EMA.
- Requires 2-candle trend confirmation for high-confidence entries.
- Standardized as **BUY** for both CE and PE.

### Step 3: Trade Preparation
- `TradePrepService` receives the pre-generated signal.
- Validates current capital and concurrent position limits.
- **Charge-Aware Target**: Adds a dynamic buffer to the target price to ensure net profit after brokerage/taxes.

### Step 4: Order Execution
- `execution_handler` sends the order to the broker.
- Paper trading applies symmetric **0.05% slippage** to simulate real impact.
- On success, `ActivePosition` is created with `is_active=True`.

### Step 5: Authoritative Monitoring
- `pnl_tracker` runs a dedicated loop monitoring all `is_active` positions.
- Uses **Soft Guards** to correct logic errors without crashing the loop.
- Updates premium-based trailing stops (upward only).

### Step 6: Position Closure
- Only the tracker triggers the exit call when SL/Target/Time condition is met.
- Captures mandatory post-trade diagnostics: `realized_rr`, `time_in_trade`, `exit_truth`.
- Marks `is_active=False`, immediately releasing capital in `CapitalManager`.

---

## 🛡️ Stability Gating

| Mechanism | Purpose |
| :--- | :--- |
| **Candle-Gating** | Prevents multiple duplicate trades in a single minute. |
| **Restart Safety** | Prevents historical data bursts on service restart. |
| **Kill-Switch** | Halts session entries on total daily loss threshold. |
| **Charges Buffer** | Guarantees net profitability on every target hit. |