# Auto Trading System Documentation

This directory contains comprehensive documentation for the modular auto trading system with Kafka integration.

## Documentation Structure

### 🏗️ [Architecture](./architecture/)
- **[System Overview](./architecture/SYSTEM_OVERVIEW.md)** - Complete system architecture and design principles
- **[Data Flow](./architecture/DATA_FLOW.md)** - End-to-end data flow documentation
- **[Kafka Integration](./architecture/KAFKA_INTEGRATION.md)** - Kafka topics, producers, and consumers
- **[Modular Design](./architecture/MODULAR_DESIGN.md)** - Clean architecture implementation

### 🔧 [Components](./components/)
- **[Orchestrator](./components/ORCHESTRATOR.md)** - Central coordination system
- **[Position Monitor](./components/POSITION_MONITOR.md)** - Real-time PnL tracking
- **[PnL Calculator](./components/PNL_CALCULATOR.md)** - Advanced options calculations
- **[Risk Manager](./components/RISK_MANAGER.md)** - Risk management and circuit breakers
- **[Strategy Executor](./components/STRATEGY_EXECUTOR.md)** - Multi-strategy execution
- **[Execution Engine](./components/EXECUTION_ENGINE.md)** - Trade processing

### 🔗 [Integration](./integration/)
- **[Options Chain APIs](./integration/OPTIONS_CHAIN.md)** - Upstox and NSE integration
- **[Market Schedule](./integration/MARKET_SCHEDULE.md)** - Time-based automation
- **[SSE Streaming](./integration/SSE_STREAMING.md)** - Real-time UI updates
- **[Database Schema](./integration/DATABASE_SCHEMA.md)** - Data model documentation

### 🚀 [Deployment](./deployment/)
- **[Setup Guide](./deployment/SETUP_GUIDE.md)** - Installation and configuration
- **[Environment Config](./deployment/ENVIRONMENT_CONFIG.md)** - Environment variables
- **[Performance Tuning](./deployment/PERFORMANCE_TUNING.md)** - Optimization guidelines
- **[Monitoring](./deployment/MONITORING.md)** - Health checks and alerts

### 💡 [Examples](./examples/)
- **[Basic Usage](./examples/BASIC_USAGE.md)** - Getting started examples
- **[Advanced Scenarios](./examples/ADVANCED_SCENARIOS.md)** - Complex use cases
- **[API Examples](./examples/API_EXAMPLES.md)** - Code samples
- **[Configuration Examples](./examples/CONFIG_EXAMPLES.md)** - Setup configurations

## Quick Start

1. **Read System Overview**: Start with [System Overview](./architecture/SYSTEM_OVERVIEW.md) to understand the architecture
2. **Setup Environment**: Follow [Setup Guide](./deployment/SETUP_GUIDE.md) for installation
3. **Run Basic Example**: Try [Basic Usage](./examples/BASIC_USAGE.md) examples
4. **Configure Components**: Customize using [Configuration Examples](./examples/CONFIG_EXAMPLES.md)

## Key Features

✅ **Modular Architecture** - Clean separation of concerns  
✅ **Kafka Integration** - High-performance data processing  
✅ **Real-time PnL** - Sub-second position monitoring  
✅ **Risk Management** - Advanced circuit breakers  
✅ **Options Trading** - Complete F&O support  
✅ **Market Automation** - Schedule-based execution  
✅ **Multi-mode Trading** - Paper/Live/Simulation  
✅ **SSE Streaming** - Real-time UI updates  

## System Requirements

- **Python**: 3.8+
- **Kafka**: 2.8+ (3 brokers recommended)
- **Redis**: 6.0+ (for caching)
- **PostgreSQL**: 12+ (primary database)
- **Memory**: 2GB+ (4GB recommended)
- **CPU**: 4 cores (8 cores recommended)

## Support & Maintenance

For technical support and maintenance:
- Check component-specific documentation for troubleshooting
- Review monitoring guidelines for health checks
- Follow performance tuning recommendations for optimization

## Version Information

- **System Version**: 2.0.0
- **Architecture**: Modular Microservices
- **Integration**: Kafka + SSE
- **Last Updated**: 2025-01-11
- **Compatibility**: Python 3.8+, Kafka 2.8+