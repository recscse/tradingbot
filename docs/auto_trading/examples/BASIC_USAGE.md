# Basic Usage Examples

## Overview

This guide provides practical examples for using the Auto Trading System. These examples demonstrate common use cases from basic setup to advanced trading scenarios.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Basic Configuration](#basic-configuration)
3. [Starting Trading Session](#starting-trading-session)
4. [Monitoring Positions](#monitoring-positions)
5. [Risk Management](#risk-management)
6. [PnL Tracking](#pnl-tracking)
7. [Session Management](#session-management)
8. [Error Handling](#error-handling)

## Quick Start

### Minimal Setup

```python
import asyncio
from services.auto_trading.orchestrator import (
    create_auto_trading_orchestrator,
    AutoTradingSystemConfig,
    AutoTradingMode
)

async def quick_start():
    # 1. Create basic configuration
    config = AutoTradingSystemConfig(
        user_id=1,
        trading_mode=AutoTradingMode.PAPER_TRADING,  # Safe for testing
        max_positions=3,
        max_daily_loss=1000.0
    )
    
    # 2. Create orchestrator
    orchestrator = create_auto_trading_orchestrator(config)
    
    # 3. Initialize and start
    if await orchestrator.initialize_system():
        print("System initialized successfully")
        
        if await orchestrator.start_trading_session():
            print(f"Trading session started: {orchestrator.session_id}")
            
            # Let it run for a while
            await asyncio.sleep(60)
            
            # Stop gracefully
            await orchestrator.stop_trading_session("Quick start completed")
        else:
            print("Failed to start trading session")
    else:
        print("System initialization failed")

# Run the quick start
if __name__ == "__main__":
    asyncio.run(quick_start())
```

## Basic Configuration

### Paper Trading Configuration
```python
from services.auto_trading.orchestrator import AutoTradingSystemConfig
from services.auto_trading.risk_manager import RiskProfile
from decimal import Decimal

# Safe configuration for testing
paper_config = AutoTradingSystemConfig(
    user_id=1,
    trading_mode=AutoTradingMode.PAPER_TRADING,
    max_positions=5,
    max_daily_loss=2000.0,
    position_size_percent=2.0,  # 2% of capital per trade
    
    # Market timing (IST)
    premarket_start_time="09:00",
    trading_start_time="09:30",
    trading_end_time="15:30",
    
    # Enable all strategies
    enable_fibonacci_strategy=True,
    enable_breakout_strategy=True,
    enable_momentum_strategy=True,
    
    # Conservative risk profile
    risk_profile=RiskProfile(
        user_id=1,
        max_daily_loss=Decimal('2000'),
        max_position_count=5,
        max_position_size=Decimal('5000'),
        max_portfolio_exposure=Decimal('25000'),
        max_drawdown_percent=Decimal('10')
    )
)
```

### Live Trading Configuration
```python
# Production configuration for live trading
live_config = AutoTradingSystemConfig(
    user_id=1,
    trading_mode=AutoTradingMode.LIVE_TRADING,
    max_positions=3,  # Conservative position count
    max_daily_loss=5000.0,
    position_size_percent=1.5,  # Conservative sizing
    
    # Market timing
    premarket_start_time="09:00",
    trading_start_time="09:30",
    trading_end_time="15:30",
    
    # Strategy selection
    enable_fibonacci_strategy=True,
    enable_breakout_strategy=False,  # Disable for conservative approach
    enable_momentum_strategy=True,
    
    # Strict risk profile
    risk_profile=RiskProfile(
        user_id=1,
        max_daily_loss=Decimal('5000'),
        max_position_count=3,
        max_position_size=Decimal('10000'),
        max_portfolio_exposure=Decimal('30000'),
        max_drawdown_percent=Decimal('8'),
        max_trades_per_hour=5,  # Limit trade frequency
        cooldown_period_minutes=10
    )
)
```

## Starting Trading Session

### Basic Session Management
```python
async def start_trading_session_example():
    # Create configuration
    config = AutoTradingSystemConfig(user_id=1, max_daily_loss=1000.0)
    orchestrator = create_auto_trading_orchestrator(config)
    
    try:
        # Initialize system
        print("Initializing system...")
        if not await orchestrator.initialize_system():
            print("Failed to initialize system")
            return
        
        # Check system status before starting
        status = orchestrator.get_system_status()
        print(f"System Status: {status['status']}")
        print(f"Trading Mode: {status['trading_mode']}")
        
        # Start trading session
        print("Starting trading session...")
        if await orchestrator.start_trading_session():
            session_id = orchestrator.session_id
            print(f"Trading session started successfully: {session_id}")
            
            # Monitor session for some time
            await monitor_session(orchestrator, duration_minutes=30)
            
        else:
            print("Failed to start trading session")
            
    except Exception as e:
        print(f"Error during trading session: {e}")
    finally:
        # Always clean up
        await orchestrator.stop_trading_session("Session completed")
        print("Trading session stopped")

async def monitor_session(orchestrator, duration_minutes):
    """Monitor trading session for specified duration"""
    end_time = datetime.now() + timedelta(minutes=duration_minutes)
    
    while datetime.now() < end_time and orchestrator.status.value == 'running':
        # Get current status
        status = orchestrator.get_system_status()
        
        print(f"Status: {status['status']} | "
              f"Phase: {status['current_phase']} | "
              f"Trades: {status['trades_executed']} | "
              f"Positions: {status['positions_monitored']}")
        
        # Check every 30 seconds
        await asyncio.sleep(30)
```

### Session with Event Monitoring
```python
import json

async def start_session_with_monitoring():
    config = AutoTradingSystemConfig(user_id=1)
    orchestrator = create_auto_trading_orchestrator(config)
    
    # Set up event monitoring
    async def monitor_sse_events():
        """Monitor SSE events for real-time updates"""
        # Note: In practice, you'd use an SSE client
        print("SSE monitoring would capture:")
        print("- Position updates")
        print("- PnL changes")
        print("- Risk alerts")
        print("- System status changes")
    
    # Start monitoring task
    monitoring_task = asyncio.create_task(monitor_sse_events())
    
    try:
        # Initialize and start
        if await orchestrator.initialize_system():
            if await orchestrator.start_trading_session():
                print("Session started with real-time monitoring")
                
                # Run for specified duration
                await asyncio.sleep(300)  # 5 minutes
                
            await orchestrator.stop_trading_session("Monitoring complete")
    finally:
        monitoring_task.cancel()
```

## Monitoring Positions

### Real-Time Position Tracking
```python
from services.auto_trading.position_monitor import get_position_monitor

async def monitor_positions_example():
    # Get position monitor instance
    monitor = await get_position_monitor()
    
    # Get all positions for a user
    user_id = 1
    positions = monitor.get_user_positions(user_id)
    
    print(f"Found {len(positions)} positions for user {user_id}")
    
    for position in positions:
        print(f"""
        Position: {position.position_id}
        Symbol: {position.symbol}
        Type: {position.position_type.value}
        Quantity: {position.quantity}
        Entry Price: ₹{position.entry_price}
        Current Price: ₹{position.current_price}
        Unrealized PnL: ₹{position.unrealized_pnl}
        Total PnL: ₹{position.total_pnl}
        Status: {position.status.value}
        """)

async def monitor_session_positions():
    monitor = await get_position_monitor()
    session_id = "your_session_id_here"
    
    # Get positions for specific session
    session_positions = monitor.get_session_positions(session_id)
    
    # Calculate session totals
    total_pnl = sum(pos.total_pnl for pos in session_positions)
    total_positions = len(session_positions)
    winning_positions = len([pos for pos in session_positions if pos.total_pnl > 0])
    
    print(f"Session {session_id} Summary:")
    print(f"Total Positions: {total_positions}")
    print(f"Winning Positions: {winning_positions}")
    print(f"Win Rate: {(winning_positions/total_positions*100):.1f}%")
    print(f"Total PnL: ₹{total_pnl}")
```

### Position Performance Analysis
```python
async def analyze_position_performance():
    monitor = await get_position_monitor()
    positions = monitor.get_user_positions(user_id=1)
    
    # Analyze performance by position type
    performance_by_type = {}
    
    for position in positions:
        pos_type = position.position_type.value
        
        if pos_type not in performance_by_type:
            performance_by_type[pos_type] = {
                'count': 0,
                'total_pnl': Decimal('0'),
                'winning_count': 0
            }
        
        stats = performance_by_type[pos_type]
        stats['count'] += 1
        stats['total_pnl'] += position.total_pnl
        
        if position.total_pnl > 0:
            stats['winning_count'] += 1
    
    # Print analysis
    print("Performance by Position Type:")
    for pos_type, stats in performance_by_type.items():
        win_rate = (stats['winning_count'] / stats['count'] * 100) if stats['count'] > 0 else 0
        avg_pnl = stats['total_pnl'] / stats['count'] if stats['count'] > 0 else 0
        
        print(f"{pos_type}:")
        print(f"  Count: {stats['count']}")
        print(f"  Win Rate: {win_rate:.1f}%")
        print(f"  Average PnL: ₹{avg_pnl}")
        print(f"  Total PnL: ₹{stats['total_pnl']}")
```

## Risk Management

### Basic Risk Monitoring
```python
from services.auto_trading.risk_manager import get_risk_manager

async def monitor_risk():
    risk_manager = await get_risk_manager()
    
    # Get active risk alerts
    alerts = risk_manager.get_active_alerts(user_id=1)
    
    if alerts:
        print(f"Found {len(alerts)} active risk alerts:")
        
        for alert in alerts:
            print(f"""
            Alert ID: {alert.alert_id}
            Risk Level: {alert.risk_level.value}
            Type: {alert.risk_type}
            Message: {alert.message}
            Recommended Action: {alert.recommended_action.value}
            Current Value: {alert.current_value}
            Threshold: {alert.threshold_value}
            Time: {alert.timestamp.strftime('%H:%M:%S')}
            """)
    else:
        print("No active risk alerts")
    
    # Get risk summary
    risk_summary = risk_manager.get_risk_summary(user_id=1)
    print(f"\nRisk Summary:")
    print(f"Total Alerts: {risk_summary['total_alerts']}")
    print(f"Critical Alerts: {risk_summary['critical_alerts']}")
    print(f"High Alerts: {risk_summary['high_alerts']}")
    print(f"Emergency Stops: {risk_summary['emergency_stops']}")
```

### Custom Risk Profile Setup
```python
async def setup_custom_risk_profile():
    from services.auto_trading.risk_manager import RiskProfile
    from decimal import Decimal
    
    risk_manager = await get_risk_manager()
    
    # Create custom risk profile
    custom_profile = RiskProfile(
        user_id=1,
        max_daily_loss=Decimal('3000'),    # ₹3,000 max daily loss
        max_position_count=4,               # Maximum 4 positions
        max_position_size=Decimal('8000'),  # ₹8,000 per position
        max_portfolio_exposure=Decimal('32000'),  # Total exposure limit
        max_drawdown_percent=Decimal('12'), # 12% max drawdown
        position_correlation_limit=Decimal('0.6'),  # 60% correlation limit
        max_trades_per_hour=8,             # Trade frequency limit
        cooldown_period_minutes=5          # Cool down after losses
    )
    
    # Set the risk profile
    risk_manager.set_user_risk_profile(user_id=1, risk_profile=custom_profile)
    print("Custom risk profile configured successfully")
    
    # Verify the profile
    profile = risk_manager.get_user_risk_profile(user_id=1)
    print(f"Max Daily Loss: ₹{profile.max_daily_loss}")
    print(f"Max Positions: {profile.max_position_count}")
    print(f"Risk Limits: {len(profile.risk_limits)} configured")
```

## PnL Tracking

### Basic PnL Calculations
```python
from services.auto_trading.pnl_calculator import get_pnl_calculator
from decimal import Decimal
from datetime import datetime

async def calculate_pnl_example():
    pnl_calculator = get_pnl_calculator()
    
    # Calculate PnL for a single position
    pnl_metrics = await pnl_calculator.calculate_position_pnl(
        position_id="pos_123",
        entry_price=Decimal('2500.0'),
        current_price=Decimal('2575.0'),
        quantity=50,
        position_type="long_call",
        entry_time=datetime.now(),
        is_closed=False
    )
    
    print("Position PnL Analysis:")
    print(f"Gross PnL: ₹{pnl_metrics.gross_pnl}")
    print(f"Trading Costs: ₹{pnl_metrics.brokerage}")
    print(f"Net PnL: ₹{pnl_metrics.net_pnl}")
    print(f"Return %: {pnl_metrics.percentage_return}%")
    print(f"Max Profit: ₹{pnl_metrics.max_profit}")
    print(f"Max Loss: ₹{pnl_metrics.max_loss}")
```

### Portfolio PnL Analysis
```python
async def analyze_portfolio_pnl():
    pnl_calculator = get_pnl_calculator()
    
    # Sample positions data
    positions = [
        {
            'position_id': 'pos_1',
            'entry_price': 2500.0,
            'current_price': 2575.0,
            'quantity': 50,
            'position_type': 'long_call',
            'entry_time': datetime.now(),
            'status': 'active'
        },
        {
            'position_id': 'pos_2',
            'entry_price': 1800.0,
            'current_price': 1750.0,
            'quantity': 25,
            'position_type': 'long_put',
            'entry_time': datetime.now(),
            'status': 'active'
        }
    ]
    
    # Calculate portfolio PnL
    portfolio_pnl = await pnl_calculator.calculate_portfolio_pnl(
        positions=positions,
        user_id=1
    )
    
    print("Portfolio Analysis:")
    print(f"Total PnL: ₹{portfolio_pnl['total_pnl']}")
    print(f"Total Return %: {portfolio_pnl['total_percentage']:.2f}%")
    print(f"Total Investment: ₹{portfolio_pnl['total_investment']}")
    print(f"Total Positions: {portfolio_pnl['positions_count']}")
    print(f"Winning Positions: {portfolio_pnl['winning_positions']}")
    print(f"Win Rate: {portfolio_pnl['win_rate']:.1f}%")
    
    # Detailed position breakdown
    print("\nPosition Details:")
    for pos_detail in portfolio_pnl['position_details']:
        print(f"  {pos_detail['position_id']}: ₹{pos_detail['pnl']} ({pos_detail['percentage']:.2f}%)")
```

### Session PnL Tracking
```python
async def track_session_pnl():
    pnl_calculator = get_pnl_calculator()
    monitor = await get_position_monitor()
    
    session_id = "session_123"
    positions = monitor.get_session_positions(session_id)
    
    if positions:
        # Convert positions to dictionary format
        positions_data = [
            {
                'position_id': pos.position_id,
                'entry_price': float(pos.entry_price),
                'current_price': float(pos.current_price),
                'quantity': pos.quantity,
                'position_type': pos.position_type.value,
                'entry_time': pos.entry_time,
                'status': pos.status.value
            }
            for pos in positions
        ]
        
        # Calculate session PnL
        session_pnl = await pnl_calculator.calculate_session_pnl(
            session_id=session_id,
            positions=positions_data
        )
        
        print(f"Session {session_id} PnL Analysis:")
        print(f"Total PnL: ₹{session_pnl['total_pnl']}")
        print(f"Session Duration: {session_pnl['session_duration_minutes']:.1f} minutes")
        print(f"PnL per Minute: ₹{session_pnl['pnl_per_minute']:.2f}")
        print(f"Average PnL per Position: ₹{session_pnl['avg_pnl_per_position']:.2f}")
    else:
        print(f"No positions found for session {session_id}")
```

## Session Management

### Session Lifecycle Management
```python
class TradingSessionManager:
    def __init__(self):
        self.orchestrator = None
        self.session_start_time = None
    
    async def start_session(self, config: AutoTradingSystemConfig):
        """Start a new trading session"""
        try:
            self.orchestrator = create_auto_trading_orchestrator(config)
            self.session_start_time = datetime.now()
            
            print(f"Starting trading session at {self.session_start_time}")
            
            # Initialize system
            if await self.orchestrator.initialize_system():
                print("System initialized successfully")
                
                # Start trading
                if await self.orchestrator.start_trading_session():
                    session_id = self.orchestrator.session_id
                    print(f"Trading session active: {session_id}")
                    return session_id
                else:
                    print("Failed to start trading session")
                    return None
            else:
                print("System initialization failed")
                return None
                
        except Exception as e:
            print(f"Error starting session: {e}")
            return None
    
    async def stop_session(self, reason: str = "Manual stop"):
        """Stop the current trading session"""
        if self.orchestrator:
            await self.orchestrator.stop_trading_session(reason)
            
            session_duration = datetime.now() - self.session_start_time
            print(f"Session stopped after {session_duration}")
            
            # Get final statistics
            status = self.orchestrator.get_system_status()
            print(f"Final Stats - Trades: {status['trades_executed']}, "
                  f"Positions: {status['positions_monitored']}")
    
    def get_session_status(self):
        """Get current session status"""
        if self.orchestrator:
            return self.orchestrator.get_system_status()
        return None

# Usage
async def session_management_example():
    session_manager = TradingSessionManager()
    
    # Configure session
    config = AutoTradingSystemConfig(
        user_id=1,
        trading_mode=AutoTradingMode.PAPER_TRADING,
        max_positions=3,
        max_daily_loss=2000.0
    )
    
    # Start session
    session_id = await session_manager.start_session(config)
    
    if session_id:
        try:
            # Run session for specified time
            await asyncio.sleep(600)  # 10 minutes
            
            # Check status periodically
            status = session_manager.get_session_status()
            print(f"Current phase: {status['current_phase']}")
            
        finally:
            # Always clean up
            await session_manager.stop_session("Example completed")
```

## Error Handling

### Robust Error Handling
```python
async def robust_trading_session():
    """Example with comprehensive error handling"""
    orchestrator = None
    
    try:
        # Configuration with validation
        config = AutoTradingSystemConfig(
            user_id=1,
            trading_mode=AutoTradingMode.PAPER_TRADING,
            max_positions=3,
            max_daily_loss=1000.0
        )
        
        # Validate configuration
        if config.max_daily_loss <= 0:
            raise ValueError("Max daily loss must be positive")
        
        if config.max_positions <= 0:
            raise ValueError("Max positions must be positive")
        
        orchestrator = create_auto_trading_orchestrator(config)
        
        # Initialize with retry logic
        max_init_attempts = 3
        for attempt in range(max_init_attempts):
            try:
                if await orchestrator.initialize_system():
                    print(f"System initialized on attempt {attempt + 1}")
                    break
                else:
                    print(f"Initialization attempt {attempt + 1} failed")
                    if attempt == max_init_attempts - 1:
                        raise Exception("All initialization attempts failed")
                    await asyncio.sleep(5)  # Wait before retry
            except Exception as e:
                print(f"Initialization error on attempt {attempt + 1}: {e}")
                if attempt == max_init_attempts - 1:
                    raise
                await asyncio.sleep(5)
        
        # Start session with monitoring
        if await orchestrator.start_trading_session():
            print("Session started successfully")
            
            # Monitor session with error handling
            await monitor_session_with_error_handling(orchestrator)
            
        else:
            raise Exception("Failed to start trading session")
    
    except ValueError as e:
        print(f"Configuration error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
        # Log error for debugging
        import traceback
        traceback.print_exc()
    
    finally:
        # Always clean up resources
        if orchestrator:
            try:
                await orchestrator.stop_trading_session("Error handling cleanup")
                print("Session stopped safely")
            except Exception as e:
                print(f"Error during cleanup: {e}")

async def monitor_session_with_error_handling(orchestrator):
    """Monitor session with comprehensive error handling"""
    monitoring_errors = 0
    max_errors = 5
    
    while orchestrator.status.value == 'running' and monitoring_errors < max_errors:
        try:
            # Get system status
            status = orchestrator.get_system_status()
            
            # Check for error conditions
            if status['status'] == 'error':
                print("System error detected, stopping session")
                break
            
            # Monitor risk alerts
            risk_manager = await get_risk_manager()
            alerts = risk_manager.get_active_alerts(user_id=status['user_id'])
            
            critical_alerts = [a for a in alerts if a.risk_level.value == 'critical']
            if critical_alerts:
                print(f"Critical risk alerts detected: {len(critical_alerts)}")
                for alert in critical_alerts:
                    print(f"  - {alert.message}")
            
            # Check position monitor health
            monitor = await get_position_monitor()
            monitor_stats = monitor.get_performance_stats()
            
            # Print status
            print(f"Status: {status['status']} | "
                  f"Phase: {status['current_phase']} | "
                  f"Positions: {monitor_stats['active_positions']}")
            
            # Reset error count on successful monitoring
            monitoring_errors = 0
            
            # Wait before next check
            await asyncio.sleep(30)
            
        except Exception as e:
            monitoring_errors += 1
            print(f"Monitoring error {monitoring_errors}/{max_errors}: {e}")
            
            if monitoring_errors >= max_errors:
                print("Too many monitoring errors, stopping session")
                break
            
            # Exponential backoff
            await asyncio.sleep(2 ** monitoring_errors)

# Run the robust example
if __name__ == "__main__":
    asyncio.run(robust_trading_session())
```

### Connection Recovery Example
```python
async def connection_recovery_example():
    """Example showing connection recovery patterns"""
    
    async def with_retry(coro_func, max_attempts=3, delay=1):
        """Generic retry wrapper"""
        for attempt in range(max_attempts):
            try:
                return await coro_func()
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt == max_attempts - 1:
                    raise
                await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff
    
    # Example with position monitor
    async def get_positions_with_retry():
        monitor = await get_position_monitor()
        return monitor.get_user_positions(user_id=1)
    
    try:
        positions = await with_retry(get_positions_with_retry, max_attempts=3)
        print(f"Retrieved {len(positions)} positions")
    except Exception as e:
        print(f"Failed to retrieve positions after retries: {e}")
```

These examples provide a solid foundation for using the Auto Trading System. Start with the quick start example and gradually work through the more advanced scenarios as you become familiar with the system.