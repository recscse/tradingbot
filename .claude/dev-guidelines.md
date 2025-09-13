# Development Guidelines for Trading Application

## How .claude Directory Enhances Development

The `.claude` directory is your AI development supercharger. It provides:

### 1. Specialized AI Agents
- **trading-system-architect**: Financial system expertise, Decimal precision, regulatory compliance
- **code-quality-enforcer**: Automatic standards enforcement, security validation
- **websocket-specialist**: Real-time systems, high-performance streaming
- **software-engineer**: General development with trading context
- **hft-expert**: High-frequency trading, microsecond latency optimization, market microstructure
- **fullstack-trading-expert**: End-to-end trading platform development, React/FastAPI integration
- **stock-market-expert**: Indian market analysis, technical/fundamental analysis, SEBI regulations
- **algo-trader-expert**: Strategy development, backtesting, quantitative analysis, ML models
- **css-ui-ux-expert**: Trading interface design, Material-UI, responsive layouts, accessibility
- **fastapi-python-expert**: High-performance APIs, async programming, WebSocket endpoints

### 2. Code Templates for Consistency
- **python-service-template.py**: Service layer with proper error handling, Decimal precision
- **react-component-template.jsx**: Material-UI components with performance optimization
- **websocket-client-template.py**: Real-time data clients with reconnection logic

### 3. Automatic Quality Enforcement
Every code request automatically applies:
- CLAUDE.md coding standards
- Financial precision (Decimal, not float)
- Comprehensive error handling
- Security best practices
- Performance optimization
- Type safety and documentation

## Development Workflow

### For Python Backend Services:
1. Use **trading-system-architect** for financial logic
2. Apply **python-service-template.py** patterns
3. **code-quality-enforcer** validates automatically
4. Ensures Decimal precision for all monetary values

### For React Frontend Components:
1. Follow **react-component-template.jsx** structure
2. Material-UI v6 compliance
3. Performance optimization with hooks
4. Responsive design patterns

### For WebSocket/Real-time Features:
1. Use **websocket-specialist** agent
2. Apply **websocket-client-template.py** patterns
3. Handle reconnection and error recovery
4. Implement proper event broadcasting

## Key Benefits Over Standard Development

### Before .claude Setup:
- ❌ Generic code without trading context
- ❌ Float precision causing financial errors
- ❌ Inconsistent error handling
- ❌ Missing security validations
- ❌ No automated quality checks

### After .claude Setup:
- ✅ Trading-specific implementations
- ✅ Decimal precision for all financial data
- ✅ Comprehensive error handling with audit trails
- ✅ Security validation built-in
- ✅ Automatic code quality enforcement
- ✅ Production-grade patterns

## Expected Code Quality Improvements

### Financial Accuracy:
```python
# Before: Risk of precision errors
total = 1.1 + 2.2  # 3.3000000000000003

# After: Guaranteed precision
total = Decimal('1.1') + Decimal('2.2')  # 3.3
```

### Error Handling:
```python
# Before: Generic exceptions
try:
    process_trade()
except Exception as e:
    print(f"Error: {e}")

# After: Specific handling with audit
try:
    process_trade()
except ValidationError as e:
    logger.error(f"Trade validation failed: {e}")
    audit_trail.log_failed_trade(trade_id, str(e))
    raise TradingError(f"Invalid trade data: {e}") from e
```

### Performance Optimization:
```javascript
// Before: Re-renders on every change
function TradingPanel({ data }) {
    return data.map(item => <Item key={item.id} data={item} />);
}

// After: Optimized with memoization
const TradingPanel = memo(({ data }) => {
    const processedData = useMemo(() =>
        data.map(item => processItem(item)), [data]);

    return processedData.map(item =>
        <Item key={item.id} data={item} />);
});
```

## Usage Commands

### Request Specialized Help:
- "Use trading-system-architect to implement portfolio calculation"
- "Use websocket-specialist to fix market data streaming"
- "Use code-quality-enforcer to review this code"
- "Use hft-expert to optimize order execution latency"
- "Use fullstack-trading-expert for end-to-end feature development"
- "Use stock-market-expert for technical analysis implementation"
- "Use algo-trader-expert to create momentum trading strategy"
- "Use css-ui-ux-expert to design responsive trading dashboard"
- "Use fastapi-python-expert to build high-performance API endpoints"

### Apply Templates:
- "Follow python-service-template for this new service"
- "Use react-component-template for the trading dashboard"
- "Apply websocket-client-template for Upstox integration"

## Automated Features

### Every Code Request Includes:
1. **Standards Validation**: CLAUDE.md compliance check
2. **Security Scan**: No hardcoded secrets, proper validation
3. **Performance Review**: Async patterns, efficient algorithms
4. **Financial Accuracy**: Decimal precision validation
5. **Documentation**: Comprehensive docstrings and type hints

### Quality Metrics:
- 80%+ test coverage requirement
- Zero security vulnerabilities
- Sub-millisecond latency for real-time features
- Regulatory compliance (SEBI, RBI)
- Production-grade error handling

This setup transforms Claude Code from a general AI assistant into a specialized trading system development expert.