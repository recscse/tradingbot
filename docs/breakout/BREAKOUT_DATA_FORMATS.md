# Breakout Detection Data Formats - Backend to UI

## Complete Data Flow Format

### 1. WebSocket Message Format (Top Level)

```json
{
  "type": "breakout_analysis_update",
  "data": {
    // Complete breakout summary data (see below)
  }
}
```

### 2. Complete Breakout Summary Data Format

```json
{
  // Frontend Compatibility Format
  "breakouts": [
    // Array of upward breakout signals (see Individual Breakout Format)
  ],
  "breakdowns": [
    // Array of downward breakdown signals (same format as breakouts)
  ],
  "summary": {
    "total_breakouts": 15,
    "total_breakdowns": 8,
    "total_today": 23,
    "is_trading_hours": true,
    "detection_active": true,
    "last_update": "2025-09-07T18:11:47.233Z"
  },
  
  // Enhanced Format (Additional Data)
  "total_breakouts_today": 23,
  "breakouts_by_type": {
    "volume_breakout": [
      // Array of volume breakout signals
    ],
    "momentum_breakout": [
      // Array of momentum breakout signals
    ],
    "resistance_breakout": [
      // Array of resistance breakout signals
    ],
    "support_breakdown": [
      // Array of support breakdown signals
    ]
  },
  "top_breakouts": [
    // Top 20 breakouts by strength
  ],
  "recent_breakouts": [
    // Last 10 most recent breakouts
  ],
  "engine_metrics": {
    "total_scans": 1250,
    "breakouts_detected": 23,
    "avg_processing_time_ms": 15.2,
    "instruments_processed": 2847,
    "memory_usage_mb": 45.7,
    "detection_accuracy": 87.5,
    "instruments_tracked": 2847,
    "market_status": "open",
    "trading_day": "2025-09-07",
    "last_scan": "2025-09-07T18:11:47.100Z"
  },
  "timestamp": "2025-09-07T18:11:47.233Z",
  "generated_at": "06:11:47 PM",
  "service": "enhanced_breakout_engine"
}
```

### 3. Individual Breakout Signal Format

Each breakout signal (in `breakouts`, `breakdowns`, `top_breakouts`, `recent_breakouts` arrays) has this format:

```json
{
  "instrument_key": "NSE_EQ|INE467B01029",
  "symbol": "RELIANCE",
  "breakout_type": "momentum_breakout",
  "current_price": 2052.66,
  "breakout_price": 2045.30,
  "trigger_price": 2048.50,
  "volume": 2500000,
  "percentage_move": 1.85,
  "strength": 7.2,
  "confidence": 0.855,
  "volume_ratio": 3.2,
  "volatility_score": 15.8,
  "timestamp": "2025-09-07T18:11:47.233Z",
  "market_cap_category": "large_cap",
  "sector": "ENERGY",
  "confirmation_signals": [
    "volume_surge",
    "price_momentum", 
    "trend_alignment"
  ],
  "time_ago": "just now",
  "epoch_timestamp": 1725711707233
}
```

## Breakout Type Values

```json
{
  "breakout_types": [
    "volume_breakout",      // High volume with price movement
    "momentum_breakout",    // Strong price momentum
    "resistance_breakout",  // Price breaks above resistance
    "support_breakdown",    // Price breaks below support
    "gap_up",              // Opening gap upward
    "gap_down",            // Opening gap downward
    "high_breakout",       // New high breakout
    "low_breakdown",       // New low breakdown
    "volatility_expansion" // Volatility breakout
  ]
}
```

## UI Processing Example

### Frontend Hook Processing:

```javascript
// useUnifiedMarketData.js
const [breakoutAnalysis, setBreakoutAnalysis] = useState({
  breakouts: [],
  breakdowns: [],
  total_breakouts_today: 0
});

const handleMessage = (data) => {
  switch (data.type) {
    case "breakout_analysis_update":
      setBreakoutAnalysis(prev => ({
        ...prev,
        ...data.data,
        lastUpdated: new Date()
      }));
      break;
  }
};
```

### Component Usage:

```jsx
// BreakoutAnalysisWidget.jsx
const BreakoutAnalysisWidget = ({ data }) => {
  const { breakouts = [], breakdowns = [], summary = {} } = data;
  
  // Combine and sort by timestamp
  const allSignals = [
    ...breakouts.map(b => ({...b, type: "breakout"})),
    ...breakdowns.map(b => ({...b, type: "breakdown"}))
  ].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
  
  return allSignals.map(signal => (
    <Box key={`${signal.instrument_key}-${signal.timestamp}`}>
      <Typography>🚨 {signal.symbol}</Typography>
      <Typography>📈 {signal.breakout_type}</Typography>
      <Typography>💰 ₹{signal.current_price?.toFixed(2)}</Typography>
      <Typography>🕒 {signal.time_ago}</Typography>
      <Typography>📊 {signal.volume_ratio?.toFixed(1)}x volume</Typography>
    </Box>
  ));
};
```

## Real Example Data Sent to UI

### Actual WebSocket Message:

```json
{
  "type": "breakout_analysis_update",
  "data": {
    "breakouts": [
      {
        "instrument_key": "NSE_EQ|INE467B01029",
        "symbol": "RELIANCE",
        "breakout_type": "momentum_breakout",
        "current_price": 2052.66,
        "breakout_price": 2045.30,
        "trigger_price": 2048.50,
        "volume": 2500000,
        "percentage_move": 1.85,
        "strength": 7.2,
        "confidence": 0.855,
        "volume_ratio": 3.2,
        "volatility_score": 15.8,
        "timestamp": "2025-09-07T18:11:47.233Z",
        "market_cap_category": "large_cap", 
        "sector": "ENERGY",
        "confirmation_signals": ["volume_surge", "price_momentum"],
        "time_ago": "just now",
        "epoch_timestamp": 1725711707233
      }
    ],
    "breakdowns": [],
    "summary": {
      "total_breakouts": 1,
      "total_breakdowns": 0,
      "total_today": 1,
      "is_trading_hours": true,
      "detection_active": true,
      "last_update": "2025-09-07T18:11:47.233Z"
    },
    "total_breakouts_today": 1,
    "engine_metrics": {
      "total_scans": 15,
      "breakouts_detected": 1,
      "avg_processing_time_ms": 8.5,
      "instruments_tracked": 2500
    },
    "timestamp": "2025-09-07T18:11:47.233Z",
    "service": "enhanced_breakout_engine"
  }
}
```

## UI Display Result

This data renders in the UI as:

```
┌─────────────────────────────────────┐
│ ⚡ BREAKOUT ANALYSIS    🔴 REAL-TIME │
├─────────────────────────────────────┤
│ 🚨 RELIANCE             🔥 FRESH    │
│ 📈 MOMENTUM BREAKOUT                │
│ 💰 ₹2,052.66                       │
│ 🕒 18:11:47 | just now               │
│ 📊 3.2x Vol | ⚡ 86% conf            │
│ ✅ volume_surge, price_momentum     │
└─────────────────────────────────────┘
```

## Key Features of the Data Format

### **Timestamps:**
- **ISO Format**: `2025-09-07T18:11:47.233Z`
- **Epoch Timestamp**: `1725711707233` (for sorting)
- **Human Readable**: `"just now"`, `"2m ago"`, `"1h 30m ago"`

### **Price Data:**
- **Current Price**: Exact breakout price
- **Breakout Price**: Price where breakout occurred
- **Percentage Move**: Calculated percentage change

### **Volume Data:**
- **Volume**: Actual volume number
- **Volume Ratio**: Multiple of average volume (e.g., 3.2x)

### **Confidence & Strength:**
- **Confidence**: 0.0 to 1.0 (displayed as percentage)
- **Strength**: 1-10 scale for breakout intensity
- **Confirmation Signals**: Array of validation signals

This format ensures the UI receives complete, structured data for real-time breakout display with precise timestamps and all necessary trading information!