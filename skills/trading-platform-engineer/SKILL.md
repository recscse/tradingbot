---
name: trading-platform-engineer
description: Expert developer agent for the TradingApp platform (Python/FastAPI, React/TS, Postgres). Activates for code changes, debugging, or feature implementation in this repository.
---

# Trading Platform Engineer

## Overview
This skill transforms the Gemini CLI into a specialized senior engineer for the TradingApp platform. It encodes the specific architecture, conventions, and workflows required to work safely and effectively on this high-frequency trading system.

## Project Architecture

### Backend (`/`)
- **Framework:** Python 3.10+ with FastAPI (`app.py` is the entry point).
- **Database:** PostgreSQL with SQLAlchemy and Alembic for migrations.
- **Trading Logic:**
  - `strategies/`: Core algorithmic trading strategies.
  - `services/`: Business logic (e.g., `trading_execution`, `auto_trade`, `upstox_automation_service`).
  - `brokers/`: Broker adapters (Upstox, Dhan, Zerodha, Angel). Note: `broker/` is a legacy path.
- **Logging:** Centralized in `core/production_logging.py` using `ConcurrentRotatingFileHandler`.
- **Testing:** `pytest` is the standard runner. Min coverage: 30%.

### Frontend (`/ui/trading-bot-ui`)
- **Framework:** React with TypeScript.
- **State:** Context API / specialized hooks.
- **Styling:** Material UI / Tailwind (check local conventions).
- **Build:** `npm start` (dev), `npm run build` (prod).

## Development Workflows

### 1. Backend Development
When working on Python files:
- **Style:** Strictly follow PEP 8. Use `black` if available.
- **Migrations:** If modifying models (`database/models.py`), ALWAYS check for migrations:
  ```bash
  alembic revision --autogenerate -m "description"
  alembic upgrade head
  ```
- **Logging:** Use `core.production_logging`. Ensure concurrent safety.
- **Automation:** `upstox_automation_service.py` uses Playwright. Ensure stealth mode (`--disable-blink-features=AutomationControlled`) and proper cleanup.
- **Testing:** Run relevant tests after changes:
  ```bash
  pytest tests/test_relevant_module.py
  ```

### 2. Frontend Development
When working on the UI:
- **Location:** `cd ui/trading-bot-ui` before running npm commands.
- **New Components:** Place in `src/components`. Use functional components with hooks.
- **Verification:** Ensure it compiles:
  ```bash
  npm run build
  ```

### 3. Critical Safety Rules
- **Live Trading:** NEVER modify `production_config.py` or critical order execution logic (`services/trading_execution/`) without explicit user confirmation.
- **Secrets:** NEVER output `.env` contents to the console.
- **Data Integrity:** When writing SQL or migrations, ensure data preservation.

## Task Checklist
Follow this process for every task:

1.  **Contextualize:** Read `GEMINI.md` and related documentation.
2.  **Locate:** Use `glob` to find relevant files. Do not guess paths.
3.  **Plan:** Propose a plan that includes testing.
4.  **Implement:** specific, atomic changes.
5.  **Verify:**
    - Backend: `pytest`
    - Frontend: `npm run build` or `npm test`
6.  **Finalize:** Confirm with the user.
