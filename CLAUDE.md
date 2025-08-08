# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a full-stack algorithmic trading bot application with a Python FastAPI backend and React/Material-UI frontend. The system supports multiple Indian brokers (Angel One, Dhan, Upstox, Zerodha, Fyers), provides real-time market data, AI-powered trading strategies, and comprehensive portfolio management with advanced WebSocket-based real-time updates.

## Common Development Commands

### Backend (Python FastAPI)
- **Start development server**: `python app.py` (main entry point with lifespan events)
- **Alternative start**: `uvicorn app:sio_app --host 0.0.0.0 --port 8000` (for SocketIO support)
- **Install dependencies**: `pip install -r requirements.txt`
- **Database migrations**: `alembic upgrade head` (create new: `alembic revision --autogenerate -m "message"`)
- **Run tests**: `python -m pytest tests/`
- **Check service health**: Access `/health` endpoint for comprehensive system status

### Frontend (React)
- **Start development server**: `cd ui/trading-bot-ui && npm start`
- **Build for production**: `cd ui/trading-bot-ui && npm run build`
- **Install dependencies**: `cd ui/trading-bot-ui && npm install`
- **Run tests**: `cd ui/trading-bot-ui && npm test`
- **Environment**: Frontend connects to backend via `REACT_APP_API_URL` environment variable

## Architecture Overview

### Backend Structure
- **`app.py`**: Main FastAPI application with comprehensive lifespan management, centralized WebSocket system, SocketIO integration, and Redis fallback caching
- **`router/`**: API endpoints organized by feature (auth, broker, trading, market data, analytics, etc.)
- **`services/`**: Business logic layer including:
  - `unified_websocket_manager.py`: Event-driven WebSocket management for all real-time features
  - `centralized_ws_manager.py`: NEW centralized single admin WebSocket system
  - `enhanced_market_analytics.py`: Real-time market analytics and sentiment analysis
  - `instrument_registry.py`: Centralized instrument management and live price tracking
  - Broker integrations with standardized interfaces
- **`database/`**: SQLAlchemy models with repository pattern, comprehensive user/broker/trade management
- **`brokers/`**: Standardized broker implementations with WebSocket support (Angel One, Dhan, Upstox, Zerodha, Fyers)
- **`models/`**: AI/ML models for trading predictions, including Fibonacci strategies and LSTM price predictors
- **`core/`**: Configuration, JWT security, token refresh middleware, and WebSocket management

### Frontend Structure
- **`src/pages/`**: Main application pages (Dashboard, Trading, Backtesting, Profile, Landing)
- **`src/components/`**: Reusable UI components organized by feature:
  - `common/`: Layout, Header, Footer, LoadingSpinner, ResponsiveChart
  - `dashboard/`: Market indices, trading stats, connection status widgets
  - `trading/`: Live market data, trade controls, portfolio tracker
  - `profile/`: User management, broker configuration, performance metrics
  - `landing/`: Marketing pages with feature showcases and pricing
- **`src/services/`**: API clients (`api.js`), authentication, WebSocket services, broker integrations
- **`src/context/`**: React context providers (Theme, Notification, Market data)
- **`src/hooks/`**: Custom React hooks including `useUnifiedWebSocket`, `useMarketWebSocket`, `useUnifiedMarketData`

### Key Services Integration
- **Dual WebSocket Architecture**: 
  - `unified_websocket_manager.py`: Event-driven system for broadcasting market data to multiple clients
  - `centralized_ws_manager.py`: NEW single admin WebSocket connection with admin token strategy
- **Market Data Pipeline**: 
  1. Broker-specific WebSocket clients (Upstox, Angel One, Dhan, etc.) receive raw market data
  2. Centralized manager processes and standardizes data format
  3. Unified manager broadcasts to all connected frontend clients via SocketIO
  4. React components receive updates through custom hooks
- **Real-time Analytics**: `enhanced_market_analytics.py` provides live market sentiment, top movers, volume analysis
- **AI Trading Engine**: Multiple strategies in `services/stratigy/` including Fibonacci retracements and ML-based predictions
- **Caching Layer**: Redis with graceful fallback to in-memory cache for critical trading data
- **Database Layer**: Repository pattern with comprehensive models for users, brokers, trades, and performance tracking

### Broker Integration Architecture
Each broker has standardized interface in `brokers/base_broker.py`:
- Authentication and token management
- Order placement and management  
- Real-time market data subscription
- Historical data fetching
- Portfolio and position tracking

### Real-Time Data Flow
1. **Data Ingestion**: Broker-specific WebSocket clients connect using admin tokens for maximum instrument coverage
2. **Processing**: Centralized manager processes raw data, standardizes format, and manages instrument registry
3. **Event Broadcasting**: Unified manager emits typed events (price_update, analytics_update, sentiment_update)
4. **Client Updates**: Frontend components subscribe to specific event types via custom hooks
5. **Analytics Pipeline**: Real-time market analytics are computed and broadcast every 30-60 seconds
6. **Fallback Safety**: Redis caching with in-memory fallback ensures data availability during connection issues

## Environment Setup
- **Backend Environment Variables**:
  - `DATABASE_URL`: PostgreSQL or SQLite connection string
  - `JWT_SECRET_KEY`: For token authentication
  - `REDIS_ENABLED`: Set to "false" to disable Redis (defaults to in-memory caching)
  - `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`: Redis configuration (optional)
  - Broker API credentials: `UPSTOX_API_KEY`, `ANGEL_ONE_API_KEY`, etc.
- **Frontend Environment**: 
  - `REACT_APP_API_URL`: Backend API URL (e.g., http://localhost:8000)
- **Requirements**: Python 3.8+, Node.js 14+, PostgreSQL/SQLite
- **Optional**: Redis for enhanced caching (graceful fallback available)

## Testing Strategy
- Backend tests in `tests/` directory using pytest
- Frontend tests using React Testing Library (npm test)
- Backtesting framework in `services/backtesting/` for strategy validation
- Integration tests for broker API connections

## Key Configuration Files
- **`alembic.ini`**: Database migration configuration with environment variable support
- **`requirements.txt`**: Comprehensive Python dependencies including ML libraries (TensorFlow, scikit-learn), broker SDKs, and WebSocket libraries
- **`ui/trading-bot-ui/package.json`**: React dependencies with Material-UI v6, Socket.IO client, charting libraries
- **`config/sector_mapping.json`**: Stock sector classifications for market analytics
- **`netlify.toml`**: Frontend deployment configuration for Netlify hosting
- **`.env`**: Environment variables (not committed to repo)

## Development Notes
- **Async Architecture**: Extensive use of async/await for concurrent broker operations and WebSocket management
- **WebSocket Strategy**: Dual system approach - centralized admin connection for data ingestion, unified manager for client broadcasting
- **Error Resilience**: Comprehensive error handling with Redis fallback caching and graceful degradation
- **Security**: All broker credentials stored as environment variables, JWT-based authentication with refresh tokens
- **UI Framework**: Material-UI v6 with custom dark theme, responsive design for mobile/desktop
- **Real-time Critical**: Always test WebSocket connections when making changes - the system is heavily dependent on live data
- **Performance**: Connection pooling, event-driven architecture, and optimized data structures for handling thousands of instruments
- **AI/ML Integration**: Models are retrained periodically, with separate services for different trading strategies

## Database Schema
- **User Management**: Comprehensive user model with Google OAuth support, role-based access (Admin/Trader/Analyst)
- **Broker Integration**: Per-user broker configurations with encrypted credentials and token management
- **Trading System**: Trade history, performance tracking, order management with status tracking
- **Market Data**: Instrument registry, live price caching, sector mappings
- **Analytics**: Trade performance metrics, notification system, OTP management
- **Migrations**: Alembic-managed schema versioning with automatic upgrades

## Important System Endpoints
- **Health Check**: `/health` - Comprehensive system status including WebSocket health, Redis status, and service availability
- **Market Analytics**: `/api/analytics/*` - Real-time market data, sentiment analysis, top movers
- **WebSocket Endpoints**: `/ws/unified`, `/api/v1/ws/dashboard`, `/api/v1/ws/trading` for real-time updates
- **Admin Endpoints**: `/api/v1/system/*` - System management and centralized WebSocket control

## Deployment
- **Backend**: Python/FastAPI with SocketIO support, requires environment variables for broker APIs
- **Frontend**: React SPA deployed via Netlify with automatic builds from repository
- **Database**: Alembic migrations must be run on deployment (`alembic upgrade head`)
- **Monitoring**: Comprehensive health endpoints and logging for production monitoring