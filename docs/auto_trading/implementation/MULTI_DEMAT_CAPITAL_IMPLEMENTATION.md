# Multi-Demat Capital Management System - Implementation Guide

## ✅ Phase 1: COMPLETED - Capital Aggregation & UI Display

### What Was Implemented

#### 1. **MultiDematCapitalService** ✅
**File**: [services/trading_execution/multi_demat_capital_service.py](services/trading_execution/multi_demat_capital_service.py)

**Features**:
- ✅ Aggregates capital from ALL active demat accounts for a user
- ✅ Supports both Paper Trading (₹10L virtual) and Live Trading (real broker funds)
- ✅ Validates token validity before including demat in capital pool
- ✅ Calculates proportional allocation across demats based on available margin
- ✅ Tracks capital utilization per demat from active positions
- ✅ Provides trade validation with capital availability check

**Key Methods**:
```python
# Get total capital overview
get_user_total_capital(user_id, db, trading_mode="live")

# Calculate proportional allocation
calculate_proportional_allocation(demats, total_allocation)

# Get capital summary for trade
get_capital_summary_for_trade(user_id, required_capital, db, trading_mode)
```

**Capital Aggregation Logic**:
```python
# Query all active demats with valid tokens
active_brokers = db.query(BrokerConfig).filter(
    BrokerConfig.user_id == user_id,
    BrokerConfig.is_active == True,
    BrokerConfig.access_token.isnot(None),
    BrokerConfig.available_margin.isnot(None)
).all()

# Calculate totals
for broker in active_brokers:
    if token_valid:
        total_available += broker.available_margin
        total_used += broker.used_margin
```

#### 2. **API Endpoints** ✅
**File**: [router/trading_execution_router.py](router/trading_execution_router.py:463)

**New Endpoints**:

1. **GET `/api/v1/trading/execution/user-capital-overview`**
   - Query Parameters: `trading_mode` (paper/live)
   - Returns: Total capital + per-demat breakdown

2. **POST `/api/v1/trading/execution/capital-allocation-plan`**
   - Query Parameters: `required_capital`, `trading_mode`
   - Returns: Allocation plan across demats + execution feasibility

**Response Format**:
```json
{
  "success": true,
  "capital_overview": {
    "user_id": 1,
    "trading_mode": "live",
    "total_available_capital": 500000,
    "total_used_margin": 100000,
    "total_free_margin": 400000,
    "capital_utilization_percent": 20,
    "max_trade_allocation": 100000,
    "demats": [
      {
        "broker_name": "upstox",
        "available_margin": 300000,
        "used_margin": 50000,
        "free_margin": 250000,
        "is_active": true,
        "token_valid": true,
        "utilization_percent": 16.67
      },
      {
        "broker_name": "angel_one",
        "available_margin": 200000,
        "used_margin": 50000,
        "free_margin": 150000,
        "is_active": true,
        "token_valid": true,
        "utilization_percent": 25
      }
    ],
    "total_demats": 2,
    "active_demats": 2
  }
}
```

#### 3. **UI - Capital Overview Dashboard** ✅
**File**: [ui/trading-bot-ui/src/pages/AutoTradingPage.js](ui/trading-bot-ui/src/pages/AutoTradingPage.js:542)

**New UI Components**:

1. **Capital Overview Card** (Lines 542-683)
   - Total Available Capital (aggregated)
   - Total Used Margin
   - Total Free Margin
   - Max Per Trade Allocation (60% of total)
   - Active Demats Count

2. **Per-Demat Breakdown Table**
   - Broker Name
   - Available Margin
   - Used Margin
   - Free Margin (color-coded)
   - Utilization % (progress bar with color indicators)
   - Token Status (Active/Expired chip)

**Real-time Updates**:
- Capital data refreshes every 2 seconds
- Automatically updates when switching between Paper/Live mode
- Shows live utilization changes as trades are executed

**UI Features**:
```jsx
// Capital state management
const [capitalData, setCapitalData] = useState({
  total_available_capital: 0,
  total_used_margin: 0,
  total_free_margin: 0,
  capital_utilization_percent: 0,
  max_trade_allocation: 0,
  demats: [],
  total_demats: 0,
  active_demats: 0
});

// Fetch capital overview
const fetchCapitalOverview = useCallback(async () => {
  const response = await api.get(
    `/v1/trading/execution/user-capital-overview?trading_mode=${tradingMode}`
  );
  setCapitalData(response.data.capital_overview);
}, [tradingMode]);

// Auto-refresh every 2 seconds
useEffect(() => {
  const interval = setInterval(() => {
    fetchCapitalOverview();
  }, 2000);
}, []);
```

---

## 📋 Phase 2: PENDING - Multi-Demat Trade Execution

### What Needs to Be Implemented

#### 1. **MultiDematTradeExecutor** 🔄
**File**: `services/trading_execution/multi_demat_executor.py` (TO BE CREATED)

**Purpose**: Execute same trade across ALL active demats in parallel

**Key Features**:
- ✅ Get all active demats with valid tokens
- ✅ Calculate proportional capital allocation per demat
- ✅ Execute trades in parallel using `asyncio.gather()`
- ✅ Create separate `AutoTradeExecution` record per demat
- ✅ Return aggregated results

**Implementation**:
```python
class MultiDematTradeExecutor:
    async def execute_across_all_demats(
        user_id: int,
        stock_selection: Dict,
        trading_mode: TradingMode,
        db: Session
    ) -> Dict:
        """Execute trade in ALL active demats"""

        # Step 1: Get capital overview
        capital = multi_demat_capital_service.get_user_total_capital(
            user_id, db, trading_mode
        )

        # Step 2: Calculate required capital for trade
        required_capital = calculate_trade_capital(stock_selection)

        # Step 3: Get allocation plan
        allocation_plan = multi_demat_capital_service.get_capital_summary_for_trade(
            user_id, required_capital, db, trading_mode
        )

        if not allocation_plan["can_execute"]:
            return {
                "success": False,
                "error": allocation_plan["reason"]
            }

        # Step 4: Execute in parallel across all demats
        tasks = []
        for allocation in allocation_plan["allocation_plan"]:
            task = self._execute_single_demat(
                user_id,
                allocation["broker_name"],
                stock_selection,
                allocation["allocated_capital"],
                trading_mode,
                db
            )
            tasks.append(task)

        # Execute all trades in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return self._aggregate_results(results)
```

#### 2. **Update AutoTradeExecution Model** 🔄
**File**: `database/models.py`

**Add Fields**:
```python
class AutoTradeExecution(Base):
    # ... existing fields ...

    # NEW: Multi-demat support
    broker_name = Column(String, nullable=True)  # Which broker executed this trade
    broker_config_id = Column(Integer, ForeignKey("broker_configs.id"), nullable=True)
    allocated_capital = Column(Float, nullable=True)  # Capital allocated for this demat
    parent_trade_id = Column(String, nullable=True)  # Link multiple demat executions
```

#### 3. **Update Auto-Execute Endpoint** 🔄
**File**: `router/trading_execution_router.py`

**Modify**:
```python
@router.post("/auto-execute-selected-stocks")
async def auto_execute_selected_stocks(
    trading_mode: str = Query("paper"),
    execute_mode: str = Query("multi_demat", description="single_demat or multi_demat"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Auto-execute with multi-demat support"""

    if execute_mode == "multi_demat":
        # Use MultiDematTradeExecutor
        from services.trading_execution.multi_demat_executor import multi_demat_executor

        for selection in final_selections:
            result = await multi_demat_executor.execute_across_all_demats(
                user_id=current_user.id,
                stock_selection=selection,
                trading_mode=TradingMode(trading_mode),
                db=db
            )
    else:
        # Existing single demat execution
        # ... existing code ...
```

---

## 📋 Phase 3: PENDING - Spot Market Strategy Execution

#### **SpotStrategyExecutor** 🔄
**File**: `services/trading_execution/spot_strategy_executor.py` (TO BE CREATED)

**Purpose**: Run SuperTrend+EMA on SPOT price, execute in OPTIONS

**Why Important**:
- Option premiums are volatile and affected by Greeks (delta, theta, vega)
- Spot prices are more stable and reliable for technical indicators
- Better signal quality from spot charts

**Implementation**:
```python
class SpotStrategyExecutor:
    async def execute_with_spot_strategy(
        stock_symbol: str,
        spot_instrument_key: str,  # NSE_EQ|INE318A01026
        option_instrument_key: str,  # NSE_FO|RELIANCE24DEC3100CE
        option_type: str,  # CE or PE
        lot_size: int,
        db: Session
    ):
        # 1. Fetch spot historical data (100 candles for indicators)
        spot_history = await self._fetch_spot_historical_data(
            spot_instrument_key,
            interval="1m",
            count=100
        )

        # 2. Calculate SuperTrend and EMA on SPOT data
        supertrend_1x, trend_1x = calculate_supertrend(
            spot_history["high"],
            spot_history["low"],
            spot_history["close"],
            period=10,
            multiplier=3.0
        )

        ema_20 = calculate_ema(spot_history["close"], period=20)

        # 3. Get current spot price
        current_spot = await self._get_live_spot_price(spot_instrument_key)

        # 4. Generate signal from SPOT
        signal = self._generate_signal(current_spot, supertrend_1x[-1], ema_20[-1])

        if signal == "BUY":
            # 5. Fetch current option premium
            option_premium = await self._get_option_premium(option_instrument_key)

            # 6. Calculate SL and Target based on SPOT
            stop_loss = supertrend_1x[-1]
            risk = abs(current_spot - stop_loss)
            target = current_spot + (risk * 2)  # 1:2 R:R

            # 7. Execute OPTION trade
            return await self._execute_option_trade(
                option_instrument_key,
                entry_price=option_premium,
                stop_loss_spot=stop_loss,
                target_spot=target,
                monitor_instrument=spot_instrument_key  # Monitor SPOT for exit
            )
```

---

## 📋 Phase 4: PENDING - Trade Audit Trail

#### **TradeAuditLog Model** 🔄
**File**: `database/models.py` (ADD THIS)

```python
class TradeAuditLog(Base):
    __tablename__ = "trade_audit_log"

    id = Column(Integer, primary_key=True)
    trade_execution_id = Column(Integer, ForeignKey("auto_trade_executions.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    broker_name = Column(String)

    # Capital Impact
    capital_before = Column(Float)
    capital_allocated = Column(Float)
    capital_after = Column(Float)

    # Trade Details
    action = Column(String)  # ENTRY, EXIT, SL_HIT, TARGET_HIT
    instrument_key = Column(String)
    price = Column(Float)
    quantity = Column(Integer)
    order_id = Column(String)

    # Strategy Info
    signal_type = Column(String)
    spot_price = Column(Float)
    supertrend_value = Column(Float)
    ema_value = Column(Float)

    # PnL
    realized_pnl = Column(Float, nullable=True)
    unrealized_pnl = Column(Float, nullable=True)

    timestamp = Column(DateTime, default=func.now())
    execution_metadata = Column(JSON)
```

#### **AuditService** 🔄
**File**: `services/trading_execution/audit_service.py` (TO BE CREATED)

```python
class TradeAuditService:
    def log_trade_execution(
        trade_id: int,
        user_id: int,
        broker_name: str,
        action: str,
        capital_impact: Dict,
        trade_details: Dict,
        db: Session
    ):
        """Log every trade action"""
        audit_log = TradeAuditLog(
            trade_execution_id=trade_id,
            user_id=user_id,
            broker_name=broker_name,
            action=action,
            capital_before=capital_impact["before"],
            capital_allocated=capital_impact["allocated"],
            capital_after=capital_impact["after"],
            **trade_details
        )
        db.add(audit_log)
        db.commit()
```

---

## 📋 Phase 5: PENDING - Real-Time Capital Utilization Tracker

#### **CapitalUtilizationTracker** 🔄
**File**: `services/trading_execution/capital_utilization_tracker.py` (TO BE CREATED)

```python
class CapitalUtilizationTracker:
    """Tracks real-time capital utilization"""

    async def start_tracking(self):
        while self.is_running:
            users_with_trades = self._get_users_with_active_positions()

            for user_id in users_with_trades:
                utilization = await self._calculate_utilization(user_id)
                await self._broadcast_capital_update(user_id, utilization)

            await asyncio.sleep(2)

    async def _calculate_utilization(self, user_id: int) -> Dict:
        """Calculate per-demat utilization"""
        capital_data = multi_demat_capital_service.get_user_total_capital(
            user_id, db, "live"
        )

        return {
            "user_id": user_id,
            "total_utilization": capital_data["capital_utilization_percent"],
            "demats": [
                {
                    "broker": d["broker_name"],
                    "utilization": d["utilization_percent"],
                    "free_margin": d["free_margin"]
                }
                for d in capital_data["demats"]
            ]
        }
```

---

## 🚀 Implementation Priority

### ✅ COMPLETED (Phase 1)
1. ✅ MultiDematCapitalService - Capital aggregation
2. ✅ API endpoints for capital overview
3. ✅ UI Capital Dashboard with per-demat breakdown
4. ✅ Real-time capital updates (2-second refresh)

### 🔄 NEXT STEPS (Recommended Order)

**Phase 2** - Multi-Demat Execution (HIGHEST PRIORITY):
1. Create `MultiDematTradeExecutor` service
2. Update `AutoTradeExecution` model with broker fields
3. Create Alembic migration for new fields
4. Update auto-execute endpoint to support multi-demat mode
5. Test parallel execution with 2-3 demats

**Phase 3** - Spot Strategy Execution:
1. Create `SpotStrategyExecutor` service
2. Add spot instrument mapping in stock selection
3. Implement historical data fetching for spot
4. Update strategy execution to monitor spot for exits

**Phase 4** - Audit Trail:
1. Create `TradeAuditLog` model
2. Create Alembic migration
3. Implement `AuditService`
4. Add audit logging to all trade actions
5. Create audit trail API endpoint

**Phase 5** - Capital Utilization Tracker:
1. Create `CapitalUtilizationTracker` service
2. Add WebSocket broadcast for capital updates
3. Start tracker in app lifespan
4. Add real-time UI updates

---

## 📊 Testing Checklist

### Phase 1 (Completed) ✅
- [x] Test capital aggregation with single demat
- [x] Test capital aggregation with multiple demats
- [x] Test paper trading capital (₹10L virtual)
- [x] Test live trading capital from broker API
- [x] Test token validation logic
- [x] Test UI capital dashboard display
- [x] Test per-demat breakdown table
- [x] Test real-time capital updates
- [x] Test trading mode toggle (paper ↔ live)

### Phase 2 (Pending) 🔄
- [ ] Test multi-demat trade execution
- [ ] Test proportional capital allocation
- [ ] Test parallel execution with asyncio
- [ ] Test individual demat failures
- [ ] Test aggregated results
- [ ] Test trade records per demat

### Phase 3 (Pending) 🔄
- [ ] Test spot data fetching
- [ ] Test SuperTrend calculation on spot
- [ ] Test signal generation from spot
- [ ] Test option execution with spot signals
- [ ] Test monitoring spot for exits

### Phase 4 (Pending) 🔄
- [ ] Test audit log creation
- [ ] Test capital impact logging
- [ ] Test strategy metadata logging
- [ ] Test audit trail query endpoint

### Phase 5 (Pending) 🔄
- [ ] Test capital utilization tracking
- [ ] Test WebSocket broadcasts
- [ ] Test real-time UI updates
- [ ] Test tracker startup/shutdown

---

## 📁 Files Modified/Created

### ✅ Created (Phase 1)
- `services/trading_execution/multi_demat_capital_service.py` (NEW)
- Updated: `router/trading_execution_router.py` (added 2 endpoints)
- Updated: `ui/trading-bot-ui/src/pages/AutoTradingPage.js` (capital dashboard)

### 🔄 To Be Created (Phases 2-5)
- `services/trading_execution/multi_demat_executor.py`
- `services/trading_execution/spot_strategy_executor.py`
- `services/trading_execution/audit_service.py`
- `services/trading_execution/capital_utilization_tracker.py`
- Alembic migration for `AutoTradeExecution` and `TradeAuditLog`

---

## 🎯 Current System Status

✅ **FULLY OPERATIONAL**:
- Multi-demat capital aggregation
- Real-time capital overview UI
- Per-demat breakdown display
- Token validation
- Capital utilization tracking from active positions
- Paper/Live mode support

🔄 **NEXT TO IMPLEMENT**:
- Multi-demat parallel trade execution (Phase 2)
- Spot-based strategy execution (Phase 3)
- Complete audit trail system (Phase 4)
- Real-time capital utilization broadcaster (Phase 5)

---

## 📞 Support

For questions or issues:
1. Check AUTO_TRADING_FLOW.md for complete system flow
2. Review COMPLETE_TRADING_SYSTEM_GUIDE.md for architecture
3. See TRADING_EXECUTION_ARCHITECTURE.md for technical details
