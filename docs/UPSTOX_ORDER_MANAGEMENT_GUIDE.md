# Upstox Order Management V3 API - Complete Guide

## Overview

Complete implementation of Upstox Order Management V3 APIs integrated with the auto-trading system. This module provides production-grade order placement, modification, cancellation, and position management with auto-slicing support.

## Features

✅ **Place Order V3** - Single order placement with auto-slicing
✅ **Place Multi Order** - Batch order placement (up to 25 orders)
✅ **Modify Order V3** - Modify existing open/pending orders
✅ **Cancel Order V3** - Cancel single order
✅ **Cancel Multi Order** - Bulk cancel with filters
✅ **Exit All Positions** - Close all positions with filters
✅ **Get Order Details** - Fetch order status
✅ **Get Order History** - View order progression
✅ **Auto-Slicing** - Automatic freeze quantity handling
✅ **Latency Tracking** - Performance monitoring
✅ **Comprehensive Error Handling** - Production-ready validation

## Architecture

### Service Layer
**Location:** `services/upstox/upstox_order_service.py`

```python
from services.upstox.upstox_order_service import get_upstox_order_service

# Initialize service
service = get_upstox_order_service(
    access_token="your_access_token",
    use_sandbox=False  # Set True for testing
)
```

### API Layer
**Location:** `router/upstox_order_router.py`

All endpoints are under `/api/v1/upstox/orders`

### Integration Points

1. **Trading Execution** (`services/trading_execution/execution_handler.py`)
   - Automatic order placement during trade execution
   - Supports both paper and live trading

2. **PnL Tracker** (`services/trading_execution/pnl_tracker.py`)
   - Automatic exit order placement when SL/Target hit
   - Position closure with real broker API calls

## API Endpoints

### 1. Place Order

**Endpoint:** `POST /api/v1/upstox/orders/place`

**Request:**
```json
{
  "quantity": 1,
  "instrument_token": "NSE_EQ|INE848E01016",
  "order_type": "MARKET",
  "transaction_type": "BUY",
  "product": "D",
  "validity": "DAY",
  "price": 0.0,
  "trigger_price": 0.0,
  "disclosed_quantity": 0,
  "is_amo": false,
  "tag": "my_order",
  "slice": true
}
```

**Response:**
```json
{
  "success": true,
  "status": "success",
  "data": {
    "order_ids": ["240108010918222"],
    "total_orders": 1
  },
  "metadata": {
    "latency": 45
  },
  "message": "Order placed successfully (1 orders)"
}
```

**Order Types:**
- `MARKET` - Market order (executes at current price)
- `LIMIT` - Limit order (executes at specified price or better)
- `SL` - Stop Loss Limit
- `SL-M` - Stop Loss Market

**Product Types:**
- `D` - Delivery
- `I` - Intraday
- `MTF` - Margin Trading Facility

**Validity:**
- `DAY` - Valid for the day
- `IOC` - Immediate or Cancel

### 2. Place Multi Order

**Endpoint:** `POST /api/v1/upstox/orders/place-multi`

**Request:**
```json
[
  {
    "correlation_id": "1",
    "quantity": 25,
    "instrument_token": "NSE_FO|62864",
    "order_type": "MARKET",
    "transaction_type": "BUY",
    "product": "D",
    "validity": "DAY",
    "price": 0,
    "trigger_price": 0,
    "disclosed_quantity": 0,
    "is_amo": false,
    "slice": false
  },
  {
    "correlation_id": "2",
    "quantity": 25,
    "instrument_token": "NSE_FO|62867",
    "order_type": "MARKET",
    "transaction_type": "SELL",
    "product": "D",
    "validity": "DAY",
    "price": 0,
    "trigger_price": 0,
    "disclosed_quantity": 0,
    "is_amo": false,
    "slice": false
  }
]
```

**Response:**
```json
{
  "success": true,
  "status": "success",
  "data": [
    {
      "correlation_id": "1",
      "order_id": "1644490272000"
    },
    {
      "correlation_id": "2",
      "order_id": "2134134141414"
    }
  ],
  "summary": {
    "total": 2,
    "payload_error": 0,
    "success": 2,
    "error": 0
  },
  "message": "Multi order: 2 successful, 0 failed"
}
```

**Notes:**
- Maximum 25 orders per request
- Each order needs unique `correlation_id`
- BUY orders executed first, then SELL

### 3. Modify Order

**Endpoint:** `PUT /api/v1/upstox/orders/modify`

**Request:**
```json
{
  "order_id": "240108010918222",
  "quantity": 3,
  "order_type": "LIMIT",
  "validity": "DAY",
  "price": 16.8,
  "trigger_price": 16.9,
  "disclosed_quantity": 0
}
```

**Response:**
```json
{
  "success": true,
  "status": "success",
  "data": {
    "order_id": "240108010918222"
  },
  "metadata": {
    "latency": 40
  },
  "message": "Order modified successfully"
}
```

### 4. Cancel Order

**Endpoint:** `DELETE /api/v1/upstox/orders/cancel/{order_id}`

**Response:**
```json
{
  "success": true,
  "status": "success",
  "data": {
    "order_id": "240108010445130"
  },
  "metadata": {
    "latency": 30
  },
  "message": "Order cancelled successfully"
}
```

### 5. Cancel Multi Order

**Endpoint:** `DELETE /api/v1/upstox/orders/cancel-multi`

**Query Parameters:**
- `segment` (optional): NSE_EQ, BSE_EQ, NSE_FO, BSE_FO, MCX_FO
- `tag` (optional): Order tag filter

**Examples:**
```bash
# Cancel all orders
DELETE /api/v1/upstox/orders/cancel-multi

# Cancel by segment
DELETE /api/v1/upstox/orders/cancel-multi?segment=NSE_FO

# Cancel by tag
DELETE /api/v1/upstox/orders/cancel-multi?tag=algo_trade
```

**Response:**
```json
{
  "success": true,
  "status": "success",
  "data": {
    "order_ids": [
      "1644490272000",
      "1644490272001",
      "1644490272003"
    ],
    "total_cancelled": 3
  },
  "summary": {
    "total": 3,
    "success": 3,
    "error": 0
  },
  "message": "Cancelled 3 orders"
}
```

**Notes:**
- Maximum 50 orders can be cancelled per request
- Without filters, cancels ALL open orders

### 6. Exit All Positions

**Endpoint:** `POST /api/v1/upstox/orders/exit-positions`

**Query Parameters:**
- `segment` (optional): Market segment filter
- `tag` (optional): Position tag filter (intraday only)

**Examples:**
```bash
# Exit all positions
POST /api/v1/upstox/orders/exit-positions

# Exit by segment
POST /api/v1/upstox/orders/exit-positions?segment=NSE_FO

# Exit by tag
POST /api/v1/upstox/orders/exit-positions?tag=strategy_1
```

**Response:**
```json
{
  "success": true,
  "status": "success",
  "data": {
    "order_ids": [
      "1644490272000",
      "1644490272001"
    ],
    "total_positions_exited": 2
  },
  "summary": {
    "total": 2,
    "success": 2,
    "error": 0
  },
  "message": "Exited 2 positions"
}
```

**Notes:**
- Auto-slicing enabled by default
- MARKET orders used for all exits
- BUY positions exit first, then SELL
- Maximum 50 positions per request
- Does NOT support delivery EQ segment
- Tags only valid for intraday positions

### 7. Get Order Details

**Endpoint:** `GET /api/v1/upstox/orders/details/{order_id}`

**Response:**
```json
{
  "success": true,
  "status": "success",
  "data": {
    "exchange": "NSE",
    "product": "D",
    "price": 571.0,
    "quantity": 1,
    "status": "complete",
    "tag": "auto_trading",
    "instrument_token": "NSE_EQ|INE062A01020",
    "placed_by": "ABC123",
    "trading_symbol": "SBIN-EQ",
    "order_type": "LIMIT",
    "validity": "DAY",
    "trigger_price": 0.0,
    "disclosed_quantity": 0,
    "transaction_type": "BUY",
    "average_price": 570.95,
    "filled_quantity": 1,
    "pending_quantity": 0,
    "status_message": null,
    "exchange_order_id": "1300000025660919",
    "order_id": "231019025562880",
    "variety": "SIMPLE",
    "order_timestamp": "2023-10-19 13:25:13",
    "exchange_timestamp": "2023-10-19 13:25:13",
    "is_amo": false
  },
  "message": "Order details retrieved successfully"
}
```

**Order Statuses:**
- `put order req received` - Order request received
- `validation pending` - Validation in progress
- `open pending` - Opening on exchange
- `open` - Order open on exchange
- `complete` - Order filled completely
- `rejected` - Order rejected
- `cancelled` - Order cancelled
- `trigger pending` - Stop loss waiting for trigger

### 8. Get Order History

**Endpoint:** `GET /api/v1/upstox/orders/history`

**Query Parameters:**
- `order_id` (optional): Specific order ID
- `tag` (optional): Order tag filter

**Examples:**
```bash
# Get history for specific order
GET /api/v1/upstox/orders/history?order_id=240108010445130

# Get history by tag
GET /api/v1/upstox/orders/history?tag=algo_trade

# Get history for order with tag (both filters)
GET /api/v1/upstox/orders/history?order_id=240108010445130&tag=algo_trade
```

**Response:**
```json
{
  "success": true,
  "status": "success",
  "data": [
    {
      "exchange": "NSE",
      "price": 571.35,
      "product": "D",
      "quantity": 1,
      "status": "put order req received",
      "order_timestamp": "2023-10-19 13:25:56"
    },
    {
      "exchange": "NSE",
      "price": 571.35,
      "product": "D",
      "quantity": 1,
      "status": "validation pending",
      "order_timestamp": "2023-10-19 13:25:56"
    },
    {
      "exchange": "NSE",
      "price": 571.35,
      "product": "D",
      "quantity": 1,
      "status": "open",
      "order_timestamp": "2023-10-19 13:25:56"
    },
    {
      "exchange": "NSE",
      "price": 571.35,
      "product": "D",
      "quantity": 1,
      "status": "complete",
      "order_timestamp": "2023-10-19 13:25:56"
    }
  ],
  "total_entries": 4,
  "message": "Order history retrieved (4 entries)"
}
```

## Auto-Slicing Feature

### What is Auto-Slicing?

Exchanges enforce freeze quantity limits. If an order exceeds this limit, it gets rejected. Auto-slicing automatically splits large orders into smaller parts based on exchange-defined freeze quantities.

### How It Works

**Example:**
- Freeze quantity for SCRIP1: 1,000
- You want to place order for: 10,100 shares
- With `slice=false`: Single order → **Rejected by exchange**
- With `slice=true`: 11 orders (10 x 1,000 + 1 x 100) → **All accepted**

### Correlation IDs for Sliced Orders

For multi-order API, sliced orders get suffixed correlation IDs:

```
Original correlation_id: "orderline25"
Sliced orders:
- orderline25_1
- orderline25_2
- ...
- orderline25_11
```

### Maximum Order Limits

- **Place Order V3**: No limit on sliced orders
- **Place Multi Order**: Max 25 orders (including sliced)
- **Cancel Multi Order**: Max 50 orders
- **Exit Positions**: Max 50 positions

## Integration with Auto-Trading

### Entry Orders (BUY)

When auto-trading executes a trade, it automatically uses the V3 API:

```python
# In execution_handler.py
result = order_service.place_order_v3(
    quantity=quantity,
    instrument_token=prepared_trade.option_instrument_key,
    order_type="MARKET",
    transaction_type="BUY",  # Entry
    product="I",  # Intraday
    validity="DAY",
    tag="auto_trading",
    slice=True  # Auto-slicing enabled
)
```

### Exit Orders (SELL)

When position hits SL/Target, automatic exit order is placed:

```python
# In pnl_tracker.py
result = order_service.place_order_v3(
    quantity=quantity,
    instrument_token=trade_execution.instrument_key,
    order_type="MARKET",
    transaction_type="SELL",  # Exit
    product="I",
    tag=f"exit_{trade_execution.trade_id}",
    slice=True
)
```

## Error Handling

### Common Errors

1. **Validation Errors (400)**
   - Invalid quantity (<= 0)
   - Missing required fields
   - Invalid order type/product/validity
   - Correlation ID too long (> 20 chars)
   - Too many orders in batch (> 25)

2. **Authentication Errors (401)**
   - Access token expired
   - Invalid access token

3. **API Errors (500)**
   - Exchange rejection
   - Network issues
   - Freeze quantity exceeded (without slicing)

### Error Response Format

```json
{
  "success": false,
  "status": "error",
  "message": "Order placement failed: Insufficient funds",
  "data": null
}
```

### Validation Examples

```python
# Quantity validation
if quantity <= 0:
    raise ValueError("Quantity must be greater than 0")

# Price validation for LIMIT orders
if order_type == "LIMIT" and price <= 0:
    raise ValueError("Price must be greater than 0 for LIMIT orders")

# Trigger price validation for SL orders
if order_type in ["SL", "SL-M"] and trigger_price <= 0:
    raise ValueError("Trigger price must be greater than 0 for stop loss orders")
```

## Testing

### Sandbox Mode

Always test in sandbox environment first:

```python
service = get_upstox_order_service(
    access_token=access_token,
    use_sandbox=True  # Sandbox mode
)
```

### Running Tests

```bash
# Set your access token
export UPSTOX_ACCESS_TOKEN="your_token_here"

# Run test script
python test_upstox_order_apis.py
```

### Test Coverage

✅ Place single order
✅ Place order with auto-slicing
✅ Place multi order (batch)
✅ Modify order
✅ Cancel single order
✅ Cancel multi order (by tag)
✅ Exit all positions
✅ Get order details
✅ Get order history

## Performance

### Latency Tracking

All V3 APIs return latency metadata:

```json
{
  "metadata": {
    "latency": 45
  }
}
```

This shows the time (in milliseconds) Upstox platform took to process your request.

### Rate Limits

- **Place Multi Order**: Different rate limit than standard
- **Cancel Multi Order**: Different rate limit than standard
- **Exit Positions**: Different rate limit than standard

Check Upstox documentation for current rate limits.

## Best Practices

1. **Always Use Sandbox First**
   ```python
   service = get_upstox_order_service(access_token, use_sandbox=True)
   ```

2. **Enable Auto-Slicing for Large Orders**
   ```python
   result = service.place_order_v3(..., slice=True)
   ```

3. **Use Tags for Order Management**
   ```python
   # Tag all algorithmic orders
   result = service.place_order_v3(..., tag="algo_v1")

   # Cancel all algo orders at once
   service.cancel_multi_order(tag="algo_v1")
   ```

4. **Check Order Status Before Modify/Cancel**
   ```python
   details = service.get_order_details(order_id)
   if details['data']['status'] == 'open':
       service.modify_order_v3(order_id, ...)
   ```

5. **Handle Errors Gracefully**
   ```python
   try:
       result = service.place_order_v3(...)
       if not result['success']:
           logger.error(f"Order failed: {result['message']}")
   except ValueError as e:
       logger.error(f"Validation error: {e}")
   except Exception as e:
       logger.error(f"Unexpected error: {e}")
   ```

6. **Monitor Latency**
   ```python
   result = service.place_order_v3(...)
   latency = result.get('metadata', {}).get('latency', 0)
   if latency > 100:  # ms
       logger.warning(f"High latency detected: {latency}ms")
   ```

## Troubleshooting

### Order Rejected

**Check:**
1. Sufficient funds in account
2. Valid instrument token
3. Freeze quantity (use auto-slicing)
4. Market hours
5. Order type compatibility

### Token Expired

**Solution:**
```python
# Refresh token before trading
from services.upstox_automation_service import refresh_upstox_token

refresh_upstox_token(user_id, db)
```

### Slicing Not Working

**Check:**
1. `slice=True` in request
2. Quantity exceeds freeze limit
3. Using correct API (V3 for slicing)

## API Reference

| Endpoint | Method | Purpose | Max Items |
|----------|--------|---------|-----------|
| `/place` | POST | Place single order | N/A |
| `/place-multi` | POST | Place batch orders | 25 |
| `/modify` | PUT | Modify order | N/A |
| `/cancel/{order_id}` | DELETE | Cancel order | N/A |
| `/cancel-multi` | DELETE | Cancel multiple | 50 |
| `/exit-positions` | POST | Exit positions | 50 |
| `/details/{order_id}` | GET | Get order details | N/A |
| `/history` | GET | Get order history | N/A |

## Support

For issues or questions:
1. Check Upstox official documentation
2. Review error logs
3. Test in sandbox mode
4. Check GitHub issues

## Changelog

### v1.0.0 (2025-01-21)
- ✅ Complete V3 API implementation
- ✅ Auto-slicing support
- ✅ Multi-order batch operations
- ✅ Integration with auto-trading system
- ✅ Comprehensive error handling
- ✅ Latency tracking
- ✅ Sandbox mode support
- ✅ Production-ready validation
