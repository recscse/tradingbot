# Comprehensive Code Review Criteria

**MANDATORY**: Every line of code must pass ALL these criteria before acceptance.

## Pre-Code Review Checklist

**Before submitting ANY code, verify:**

### 1. Naming Standards ✓
- [ ] Functions use `snake_case`: `calculate_portfolio_value()`
- [ ] Variables use `snake_case`: `user_balance`, `total_profit_loss`
- [ ] Classes use `PascalCase`: `TradingEngine`, `PortfolioManager`
- [ ] Constants use `UPPER_SNAKE_CASE`: `MAX_POSITIONS`, `API_TIMEOUT`
- [ ] Private methods start with underscore: `_validate_input()`
- [ ] Boolean variables are questions: `is_market_open`, `has_permissions`
- [ ] Collection variables are plural: `positions`, `trades`, `orders`
- [ ] No abbreviations: `user_id` not `uid`, `calculate` not `calc`

### 2. Documentation Standards ✓
- [ ] Every function has comprehensive docstring
- [ ] Docstring includes Args section with types
- [ ] Docstring includes Returns section with type
- [ ] Docstring includes Raises section with specific exceptions
- [ ] Complex logic has inline comments explaining "why"
- [ ] Business logic comments explain domain concepts
- [ ] TODO comments include date and assignee
- [ ] No dead code or commented-out blocks

### 3. Type Safety ✓
- [ ] All function parameters have type hints
- [ ] All function return types are specified
- [ ] Complex types use proper generics: `List[Position]`, `Dict[str, Decimal]`
- [ ] Optional parameters use `Optional[Type]`
- [ ] Union types are used when appropriate: `Union[int, str]`
- [ ] Custom types are defined for business objects
- [ ] Type checking passes without errors

### 4. Input Validation ✓
- [ ] All public functions validate their inputs
- [ ] Validation happens at the start of functions
- [ ] Invalid inputs raise specific exceptions with clear messages
- [ ] None/empty checks are explicit: `if data is None:`
- [ ] Numeric ranges are validated: `if user_id <= 0:`
- [ ] String inputs are stripped and validated
- [ ] Complex objects are validated using isinstance()

### 5. Error Handling ✓
- [ ] All possible exceptions are caught and handled
- [ ] Specific exception types are used (not generic Exception)
- [ ] Exception messages provide context and actionable information
- [ ] Original exceptions are chained using `raise ... from e`
- [ ] Critical errors are logged with full context
- [ ] Business logic errors use custom exception classes
- [ ] Resource cleanup happens in finally blocks or context managers

### 6. Financial Precision ✓
- [ ] Money values use `Decimal` type, never float
- [ ] Currency conversions maintain precision
- [ ] Percentage calculations use Decimal arithmetic
- [ ] Rounding is explicit with specified precision
- [ ] Division operations handle zero divisor cases
- [ ] Financial calculations are logged for audit trail

### 7. Security Standards ✓
- [ ] No hardcoded passwords, tokens, or API keys
- [ ] All database queries use parameterized statements
- [ ] User inputs are sanitized and validated
- [ ] Sensitive data is not logged
- [ ] Authentication is required for protected operations
- [ ] Authorization checks are performed
- [ ] Input length limits are enforced

### 8. Performance Standards ✓
- [ ] Database queries are optimized with proper indexes
- [ ] N+1 query problems are avoided
- [ ] Large datasets use pagination
- [ ] Expensive operations are cached when appropriate
- [ ] Async/await is used for I/O operations
- [ ] Memory usage is reasonable for expected load
- [ ] Loop complexity is optimized

### 9. Logging Standards ✓
- [ ] Entry and exit points are logged for critical functions
- [ ] Business operations are logged with sufficient context
- [ ] Error logging includes full error details and context
- [ ] Log levels are appropriate (DEBUG, INFO, WARNING, ERROR)
- [ ] Sensitive data is not logged
- [ ] Log messages are actionable and clear
- [ ] Performance metrics are logged for critical operations

### 10. Testing Standards ✓
- [ ] All new functions have corresponding unit tests
- [ ] Tests cover both success and failure scenarios
- [ ] Edge cases are tested (empty inputs, boundary values)
- [ ] Mock objects are used for external dependencies
- [ ] Test names clearly describe what is being tested
- [ ] Tests are independent and can run in any order
- [ ] Test data setup and cleanup is handled properly

## Line-by-Line Review Questions

**For EVERY line of code, ask:**

### Readability Questions
1. **Immediate Understanding**: Can I understand this line without context?
2. **Variable Names**: Do variable names explain their purpose?
3. **Magic Numbers**: Are there any hardcoded values that should be constants?
4. **Complexity**: Is this line doing too many things?

### Correctness Questions
1. **Logic**: Is the logic correct for all possible inputs?
2. **Edge Cases**: What happens with null, empty, or boundary values?
3. **Type Safety**: Are types used consistently?
4. **Business Rules**: Does this implement business requirements correctly?

### Maintainability Questions
1. **Future Changes**: How hard would it be to modify this line?
2. **Dependencies**: Does this line couple components unnecessarily?
3. **Reusability**: Could this logic be reused elsewhere?
4. **Documentation**: Is the purpose clear to future developers?

### Security Questions
1. **Input Validation**: Are all inputs properly validated?
2. **Data Exposure**: Could this leak sensitive information?
3. **Injection Attacks**: Are queries parameterized?
4. **Authentication**: Are security checks in place?

### Performance Questions
1. **Efficiency**: Is this the most efficient approach?
2. **Scalability**: How does this perform with large datasets?
3. **Resource Usage**: Does this manage memory/connections properly?
4. **Caching**: Should this result be cached?

## Code Review Process

### Step 1: Automated Checks
```bash
# Run these before human review
python -m pytest tests/
python -m mypy src/
python -m flake8 src/
python -m black --check src/
```

### Step 2: Manual Review Phases

#### Phase 1: Architecture Review
- [ ] Does this follow single responsibility principle?
- [ ] Are abstractions appropriate?
- [ ] Is the design extensible?
- [ ] Are dependencies managed correctly?

#### Phase 2: Implementation Review  
- [ ] Is the algorithm correct and efficient?
- [ ] Are all edge cases handled?
- [ ] Is error handling comprehensive?
- [ ] Are business rules implemented correctly?

#### Phase 3: Code Quality Review
- [ ] Are naming conventions followed?
- [ ] Is documentation complete and accurate?
- [ ] Are logging and monitoring adequate?
- [ ] Is the code testable?

#### Phase 4: Security Review
- [ ] Are inputs properly validated and sanitized?
- [ ] Is authentication and authorization correct?
- [ ] Are sensitive operations logged appropriately?
- [ ] Are dependencies secure and up-to-date?

## Rejection Criteria

**Code MUST be rejected if:**

1. **Any naming convention is violated**
2. **Missing or inadequate documentation**
3. **No input validation for public functions**
4. **Generic exception handling**
5. **Float used for financial calculations**
6. **Hardcoded secrets or configuration**
7. **No error handling for external calls**
8. **Magic numbers without explanation**
9. **Functions longer than 50 lines without justification**
10. **Missing unit tests for new functionality**

## Approval Criteria

**Code can be approved ONLY if:**

1. **All automated checks pass**
2. **All manual review phases are complete**
3. **No rejection criteria are present**
4. **Performance impact is acceptable**
5. **Security review is passed**
6. **Documentation is complete**
7. **Tests provide adequate coverage**
8. **Business requirements are satisfied**

## Review Comments Templates

### For Naming Issues:
```
❌ Variable name 'data' is too generic. 
✅ Use descriptive name like 'user_portfolio_positions' 
📖 Reference: CLAUDE.md naming conventions
```

### For Missing Documentation:
```
❌ Function missing comprehensive docstring
✅ Add docstring with Args, Returns, Raises sections
📖 Reference: CODE_TEMPLATES.md function template
```

### For Error Handling:
```
❌ Generic exception handling hides real issues
✅ Catch specific exceptions and provide context
📖 Reference: LINE_BY_LINE_STANDARDS.md error handling
```

### For Type Safety:
```
❌ Missing type hints for parameters
✅ Add type hints: def calculate_value(price: Decimal) -> Decimal:
📖 Reference: Python typing documentation
```

### For Python-Specific Issues:
```
❌ Using .format() instead of f-strings
✅ Use f-strings: f"Processing {symbol} at {price}"
📖 Reference: Python PEP 498 - Literal String Interpolation
```

### For Database Issues:
```
❌ Raw SQL query without parameterization
✅ Use SQLAlchemy ORM: session.query(User).filter(User.id == user_id)
📖 Reference: SQLAlchemy documentation
```

### For Security Issues:
```
❌ Hardcoded API key in source code
✅ Use environment variables: os.getenv('API_KEY')
📖 Reference: Security best practices
```

### For React/Frontend Issues:
```
❌ Class component without hooks
✅ Convert to functional component with useState/useEffect
📖 Reference: React Hooks documentation
```

### For Performance Issues:
```
❌ Loading all records without pagination
✅ Implement pagination: .limit(20).offset(page * 20)
📖 Reference: Performance optimization guidelines
```

### For Accessibility Issues:
```
❌ Button without aria-label
✅ Add accessibility: <button aria-label="Submit trade order">
📖 Reference: WCAG 2.1 guidelines
```

### For Financial/Trading Issues:
```
❌ Using float for monetary calculations
✅ Use Decimal: from decimal import Decimal; price = Decimal('100.50')
📖 Reference: Financial precision standards
```

## Review Quality Metrics

**Track these metrics for review quality:**

1. **Defect Detection Rate**: Issues found in review vs production
2. **Review Coverage**: Percentage of lines reviewed thoroughly
3. **Review Time**: Time spent per line of code reviewed
4. **Rework Rate**: Percentage of code requiring changes
5. **Standards Compliance**: Adherence to coding standards

**Target Metrics:**
- 95%+ defect detection rate
- 100% review coverage for critical code
- <5% code requiring major rework
- 100% standards compliance

## GOLDEN RULES FOR REVIEWERS

1. **Be Thorough**: Every line matters in financial systems
2. **Be Constructive**: Suggest improvements, don't just criticize
3. **Be Consistent**: Apply standards uniformly
4. **Be Educational**: Help developers learn from feedback
5. **Be Security-Minded**: Always consider security implications

**Remember**: Code review is the last line of defense before production. Take it seriously.