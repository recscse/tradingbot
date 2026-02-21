# 🚀 AI-Powered Trading Bot Platform

A comprehensive full-stack algorithmic trading platform with advanced AI strategies, real-time market data, and professional-grade automation workflows. Built for Indian stock markets with support for multiple brokers.

[![Netlify Status](https://api.netlify.com/api/v1/badges/c269af19-e741-48b2-84e2-236f5a75a251/deploy-status)](https://app.netlify.com/sites/resplendent-shortbread-e830d3/deploys)
[![Backend Deploy](https://img.shields.io/badge/Backend-Render-46E3B7.svg)](https://render.com)
[![Documentation](https://img.shields.io/badge/Docs-MkDocs-blue.svg)](https://tradingbot-ttys.onrender.com/documentation)
[![Version](https://img.shields.io/badge/version-v1.0.0-blue.svg)](https://github.com/growthquantix/tradingbot/releases)
[![Security](https://img.shields.io/badge/Security-Hardened-green.svg)](./SECURITY_FIXES.md)

## 📋 Table of Contents

- [🎯 Features](#-features)
- [🛠️ Tech Stack](#️-tech-stack)
- [⚡ Quick Start](#-quick-start)
- [🤖 Solo-Developer Workflow](#-solo-developer-workflow)
- [🔧 Configuration](#-configuration)
- [🚀 Deployment](#-deployment)
- [📊 Monitoring](#-monitoring)
- [📖 Documentation](#-documentation)
- [🤝 Contributing](#-contributing)

## 🎯 Features

### Core Trading Features
- **Multi-Broker Support**: Angel One, Dhan, Upstox, Zerodha, Fyers
- **Real-Time Market Data**: Live prices, indices, and market analytics
- **AI-Powered Strategies**: Fibonacci retracements, SuperTrend + EMA, sentiment analysis
- **Advanced Order Management**: Stop-loss, target orders, position sizing
- **Options Trading**: Comprehensive options strategies and ATM selection
- **Risk Management**: Portfolio tracking, P&L analysis, drawdown monitoring

### Platform Features
- **User Authentication**: Google OAuth, JWT tokens, role-based access
- **WebSocket Architecture**: Centralized high-speed admin feed for multiple users
- **Responsive UI**: Material-UI v6 with dark theme, mobile-optimized
- **System Health**: Parallelized real-time telemetry and operational integrity checks
- **Backtesting Engine**: Strategy validation with historical data

### Automation & DevOps
- **⚡ Zero-Downtime Deployment**: Automated rolling updates via Railway and Render
- **🧠 Automated Releases**: Push-to-Tag triggers for GitHub Releases & Changelogs
- **🔒 Security Scanning**: Automatic secret, dependency, and code analysis
- **📊 Performance Monitoring**: Integrated system resource tracking
- **📖 Auto-Built Docs**: MkDocs Material site automatically deployed to `/documentation`

## 🤖 Solo-Developer Workflow

This platform is optimized for a solo developer to manage high-stakes trading with zero manual maintenance.

### Daily Release Cycle
1.  **Develop**: Commit changes using prefixes like `feat:`, `fix:`, or `perf:`.
2.  **Tag**: At the end of the day, create a version tag:
    ```bash
    git tag v1.0.1
    ```
3.  **Push**: Push the tag to trigger the automated release and deployment:
    ```bash
    git push origin v1.0.1
    ```
4.  **Result**: Your bot is deployed, health checks run, and a formal GitHub Release with an auto-generated changelog is created.

## 🛠️ Tech Stack

### Backend
- **Framework**: Python 3.10+ with FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Real-Time**: WebSocket + Socket.IO for live data
- **Caching**: Redis with connection failure caching
- **AI/ML**: Technical indicators and sentiment analysis engine

### Frontend
- **Framework**: React 19 with TypeScript
- **UI Library**: Material-UI v6 + Tailwind CSS
- **Documentation**: MkDocs Material (hosted at `/documentation`)
- **Charts**: Recharts & Lightweight Charts

## ⚡ Quick Start

### 1. Access Application (Production)
- **Live App**: [https://tradingbot-ttys.onrender.com](https://tradingbot-ttys.onrender.com)
- **Full Documentation**: [https://tradingbot-ttys.onrender.com/documentation](https://tradingbot-ttys.onrender.com/documentation)
- **API Reference**: [/docs](https://tradingbot-ttys.onrender.com/docs) (Swagger)

### 2. Local Setup
```bash
# Clone repository
git clone https://github.com/growthquantix/tradingbot.git
cd tradingbot

# Install requirements
pip install -r requirements.txt

# Start backend
python app.py
```

## 🔧 Configuration

### Environment Variables
Configure these in your `.env` or cloud dashboard (Render/Railway):
- `DATABASE_URL`: Your PostgreSQL connection string
- `JWT_SECRET`: 32+ character random string
- `UPSTOX_API_KEY`: For broker connectivity
- `ENVIRONMENT`: Set to `production` for cloud deployment

## 🚀 Deployment

### Production Infrastructure
- **Backend**: Python FastAPI hosted on **Render**
- **Database**: PostgreSQL hosted on **Render** (Managed)
- **Frontend**: React SPA hosted on **Netlify**
- **Documentation**: Static MkDocs site hosted on **Netlify** under `/documentation`

## 📊 Monitoring

### System Health Dashboard
Access the **System Health** page in the UI to monitor:
- **Operational Integrity**: Real-time status of Token Refresh, Stock Selection, and Options Enhancement.
- **Resource Usage**: CPU, RAM, and Disk telemetry.
- **Latency**: Database, Redis, and API response times.

## 🔒 Security

### Hardened Architecture
- ✅ **Secret Protection**: Automatic secret scanning in CI/CD.
- ✅ **SQL Injection Prevention**: Using SQLAlchemy ORM.
- ✅ **Production Logging**: Console-only logging in production to prevent disk bloat.
- ✅ **Secure Auth**: JWT with refresh tokens and Google OAuth.

---

**Built with ❤️ for Indian Stock Market Traders**
*Empowering retail traders with institutional-grade technology*