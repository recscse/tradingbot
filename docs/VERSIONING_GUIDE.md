# 🏷️ Versioning & Release Guide

This guide explains how to maintain the version history, write standard commit messages, and create automated releases for the Trading Bot platform.

## 1. Semantic Versioning (SemVer)

We use the `vMAJOR.MINOR.PATCH` format:

*   **MAJOR** (`v1.0.0`): Breaking changes or a total system overhaul.
*   **MINOR** (`v1.1.0`): New features or strategies (e.g., adding a new indicator or broker).
*   **PATCH** (`v1.0.1`): Daily bug fixes, optimizations, or minor UI tweaks.

## 2. Conventional Commits

GitHub uses your commit prefixes to build the **Automated Changelog**. Use these prefixes:

| Prefix | Description | Example |
| :--- | :--- | :--- |
| `feat:` | A new feature | `feat: add RSI-based entry signal` |
| `fix:` | A bug fix | `fix: resolve lot size rounding issue` |
| `perf:` | Performance improvement | `perf: reduce WebSocket processing time` |
| `docs:` | Documentation changes | `docs: update setup instructions` |
| `refactor:` | Code cleanup (no new feature) | `refactor: optimize logging logic` |
| `chore:` | Maintenance tasks | `chore: update dependencies` |

## 3. Daily Release Workflow

Follow these 3 steps at the end of every day to publish your changes:

### Step 1: Push your code
Ensure all your daily changes are committed and pushed to the `main` branch.
```bash
git add .
git commit -m "feat: added new strategy and fixed UI"
git push origin main
```

### Step 2: Create a new Tag
Decide on the next version number (e.g., if current is `v1.0.0`, use `v1.0.1`).
```bash
git tag v1.0.1
```

### Step 3: Push the Tag
This triggers the GitHub Action to deploy and create the Release page.
```bash
git push origin v1.0.1
```

## 4. Automation Benefits

By following this process:
1.  **GitHub Releases**: A formal release page is created automatically with a summary of your changes.
2.  **GitBook Sync**: Your documentation sidebar will always show the latest version and historical changes.
3.  **Audit Trail**: You can easily roll back to a specific version if a new strategy performs poorly in live trading.
4.  **Stability**: The CI/CD pipeline runs health checks on every tag to ensure your production bot doesn't crash.
