# Intelligent Stock Selection Service - Test Suite

This directory contains a comprehensive test suite for the Intelligent Stock Selection Service using pytest.

## Test Structure

```
tests/
├── conftest.py                    # Pytest fixtures and configuration
├── unit/                         # Unit tests (isolated component testing)
│   ├── test_sentiment_analysis.py
│   ├── test_sector_strength.py
│   ├── test_scoring_algorithms.py
│   └── test_risk_assessment.py
├── integration/                  # Integration tests (component interaction)
│   └── test_intelligent_stock_integration.py
├── e2e/                         # End-to-end tests (complete user workflows)
│   └── test_intelligent_stock_e2e.py
└── performance/                 # Performance and benchmark tests
    └── test_intelligent_stock_performance.py
```

## Test Categories

### Unit Tests (`@pytest.mark.unit`)
- **test_sentiment_analysis.py**: Tests market sentiment analysis algorithms in isolation
- **test_sector_strength.py**: Tests sector strength calculation algorithms
- **test_scoring_algorithms.py**: Tests stock scoring and ranking algorithms
- **test_risk_assessment.py**: Tests risk assessment and validation algorithms

### Integration Tests (`@pytest.mark.integration`)
- **test_intelligent_stock_integration.py**: Tests integration between different service components

### End-to-End Tests (`@pytest.mark.e2e`)
- **test_intelligent_stock_e2e.py**: Tests complete user workflows and system integration

### Performance Tests (`@pytest.mark.performance`)
- **test_intelligent_stock_performance.py**: Tests performance benchmarks and scalability

## Running Tests

### Run All Tests
```bash
python -m pytest
```

### Run Specific Test Categories
```bash
# Unit tests only
python -m pytest -m unit

# Integration tests only
python -m pytest -m integration

# E2E tests only
python -m pytest -m e2e

# Performance tests only
python -m pytest -m performance

# Exclude slow tests
python -m pytest -m "not slow"
```

### Run Specific Test Files
```bash
python -m pytest tests/unit/test_sentiment_analysis.py
python -m pytest tests/integration/test_intelligent_stock_integration.py
```

### Run with Coverage
```bash
python -m pytest --cov=services --cov-report=html
```

### Run in Parallel (if pytest-xdist is installed)
```bash
python -m pytest -n auto
```

## Test Configuration

The test suite is configured via `pytest.ini`:

- **Coverage**: 80% minimum coverage requirement
- **Timeout**: 300 seconds maximum per test
- **Async Support**: Automatic asyncio mode
- **Markers**: Strict marker enforcement
- **Reporting**: HTML coverage reports in `htmlcov/`

## Fixtures

The `conftest.py` file provides comprehensive fixtures:

### Service Fixtures
- `intelligent_stock_service_with_mocks`: Fully mocked service for unit testing
- `clean_intelligent_stock_service`: Clean service instance for integration tests

### Data Fixtures
- `comprehensive_market_data`: Complete mock market data
- `mock_sector_performance_data`: Mock sector performance metrics
- `mock_sector_stocks_data`: Mock sector-stock mappings
- `sample_stock_for_scoring`: Sample stock data for algorithm testing

### Utility Fixtures
- `all_market_sentiments`: Parametrized market sentiment scenarios
- `all_trading_phases`: Parametrized trading phase scenarios
- `performance_benchmarks`: Performance threshold configurations

## Test Dependencies

Required packages:
```bash
pip install pytest pytest-asyncio pytest-cov pytest-timeout
```

Optional for parallel execution:
```bash
pip install pytest-xdist
```

## Performance Benchmarks

The test suite includes performance benchmarks:

- **Sentiment Analysis**: < 100ms
- **Sector Analysis**: < 50ms
- **Stock Selection**: < 200ms
- **Scoring Algorithm**: < 10ms per stock
- **Complete Workflow**: < 1000ms

## Best Practices

1. **Isolation**: Unit tests use mocks to isolate components
2. **Realistic Data**: Integration tests use realistic mock data
3. **Complete Workflows**: E2E tests cover complete user journeys
4. **Performance Monitoring**: Performance tests ensure scalability
5. **Error Scenarios**: Tests cover edge cases and error conditions
6. **Async Testing**: Proper async/await testing with pytest-asyncio
7. **Parametrization**: Test multiple scenarios using pytest.mark.parametrize

## Continuous Integration

The test suite is designed for CI/CD integration:

- Fast unit tests for quick feedback
- Comprehensive integration tests for quality assurance
- Performance tests to prevent regression
- Coverage reporting for code quality metrics

## Debugging Tests

### Run with Verbose Output
```bash
python -m pytest -v
```

### Run with Debug Output
```bash
python -m pytest -s
```

### Run Specific Test Method
```bash
python -m pytest tests/unit/test_sentiment_analysis.py::TestMarketSentimentAnalysis::test_sentiment_analysis_basic_functionality
```

### Profile Test Performance
```bash
python -m pytest --durations=10
```

## Contributing

When adding new functionality:

1. Add unit tests for new components
2. Add integration tests for component interactions
3. Update E2E tests for new user workflows
4. Add performance tests for performance-critical features
5. Ensure all tests pass and coverage remains above 80%