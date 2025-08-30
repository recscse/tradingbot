# Quick Coding Standards Checklist

**Before accepting any code, verify:**

## Naming ✓
- [ ] Functions: `snake_case` (e.g., `calculate_portfolio_value`)
- [ ] Variables: `snake_case` (e.g., `user_balance`)
- [ ] Classes: `PascalCase` (e.g., `TradingEngine`)
- [ ] Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_POSITIONS`)

## Documentation ✓
- [ ] Comprehensive docstring with description
- [ ] Args section with types and descriptions
- [ ] Returns section with type and description  
- [ ] Raises section with specific exceptions
- [ ] Example usage (for complex functions)

## Code Quality ✓
- [ ] Type hints for all parameters and return values
- [ ] Input validation at function start
- [ ] Specific exception types (not generic Exception)
- [ ] Single responsibility (function does one thing)
- [ ] No magic numbers (use named constants)
- [ ] No emojis in code, comments, or logging

## Error Handling ✓
- [ ] Validate inputs before processing
- [ ] Use specific exception types
- [ ] Include helpful error messages
- [ ] Log errors appropriately
- [ ] Chain exceptions with `raise ... from e`

**If ANY item is missing, request fixes before proceeding!**