"""
Upstox Order Management API Router
FastAPI endpoints for complete order lifecycle management
"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, validator
from datetime import datetime

from database.connection import get_db
from database.models import User, BrokerConfig
from router.auth_router import get_current_user
from services.upstox.upstox_order_service import (
    get_upstox_order_service,
    UpstoxOrderService,
    OrderType,
    TransactionType,
    ProductType,
    Validity
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/upstox/orders", tags=["Upstox Orders"])


# ==================== Request/Response Models ====================

class PlaceOrderRequest(BaseModel):
    """Request model for placing a single order"""
    quantity: int = Field(..., gt=0, description="Order quantity (must be positive)")
    instrument_token: str = Field(..., description="Instrument key (e.g., NSE_FO|43919)")
    order_type: str = Field(..., description="Order type: MARKET, LIMIT, SL, SL-M")
    transaction_type: str = Field(..., description="Transaction type: BUY or SELL")
    product: str = Field(default="D", description="Product type: D, I, MTF")
    validity: str = Field(default="DAY", description="Order validity: DAY or IOC")
    price: float = Field(default=0.0, ge=0, description="Limit price (required for LIMIT orders)")
    trigger_price: float = Field(default=0.0, ge=0, description="Trigger price (required for SL orders)")
    disclosed_quantity: int = Field(default=0, ge=0, description="Quantity to disclose in market depth")
    is_amo: bool = Field(default=False, description="After Market Order flag")
    tag: Optional[str] = Field(default=None, max_length=40, description="Unique order tag")
    slice: bool = Field(default=False, description="Enable auto-slicing for large orders")

    @validator('order_type')
    def validate_order_type(cls, v):
        valid_types = [ot.value for ot in OrderType]
        if v not in valid_types:
            raise ValueError(f"Invalid order_type. Must be one of: {valid_types}")
        return v

    @validator('transaction_type')
    def validate_transaction_type(cls, v):
        valid_types = [tt.value for tt in TransactionType]
        if v not in valid_types:
            raise ValueError(f"Invalid transaction_type. Must be one of: {valid_types}")
        return v

    @validator('product')
    def validate_product(cls, v):
        valid_products = [pt.value for pt in ProductType]
        if v not in valid_products:
            raise ValueError(f"Invalid product. Must be one of: {valid_products}")
        return v

    @validator('validity')
    def validate_validity(cls, v):
        valid_validities = [val.value for val in Validity]
        if v not in valid_validities:
            raise ValueError(f"Invalid validity. Must be one of: {valid_validities}")
        return v


class MultiOrderItem(BaseModel):
    """Individual order item for multi-order request"""
    correlation_id: str = Field(..., max_length=20, description="Unique identifier for this order line")
    quantity: int = Field(..., gt=0)
    instrument_token: str = Field(...)
    order_type: str = Field(...)
    transaction_type: str = Field(...)
    product: str = Field(default="D")
    validity: str = Field(default="DAY")
    price: float = Field(default=0.0, ge=0)
    trigger_price: float = Field(default=0.0, ge=0)
    disclosed_quantity: int = Field(default=0, ge=0)
    is_amo: bool = Field(default=False)
    slice: bool = Field(default=False)
    tag: Optional[str] = Field(default=None, max_length=40)


class ModifyOrderRequest(BaseModel):
    """Request model for modifying an order"""
    order_id: str = Field(..., description="Order ID to modify")
    quantity: Optional[int] = Field(default=None, gt=0, description="New quantity (optional)")
    order_type: str = Field(default="LIMIT", description="New order type")
    validity: str = Field(default="DAY", description="Order validity")
    price: float = Field(default=0.0, ge=0, description="New limit price")
    trigger_price: float = Field(default=0.0, ge=0, description="New trigger price")
    disclosed_quantity: Optional[int] = Field(default=None, ge=0, description="New disclosed quantity")


class OrderResponse(BaseModel):
    """Standard response model for order operations"""
    success: bool
    status: str
    data: Optional[Dict[str, Any]]
    message: str
    metadata: Optional[Dict[str, Any]] = None


# ==================== Helper Functions ====================

def get_upstox_service(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    use_sandbox: bool = Query(False, description="Use sandbox environment for testing")
) -> UpstoxOrderService:
    """
    Get Upstox Order Service instance with user's access token

    Args:
        current_user: Authenticated user
        db: Database session
        use_sandbox: Use sandbox environment flag

    Returns:
        UpstoxOrderService instance

    Raises:
        HTTPException: If no active Upstox broker configuration found
    """
    broker_config = (
        db.query(BrokerConfig)
        .filter(
            BrokerConfig.user_id == current_user.id,
            BrokerConfig.broker_name == "upstox",
            BrokerConfig.is_active == True,
            BrokerConfig.access_token.isnot(None)
        )
        .first()
    )

    if not broker_config:
        raise HTTPException(
            status_code=400,
            detail="No active Upstox broker configuration found. Please configure and authenticate with Upstox first."
        )

    # Validate token expiry
    if broker_config.access_token_expiry and broker_config.access_token_expiry < datetime.now():
        raise HTTPException(
            status_code=401,
            detail="Upstox access token expired. Please refresh your token."
        )

    return get_upstox_order_service(broker_config.access_token, use_sandbox)


# ==================== API Endpoints ====================

@router.post("/place", response_model=OrderResponse)
async def place_order(
    request: PlaceOrderRequest,
    service: UpstoxOrderService = Depends(get_upstox_service),
    current_user: User = Depends(get_current_user)
):
    """
    Place a single order using Upstox V3 API

    **Features:**
    - Market, Limit, Stop Loss orders
    - Auto-slicing for large orders (freeze quantity handling)
    - After Market Orders (AMO)
    - Custom order tagging
    - Latency tracking

    **Returns:**
    - Order ID(s) for successful placement
    - Latency metadata
    - Detailed error messages on failure

    **Example:**
    ```json
    {
        "quantity": 4000,
        "instrument_token": "NSE_FO|43919",
        "order_type": "MARKET",
        "transaction_type": "BUY",
        "product": "D",
        "slice": true
    }
    ```
    """
    try:
        logger.info(
            f"User {current_user.id} placing order: {request.transaction_type} "
            f"{request.quantity} x {request.instrument_token}"
        )

        result = service.place_order_v3(
            quantity=request.quantity,
            instrument_token=request.instrument_token,
            order_type=request.order_type,
            transaction_type=request.transaction_type,
            product=request.product,
            validity=request.validity,
            price=request.price,
            trigger_price=request.trigger_price,
            disclosed_quantity=request.disclosed_quantity,
            is_amo=request.is_amo,
            tag=request.tag,
            slice=request.slice
        )

        return OrderResponse(**result)

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error placing order: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to place order: {str(e)}")


@router.post("/place-multi", response_model=OrderResponse)
async def place_multi_order(
    orders: List[MultiOrderItem] = Body(..., min_items=1, max_items=25),
    service: UpstoxOrderService = Depends(get_upstox_service),
    current_user: User = Depends(get_current_user)
):
    """
    Place multiple orders in a single API call

    **Features:**
    - Batch order placement (max 25 orders)
    - Individual order correlation IDs
    - Mixed BUY/SELL orders (BUY executed first)
    - Per-order auto-slicing
    - Partial success handling

    **Returns:**
    - Individual order IDs per correlation_id
    - Summary of successful/failed orders
    - Detailed error information per order

    **Example:**
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
        }
    ]
    ```
    """
    try:
        logger.info(f"User {current_user.id} placing multi order: {len(orders)} orders")

        # Convert Pydantic models to dicts
        orders_dict = [order.dict() for order in orders]

        result = service.place_multi_order(orders_dict)

        return OrderResponse(**result)

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error placing multi order: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to place multi order: {str(e)}")


@router.put("/modify", response_model=OrderResponse)
async def modify_order(
    request: ModifyOrderRequest,
    service: UpstoxOrderService = Depends(get_upstox_service),
    current_user: User = Depends(get_current_user)
):
    """
    Modify an existing open or pending order

    **Features:**
    - Modify quantity, price, trigger price
    - Change order type
    - Update disclosed quantity
    - Latency tracking

    **Returns:**
    - Modified order ID
    - Latency metadata
    - Error details on failure

    **Example:**
    ```json
    {
        "order_id": "240108010918222",
        "quantity": 3,
        "order_type": "LIMIT",
        "price": 16.8,
        "trigger_price": 16.9
    }
    ```
    """
    try:
        logger.info(f"User {current_user.id} modifying order: {request.order_id}")

        result = service.modify_order_v3(
            order_id=request.order_id,
            quantity=request.quantity,
            order_type=request.order_type,
            validity=request.validity,
            price=request.price,
            trigger_price=request.trigger_price,
            disclosed_quantity=request.disclosed_quantity
        )

        return OrderResponse(**result)

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error modifying order: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to modify order: {str(e)}")


@router.delete("/cancel/{order_id}", response_model=OrderResponse)
async def cancel_order(
    order_id: str,
    service: UpstoxOrderService = Depends(get_upstox_service),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel an open or pending order

    **Features:**
    - Cancel by order ID
    - Works for regular and AMO orders
    - Latency tracking

    **Returns:**
    - Cancelled order ID
    - Latency metadata
    - Error details on failure
    """
    try:
        logger.info(f"User {current_user.id} cancelling order: {order_id}")

        result = service.cancel_order_v3(order_id)

        return OrderResponse(**result)

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error cancelling order: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel order: {str(e)}")


@router.delete("/cancel-multi", response_model=OrderResponse)
async def cancel_multi_order(
    segment: Optional[str] = Query(None, description="Market segment: NSE_EQ, BSE_EQ, NSE_FO, BSE_FO, MCX_FO, etc."),
    tag: Optional[str] = Query(None, description="Order tag filter"),
    service: UpstoxOrderService = Depends(get_upstox_service),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel all open orders or filter by segment/tag

    **Features:**
    - Cancel all open orders (no filters)
    - Filter by market segment
    - Filter by order tag
    - Max 50 orders per request
    - Partial success handling

    **Returns:**
    - List of cancelled order IDs
    - Summary of successful/failed cancellations
    - Error details per order

    **Examples:**
    - Cancel all: `DELETE /cancel-multi`
    - Cancel by segment: `DELETE /cancel-multi?segment=NSE_FO`
    - Cancel by tag: `DELETE /cancel-multi?tag=algo_trade`
    """
    try:
        filter_desc = []
        if segment:
            filter_desc.append(f"segment={segment}")
        if tag:
            filter_desc.append(f"tag={tag}")

        filter_str = ", ".join(filter_desc) if filter_desc else "all orders"
        logger.info(f"User {current_user.id} cancelling multiple orders: {filter_str}")

        result = service.cancel_multi_order(segment=segment, tag=tag)

        return OrderResponse(**result)

    except Exception as e:
        logger.error(f"Error cancelling multiple orders: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel multiple orders: {str(e)}")


@router.post("/exit-positions", response_model=OrderResponse)
async def exit_all_positions(
    segment: Optional[str] = Query(None, description="Market segment filter"),
    tag: Optional[str] = Query(None, description="Position tag filter (intraday only)"),
    service: UpstoxOrderService = Depends(get_upstox_service),
    current_user: User = Depends(get_current_user)
):
    """
    Exit all open positions or filter by segment/tag

    **Features:**
    - Exit all positions (no filters)
    - Filter by market segment
    - Filter by order tag (intraday positions only)
    - Auto-slicing enabled
    - MARKET orders for all exits
    - Max 50 positions per request

    **Returns:**
    - List of exit order IDs
    - Summary of successful/failed exits
    - Error details per position

    **Notes:**
    - Tags only apply to intraday positions
    - BUY positions exited first, then SELL
    - Does NOT support delivery EQ segment

    **Examples:**
    - Exit all: `POST /exit-positions`
    - Exit by segment: `POST /exit-positions?segment=NSE_FO`
    - Exit by tag: `POST /exit-positions?tag=strategy_1`
    """
    try:
        filter_desc = []
        if segment:
            filter_desc.append(f"segment={segment}")
        if tag:
            filter_desc.append(f"tag={tag}")

        filter_str = ", ".join(filter_desc) if filter_desc else "all positions"
        logger.info(f"User {current_user.id} exiting positions: {filter_str}")

        result = service.exit_all_positions(segment=segment, tag=tag)

        return OrderResponse(**result)

    except Exception as e:
        logger.error(f"Error exiting positions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to exit positions: {str(e)}")


@router.get("/details/{order_id}", response_model=OrderResponse)
async def get_order_details(
    order_id: str,
    service: UpstoxOrderService = Depends(get_upstox_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get latest status and details of a specific order

    **Returns:**
    - Complete order details
    - Current status (open, complete, rejected, etc.)
    - Entry/fill prices
    - Quantities (total, filled, pending)
    - Timestamps
    - Broker information

    **Note:** Orders available for current trading day only
    """
    try:
        logger.info(f"User {current_user.id} fetching order details: {order_id}")

        result = service.get_order_details(order_id)

        return OrderResponse(**result)

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching order details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch order details: {str(e)}")


@router.get("/history", response_model=OrderResponse)
async def get_order_history(
    order_id: Optional[str] = Query(None, description="Specific order ID"),
    tag: Optional[str] = Query(None, description="Order tag filter"),
    service: UpstoxOrderService = Depends(get_upstox_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get order history showing progression through execution stages

    **Features:**
    - Track order lifecycle
    - View status transitions
    - Filter by order ID or tag
    - Multiple history entries per order

    **Returns:**
    - List of order history entries
    - Status progression (put order req received → validation pending → open → complete)
    - Timestamps for each stage
    - Price and quantity updates

    **Examples:**
    - Specific order: `GET /history?order_id=240108010445130`
    - By tag: `GET /history?tag=algo_trade`
    - Both: `GET /history?order_id=240108010445130&tag=algo_trade`
    """
    try:
        filter_desc = []
        if order_id:
            filter_desc.append(f"order_id={order_id}")
        if tag:
            filter_desc.append(f"tag={tag}")

        filter_str = ", ".join(filter_desc) if filter_desc else "all"
        logger.info(f"User {current_user.id} fetching order history: {filter_str}")

        result = service.get_order_history(order_id=order_id, tag=tag)

        return OrderResponse(**result)

    except Exception as e:
        logger.error(f"Error fetching order history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch order history: {str(e)}")


@router.get("/health")
async def health_check(
    service: UpstoxOrderService = Depends(get_upstox_service),
    current_user: User = Depends(get_current_user)
):
    """
    Health check endpoint for Upstox order service

    **Returns:**
    - Service status
    - Environment (sandbox/live)
    - User authentication status
    """
    return {
        "success": True,
        "service": "Upstox Order Management",
        "status": "operational",
        "environment": "sandbox" if service.use_sandbox else "live",
        "user_id": current_user.id,
        "timestamp": datetime.now().isoformat()
    }
