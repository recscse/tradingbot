# Line-by-Line Coding Standards

**CRITICAL**: Every single line of code must follow these micro-level standards. No exceptions.

## Every Line Must Ask These Questions

Before writing ANY line of code, ask:
1. **Purpose**: Why does this line exist?
2. **Clarity**: Is it immediately understandable?
3. **Necessity**: Can this be simplified or removed?
4. **Safety**: What can go wrong with this line?
5. **Performance**: Is this the most efficient approach?

## Variable Declaration Standards

### ✅ GOOD Examples:
```python
# Clear, descriptive, immediate understanding
user_portfolio_balance = Decimal('0.00')
maximum_allowed_positions = 10
current_active_trade_count = 0
is_market_open_for_trading = False
last_price_update_timestamp = datetime.now()

# Constants are SCREAMING_SNAKE_CASE with context
PORTFOLIO_CALCULATION_TIMEOUT_SECONDS = 30
MAXIMUM_DAILY_LOSS_PERCENTAGE = 5.0
DEFAULT_RISK_TOLERANCE_LEVEL = RiskLevel.MODERATE
```

### ❌ BAD Examples:
```python
# Unclear, abbreviated, confusing
bal = 0  # What balance? User? Account? Portfolio?
max_pos = 10  # Max positions? Max something else?
cnt = 0  # Count of what?
flag = False  # What does this flag represent?
ts = datetime.now()  # Timestamp of what event?
```

## Function Call Standards

### ✅ GOOD Examples:
```python
# Each parameter is clear and well-named
portfolio_value = calculate_total_portfolio_value(
    user_id=current_user.id,
    include_pending_orders=True,
    as_of_date=trading_session.current_date,
    currency_code='INR'
)

# Break complex calls into readable chunks
risk_assessment = risk_calculator.assess_position_risk(
    position=new_position,
    market_volatility=current_market_volatility,
    user_risk_tolerance=user.risk_profile.tolerance_level
)

# Chain calls clearly with intermediate variables
raw_market_data = fetch_market_data_from_broker(symbol)
validated_data = validate_market_data_integrity(raw_market_data)
processed_data = transform_data_for_analysis(validated_data)
```

### ❌ BAD Examples:
```python
# Unclear parameters, nested complexity
val = calc(user.id, True, dt.now(), 'INR')

# Unreadable chaining
result = process(validate(fetch(symbol).data).clean()).analyze()
```

## Conditional Logic Standards

### ✅ GOOD Examples:
```python
# Clear boolean expressions with descriptive names
is_user_authorized_for_trading = (
    user.is_verified and 
    user.has_sufficient_balance and 
    user.risk_profile_completed
)

if is_user_authorized_for_trading:
    proceed_with_trade_execution()

# Explicit null/empty checks
if portfolio_positions is None:
    raise ValueError("Portfolio positions data is required")

if len(portfolio_positions) == 0:
    logger.warning(f"No positions found for user {user_id}")
    return empty_portfolio_response()

# Guard clauses for early returns
if not user_id:
    raise ValueError("User ID cannot be empty")
    
if user_id <= 0:
    raise ValueError("User ID must be positive integer")
    
if not user.is_active:
    raise UserAccountInactiveError(f"User {user_id} account is inactive")
```

### ❌ BAD Examples:
```python
# Unclear conditions
if user.verified and user.balance and user.risk:
    # What does this really check?

# Nested complexity
if data:
    if len(data) > 0:
        if data[0]:
            # Too many nested levels
```

## Loop Standards

### ✅ GOOD Examples:
```python
# Clear iteration purpose and variable names
for individual_position in user_portfolio_positions:
    current_market_value = calculate_position_current_value(individual_position)
    total_portfolio_value += current_market_value
    
    # Clear break conditions
    if total_portfolio_value > maximum_portfolio_limit:
        logger.warning(f"Portfolio limit exceeded: {total_portfolio_value}")
        break

# Enumerate when index is needed
for position_index, trading_position in enumerate(active_positions):
    position_rank = position_index + 1
    logger.info(f"Processing position #{position_rank}: {trading_position.symbol}")

# Dictionary iteration with clear names
for stock_symbol, position_data in portfolio_positions.items():
    current_stock_price = get_latest_stock_price(stock_symbol)
    position_current_value = position_data.quantity * current_stock_price
    update_position_market_value(stock_symbol, position_current_value)
```

### ❌ BAD Examples:
```python
# Unclear iteration variables
for x in data:
    val = calc(x)
    
for i, p in enumerate(pos):
    # What is i? What is p?
```

## Error Handling Line Standards

### ✅ GOOD Examples:
```python
try:
    # Clear operation description in comment
    user_portfolio_data = fetch_user_portfolio_from_database(user_id)
    
except DatabaseConnectionError as database_error:
    # Specific exception with descriptive variable name
    logger.error(
        f"Database connection failed while fetching portfolio for user {user_id}: "
        f"{database_error}"
    )
    raise PortfolioUnavailableError(
        "Unable to retrieve portfolio data due to database connectivity issues"
    ) from database_error
    
except ValidationError as validation_error:
    # Handle specific validation issues
    logger.warning(
        f"Portfolio data validation failed for user {user_id}: {validation_error}"
    )
    raise InvalidPortfolioDataError(
        f"Portfolio data is corrupted for user {user_id}"
    ) from validation_error
    
except Exception as unexpected_error:
    # Always log unexpected errors with full context
    logger.exception(
        f"Unexpected error occurred while processing portfolio for user {user_id}"
    )
    raise PortfolioProcessingError(
        "An unexpected error occurred while processing portfolio data"
    ) from unexpected_error
```

### ❌ BAD Examples:
```python
try:
    data = fetch(id)
except Exception as e:
    # Too generic, no context
    raise Exception("Error") from e
```

## Comment Standards for Every Line

### ✅ GOOD Examples:
```python
# Calculate portfolio value using real-time market prices
portfolio_value = Decimal('0.00')

# Iterate through each position to compute individual values
for position in user_positions:
    # Get current market price from live feed
    current_price = market_data_service.get_live_price(position.symbol)
    
    # Calculate position value: quantity × current price
    position_value = Decimal(str(position.quantity)) * Decimal(str(current_price))
    
    # Add to total portfolio value
    portfolio_value += position_value
    
    # Log individual position calculation for debugging
    logger.debug(
        f"Position {position.symbol}: {position.quantity} × {current_price} = {position_value}"
    )

# Return calculated value with proper precision
return portfolio_value
```

### ✅ Complex Logic Comments:
```python
# Risk calculation using Black-Scholes model with Indian market adjustments
risk_free_rate = get_indian_risk_free_rate()  # Current RBI repo rate
market_volatility = calculate_nifty_implied_volatility()  # VIX equivalent for NSE

# Adjust volatility for Indian market hours (9:15 AM - 3:30 PM IST)
adjusted_volatility = market_volatility * INDIAN_MARKET_HOURS_ADJUSTMENT_FACTOR

# Calculate option Greeks for risk assessment
option_delta = calculate_option_delta(
    underlying_price=current_stock_price,
    strike_price=option_contract.strike_price,
    time_to_expiry=days_until_expiry / 365.0,
    volatility=adjusted_volatility,
    risk_free_rate=risk_free_rate
)
```

## Logging Standards for Every Line

### ✅ GOOD Examples:
```python
# Entry point logging with context
logger.info(f"Starting portfolio calculation for user {user_id} at {datetime.now()}")

# Progress logging for long operations
logger.info(f"Processing {len(positions)} positions for portfolio calculation")

# Debug logging for development
logger.debug(f"Retrieved market price for {symbol}: {current_price}")

# Warning for business logic issues
logger.warning(
    f"Position {position.symbol} has negative value: {position_value}. "
    f"This may indicate data quality issues."
)

# Error logging with full context
logger.error(
    f"Failed to calculate position value for {symbol}. "
    f"Position: {position}, Price: {current_price}, Error: {str(error)}"
)

# Success logging with results
logger.info(
    f"Portfolio calculation completed for user {user_id}. "
    f"Total value: {portfolio_value}, Positions: {len(positions)}"
)
```

## Import Statement Standards

### ✅ GOOD Examples:
```python
# Standard library imports first
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Union

# Third-party imports second  
import pandas as pd
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, validator

# Local application imports third
from database.connection import get_database_session
from database.models import User, Portfolio, Position, Trade
from services.market_data.price_service import LivePriceService
from services.trading.risk_manager import RiskManager
from utils.validation.input_validators import validate_user_id
from utils.exceptions.trading_exceptions import PortfolioCalculationError
```

## Assignment Standards

### ✅ GOOD Examples:
```python
# Clear assignment with type hints
user_total_balance: Decimal = Decimal('0.00')
maximum_position_size: int = 1000
is_trading_session_active: bool = check_market_hours()
current_positions_list: List[Position] = []

# Dictionary assignments with clear structure
portfolio_summary: Dict[str, Union[Decimal, int]] = {
    'total_value': portfolio_total_value,
    'total_positions': active_positions_count,
    'daily_pnl': calculated_daily_profit_loss,
    'cash_balance': available_cash_balance
}

# Complex object initialization with named parameters
risk_calculator = PortfolioRiskCalculator(
    risk_model=RiskModel.BLACK_SCHOLES,
    confidence_level=0.95,
    time_horizon_days=1,
    currency='INR',
    market_data_source=market_data_service
)
```

## Return Statement Standards

### ✅ GOOD Examples:
```python
# Simple returns with clear values
return calculated_portfolio_value

# Complex returns with clear structure
return PortfolioSummary(
    total_value=total_portfolio_value,
    positions_count=len(active_positions),
    daily_change=daily_profit_loss,
    last_updated=datetime.now(timezone.utc),
    currency='INR'
)

# Early returns with clear conditions
if not user_has_valid_permissions:
    return PermissionDeniedResponse(
        message="User lacks sufficient permissions for portfolio access"
    )
    
if portfolio_positions_empty:
    return EmptyPortfolioResponse(
        message="No positions found for user",
        user_id=user_id
    )
```

## Line-by-Line Review Checklist

**For EVERY line of code, verify:**

1. **Readability**: Can a new developer understand this line immediately?
2. **Purpose**: Is the purpose of this line obvious?
3. **Safety**: What happens if this line fails?
4. **Performance**: Is this the most efficient way?
5. **Maintainability**: Will this be easy to modify later?
6. **Testability**: Can this line be easily tested?
7. **Documentation**: Is this line properly documented?
8. **Standards**: Does this follow our naming conventions?
9. **Security**: Does this line introduce any security risks?
10. **Business Logic**: Does this align with business requirements?

## Code Review Questions for Each Line

**Before approving ANY line:**

- [ ] Is the variable/function name self-documenting?
- [ ] Are all inputs validated?
- [ ] Are all possible errors handled?
- [ ] Is the logic as simple as possible?
- [ ] Are there any magic numbers or strings?
- [ ] Is the performance acceptable?
- [ ] Is this line necessary?
- [ ] Does this follow DRY principle?
- [ ] Is this testable in isolation?
- [ ] Does this handle edge cases?

**CRITICAL RULE**: If you cannot answer "YES" to all questions for a line of code, that line must be rewritten.

## Modification Standards

**When modifying existing code:**

1. **Understand Context**: Read surrounding 20 lines minimum
2. **Preserve Intent**: Maintain original business logic purpose
3. **Improve Quality**: Make it better than before
4. **Add Tests**: Cover your modifications
5. **Update Documentation**: Reflect your changes
6. **Performance Impact**: Ensure no degradation
7. **Backward Compatibility**: Don't break existing features

**Every modification must improve the codebase overall quality.**