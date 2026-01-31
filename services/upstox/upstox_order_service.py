"""
Upstox Order Management Service - V3 API Integration
Production-grade implementation of all Upstox order management endpoints
"""

import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime
import requests
from enum import Enum

logger = logging.getLogger(__name__)


class OrderType(Enum):
    """Upstox order types"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"
    SL_M = "SL-M"


class TransactionType(Enum):
    """Transaction types"""
    BUY = "BUY"
    SELL = "SELL"


class ProductType(Enum):
    """Product types"""
    INTRADAY = "I"
    DELIVERY = "D"
    COVER_ORDER = "CO"
    MTF = "MTF"


class Validity(Enum):
    """Order validity types"""
    DAY = "DAY"
    IOC = "IOC"


class OrderStatus(Enum):
    """Order status types"""
    PUT_ORDER_REQ_RECEIVED = "put order req received"
    VALIDATION_PENDING = "validation pending"
    OPEN_PENDING = "open pending"
    OPEN = "open"
    COMPLETE = "complete"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    TRIGGER_PENDING = "trigger pending"
    AFTER_MARKET_ORDER_REQ_RECEIVED = "after market order req received"


class UpstoxOrderService:
    """
    Complete Upstox order management service with V3 API support

    Features:
    - Place Order V3 with auto-slicing
    - Place Multi Order (batch orders)
    - Modify Order V3
    - Cancel Order V3
    - Cancel Multi Order
    - Exit All Positions
    - Get Order Details
    - Get Order History
    - Comprehensive error handling
    - Rate limit management
    - Latency tracking
    """

    BASE_URL_V2 = "https://api.upstox.com/v2"
    BASE_URL_V3 = "https://api-hft.upstox.com/v3"
    SANDBOX_URL_V2 = "https://api-sandbox.upstox.com/v2"
    SANDBOX_URL_V3 = "https://api-sandbox.upstox.com/v3"

    MAX_MULTI_ORDER_COUNT = 25
    MAX_CANCEL_MULTI_COUNT = 50
    MAX_EXIT_POSITIONS_COUNT = 50

    def __init__(self, access_token: str, use_sandbox: bool = False):
        """
        Initialize Upstox Order Service

        Args:
            access_token: Upstox access token
            use_sandbox: Use sandbox environment for testing
        """
        if not access_token:
            raise ValueError("Access token is required")

        self.access_token = access_token
        self.base_url_v2 = self.SANDBOX_URL_V2 if use_sandbox else self.BASE_URL_V2
        self.base_url_v3 = self.SANDBOX_URL_V3 if use_sandbox else self.BASE_URL_V3
        self.use_sandbox = use_sandbox

    def _get_headers(self) -> Dict[str, str]:
        """
        Get standard headers for API requests

        Returns:
            Dict with authorization and content type headers
        """
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _validate_order_params(
        self,
        quantity: int,
        instrument_token: str,
        order_type: str,
        transaction_type: str,
        product: str,
        validity: str,
        price: float,
        trigger_price: float
    ) -> None:
        """
        Validate order parameters before submission

        Args:
            quantity: Order quantity
            instrument_token: Instrument token
            order_type: Order type
            transaction_type: BUY or SELL
            product: Product type
            validity: Order validity
            price: Limit price
            trigger_price: Stop loss trigger price

        Raises:
            ValueError: If validation fails
        """
        if quantity <= 0:
            raise ValueError("Quantity must be greater than 0")

        if not instrument_token:
            raise ValueError("Instrument token is required")

        if order_type not in [ot.value for ot in OrderType]:
            raise ValueError(f"Invalid order type: {order_type}")

        if transaction_type not in [tt.value for tt in TransactionType]:
            raise ValueError(f"Invalid transaction type: {transaction_type}")

        if product not in [pt.value for pt in ProductType]:
            raise ValueError(f"Invalid product type: {product}")

        if validity not in [v.value for v in Validity]:
            raise ValueError(f"Invalid validity: {validity}")

        if order_type == OrderType.LIMIT.value and price <= 0:
            raise ValueError("Price must be greater than 0 for LIMIT orders")

        if order_type in [OrderType.SL.value, OrderType.SL_M.value] and trigger_price <= 0:
            raise ValueError("Trigger price must be greater than 0 for stop loss orders")

    def place_order_v3(
        self,
        quantity: int,
        instrument_token: str,
        order_type: str,
        transaction_type: str,
        product: str = "D",
        validity: str = "DAY",
        price: float = 0.0,
        trigger_price: float = 0.0,
        disclosed_quantity: int = 0,
        is_amo: bool = False,
        tag: Optional[str] = None,
        slice: bool = False
    ) -> Dict[str, Any]:
        """
        Place order using Upstox V3 API with auto-slicing support

        Args:
            quantity: Order quantity (for F&O: multiples of lot size)
            instrument_token: Instrument key (e.g., NSE_FO|43919)
            order_type: MARKET, LIMIT, SL, SL-M
            transaction_type: BUY or SELL
            product: D (Delivery), I (Intraday), MTF (Margin Trading)
            validity: DAY or IOC
            price: Limit price (required for LIMIT orders)
            trigger_price: Trigger price (required for SL orders)
            disclosed_quantity: Quantity to disclose in market depth
            is_amo: After Market Order flag
            tag: Unique tag for order identification
            slice: Enable auto-slicing for large orders

        Returns:
            Dict with success status, order_ids, and latency metadata

        Raises:
            ValueError: If parameters are invalid
            Exception: If API call fails

        Example:
            >>> result = service.place_order_v3(
            ...     quantity=4000,
            ...     instrument_token="NSE_FO|43919",
            ...     order_type="MARKET",
            ...     transaction_type="BUY",
            ...     product="D",
            ...     slice=True
            ... )
            >>> print(result['data']['order_ids'])
        """
        try:
            # Validate parameters
            self._validate_order_params(
                quantity, instrument_token, order_type,
                transaction_type, product, validity, price, trigger_price
            )

            url = f"{self.base_url_v3}/order/place"

            payload = {
                "quantity": quantity,
                "product": product,
                "validity": validity,
                "price": float(price),
                "instrument_token": instrument_token,
                "order_type": order_type,
                "transaction_type": transaction_type,
                "disclosed_quantity": disclosed_quantity,
                "trigger_price": float(trigger_price),
                "is_amo": is_amo,
                "slice": slice
            }

            if tag:
                payload["tag"] = tag

            logger.info(
                f"Placing order V3: {transaction_type} {quantity} x {instrument_token} "
                f"({order_type}, slice={slice})"
            )

            response = requests.post(url, json=payload, headers=self._get_headers())

            if response.status_code == 200:
                result = response.json()

                if result.get("status") == "success":
                    order_ids = result.get("data", {}).get("order_ids", [])
                    latency = result.get("metadata", {}).get("latency", 0)

                    logger.info(
                        f"Order placed successfully: {len(order_ids)} orders, "
                        f"latency: {latency}ms, IDs: {order_ids}"
                    )

                    return {
                        "success": True,
                        "status": result["status"],
                        "data": {
                            "order_ids": order_ids,
                            "total_orders": len(order_ids)
                        },
                        "metadata": {
                            "latency": latency
                        },
                        "message": f"Order placed successfully ({len(order_ids)} orders)"
                    }
                else:
                    error_msg = result.get("message", "Unknown error")
                    logger.error(f"Order placement failed: {error_msg}")
                    return {
                        "success": False,
                        "status": "error",
                        "message": error_msg,
                        "data": None
                    }
            else:
                error_text = response.text
                logger.error(f"API error {response.status_code}: {error_text}")
                raise Exception(f"API error: {response.status_code} - {error_text}")

        except ValueError as e:
            logger.error(f"Validation error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            raise

    def place_multi_order(
        self,
        orders: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Place multiple orders in a single API call

        Args:
            orders: List of order dictionaries, each containing:
                - correlation_id: Unique identifier for this order line
                - quantity: Order quantity
                - instrument_token: Instrument key
                - order_type: MARKET, LIMIT, SL, SL-M
                - transaction_type: BUY or SELL
                - product: D, I, MTF
                - validity: DAY or IOC
                - price: Limit price
                - trigger_price: Trigger price
                - disclosed_quantity: Disclosed quantity
                - is_amo: After Market Order flag
                - slice: Auto-slicing flag
                - tag: Optional order tag

        Returns:
            Dict with success status, order details, and summary

        Raises:
            ValueError: If order count exceeds limit or parameters invalid
            Exception: If API call fails

        Example:
            >>> orders = [
            ...     {
            ...         "correlation_id": "1",
            ...         "quantity": 25,
            ...         "instrument_token": "NSE_FO|62864",
            ...         "order_type": "MARKET",
            ...         "transaction_type": "BUY",
            ...         "product": "D",
            ...         "validity": "DAY",
            ...         "price": 0,
            ...         "trigger_price": 0,
            ...         "disclosed_quantity": 0,
            ...         "is_amo": False,
            ...         "slice": False
            ...     }
            ... ]
            >>> result = service.place_multi_order(orders)
        """
        try:
            if not orders:
                raise ValueError("Orders list cannot be empty")

            if len(orders) > self.MAX_MULTI_ORDER_COUNT:
                raise ValueError(
                    f"Maximum {self.MAX_MULTI_ORDER_COUNT} orders allowed per request"
                )

            # Validate each order has correlation_id
            for order in orders:
                if "correlation_id" not in order:
                    raise ValueError("Each order must have a correlation_id")

                correlation_id = order["correlation_id"]
                if len(str(correlation_id)) > 20:
                    raise ValueError(
                        f"correlation_id cannot exceed 20 characters: {correlation_id}"
                    )

            url = f"{self.base_url_v2}/order/multi/place"

            logger.info(f"Placing multi order: {len(orders)} orders")

            response = requests.post(url, json=orders, headers=self._get_headers())

            if response.status_code in [200, 207]:
                result = response.json()
                status = result.get("status")
                summary = result.get("summary", {})

                logger.info(
                    f"Multi order result - Status: {status}, "
                    f"Success: {summary.get('success', 0)}/{summary.get('total', 0)}, "
                    f"Errors: {summary.get('error', 0)}"
                )

                return {
                    "success": status in ["success", "partial_success"],
                    "status": status,
                    "data": result.get("data", []),
                    "summary": summary,
                    "message": f"Multi order: {summary.get('success', 0)} successful, {summary.get('error', 0)} failed"
                }
            else:
                error_text = response.text
                logger.error(f"Multi order API error {response.status_code}: {error_text}")
                raise Exception(f"API error: {response.status_code} - {error_text}")

        except ValueError as e:
            logger.error(f"Validation error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error placing multi order: {e}")
            raise

    def modify_order_v3(
        self,
        order_id: str,
        order_type: str,
        price: float,
        trigger_price: float,
        validity: str = "DAY",
        quantity: Optional[int] = None,
        disclosed_quantity: int = 0
    ) -> Dict[str, Any]:
        """
        Modify an existing open or pending order using V3 API

        Args:
            order_id: Order ID to modify (required)
            order_type: Order type (required: MARKET, LIMIT, SL, SL-M)
            price: Limit price (required, 0.0 if MARKET)
            trigger_price: Trigger price (required, 0.0 if not SL)
            validity: Order validity (default "DAY")
            quantity: New quantity (optional)
            disclosed_quantity: New disclosed quantity (default 0)

        Returns:
            Dict with success status, order_id, and latency metadata
        """
        try:
            if not order_id:
                raise ValueError("Order ID is required for modification")

            url = f"{self.base_url_v3}/order/modify"

            # Based on V3 docs, these fields are mandatory in the payload
            payload = {
                "order_id": order_id,
                "order_type": order_type,
                "price": float(price),
                "trigger_price": float(trigger_price),
                "validity": validity,
                "disclosed_quantity": disclosed_quantity
            }

            if quantity is not None:
                payload["quantity"] = quantity

            logger.info(f"Modifying order V3: {order_id} ({order_type}, price={price})")

            response = requests.put(url, json=payload, headers=self._get_headers())

            if response.status_code == 200:
                result = response.json()

                if result.get("status") == "success":
                    modified_order_id = result.get("data", {}).get("order_id")
                    latency = result.get("metadata", {}).get("latency", 0)

                    logger.info(f"Order modified successfully: {modified_order_id}, latency: {latency}ms")

                    return {
                        "success": True,
                        "status": result["status"],
                        "data": {
                            "order_id": modified_order_id
                        },
                        "metadata": {
                            "latency": latency
                        },
                        "message": "Order modified successfully"
                    }
                else:
                    error_msg = result.get("message", "Unknown error")
                    logger.error(f"Order modification failed: {error_msg}")
                    return {
                        "success": False,
                        "status": "error",
                        "message": error_msg,
                        "data": None
                    }
            else:
                error_text = response.text
                logger.error(f"API error {response.status_code}: {error_text}")
                raise Exception(f"API error: {response.status_code} - {error_text}")

        except ValueError as e:
            logger.error(f"Validation error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error modifying order: {e}")
            raise

    def cancel_order_v3(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel an open or pending order using V3 API

        Args:
            order_id: Order ID to cancel

        Returns:
            Dict with success status, order_id, and latency metadata

        Raises:
            ValueError: If order_id is empty
            Exception: If API call fails

        Example:
            >>> result = service.cancel_order_v3("240108010445130")
        """
        try:
            if not order_id:
                raise ValueError("Order ID is required for cancellation")

            url = f"{self.base_url_v3}/order/cancel"
            params = {"order_id": order_id}

            logger.info(f"Cancelling order: {order_id}")

            response = requests.delete(url, params=params, headers=self._get_headers())

            if response.status_code == 200:
                result = response.json()

                if result.get("status") == "success":
                    cancelled_order_id = result.get("data", {}).get("order_id")
                    latency = result.get("metadata", {}).get("latency", 0)

                    logger.info(f"Order cancelled successfully: {cancelled_order_id}, latency: {latency}ms")

                    return {
                        "success": True,
                        "status": result["status"],
                        "data": {
                            "order_id": cancelled_order_id
                        },
                        "metadata": {
                            "latency": latency
                        },
                        "message": "Order cancelled successfully"
                    }
                else:
                    error_msg = result.get("message", "Unknown error")
                    logger.error(f"Order cancellation failed: {error_msg}")
                    return {
                        "success": False,
                        "status": "error",
                        "message": error_msg,
                        "data": None
                    }
            else:
                error_text = response.text
                logger.error(f"API error {response.status_code}: {error_text}")
                raise Exception(f"API error: {response.status_code} - {error_text}")

        except ValueError as e:
            logger.error(f"Validation error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            raise

    def cancel_multi_order(
        self,
        segment: Optional[str] = None,
        tag: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cancel all open orders or filter by segment/tag

        Args:
            segment: Market segment filter (NSE_EQ, BSE_EQ, NSE_FO, BSE_FO, MCX_FO, etc.)
            tag: Order tag filter

        Returns:
            Dict with success status, cancelled order_ids, and summary

        Raises:
            Exception: If API call fails

        Notes:
            - Maximum 50 orders can be cancelled per request
            - Without filters, cancels ALL open orders

        Example:
            >>> result = service.cancel_multi_order(segment="NSE_FO")
            >>> result = service.cancel_multi_order(tag="algo_trade")
            >>> result = service.cancel_multi_order()  # Cancel all
        """
        try:
            url = f"{self.base_url_v2}/order/multi/cancel"
            params = {}

            if segment:
                params["segment"] = segment
            if tag:
                params["tag"] = tag

            filter_desc = []
            if segment:
                filter_desc.append(f"segment={segment}")
            if tag:
                filter_desc.append(f"tag={tag}")

            filter_str = ", ".join(filter_desc) if filter_desc else "all orders"
            logger.info(f"Cancelling multiple orders: {filter_str}")

            response = requests.delete(url, params=params, headers=self._get_headers())

            if response.status_code in [200, 207]:
                result = response.json()
                status = result.get("status")
                summary = result.get("summary", {})
                data = result.get("data", {}) or {}
                order_ids = data.get("order_ids", [])
                errors = result.get("errors", [])

                logger.info(
                    f"Multi cancel result - Status: {status}, "
                    f"Cancelled: {summary.get('success', 0)}/{summary.get('total', 0)}, "
                    f"Errors: {summary.get('error', 0)}"
                )

                if errors:
                    logger.warning(f"Multi cancel errors: {errors}")

                return {
                    "success": status in ["success", "partial_success"],
                    "status": status,
                    "data": {
                        "order_ids": order_ids,
                        "total_cancelled": len(order_ids)
                    },
                    "summary": summary,
                    "errors": errors,
                    "message": f"Cancelled {len(order_ids)} orders. Failed: {summary.get('error', 0)}"
                }
            else:
                error_text = response.text
                logger.error(f"Multi cancel API error {response.status_code}: {error_text}")
                raise Exception(f"API error: {response.status_code} - {error_text}")

        except Exception as e:
            logger.error(f"Error cancelling multiple orders: {e}")
            raise

    def exit_all_positions(
        self,
        segment: Optional[str] = None,
        tag: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Exit all open positions or filter by segment/tag

        Args:
            segment: Market segment filter (NSE_EQ, BSE_EQ, NSE_FO, BSE_FO, MCX_FO, etc.)
            tag: Position tag filter (applies to intraday positions only)

        Returns:
            Dict with success status, exit order_ids, summary, and errors

        Raises:
            Exception: If API call fails

        Notes:
            - Maximum 50 positions can be exited per request
            - Auto-slicing enabled by default
            - BUY positions executed first, then SELL positions
            - Tags only valid for intraday positions

        Example:
            >>> result = service.exit_all_positions(segment="NSE_FO")
            >>> result = service.exit_all_positions(tag="strategy_1")
            >>> result = service.exit_all_positions()  # Exit all
        """
        try:
            url = f"{self.base_url_v2}/order/positions/exit"
            params = {}

            if segment:
                params["segment"] = segment
            if tag:
                params["tag"] = tag

            filter_desc = []
            if segment:
                filter_desc.append(f"segment={segment}")
            if tag:
                filter_desc.append(f"tag={tag}")

            filter_str = ", ".join(filter_desc) if filter_desc else "all positions"
            logger.info(f"Exiting positions: {filter_str}")

            response = requests.post(url, params=params, headers=self._get_headers())

            if response.status_code in [200, 207]:
                result = response.json()
                status = result.get("status")
                summary = result.get("summary", {})
                data = result.get("data", {}) or {}
                order_ids = data.get("order_ids", [])
                errors = result.get("errors", [])

                logger.info(
                    f"Exit positions result - Status: {status}, "
                    f"Exited: {summary.get('success', 0)}/{summary.get('total', 0)}, "
                    f"Errors: {summary.get('error', 0)}"
                )

                if errors:
                    logger.warning(f"Exit positions errors: {errors}")

                return {
                    "success": status in ["success", "partial_success"],
                    "status": status,
                    "data": {
                        "order_ids": order_ids,
                        "total_positions_exited": len(order_ids)
                    },
                    "summary": summary,
                    "errors": errors,
                    "message": f"Exited {len(order_ids)} positions. Failed: {summary.get('error', 0)}"
                }
            else:
                error_text = response.text
                logger.error(f"Exit positions API error {response.status_code}: {error_text}")
                raise Exception(f"API error: {response.status_code} - {error_text}")

        except Exception as e:
            logger.error(f"Error exiting positions: {e}")
            raise

    def get_order_details(self, order_id: str) -> Dict[str, Any]:
        """
        Get latest status and details of a specific order

        Args:
            order_id: Order ID to fetch

        Returns:
            Dict with order details including status, prices, quantities

        Raises:
            ValueError: If order_id is empty
            Exception: If API call fails

        Example:
            >>> details = service.get_order_details("240108010445130")
            >>> print(details['data']['status'])  # complete, open, rejected, etc.
        """
        try:
            if not order_id:
                raise ValueError("Order ID is required")

            url = f"{self.base_url_v2}/order/details"
            params = {"order_id": order_id}

            logger.info(f"Fetching order details: {order_id}")

            response = requests.get(url, params=params, headers=self._get_headers())

            if response.status_code == 200:
                result = response.json()

                if result.get("status") == "success":
                    order_data = result.get("data", {})
                    logger.info(f"Order details retrieved: {order_id}, status: {order_data.get('status')}")

                    return {
                        "success": True,
                        "status": result["status"],
                        "data": order_data,
                        "message": "Order details retrieved successfully"
                    }
                else:
                    error_msg = result.get("message", "Unknown error")
                    logger.error(f"Failed to fetch order details: {error_msg}")
                    return {
                        "success": False,
                        "status": "error",
                        "message": error_msg,
                        "data": None
                    }
            else:
                error_text = response.text
                logger.error(f"API error {response.status_code}: {error_text}")
                raise Exception(f"API error: {response.status_code} - {error_text}")

        except ValueError as e:
            logger.error(f"Validation error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching order details: {e}")
            raise

    def get_order_history(
        self,
        order_id: Optional[str] = None,
        tag: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get order history showing progression through execution stages

        Args:
            order_id: Specific order ID (optional)
            tag: Order tag to filter history (optional)

        Returns:
            Dict with list of order history entries

        Raises:
            Exception: If API call fails

        Notes:
            - If both order_id and tag provided, returns history matching both
            - If only tag provided, returns history of all orders with that tag
            - Orders remain available for one trading day only

        Example:
            >>> history = service.get_order_history(order_id="240108010445130")
            >>> history = service.get_order_history(tag="algo_trade")
        """
        try:
            url = f"{self.base_url_v2}/order/history"
            params = {}

            if order_id:
                params["order_id"] = order_id
            if tag:
                params["tag"] = tag

            filter_desc = []
            if order_id:
                filter_desc.append(f"order_id={order_id}")
            if tag:
                filter_desc.append(f"tag={tag}")

            filter_str = ", ".join(filter_desc) if filter_desc else "all"
            logger.info(f"Fetching order history: {filter_str}")

            response = requests.get(url, params=params, headers=self._get_headers())

            if response.status_code == 200:
                result = response.json()

                if result.get("status") == "success":
                    history_data = result.get("data", [])
                    logger.info(f"Order history retrieved: {len(history_data)} entries")

                    return {
                        "success": True,
                        "status": result["status"],
                        "data": history_data,
                        "total_entries": len(history_data),
                        "message": f"Order history retrieved ({len(history_data)} entries)"
                    }
                else:
                    error_msg = result.get("message", "Unknown error")
                    logger.error(f"Failed to fetch order history: {error_msg}")
                    return {
                        "success": False,
                        "status": "error",
                        "message": error_msg,
                        "data": None
                    }
            else:
                error_text = response.text
                logger.error(f"API error {response.status_code}: {error_text}")
                raise Exception(f"API error: {response.status_code} - {error_text}")

        except Exception as e:
            logger.error(f"Error fetching order history: {e}")
            raise

    def get_brokerage_charges(
        self,
        instrument_token: str,
        quantity: int,
        transaction_type: str,
        price: float,
        product: str = "D"
    ) -> Dict[str, Any]:
        """
        Calculate brokerage charges for a specific trade order

        Args:
            instrument_token: Instrument key
            quantity: Order quantity
            transaction_type: BUY or SELL
            price: Order price
            product: Product type (I, D, etc.)

        Returns:
            Dict with detailed charges breakdown
        """
        try:
            url = f"{self.base_url_v2}/charges/brokerage"
            params = {
                "instrument_token": instrument_token,
                "quantity": quantity,
                "product": product,
                "transaction_type": transaction_type,
                "price": float(price)
            }

            logger.debug(f"Fetching brokerage charges for {instrument_token}")

            response = requests.get(url, params=params, headers=self._get_headers())

            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "success":
                    return {
                        "success": True,
                        "data": result.get("data", {}),
                        "charges": result.get("data", {}).get("charges", {})
                    }
                else:
                    return {
                        "success": False,
                        "message": result.get("message", "Unknown error")
                    }
            else:
                logger.error(f"Brokerage API error: {response.text}")
                return {"success": False, "message": f"API error: {response.status_code}"}

        except Exception as e:
            logger.error(f"Error fetching brokerage: {e}")
            return {"success": False, "message": str(e)}

    def fetch_margin_requirements(
        self,
        instruments: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Fetch margin requirements for a list of instruments

        Args:
            instruments: List of dicts, each containing:
                - instrument_token (str)
                - quantity (int)
                - transaction_type (BUY/SELL)
                - product (I/D/CO)
                - price (float, optional)

        Returns:
            Dict with margin details (required_margin, final_margin, etc.)
        """
        try:
            url = f"{self.base_url_v2}/charges/margin"
            
            # Upstox API expects body with "instruments": [...]
            payload = {
                "instruments": instruments
            }

            logger.debug(f"Fetching margin requirements for {len(instruments)} instruments")

            response = requests.post(url, json=payload, headers=self._get_headers())

            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "success":
                    data = result.get("data", {})
                    return {
                        "success": True,
                        "required_margin": data.get("required_margin", 0),
                        "final_margin": data.get("final_margin", 0),
                        "margins": data.get("margins", [])
                    }
                else:
                    return {
                        "success": False,
                        "message": result.get("message", "Unknown error")
                    }
            else:
                logger.error(f"Margin API error: {response.text}")
                return {"success": False, "message": f"API error: {response.status_code}"}

        except Exception as e:
            logger.error(f"Error fetching margin: {e}")
            return {"success": False, "message": str(e)}


# Singleton instance factory
_upstox_order_service_instance = None

def get_upstox_order_service(access_token: str, use_sandbox: bool = False) -> UpstoxOrderService:
    """
    Get or create UpstoxOrderService instance

    Args:
        access_token: Upstox access token
        use_sandbox: Use sandbox environment

    Returns:
        UpstoxOrderService instance
    """
    global _upstox_order_service_instance

    if _upstox_order_service_instance is None or _upstox_order_service_instance.access_token != access_token:
        _upstox_order_service_instance = UpstoxOrderService(access_token, use_sandbox)

    return _upstox_order_service_instance
