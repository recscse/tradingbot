# MCX Data Format Specification

This document provides comprehensive details about the MCX (Multi Commodity Exchange) data format received via Upstox WebSocket API and how it's processed in our system.

## Overview

MCX data comes through the Upstox WebSocket in protobuf format and is decoded into JSON. The data follows the same structure as other Upstox instruments but contains commodity-specific information.

## Raw WebSocket Data Format

### Input Message Structure
```json
{
  "type": "live_feed",
  "feeds": {
    "MCX_FO|469601": {
      "fullFeed": {
        "marketFF": {
          "ltpc": {
            "ltp": 6500.50,
            "cp": 6450.00,
            "ltq": "10",
            "ltt": "1758308567467"
          },
          "marketLevel": {
            "bidAskQuote": [
              {
                "bidQ": "150",
                "bidP": 6500.00,
                "askQ": "200",
                "askP": 6501.00
              },
              {
                "bidQ": "100",
                "bidP": 6499.50,
                "askQ": "180",
                "askP": 6501.50
              },
              {}, {}, {}
            ]
          },
          "optionGreeks": {},
          "marketOHLC": {
            "ohlc": [
              {
                "interval": "1d",
                "open": 6480.00,
                "high": 6520.75,
                "low": 6440.25,
                "close": 6500.50,
                "vol": "85000",
                "ts": "1758220200000"
              },
              {
                "interval": "I1",
                "open": 6500.00,
                "high": 6500.50,
                "low": 6499.75,
                "close": 6500.50,
                "vol": "150",
                "ts": "1758308500000"
              }
            ]
          },
          "atp": 6495.25,
          "vtt": "85000",
          "tbq": 150000.0,
          "tsq": 140000.0
        }
      },
      "requestMode": "full_d5"
    }
  },
  "currentTs": "1758291921887"
}
```

## Field Definitions

### Top Level Structure

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always "live_feed" for real-time data |
| `feeds` | object | Container for all instrument data |
| `currentTs` | string | Current timestamp in milliseconds |

### Instrument Key Format

**Pattern**: `MCX_FO|{exchange_token}`

**Examples**:
- `MCX_FO|469601` - Crude Oil Future
- `MCX_FO|447500` - Gold Future
- `MCX_COM|114` - Gold Commodity

### Market Data Structure (`marketFF`)

#### LTPC (Last Traded Price & Close)
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `ltp` | number | Last Traded Price | 6500.50 |
| `cp` | number | Previous Close Price | 6450.00 |
| `ltq` | string | Last Traded Quantity | "10" |
| `ltt` | string | Last Traded Time (timestamp) | "1758308567467" |

#### Market Level (Bid/Ask Depth)
```json
"bidAskQuote": [
  {
    "bidQ": "150",    // Bid Quantity
    "bidP": 6500.00,  // Bid Price
    "askQ": "200",    // Ask Quantity
    "askP": 6501.00   // Ask Price
  },
  // ... up to 5 levels
]
```

#### Market OHLC
```json
"ohlc": [
  {
    "interval": "1d",           // Daily interval
    "open": 6480.00,           // Day's opening price
    "high": 6520.75,           // Day's high price
    "low": 6440.25,            // Day's low price
    "close": 6500.50,          // Current/closing price
    "vol": "85000",            // Volume traded
    "ts": "1758220200000"      // Timestamp
  },
  {
    "interval": "I1",           // 1-minute interval
    "open": 6500.00,
    "high": 6500.50,
    "low": 6499.75,
    "close": 6500.50,
    "vol": "150",
    "ts": "1758308500000"
  }
]
```

#### Volume & Trade Data
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `atp` | number | Average Trade Price | 6495.25 |
| `vtt` | string | Volume Traded Today | "85000" |
| `tbq` | number | Total Buy Quantity | 150000.0 |
| `tsq` | number | Total Sell Quantity | 140000.0 |

## Processed Data Format

After processing through our MCX service, the data is transformed into structured pandas DataFrames:

### Current Snapshot DataFrame
```python
columns = [
    'instrument_key',     # MCX_FO|469601
    'timestamp',          # 2025-01-20 14:30:15
    'ltp',               # 6500.50
    'cp',                # 6450.00
    'volume',            # 150000.0
    'symbol',            # CRUDEOIL
    'exchange_token',    # 469601
    'change',            # 50.50
    'change_percent',    # 0.78
    'open',              # 6480.00
    'high',              # 6520.75
    'low',               # 6440.25
    'close',             # 6500.50
    'bid_price',         # 6500.00
    'bid_qty',           # 150
    'ask_price',         # 6501.00
    'ask_qty'            # 200
]
```

### Futures Chain DataFrame
```python
columns = [
    'symbol',            # CRUDEOIL
    'instrument_key',    # MCX_FO|469601
    'ltp',              # 6500.50
    'change',           # 50.50
    'change_percent',   # 0.78
    'volume',           # 150000.0
    'timestamp'         # 2025-01-20 14:30:15
]
```

### Volume Data DataFrame
```python
columns = [
    'symbol',           # CRUDEOIL
    'instrument_key',   # MCX_FO|469601
    'volume',          # 150000.0
    'timestamp'        # 2025-01-20 14:30:15
]
```

## MCX Instrument Mapping

### Common MCX Symbols
| Exchange Token | Symbol | Full Name |
|----------------|--------|-----------|
| 469601 | CRUDEOIL | Crude Oil |
| 447500 | GOLD | Gold |
| 114 | GOLD | Gold (alternate) |
| 463598 | CRUDEOIL | Crude Oil (alternate) |

### Symbol Extraction Logic
```python
mcx_mapping = {
    "469601": "CRUDEOIL",
    "447500": "GOLD",
    "114": "GOLD",
    "463598": "CRUDEOIL",
    # Add more as needed
}

def extract_symbol(instrument_key):
    if "|" in instrument_key:
        token = instrument_key.split("|")[1]
        return mcx_mapping.get(token, f"MCX_{token}")
```

## Analytics Output Format

### Real-time Analytics
```json
{
  "total_instruments": 25,
  "total_symbols": 8,
  "price_stats": {
    "avg_change_percent": 1.23,
    "max_change_percent": 4.56,
    "min_change_percent": -2.34,
    "top_gainers": [
      {
        "symbol": "CRUDEOIL",
        "change_percent": 4.56
      }
    ],
    "top_losers": [
      {
        "symbol": "GOLD",
        "change_percent": -2.34
      }
    ]
  },
  "volume_stats": {
    "total_volume": 5000000,
    "top_volume_symbols": {
      "CRUDEOIL": 2000000,
      "GOLD": 1500000
    }
  },
  "futures_chain_stats": {
    "CRUDEOIL": {
      "contract_count": 12,
      "avg_change": 1.45
    }
  },
  "last_update": "2025-01-20T14:30:15"
}
```

## Data Processing Pipeline

### 1. Raw Data Ingestion
```
Upstox WebSocket → Protobuf Decode → JSON Format
```

### 2. Data Extraction
```python
# Extract market data
market_ff = feed_data["fullFeed"]["marketFF"]
ltpc = market_ff.get("ltpc", {})

# Convert to structured format
data_row = {
    'ltp': safe_float(ltpc.get('ltp')),
    'cp': safe_float(ltpc.get('cp')),
    'volume': safe_float(market_ff.get('tbq')),
    # ... other fields
}
```

### 3. Pandas Processing
```python
# Create DataFrame
df = pd.DataFrame(processed_data)

# Calculate derived metrics
df['change'] = df['ltp'] - df['cp']
df['change_percent'] = (df['change'] / df['cp']) * 100

# Group by symbol for futures chains
futures_chain = df.groupby('symbol').apply(...)
```

### 4. Analytics Generation
```python
# Statistical analysis
analytics = {
    'avg_change_percent': df['change_percent'].mean(),
    'top_gainers': df.nlargest(5, 'change_percent'),
    'volume_leaders': df.nlargest(5, 'volume'),
    # ... more analytics
}
```

## Error Handling

### Common Data Issues
1. **Null Values**: Handle None/null in numeric fields
2. **String Numbers**: Convert string quantities to numbers
3. **Missing Fields**: Graceful handling of optional fields
4. **Invalid Timestamps**: Fallback to current time

### Data Validation
```python
def safe_float(value):
    try:
        return float(value) if value is not None else None
    except (ValueError, TypeError):
        return None

def validate_mcx_data(data):
    required_fields = ['ltp', 'cp']
    return all(field in data for field in required_fields)
```

## Performance Considerations

### Memory Management
- Keep only last 1000 records per instrument
- Automatic cleanup of old data
- Efficient pandas operations

### Processing Speed
- Vectorized pandas operations
- NumPy for numerical computations
- Async processing to prevent blocking

### Data Storage
- CSV export for historical analysis
- Redis caching for real-time access
- In-memory DataFrames for speed

## Integration Points

### With Main Application
```python
# Health check data
{
  "is_running": True,
  "instruments_count": 25,
  "last_update": "2025-01-20T14:30:15",
  "data_quality": "good"
}

# Dashboard broadcast
{
  "type": "mcx_update",
  "count": 25,
  "analytics": {...},
  "timestamp": "1758291921887"
}
```

### API Endpoints
```
GET /api/mcx/data          # Current market data
GET /api/mcx/analytics     # Real-time analytics
GET /api/mcx/symbol/{sym}  # Symbol-specific data
GET /api/mcx/futures/{sym} # Futures chain for symbol
```

This specification covers the complete data flow from raw Upstox WebSocket messages to processed analytics ready for consumption by trading applications and user interfaces.