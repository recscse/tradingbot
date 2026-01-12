import requests
import logging
from typing import Dict, Any
from brokers.base_broker import BaseBroker

logger = logging.getLogger(__name__)


class UpstoxBroker(BaseBroker):
    """Handles authentication and order placement for Upstox"""
    BASE_URL = "https://api.upstox.com/v2"

    def __init__(self, broker_config):
        """
        Initialize Upstox broker

        Args:
            broker_config: BrokerConfig model with access_token
        """
        self.broker_config = broker_config
        self.access_token = broker_config.access_token
        self.broker_name = broker_config.broker_name

    def authenticate(self):
        """Authenticate with Upstox API"""
        auth_url = f"{self.BASE_URL}/auth/login"
        headers = {"Content-Type": "application/json"}
        response = requests.post(auth_url, json=self.credentials, headers=headers)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Authentication failed: {response.text}")

    def place_order(
        self,
        instrument_key: str,
        quantity: int,
        order_type: str = "MARKET",
        transaction_type: str = "BUY",
        product_type: str = "INTRADAY",
        price: float = 0.0,
        trigger_price: float = 0.0
    ) -> Dict[str, Any]:
        """
        Place order via Upstox API v2

        Args:
            instrument_key: Instrument key (e.g., NSE_FO|12345)
            quantity: Order quantity
            order_type: MARKET, LIMIT, SL, SL-M
            transaction_type: BUY or SELL
            product_type: INTRADAY, DELIVERY, MARGIN
            price: Limit price (for LIMIT orders)
            trigger_price: Trigger price (for SL orders)

        Returns:
            Dict with order_id and status

        Raises:
            Exception: If order placement fails
        """
        try:
            url = f"{self.BASE_URL}/order/place"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            payload = {
                "quantity": quantity,
                "product": product_type,
                "validity": "DAY",
                "price": price if order_type == "LIMIT" else 0,
                "tag": "auto_trading",
                "instrument_token": instrument_key,
                "order_type": order_type,
                "transaction_type": transaction_type,
                "disclosed_quantity": 0,
                "trigger_price": trigger_price if order_type in ["SL", "SL-M"] else 0,
                "is_amo": False
            }

            logger.info(f"Placing Upstox order: {transaction_type} {quantity} x {instrument_key}")

            response = requests.post(url, json=payload, headers=headers)

            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "success":
                    order_id = result.get("data", {}).get("order_id")
                    logger.info(f"✅ Upstox order placed successfully: {order_id}")
                    return {
                        "success": True,
                        "order_id": order_id,
                        "message": "Order placed successfully"
                    }
                else:
                    error_msg = result.get("message", "Unknown error")
                    logger.error(f"❌ Upstox order failed: {error_msg}")
                    raise Exception(f"Order placement failed: {error_msg}")
            else:
                error_text = response.text
                logger.error(f"❌ Upstox API error: {error_text}")
                raise Exception(f"API error: {response.status_code} - {error_text}")

        except Exception as e:
            logger.error(f"❌ Error placing Upstox order: {e}")
            raise

    def get_historical_data(
        self,
        instrument_key: str,
        interval: str = "1minute",
        from_date: str = None,
        to_date: str = None
    ) -> Dict[str, Any]:
        """
        Fetch historical candle data from Upstox API.
        Uses intraday endpoint for current day data to ensure 'live' candles.
        """
        try:
            # Check if we should use the intraday endpoint (for today's data)
            from utils.timezone_utils import get_ist_now_naive
            today_str = get_ist_now_naive().strftime("%Y-%m-%d")
            
            is_today = (to_date == today_str) or (to_date is None)
            
            if is_today:
                # Use intraday endpoint for latest 'live' candles
                url = f"{self.BASE_URL}/historical-candle/intraday/{instrument_key}/{interval}"
            else:
                # Use standard historical endpoint
                url = f"{self.BASE_URL}/historical-candle/{instrument_key}/{interval}/{to_date}"
                if from_date:
                    url = f"{self.BASE_URL}/historical-candle/{instrument_key}/{interval}/{to_date}/{from_date}"

            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {self.access_token}"
            }

            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "success":
                    candles = result.get("data", {}).get("candles", [])
                    # Upstox returns candles in descending order (newest first), reverse to ascending
                    return {"candles": candles[::-1]} if candles else {"candles": []}
                else:
                    logger.error(f"❌ Upstox historical data failed: {result.get('message')}")
                    return {"candles": []}
            else:
                logger.error(f"❌ Upstox API error ({response.status_code}): {response.text}")
                return {"candles": []}

        except Exception as e:
            logger.error(f"❌ Error fetching Upstox historical data: {e}")
            return {"candles": []}

    def get_funds(self) -> Dict[str, Any]:
        """
        Get available funds and margin from Upstox API

        Returns:
            Dict containing funds data
        """
        try:
            url = f"{self.BASE_URL}/user/get-funds-and-margin"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json"
            }

            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "success":
                    return result.get("data", {})
                else:
                    logger.error(f"❌ Upstox funds fetch failed: {result.get('message')}")
                    return {}
            else:
                logger.error(f"❌ Upstox API error: {response.text}")
                return {}

        except Exception as e:
            logger.error(f"❌ Error fetching Upstox funds: {e}")
            return {}
