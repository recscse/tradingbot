# Automated Code Quality Checklist

## Financial Trading System Requirements

### 1. Financial Precision (CRITICAL)
- [ ] All monetary values use `Decimal` type, never `float`
- [ ] Price calculations maintain precision to 2-4 decimal places
- [ ] Percentage calculations use Decimal arithmetic
- [ ] Currency formatting follows Indian standards (₹)
- [ ] Portfolio calculations handle large numbers correctly

### 2. Security Validation (MANDATORY)
- [ ] No hardcoded API keys, passwords, or secrets
- [ ] All database queries use parameterization
- [ ] Input validation for all user-provided data
- [ ] Authentication tokens properly validated
- [ ] Rate limiting implemented for API endpoints
- [ ] HTTPS enforced for all external communications

### 3. Error Handling & Logging
- [ ] Specific exception types (no generic `Exception`)
- [ ] Comprehensive error logging with context
- [ ] Audit trails for all financial operations
- [ ] Graceful degradation for external service failures
- [ ] Circuit breaker patterns for broker connections
- [ ] Correlation IDs for distributed tracing

### 4. Performance Standards
- [ ] Async/await for all I/O operations
- [ ] Database connection pooling configured
- [ ] Caching implemented with TTL
- [ ] Memory-efficient data structures
- [ ] Sub-millisecond latency for market data processing
- [ ] Pagination for large datasets

### 5. Code Quality Standards
- [ ] Snake_case naming for Python
- [ ] CamelCase naming for JavaScript/React
- [ ] Type hints for all Python functions
- [ ] Comprehensive docstrings with Args/Returns/Raises
- [ ] Single Responsibility Principle followed
- [ ] DRY principle applied (no code duplication)

### 6. Testing Requirements
- [ ] Unit tests with 80%+ coverage
- [ ] Integration tests for API endpoints
- [ ] Mock external dependencies (broker APIs)
- [ ] Edge case testing for financial calculations
- [ ] Performance benchmarks for critical paths
- [ ] Error scenario testing

### 7. Trading System Specific
- [ ] Market hours validation implemented
- [ ] Position size limits enforced
- [ ] Risk management checks integrated
- [ ] Order status tracking comprehensive
- [ ] Broker-specific error handling
- [ ] Real-time data validation

### 8. WebSocket & Real-time Systems
- [ ] Automatic reconnection with exponential backoff
- [ ] Heartbeat mechanism for connection health
- [ ] Event-driven architecture with proper typing
- [ ] Connection lifecycle management
- [ ] Data normalization across broker formats
- [ ] Proper resource cleanup on disconnect

### 9. Database & Data Management
- [ ] Transaction boundaries properly defined
- [ ] Foreign key constraints enforced
- [ ] Index optimization for query performance
- [ ] Data migration scripts versioned
- [ ] Backup and recovery procedures defined
- [ ] Data retention policies implemented

### 10. Production Readiness
- [ ] Health check endpoints available
- [ ] Monitoring and alerting configured
- [ ] Environment-based configuration
- [ ] Deployment automation ready
- [ ] Rollback procedures defined
- [ ] Documentation comprehensive

## Automated Validation Commands

### Python Backend:
```bash
# Run linting
flake8 services/ router/ database/

# Type checking
mypy services/ router/ database/

# Security scan
bandit -r services/ router/ database/

# Test coverage
pytest --cov=services --cov-report=html
```

### Frontend (React):
```bash
# Linting
npm run lint

# Type checking
npm run type-check

# Security audit
npm audit

# Test coverage
npm test -- --coverage
```

### Database:
```bash
# Migration validation
alembic check

# Schema validation
alembic upgrade --sql head
```

## Quality Gates

### Pre-commit Requirements:
- All checklist items must pass
- Test coverage >= 80%
- No security vulnerabilities
- Performance benchmarks met
- Documentation complete

### Pre-deployment Requirements:
- Integration tests passing
- Load testing completed
- Security scan clean
- Database migrations tested
- Monitoring configured

## Financial Calculation Examples

### Correct Decimal Usage:
```python
# Portfolio value calculation
def calculate_portfolio_value(positions: List[Position]) -> Decimal:
    total = Decimal('0')
    for position in positions:
        quantity = Decimal(str(position.quantity))
        price = Decimal(str(position.current_price))
        total += quantity * price
    return total

# Percentage calculation
def calculate_return_percentage(initial: Decimal, current: Decimal) -> Decimal:
    if initial == Decimal('0'):
        return Decimal('0')
    return ((current - initial) / initial) * Decimal('100')
```

### Error Handling Pattern:
```python
async def execute_trade(trade_request: TradeRequest) -> TradeResponse:
    try:
        # Validate trade request
        await validate_trade_request(trade_request)

        # Execute trade
        result = await broker_client.place_order(trade_request)

        # Log successful trade
        audit_trail.log_trade_execution(trade_request, result)

        return TradeResponse(success=True, data=result)

    except ValidationError as e:
        logger.error(f"Trade validation failed: {e}")
        audit_trail.log_failed_trade(trade_request, str(e))
        raise TradingError(f"Invalid trade request: {e}") from e

    except BrokerConnectionError as e:
        logger.error(f"Broker connection failed: {e}")
        raise TradingError("Trading service temporarily unavailable") from e

    except Exception as e:
        logger.exception(f"Unexpected trading error: {e}")
        raise TradingError("Internal trading system error") from e
```

This checklist ensures every piece of code meets production standards for a financial trading system.