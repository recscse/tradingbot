# Risk Management & Capital Engine (Stabilized Feb 2026)

## Overview
The Risk Management system ensures capital protection through single-point authority, deterministic execution, and a global emergency halt mechanism. It is designed to be investor-grade, race-condition free, and fully auditable.

---

## 🏛️ Core Risk Architecture

The system enforces **Strict Responsibility Separation**:
- **Entry Risk**: Managed by `CapitalManager` and `TradePrepService`.
- **Exit Risk**: Managed EXCLUSIVELY by `pnl_tracker.py`. Any position closure triggered outside this file is considered a critical bug.

---

## 🛡️ Key Risk Controls

### 1. Single Exit Authority
**Mandate:** No other component (Live Feed or Strategy) is allowed to trigger a position closure.
- **Why**: Eliminates double-close race conditions and conflicting exit signals.
- **Enforcement**: `pnl_tracker.py` maintains the authoritative monitoring loop for SL, Target, Trailing, and Time-based triggers.

### 2. Global Kill-Switch
An automatic emergency halt system monitored by the PnL Tracker.
- **Trigger Conditions**:
    - ❌ **Max Daily Loss**: Halt if session loss exceeds threshold (e.g., -₹5000).
    - ❌ **Excessive SL Hits**: Halt if strategy produces 3+ sequential losses in a short window.
- **Action**: Sets `shared_registry.is_risk_halted = True`.
- **Enforcement**: `AutoTradeLiveFeed` checks this flag before executing ANY entry order.

### 3. Charges-Aware Target Calculation
To prevent "Net Loss on Target Hit", the target price is dynamically adjusted by the preparation service.
- **Formula**: `Target = Entry + (Risk * RR) + Charges_Buffer + Safety_Margin`
- **Calculation**: Brokerage (₹40) + Taxes (~0.12% turnover) are converted to per-unit premium points and added to the mathematical target.

---

## 💰 Capital Management (`CapitalManager`)

### 1. Fund Integrity
- **Anchor**: Capital allocation is derived strictly from `ActivePosition.is_active == True`.
- **Ghost Prevention**: Once a position is marked inactive by the PnL Tracker, the capital is immediately released for new trades.

### 2. Position Sizing
- **Risk Floor**: If the calculated lot size is $\le 0$ (due to low capital or high premium), the trade is rejected.
- **Allocation Limit**: Capped at 60% of total available capital per trade to allow for concurrent positions.

---

## 📊 Post-Trade Diagnostics

Every closed trade captures mandatory diagnostics in the `metadata` column:
- `realized_rr`: The actual risk-to-reward ratio achieved after slippage and charges.
- `time_in_trade_min`: Exact duration from entry to exit.
- `exit_truth`: The raw trigger (STOP_LOSS_HIT, TARGET_HIT, TIME_BASED_EXIT, etc.).
- `diagnostic_check`: Health status of the trade execution data.

---

## 🧪 Simulation Integrity (Paper Trading)

Paper trading logic is identical to live trading logic to ensure metrics are valid for backtesting.
- **Symmetric Slippage**: 0.05% slippage is applied to BOTH Entry and Exit in Paper mode.
- **Logic Parity**: Every risk rule used in Live mode is active in Paper mode.