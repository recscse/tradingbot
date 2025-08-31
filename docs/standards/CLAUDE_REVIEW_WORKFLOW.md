# Claude Code Review Workflow

This document outlines the comprehensive code review process for Claude Code to follow automatically.

## 🔍 Automatic Review Process

### Phase 1: Initial Code Analysis (Always Execute)

When ANY code is written or modified, Claude Code must automatically:

1. **Standards Compliance Check**
   - Verify naming conventions (snake_case, PascalCase, UPPER_SNAKE_CASE)
   - Check for comprehensive docstrings
   - Validate type hints presence
   - Ensure specific exception handling

2. **Technology-Specific Validation**
   - **Python**: f-strings, context managers, asyncio patterns
   - **Database**: SQLAlchemy ORM usage, parameterized queries
   - **Security**: No hardcoded secrets, input validation
   - **React**: Functional components, hooks, accessibility
   - **Financial**: Decimal precision, audit trails

3. **SOLID Principles Assessment**
   - Single Responsibility Principle compliance
   - Open/Closed Principle adherence
   - Dependency Inversion implementation
   - Interface Segregation validation

### Phase 2: Code Quality Review (Mandatory)

For every function, class, or component:

1. **Readability Analysis**
   ```python
   # ✅ GOOD - Self-documenting code
   def calculate_portfolio_total_value(
       user_positions: List[Position],
       current_market_prices: Dict[str, Decimal],
       include_pending_orders: bool = False
   ) -> Decimal:
       """Calculate total portfolio value with current market prices."""
   
   # ❌ BAD - Unclear purpose and parameters
   def calc_val(pos, prices, flag=False):
       """Calculate value."""
   ```

2. **Performance Impact Assessment**
   - Database query optimization (N+1 prevention)
   - Memory usage analysis
   - Async/await pattern usage
   - Caching strategy implementation

3. **Security Vulnerability Scan**
   - SQL injection prevention
   - XSS vulnerability checks
   - Authentication/authorization validation
   - Sensitive data exposure prevention

### Phase 3: Financial/Trading-Specific Review (Auto-Execute)

For financial trading code:

1. **Precision Validation**
   ```python
   # ✅ CORRECT - Using Decimal for financial calculations
   portfolio_value = Decimal('0.00')
   for position in positions:
       position_value = Decimal(str(position.quantity)) * Decimal(str(current_price))
       portfolio_value += position_value
   
   # ❌ INCORRECT - Float precision issues
   portfolio_value = 0.0
   position_value = position.quantity * current_price
   ```

2. **Risk Management Checks**
   - Position sizing validation
   - Stop-loss implementation
   - Market hours verification
   - Regulatory compliance

3. **Audit Trail Verification**
   - Transaction logging
   - User action tracking
   - Error logging with context

### Phase 4: Test Coverage Analysis (Always Required)

1. **Unit Test Validation**
   - Minimum 80% code coverage
   - Edge case testing
   - Mock dependency usage
   - Performance test inclusion

2. **Integration Test Coverage**
   - API endpoint testing
   - Database interaction testing
   - External service mock testing

### Phase 5: Documentation Review (Mandatory)

1. **Code Documentation**
   - Function docstrings with Args/Returns/Raises
   - Complex logic inline comments
   - API endpoint documentation

2. **Architecture Documentation**
   - README updates for new features
   - Architecture decision records (ADRs)
   - Database schema changes

## 🚨 Automatic Rejection Criteria

Claude Code must REJECT code that contains:

1. **Naming Violations**
   - Generic variable names (data, item, value)
   - Abbreviated names (calc, temp, val)
   - Non-descriptive function names

2. **Missing Critical Elements**
   - No docstrings for public functions
   - Missing type hints
   - No input validation for public functions
   - Generic exception handling

3. **Security Issues**
   - Hardcoded secrets or API keys
   - Raw SQL queries
   - Missing input sanitization
   - No authentication checks for protected operations

4. **Financial Violations**
   - Float usage for monetary calculations
   - Missing audit trails for transactions
   - No risk validation for trades
   - Hardcoded financial limits

5. **Performance Issues**
   - N+1 database queries
   - Missing pagination for large datasets
   - Synchronous I/O operations
   - Memory leaks in React components

## ✅ Approval Checklist

Code can only be approved if ALL criteria are met:

### Basic Standards ✓
- [ ] Naming conventions followed
- [ ] Comprehensive documentation present
- [ ] Type hints included
- [ ] Specific exception handling implemented
- [ ] Input validation present

### Technology-Specific ✓
- [ ] Python: f-strings, type hints, asyncio patterns
- [ ] Database: SQLAlchemy ORM, connection pooling
- [ ] Security: JWT auth, parameterized queries
- [ ] React: Functional components, accessibility
- [ ] Performance: Optimized queries, caching

### Financial/Trading ✓
- [ ] Decimal precision for monetary values
- [ ] Audit trails for all transactions
- [ ] Risk management checks
- [ ] Regulatory compliance considerations
- [ ] Market hours validation

### Production Readiness ✓
- [ ] Unit tests with 80%+ coverage
- [ ] Integration tests present
- [ ] Error handling comprehensive
- [ ] Logging implemented
- [ ] Monitoring considerations included

## 📝 Review Comment Templates

### For Immediate Rejection:
```
🚫 REJECTED: Critical violation found

Issue: [Specific problem]
Solution: [Required fix]
Reference: [Standards document]

This PR cannot be approved until this issue is resolved.
```

### For Required Changes:
```
🔧 CHANGES REQUIRED

Issues Found:
1. [Issue 1 with solution]
2. [Issue 2 with solution]

Please address these issues and request review again.
```

### For Approval:
```
✅ APPROVED

Code meets all standards:
✓ Naming conventions
✓ Documentation complete
✓ Security validated
✓ Performance optimized
✓ Tests comprehensive

Ready for merge.
```

## 🔄 Continuous Improvement

1. **Metrics Tracking**
   - Review time per pull request
   - Defect detection rate
   - Standards compliance percentage
   - Code quality improvements

2. **Standards Updates**
   - Regular review of standards effectiveness
   - Industry best practice integration
   - Team feedback incorporation

## 🎯 Success Metrics

**Target Goals:**
- 100% standards compliance
- <5% code requiring major rework
- 95%+ defect detection rate
- 80%+ test coverage maintenance
- Zero security vulnerabilities in production

**Review Quality Indicators:**
- Consistent application of standards
- Constructive feedback provided
- Educational value in comments
- Timely review completion
- Production-ready code output

---

**Remember:** This workflow ensures every piece of code meets enterprise-grade standards automatically, making our trading platform reliable, secure, and maintainable.