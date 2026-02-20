# Auto-Trading System Stabilization Report (February 2026)

## Overview
This document summarizes the critical architectural stabilization applied to the algorithmic trading system to ensure deterministic execution, race-condition freedom, and capital safety.

---

## 🏛️ Core Mandates

### 1. Single Exit Authority
**Mandate:** `pnl_tracker.py` is the ONLY component allowed to close trades.
- **AutoTradeLiveFeed**: Completely neutralized for exits. It handles **Entry-Only** execution and UI price/PnL updates.
- **StrategyEngine**: Neutralized for exit blocking. It purely generates signals and does not enforce hold times or profit percentages.
- **Effect**: Eliminates double-close race conditions and conflicting exit logic.

### 2. Deterministic Execution (Candle-Gating)
**Mandate:** One completed candle → One strategy signal → One trade max.
- **Mechanism**: Implemented `last_processed_candle_count` gating in `SharedInstrumentRegistry`.
- **Startup Safety**: `last_processed_candle_count` is initialized on system start to prevent "startup trade bursts" from historical data.
- **Effect**: Drastically reduces over-trading and redundant entries.

### 3. Option Buying Logic (Pure Long Premium)
**Mandate:** Both CE and PE are handled as LONG premium positions.
- **Direction**: Entry is always a BUY. Target is always ABOVE entry premium. Stop Loss is always BELOW entry premium.
- **Math Fix**: Removed all legacy logic that treated PE as a short/subtracting premium trade.

### 4. Guaranteed Profitability (Charges Awareness)
**Mandate:** Target hits must result in a strictly positive Net PnL.
- **Implementation**: `TradePrepService` dynamically calculates a charges buffer (Brokerage + Taxes + Safety) and adds it to the mathematical target.
- **Effect**: Prevents "winning" trades from resulting in a negative wallet balance.

---

## 🛡️ Risk Management (Global Kill-Switch)

The system now features a global risk monitor inside `pnl_tracker.py`.

**Trigger Conditions:**
- ❌ **Max Daily Loss**: Triggered if unrealized/realized PnL drops below the threshold (e.g., -₹5000).
- ❌ **Consecutive Losses**: Monitored per session.

**Action:**
- Sets `shared_registry.is_risk_halted = True`.
- **AutoTradeLiveFeed** checks this flag before ANY entry. If halted, entries are blocked.
- Admin is alerted via Telegram/UI.

---

## 📊 Post-Trade Diagnostics

Every closed trade now stores mandatory metadata for investor-grade auditing:
- `realized_rr`: The actual risk-to-reward ratio achieved.
- `time_in_trade_min`: Exact duration of the position.
- `exit_reason`: STOP_LOSS_HIT, TARGET_HIT, TIME_BASED_EXIT, etc.
- `diagnostic_check`: "PASSED" or failure reason (e.g., data inconsistency).

---

## 🧪 Paper = Live Parity

**Mandate:** Identical logic paths for both modes.
- **Symmetry**: The only difference is execution (Simulated vs Upstox V3 API).
- **Slippage**: Paper trading now applies symmetric **0.05% slippage** on both ENTRY and EXIT to ensure conservative and realistic metrics.

---

## 📂 Responsibility Boundaries

| Component | Responsibility |
| :--- | :--- |
| **StrategyEngine** | Signal generation (Spot-based) |
| **AutoTradeLiveFeed** | Market data ingestion, Entry execution, UI price updates |
| **execution_handler** | Low-level Order execution (Broker API / Simulator) |
| **pnl_tracker** | **ALL** exit logic, Trailing SL, Time windows, Kill-Switch |
| **CapitalManager** | Fund validation and Position sizing |

---

**Status:** STABLE & INVESTOR-READY.
**Validation Batch:** 30–50 Paper Trades recommended.
