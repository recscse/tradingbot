# Micro-Level Implementation Standards

**MANDATORY**: Follow these standards for every specific implementation scenario.

## Variable Initialization Patterns

### ✅ Financial Data - Always Use Decimal
```python
# NEVER use float for money - precision loss
portfolio_value = Decimal('0.00')  # ✅ Correct
user_balance = Decimal(str(balance_from_api))  # ✅ Convert safely
stop_loss_price = Decimal('2550.75')  # ✅ Precise decimal

# BAD - Float precision issues
portfolio_value = 0.0  # ❌ Never for money
price = 2550.75  # ❌ Can cause rounding errors
```

### ✅ Counters and IDs
```python
# Counters start at zero with descriptive names
active_positions_count = 0
processed_trades_count = 0
failed_api_calls_count = 0

# IDs are validated immediately
user_id = int(user_id_input)
if user_id <= 0:
    raise ValueError(f"Invalid user ID: {user_id}")
```

### ✅ Boolean Flags
```python
# Boolean names are questions that can be answered yes/no
is_market_open = check_current_market_status()
has_sufficient_balance = user.balance >= required_amount
can_place_order = is_market_open and has_sufficient_balance
should_execute_stop_loss = current_price <= stop_loss_trigger_price
```

### ✅ Collections
```python
# Initialize with type hints and descriptive names
active_positions: List[Position] = []
symbol_to_price_mapping: Dict[str, Decimal] = {}
failed_symbol_list: Set[str] = set()
pending_orders_queue: Queue[Order] = Queue()

# Never use generic names
data = []  # ❌ What kind of data?
items = {}  # ❌ What items?
```

## Function Parameter Patterns

### ✅ Required Parameters First
```python
def calculate_position_value(
    # Required parameters first
    symbol: str,
    quantity: int,
    current_price: Decimal,
    # Optional parameters after
    include_fees: bool = True,
    currency: str = 'INR',
    precision_digits: int = 2
) -> Decimal:
```

### ✅ Parameter Validation Block
```python
def process_trading_order(order_id: str, user_id: int, symbol: str) -> OrderResult:
    """Process trading order with complete validation."""
    
    # Parameter validation block - ALWAYS first
    if not order_id or not order_id.strip():
        raise ValueError("Order ID cannot be empty or whitespace")
    
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError(f"User ID must be positive integer, got: {user_id}")
    
    if not symbol or len(symbol) < 2:
        raise ValueError(f"Invalid trading symbol: {symbol}")
    
    # Normalize inputs
    order_id = order_id.strip().upper()
    symbol = symbol.strip().upper()
    
    # Business logic follows...
```

## API Call Patterns

### ✅ External API Calls
```python
async def fetch_stock_price_from_broker(symbol: str) -> Decimal:
    """Fetch current stock price with comprehensive error handling."""
    
    # Validate input
    if not symbol:
        raise ValueError("Symbol cannot be empty")
    
    # Prepare request with timeout
    request_timeout_seconds = 10
    max_retry_attempts = 3
    
    for attempt_number in range(1, max_retry_attempts + 1):
        try:
            logger.debug(f"Fetching price for {symbol}, attempt {attempt_number}")
            
            # Make API call with specific timeout
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=request_timeout_seconds)) as session:
                api_url = f"{BROKER_API_BASE_URL}/quotes/{symbol}"
                headers = {
                    'Authorization': f'Bearer {get_api_token()}',
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
                
                async with session.get(api_url, headers=headers) as response:
                    # Check HTTP status
                    if response.status == 200:
                        response_data = await response.json()
                        
                        # Validate response structure
                        if 'price' not in response_data:
                            raise APIResponseError(f"Missing price in response for {symbol}")
                        
                        # Convert to Decimal for precision
                        stock_price = Decimal(str(response_data['price']))
                        
                        logger.info(f"Successfully fetched price for {symbol}: {stock_price}")
                        return stock_price
                    
                    elif response.status == 404:
                        raise SymbolNotFoundError(f"Symbol {symbol} not found")
                    
                    elif response.status == 429:
                        # Rate limit - wait and retry
                        wait_seconds = 2 ** attempt_number
                        logger.warning(f"Rate limited, waiting {wait_seconds}s before retry")
                        await asyncio.sleep(wait_seconds)
                        continue
                    
                    else:
                        raise APIError(f"API returned status {response.status}")
        
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching price for {symbol}, attempt {attempt_number}")
            if attempt_number == max_retry_attempts:
                raise PriceUnavailableError(f"Timeout fetching price for {symbol} after {max_retry_attempts} attempts")
        
        except Exception as error:
            logger.error(f"Error fetching price for {symbol}: {error}")
            if attempt_number == max_retry_attempts:
                raise PriceUnavailableError(f"Failed to fetch price for {symbol}") from error
    
    # Should never reach here due to raises above
    raise PriceUnavailableError(f"Unable to fetch price for {symbol}")
```

## Database Query Patterns

### ✅ Database Operations
```python
def get_user_positions_from_database(user_id: int, include_closed: bool = False) -> List[Position]:
    """Retrieve user positions with proper error handling and logging."""
    
    # Validate input
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError(f"Invalid user_id: {user_id}")
    
    try:
        # Log operation start
        logger.debug(f"Querying positions for user {user_id}, include_closed={include_closed}")
        
        # Get database session
        with get_database_session() as db_session:
            # Build query with explicit conditions
            query = db_session.query(Position).filter(Position.user_id == user_id)
            
            # Add conditional filters
            if not include_closed:
                query = query.filter(Position.status.in_([PositionStatus.OPEN, PositionStatus.PARTIALLY_CLOSED]))
            
            # Order by most recent first
            query = query.order_by(Position.created_at.desc())
            
            # Execute query
            positions_list = query.all()
            
            # Log results
            logger.info(f"Found {len(positions_list)} positions for user {user_id}")
            
            return positions_list
    
    except SQLAlchemyError as db_error:
        logger.error(f"Database error querying positions for user {user_id}: {db_error}")
        raise DatabaseOperationError(f"Failed to retrieve positions for user {user_id}") from db_error
    
    except Exception as unexpected_error:
        logger.exception(f"Unexpected error querying positions for user {user_id}")
        raise DatabaseOperationError(f"Unexpected database error for user {user_id}") from unexpected_error
```

## Mathematical Calculation Patterns

### ✅ Financial Calculations
```python
def calculate_position_profit_loss(
    entry_price: Decimal,
    current_price: Decimal, 
    quantity: int,
    position_type: PositionType
) -> Decimal:
    """Calculate P&L with proper decimal precision and validation."""
    
    # Validate all inputs
    if entry_price <= 0:
        raise ValueError(f"Entry price must be positive: {entry_price}")
    
    if current_price <= 0:
        raise ValueError(f"Current price must be positive: {current_price}")
    
    if quantity == 0:
        raise ValueError("Quantity cannot be zero")
    
    if not isinstance(position_type, PositionType):
        raise ValueError(f"Invalid position type: {position_type}")
    
    try:
        # Calculate price difference
        price_difference = current_price - entry_price
        
        # Apply position type multiplier
        if position_type == PositionType.LONG:
            direction_multiplier = 1
        elif position_type == PositionType.SHORT:
            direction_multiplier = -1
        else:
            raise ValueError(f"Unsupported position type: {position_type}")
        
        # Calculate P&L with proper decimal arithmetic
        profit_loss = price_difference * Decimal(str(abs(quantity))) * direction_multiplier
        
        # Log calculation for debugging
        logger.debug(
            f"P&L calculation: ({current_price} - {entry_price}) * {quantity} * {direction_multiplier} = {profit_loss}"
        )
        
        return profit_loss
    
    except (InvalidOperation, DecimalException) as decimal_error:
        logger.error(f"Decimal calculation error: {decimal_error}")
        raise CalculationError("Failed to calculate position P&L due to decimal precision error") from decimal_error
```

## Loop Implementation Patterns

### ✅ Processing Collections
```python
def process_all_user_positions(positions: List[Position]) -> PositionSummary:
    """Process positions with proper error handling and progress tracking."""
    
    if not positions:
        logger.info("No positions to process")
        return PositionSummary.empty()
    
    # Initialize accumulators
    total_value = Decimal('0.00')
    processed_count = 0
    error_count = 0
    position_details = []
    
    logger.info(f"Starting to process {len(positions)} positions")
    
    # Process each position individually
    for position_index, current_position in enumerate(positions):
        try:
            # Log progress for large batches
            if len(positions) > 100 and position_index % 50 == 0:
                logger.info(f"Processing position {position_index + 1}/{len(positions)}")
            
            # Validate position data
            if not current_position.symbol:
                logger.warning(f"Skipping position with empty symbol at index {position_index}")
                error_count += 1
                continue
            
            # Calculate position value
            position_current_value = calculate_position_current_value(current_position)
            
            # Accumulate totals
            total_value += position_current_value
            processed_count += 1
            
            # Store details for summary
            position_detail = PositionDetail(
                symbol=current_position.symbol,
                quantity=current_position.quantity,
                current_value=position_current_value
            )
            position_details.append(position_detail)
            
        except PositionCalculationError as calc_error:
            logger.error(f"Failed to calculate value for position {current_position.symbol}: {calc_error}")
            error_count += 1
            continue
        
        except Exception as unexpected_error:
            logger.exception(f"Unexpected error processing position {current_position.symbol}")
            error_count += 1
            continue
    
    # Log final results
    logger.info(
        f"Position processing complete: {processed_count} successful, "
        f"{error_count} errors, total value: {total_value}"
    )
    
    return PositionSummary(
        total_value=total_value,
        processed_count=processed_count,
        error_count=error_count,
        position_details=position_details
    )
```

## Conditional Logic Patterns

### ✅ Complex Business Logic
```python
def determine_trading_action(
    current_price: Decimal,
    user_position: Position,
    market_conditions: MarketConditions,
    user_risk_profile: RiskProfile
) -> TradingAction:
    """Determine trading action based on multiple criteria."""
    
    # Early validation returns
    if current_price <= 0:
        return TradingAction.NO_ACTION_INVALID_PRICE
    
    if not user_position:
        return TradingAction.NO_ACTION_NO_POSITION
    
    # Calculate key metrics
    position_current_pnl = calculate_position_pnl(user_position, current_price)
    position_pnl_percentage = (position_current_pnl / user_position.invested_amount) * 100
    
    # Risk-based decision logic
    is_stop_loss_triggered = position_pnl_percentage <= -user_risk_profile.max_loss_percentage
    is_profit_target_reached = position_pnl_percentage >= user_risk_profile.profit_target_percentage
    is_market_volatile = market_conditions.volatility_index > VOLATILITY_THRESHOLD
    
    # Decision logic with clear priorities
    if is_stop_loss_triggered:
        logger.warning(
            f"Stop loss triggered for {user_position.symbol}: "
            f"P&L {position_pnl_percentage:.2f}% exceeds max loss {user_risk_profile.max_loss_percentage}%"
        )
        return TradingAction.SELL_STOP_LOSS
    
    elif is_profit_target_reached and not is_market_volatile:
        logger.info(
            f"Profit target reached for {user_position.symbol}: "
            f"P&L {position_pnl_percentage:.2f}% meets target {user_risk_profile.profit_target_percentage}%"
        )
        return TradingAction.SELL_PROFIT_TARGET
    
    elif is_market_volatile and position_pnl_percentage > 0:
        logger.info(
            f"Market volatile, securing profits for {user_position.symbol}: "
            f"Current P&L {position_pnl_percentage:.2f}%"
        )
        return TradingAction.SELL_SECURE_PROFITS
    
    else:
        # Hold position - log reasoning
        logger.debug(
            f"Holding position {user_position.symbol}: "
            f"P&L {position_pnl_percentage:.2f}%, "
            f"Volatility {market_conditions.volatility_index:.2f}"
        )
        return TradingAction.HOLD_POSITION
```

## CRITICAL IMPLEMENTATION RULES

### Every Line Must:
1. **Have Clear Intent**: Anyone should understand what it does
2. **Handle Failure**: What happens when it goes wrong?
3. **Be Testable**: Can you write a unit test for it?
4. **Be Reversible**: Can you undo its effects?
5. **Be Monitored**: Can you track its execution?

### Every Function Must:
1. **Validate Inputs**: Check all parameters at the start
2. **Handle Errors**: Catch and re-raise with context
3. **Log Actions**: Document what it's doing
4. **Return Consistently**: Same type for all code paths
5. **Be Single Purpose**: Do one thing well

### Every Variable Must:
1. **Self-Document**: Name explains its purpose
2. **Be Typed**: Clear type hints in Python
3. **Be Initialized**: Never use undefined variables
4. **Have Scope**: Minimal necessary scope
5. **Be Immutable**: When possible, prefer constants

**GOLDEN RULE**: If you can't explain why every single line exists and what happens if it fails, the code is not ready for production.