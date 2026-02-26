# ðŸ“ Changelog

All notable changes to this project will be documented in this file.

## [2.0.1] - 2026-02-25
### Added
- **AI-Powered Development Agents:**
  - Automated Issue Triager for bug analysis using Gemini.
  - Automated PR Reviewer for code quality, complexity (radon), and risk checks.
  - Automated Backtesting for strategy performance validation in pull requests.
  - AI Documentation Agent for automated semantic changelogs.
  - Trading Risk Guard for detecting dangerous code patterns (hardcoded secrets, unlocalized time).
- **Fund Ledger System:**
  - Database-backed fund ledger tracking all deposits and withdrawals.
  - Integration with `CapitalManager` for accurate balance management across brokers.
  - New UI components: `AddFundsModal`, `FundStatementTable`, and `FundsTab` in profile.
- **AI Support & Telegram Integration:**
  - `AISupportService` for context-aware support answering queries using project docs and trade history.
  - Telegram bot for remote support and account status tracking.

### Changed
- Refactored `execution_handler.py` and `pnl_tracker.py` to utilize the new `FundManager` for balance synchronization.
- Enhanced `AutoTradingPage` for better performance and list virtualization.
- Updated `requirements.txt` with `google-generativeai` and `PyGithub`.

### Fixed
- Improved timezone handling for IST consistency across services.
- Corrected paper trading P&L logic for accurate balance updates.
- Refined stock selection direction logic for neutral market conditions.
