# Auto Trading Orchestrator

## Overview

The Auto Trading Orchestrator is the central coordination component that manages the complete auto trading workflow. It implements a 7-phase execution model, coordinates all system components, and provides comprehensive system health monitoring.

**Location**: `services/auto_trading/orchestrator.py`  
**Type**: Application Layer Component  
**Dependencies**: Kafka, SSE Manager, All Trading Components

## Architecture

### Class Structure

```python
class AutoTradingOrchestrator:
    """
    Central orchestrator for the complete auto trading system.
    Coordinates all components through a 7-phase workflow.
    """
    
    def __init__(self, config: AutoTradingSystemConfig)
    async def initialize_system(self) -> bool
    async def start_trading_session(self) -> bool
    async def stop_trading_session(self, reason: str) -> None
    def get_system_status(self) -> Dict[str, Any]
```

### Configuration

```python
@dataclass
class AutoTradingSystemConfig:
    user_id: int
    trading_mode: AutoTradingMode = AutoTradingMode.PAPER_TRADING
    max_positions: int = 5
    max_daily_loss: float = 5000.0
    position_size_percent: float = 2.0
    
    # Market timing
    premarket_start_time: str = "09:00"
    trading_start_time: str = "09:30"
    trading_end_time: str = "15:30"
    
    # Strategy configuration
    enable_fibonacci_strategy: bool = True
    enable_breakout_strategy: bool = True
    enable_momentum_strategy: bool = True
    
    # Risk management
    risk_profile: Optional[RiskProfile] = None
```

## Core Features

### 1. System Initialization

The orchestrator initializes all system components in the correct order:

```python
async def initialize_system(self) -> bool:
    """Initialize all auto trading components"""
    try:
        # 1. Initialize communication (Kafka + SSE)
        await self._initialize_communication()
        
        # 2. Initialize Kafka Analytics System
        await self._initialize_kafka_analytics()
        
        # 3. Initialize trading components
        await self._initialize_trading_components()
        
        # 4. Set up risk management
        await self._initialize_risk_management()
        
        # 5. Start monitoring tasks
        await self._start_monitoring_tasks()
        
        self.status = SystemStatus.RUNNING
        return True
        
    except Exception as e:
        logger.error(f"System initialization failed: {e}")
        await self._cleanup_on_failure()
        return False
```

**Initialization Sequence**:
1. **Communication Setup**: Kafka producer and SSE manager
2. **Analytics Integration**: Start Kafka analytics orchestrator
3. **Trading Components**: Position monitor, PnL calculator, risk manager
4. **Risk Configuration**: Set user-specific risk profiles
5. **Monitoring Tasks**: Health checks and performance tracking

### 2. 7-Phase Execution Workflow

The orchestrator manages trading through seven distinct phases:

#### Phase 1: Premarket Analysis (09:00-09:15)
```python
async def _premarket_analysis(self) -> None:
    """Execute premarket analysis phase"""
    analysis_data = {
        'phase': 'premarket_analysis',
        'market_conditions': await self._assess_market_conditions(),
        'system_health': await self._get_system_health(),
        'timestamp': datetime.now().isoformat()
    }
    
    await self._kafka_producer.produce_message(
        topic="hft.trading.phase_updates",
        message=analysis_data
    )
```

**Activities**:
- Market condition assessment
- System health verification
- Component readiness check
- Strategy preparation

#### Phase 2: Stock Selection (09:15-09:25)
```python
async def _stock_selection(self) -> None:
    """Execute stock selection using Kafka analytics"""
    selection_request = {
        'user_id': self.config.user_id,
        'session_id': self.session_id,
        'max_stocks': self.config.max_positions,
        'selection_criteria': {
            'enable_fibonacci': self.config.enable_fibonacci_strategy,
            'enable_breakout': self.config.enable_breakout_strategy,
            'enable_momentum': self.config.enable_momentum_strategy
        }
    }
    
    await self._kafka_producer.produce_message(
        topic="hft.trading.stock_selection_requests",
        message=selection_request
    )
```

**Activities**:
- Consume analytics from Kafka
- Apply selection criteria
- Options chain analysis
- Stock ranking and filtering

#### Phase 3: Strategy Assignment (09:25-09:30)
```python
async def _strategy_assignment(self) -> None:
    """Assign strategies to selected stocks"""
    await self._strategy_executor.assign_strategies_to_stocks()
```

**Activities**:
- Map strategies to selected stocks
- Configure strategy parameters
- Set position sizing rules
- Prepare for execution

#### Phase 4: Trade Execution (09:30-15:30)
```python
async def _trade_execution(self) -> None:
    """Activate continuous trade execution"""
    execution_status = {
        'phase': 'trade_execution',
        'session_id': self.session_id,
        'active': True,
        'timestamp': datetime.now().isoformat()
    }
    
    await self._kafka_producer.produce_message(
        topic="hft.trading.execution_status",
        message=execution_status
    )
```

**Activities**:
- Monitor strategy signals
- Execute trades based on signals
- Manage order lifecycle
- Handle execution confirmations

#### Phase 5: Position Monitoring (Continuous)
```python
async def _position_monitoring(self) -> None:
    """Monitor positions and calculate live PnL"""
    positions = self._position_monitor.get_session_positions(self.session_id)
    self._positions_monitored = len(positions)
```

**Activities**:
- Real-time position tracking
- PnL calculations
- Mark-to-market updates
- UI streaming

#### Phase 6: Risk Management (Continuous)
```python
async def _risk_management(self) -> None:
    """Execute continuous risk management"""
    positions = self._position_monitor.get_session_positions(self.session_id)
    
    if positions:
        portfolio_pnl = await self._pnl_calculator.calculate_session_pnl(
            self.session_id, [pos.__dict__ for pos in positions]
        )
        
        alerts = await self._risk_manager.evaluate_position_risk(
            self.config.user_id, self.session_id,
            [pos.__dict__ for pos in positions],
            portfolio_pnl.get('total_pnl', 0)
        )
```

**Activities**:
- Continuous risk evaluation
- Limit monitoring
- Circuit breaker checks
- Emergency controls

#### Phase 7: Performance Tracking (Continuous)
```python
async def _performance_tracking(self) -> None:
    """Track and analyze performance"""
    performance_data = {
        'session_id': self.session_id,
        'trades_executed': self._trades_executed,
        'positions_monitored': self._positions_monitored,
        'risk_alerts_handled': self._risk_alerts_handled
    }
    
    await self._kafka_producer.produce_message(
        topic="hft.trading.performance",
        message=performance_data
    )
```

**Activities**:
- Performance metrics collection
- Analytics and reporting
- Session summary generation
- Historical data storage

### 3. System Monitoring

The orchestrator runs multiple background monitoring tasks:

#### Health Monitoring
```python
async def _system_health_monitoring(self) -> None:
    """Continuous system health monitoring"""
    while self.status == SystemStatus.RUNNING:
        await asyncio.sleep(30)  # Check every 30 seconds
        
        health = await self._get_system_health()
        if not health['is_healthy']:
            await self._sse_manager.broadcast_to_channel(
                channel=SSEChannel.SYSTEM_STATUS,
                event_type="health_alert",
                data=health,
                priority=2
            )
```

**Monitored Components**:
- Kafka analytics system status
- Position monitor status
- Risk manager alerts count
- Component responsiveness

#### Phase Management
```python
async def _phase_management(self) -> None:
    """Manage trading phases based on market schedule"""
    while self.status == SystemStatus.RUNNING:
        current_time = datetime.now().time()
        
        # Determine appropriate phase based on market timing
        if current_time >= time(9, 0) and current_time < time(9, 15):
            await self._execute_phase(ExecutionPhase.PREMARKET_ANALYSIS)
        elif current_time >= time(9, 15) and current_time < time(9, 30):
            await self._execute_phase(ExecutionPhase.STOCK_SELECTION)
        # ... additional phase logic
```

#### Risk Monitoring
```python
async def _continuous_risk_monitoring(self) -> None:
    """Continuous risk monitoring with emergency stop capability"""
    while self.status == SystemStatus.RUNNING:
        await asyncio.sleep(5)  # Monitor every 5 seconds
        
        if self._risk_manager.is_session_emergency_stopped(self.session_id):
            logger.critical("Emergency stop detected - stopping session")
            await self.stop_trading_session("Emergency stop activated")
            break
```

### 4. System Status Tracking

#### System Status Enum
```python
class SystemStatus(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"
```

#### Status Information
```python
def get_system_status(self) -> Dict[str, Any]:
    """Get comprehensive system status"""
    return {
        'session_id': self.session_id,
        'user_id': self.config.user_id,
        'status': self.status.value,
        'current_phase': self.current_phase.value,
        'start_time': self.start_time.isoformat() if self.start_time else None,
        'trading_mode': self.config.trading_mode.value,
        'trades_executed': self._trades_executed,
        'positions_monitored': self._positions_monitored,
        'risk_alerts_handled': self._risk_alerts_handled,
        'active_tasks': len(self._orchestrator_tasks)
    }
```

## Usage Examples

### Basic Usage

```python
from services.auto_trading.orchestrator import (
    create_auto_trading_orchestrator,
    AutoTradingSystemConfig,
    AutoTradingMode
)
from services.auto_trading.risk_manager import RiskProfile
from decimal import Decimal

# 1. Create configuration
config = AutoTradingSystemConfig(
    user_id=1,
    trading_mode=AutoTradingMode.LIVE_TRADING,
    max_positions=5,
    max_daily_loss=5000.0,
    risk_profile=RiskProfile(
        user_id=1,
        max_daily_loss=Decimal('5000'),
        max_position_count=5
    )
)

# 2. Create orchestrator
orchestrator = create_auto_trading_orchestrator(config)

# 3. Initialize and start
async def main():
    if await orchestrator.initialize_system():
        success = await orchestrator.start_trading_session()
        if success:
            print(f"Trading session started: {orchestrator.session_id}")
        else:
            print("Failed to start trading session")
    else:
        print("System initialization failed")

# Run the system
asyncio.run(main())
```

### Advanced Configuration

```python
# Advanced configuration with all options
config = AutoTradingSystemConfig(
    user_id=1,
    trading_mode=AutoTradingMode.LIVE_TRADING,
    max_positions=3,
    max_daily_loss=2000.0,
    position_size_percent=1.5,
    
    # Custom market timing
    premarket_start_time="08:45",
    trading_start_time="09:30",
    trading_end_time="15:30",
    
    # Strategy selection
    enable_fibonacci_strategy=True,
    enable_breakout_strategy=False,  # Disable breakout
    enable_momentum_strategy=True,
    
    # Advanced risk profile
    risk_profile=RiskProfile(
        user_id=1,
        max_daily_loss=Decimal('2000'),
        max_position_count=3,
        max_position_size=Decimal('5000'),
        max_portfolio_exposure=Decimal('15000'),
        max_drawdown_percent=Decimal('8'),
        max_trades_per_hour=5,
        cooldown_period_minutes=10
    )
)
```

### Monitoring System Status

```python
# Get current system status
status = orchestrator.get_system_status()
print(f"Session: {status['session_id']}")
print(f"Status: {status['status']}")
print(f"Phase: {status['current_phase']}")
print(f"Trades: {status['trades_executed']}")
print(f"Positions: {status['positions_monitored']}")

# Check if system is running
if orchestrator.status == SystemStatus.RUNNING:
    print("System is actively trading")
```

### Graceful Shutdown

```python
# Stop trading session with reason
await orchestrator.stop_trading_session("Manual stop requested")

# Or emergency stop (handled by risk manager)
# This would be triggered automatically by risk conditions
```

## Integration Points

### Kafka Analytics Integration

The orchestrator integrates with the Kafka analytics system:

```python
async def _initialize_kafka_analytics(self) -> None:
    """Initialize Kafka analytics orchestrator"""
    self._kafka_analytics = await get_kafka_analytics_orchestrator()
    
    # Start analytics system if not running
    if not self._kafka_analytics.get_system_status()['is_running']:
        success = await self._kafka_analytics.start_system()
        if not success:
            raise Exception("Failed to start Kafka analytics system")
```

### Component Integration

All major components are initialized and coordinated:

```python
async def _initialize_trading_components(self) -> None:
    """Initialize all trading components"""
    # Stock selector (Kafka-integrated)
    self._stock_selector = await get_modular_stock_selector()
    
    # Strategy executor
    self._strategy_executor = KafkaStrategyExecutor(
        user_id=self.config.user_id,
        trading_mode=self.config.trading_mode
    )
    
    # Position monitor
    self._position_monitor = await get_position_monitor()
    
    # PnL calculator
    self._pnl_calculator = get_pnl_calculator()
    
    # Risk manager
    self._risk_manager = await get_risk_manager()
```

## Performance Considerations

### Resource Management
- **Memory**: Efficient task management with proper cleanup
- **CPU**: Asynchronous processing for all I/O operations
- **Network**: Batch Kafka message publishing

### Scalability
- **Horizontal**: Multiple orchestrator instances per user
- **Vertical**: Configurable monitoring intervals
- **Resource Limits**: Configurable position and exposure limits

## Error Handling

### Initialization Failures
```python
async def _cleanup_on_failure(self) -> None:
    """Cleanup on system initialization failure"""
    self.status = SystemStatus.ERROR
    
    # Stop running tasks
    for task in self._orchestrator_tasks:
        if not task.done():
            task.cancel()
    
    # Clear component references
    self._kafka_analytics = None
    self._position_monitor = None
```

### Runtime Errors
- **Component Failures**: Automatic restart and fallback
- **Network Issues**: Retry logic with exponential backoff
- **Data Inconsistencies**: Validation and sanitization

### Emergency Procedures
- **Emergency Stop**: Immediate session termination
- **Risk Breach**: Automatic risk management activation
- **System Failure**: Graceful degradation and notification

## Testing

### Unit Tests
```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_orchestrator_initialization():
    config = AutoTradingSystemConfig(user_id=1)
    orchestrator = AutoTradingOrchestrator(config)
    
    # Mock dependencies
    orchestrator._kafka_producer = AsyncMock()
    orchestrator._sse_manager = AsyncMock()
    
    # Test initialization
    result = await orchestrator.initialize_system()
    assert result == True
    assert orchestrator.status == SystemStatus.RUNNING
```

### Integration Tests
```python
@pytest.mark.asyncio
async def test_complete_workflow():
    # Test complete workflow from initialization to shutdown
    orchestrator = create_auto_trading_orchestrator(test_config)
    
    # Initialize
    assert await orchestrator.initialize_system()
    
    # Start session
    assert await orchestrator.start_trading_session()
    
    # Verify status
    status = orchestrator.get_system_status()
    assert status['status'] == 'running'
    
    # Stop session
    await orchestrator.stop_trading_session("Test completed")
    assert orchestrator.status == SystemStatus.STOPPED
```

## Monitoring and Alerts

### Health Metrics
- System initialization success rate
- Component availability
- Task completion rates
- Error frequencies

### Performance Metrics
- Phase execution times
- Message processing latency
- Resource utilization
- Trading session duration

### Business Metrics
- Trading session success rate
- Average positions per session
- PnL calculation accuracy
- Risk alert response time

The Auto Trading Orchestrator serves as the central nervous system of the entire auto trading platform, ensuring coordinated execution, comprehensive monitoring, and robust error handling across all system components.