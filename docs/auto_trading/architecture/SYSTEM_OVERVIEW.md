# Auto Trading System - System Overview

## Introduction

The Auto Trading System is a production-ready, modular trading platform designed for Indian F&O markets. Built on clean architecture principles, it provides real-time trading capabilities with comprehensive risk management, advanced options support, and seamless Kafka integration.

## Architecture Principles

### Clean Architecture
The system follows Uncle Bob's Clean Architecture principles:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Presentation Layer                          │
│              (React UI, SSE Streaming)                         │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────┼───────────────────────────────────────────┐
│                 Application Layer                               │
│         (Orchestrator, Use Cases, DTOs)                        │
└─────────────────────┼───────────────────────────────────────────┘
                      │
┌─────────────────────┼───────────────────────────────────────────┐
│                  Business Layer                                 │
│    (Position Monitor, PnL Calculator, Risk Manager)            │
└─────────────────────┼───────────────────────────────────────────┘
                      │
┌─────────────────────┼───────────────────────────────────────────┐
│               Infrastructure Layer                              │
│      (Kafka, Database, APIs, WebSocket)                        │
└─────────────────────────────────────────────────────────────────┘
```

### SOLID Principles Implementation

**Single Responsibility**: Each component has one clear purpose
- `PositionMonitor` → Track positions and calculate PnL
- `RiskManager` → Evaluate and manage trading risks
- `PnLCalculator` → Calculate profit/loss metrics

**Open/Closed**: Easy to extend without modification
- New strategies can be added to `StrategyExecutor`
- Additional risk rules can be added to `RiskManager`

**Liskov Substitution**: Components are substitutable
- Any `BaseHFTConsumer` can replace another
- Different broker implementations are interchangeable

**Interface Segregation**: Focused interfaces
- `IAnalyticsCalculator` for analytics
- `IFeatureCalculator` for feature computation

**Dependency Inversion**: Depend on abstractions
- Components depend on interfaces, not implementations
- Easy mocking and testing

## System Components

### Core Components

#### 1. Auto Trading Orchestrator
**Location**: `services/auto_trading/orchestrator.py`  
**Purpose**: Central coordination of the entire trading workflow  
**Responsibilities**:
- System initialization and lifecycle management
- Phase-based execution workflow
- Component coordination
- Health monitoring and status reporting

#### 2. Position Monitor
**Location**: `services/auto_trading/position_monitor.py`  
**Purpose**: Real-time position tracking and PnL calculation  
**Responsibilities**:
- Kafka consumer for market data and trade executions
- Real-time PnL updates with sub-second latency
- Position lifecycle management
- SSE broadcasting for UI updates

#### 3. PnL Calculator
**Location**: `services/auto_trading/pnl_calculator.py`  
**Purpose**: Advanced profit/loss calculations  
**Responsibilities**:
- Mark-to-market PnL calculations
- Indian market cost calculations (brokerage, GST, charges)
- Options-specific calculations
- Portfolio-level aggregations

#### 4. Risk Manager
**Location**: `services/auto_trading/risk_manager.py`  
**Purpose**: Comprehensive risk management  
**Responsibilities**:
- Real-time risk monitoring
- Circuit breaker implementation
- Risk limit enforcement
- Emergency stop mechanisms

#### 5. Strategy Executor
**Location**: `services/auto_trading/kafka_strategy_executor.py`  
**Purpose**: Multi-strategy execution engine  
**Responsibilities**:
- Strategy signal processing
- Real-time strategy execution
- Performance tracking
- Dynamic strategy assignment

#### 6. Execution Engine
**Location**: `services/auto_trading/execution_engine.py`  
**Purpose**: Trade execution and order management  
**Responsibilities**:
- Order placement and management
- Execution reporting
- Broker integration
- Trade reconciliation

### Integration Components

#### Kafka Analytics System
**Purpose**: High-performance market data processing  
**Components**:
- `RealTimeAnalyticsEngine` - Market data processing
- `KafkaSSEBridge` - Real-time UI streaming
- `RealTimeStockSelector` - AI-driven stock selection

#### Market Data Infrastructure
**Purpose**: Live market data ingestion and distribution  
**Components**:
- `CentralizedWebSocketManager` - Data ingestion
- `HFTProducer` - High-frequency data publishing
- `InstrumentRegistry` - Symbol management

#### Options Trading Support
**Purpose**: Options chain data and analysis  
**Components**:
- `UpstoxOptionService` - Live options chain
- `OptionsAnalyzer` - Greeks and risk metrics
- `OptionsChain` - NSE fallback data

## Execution Workflow

### 7-Phase Trading Workflow

```
1. Premarket Analysis (09:00-09:15)
   ├── Market condition assessment
   ├── System health verification
   └── Strategy preparation

2. Stock Selection (09:15-09:25)
   ├── Kafka analytics consumption
   ├── AI-driven filtering
   └── Options chain analysis

3. Strategy Assignment (09:25-09:30)
   ├── Strategy-stock mapping
   ├── Risk parameter setting
   └── Position sizing

4. Trade Execution (09:30-15:30)
   ├── Real-time signal processing
   ├── Order placement
   └── Execution monitoring

5. Position Monitoring (Continuous)
   ├── Real-time PnL calculation
   ├── Position status updates
   └── UI streaming

6. Risk Management (Continuous)
   ├── Limit monitoring
   ├── Circuit breaker checks
   └── Emergency controls

7. Performance Tracking (End of day)
   ├── Session analytics
   ├── Performance metrics
   └── Reporting
```

### Data Flow Architecture

```
External Data Sources
         │
         ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Market Data     │───▶│ Kafka Analytics  │───▶│ Stock Selection │
│ (WebSocket)     │    │ System           │    │ Engine          │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Price Updates   │    │ Technical        │    │ Selected Stocks │
│ (Real-time)     │    │ Features         │    │ with Strategies │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Auto Trading Orchestrator                   │
└─────────────────────┬───────────────────────────────────────────┘
                      │
         ┌────────────┼────────────┐
         │            │            │
         ▼            ▼            ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ Strategy    │ │ Execution   │ │ Position    │
│ Executor    │ │ Engine      │ │ Monitor     │
└─────────────┘ └─────────────┘ └─────────────┘
         │            │            │
         └────────────┼────────────┘
                      │
                      ▼
         ┌────────────────────────────┐
         │         Risk Manager       │
         └────────────┬───────────────┘
                      │
                      ▼
         ┌────────────────────────────┐
         │      SSE Streaming         │
         │    (Real-time UI)          │
         └────────────────────────────┘
```

## Technology Stack

### Core Technologies
- **Python 3.8+**: Primary programming language
- **Apache Kafka**: High-performance message streaming
- **Redis**: Caching and session storage
- **PostgreSQL**: Primary database
- **WebSocket**: Real-time data ingestion
- **Server-Sent Events**: Real-time UI updates

### Libraries and Frameworks
- **aiokafka**: Asynchronous Kafka client
- **asyncio**: Asynchronous programming
- **pandas**: Data manipulation
- **numpy**: Numerical computing
- **sqlalchemy**: Database ORM
- **pydantic**: Data validation
- **fastapi**: Web framework (existing integration)

### External APIs
- **Upstox API**: Primary broker integration
- **NSE API**: Options chain fallback
- **Angel One API**: Additional broker support
- **Dhan API**: Additional broker support

## Performance Specifications

### Latency Requirements
| Component | Target Latency | Description |
|-----------|----------------|-------------|
| Market Data Processing | < 1ms | WebSocket to Kafka |
| Position PnL Updates | < 100ms | Price change to UI |
| Risk Evaluations | < 500ms | Risk check completion |
| Trade Executions | < 2 seconds | Signal to order placement |
| UI Updates | < 1 second | Data to user interface |

### Throughput Capabilities
| Metric | Capacity | Notes |
|--------|----------|-------|
| Positions Monitored | 1000+ | Simultaneous positions |
| PnL Calculations/sec | 100+ | Real-time calculations |
| Kafka Messages/sec | 10,000+ | High-frequency processing |
| Concurrent Users | 50+ | Multiple trading sessions |
| UI Updates/sec | 10 per channel | Real-time streaming |

### Resource Requirements
| Resource | Development | Production |
|----------|-------------|------------|
| Memory | 2GB | 8GB+ |
| CPU | 2 cores | 8 cores+ |
| Storage | 10GB | 100GB+ |
| Network | 10 Mbps | 100 Mbps+ |
| Database | SQLite | PostgreSQL Cluster |

## Security Architecture

### Authentication & Authorization
- JWT-based session management
- Role-based access control (Admin/Trader/Analyst)
- API key management for broker integrations
- Encrypted credential storage

### Data Protection
- TLS encryption for all API communications
- Database encryption at rest
- PII data anonymization
- Audit trail maintenance

### Trading Security
- Position limits enforcement
- Risk-based circuit breakers
- Emergency stop mechanisms
- Trade reconciliation

## Monitoring & Observability

### Health Monitoring
- Component health checks every 30 seconds
- System performance metrics collection
- Error rate monitoring and alerting
- Resource utilization tracking

### Business Metrics
- Trading performance KPIs
- PnL accuracy verification
- Execution quality metrics
- Risk exposure monitoring

### Logging Strategy
- Structured logging with correlation IDs
- Different log levels (DEBUG, INFO, WARN, ERROR)
- Centralized log aggregation
- Performance metrics logging

## Scalability Considerations

### Horizontal Scaling
- Multiple orchestrator instances per user
- Kafka partition-based load distribution
- Stateless component design
- Load balancer integration

### Vertical Scaling
- CPU-intensive components identification
- Memory optimization for large position sets
- Database query optimization
- Network bandwidth optimization

### Future Scaling Plans
- Microservices decomposition
- Container orchestration (Kubernetes)
- Event sourcing implementation
- CQRS pattern adoption

## Integration Points

### Existing System Integration
- **Unified WebSocket Manager**: Market data ingestion
- **Enhanced Market Analytics**: Technical analysis
- **Market Schedule Service**: Time-based automation
- **Instrument Registry**: Symbol management

### External System Integration
- **Broker APIs**: Trade execution
- **Market Data Providers**: Real-time feeds
- **Risk Management Systems**: Compliance
- **Reporting Systems**: Performance analytics

This system overview provides the foundation for understanding the complete auto trading architecture. For detailed component documentation, refer to the individual component guides in the [components](../components/) directory.