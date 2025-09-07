# TRUE HFT System Architecture - Common Integration Points

## 🔥 MAIN DATA FLOW (Producer-Consumer Pattern)

```
Live WebSocket Feed 
    ↓
centralized_ws_manager.py (PRODUCER)
    ↓ 
    └── async def _handle_feeds_data(data)
        └── hft_hub.ingest_feeds_data(feeds)
    ↓
HFT Data Hub (CORE BROKER/DISTRIBUTOR)
    ↓
    └── async def _broadcast_to_all_services(feeds)
        ├── Enhanced Market Analytics (CONSUMER)
        ├── Dashboard Stream Service (CONSUMER)  
        ├── Breakout Scanner Service (CONSUMER)
        ├── Gap Detection Service (CONSUMER)
        └── Strategy Services (CONSUMER)
```

## 🔥 COMMON INTEGRATION POINT #1: HFT Data Hub

**Location**: `services/hft_data_hub.py`

### Producer Interface (Data Ingestion)
```python
# Main entry point for all live data
async def ingest_feeds_data(self, feeds: Dict[str, Any]) -> bool:
    """
    COMMON PRODUCER INTERFACE
    - Called by centralized_ws_manager 
    - Processes live WebSocket feed data
    - Triggers broadcast to all consumers
    """
```

### Consumer Interface (Service Integration)
```python
# Method 1: Direct data access
def get_live_price(self, instrument_key: str) -> Optional[Dict[str, Any]]
def get_bulk_price_data(self, instrument_keys: List[str]) -> Dict[str, Dict[str, Any]]

# Method 2: Callback registration (Real-time push)
def register_callback(self, callback_func, service_name: str)

# Method 3: Vectorized operations (Ultra-fast)
def get_top_movers_vectorized(self, limit: int = 20) -> Tuple[np.ndarray, np.ndarray]
```

## 🔥 COMMON INTEGRATION POINT #2: Symbol/Sector/Name Metadata

**Location**: `services/instrument_registry.py`

### Metadata Structure
```python
# How symbols, sectors, names are stored and accessed
self._enriched_prices = {
    "NSE_EQ|RELIANCE": {
        "symbol": "RELIANCE",           # ← SYMBOL
        "name": "Reliance Industries",  # ← NAME  
        "sector": "ENERGY",            # ← SECTOR
        "trading_symbol": "RELIANCE",
        "exchange": "NSE",
        "instrument_type": "EQ",
        "ltp": 2456.75,
        "change": 45.20,
        "change_percent": 1.87,
        "volume": 2500000,
        # ... other price data
    }
}
```

### Common Metadata Access Pattern
```python
# ALL SERVICES use this same pattern:
def get_enriched_data_with_metadata():
    # 1. Get data from HFT Hub (if available)
    if HFT_SYSTEM_AVAILABLE:
        data = hft_hub.get_all_live_data()
    
    # 2. Fallback to instrument registry
    else:
        data = instrument_registry.get_enriched_prices()
    
    # 3. Extract common fields that ALL services need
    for instrument_key, stock_data in data.items():
        symbol = stock_data.get("symbol", "N/A")     # ← SYMBOL
        name = stock_data.get("name", symbol)        # ← NAME
        sector = stock_data.get("sector", "OTHER")   # ← SECTOR
        ltp = stock_data.get("ltp", 0)
        change_percent = stock_data.get("change_percent", 0)
        volume = stock_data.get("volume", 0)
```

## 🔥 SERVICE INTEGRATION PATTERNS

### Pattern 1: Enhanced Market Analytics Integration
**File**: `services/enhanced_market_analytics.py`

```python
class EnhancedMarketAnalyticsService:
    def __init__(self):
        # 1. Register with HFT Data Hub
        if HFT_DATA_HUB_AVAILABLE:
            self._hft_hub = get_hft_hub()
            self.hft_callback_registered = True
    
    def _get_cached_enriched_data(self):
        # 2. Priority: HFT Data first, fallback to legacy
        if HFT_DATA_HUB_AVAILABLE:
            return self._get_hft_data()
        else:
            return instrument_registry.get_enriched_prices()
    
    def get_top_gainers_losers(self):
        # 3. Use common data with metadata
        market_data = self._get_cached_enriched_data()
        for instrument_key, data in market_data.items():
            symbol = data.get("symbol", "N/A")    # ← SAME PATTERN
            sector = data.get("sector", "OTHER")  # ← SAME PATTERN
            name = data.get("name", symbol)       # ← SAME PATTERN
```

### Pattern 2: Breakout Scanner Integration
**File**: `services/breakout_scanner_service.py`

```python
class BreakoutScannerService:
    def __init__(self):
        # 1. Register with HFT Data Hub (SAME PATTERN)
        self.data_source = "hft_hub" if HFT_SYSTEM_AVAILABLE else "instrument_registry"
    
    async def process_live_data(self):
        # 2. Get data using same pattern
        if self.data_source == "hft_hub":
            live_data = hft_hub.get_bulk_price_data(self.monitored_instruments)
        else:
            live_data = instrument_registry.get_enriched_prices()
        
        # 3. Process with same metadata extraction
        for instrument_key, data in live_data.items():
            symbol = data.get("symbol", "N/A")    # ← SAME PATTERN
            sector = data.get("sector", "OTHER")  # ← SAME PATTERN
            ltp = data.get("ltp", 0)
            
            # 4. Breakout detection logic
            breakout_signal = self.detect_breakout(symbol, ltp, data)
```

### Pattern 3: Gap Detection Integration
**File**: `services/gap_detector_service.py`

```python
class GapDetectorService:
    def __init__(self):
        # 1. Same HFT registration pattern
        self._register_with_hft_hub()
    
    def scan_for_gaps(self):
        # 2. Same data access pattern
        market_data = self._get_market_data_with_hft_priority()
        
        # 3. Same metadata extraction
        for instrument_key, data in market_data.items():
            symbol = data.get("symbol", "N/A")    # ← SAME PATTERN
            sector = data.get("sector", "OTHER")  # ← SAME PATTERN
            name = data.get("name", symbol)       # ← SAME PATTERN
            
            # 4. Gap detection logic
            gap_signal = self.calculate_gap(symbol, data)
```

## 🔥 STRATEGY SERVICE INTEGRATION

### Common Strategy Pattern
```python
class AnyTradingStrategy:
    def __init__(self):
        # 1. ALWAYS register with HFT Data Hub first
        self._hft_hub = get_hft_hub() if HFT_SYSTEM_AVAILABLE else None
        self._fallback_registry = instrument_registry
        
        # 2. Subscribe to specific instruments
        self.monitored_symbols = ["RELIANCE", "TCS", "INFY"]
        self.instrument_keys = self._resolve_symbol_to_keys(self.monitored_symbols)
        
        # 3. Register callback for real-time updates
        if self._hft_hub:
            self._hft_hub.register_callback(
                callback=self._on_price_update,
                service_name=f"strategy_{self.__class__.__name__}"
            )
    
    def _get_live_data(self):
        """COMMON DATA ACCESS - ALL STRATEGIES USE THIS"""
        if self._hft_hub:
            return self._hft_hub.get_bulk_price_data(self.instrument_keys)
        else:
            return self._fallback_registry.get_enriched_prices()
    
    def _on_price_update(self, feeds_data, timestamp_ms, stats):
        """COMMON CALLBACK - ALL STRATEGIES GET REAL-TIME UPDATES"""
        for instrument_key, price_data in feeds_data.items():
            if instrument_key in self.instrument_keys:
                # Extract common metadata (SAME FOR ALL)
                symbol = price_data.get("symbol", "N/A")
                ltp = price_data.get("ltp", 0)
                change_percent = price_data.get("change_percent", 0)
                
                # Strategy-specific logic
                self._execute_strategy_logic(symbol, ltp, price_data)
```

## 🔥 HOW TO ADD NEW SERVICES/STRATEGIES

### Step 1: Service Registration
```python
# In your new service __init__
def __init__(self):
    # Register with HFT Data Hub
    self._hft_hub = get_hft_hub() if HFT_SYSTEM_AVAILABLE else None
    
    # Register callback for real-time updates
    if self._hft_hub:
        self._hft_hub.register_callback(
            callback=self._handle_price_updates,
            service_name="your_service_name"
        )
```

### Step 2: Data Access Pattern
```python
def _get_market_data(self):
    """Standard data access - use this exact pattern"""
    if self._hft_hub:
        return self._hft_hub.get_bulk_price_data(self.instrument_keys)
    else:
        from services.instrument_registry import instrument_registry
        return instrument_registry.get_enriched_prices()
```

### Step 3: Metadata Extraction
```python
def _process_data(self, market_data):
    """Standard metadata extraction - use this exact pattern"""
    for instrument_key, data in market_data.items():
        # Extract common fields (SAME FOR ALL SERVICES)
        symbol = data.get("symbol", "N/A")           # ← SYMBOL
        name = data.get("name", symbol)              # ← NAME
        sector = data.get("sector", "OTHER")         # ← SECTOR
        ltp = data.get("ltp", 0)                    # ← PRICE
        change_percent = data.get("change_percent", 0) # ← CHANGE
        volume = data.get("volume", 0)               # ← VOLUME
        
        # Your service-specific logic here
        your_logic(symbol, name, sector, ltp, change_percent, volume)
```

## 🔥 CURRENT SERVICES USING THIS PATTERN

1. **Enhanced Market Analytics** ✅ - Uses HFT priority data access
2. **HFT Dashboard Stream** ✅ - Real-time UI broadcasting  
3. **HFT Stocks Router** ✅ - Server-Sent Events for stocks section
4. **Breakout Scanner** ⚠️ - Needs HFT integration update
5. **Gap Detection** ⚠️ - Needs HFT integration update
6. **Strategy Services** ⚠️ - Need HFT integration update

## 🔥 REQUIRED UPDATES FOR REMAINING SERVICES

### For Breakout Scanner:
```python
# Add to services/breakout_scanner_service.py
from services.hft_data_hub import get_hft_hub, HFT_SYSTEM_AVAILABLE

class BreakoutScannerService:
    def __init__(self):
        # Add HFT integration
        self._hft_hub = get_hft_hub() if HFT_SYSTEM_AVAILABLE else None
        if self._hft_hub:
            self._hft_hub.register_callback(
                callback=self._handle_hft_update,
                service_name="breakout_scanner"
            )
```

### For Gap Detection:
```python
# Add to services/gap_detector_service.py  
from services.hft_data_hub import get_hft_hub, HFT_SYSTEM_AVAILABLE

class GapDetectorService:
    def __init__(self):
        # Add HFT integration
        self._hft_hub = get_hft_hub() if HFT_SYSTEM_AVAILABLE else None
        if self._hft_hub:
            self._hft_hub.register_callback(
                callback=self._handle_hft_update,
                service_name="gap_detector"
            )
```

## 📊 SUMMARY

**Common Integration Point**: `services/hft_data_hub.py`
- **Producer**: `centralized_ws_manager.py` → `hft_hub.ingest_feeds_data()`
- **Broker/Distributor**: `hft_data_hub._broadcast_to_all_services()`  
- **Consumers**: All services register callbacks and access data via standard patterns

**Common Metadata Source**: `services/instrument_registry.py`
- **Symbols, Names, Sectors**: All stored in `_enriched_prices` dictionary
- **Standard Access Pattern**: All services use same data extraction logic
- **Fallback System**: HFT Data Hub → Instrument Registry → Mock/Empty data

**Integration Pattern**: Every service follows same 3-step pattern:
1. **Register** with HFT Data Hub for real-time updates
2. **Access** data with HFT priority, fallback to instrument registry  
3. **Extract** metadata using common field names (symbol, name, sector)