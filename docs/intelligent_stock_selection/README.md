# Intelligent Stock Selection System

## Overview

The Intelligent Stock Selection System automatically selects stocks for options trading based on real-time market sentiment, sector performance, and technical analysis.

## Quick Links

- **[Overview & Architecture](01_overview_and_architecture.md)** - System design and data flow
- **[When & How It Runs](02_execution_workflow.md)** - Timing and execution workflow
- **[Database Schema](03_database_schema.md)** - Complete database structure and fields
- **[Market Sentiment Analysis](04_market_sentiment_analysis.md)** - How sentiment is calculated and used
- **[Options Trading Direction](05_options_trading_direction.md)** - CE/PE selection based on sentiment
- **[Stock Selection Criteria](06_stock_selection_criteria.md)** - Selection algorithm and scoring
- **[API Endpoints](07_api_endpoints.md)** - API reference and examples
- **[Configuration](08_configuration.md)** - Setup and configuration guide
- **[Troubleshooting](09_troubleshooting.md)** - Common issues and solutions

## Key Features

- ✅ Real-time market sentiment analysis from live WebSocket feed
- ✅ Automatic options direction (CE/PE) based on market conditions
- ✅ Complete market context stored in database
- ✅ Advance/Decline ratio and market breadth tracking
- ✅ Two-phase workflow: Premarket → Market Open Validation
- ✅ Integration with auto-trading system
- ✅ RESTful API for manual triggering and monitoring

## Quick Start

### 1. Run Database Migration

```bash
cd c:\Work\P\app\tradingapp-main\tradingapp-main
alembic upgrade head
```

### 2. Trigger Stock Selection

```bash
curl -X POST http://localhost:8000/api/v1/auto-trading/run-stock-selection \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. Check Results

```bash
curl http://localhost:8000/api/v1/auto-trading/selected-stocks \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## System Flow

```
Live Market Feed → Real-time Engine → Stock Selection → Database → Auto-Trading
```

See [Overview & Architecture](01_overview_and_architecture.md) for detailed flow.

## Market Sentiment → Options

| Market Condition | Sentiment | Options Direction |
|-----------------|-----------|-------------------|
| Strong Bull Market | very_bullish | **CE (CALL)** |
| Bull Market | bullish | **CE (CALL)** |
| Sideways Market | neutral | **CE (CALL)** |
| Bear Market | bearish | **PE (PUT)** |
| Strong Bear Market | very_bearish | **PE (PUT)** |

See [Options Trading Direction](05_options_trading_direction.md) for details.

## Documentation Structure

```
docs/intelligent_stock_selection/
├── README.md (this file)
├── 01_overview_and_architecture.md
├── 02_execution_workflow.md
├── 03_database_schema.md
├── 04_market_sentiment_analysis.md
├── 05_options_trading_direction.md
├── 06_stock_selection_criteria.md
├── 07_api_endpoints.md
├── 08_configuration.md
└── 09_troubleshooting.md
```

## Support

For issues or questions:
1. Check the [Troubleshooting Guide](09_troubleshooting.md)
2. Review the [API Documentation](07_api_endpoints.md)
3. Verify [Configuration](08_configuration.md)

---

**Last Updated**: January 2025
**Version**: 1.0.0