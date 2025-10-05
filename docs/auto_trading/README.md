# Auto-Trading System Documentation

Complete documentation for the fully automated trading system. Documentation is organized into modular sections for easy navigation.

---

## 📚 Documentation Structure

### 🎓 Guides (Start Here)
User-focused guides for understanding and using the auto-trading system.

- **[Complete Trading System Guide](guides/COMPLETE_TRADING_SYSTEM_GUIDE.md)**
  Complete end-to-end guide covering all aspects of the auto-trading system

- **[Fully Automatic Trading Guide](guides/FULLY_AUTOMATIC_TRADING_FINAL.md)**
  User guide explaining the fully automatic trading workflow and UI controls

- **[Auto-Start/Stop Guide](guides/AUTO_START_STOP_GUIDE.md)**
  How the scheduler automatically starts and stops trading at market hours

- **[Auto-Trading Live Feed Guide](guides/AUTO_TRADING_LIVE_FEED_GUIDE.md)**
  Understanding the WebSocket live feed and data processing

---

### 🏗️ Architecture
Technical architecture and data flow documentation.

- **[Auto-Trading Complete Flow](architecture/AUTO_TRADING_COMPLETE_FLOW.md)**
  Complete phase-by-phase flow from stock selection to trade exit

- **[Data Flow to Strategy](architecture/DATA_FLOW_TO_STRATEGY.md)**
  Detailed data flow from WebSocket to strategy execution with code references

- **[Trade Execution Flow](architecture/TRADE_EXECUTION_FLOW.md)**
  Trade preparation and execution architecture

- **[Trading Execution Architecture](architecture/TRADING_EXECUTION_ARCHITECTURE.md)**
  Overall system architecture and component interactions

---

### 🔧 Implementation
Implementation details and technical specifications.

- **[Multi-Demat Capital Implementation](implementation/MULTI_DEMAT_CAPITAL_IMPLEMENTATION.md)**
  Capital management across multiple broker accounts

---

### 📖 Reference
Technical reference and explanations.

- **[Auto-Start/Stop Summary](reference/AUTO_START_STOP_SUMMARY.md)**
  Quick reference for auto-start/stop functionality

- **[Why OHLC Not LTP](reference/WHY_OHLC_NOT_LTP.md)**
  Technical explanation of why we use OHLC data instead of just LTP for strategies

---

## 🚀 Quick Start

### For Users:
1. Read [Fully Automatic Trading Guide](guides/FULLY_AUTOMATIC_TRADING_FINAL.md)
2. Understand [Auto-Start/Stop Guide](guides/AUTO_START_STOP_GUIDE.md)
3. Review [Complete Trading System Guide](guides/COMPLETE_TRADING_SYSTEM_GUIDE.md)

### For Developers:
1. Understand [Auto-Trading Complete Flow](architecture/AUTO_TRADING_COMPLETE_FLOW.md)
2. Study [Data Flow to Strategy](architecture/DATA_FLOW_TO_STRATEGY.md)
3. Review [Trading Execution Architecture](architecture/TRADING_EXECUTION_ARCHITECTURE.md)
4. Implement following [Multi-Demat Capital Implementation](implementation/MULTI_DEMAT_CAPITAL_IMPLEMENTATION.md)

---

## 📝 Key Concepts

### Auto-Trading Flow
```
Stock Selection (9:00 AM)
  ↓
Scheduler Detects Selection (9:15 AM)
  ↓
WebSocket Auto-Starts
  ↓
Live Data Processing (SPOT + OPTION)
  ↓
Strategy Runs on Live Data
  ↓
Auto-Executes on Valid Signals
  ↓
Position Management with Trailing SL
  ↓
Auto-Exits on SL/Target/Time
  ↓
WebSocket Auto-Stops When All Closed
```

### Key Components
- **Scheduler**: `services/trading_execution/auto_trade_scheduler.py`
- **Live Feed**: `services/trading_execution/auto_trade_live_feed.py`
- **Strategy Engine**: `services/trading_execution/strategy_engine.py`
- **Trade Prep**: `services/trading_execution/trade_prep_service.py`
- **Execution**: `services/trading_execution/execution_handler.py`
- **Capital Manager**: `services/trading_execution/multi_demat_capital_service.py`

### Trading Modes
- **Paper Trading**: Virtual ₹10 lakhs, no real money, safe for testing
- **Live Trading**: Real broker API, actual money at risk

### Execution Modes
- **Single-Demat**: Execute on one broker account
- **Multi-Demat**: Distribute across all active broker accounts

---

## 🔗 Related Documentation

### System-Wide Documentation
- **[Main README](../../README.md)**: Project overview
- **[CLAUDE.md](../../CLAUDE.md)**: Coding standards and project structure

### Other Trading Documentation
- **Market Data**: WebSocket integration and live feed
- **Broker Integration**: Multi-broker support
- **Stock Selection**: Intelligent stock selection service
- **Options Enhancement**: Option chain analysis and selection

---

## 📊 System Status

### Current Implementation Status
- ✅ **Stock Selection**: Automated with option contract assignment
- ✅ **Auto-Start**: Scheduler-based at 9:15 AM
- ✅ **WebSocket**: Dedicated connection for selected stocks
- ✅ **Live Data**: SPOT for strategy, OPTION for trading/PnL
- ✅ **Strategy**: SuperTrend + EMA with signal validation
- ✅ **Auto-Execute**: Signal-based automatic execution
- ✅ **Position Management**: Trailing SL, live PnL tracking
- ✅ **Auto-Exit**: Multiple exit conditions
- ✅ **Auto-Stop**: When all positions closed
- ✅ **Paper Trading**: Full simulation with ₹10 lakhs
- ✅ **Live Trading**: Real broker API integration
- ✅ **Multi-Demat**: Capital distribution across accounts

---

## System Requirements

- **Python**: 3.8+
- **PostgreSQL**: 12+ (primary database)
- **Redis**: Optional (for enhanced caching, falls back to in-memory)
- **WebSocket**: Broker WebSocket support (Upstox, Angel One, Dhan, Zerodha, Fyers)
- **Memory**: 2GB+ (4GB recommended)
- **CPU**: 4 cores (8 cores recommended)

---

## 🛠️ Maintenance

### Updating Documentation
When making changes to the auto-trading system:

1. Update relevant architecture docs in `/architecture`
2. Update user guides in `/guides` if UI/UX changes
3. Update implementation docs in `/implementation` for technical changes
4. Add new reference docs in `/reference` for new concepts
5. Update this README if new sections are added

### Documentation Standards
- Use markdown format
- Include code examples with file references
- Add diagrams for complex flows
- Keep user guides simple and developer docs technical
- Update date stamps when making changes

---

**Last Updated**: 2025-10-05
**System Version**: 1.0
**Architecture**: WebSocket-based Real-time Trading System
**Status**: Production-Ready with Paper & Live Trading