# PnL Calculator Component

## Overview

The PnL Calculator is a sophisticated financial calculation engine designed for real-time profit and loss tracking in the Auto Trading System. It provides comprehensive PnL calculations with support for Indian market trading costs, options strategies, and real-time mark-to-market updates.

**Location**: `services/auto_trading/pnl_calculator.py`  
**Type**: Business Logic Component  
**Dependencies**: Position data, market prices, trading cost configurations

## Architecture

### Class Structure

```python
class AutoTradingPnLCalculator:
    """
    Advanced PnL calculation engine with comprehensive trading cost support.
    Handles real-time mark-to-market calculations for Indian markets.
    """
    
    def __init__(self, config: PnLCalculatorConfig)
    async def calculate_position_pnl(self, position: Position, current_price: Decimal) -> PnLMetrics
    async def calculate_portfolio_pnl(self, positions: List[Position]) -> PortfolioPnL
    async def calculate_session_pnl(self, session_id: str, positions: List[Dict]) -> Dict[str, Any]
    def calculate_trading_costs(self, trade_value: Decimal, is_options: bool) -> TradingCosts
```

### Configuration

```python
@dataclass
class PnLCalculatorConfig:
    """Configuration for PnL calculation parameters"""
    # Brokerage rates
    equity_brokerage_rate: Decimal = Decimal('0.0003')  # 0.03%
    options_brokerage_flat: Decimal = Decimal('20.0')   # ₹20 per lot
    
    # Exchange charges
    nse_transaction_charge: Decimal = Decimal('0.00325')  # 0.325%
    sebi_charges: Decimal = Decimal('0.000001')          # 0.0001%
    
    # Taxes
    gst_rate: Decimal = Decimal('0.18')                  # 18% GST
    stt_rate: Decimal = Decimal('0.00025')               # 0.025% for equity
    
    # Options specific
    options_stt_rate: Decimal = Decimal('0.0005')       # 0.05% for options
    options_transaction_charge: Decimal = Decimal('0.00053')  # 0.053%
    
    # Calculation precision
    precision_places: int = 2
    rounding_mode: str = ROUND_HALF_UP
```

## Core Features

### 1. Position PnL Calculation

The calculator provides comprehensive position-level PnL calculations:

```python
async def calculate_position_pnl(
    self, 
    position: Position, 
    current_price: Decimal
) -> PnLMetrics:
    """
    Calculate comprehensive PnL metrics for a single position.
    
    Args:
        position: Position object with entry details
        current_price: Current market price
        
    Returns:
        PnLMetrics with all calculated values
    """
    # 1. Calculate gross PnL based on position type
    if position.position_type in [PositionType.LONG_CALL, PositionType.LONG_PUT]:
        gross_pnl = (current_price - position.entry_price) * abs(position.quantity)
    elif position.position_type in [PositionType.SHORT_CALL, PositionType.SHORT_PUT]:
        gross_pnl = (position.entry_price - current_price) * abs(position.quantity)
    else:
        # Equity positions
        if position.quantity > 0:  # Long position
            gross_pnl = (current_price - position.entry_price) * position.quantity
        else:  # Short position
            gross_pnl = (position.entry_price - current_price) * abs(position.quantity)
    
    # 2. Calculate trading costs
    entry_value = position.entry_price * abs(position.quantity)
    exit_value = current_price * abs(position.quantity)
    
    entry_costs = self.calculate_trading_costs(
        entry_value, 
        position.position_type in [PositionType.LONG_CALL, PositionType.SHORT_CALL, 
                                 PositionType.LONG_PUT, PositionType.SHORT_PUT]
    )
    
    if position.status == PositionStatus.CLOSED:
        exit_costs = self.calculate_trading_costs(exit_value, position.is_options)
    else:
        # Estimate exit costs for unrealized PnL
        exit_costs = self.calculate_trading_costs(exit_value, position.is_options)
    
    # 3. Calculate net PnL
    total_costs = entry_costs.total_cost + exit_costs.total_cost
    net_pnl = gross_pnl - total_costs
    
    # 4. Calculate percentage return
    investment = entry_value + entry_costs.total_cost
    percentage_return = (net_pnl / investment * 100) if investment > 0 else Decimal('0')
    
    return PnLMetrics(
        position_id=position.position_id,
        gross_pnl=gross_pnl,
        net_pnl=net_pnl,
        percentage_return=percentage_return,
        total_costs=total_costs,
        entry_costs=entry_costs,
        exit_costs=exit_costs if position.status == PositionStatus.CLOSED else None,
        mark_to_market_price=current_price,
        calculation_timestamp=datetime.now()
    )
```

### 2. Portfolio PnL Aggregation

Portfolio-level calculations with risk metrics:

```python
async def calculate_portfolio_pnl(
    self, 
    positions: List[Position]
) -> PortfolioPnL:
    """
    Calculate comprehensive portfolio-level PnL metrics.
    
    Args:
        positions: List of all portfolio positions
        
    Returns:
        PortfolioPnL with aggregated metrics
    """
    if not positions:
        return PortfolioPnL.empty()
    
    # 1. Calculate individual position PnLs
    position_pnls = []
    for position in positions:
        current_price = await self._get_current_price(position.instrument_key)
        pnl = await self.calculate_position_pnl(position, current_price)
        position_pnls.append(pnl)
    
    # 2. Aggregate portfolio metrics
    total_gross_pnl = sum(pnl.gross_pnl for pnl in position_pnls)
    total_net_pnl = sum(pnl.net_pnl for pnl in position_pnls)
    total_investment = sum(
        pos.entry_price * abs(pos.quantity) for pos in positions
    )
    total_costs = sum(pnl.total_costs for pnl in position_pnls)
    
    # 3. Calculate portfolio-level metrics
    portfolio_return = (
        (total_net_pnl / total_investment * 100) 
        if total_investment > 0 else Decimal('0')
    )
    
    # 4. Risk metrics
    winning_positions = [pnl for pnl in position_pnls if pnl.net_pnl > 0]
    losing_positions = [pnl for pnl in position_pnls if pnl.net_pnl < 0]
    
    win_rate = (
        (len(winning_positions) / len(position_pnls) * 100) 
        if position_pnls else Decimal('0')
    )
    
    # 5. Drawdown calculation
    max_drawdown = await self._calculate_max_drawdown(position_pnls)
    
    return PortfolioPnL(
        total_positions=len(positions),
        total_gross_pnl=total_gross_pnl,
        total_net_pnl=total_net_pnl,
        portfolio_return=portfolio_return,
        total_investment=total_investment,
        total_costs=total_costs,
        winning_positions=len(winning_positions),
        losing_positions=len(losing_positions),
        win_rate=win_rate,
        max_drawdown=max_drawdown,
        position_pnls=position_pnls,
        calculation_timestamp=datetime.now()
    )
```

### 3. Trading Costs Calculation

Comprehensive Indian market trading costs:

```python
def calculate_trading_costs(
    self, 
    trade_value: Decimal, 
    is_options: bool = False
) -> TradingCosts:
    """
    Calculate comprehensive trading costs for Indian markets.
    
    Args:
        trade_value: Total value of the trade
        is_options: Whether this is an options trade
        
    Returns:
        TradingCosts with detailed breakdown
    """
    # 1. Brokerage calculation
    if is_options:
        # Options: Flat rate per lot (assuming 1 lot = trade_value/lot_size)
        brokerage = self.config.options_brokerage_flat
    else:
        # Equity: Percentage of trade value
        brokerage = trade_value * self.config.equity_brokerage_rate
    
    # 2. STT (Securities Transaction Tax)
    stt_rate = self.config.options_stt_rate if is_options else self.config.stt_rate
    stt = trade_value * stt_rate
    
    # 3. Exchange transaction charges
    transaction_rate = (
        self.config.options_transaction_charge if is_options 
        else self.config.nse_transaction_charge
    )
    transaction_charges = trade_value * transaction_rate
    
    # 4. SEBI charges
    sebi_charges = trade_value * self.config.sebi_charges
    
    # 5. GST on (brokerage + transaction charges + SEBI charges)
    taxable_amount = brokerage + transaction_charges + sebi_charges
    gst = taxable_amount * self.config.gst_rate
    
    # 6. Calculate total cost
    total_cost = brokerage + stt + transaction_charges + sebi_charges + gst
    
    return TradingCosts(
        brokerage=brokerage,
        stt=stt,
        transaction_charges=transaction_charges,
        sebi_charges=sebi_charges,
        gst=gst,
        total_cost=total_cost,
        trade_value=trade_value,
        is_options=is_options
    )
```

### 4. Session PnL Tracking

Real-time session-level PnL calculations:

```python
async def calculate_session_pnl(
    self, 
    session_id: str, 
    positions: List[Dict]
) -> Dict[str, Any]:
    """
    Calculate comprehensive session PnL with real-time updates.
    
    Args:
        session_id: Trading session identifier
        positions: List of position dictionaries
        
    Returns:
        Dictionary with session PnL metrics
    """
    if not positions:
        return {
            'session_id': session_id,
            'total_pnl': Decimal('0'),
            'realized_pnl': Decimal('0'),
            'unrealized_pnl': Decimal('0'),
            'total_trades': 0,
            'active_positions': 0,
            'calculation_time': datetime.now().isoformat()
        }
    
    # 1. Separate realized and unrealized positions
    closed_positions = [pos for pos in positions if pos['status'] == 'closed']
    open_positions = [pos for pos in positions if pos['status'] == 'open']
    
    # 2. Calculate realized PnL
    realized_pnl = Decimal('0')
    for position_dict in closed_positions:
        position = self._dict_to_position(position_dict)
        # For closed positions, use exit price
        pnl_metrics = await self.calculate_position_pnl(
            position, 
            position.exit_price or position.current_price
        )
        realized_pnl += pnl_metrics.net_pnl
    
    # 3. Calculate unrealized PnL
    unrealized_pnl = Decimal('0')
    for position_dict in open_positions:
        position = self._dict_to_position(position_dict)
        current_price = await self._get_current_price(position.instrument_key)
        pnl_metrics = await self.calculate_position_pnl(position, current_price)
        unrealized_pnl += pnl_metrics.net_pnl
    
    # 4. Calculate session metrics
    total_pnl = realized_pnl + unrealized_pnl
    total_trades = len(closed_positions)
    active_positions = len(open_positions)
    
    # 5. Additional session analytics
    winning_trades = len([pos for pos in closed_positions if pos.get('pnl', 0) > 0])
    losing_trades = len([pos for pos in closed_positions if pos.get('pnl', 0) < 0])
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    return {
        'session_id': session_id,
        'total_pnl': float(total_pnl),
        'realized_pnl': float(realized_pnl),
        'unrealized_pnl': float(unrealized_pnl),
        'total_trades': total_trades,
        'active_positions': active_positions,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': win_rate,
        'calculation_time': datetime.now().isoformat()
    }
```

## Data Models

### PnL Metrics

```python
@dataclass
class PnLMetrics:
    """Comprehensive PnL metrics for a single position"""
    position_id: str
    gross_pnl: Decimal
    net_pnl: Decimal
    percentage_return: Decimal
    total_costs: Decimal
    entry_costs: TradingCosts
    exit_costs: Optional[TradingCosts]
    mark_to_market_price: Decimal
    calculation_timestamp: datetime
    
    @property
    def is_profitable(self) -> bool:
        return self.net_pnl > Decimal('0')
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'position_id': self.position_id,
            'gross_pnl': float(self.gross_pnl),
            'net_pnl': float(self.net_pnl),
            'percentage_return': float(self.percentage_return),
            'total_costs': float(self.total_costs),
            'mark_to_market_price': float(self.mark_to_market_price),
            'is_profitable': self.is_profitable,
            'calculation_timestamp': self.calculation_timestamp.isoformat()
        }
```

### Trading Costs

```python
@dataclass
class TradingCosts:
    """Detailed breakdown of trading costs"""
    brokerage: Decimal
    stt: Decimal                    # Securities Transaction Tax
    transaction_charges: Decimal    # Exchange charges
    sebi_charges: Decimal          # SEBI regulatory charges
    gst: Decimal                   # GST on taxable charges
    total_cost: Decimal
    trade_value: Decimal
    is_options: bool
    
    def get_cost_breakdown_percentage(self) -> Dict[str, float]:
        """Get percentage breakdown of each cost component"""
        if self.total_cost == 0:
            return {}
        
        return {
            'brokerage_pct': float(self.brokerage / self.total_cost * 100),
            'stt_pct': float(self.stt / self.total_cost * 100),
            'transaction_charges_pct': float(self.transaction_charges / self.total_cost * 100),
            'sebi_charges_pct': float(self.sebi_charges / self.total_cost * 100),
            'gst_pct': float(self.gst / self.total_cost * 100)
        }
```

### Portfolio PnL

```python
@dataclass
class PortfolioPnL:
    """Portfolio-level PnL aggregation"""
    total_positions: int
    total_gross_pnl: Decimal
    total_net_pnl: Decimal
    portfolio_return: Decimal
    total_investment: Decimal
    total_costs: Decimal
    winning_positions: int
    losing_positions: int
    win_rate: Decimal
    max_drawdown: Decimal
    position_pnls: List[PnLMetrics]
    calculation_timestamp: datetime
    
    @classmethod
    def empty(cls) -> 'PortfolioPnL':
        """Create empty portfolio PnL for zero positions"""
        return cls(
            total_positions=0,
            total_gross_pnl=Decimal('0'),
            total_net_pnl=Decimal('0'),
            portfolio_return=Decimal('0'),
            total_investment=Decimal('0'),
            total_costs=Decimal('0'),
            winning_positions=0,
            losing_positions=0,
            win_rate=Decimal('0'),
            max_drawdown=Decimal('0'),
            position_pnls=[],
            calculation_timestamp=datetime.now()
        )
```

## Usage Examples

### Basic Position PnL Calculation

```python
from services.auto_trading.pnl_calculator import (
    AutoTradingPnLCalculator,
    PnLCalculatorConfig
)
from decimal import Decimal

# 1. Create calculator with default config
calculator = AutoTradingPnLCalculator(PnLCalculatorConfig())

# 2. Calculate PnL for a position
position = Position(
    position_id="pos_123",
    instrument_key="NSE_EQ|INE002A01018",
    position_type=PositionType.LONG,
    quantity=100,
    entry_price=Decimal('1500.50'),
    current_price=Decimal('1525.75'),
    status=PositionStatus.OPEN
)

current_price = Decimal('1525.75')
pnl_metrics = await calculator.calculate_position_pnl(position, current_price)

print(f"Gross PnL: ₹{pnl_metrics.gross_pnl}")
print(f"Net PnL: ₹{pnl_metrics.net_pnl}")
print(f"Return: {pnl_metrics.percentage_return}%")
print(f"Total Costs: ₹{pnl_metrics.total_costs}")
```

### Portfolio PnL Analysis

```python
# Calculate portfolio-level metrics
positions = [position1, position2, position3]
portfolio_pnl = await calculator.calculate_portfolio_pnl(positions)

print(f"Total Portfolio PnL: ₹{portfolio_pnl.total_net_pnl}")
print(f"Portfolio Return: {portfolio_pnl.portfolio_return}%")
print(f"Win Rate: {portfolio_pnl.win_rate}%")
print(f"Max Drawdown: {portfolio_pnl.max_drawdown}%")
```

### Options Trading PnL

```python
# Options position PnL calculation
options_position = Position(
    position_id="opt_456",
    instrument_key="NSE_FO|BANKNIFTY2341142700CE",
    position_type=PositionType.LONG_CALL,
    quantity=75,  # 1 lot
    entry_price=Decimal('125.50'),
    current_price=Decimal('145.25'),
    status=PositionStatus.OPEN
)

options_pnl = await calculator.calculate_position_pnl(
    options_position, 
    Decimal('145.25')
)

print(f"Options Gross PnL: ₹{options_pnl.gross_pnl}")
print(f"Options Net PnL: ₹{options_pnl.net_pnl}")
```

### Trading Costs Analysis

```python
# Detailed trading costs breakdown
trade_value = Decimal('100000')  # ₹1 lakh trade
costs = calculator.calculate_trading_costs(trade_value, is_options=False)

print("Trading Costs Breakdown:")
print(f"Brokerage: ₹{costs.brokerage}")
print(f"STT: ₹{costs.stt}")
print(f"Transaction Charges: ₹{costs.transaction_charges}")
print(f"SEBI Charges: ₹{costs.sebi_charges}")
print(f"GST: ₹{costs.gst}")
print(f"Total Cost: ₹{costs.total_cost}")

# Cost percentage breakdown
cost_breakdown = costs.get_cost_breakdown_percentage()
for component, percentage in cost_breakdown.items():
    print(f"{component}: {percentage:.2f}%")
```

## Integration Points

### Position Monitor Integration

The PnL Calculator integrates seamlessly with the Position Monitor:

```python
# In Position Monitor
async def _update_position_pnl(self, position: Position, new_price: Decimal) -> None:
    """Update position PnL when price changes"""
    pnl_metrics = await self._pnl_calculator.calculate_position_pnl(
        position, new_price
    )
    
    # Update position with new PnL
    position.unrealized_pnl = pnl_metrics.net_pnl
    position.percentage_return = pnl_metrics.percentage_return
    position.current_price = new_price
    
    # Broadcast update if significant change
    if self._is_significant_pnl_change(position, pnl_metrics):
        await self._broadcast_position_update(position, pnl_metrics)
```

### Kafka Message Processing

Real-time PnL updates via Kafka:

```python
async def process_price_update_messages(
    self, 
    messages: List[Dict[str, Any]]
) -> None:
    """Process price updates and calculate PnL"""
    for message in messages:
        instrument_key = message.get('instrument_key')
        new_price = Decimal(str(message.get('ltp', 0)))
        
        # Find positions for this instrument
        positions = self._get_positions_for_instrument(instrument_key)
        
        for position in positions:
            # Calculate updated PnL
            pnl_metrics = await self.calculate_position_pnl(position, new_price)
            
            # Create PnL update message
            pnl_update = {
                'session_id': position.session_id,
                'position_id': position.position_id,
                'pnl_metrics': pnl_metrics.to_dict(),
                'timestamp': datetime.now().isoformat()
            }
            
            # Publish to PnL update topic
            await self._kafka_producer.produce_message(
                topic='hft.trading.pnl_updates',
                message=pnl_update
            )
```

## Performance Considerations

### Optimization Strategies

1. **Batch Calculations**: Process multiple positions in batches
2. **Price Caching**: Cache market prices with TTL
3. **Calculation Caching**: Cache PnL results for unchanged positions
4. **Decimal Precision**: Use appropriate precision for calculations
5. **Memory Management**: Efficient data structure usage

### Calculation Performance

```python
class PnLCalculationOptimizer:
    """Optimization utilities for PnL calculations"""
    
    def __init__(self, cache_ttl: int = 1):
        self._price_cache = TTLCache(maxsize=1000, ttl=cache_ttl)
        self._pnl_cache = TTLCache(maxsize=500, ttl=5)
    
    async def get_optimized_position_pnl(
        self, 
        position: Position
    ) -> PnLMetrics:
        """Get PnL with caching optimization"""
        cache_key = f"{position.position_id}_{position.current_price}"
        
        if cache_key in self._pnl_cache:
            return self._pnl_cache[cache_key]
        
        # Calculate and cache
        pnl_metrics = await self._calculate_position_pnl(position)
        self._pnl_cache[cache_key] = pnl_metrics
        
        return pnl_metrics
```

## Error Handling

### Calculation Errors

```python
class PnLCalculationError(Exception):
    """Base exception for PnL calculation errors"""
    pass

class InvalidPositionError(PnLCalculationError):
    """Raised when position data is invalid"""
    pass

class PriceDataUnavailableError(PnLCalculationError):
    """Raised when current price data is unavailable"""
    pass

# Error handling in calculations
async def calculate_position_pnl_safe(
    self, 
    position: Position, 
    current_price: Decimal
) -> Optional[PnLMetrics]:
    """Safe PnL calculation with error handling"""
    try:
        if not position or not position.position_id:
            raise InvalidPositionError("Invalid position data")
        
        if current_price <= 0:
            raise ValueError("Current price must be positive")
        
        return await self.calculate_position_pnl(position, current_price)
        
    except Exception as e:
        logger.error(
            f"PnL calculation failed for position {position.position_id}: {e}"
        )
        return None
```

## Testing

### Unit Tests

```python
import pytest
from decimal import Decimal
from services.auto_trading.pnl_calculator import AutoTradingPnLCalculator

@pytest.mark.asyncio
async def test_equity_position_pnl():
    calculator = AutoTradingPnLCalculator(PnLCalculatorConfig())
    
    position = create_test_position(
        position_type=PositionType.LONG,
        quantity=100,
        entry_price=Decimal('1000'),
        current_price=Decimal('1100')
    )
    
    pnl_metrics = await calculator.calculate_position_pnl(
        position, Decimal('1100')
    )
    
    # Test gross PnL
    assert pnl_metrics.gross_pnl == Decimal('10000')  # (1100-1000)*100
    
    # Test net PnL includes trading costs
    assert pnl_metrics.net_pnl < pnl_metrics.gross_pnl
    assert pnl_metrics.total_costs > 0

@pytest.mark.asyncio
async def test_options_trading_costs():
    calculator = AutoTradingPnLCalculator(PnLCalculatorConfig())
    
    trade_value = Decimal('50000')
    costs = calculator.calculate_trading_costs(trade_value, is_options=True)
    
    # Options should use flat brokerage
    assert costs.brokerage == Decimal('20.0')
    assert costs.total_cost > costs.brokerage
```

The PnL Calculator provides comprehensive financial calculations with precise cost modeling for Indian markets, ensuring accurate real-time profit and loss tracking across the entire Auto Trading System.