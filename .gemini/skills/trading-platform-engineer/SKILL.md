---
name: trading-platform-engineer
description: Expert developer agent for the TradingApp platform (Python/FastAPI, React/TS, Postgres). Activates for code changes, debugging, or feature implementation in this repository.
---

# Trading Platform Engineer

## Overview
This skill transforms the Gemini CLI into a specialized senior engineer for the TradingApp platform. It encodes the specific architecture, conventions, and workflows required to work safely and effectively on this high-frequency trading (HFT) system focused on the Indian stock market.

## Project Architecture

### Backend (`/`)
- **Framework:** Python 3.10+ with FastAPI (`app.py` is the entry point).
- **Timezone:** STRICTLY use `Asia/Kolkata` (IST). Use `utils/timezone_utils.py` for all time operations.
- **Database:** PostgreSQL with SQLAlchemy and Alembic.
- **Instrument Management:**
  - `services/trading_execution/shared_instrument_registry.py`: Central hub for market data monitoring across all users.
  - `services/instrument_registry.py`: (Legacy/Commented) - Reference `shared_instrument_registry.py` instead.
- **Trading Execution:**
  - `services/trading_execution/trade_prep.py`: Validates and prepares trades.
  - `services/trading_execution/execution_handler.py`: Orchestrates trade execution.
  - `services/upstox/upstox_order_service.py`: Implements Upstox V3 API, including auto-slicing and Emergency Exit.
- **Paper Trading:** Simulated environment with a default balance of **1,00,000 INR**.
- **Logging:** Centralized in `core/production_logging.py`. Use `log_to_db` for persistent trade logs.
- **Notifications:** Implements deduplication (5s for WebSockets, 5m for Database).

### Frontend (`/ui/trading-bot-ui`)
- **Framework:** React with TypeScript.
- **UI Components:** Optimized for mobile-first premium UX using Material UI and Tailwind CSS.
- **Animations:** Framer Motion for smooth transitions (e.g., `StocksList.js`).
- **Performance:** Use `useMemo` for derived data and componentize complex lists (e.g., `ActivePositionCard`, `SelectedStockCard`).

## Development Workflows

### 1. Backend Development
- **Time Handling:** NEVER use naive `datetime.now()`. ALWAYS use `get_ist_now()` or `get_ist_now_naive()` from `utils.timezone_utils`.
- **Order APIs:** Use Upstox V3 endpoints. Note the distinction between `place_order_v3` and `place_multi_order`.
- **Automation:** `upstox_automation_service.py` (Playwright) must use "Stealth Mode":
  - Mask `navigator.webdriver`.
  - Use realistic User Agents.
  - Handle Cloudflare/CAPTCHA by logging page title/URL on failure.
- **Testing:** `pytest` is the standard runner. Target specific modules: `pytest tests/test_relevant_module.py`.

### 2. Frontend Development
- **Location:** `cd ui/trading-bot-ui`.
- **Styling:** Follow the established dark-theme premium aesthetic using MUI Rounded Icons.
- **Data Fetching:** Ensure hooks handle loading/error states and use the correct IST formatting for display.

### 3. Critical Safety Rules
- **Live Trading Safety:** NEVER modify critical order execution logic without verification.
- **Emergency Exit:** Be aware of the `/emergency-exit-all` endpoint for rapid position closure.
- **PnL Integrity:** Ensure PnL calculations do not double-count lot sizes (Quantity already represents total units).
- **Secrets:** NEVER expose `.env` or sensitive broker tokens.

## Task Checklist
1.  **Contextualize:** Review `GEMINI.md` and `TIMEZONE_FIX_SUMMARY.md`.
2.  **Verify Timezone:** Ensure any time-based logic uses IST utilities.
3.  **Instrument Resolution:** Use `InstrumentRegistry` or `SharedInstrumentRegistry` for key resolution.
4.  **Test Paper Mode:** Always verify logic in Paper Trading mode before considering Live implications.
5.  **Verify Build:** Run `npm run build` for frontend changes to ensure TS/Lint compliance.
