# Real-Time Breakout Detection Flow in UI

## Complete Data Flow: Backend → Frontend

### 1. **Backend Detection Process**

**Enhanced Breakout Engine (`services/enhanced_breakout_engine.py`)**:
```python
# Real-time detection at 10Hz (100ms intervals)
async def _detect_breakouts_vectorized(self):
    # Vectorized breakout detection using NumPy
    volume_breakouts = fast_volume_breakout_check(...)
    momentum_breakouts = fast_momentum_breakout_check(...)
    resistance_breakouts = fast_resistance_breakout_check(...)
    
    # Create breakout signals with precise timestamps
    for i in range(n_instruments):
        if volume_breakouts[i] == 1:
            signal = BreakoutSignal(
                timestamp=datetime.now(),  # ← PRECISE TIMESTAMP
                symbol=symbol,
                breakout_type=BreakoutType.VOLUME_BREAKOUT,
                current_price=current_price,
                confidence=confidence,
                # ... other fields
            )
            new_breakouts.append(signal)
    
    # Broadcast immediately to UI
    if new_breakouts:
        await self._broadcast_breakouts(new_breakouts)
```

### 2. **WebSocket Broadcasting**

**Unified Manager Broadcasting (`services/unified_websocket_manager.py`)**:
```python
async def _broadcast_breakouts(self, breakouts):
    broadcast_data = {
        "type": "breakout_analysis_update",  # ← KEY EVENT TYPE
        "data": {
            "breakouts": [b.to_dict() for b in breakouts],
            "total_breakouts_today": len(self.daily_breakouts),
            "timestamp": datetime.now().isoformat()
        }
    }
    
    # Broadcast to all connected WebSocket clients
    self.unified_manager.emit_event("breakout_analysis_update", broadcast_data, priority=1)
```

### 3. **Frontend Reception**

**WebSocket Hook (`hooks/useUnifiedMarketData.js`)**:
```javascript
// State for breakout data
const [breakoutAnalysis, setBreakoutAnalysis] = useState({
    breakouts: [],
    breakdowns: [],
    total_breakouts_today: 0,
    timestamp: null
});

// Message handler
const handleMessage = useCallback((data) => {
    switch (data.type) {
        case "breakout_analysis_update":
            // Real-time update of breakout data
            setBreakoutAnalysis(prev => ({
                ...prev,
                ...data.data,
                lastUpdated: new Date()
            }));
            break;
        // ... other cases
    }
}, []);
```

### 4. **UI Display Components**

**Breakout Analysis Widget (`components/dashboard/BreakoutAnalysisWidget.js`)**:
```jsx
const BreakoutAnalysisWidget = ({ data, isLoading }) => {
    // Extract breakout data from WebSocket
    const { breakouts = [], breakdowns = [], summary = {} } = data;
    
    // Real-time sorting by timestamp (newest first)
    const filteredSignals = allSignals
        .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    
    // Display each breakout with precise timing
    const renderBreakoutSignal = (signal) => {
        const displayTime = signal.timestamp 
            ? new Date(signal.timestamp).toLocaleTimeString("en-US", {
                hour12: false,
                hour: "2-digit", 
                minute: "2-digit",
                second: "2-digit"
            })
            : "N/A";
        
        return (
            <Box>
                <Typography>🚨 {signal.symbol}</Typography>
                <Typography>📈 {signal.breakout_type}</Typography>
                <Typography>🕒 {displayTime}</Typography>
                <Typography>💰 ₹{signal.current_price?.toFixed(2)}</Typography>
                <Typography>📊 {signal.volume_ratio?.toFixed(1)}x volume</Typography>
            </Box>
        );
    };
};
```

**Enhanced Breakout Widget (`components/dashboard/EnhancedBreakoutWidget.js`)**:
```jsx
const EnhancedBreakoutWidget = ({ data, realTimeEnabled = true }) => {
    // Real-time indicators
    {realTimeEnabled && (
        <Chip 
            label="LIVE" 
            sx={{ 
                backgroundColor: "#4CAF50", 
                animation: "pulse 2s infinite"  // ← LIVE INDICATOR
            }} 
        />
    )}
    
    // Auto-refresh timer for real-time updates
    useEffect(() => {
        if (autoRefresh && onRefresh) {
            const interval = setInterval(onRefresh, 10000); // Every 10 seconds
            return () => clearInterval(interval);
        }
    }, [autoRefresh, onRefresh]);
    
    // Display breakout with time calculation
    const getTimeAgo = (timestamp) => {
        const now = new Date();
        const past = new Date(timestamp);
        const diffInSeconds = Math.floor((now - past) / 1000);
        
        if (diffInSeconds < 60) return `${diffInSeconds}s ago`;
        if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
        // ... time calculations
    };
};
```

## Real-Time Display Features

### **1. Live Breakout Detection**
- **Detection Speed**: 100ms processing loops (10Hz)
- **Timestamp Precision**: Exact detection time with millisecond accuracy
- **Immediate Broadcasting**: Zero-delay WebSocket push to UI

### **2. UI Real-Time Updates**
```jsx
// Live indicators
<Chip label="REAL-TIME" sx={{ animation: "pulse 2s infinite" }} />
<Chip label="LIVE" sx={{ backgroundColor: "#4CAF50" }} />

// Fresh breakout highlighting
{timeAgo.includes("min") && parseInt(timeAgo) <= 15 && (
    <Box sx={{ 
        backgroundColor: `${bloombergColors.accent}80`,
        color: "white"
    }}>
        🔥 FRESH
    </Box>
)}

// Time ago calculations
"Just now"     // < 1 minute
"2m ago"       // < 1 hour  
"1h 30m ago"   // < 1 day
```

### **3. Visual Real-Time Indicators**

**Fresh Breakout Highlighting**:
- **"🔥 FRESH"** badge for breakouts < 15 minutes old
- **Pulsing animation** for live data indicator
- **Color-coded timestamps** (green for recent, fading to gray)

**Real-Time Sorting**:
- Always shows newest breakouts first
- Timestamp-based sorting: `new Date(b.timestamp) - new Date(a.timestamp)`

**Live Volume Indicators**:
- **"2.5x Vol"** chips for unusual volume
- **Volume ratio calculations**: `volume_ratio.toFixed(1)x Vol`
- **Real-time volume formatting**: `Vol: 245K` or `Vol: 2.5Cr`

## Sample Real-Time Flow

### **Breakout Detection** (Backend):
```
17:12:45.301 - 🚨 Detected 1 breakouts via vectorized processing
17:12:45.301 - 📡 Broadcasted breakout analysis via unified manager

Signal: {
    symbol: "RELIANCE",
    breakout_type: "momentum_breakout",
    current_price: 2205.40,
    timestamp: "2025-09-07T17:12:45.301Z",
    volume_ratio: 3.2,
    confidence: 85.5
}
```

### **WebSocket Message** (Real-Time):
```json
{
    "type": "breakout_analysis_update",
    "data": {
        "breakouts": [{
            "symbol": "RELIANCE",
            "breakout_type": "momentum_breakout",
            "current_price": 2205.40,
            "timestamp": "2025-09-07T17:12:45.301Z",
            "time_ago": "just now",
            "epoch_timestamp": 1725711765301
        }],
        "total_breakouts_today": 1
    }
}
```

### **UI Display** (Immediate):
```
🚨 RELIANCE                    🔥 FRESH
📈 MOMENTUM BREAKOUT           ⚡ 85.5% conf
💰 ₹2,205.40                   🕒 17:12:45
📊 3.2x Vol | just now         🔴 LIVE
```

## Testing Real-Time Flow

You can test the real-time flow using our test endpoints:

1. **Check Status**: `GET /api/test/breakout/status`
2. **Trigger Detection**: `POST /api/test/breakout/test-enhanced-engine`
3. **View Breakouts**: `GET /api/test/breakout/breakouts`

The breakouts will appear in the UI widgets with precise timestamps and real-time indicators showing exactly when they were detected!