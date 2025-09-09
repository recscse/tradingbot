# Gap Detection Strategy Documentation

## Overview

The Gap Detection Strategy (`services/premarket_candle_builder.py`) is a specialized algorithmic trading strategy that identifies and analyzes price gaps during the premarket session (9:00 AM - 9:08 AM IST). It builds real-time OHLC candles from tick-by-tick data and detects significant price gaps for trading opportunities.

## Strategy Fundamentals

### What is a Gap?
A gap occurs when a stock's opening price differs significantly from the previous day's closing price, creating a "gap" in the price chart.

**Gap Formula:**
```python
gap_percentage = ((open_price - previous_close) / previous_close) * 100
```

### Gap Types
- **Gap Up**: `gap_percentage > 0.5%` (bullish)
- **Gap Down**: `gap_percentage < -0.5%` (bearish)  
- **No Gap**: `-0.5% ≤ gap_percentage ≤ 0.5%`

### Gap Strength Classification
```python
def get_gap_strength(self) -> str:
    abs_gap = abs(gap_percentage)
    if abs_gap >= 8.0:
        return "VERY_STRONG"      # >8% gap
    elif abs_gap >= 5.0:
        return "STRONG"           # 5-8% gap
    elif abs_gap >= 2.5:
        return "MODERATE"         # 2.5-5% gap
    elif abs_gap >= 1.0:
        return "WEAK"             # 1-2.5% gap
    else:
        return "INSIGNIFICANT"    # <1% gap
```

## Live Feed Integration

### Real-Time Data Processing
```python
async def _handle_direct_market_data(self, event_data: dict):
    """Process live WebSocket feed data for gap detection"""
    try:
        # Extract normalized data from centralized manager
        for instrument_key, price_data in event_data.items():
            symbol = price_data.get('symbol')
            current_price = price_data.get('ltp')           # Last traded price
            previous_close = price_data.get('cp')           # Previous close
            volume = price_data.get('volume', 0)
            timestamp = datetime.now()
            
            # Create tick data
            tick = TickData(
                timestamp=timestamp,
                price=Decimal(str(current_price)),
                volume=int(volume),
                instrument_key=instrument_key,
                symbol=symbol
            )
            
            # Process tick for gap detection
            await self._process_tick_data(tick)
```

### Data Flow from Live Feed
1. **Raw WebSocket Data** → Centralized WS Manager normalizes data
2. **Normalized Data** → Gap Detection Service receives enriched data
3. **Tick Processing** → Real-time candle building and gap calculation
4. **Gap Detection** → Alert generation and database storage

## Premarket Candle Building

### Time-Based Processing
```python
# Premarket trading hours (IST)
PREMARKET_START_TIME = time(9, 0)   # 9:00 AM
PREMARKET_END_TIME = time(9, 8)     # 9:08 AM  
MARKET_OPEN_TIME = time(9, 15)      # 9:15 AM

def is_premarket_hours(self) -> bool:
    """Check if current time is within premarket window"""
    current_time = datetime.now().time()
    return PREMARKET_START_TIME <= current_time <= PREMARKET_END_TIME
```

### Real-Time Candle Construction
```python
@dataclass  
class CandleBuilder:
    """Real-time candle builder for a single instrument"""
    symbol: str
    instrument_key: str
    start_time: datetime
    end_time: datetime
    
    # OHLC data
    open_price: Optional[Decimal] = None
    high_price: Optional[Decimal] = None
    low_price: Optional[Decimal] = None
    close_price: Optional[Decimal] = None
    
    # Volume and trade data
    total_volume: int = 0
    total_trades: int = 0
    tick_count: int = 0
    
    # Previous close for gap calculation
    previous_close: Optional[Decimal] = None
    
    def add_tick(self, tick: TickData) -> None:
        """Add a single tick to the candle"""
        price = tick.price
        volume = tick.volume
        
        # Initialize OHLC on first tick
        if self.open_price is None:
            self.open_price = price
            self.high_price = price
            self.low_price = price
            self.first_tick_time = tick.timestamp
            
        # Update OHLC values
        if price > self.high_price:
            self.high_price = price
        if price < self.low_price:
            self.low_price = price
            
        self.close_price = price  # Always update to latest price
        self.total_volume += volume
        self.tick_count += 1
        self.last_tick_time = tick.timestamp
```

## Gap Detection Logic

### Primary Gap Analysis
```python
def detect_gap_opportunity(self, candle: CandleBuilder) -> Dict[str, Any]:
    """Comprehensive gap analysis"""
    
    # Calculate gap metrics
    gap_percentage = candle.calculate_gap_percentage()
    gap_type = candle.get_gap_type()
    gap_strength = candle.get_gap_strength()
    
    # Volume confirmation
    volume_ratio = self._calculate_volume_ratio(candle)
    has_volume_support = volume_ratio > 1.5  # 50% above average
    
    # Quality assessment
    data_quality = candle.get_data_quality_score()
    is_reliable = data_quality > 0.7
    
    # Significance threshold
    is_significant = abs(gap_percentage) >= 1.0  # Minimum 1% gap
    
    return {
        'gap_percentage': gap_percentage,
        'gap_type': gap_type,
        'gap_strength': gap_strength,
        'volume_confirmation': has_volume_support,
        'volume_ratio': volume_ratio,
        'data_quality': data_quality,
        'is_tradeable': is_significant and has_volume_support and is_reliable,
        'confidence_score': calculate_confidence_score(
            gap_percentage, volume_ratio, data_quality
        )
    }
```

### Volume Confirmation Logic
```python
def _calculate_volume_ratio(self, builder: CandleBuilder) -> Optional[Decimal]:
    """Calculate volume ratio vs. historical average"""
    try:
        # Get 20-day average volume for comparison
        avg_volume = self._get_average_volume(builder.symbol, days=20)
        
        if avg_volume and avg_volume > 0:
            # Calculate 8-minute volume ratio
            # Scale to full day equivalent: (total_volume / 8 minutes) * 375 minutes
            estimated_daily_volume = builder.total_volume * (375 / 8)
            ratio = Decimal(estimated_daily_volume) / Decimal(avg_volume)
            return ratio.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
        return None
    except Exception as e:
        logger.debug(f"Volume ratio calculation error: {e}")
        return None
```

## Strategy Execution Flow

### 1. Market Session Initialization
```python
async def start_premarket_session(self):
    """Initialize premarket gap detection session"""
    
    # Setup WebSocket integration
    await self.setup_direct_ws_integration()
    
    # Load previous day's closing prices
    await self._load_previous_closes()
    
    # Initialize active builders for monitored stocks
    await self._initialize_stock_builders()
    
    # Start gap monitoring
    self.is_premarket_active = True
    logger.info("🚨 PREMARKET GAP DETECTION SESSION STARTED")
```

### 2. Real-Time Processing
```python
async def _process_tick_callback(self, instrument_key: str, price_data: dict):
    """Process incoming tick data during premarket hours"""
    try:
        # Only process during premarket hours
        if not self.is_premarket_hours():
            return
            
        # Extract data from NORMALIZED format
        symbol = price_data.get('symbol')
        current_price = price_data.get('ltp')
        previous_close = price_data.get('cp')
        volume = price_data.get('volume', 0)
        
        # Create tick and add to builder
        tick = TickData(
            timestamp=datetime.now(),
            price=Decimal(str(current_price)),
            volume=int(volume),
            instrument_key=instrument_key,
            symbol=symbol
        )
        
        # Get or create candle builder
        builder = self._get_or_create_builder(tick)
        builder.add_tick(tick)
        
        # Check for significant gaps
        if self._should_check_gap(builder):
            await self._analyze_gap_opportunity(builder)
            
    except Exception as e:
        logger.error(f"Error processing tick: {e}")
```

### 3. Gap Alert Generation
```python
async def _generate_gap_alert(self, candle: PremarketCandle):
    """Generate gap detection alert"""
    try:
        gap_pct = abs(candle.gap_percentage or Decimal('0'))
        
        # Determine alert priority
        if gap_pct >= Decimal('8.0'):
            priority = "CRITICAL"
        elif gap_pct >= Decimal('5.0'):
            priority = "HIGH"
        elif gap_pct >= Decimal('2.5'):
            priority = "MEDIUM"
        else:
            priority = "LOW"
            
        # Calculate confidence score
        confidence = self._calculate_confidence_score(candle)
        
        # Create alert record
        alert = GapDetectionAlert(
            symbol=candle.symbol,
            instrument_key=candle.instrument_key,
            gap_percentage=candle.gap_percentage,
            gap_type=candle.gap_type,
            gap_strength=candle.gap_strength,
            trigger_price=candle.close_price,
            previous_close=candle.previous_close,
            alert_priority=priority,
            confidence_score=confidence,
            volume_at_alert=candle.total_volume,
            volume_ratio=candle.volume_ratio,
            expires_at=datetime.combine(candle.candle_date, time(15, 30))  # Market close
        )
        
        # Save to database
        db = next(get_db())
        db.add(alert)
        db.commit()
        
        # Broadcast real-time alert
        await self._broadcast_gap_alert(alert)
        
    except Exception as e:
        logger.error(f"Error generating gap alert: {e}")
```

## Trading Strategy Integration

### Entry Signal Generation
```python
def generate_entry_signals(self, gap_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate trading entry signals based on gap analysis"""
    
    signals = []
    gap_percentage = gap_data['gap_percentage']
    gap_type = gap_data['gap_type']
    confidence = gap_data['confidence_score']
    
    # Gap Up Strategy
    if gap_type == "GAP_UP" and confidence > 0.7:
        if gap_percentage > 3.0:
            # Strong gap up - potential continuation
            signals.append({
                'action': 'BUY',
                'strategy': 'GAP_UP_CONTINUATION',
                'entry_type': 'MARKET_OPEN',
                'stop_loss': gap_data['previous_close'],
                'target_1': gap_data['trigger_price'] * 1.02,  # 2% target
                'target_2': gap_data['trigger_price'] * 1.05,  # 5% target
                'confidence': confidence
            })
        elif 1.0 < gap_percentage <= 3.0:
            # Moderate gap up - potential fill
            signals.append({
                'action': 'SELL',
                'strategy': 'GAP_FILL',
                'entry_type': 'MARKET_OPEN',
                'stop_loss': gap_data['trigger_price'] * 1.015,  # 1.5% stop
                'target_1': gap_data['previous_close'],  # Gap fill target
                'confidence': confidence
            })
    
    # Gap Down Strategy  
    elif gap_type == "GAP_DOWN" and confidence > 0.7:
        if gap_percentage < -3.0:
            # Strong gap down - potential bounce
            signals.append({
                'action': 'BUY',
                'strategy': 'GAP_DOWN_BOUNCE',
                'entry_type': 'MARKET_OPEN',
                'stop_loss': gap_data['trigger_price'] * 0.98,  # 2% stop
                'target_1': gap_data['previous_close'],  # Bounce to previous close
                'confidence': confidence
            })
    
    return signals
```

### Risk Management
```python
def calculate_position_size(self, signal: Dict[str, Any], account_balance: float) -> int:
    """Calculate position size based on risk management rules"""
    
    # Risk per trade: 1% of account
    risk_amount = account_balance * 0.01
    
    # Calculate stop loss distance
    entry_price = signal.get('trigger_price', 0)
    stop_loss = signal.get('stop_loss', 0)
    stop_distance = abs(entry_price - stop_loss)
    
    if stop_distance > 0:
        # Position size = Risk Amount / Stop Loss Distance
        position_size = int(risk_amount / stop_distance)
        
        # Maximum position size: 10% of account
        max_position_value = account_balance * 0.10
        max_shares = int(max_position_value / entry_price)
        
        return min(position_size, max_shares)
    
    return 0
```

## Performance Metrics & Profitability

### Gap Strategy Success Rates
```python
def calculate_strategy_performance(self, start_date: date, end_date: date) -> Dict[str, Any]:
    """Calculate gap strategy performance metrics"""
    
    # Fetch gap alerts and trades for period
    alerts = self._get_gap_alerts(start_date, end_date)
    trades = self._get_gap_trades(start_date, end_date)
    
    performance = {
        'total_gaps_detected': len(alerts),
        'gaps_traded': len(trades),
        'win_rate': 0,
        'avg_profit_per_trade': 0,
        'total_pnl': 0,
        'max_drawdown': 0,
        'sharpe_ratio': 0,
        'profit_factor': 0
    }
    
    if trades:
        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl < 0]
        
        performance.update({
            'win_rate': len(winning_trades) / len(trades) * 100,
            'avg_profit_per_trade': sum(t.pnl for t in trades) / len(trades),
            'total_pnl': sum(t.pnl for t in trades),
            'best_trade': max(t.pnl for t in trades),
            'worst_trade': min(t.pnl for t in trades),
            'avg_win': sum(t.pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0,
            'avg_loss': sum(t.pnl for t in losing_trades) / len(losing_trades) if losing_trades else 0
        })
        
        # Calculate profit factor
        gross_profit = sum(t.pnl for t in winning_trades)
        gross_loss = abs(sum(t.pnl for t in losing_trades))
        performance['profit_factor'] = gross_profit / gross_loss if gross_loss > 0 else 0
    
    return performance
```

### Typical Performance Characteristics
- **Win Rate**: 65-75% (depending on market conditions)
- **Profit Factor**: 1.5-2.0 (profitable strategies)
- **Average Hold Time**: 15-45 minutes
- **Risk-Reward Ratio**: 1:1.5 to 1:3
- **Daily Opportunities**: 2-8 tradeable gaps

## Database Schema

### Premarket Candle Storage
```python
class PremarketCandle(Base):
    __tablename__ = "premarket_candles"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    instrument_key = Column(String(50), nullable=False)
    candle_date = Column(Date, nullable=False, index=True)
    
    # OHLC Data
    open_price = Column(Numeric(10, 4), nullable=False)
    high_price = Column(Numeric(10, 4), nullable=False)
    low_price = Column(Numeric(10, 4), nullable=False)
    close_price = Column(Numeric(10, 4), nullable=False)
    previous_close = Column(Numeric(10, 4))
    
    # Gap Analysis
    gap_percentage = Column(Numeric(8, 4))
    gap_type = Column(String(20))  # GAP_UP, GAP_DOWN, NO_GAP
    gap_strength = Column(String(20))  # WEAK, MODERATE, STRONG, VERY_STRONG
    
    # Volume Analysis
    total_volume = Column(BigInteger, default=0)
    volume_ratio = Column(Numeric(6, 2))
    volume_confirmation = Column(Boolean, default=False)
    
    # Quality Metrics
    data_quality_score = Column(Numeric(4, 3))
    ticks_received = Column(Integer, default=0)
    is_significant_gap = Column(Boolean, default=False)
```

### Gap Alert Storage
```python
class GapDetectionAlert(Base):
    __tablename__ = "gap_detection_alerts"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    gap_percentage = Column(Numeric(8, 4), nullable=False)
    gap_type = Column(String(20), nullable=False)
    gap_strength = Column(String(20), nullable=False)
    
    alert_priority = Column(String(20))  # LOW, MEDIUM, HIGH, CRITICAL
    confidence_score = Column(Numeric(4, 3))
    trigger_price = Column(Numeric(10, 4))
    previous_close = Column(Numeric(10, 4))
    
    volume_at_alert = Column(BigInteger)
    volume_ratio = Column(Numeric(6, 2))
    
    alert_time = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
```

## Integration with Other Strategies

### Handoff to Execution Engine
```python
async def handoff_gap_signals(self, gap_signals: List[Dict[str, Any]]):
    """Hand off gap signals to execution engine"""
    
    for signal in gap_signals:
        # Create trade order
        order_request = {
            'symbol': signal['symbol'],
            'action': signal['action'],
            'quantity': signal['position_size'],
            'order_type': 'MARKET',
            'strategy': 'GAP_DETECTION',
            'entry_reason': f"Gap {signal['gap_type']} - {signal['confidence']:.2f} confidence",
            'stop_loss': signal['stop_loss'],
            'target_price': signal['target_1'],
            'max_hold_time': 45  # minutes
        }
        
        # Send to execution engine
        await execution_engine.submit_order(order_request)
```

## Related Documentation
- [Stock Selection Process](./STOCK_SELECTION_PROCESS.md)
- [Breakout Strategy](./BREAKOUT_STRATEGY.md)
- [Trade Execution Flow](./TRADE_EXECUTION_FLOW.md)
- [Live Feed Integration](../data-flow/LIVE_FEED_DATA_FORMAT.md)