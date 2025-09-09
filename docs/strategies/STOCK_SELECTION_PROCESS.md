# Stock Selection Process Documentation

## Overview

The Automated Stock Selection Service (`services/auto_stock_selection_service.py`) is responsible for intelligently selecting stocks for algorithmic trading based on multiple criteria including ADR analysis, market sentiment, sector momentum, and technical indicators.

## Selection Flow

### 1. Initialization & Configuration

```python
class AutoStockSelectionService:
    def __init__(self, user_id: int = 1):
        # Core Configuration
        self.max_stocks_to_select = 2           # Focus on quality over quantity
        self.sectors_to_analyze = 1             # Top performing sector only
        self.min_volume_threshold = 100000      # Minimum daily volume
        self.min_adr_correlation = 0.3          # ADR correlation threshold
```

### 2. Selection Criteria & Scoring

#### A. Volume & Liquidity Requirements
```python
fno_selection_config = {
    'volume_threshold': 100000,         # Daily volume > 1L
    'option_liquidity': {
        'min_oi': 10000,               # Open Interest > 10K
        'bid_ask_spread': 0.05         # Max 5 paisa spread
    },
    'price_range': {
        'min_price': 50,
        'max_price': 5000
    }
}
```

#### B. Market Sentiment Analysis
- **Bullish Market**: Selects Call Options (CE)
- **Bearish Market**: Selects Put Options (PE)
- **Neutral Market**: Focus on high probability setups

#### C. ADR (American Depositary Receipt) Analysis
- Analyzes overnight US market performance
- Correlates with Indian stock performance
- Minimum correlation threshold: 0.3

#### D. Sector Momentum Evaluation
- Identifies top performing sectors
- Focuses on sector leaders with strong momentum
- Uses relative strength comparison

### 3. Technical Scoring Formula

```python
@dataclass
class StockSelectionResult:
    symbol: str
    sector: str
    selection_score: float              # Composite score (0-100)
    selection_reason: str
    price_at_selection: float
    option_type: str                    # CE/PE/NEUTRAL
    adr_score: float                    # ADR correlation (0-1)
    sector_momentum: float              # Sector strength (0-1)
    volume_score: float                 # Volume analysis (0-1)
    technical_score: float              # Technical indicators (0-1)
    market_sentiment_alignment: bool
```

#### Composite Scoring Algorithm:
```python
selection_score = (
    adr_score * 0.25 +                 # 25% weight to ADR correlation
    sector_momentum * 0.30 +           # 30% weight to sector performance
    volume_score * 0.20 +              # 20% weight to volume analysis
    technical_score * 0.25             # 25% weight to technical indicators
) * 100
```

### 4. Live Feed Integration

#### Data Source Connection
```python
# Live market data processing
from services.high_speed_market_data import high_speed_market_data
from services.live_adapter import live_feed_adapter

# Real-time price updates for selection validation
def validate_selection_prices(self, selected_stocks: List[StockSelectionResult]):
    for stock in selected_stocks:
        current_price = live_feed_adapter.get_live_price(stock.symbol)
        # Validate price movement within acceptable range
        price_change = abs(current_price - stock.price_at_selection) / stock.price_at_selection
        if price_change > 0.02:  # 2% price movement threshold
            # Re-evaluate selection
```

### 5. Selection Process Execution

#### Timing & Scheduling
- **Execution Time**: 9:00 AM IST (Pre-market)
- **Duration**: 5-8 minutes before market open
- **Frequency**: Daily during trading days

#### Step-by-Step Process
```python
async def run_stock_selection(self) -> List[StockSelectionResult]:
    """Complete stock selection process"""
    
    # Step 1: Market Analysis
    market_sentiment = await self._analyze_market_sentiment()
    adr_data = await self._fetch_adr_data()
    sector_analysis = await self._analyze_sector_momentum()
    
    # Step 2: Stock Screening
    candidate_stocks = await self._screen_candidate_stocks()
    
    # Step 3: Technical Analysis
    for stock in candidate_stocks:
        stock.technical_score = await self._calculate_technical_score(stock)
        stock.volume_score = await self._calculate_volume_score(stock)
        stock.adr_score = await self._calculate_adr_correlation(stock, adr_data)
    
    # Step 4: Option Analysis (if applicable)
    for stock in candidate_stocks:
        if market_sentiment != 'NEUTRAL':
            option_data = await self._analyze_options_chain(stock)
            stock.option_contract = option_data.get('best_contract')
            stock.atm_strike = option_data.get('atm_strike')
    
    # Step 5: Final Selection & Ranking
    selected_stocks = self._rank_and_select(candidate_stocks)
    
    # Step 6: Database Storage
    await self._store_selections(selected_stocks)
    
    return selected_stocks
```

### 6. Option Strategy Selection

#### ATM Strike Calculation
```python
def calculate_atm_strike(self, current_price: float) -> float:
    """Calculate At-The-Money strike price"""
    # Round to nearest strike price
    if current_price <= 100:
        strike_interval = 2.5
    elif current_price <= 500:
        strike_interval = 5
    elif current_price <= 1000:
        strike_interval = 10
    else:
        strike_interval = 50
    
    return round(current_price / strike_interval) * strike_interval
```

#### Option Type Decision Logic
```python
def determine_option_type(self, market_sentiment: str, stock_momentum: float) -> str:
    """Determine CE/PE based on market conditions"""
    if market_sentiment == 'BULLISH' and stock_momentum > 0.6:
        return 'CE'  # Call Option
    elif market_sentiment == 'BEARISH' and stock_momentum < 0.4:
        return 'PE'  # Put Option
    else:
        return 'NEUTRAL'  # Cash trading or wait
```

### 7. Selection Validation & Risk Management

#### Risk Filters
```python
def validate_selection_risk(self, stock: StockSelectionResult) -> bool:
    """Validate selection against risk parameters"""
    
    # Volume validation
    if stock.volume_score < 0.5:
        return False
    
    # Price stability check
    if abs(stock.technical_score - 0.5) < 0.2:  # Too neutral
        return False
    
    # ADR correlation validation
    if stock.adr_score < self.min_adr_correlation:
        return False
    
    # Market cap validation (avoid penny stocks)
    if stock.price_at_selection < 50:
        return False
    
    return True
```

### 8. Database Integration

#### Selection Storage
```python
# Database Models
class SelectedStock(Base):
    __tablename__ = "selected_stocks"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    symbol = Column(String(20), nullable=False)
    sector = Column(String(50))
    selection_score = Column(Float)
    selection_reason = Column(Text)
    price_at_selection = Column(Numeric(10, 2))
    option_type = Column(String(10))  # CE/PE/NEUTRAL
    atm_strike = Column(Numeric(10, 2))
    expiry_date = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
```

### 9. Performance Tracking

#### Selection Accuracy Metrics
```python
def calculate_selection_performance(self, selection_date: date) -> Dict[str, float]:
    """Calculate how well selections performed"""
    
    selections = self._get_selections_by_date(selection_date)
    performance_metrics = {}
    
    for selection in selections:
        # Calculate intraday performance
        entry_price = selection.price_at_selection
        high_price = self._get_intraday_high(selection.symbol, selection_date)
        low_price = self._get_intraday_low(selection.symbol, selection_date)
        close_price = self._get_closing_price(selection.symbol, selection_date)
        
        # Performance calculations
        max_gain = (high_price - entry_price) / entry_price * 100
        max_loss = (low_price - entry_price) / entry_price * 100
        closing_pnl = (close_price - entry_price) / entry_price * 100
        
        performance_metrics[selection.symbol] = {
            'max_gain': max_gain,
            'max_loss': max_loss,
            'closing_pnl': closing_pnl,
            'selection_score': selection.selection_score
        }
    
    return performance_metrics
```

### 10. Integration with Trading Strategies

#### Strategy Handoff
```python
def handoff_to_trading_strategies(self, selected_stocks: List[StockSelectionResult]):
    """Pass selected stocks to active trading strategies"""
    
    for stock in selected_stocks:
        # Register with Gap Detection Strategy
        if stock.adr_score > 0.7:
            gap_detector.register_stock(stock.symbol, stock.instrument_key)
        
        # Register with Breakout Strategy
        if stock.technical_score > 0.8:
            breakout_engine.register_stock(stock.symbol, stock.instrument_key)
        
        # Register with Options Strategy
        if stock.option_type != 'NEUTRAL':
            options_strategy.register_stock(stock)
```

## Key Features

### 1. **Multi-Factor Analysis**
- Combines fundamental, technical, and sentiment analysis
- Real-time market data integration
- Global market correlation (ADR)

### 2. **Risk Management**
- Volume and liquidity filters
- Price stability validation
- Maximum position size limits

### 3. **Performance Optimization**
- Pandas/NumPy for fast calculations
- Async processing for concurrent data fetching
- Memory-efficient data structures

### 4. **Flexibility**
- Configurable selection criteria
- Multiple market condition handling
- Easy integration with new strategies

## Usage Example

```python
# Initialize service
stock_selector = AutoStockSelectionService(user_id=1)

# Run daily selection
selected_stocks = await stock_selector.run_stock_selection()

# Process results
for stock in selected_stocks:
    logger.info(f"Selected: {stock.symbol} ({stock.sector})")
    logger.info(f"Score: {stock.selection_score:.2f}")
    logger.info(f"Option Type: {stock.option_type}")
    logger.info(f"Reason: {stock.selection_reason}")
```

## Related Documentation
- [Gap Detection Strategy](./GAP_DETECTION_STRATEGY.md)
- [Breakout Strategy](./BREAKOUT_STRATEGY.md)
- [Live Feed Integration](../data-flow/LIVE_FEED_DATA_FORMAT.md)
- [Options Trading](./OPTIONS_STRATEGY.md)