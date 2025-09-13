"""
Template for Python service classes following trading application standards.
"""
from decimal import Decimal
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ServiceResponse:
    """Standard response format for service operations."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class BaseService:
    """
    Base service class following trading application patterns.

    This template ensures:
    - Proper error handling
    - Decimal precision for financial data
    - Comprehensive logging
    - Type safety
    - Consistent response format
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize service with configuration.

        Args:
            config: Service configuration dictionary

        Raises:
            ValueError: If config is invalid
        """
        if not config:
            raise ValueError("Configuration cannot be empty")

        self.config = config
        self._validate_config()

    def _validate_config(self) -> None:
        """
        Validate service configuration.

        Raises:
            ValueError: If required configuration is missing
        """
        required_keys = ['service_name', 'timeout']
        missing_keys = [key for key in required_keys if key not in self.config]

        if missing_keys:
            raise ValueError(f"Missing required configuration keys: {missing_keys}")

    async def process_financial_data(
        self,
        amount: Decimal,
        currency: str = "INR"
    ) -> ServiceResponse:
        """
        Process financial data with proper decimal precision.

        Args:
            amount: Financial amount using Decimal for precision
            currency: Currency code (default: INR)

        Returns:
            ServiceResponse with processed data

        Raises:
            ValueError: If amount is invalid
            ProcessingError: If processing fails
        """
        # Input validation
        if amount < Decimal('0'):
            raise ValueError("Amount cannot be negative")

        if not currency or len(currency) != 3:
            raise ValueError("Currency must be a 3-character code")

        try:
            logger.info(f"Processing financial data: {amount} {currency}")

            # Business logic here
            processed_amount = self._calculate_with_precision(amount)

            result = {
                'original_amount': amount,
                'processed_amount': processed_amount,
                'currency': currency,
                'processing_time': datetime.utcnow()
            }

            logger.info(f"Successfully processed amount: {processed_amount}")
            return ServiceResponse(success=True, data=result)

        except Exception as e:
            logger.exception(f"Error processing financial data: {e}")
            return ServiceResponse(
                success=False,
                error=f"Processing failed: {str(e)}"
            )

    def _calculate_with_precision(self, amount: Decimal) -> Decimal:
        """
        Perform calculations with proper decimal precision.

        Args:
            amount: Input amount

        Returns:
            Calculated amount with proper precision
        """
        # Example calculation with proper precision
        tax_rate = Decimal('0.18')  # 18% GST
        return amount * (Decimal('1') + tax_rate)

    async def validate_market_hours(self) -> bool:
        """
        Validate if markets are open.

        Returns:
            True if markets are open, False otherwise
        """
        current_time = datetime.now()
        # Market hours: 9:15 AM to 3:30 PM IST
        market_open = current_time.replace(hour=9, minute=15, second=0)
        market_close = current_time.replace(hour=15, minute=30, second=0)

        return market_open <= current_time <= market_close

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get service health status.

        Returns:
            Health status dictionary
        """
        return {
            'service_name': self.config.get('service_name'),
            'status': 'healthy',
            'timestamp': datetime.utcnow(),
            'config_valid': True
        }


# Example specialized service
class TradingDataService(BaseService):
    """Example trading-specific service implementation."""

    async def calculate_portfolio_value(
        self,
        positions: List[Dict[str, Any]]
    ) -> ServiceResponse:
        """
        Calculate total portfolio value.

        Args:
            positions: List of position dictionaries

        Returns:
            ServiceResponse with portfolio value
        """
        if not positions:
            return ServiceResponse(
                success=True,
                data={'total_value': Decimal('0')}
            )

        try:
            total_value = Decimal('0')

            for position in positions:
                quantity = Decimal(str(position.get('quantity', 0)))
                price = Decimal(str(position.get('current_price', 0)))
                total_value += quantity * price

            return ServiceResponse(
                success=True,
                data={
                    'total_value': total_value,
                    'currency': 'INR',
                    'position_count': len(positions)
                }
            )

        except Exception as e:
            logger.exception(f"Error calculating portfolio value: {e}")
            return ServiceResponse(
                success=False,
                error=f"Portfolio calculation failed: {str(e)}"
            )