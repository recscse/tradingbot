# 🚀 AI-Powered Trading Bot Platform

A comprehensive full-stack algorithmic trading platform with advanced AI strategies, real-time market data, and professional-grade automation workflows. Built for Indian stock markets with support for multiple brokers.

[![Netlify Status](https://api.netlify.com/api/v1/badges/c269af19-e741-48b2-84e2-236f5a75a251/deploy-status)](https://app.netlify.com/sites/resplendent-shortbread-e830d3/deploys)
[![Backend Deploy](https://img.shields.io/badge/Backend-Render-46E3B7.svg)](https://render.com)
[![Security](https://img.shields.io/badge/Security-Hardened-green.svg)](./SECURITY_FIXES.md)

## 📋 Table of Contents

- [🎯 Features](#-features)
- [🛠️ Tech Stack](#️-tech-stack)
- [⚡ Quick Start](#-quick-start)
- [📦 Installation](#-installation)
- [🔧 Configuration](#-configuration)
- [🚀 Deployment](#-deployment)
- [🤖 CI/CD & Automation](#-cicd--automation)
- [📊 Monitoring](#-monitoring)
- [🔒 Security](#-security)
- [📚 Documentation](#-documentation)
- [🤝 Contributing](#-contributing)

## 🎯 Features

### Core Trading Features
- **Multi-Broker Support**: Angel One, Dhan, Upstox, Zerodha, Fyers
- **Real-Time Market Data**: Live prices, indices, and market analytics
- **AI-Powered Strategies**: Fibonacci retracements, LSTM predictions, sentiment analysis
- **Advanced Order Management**: Stop-loss, target orders, position sizing
- **Options Trading**: Comprehensive options strategies and analytics
- **Risk Management**: Portfolio tracking, P&L analysis, drawdown monitoring

### Platform Features
- **User Authentication**: Google OAuth, JWT tokens, role-based access
- **WebSocket Architecture**: Dual real-time system for optimal performance
- **Responsive UI**: Material-UI v6 with dark theme, mobile-optimized
- **Real-Time Analytics**: Market sentiment, top movers, volume analysis
- **Backtesting Engine**: Strategy validation with historical data
- **Admin Dashboard**: System monitoring, user management, trading controls

### Automation & DevOps
- **🤖 Automated PR Creation**: Creates PRs when pushing to feature branches
- **⚡ Auto-Merge System**: Merges PRs automatically when conditions are met
- **🧠 Claude Code Agent Integration**: AI-powered code review and analysis
- **🔒 Security Scanning**: CodeQL, dependency checks, vulnerability monitoring
- **📊 Performance Monitoring**: Prometheus + Grafana stack
- **☁️ Cloud Deployment**: Render (backend) + Netlify (frontend)

## 🛠️ Tech Stack

### Backend
- **Framework**: Python 3.10+ with FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Real-Time**: WebSocket + Socket.IO for live data
- **Caching**: Redis with graceful fallback
- **AI/ML**: TensorFlow, scikit-learn for trading algorithms
- **APIs**: RESTful APIs with comprehensive documentation

### Frontend
- **Framework**: React 18 with TypeScript
- **UI Library**: Material-UI v6 with custom theming
- **State Management**: React Context + Custom hooks
- **Charts**: Recharts for trading visualizations
- **Real-Time**: Socket.IO client for live updates

### DevOps & Infrastructure
- **CI/CD**: GitHub Actions with automated workflows
- **Monitoring**: Prometheus + Grafana + AlertManager
- **Security**: CodeQL, Bandit, Safety scanning
- **Deployment**: Docker, Render, Netlify
- **Documentation**: Auto-generated API docs

## ⚡ Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 13+
- Git

### 1. Clone & Setup Environment
```bash
git clone https://github.com/growthquantix/tradingbot.git
cd tradingbot

# Copy environment template and configure
cp .env.template .env
# Edit .env with your API credentials
```

### 2. Backend Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start backend server
python app.py
```

### 3. Frontend Setup
```bash
cd ui/trading-bot-ui
npm install
npm start
```

### 4. Access Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 📦 Installation

### Development Environment
```bash
# 1. Clone repository
git clone https://github.com/growthquantix/tradingbot.git
cd tradingbot

# 2. Setup Python environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Setup database
createdb tradingapp  # PostgreSQL
alembic upgrade head

# 4. Setup frontend
cd ui/trading-bot-ui
npm install

# 5. Start development servers
# Terminal 1 (Backend)
python app.py

# Terminal 2 (Frontend)
cd ui/trading-bot-ui && npm start
```

### Docker Deployment (Optional)
```bash
# Start monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d

# Access Grafana at http://localhost:3001
```

## 🔧 Configuration

### Environment Variables

#### Required Configuration
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/tradingapp

# JWT Security (Generate strong random values)
JWT_SECRET=your-strong-32-character-secret-key
REFRESH_SECRET=your-strong-refresh-secret-key

# Broker API Credentials
UPSTOX_API_KEY=your_upstox_api_key
UPSTOX_API_SECRET=your_upstox_api_secret
ZERODHA_API_KEY=your_zerodha_api_key
ZERODHA_API_SECRET=your_zerodha_api_secret
```

#### Optional Configuration
```bash
# Redis (optional - graceful fallback available)
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379

# Monitoring
GRAFANA_PASSWORD=secure_password
PROMETHEUS_ENABLED=true
```

See [`.env.template`](.env.template) for complete configuration options.

### Broker Setup
1. **Register** with supported brokers (Upstox, Zerodha, etc.)
2. **Generate API credentials** from broker developer portals
3. **Configure** in `.env` file
4. **Test connection** via admin dashboard

## 🚀 Deployment

### Production Deployment

#### Backend (Render)
1. Connect GitHub repository to Render
2. Set environment variables in Render dashboard
3. Deploy automatically on main branch push

#### Frontend (Netlify)
1. Connect GitHub repository to Netlify
2. Set build command: `cd ui/trading-bot-ui && npm run build`
3. Set publish directory: `ui/trading-bot-ui/build`
4. Deploy automatically on main branch push

#### Database
- Use managed PostgreSQL (Render, AWS RDS, etc.)
- Run migrations: `alembic upgrade head`
- Ensure proper security groups and access controls

## 🤖 CI/CD & Automation

### Automated Workflows

#### Pull Request Automation
- **Auto PR Creation**: Creates PRs when pushing to feature branches
- **Auto Merge**: Merges when all conditions are met
- **Smart Labeling**: Automatic labels based on file changes
- **Reviewer Assignment**: Auto-assigns based on code changes

#### Claude Code Agent Integration 🧠
- **Intelligent Code Review**: AI-powered analysis of every PR
- **Trading-Specific Validation**: Extra scrutiny for trading system changes
- **Security Analysis**: Automated detection of security-sensitive changes
- **Bug Investigation**: AI-assisted bug analysis and resolution guidance
- **Performance Optimization**: Automated suggestions for code improvements

#### Quality Gates
- **Security Scanning**: CodeQL, Bandit, Safety checks
- **Code Quality**: Linting, formatting, complexity analysis
- **Testing**: Unit tests, integration tests, coverage reports
- **Performance**: Load testing, dependency analysis

#### Branch Management
- **Naming Validation**: Enforces branch naming conventions
- **Stale Cleanup**: Automatic cleanup of old branches
- **Protection Rules**: Prevents direct commits to main

### Workflow Commands
```bash
# Skip auto PR creation
git commit -m "feat: new feature [skip-pr]"

# Prevent auto-merge (add label to PR)
gh pr create --label "no-auto-merge"
```

See [PR_AUTOMATION_GUIDE.md](PR_AUTOMATION_GUIDE.md) for detailed automation documentation.

## 📊 Monitoring

### Production Monitoring Stack
- **Metrics**: Prometheus for time-series data
- **Visualization**: Grafana dashboards
- **Alerting**: AlertManager for notifications
- **Logs**: Structured JSON logging with audit trails
- **Health Checks**: Comprehensive system monitoring

### Key Metrics Monitored
- Trading performance and P&L
- WebSocket connection health
- Database query performance
- API response times
- Broker connection status
- User activity and errors

### Access Monitoring
```bash
# Start monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d

# Access dashboards
# Grafana: http://localhost:3001
# Prometheus: http://localhost:9090
```

## 🔒 Security

### Security Features Implemented
- ✅ **Credential Management**: All secrets in environment variables
- ✅ **JWT Authentication**: Secure token-based auth with refresh
- ✅ **Rate Limiting**: API protection against abuse
- ✅ **Input Validation**: Comprehensive request validation
- ✅ **SQL Injection Protection**: Parameterized queries
- ✅ **HTTPS Enforcement**: Secure transport layer
- ✅ **CORS Configuration**: Proper origin restrictions

### Security Scanning
- **CodeQL**: Automated code analysis
- **Dependency Scanning**: Vulnerability detection
- **Secret Scanning**: Prevents credential leaks
- **SEBI Compliance**: Indian market regulation adherence

### Security Best Practices
1. Use strong, unique JWT secrets (32+ characters)
2. Rotate API keys regularly
3. Never commit credentials to version control
4. Use HTTPS in production
5. Monitor for suspicious activities

See [SECURITY_FIXES.md](SECURITY_FIXES.md) for detailed security documentation.

## 📚 Documentation

### Available Documentation
- **[CLAUDE.md](CLAUDE.md)**: Comprehensive development guide
- **[PR_AUTOMATION_GUIDE.md](PR_AUTOMATION_GUIDE.md)**: Automation workflows
- **[CLAUDE_CODE_INTEGRATION.md](.github/CLAUDE_CODE_INTEGRATION.md)**: AI-powered development assistance
- **[SECURITY_FIXES.md](SECURITY_FIXES.md)**: Security guidelines
- **API Docs**: Available at `/docs` endpoint
- **OpenAPI Spec**: Available at `/openapi.json`

### Architecture Overview
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React SPA     │    │  FastAPI Backend│    │   PostgreSQL    │
│  (Netlify)      │◄──►│    (Render)     │◄──►│   Database      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   WebSocket     │    │   Redis Cache   │    │   Monitoring    │
│   Real-time     │    │   (Optional)    │    │   Stack         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🤝 Contributing

### Development Workflow
1. **Fork** the repository
2. **Create** feature branch: `git checkout -b feature/amazing-feature`
3. **Commit** changes: `git commit -m 'feat: add amazing feature'`
4. **Push** to branch: `git push origin feature/amazing-feature`
5. **Open** Pull Request (auto-created by workflow)

### Automated Contribution Process
- 🤖 **Auto PR Creation**: PRs created automatically on feature branch push
- 🔍 **Automated Review**: Code quality, security, and style checks
- ✅ **Auto Merge**: PRs merged when all conditions are met
- 🧹 **Branch Cleanup**: Automatic cleanup after merge

### Code Standards
- **Python**: Black formatting, PEP 8 compliance
- **JavaScript**: ESLint, Prettier formatting
- **Commits**: Conventional commit format
- **Testing**: Minimum 30% coverage requirement

### Getting Help
- 📖 Check [CLAUDE.md](CLAUDE.md) for development guidelines
- 🐛 Report bugs via GitHub Issues
- 💡 Feature requests welcome
- 📧 Contact: admin@growthquantix.com

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🌟 Acknowledgments

- **Indian Stock Exchanges**: NSE, BSE for market data
- **Broker Partners**: Upstox, Zerodha, Angel One, Dhan, Fyers
- **Technology Stack**: FastAPI, React, Material-UI teams
- **Open Source Community**: For excellent libraries and tools

---

**Built with ❤️ for Indian Stock Market Traders**

*Empowering retail traders with institutional-grade technology*