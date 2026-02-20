# Auto-Trading Live Feed Guide (Stabilized Feb 2026)

## Overview
The `AutoTradeLiveFeed` is the high-speed data ingestion and entry execution engine. It is designed for deterministic, low-latency performance using a centralized WebSocket architecture.

---

## 🏛️ Responsibility: ENTRY-ONLY
As of the February 2026 stabilization, the Live Feed is strictly an **Entry-Only** component.
- **Entry Responsibility**: High-speed market data ingestion and trade entry execution.
- **UI Responsibility**: Broadcasting real-time price and PnL updates to the dashboard for active positions.
- **Exit Authority**: **NONE**. All exit decisions (SL, Target, Trailing, Time) are handled EXCLUSIVELY by the PnL Tracker (`pnl_tracker.py`).

---

## ⏱️ Deterministic Execution (Candle-Gating)
To prevent over-trading and multiple entries per candle, the feed utilizes a candle-gating mechanism.

### How it works:
1. The feed receives real-time ticks from the broker WebSocket.
2. It updates the `SharedInstrumentRegistry` with the latest LTP.
3. The strategy engine is triggered **ONLY** when a new completed candle is detected via `last_processed_candle_count`.
4. **Restart Safety**: On system startup, the feed initializes the candle count to the current history length, preventing "startup bursts" from historical data.

---

## 📡 Data Flow

### 1. Ingestion
- **Centralized Connection**: A single WebSocket connection handles all instruments for all users.
- **Shared Memory**: Data is stored in the `SharedInstrumentRegistry` to ensure a single source of truth.

### 2. Signal Processing
- When a new candle completes, `StrategyEngine` generates a Spot-based signal.
- The signal is converted to Option Premium targets/SLs with a dynamic charges buffer.

### 3. Entry Execution
- The feed checks the global `is_risk_halted` flag (managed by PnL Tracker).
- Approved signals are passed to the `execution_handler` for low-level order placement.

---

## 📊 Broadcast Events
The live feed pushes the following events to the UI:
- `selected_stock_price_update`: Live LTP and instrument status.
- `trading_signal`: Real-time signal alerts.
- `pnl_update`: UI-only mark-to-market calculations for active positions.

---

## 🛠️ Debugging
- **Logs**: Monitor the `auto_trade_live_feed` channel for ingestion and entry logs.
- **Heartbeat**: "💓 Live Data Heartbeat" confirms the monitoring loop is active.
- **Initialization**: Verify `Initialized candle count for [SYMBOL]` appears on startup.