# CLAUDE.md

**MANDATORY**: This file contains STRICT coding standards that MUST be followed for ALL code written in this repository.

**CRITICAL INSTRUCTION**: Before writing ANY code, read and follow the "Coding Standards and Best Practices" section below. These are NON-NEGOTIABLE requirements.

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
  - **Token Automation Requirements**:
    - `UPSTOX_MOBILE`: Mobile number for automation login
    - `UPSTOX_PIN`: 6-digit PIN for Upstox account
    - `UPSTOX_TOTP_KEY`: TOTP secret key for 2FA authentication
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
- **Token Automation**: Playwright browser installed automatically via `start.sh` for token refresh automation
- **Monitoring**: Comprehensive health endpoints and logging for production monitoring
## Coding Standards and Best Practices

**MANDATORY REQUIREMENTS**: All code written for this project MUST follow these standards:

### Clean Code Principles (MANDATORY)
1. **Single Responsibility Principle**: Each function/class has ONE clear purpose
2. **DRY (Don't Repeat Yourself)**: Avoid code duplication
3. **KISS (Keep It Simple, Stupid)**: Prefer simple, readable solutions
4. **YAGNI (You Aren't Gonna Need It)**: Don't over-engineer
5. **Separation of Concerns**: Business logic, data access, and presentation are separate

### Naming Conventions (MANDATORY)

#### Python Backend:
- **Functions**: `snake_case` - `calculate_portfolio_value()`, `get_user_trades()`
- **Variables**: `snake_case` - `user_balance`, `total_profit_loss`
- **Classes**: `PascalCase` - `TradingEngine`, `MarketDataProcessor`
- **Constants**: `UPPER_SNAKE_CASE` - `MAX_POSITIONS`, `DEFAULT_TIMEOUT`
- **Private methods**: `_snake_case` - `_validate_credentials()`, `_process_data()`
- **Modules/Files**: `snake_case` - `market_analytics.py`, `trading_engine.py`

#### JavaScript/React Frontend:
- **Functions**: `camelCase` - `calculateTotalValue()`, `handleUserLogin()`
- **Variables**: `camelCase` - `userBalance`, `totalProfitLoss`
- **Components**: `PascalCase` - `TradingDashboard`, `MarketChart`
- **Constants**: `UPPER_SNAKE_CASE` - `API_ENDPOINTS`, `DEFAULT_CONFIG`
- **Files**: `PascalCase` for components, `camelCase` for utilities
- **CSS Classes**: `kebab-case` - `trading-panel`, `market-data-grid`

### Code Structure Standards (MANDATORY)

#### Function Design:
```python
def calculate_portfolio_metrics(user_id: int, date_range: DateRange) -> PortfolioMetrics:
    """
    Calculate comprehensive portfolio performance metrics.
    
    Args:
        user_id: User identifier
        date_range: Date range for calculation
        
    Returns:
        PortfolioMetrics object with calculated values
        
    Raises:
        ValueError: If user_id is invalid
        DataNotFoundError: If no trades found for user
    """
    # Input validation
    if not user_id or user_id <= 0:
        raise ValueError("Invalid user_id provided")
    
    # Single responsibility - delegate to specialized functions
    trades = get_user_trades(user_id, date_range)
    return _compute_metrics_from_trades(trades)
```

### Error Handling Standards (MANDATORY)

#### Python:
```python
def process_market_data(data: dict) -> ProcessedData:
    if not data:
        raise ValueError("Market data cannot be empty")
    
    try:
        return MarketDataProcessor.process(data)
    except ValidationError as e:
        logger.error(f"Data validation failed: {e}")
        raise ProcessingError(f"Invalid market data format: {e}") from e
    except Exception as e:
        logger.exception("Unexpected error processing market data")
        raise ProcessingError("Failed to process market data") from e
```

### Documentation Standards (MANDATORY)

#### Python Docstrings:
```python
def calculate_risk_metrics(
    positions: List[Position],
    market_data: MarketData,
    confidence_level: float = 0.95
) -> RiskMetrics:
    """
    Calculate comprehensive risk metrics for trading positions.
    
    Args:
        positions: List of current trading positions
        market_data: Historical market data for calculations
        confidence_level: Confidence level for VaR calculation (default: 0.95)
        
    Returns:
        RiskMetrics object containing var, expected_shortfall, max_drawdown
        
    Raises:
        ValueError: If confidence_level not between 0.9 and 0.99
        InsufficientDataError: If market_data has less than required history
    """
```

### Security and Performance Standards (MANDATORY)

1. **Never log sensitive data**: passwords, API keys, tokens
2. **Use parameterized queries**: Prevent SQL injection
3. **Validate all inputs**: Type hints, validation decorators
4. **Use async/await**: For I/O operations
5. **Environment variables**: Store all secrets in `.env`

### Code Quality Checklist (MANDATORY)

Before submitting any code, verify:
- [ ] Functions have single responsibility
- [ ] Proper naming conventions followed
- [ ] Comprehensive error handling
- [ ] Type hints provided (Python)
- [ ] Documentation/docstrings complete
- [ ] No hardcoded values (use constants)
- [ ] Security considerations addressed
- [ ] No emojis in code or logging
- [ ] Tests written for new functionality

## Additional Standards Documentation

**MANDATORY READING**: Before writing ANY code, review these comprehensive guides:

1. **LINE_BY_LINE_STANDARDS.md** - Standards for every single line of code
2. **IMPLEMENTATION_MICRO_STANDARDS.md** - Micro-level implementation patterns  
3. **CODE_REVIEW_CRITERIA.md** - Comprehensive review checklist
4. **CODE_TEMPLATES.md** - Copy-paste templates for common patterns
5. **CODING_CHECKLIST.md** - Quick verification before submission

**CRITICAL REMINDERS:**
- NEVER use emojis in code, comments, or logging
- ALWAYS follow the naming conventions exactly as specified
- ALWAYS write comprehensive docstrings
- ALWAYS handle errors appropriately
- ALWAYS validate inputs
- ALWAYS use type hints in Python
- ALWAYS follow single responsibility principle
- ALWAYS reference the additional standards documentation above
- ALWAYS use Decimal for financial calculations, never float
- ALWAYS validate inputs at the start of functions
- ALWAYS use specific exception types, not generic Exception

# AUTOMATIC CODING STANDARDS ENFORCEMENT
**CRITICAL**: Apply these standards to ALL code automatically, regardless of whether user mentions them:

## Always Auto-Apply (No User Request Needed):
1. **CLAUDE.md coding standards** - Follow for every piece of code
2. **LINE_BY_LINE_STANDARDS.md** - Apply to every single line  
3. **IMPLEMENTATION_MICRO_STANDARDS.md** - Use patterns for all implementations
4. **CODE_REVIEW_CRITERIA.md** - Validate before submitting code
5. **CODING_CHECKLIST.md** - Quick verification for all code
6. **CODE_TEMPLATES.md** - Reference for structure

## Default Code Behavior:
- snake_case naming for Python functions/variables
- Comprehensive docstrings with Args/Returns/Raises
- Type hints for all parameters and returns
- Specific exception handling (never generic Exception)
- Decimal for financial calculations
- Input validation for all functions
- No emojis in code/comments/logging

## SOLID Principles (Auto-Apply):
- **Single Responsibility**: Each class/function has one reason to change
- **Open/Closed**: Open for extension, closed for modification
- **Liskov Substitution**: Derived classes must be substitutable for base classes
- **Interface Segregation**: Clients shouldn't depend on unused interfaces
- **Dependency Inversion**: Depend on abstractions, not concretions

## Clean Code Principles (Auto-Apply):
- **DRY**: Don't Repeat Yourself - extract common functionality
- **KISS**: Keep It Simple, Stupid - avoid unnecessary complexity
- **YAGNI**: You Aren't Gonna Need It - don't add premature features
- **Boy Scout Rule**: Leave code cleaner than you found it

## Separation of Concerns (Auto-Apply):
- Business logic separate from data access
- Validation separate from business operations
- Configuration separate from implementation
- UI logic separate from business logic
- Error handling separate from business flow

## Security Best Practices (Auto-Apply):
- No hardcoded secrets, passwords, API keys
- Parameterized database queries (prevent SQL injection)
- Input validation and sanitization
- Authentication and authorization checks
- Sensitive data not logged or exposed
- Rate limiting for API endpoints
- HTTPS for all external communications

## Logging Standards (Auto-Apply):
- Log entry and exit of critical functions
- Log business operations with context
- Use appropriate log levels (DEBUG, INFO, WARNING, ERROR)
- Include timestamp, user context, operation details
- Never log sensitive data (passwords, tokens, PII)
- Structured logging with consistent format
- Error logs include full stack trace and context

## Production-Grade Requirements (Auto-Apply):

### Performance & Scalability:
- Async/await for I/O operations
- Connection pooling for databases
- Pagination for large datasets
- Memory-efficient data structures
- Caching with TTL

### Testing & Quality:
- Unit tests (80%+ coverage)
- Integration tests for APIs
- Edge case testing
- Performance benchmarks
- Mock external dependencies

### Monitoring & Observability:
- Error tracking with context
- Performance metrics logging
- Health check endpoints
- Distributed tracing
- Business metrics tracking

### Resilience & Reliability:
- Circuit breaker pattern
- Retry with exponential backoff
- Graceful degradation
- Timeout configurations
- Correlation IDs

### Data & Configuration:
- Database transactions
- Environment-based config
- Audit trails
- Data validation layers
- Versioned migrations

### API & Deployment:
- RESTful design
- Proper HTTP status codes
- API versioning
- Rate limiting
- CI/CD pipeline ready

### Financial/Trading-Specific:
- Decimal precision for all monetary values
- Trade reconciliation and audit trails
- Market hours validation
- Risk management checks
- Regulatory compliance (SEBI, RBI)
- PnL calculations with mark-to-market accuracy

### Enterprise-Level:
- Business continuity (RTO < 30s, RPO < 1s)
- Disaster recovery procedures
- Compliance and regulatory reporting
- Thread-safe concurrent operations
- Event sourcing for critical events
- Comprehensive documentation and ADRs

### Technology-Specific (Auto-Apply):
**Python**: f-strings, type hints, dataclasses, context managers, asyncio
**Database**: SQLAlchemy ORM, Alembic migrations, proper indexing, connection pooling
**Security**: JWT auth, bcrypt hashing, HTTPS, CORS, CSP headers, rate limiting
**React**: Functional components, hooks, React.memo, lazy loading, accessibility
**UI/UX**: Material-UI consistency, loading states, responsive design, WCAG compliance
**Performance**: Bundle optimization, image optimization, caching, virtual scrolling
**Testing**: Unit/integration/E2E tests, 80% coverage, mock dependencies

## Claude Code Review Workflow (Auto-Execute):
- **Always follow CLAUDE_REVIEW_WORKFLOW.md 5-phase process**
- Phase 1: Standards compliance (naming, docs, types)
- Phase 2: Code quality (readability, performance, security)
- Phase 3: Financial validation (Decimal precision, audit trails)
- Phase 4: Test coverage (80%+ requirement)
- Phase 5: Documentation review (comprehensive docs)

**MANDATORY**: All above principles, technology standards, AND 5-phase review workflow apply to EVERY code request automatically.

# important-instruction-reminders  
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.