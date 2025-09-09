# Live Feed Data Format Reference

## Overview

This document describes the real-time market data format received from broker WebSocket connections, specifically focusing on the Upstox WebSocket feed structure. This data is critical for the trading application's real-time features and analytics.

## Upstox WebSocket Live Feed Structure

### Message Format

The system receives real-time market data in the following JSON structure:

```json
{
  "type": "live_feed",
  "feeds": {
    "INSTRUMENT_KEY": {
      "fullFeed": {
        "marketFF": { /* Market data for equity instruments */ },
        "indexFF": { /* Market data for index instruments */ }
      },
      "requestMode": "full_d5"
    }
  }
}
```

### Instrument Key Format

Instrument keys follow the pattern: `EXCHANGE|IDENTIFIER`

**Examples:**
- `NSE_EQ|INE318A01026` - NSE Equity with ISIN
- `NSE_INDEX|Nifty Bank` - NSE Index
- `NSE_FO|SYMBOL` - NSE Futures & Options

### Equity Data Structure (marketFF)

```json
{
  "marketFF": {
    "ltpc": {
      "ltp": 3097.7,          // Last traded price (number)
      "ltt": "1757308567467", // Last traded time (timestamp string)
      "ltq": "1",             // Last traded quantity (string)
      "cp": 3095.1            // Previous close price (number)
    },
    "marketLevel": {
      "bidAskQuote": [
        {
          "bidQ": "1",        // Bid quantity (string)
          "bidP": 3097.4,     // Bid price (number)
          "askQ": "2",        // Ask quantity (string)
          "askP": 3097.9      // Ask price (number)
        }
        // ... up to 5 levels of market depth
      ]
    },
    "optionGreeks": {},       // Option Greeks data (empty for equity)
    "marketOHLC": {
      "ohlc": [
        {
          "interval": "1d",           // Time interval
          "open": 3094.0,             // Open price
          "high": 3115.4,             // High price
          "low": 3081.0,              // Low price
          "close": 3097.7,            // Close price
          "vol": "31929",             // Volume (string)
          "ts": "1757269800000"       // Timestamp (string)
        },
        {
          "interval": "I1",           // 1-minute interval
          "open": 3097.0,
          "high": 3097.5,
          "low": 3095.2,
          "close": 3097.5,
          "vol": "488",
          "ts": "1757308500000"
        }
      ]
    },
    "atp": 3096.11,          // Average traded price (number)
    "vtt": "31929",          // Total volume traded (string)
    "tbq": 49001.0,          // Total buy quantity (number)
    "tsq": 45374.0           // Total sell quantity (number)
  }
}
```

### Index Data Structure (indexFF)

```json
{
  "indexFF": {
    "ltpc": {
      "ltp": 54154.8,        // Index last value (number)
      "ltt": "1757308567000", // Last update time (timestamp string)
      "cp": 54114.55         // Previous close (number)
    },
    "marketOHLC": {
      "ohlc": [
        {
          "interval": "1d",
          "open": 54215.4,
          "high": 54329.2,
          "low": 54067.15,
          "close": 54154.8,
          "ts": "1757269800000"
        },
        {
          "interval": "I1",
          "open": 54146.15,
          "high": 54156.4,
          "low": 54141.25,
          "close": 54156.4,
          "ts": "1757308500000"
        }
      ]
    }
  }
}
```

## Data Types and Precision

### Price Data
- **Type**: `number` (floating-point)
- **Precision**: Up to 2 decimal places for most instruments
- **Financial Calculations**: Convert to `Decimal` type for accurate calculations

### Volume Data
- **Type**: `string` (to handle large numbers)
- **Conversion**: Parse to integer/long for calculations
- **Range**: Can exceed JavaScript number precision limits

### Timestamps
- **Format**: Unix timestamp in milliseconds (string)
- **Conversion**: `new Date(parseInt(timestamp))` in JavaScript
- **Precision**: Millisecond accuracy

### Quantity Data
- **Market Depth**: Quantities provided as strings
- **Volume**: Total volume as string
- **Conversion**: Parse to appropriate numeric type

## OHLC Intervals

### Available Intervals
- `1d` - Daily OHLC data
- `I1` - 1-minute interval data
- Additional intervals may be available based on subscription

### Data Freshness
- **Daily Data**: Updated at market close
- **Intraday Data**: Real-time updates during market hours
- **Timestamp**: Indicates data validity period

## Market Depth Information

### Bid-Ask Levels
- **Depth**: Up to 5 levels of market depth
- **Order**: Sorted by price (best bid/ask first)
- **Updates**: Real-time during market hours

### Volume Indicators
- **tbq** (Total Buy Quantity): Aggregate buy interest
- **tsq** (Total Sell Quantity): Aggregate sell interest
- **Usage**: Market sentiment analysis

## System Integration Flow

### Data Pipeline
1. **Reception**: `services/upstox/ws_client.py` receives raw WebSocket data
2. **Processing**: `services/centralized_ws_manager.py` standardizes format
3. **Broadcasting**: `services/unified_websocket_manager.py` distributes to clients
4. **Frontend**: React components receive via custom hooks

### Error Handling
- **Connection Loss**: Automatic reconnection with exponential backoff
- **Data Validation**: Schema validation before processing
- **Fallback**: Redis cache maintains last known prices

### Performance Considerations
- **Batching**: Multiple instrument updates in single message
- **Filtering**: Subscribe only to required instruments
- **Caching**: Store frequently accessed data in memory

## Usage Examples

### Processing Live Feed
```python
def process_live_feed(feed_data: dict) -> None:
    """Process incoming live feed data."""
    if feed_data.get("type") != "live_feed":
        return
    
    feeds = feed_data.get("feeds", {})
    for instrument_key, data in feeds.items():
        full_feed = data.get("fullFeed", {})
        
        # Process equity data
        if "marketFF" in full_feed:
            market_data = full_feed["marketFF"]
            ltpc = market_data.get("ltpc", {})
            
            price = ltpc.get("ltp")
            if price:
                update_instrument_price(instrument_key, Decimal(str(price)))
        
        # Process index data
        elif "indexFF" in full_feed:
            index_data = full_feed["indexFF"]
            ltpc = index_data.get("ltpc", {})
            
            value = ltpc.get("ltp")
            if value:
                update_index_value(instrument_key, Decimal(str(value)))
```

### Frontend Data Handling
```javascript
const processFeedUpdate = (feedData) => {
  if (feedData.type !== 'live_feed') return;
  
  Object.entries(feedData.feeds).forEach(([instrumentKey, data]) => {
    const fullFeed = data.fullFeed;
    
    if (fullFeed.marketFF) {
      const { ltpc, marketLevel } = fullFeed.marketFF;
      updateMarketData(instrumentKey, {
        ltp: ltpc.ltp,
        change: ltpc.ltp - ltpc.cp,
        volume: fullFeed.marketFF.vtt,
        bidAsk: marketLevel.bidAskQuote
      });
    }
  });
};
```

## Troubleshooting

### Common Issues
1. **Missing Data Fields**: Check subscription parameters
2. **Timestamp Parsing**: Ensure correct millisecond conversion
3. **Precision Loss**: Use Decimal for financial calculations
4. **Volume Overflow**: Handle large volume strings properly

### Validation Checklist
- [ ] Instrument key format validation
- [ ] Required field presence check
- [ ] Numeric type conversion
- [ ] Timestamp validity
- [ ] Market hours verification

## Data Normalization & Enrichment Process

### Centralized WebSocket Manager Processing

The `services/centralized_ws_manager.py` performs comprehensive data normalization:

#### Step 1: Raw Data Validation
```python
def _validate_raw_input(self, instrument_key: str, raw_data: Any) -> bool:
    """Validate raw input data"""
    if not instrument_key or "|" not in instrument_key:
        return False
    if not isinstance(raw_data, dict):
        return False
    if "fullFeed" not in raw_data:
        return False
    return True
```

#### Step 2: Format-Specific Extraction
```python
def _extract_by_format(self, raw_data: dict) -> Optional[dict]:
    """Extract data based on Upstox format type"""
    full_feed = raw_data.get("fullFeed", {})
    
    # Format 1: Market Data (NSE_EQ, NSE_FO, MCX_FO)
    if "marketFF" in full_feed:
        return self._extract_market_format(full_feed["marketFF"])
    
    # Format 2: Index Data (NSE_INDEX, BSE_INDEX)
    elif "indexFF" in full_feed:
        return self._extract_index_format(full_feed["indexFF"])
```

#### Step 3: Market Data Extraction (Equity/F&O)
```python
def _extract_market_format(self, market_ff: dict) -> dict:
    """Extract from marketFF format"""
    data = {}
    
    # Core price data
    if "ltpc" in market_ff and market_ff["ltpc"]:
        ltpc = market_ff["ltpc"]
        data.update({
            "ltp": self._safe_float(ltpc.get("ltp")),
            "cp": self._safe_float(ltpc.get("cp")),
            "ltq": self._safe_int(ltpc.get("ltq")),
            "ltt": self._safe_string(ltpc.get("ltt")),
        })
    
    # Volume and OHLC data extraction...
    # Bid/Ask market depth...
    # Options Greeks (if applicable)...
```

#### Step 4: Metadata Enrichment
```python
def _enrich_with_metadata(self, instrument_key: str, extracted_data: dict) -> Optional[dict]:
    """Enrich data with symbol metadata"""
    # Resolve symbol from instrument key
    symbol_info = self._resolve_instrument_symbol(instrument_key)
    
    # Calculate derived metrics
    self._calculate_price_metrics(extracted_data)
    
    # Create enriched structure
    enriched = {
        # Identifiers
        "instrument_key": instrument_key,
        "symbol": symbol_info["symbol"],
        "name": symbol_info["name"],
        "exchange": symbol_info["exchange"],
        "sector": symbol_info["sector"],
        "instrument_type": symbol_info["type"],
        
        # Price data with frontend-compatible field names
        **extracted_data,
        "last_price": extracted_data.get("ltp", 0),  # Frontend compatibility
        
        # Metadata
        "timestamp": datetime.now().isoformat(),
        "data_source": "upstox_live",
        "processing_time": datetime.now().isoformat(),
    }
```

### Normalized Data Output Format

After processing by the centralized manager, data is normalized to this structure:

```json
{
  "NSE_EQ|INE318A01026": {
    // Identifiers
    "instrument_key": "NSE_EQ|INE318A01026",
    "symbol": "RELIANCE",
    "name": "Reliance Industries Limited",
    "exchange": "NSE",
    "sector": "ENERGY",
    "instrument_type": "EQ",
    
    // Price Data
    "ltp": 3097.7,                    // Last traded price
    "last_price": 3097.7,             // Frontend-compatible field
    "cp": 3095.1,                     // Previous close price
    "ltq": 1,                         // Last traded quantity
    "ltt": "1757308567467",           // Last traded time
    
    // OHLC Data
    "open": 3094.0,
    "high": 3115.4,
    "low": 3081.0,
    "close": 3097.7,
    "volume": 31929,
    
    // Market Depth (Best Bid/Ask)
    "bid_price": 3097.4,
    "bid_qty": 1,
    "ask_price": 3097.9,
    "ask_qty": 2,
    
    // Calculated Metrics
    "change": 2.6,                    // Price change from previous close
    "change_percent": 0.084,          // Percentage change
    "avg_trade_price": 3096.11,       // Average traded price
    
    // Options Data (if applicable)
    "option_greeks": {
      "delta": null,
      "theta": null,
      "gamma": null,
      "vega": null,
      "rho": null
    },
    
    // Metadata
    "timestamp": "2025-09-09T10:46:28.000Z",
    "data_source": "upstox_live",
    "processing_time": "2025-09-09T10:46:28.100Z"
  }
}
```

### Instrument Registry Enrichment

The `services/instrument_registry.py` further enriches data for frontend consumption:

#### Performance Metrics Addition
```python
def _create_complete_entry(self, instrument_key: str, symbol: str, price_data: dict) -> dict:
    """Create complete enriched entry with performance metrics"""
    enriched_data = {
        **price_data,  # Include all normalized data
        
        // Additional Performance Metrics
        "day_range": f"{price_data.get('low', 0):.2f} - {price_data.get('high', 0):.2f}",
        "volume_formatted": self._format_volume(price_data.get('volume', 0)),
        "market_cap_category": self._categorize_by_market_cap(symbol),
        "volatility_indicator": self._calculate_volatility(price_data),
        "momentum_score": self._calculate_momentum(price_data),
        
        // UI Display Fields
        "display_name": f"{symbol} ({price_data.get('name', '')})",
        "color_indicator": "green" if price_data.get('change', 0) > 0 else "red",
        "trend_arrow": "↑" if price_data.get('change', 0) > 0 else "↓",
        
        // Cache Management
        "last_updated": datetime.now().isoformat(),
        "access_count": 1,
        "priority_score": self._calculate_priority_score(symbol, price_data)
    }
```

### Final Frontend Data Format

The enriched data sent to the frontend via WebSocket:

```json
{
  "type": "price_update",
  "data": {
    "RELIANCE": {
      // Core Market Data
      "symbol": "RELIANCE",
      "last_price": 3097.7,
      "change": 2.6,
      "change_percent": 0.084,
      "volume": 31929,
      "volume_formatted": "31.9K",
      
      // OHLC Data
      "open": 3094.0,
      "high": 3115.4,
      "low": 3081.0,
      "day_range": "3081.00 - 3115.40",
      
      // Market Depth
      "bid_price": 3097.4,
      "ask_price": 3097.9,
      "spread": 0.5,
      
      // Metadata for UI
      "sector": "ENERGY",
      "exchange": "NSE",
      "instrument_type": "EQ",
      "display_name": "RELIANCE (Reliance Industries Limited)",
      "color_indicator": "green",
      "trend_arrow": "↑",
      
      // Performance Indicators
      "momentum_score": 0.75,
      "volatility_indicator": "MEDIUM",
      "market_cap_category": "LARGE_CAP",
      
      // System Fields
      "timestamp": "2025-09-09T10:46:28.000Z",
      "data_source": "upstox_live",
      "last_updated": "2025-09-09T10:46:28.200Z"
    }
  },
  "timestamp": "2025-09-09T10:46:28.200Z",
  "source": "unified_websocket_manager"
}
```

### Broadcasting Pipeline

1. **Raw Feed** → `services/upstox/ws_client.py` receives Upstox WebSocket data
2. **Normalization** → `services/centralized_ws_manager.py` standardizes and enriches
3. **Registry Update** → `services/instrument_registry.py` adds performance metrics
4. **Broadcasting** → `services/unified_websocket_manager.py` sends to frontend clients
5. **Frontend Reception** → React components receive via custom hooks (`useUnifiedMarketData`)

## Related Documentation
- [WebSocket Client Implementation](../services/WEBSOCKET_CLIENT.md)
- [Market Data Processing](./MARKET_DATA_FLOW.md)
- [Real-time Analytics](../architecture/ANALYTICS_ARCHITECTURE.md)