# Position Monitor

## Overview

The Position Monitor is a critical component that provides real-time position tracking and live PnL calculation for the auto trading system. It processes market data and trade executions to maintain accurate position states and streams updates to the UI with sub-second latency.

**Location**: `services/auto_trading/position_monitor.py`  
**Type**: Business Layer Component  
**Pattern**: Kafka Consumer + Event Publisher  
**Dependencies**: HFT Kafka, SSE Manager, PnL Calculator

## Architecture

### Class Structure

```python
class AutoTradingPositionMonitor(BaseHFTConsumer):
    """
    Real-time position monitor with Kafka integration.
    Monitors active positions, calculates live PnL, and streams
    updates to the UI via SSE channels.
    """
    
    def __init__(self)
    async def process_messages(self, messages: List[Dict[str, Any]]) -> None
    def get_user_positions(self, user_id: int) -> List[Position]
    def get_session_positions(self, session_id: str) -> List[Position]
    def get_performance_stats(self) -> Dict[str, Any]
```

### Core Data Structures

#### Position
```python
@dataclass
class Position:
    position_id: str
    user_id: int
    session_id: str
    instrument_key: str
    symbol: str
    position_type: PositionType
    quantity: int
    entry_price: Decimal
    current_price: Decimal
    entry_time: datetime
    
    # PnL calculations
    unrealized_pnl: Decimal = Decimal('0')
    realized_pnl: Decimal = Decimal('0')
    total_pnl: Decimal = Decimal('0')
    
    # Risk metrics
    max_profit: Decimal = Decimal('0')
    max_loss: Decimal = Decimal('0')
    break_even_price: Decimal = Decimal('0')
    
    # Status and metadata
    status: PositionStatus = PositionStatus.ACTIVE
    last_update: datetime = field(default_factory=datetime.now)
```

#### Position Types
```python
class PositionType(Enum):
    LONG_CALL = "long_call"
    SHORT_CALL = "short_call"
    LONG_PUT = "long_put"
    SHORT_PUT = "short_put"
```

#### Position Status
```python
class PositionStatus(Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    EXPIRED = "expired"
    ASSIGNED = "assigned"
    EXERCISED = "exercised"
```

## Core Features

### 1. Real-Time Position Tracking

The Position Monitor processes two types of Kafka messages:

#### Market Data Processing
```python
async def _process_price_updates(self, price_updates: List[Dict[str, Any]]) -> None:
    """Process price updates for position PnL calculation"""
    updated_positions = []
    
    for update in price_updates:
        if 'feeds' in update:
            feeds = update['feeds']
            
            for instrument_key, feed_data in feeds.items():
                # Find positions for this instrument
                matching_positions = [
                    pos for pos in self._active_positions.values()
                    if pos.instrument_key == instrument_key
                ]
                
                if matching_positions:
                    current_price = self._extract_current_price(feed_data)
                    
                    if current_price:
                        for position in matching_positions:
                            old_pnl = position.total_pnl
                            position.update_price(current_price)
                            
                            # Check if PnL change is significant
                            pnl_change = abs(position.total_pnl - old_pnl)
                            if pnl_change >= self._pnl_threshold:
                                updated_positions.append(position)
    
    # Broadcast significant updates
    if updated_positions:
        await self._broadcast_pnl_updates(updated_positions)
```

#### Trade Execution Processing
```python
async def _handle_trade_execution(self, execution: Dict[str, Any]) -> None:
    """Handle individual trade execution"""
    position_id = execution.get('position_id')
    action = execution.get('action', '').lower()
    
    if action == 'buy':
        # Create new position
        await self._create_position(execution)
    elif action == 'sell':
        # Close existing position
        await self._close_position(execution)
```

### 2. Position Lifecycle Management

#### Position Creation
```python
async def _create_position(self, execution: Dict[str, Any]) -> None:
    """Create new position from trade execution"""
    position = Position(
        position_id=execution['position_id'],
        user_id=execution['user_id'],
        session_id=execution['session_id'],
        instrument_key=execution['instrument_key'],
        symbol=execution.get('symbol', ''),
        position_type=self._get_position_type(execution),
        quantity=execution.get('quantity', 0),
        entry_price=Decimal(str(execution.get('price', 0))),
        current_price=Decimal(str(execution.get('price', 0))),
        entry_time=datetime.now()
    )
    
    # Store position
    self._active_positions[position.position_id] = position
    
    # Update tracking indexes
    self._update_tracking_indexes(position)
    
    # Broadcast position creation
    await self._broadcast_position_update(position, 'position_created')
```

#### Position Updates
```python
def update_price(self, new_price: Decimal) -> None:
    """Update position with new market price"""
    self.current_price = new_price
    self.last_update = datetime.now()
    
    # Calculate unrealized PnL based on position type
    if self.position_type in [PositionType.LONG_CALL, PositionType.LONG_PUT]:
        # Long positions: profit when price increases above entry
        self.unrealized_pnl = (new_price - self.entry_price) * self.quantity
    else:
        # Short positions: profit when price decreases below entry
        self.unrealized_pnl = (self.entry_price - new_price) * self.quantity
        
    self.total_pnl = self.unrealized_pnl + self.realized_pnl
    
    # Update max profit/loss tracking
    if self.total_pnl > self.max_profit:
        self.max_profit = self.total_pnl
    if self.total_pnl < self.max_loss:
        self.max_loss = self.total_pnl
```

#### Position Closure
```python
async def _close_position(self, execution: Dict[str, Any]) -> None:
    """Close existing position"""
    position_id = execution['position_id']
    
    if position_id in self._active_positions:
        position = self._active_positions[position_id]
        
        # Calculate final PnL
        exit_price = Decimal(str(execution.get('price', 0)))
        position.update_price(exit_price)
        position.realized_pnl = position.unrealized_pnl
        position.unrealized_pnl = Decimal('0')
        position.status = PositionStatus.CLOSED
        
        # Broadcast position closure
        await self._broadcast_position_update(position, 'position_closed')
        
        # Remove from active positions
        del self._active_positions[position_id]
        self._update_tracking_indexes_on_removal(position)
```

### 3. Real-Time PnL Streaming

#### Individual Position Updates
```python
async def _broadcast_position_update(self, position: Position, event_type: str) -> None:
    """Broadcast individual position update via SSE"""
    position_data = {
        'position_id': position.position_id,
        'user_id': position.user_id,
        'session_id': position.session_id,
        'symbol': position.symbol,
        'position_type': position.position_type.value,
        'quantity': position.quantity,
        'entry_price': float(position.entry_price),
        'current_price': float(position.current_price),
        'unrealized_pnl': float(position.unrealized_pnl),
        'realized_pnl': float(position.realized_pnl),
        'total_pnl': float(position.total_pnl),
        'status': position.status.value,
        'last_update': position.last_update.isoformat()
    }
    
    await self._sse_manager.broadcast_to_channel(
        channel=SSEChannel.TRADING_SIGNALS,
        event_type=event_type,
        data=position_data,
        priority=1  # High priority for position updates
    )
```

#### Batch PnL Updates
```python
async def _broadcast_pnl_updates(self, updated_positions: List[Position]) -> None:
    """Broadcast batch PnL updates with aggregation"""
    # Group by user and session for efficient updates
    user_updates = {}
    session_updates = {}
    
    for position in updated_positions:
        # User-level aggregation
        if position.user_id not in user_updates:
            user_updates[position.user_id] = {
                'total_pnl': Decimal('0'),
                'positions': [],
                'active_count': 0
            }
        
        user_data = user_updates[position.user_id]
        user_data['total_pnl'] += position.total_pnl
        user_data['positions'].append({
            'position_id': position.position_id,
            'symbol': position.symbol,
            'pnl': float(position.total_pnl)
        })
        user_data['active_count'] += 1
        
        # Session-level aggregation (similar logic)
    
    # Broadcast aggregated updates
    pnl_update_data = {
        'timestamp': datetime.now().isoformat(),
        'user_pnl': {
            str(user_id): {
                'total_pnl': float(data['total_pnl']),
                'active_positions': data['active_count'],
                'positions': data['positions']
            }
            for user_id, data in user_updates.items()
        },
        'session_pnl': {
            # Session aggregation data
        }
    }
    
    await self._sse_manager.broadcast_to_channel(
        channel=SSEChannel.TRADING_SIGNALS,
        event_type='live_pnl_update',
        data=pnl_update_data,
        priority=1
    )
```

### 4. Data Access Methods

#### User Position Queries
```python
def get_user_positions(self, user_id: int) -> List[Position]:
    """Get all active positions for a user"""
    if user_id not in self._user_positions:
        return []
    
    return [
        self._active_positions[pos_id]
        for pos_id in self._user_positions[user_id]
        if pos_id in self._active_positions
    ]
```

#### Session Position Queries
```python
def get_session_positions(self, session_id: str) -> List[Position]:
    """Get all positions for a trading session"""
    if session_id not in self._session_positions:
        return []
    
    return [
        self._active_positions[pos_id]
        for pos_id in self._session_positions[session_id]
        if pos_id in self._active_positions
    ]
```

## Performance Optimization

### Efficient Data Structures
- **Position Storage**: Hash maps for O(1) lookups
- **Index Maintenance**: Separate indexes for users and sessions
- **Memory Management**: Automatic cleanup of closed positions

### Batch Processing
```python
async def process_messages(self, messages: List[Dict[str, Any]]) -> None:
    """Process batch of messages from Kafka"""
    price_updates = []
    execution_updates = []
    
    # Categorize messages for batch processing
    for message in messages:
        message_type = message.get('type', '')
        if message_type == 'live_feed':
            price_updates.append(message)
        elif message_type == 'trade_execution':
            execution_updates.append(message)
    
    # Process in optimized order
    if execution_updates:
        await self._process_trade_executions(execution_updates)
    
    if price_updates:
        await self._process_price_updates(price_updates)
```

### Threshold-Based Updates
```python
# Configuration
self._update_interval_ms = 100  # 100ms updates
self._pnl_threshold = Decimal('0.01')  # Minimum change to broadcast

# Only broadcast significant changes
pnl_change = abs(position.total_pnl - old_pnl)
if pnl_change >= self._pnl_threshold:
    updated_positions.append(position)
```

## Usage Examples

### Basic Usage
```python
from services.auto_trading.position_monitor import get_position_monitor

# Get position monitor instance
monitor = await get_position_monitor()

# Start consuming (usually done by orchestrator)
await monitor.start_consuming()

# Get positions for a user
user_positions = monitor.get_user_positions(user_id=1)
for position in user_positions:
    print(f"{position.symbol}: ₹{position.total_pnl}")

# Get positions for a session
session_positions = monitor.get_session_positions(session_id="session_123")
```

### Performance Monitoring
```python
# Get performance statistics
stats = monitor.get_performance_stats()
print(f"Positions monitored: {stats['total_positions_monitored']}")
print(f"Active positions: {stats['active_positions']}")
print(f"PnL updates sent: {stats['pnl_updates_sent']}")
print(f"Last update: {stats['last_update_time']}")
```

### Custom Event Handling
```python
# The monitor automatically handles events, but you can access data:

# Get all active positions
all_positions = monitor._active_positions

# Get positions by instrument
instrument_positions = [
    pos for pos in all_positions.values()
    if pos.instrument_key == "NSE_EQ|INE318A01026"
]
```

## Integration Points

### Kafka Integration
**Consumes From**:
- `hft.analytics.market_data`: Real-time price updates
- `hft.trading.executions`: Trade execution events

**Message Processing**:
```python
def __init__(self):
    super().__init__(
        service_name="auto_trading_position_monitor",
        topics=["hft.analytics.market_data", "hft.trading.executions"],
        group_id="position_monitor_group"
    )
```

### SSE Integration
**Broadcasts To**:
- `TRADING_SIGNALS`: Position updates, PnL changes
- `SYSTEM_STATUS`: Error notifications (if needed)

### PnL Calculator Integration
The Position Monitor can integrate with the PnL Calculator for advanced calculations:

```python
from services.auto_trading.pnl_calculator import get_pnl_calculator

# Enhanced PnL calculation
pnl_calculator = get_pnl_calculator()
advanced_metrics = await pnl_calculator.calculate_position_pnl(
    position_id=position.position_id,
    entry_price=position.entry_price,
    current_price=position.current_price,
    quantity=position.quantity,
    position_type=position.position_type.value,
    entry_time=position.entry_time
)
```

## Error Handling

### Data Validation
```python
def _validate_execution_data(self, execution: Dict[str, Any]) -> bool:
    """Validate trade execution data"""
    required_fields = ['position_id', 'user_id', 'session_id', 'instrument_key']
    
    for field in required_fields:
        if field not in execution or not execution[field]:
            logger.warning(f"Missing required field: {field}")
            return False
    
    return True
```

### Price Extraction Safety
```python
def _extract_current_price(self, feed_data: Dict[str, Any]) -> Optional[Decimal]:
    """Safely extract current price from feed data"""
    try:
        full_feed = feed_data.get('fullFeed', {})
        market_data = full_feed.get('marketFF') or full_feed.get('indexFF')
        
        if market_data and 'ltpc' in market_data:
            ltp = market_data['ltpc'].get('ltp')
            if ltp and ltp > 0:
                return Decimal(str(ltp))
        
        return None
        
    except Exception as e:
        logger.error(f"Error extracting price: {e}")
        return None
```

### Connection Recovery
```python
async def _handle_kafka_error(self, error: Exception) -> None:
    """Handle Kafka connection errors"""
    logger.error(f"Kafka error in position monitor: {error}")
    
    # Attempt reconnection with exponential backoff
    for attempt in range(3):
        try:
            await asyncio.sleep(2 ** attempt)
            await self._consumer.start()
            logger.info("Position monitor Kafka connection restored")
            break
        except Exception as e:
            logger.warning(f"Reconnection attempt {attempt + 1} failed: {e}")
```

## Testing

### Unit Tests
```python
import pytest
from decimal import Decimal
from datetime import datetime

@pytest.fixture
def position_monitor():
    return AutoTradingPositionMonitor()

@pytest.mark.asyncio
async def test_position_creation(position_monitor):
    execution = {
        'position_id': 'test_pos_1',
        'user_id': 1,
        'session_id': 'session_1',
        'instrument_key': 'NSE_EQ|INE318A01026',
        'symbol': 'RELIANCE',
        'action': 'buy',
        'quantity': 50,
        'price': 2500.0
    }
    
    await position_monitor._create_position(execution)
    
    # Verify position was created
    assert 'test_pos_1' in position_monitor._active_positions
    position = position_monitor._active_positions['test_pos_1']
    assert position.symbol == 'RELIANCE'
    assert position.quantity == 50
    assert position.entry_price == Decimal('2500.0')

@pytest.mark.asyncio  
async def test_pnl_calculation(position_monitor):
    # Create position
    position = Position(
        position_id='test_pos',
        user_id=1,
        session_id='session_1',
        instrument_key='NSE_EQ|INE318A01026',
        symbol='RELIANCE',
        position_type=PositionType.LONG_CALL,
        quantity=50,
        entry_price=Decimal('2500.0'),
        current_price=Decimal('2500.0'),
        entry_time=datetime.now()
    )
    
    # Update price and verify PnL
    position.update_price(Decimal('2550.0'))
    expected_pnl = (Decimal('2550.0') - Decimal('2500.0')) * 50
    assert position.unrealized_pnl == expected_pnl
```

### Integration Tests
```python
@pytest.mark.asyncio
async def test_kafka_message_processing():
    monitor = AutoTradingPositionMonitor()
    
    # Mock Kafka messages
    market_data_message = {
        'type': 'live_feed',
        'feeds': {
            'NSE_EQ|INE318A01026': {
                'fullFeed': {
                    'marketFF': {
                        'ltpc': {'ltp': 2550.0}
                    }
                }
            }
        }
    }
    
    execution_message = {
        'type': 'trade_execution',
        'position_id': 'test_pos',
        'action': 'buy',
        'user_id': 1,
        'session_id': 'session_1',
        'instrument_key': 'NSE_EQ|INE318A01026',
        'quantity': 50,
        'price': 2500.0
    }
    
    # Process messages
    await monitor.process_messages([execution_message, market_data_message])
    
    # Verify position was created and updated
    positions = monitor.get_user_positions(1)
    assert len(positions) == 1
    assert positions[0].total_pnl > 0  # Should have profit
```

## Monitoring and Alerts

### Performance Metrics
```python
def get_performance_stats(self) -> Dict[str, Any]:
    """Get comprehensive performance statistics"""
    return {
        'total_positions_monitored': self._total_positions_monitored,
        'active_positions': len(self._active_positions),
        'pnl_updates_sent': self._pnl_updates_sent,
        'last_update_time': self._last_update_time.isoformat(),
        'users_tracked': len(self._user_positions),
        'sessions_tracked': len(self._session_positions),
        'avg_update_frequency': self._calculate_avg_update_frequency(),
        'memory_usage': self._estimate_memory_usage()
    }
```

### Health Checks
```python
def health_check(self) -> Dict[str, Any]:
    """Perform health check"""
    last_update_age = datetime.now() - self._last_update_time
    
    return {
        'status': 'healthy' if last_update_age.seconds < 30 else 'stale',
        'active_positions': len(self._active_positions),
        'last_update_seconds_ago': last_update_age.seconds,
        'kafka_consumer_running': self._is_running,
        'error_rate': self._calculate_error_rate()
    }
```

### Business Metrics
- **Position Accuracy**: Verification against broker records
- **PnL Accuracy**: Comparison with manual calculations
- **Update Latency**: Time from price change to UI update
- **Throughput**: Positions processed per second

The Position Monitor serves as the real-time heart of the trading system, providing accurate, low-latency position tracking and PnL calculation essential for effective trading operations.