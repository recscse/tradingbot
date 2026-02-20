# Auto-Trading System Documentation (Stabilized Feb 2026)

Complete documentation for the deterministic algorithmic trading system. This system is optimized for high-frequency data ingestion and surgical execution with strict risk boundaries.

---

## 🏛️ Core Architecture

The system follows a **Single Exit Authority** model to eliminate race conditions and ensure investor-grade diagnostics.

### 🔌 Component Responsibilities

| Component | Responsibility | Decision Type |
| :--- | :--- | :--- |
| **AutoTradeLiveFeed** | Market Data ingestion, Entry Execution, UI Updates | **Reactive (Ticks)** |
| **StrategyEngine** | Signal Generation (Spot Trend detection) | **Deterministic (Candles)** |
| **TradePrepService** | Capital Validation & Charge-Aware Target calculation | **Validation** |
| **PnL Tracker** | **ALL EXITS** (SL, Target, Time), Risk Monitoring | **Authoritative** |
| **CapitalManager** | Fund Integrity & Position Sizing | **Resource Control** |

---

## 📚 Documentation Structure

### 🎓 Guides (Start Here)
- **[Stabilization Report](STABILIZATION_REPORT.md)** - **Mandatory Reading** for understanding the core mandates.
- **[Fully Automatic Trading Guide](guides/FULLY_AUTOMATIC_TRADING_FINAL.md)**
  User guide explaining the fully automatic trading workflow and UI controls.

---

### 🏗️ Architecture
Technical architecture and data flow documentation.

- **[Trading Execution Architecture](architecture/TRADING_EXECUTION_ARCHITECTURE.md)**
  Stabilized system architecture and component interactions.
- **[Auto-Trading Complete Flow](architecture/AUTO_TRADING_COMPLETE_FLOW.md)**
  Complete phase-by-phase flow from stock selection to trade exit.

---

## 🚀 Key Stabilized Features

### ⏱️ Deterministic Execution
- **Candle-Gating**: Strategy triggers exactly once per completed candle via `last_processed_candle_count`.
- **Restart Safety**: Zero-burst logic prevents duplicate trades upon service restart by initializing history counters.

### 🛡️ Risk Management
- **Single Exit Authority**: Exits are managed purely in `pnl_tracker.py` to prevent race conditions.
- **Global Kill-Switch**: Automatic halt on daily loss threshold or excessive SL hits.
- **Charges-Aware Targets**: Every target hit is mathematically guaranteed to be net profitable after brokerage and taxes.

### 📊 Investor-Grade Diagnostics
Every trade metadata includes:
- Realized Risk/Reward (RR)
- Exact time-in-trade duration
- Slip-adjusted exit reason
- Diagnostic health check status

---

## 📊 System Status (Feb 2026)

### Current Implementation Status
- ✅ **Deterministic Gating**: Enforced via candle count tracking.
- ✅ **Single Exit Authority**: Centralized in `pnl_tracker.py`.
- ✅ **PE Logic Fix**: Standardized as Long Premium (Buy Puts).
- ✅ **Startup Safety**: burst protection active.
- ✅ **Charges Buffer**: Dynamic buffer added to Target prices.
- ✅ **Paper/Live Parity**: Identical risk paths with symmetric slippage.

---

**Last Updated**: 2026-02-19
**System Version**: 2.0 (Stabilized)
**Architecture**: Deterministic WebSocket-based Execution
**Status**: Ready for Paper Validation (Batch 30-50)