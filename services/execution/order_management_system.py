"""
Advanced Order Management System with Error Handling and Retry Logic
Comprehensive order lifecycle management with intelligent retry strategies
Features: Smart retry logic, error classification, order state management
"""

import asyncio
import logging
import time
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import random
from collections import defaultdict, deque
import aiohttp

logger = logging.getLogger(__name__)

class OrderState(Enum):
    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"

class ErrorType(Enum):
    NETWORK_ERROR = "NETWORK_ERROR"
    BROKER_API_ERROR = "BROKER_API_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    INVALID_SYMBOL = "INVALID_SYMBOL"
    MARKET_CLOSED = "MARKET_CLOSED"
    RATE_LIMIT = "RATE_LIMIT"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"

class RetryStrategy(Enum):
    IMMEDIATE = "IMMEDIATE"
    LINEAR_BACKOFF = "LINEAR_BACKOFF"
    EXPONENTIAL_BACKOFF = "EXPONENTIAL_BACKOFF"
    FIBONACCI_BACKOFF = "FIBONACCI_BACKOFF"
    NO_RETRY = "NO_RETRY"

@dataclass
class ErrorInfo:
    """Error information with classification"""
    error_type: ErrorType
    error_message: str
    error_code: Optional[str] = None
    is_retryable: bool = True
    suggested_action: str = "RETRY"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class RetryConfig:
    """Retry configuration for different error types"""
    max_attempts: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    initial_delay: float = 1.0
    max_delay: float = 30.0
    backoff_multiplier: float = 2.0
    jitter: bool = True

@dataclass
class OrderAttempt:
    """Individual order attempt record"""
    attempt_number: int
    timestamp: datetime
    broker_used: str
    response_time_ms: float
    success: bool
    error: Optional[ErrorInfo] = None
    broker_response: Optional[Dict] = None

@dataclass
class OrderRecord:
    """Comprehensive order record with full lifecycle tracking"""
    order_id: str
    client_order_id: str
    symbol: str
    instrument_key: str
    quantity: int
    order_type: str
    side: str
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    
    # State tracking
    current_state: OrderState = OrderState.CREATED
    state_history: List[Tuple[OrderState, datetime]] = field(default_factory=list)
    
    # Execution tracking
    filled_quantity: int = 0
    average_fill_price: float = 0.0
    remaining_quantity: int = 0
    
    # Attempt tracking
    attempts: List[OrderAttempt] = field(default_factory=list)
    current_attempt: int = 0
    max_attempts: int = 3
    
    # Error handling
    last_error: Optional[ErrorInfo] = None
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    next_retry_time: Optional[datetime] = None
    
    # Performance metrics
    total_execution_time_ms: float = 0.0
    broker_response_times: List[float] = field(default_factory=list)
    
    # Timestamps
    created_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    submitted_time: Optional[datetime] = None
    filled_time: Optional[datetime] = None
    
    # Metadata
    strategy_id: str = ""
    user_id: Optional[int] = None
    parent_order_id: Optional[str] = None
    child_order_ids: List[str] = field(default_factory=list)

class ErrorClassifier:
    """Intelligent error classification and retry decision system"""
    
    def __init__(self):
        # Error patterns for classification
        self.error_patterns = {
            ErrorType.NETWORK_ERROR: [
                "connection timeout", "network unreachable", "connection refused",
                "timeout", "connection error", "socket error"
            ],
            ErrorType.RATE_LIMIT: [
                "rate limit", "too many requests", "throttling", "quota exceeded",
                "api limit", "request limit"
            ],
            ErrorType.INSUFFICIENT_FUNDS: [
                "insufficient funds", "insufficient balance", "margin exceeded",
                "not enough balance", "insufficient margin"
            ],
            ErrorType.INVALID_SYMBOL: [
                "invalid symbol", "symbol not found", "invalid instrument",
                "unknown symbol", "invalid token"
            ],
            ErrorType.MARKET_CLOSED: [
                "market closed", "trading not allowed", "market not open",
                "outside trading hours", "session closed"
            ],
            ErrorType.AUTHENTICATION_ERROR: [
                "authentication failed", "invalid token", "unauthorized",
                "access denied", "invalid credentials"
            ]
        }
        
        # Retry configurations by error type
        self.retry_configs = {
            ErrorType.NETWORK_ERROR: RetryConfig(
                max_attempts=5,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                initial_delay=0.5,
                max_delay=10.0
            ),
            ErrorType.RATE_LIMIT: RetryConfig(
                max_attempts=3,
                strategy=RetryStrategy.LINEAR_BACKOFF,
                initial_delay=5.0,
                max_delay=30.0
            ),
            ErrorType.BROKER_API_ERROR: RetryConfig(
                max_attempts=3,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                initial_delay=1.0,
                max_delay=15.0
            ),
            ErrorType.TIMEOUT_ERROR: RetryConfig(
                max_attempts=4,
                strategy=RetryStrategy.FIBONACCI_BACKOFF,
                initial_delay=2.0,
                max_delay=20.0
            ),
            ErrorType.INSUFFICIENT_FUNDS: RetryConfig(
                max_attempts=1,
                strategy=RetryStrategy.NO_RETRY
            ),
            ErrorType.INVALID_SYMBOL: RetryConfig(
                max_attempts=1,
                strategy=RetryStrategy.NO_RETRY
            ),
            ErrorType.MARKET_CLOSED: RetryConfig(
                max_attempts=1,
                strategy=RetryStrategy.NO_RETRY
            )
        }
    
    def classify_error(self, error_message: str, error_code: Optional[str] = None) -> ErrorInfo:
        """Classify error and determine retry strategy"""
        error_message_lower = error_message.lower()
        error_type = ErrorType.SYSTEM_ERROR  # Default
        
        # Pattern matching for error classification
        for err_type, patterns in self.error_patterns.items():
            if any(pattern in error_message_lower for pattern in patterns):
                error_type = err_type
                break
        
        # Special handling for HTTP status codes
        if error_code:
            if error_code in ['429', '503']:
                error_type = ErrorType.RATE_LIMIT
            elif error_code in ['401', '403']:
                error_type = ErrorType.AUTHENTICATION_ERROR
            elif error_code in ['400', '422']:
                error_type = ErrorType.VALIDATION_ERROR
            elif error_code in ['500', '502', '504']:
                error_type = ErrorType.BROKER_API_ERROR
        
        # Determine if retryable
        non_retryable_errors = {
            ErrorType.INSUFFICIENT_FUNDS,
            ErrorType.INVALID_SYMBOL,
            ErrorType.MARKET_CLOSED,
            ErrorType.VALIDATION_ERROR
        }
        
        is_retryable = error_type not in non_retryable_errors
        
        return ErrorInfo(
            error_type=error_type,
            error_message=error_message,
            error_code=error_code,
            is_retryable=is_retryable,
            suggested_action="RETRY" if is_retryable else "FAIL"
        )
    
    def get_retry_config(self, error_type: ErrorType) -> RetryConfig:
        """Get retry configuration for error type"""
        return self.retry_configs.get(error_type, RetryConfig())

class RetryManager:
    """Manages retry logic with various backoff strategies"""
    
    @staticmethod
    def calculate_delay(attempt_number: int, retry_config: RetryConfig) -> float:
        """Calculate delay for next retry attempt"""
        if retry_config.strategy == RetryStrategy.IMMEDIATE:
            delay = 0.0
        elif retry_config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = retry_config.initial_delay * attempt_number
        elif retry_config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = retry_config.initial_delay * (retry_config.backoff_multiplier ** (attempt_number - 1))
        elif retry_config.strategy == RetryStrategy.FIBONACCI_BACKOFF:
            delay = RetryManager._fibonacci_delay(attempt_number, retry_config.initial_delay)
        else:
            delay = retry_config.initial_delay
        
        # Apply max delay limit
        delay = min(delay, retry_config.max_delay)
        
        # Add jitter to prevent thundering herd
        if retry_config.jitter:
            jitter_factor = random.uniform(0.8, 1.2)
            delay *= jitter_factor
        
        return delay
    
    @staticmethod
    def _fibonacci_delay(n: int, base_delay: float) -> float:
        """Calculate Fibonacci backoff delay"""
        if n <= 1:
            return base_delay
        elif n == 2:
            return base_delay
        
        a, b = 1, 1
        for _ in range(2, n):
            a, b = b, a + b
        
        return base_delay * b

class OrderValidator:
    """Order validation system"""
    
    def __init__(self):
        self.validation_rules = {
            'min_quantity': 1,
            'max_quantity': 10000,
            'min_price': 0.01,
            'max_price': 100000.0,
            'valid_order_types': ['MARKET', 'LIMIT', 'STOP_LOSS', 'STOP_LIMIT'],
            'valid_sides': ['BUY', 'SELL'],
            'valid_products': ['MIS', 'CNC', 'NRML']
        }
    
    def validate_order(self, order_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate order data and return validation result"""
        errors = []
        
        # Quantity validation
        quantity = order_data.get('quantity', 0)
        if quantity < self.validation_rules['min_quantity']:
            errors.append(f"Quantity {quantity} below minimum {self.validation_rules['min_quantity']}")
        elif quantity > self.validation_rules['max_quantity']:
            errors.append(f"Quantity {quantity} exceeds maximum {self.validation_rules['max_quantity']}")
        
        # Price validation
        price = order_data.get('price')
        if price is not None:
            if price < self.validation_rules['min_price']:
                errors.append(f"Price {price} below minimum {self.validation_rules['min_price']}")
            elif price > self.validation_rules['max_price']:
                errors.append(f"Price {price} exceeds maximum {self.validation_rules['max_price']}")
        
        # Order type validation
        order_type = order_data.get('order_type')
        if order_type not in self.validation_rules['valid_order_types']:
            errors.append(f"Invalid order type: {order_type}")
        
        # Side validation
        side = order_data.get('side')
        if side not in self.validation_rules['valid_sides']:
            errors.append(f"Invalid side: {side}")
        
        # Symbol validation
        symbol = order_data.get('symbol')
        if not symbol or len(symbol) < 2:
            errors.append("Invalid or missing symbol")
        
        return len(errors) == 0, errors

class OrderManagementSystem:
    """
    Advanced Order Management System
    Features:
    - Intelligent error handling and retry logic
    - Comprehensive order lifecycle tracking
    - Multiple broker support with failover
    - Performance monitoring and analytics
    - Smart order routing
    """
    
    def __init__(self, broker_manager, db_service, position_monitor):
        self.broker_manager = broker_manager
        self.db_service = db_service
        self.position_monitor = position_monitor
        
        # Core components
        self.error_classifier = ErrorClassifier()
        self.retry_manager = RetryManager()
        self.order_validator = OrderValidator()
        
        # Order tracking
        self.active_orders: Dict[str, OrderRecord] = {}
        self.completed_orders: Dict[str, OrderRecord] = {}
        self.retry_queue: asyncio.Queue = asyncio.Queue()
        
        # Performance tracking
        self.order_statistics = {
            'total_orders': 0,
            'successful_orders': 0,
            'failed_orders': 0,
            'retry_success_rate': 0.0,
            'avg_execution_time_ms': 0.0,
            'avg_attempts_per_order': 0.0,
            'error_distribution': defaultdict(int)
        }
        
        # System state
        self.system_active = False
        self.max_concurrent_orders = 100
        self.order_timeout_seconds = 30
        
        # Callbacks
        self.order_callbacks: List[Callable] = []
        
        logger.info("Order Management System initialized")
    
    async def start_system(self):
        """Start the order management system"""
        try:
            self.system_active = True
            
            # Start background tasks
            asyncio.create_task(self._process_retry_queue())
            asyncio.create_task(self._monitor_order_timeouts())
            asyncio.create_task(self._update_order_statistics())
            
            logger.info("Order Management System started")
            
        except Exception as e:
            logger.error(f"Failed to start Order Management System: {e}")
            raise
    
    async def place_order(self, order_data: Dict[str, Any]) -> str:
        """
        Place order with comprehensive error handling
        Returns order ID for tracking
        """
        start_time = time.time()
        
        # Generate order ID
        order_id = f"ORD_{int(time.time() * 1000000)}"
        client_order_id = order_data.get('client_order_id', order_id)
        
        try:
            # Validate order
            is_valid, validation_errors = self.order_validator.validate_order(order_data)
            if not is_valid:
                error_msg = f"Order validation failed: {', '.join(validation_errors)}"
                await self._handle_order_failure(order_id, ErrorType.VALIDATION_ERROR, error_msg)
                return order_id
            
            # Create order record
            order_record = OrderRecord(
                order_id=order_id,
                client_order_id=client_order_id,
                symbol=order_data['symbol'],
                instrument_key=order_data['instrument_key'],
                quantity=order_data['quantity'],
                order_type=order_data['order_type'],
                side=order_data['side'],
                price=order_data.get('price'),
                trigger_price=order_data.get('trigger_price'),
                strategy_id=order_data.get('strategy_id', ''),
                user_id=order_data.get('user_id'),
                remaining_quantity=order_data['quantity']
            )
            
            self.active_orders[order_id] = order_record
            self._update_order_state(order_record, OrderState.VALIDATING)
            
            # Attempt order placement
            success = await self._attempt_order_placement(order_record)
            
            if success:
                order_record.total_execution_time_ms = (time.time() - start_time) * 1000
                logger.info(f"Order placed successfully: {order_id} in {order_record.total_execution_time_ms:.2f}ms")
            else:
                logger.warning(f"Order placement failed after all attempts: {order_id}")
            
            return order_id
            
        except Exception as e:
            logger.error(f"Unexpected error placing order {order_id}: {e}")
            await self._handle_order_failure(order_id, ErrorType.SYSTEM_ERROR, str(e))
            return order_id
    
    async def _attempt_order_placement(self, order_record: OrderRecord) -> bool:
        """Attempt order placement with retry logic"""
        while order_record.current_attempt < order_record.max_attempts:
            order_record.current_attempt += 1
            attempt_start = time.time()
            
            try:
                self._update_order_state(order_record, OrderState.PENDING)
                
                # Convert to broker order format
                broker_order = self._convert_to_broker_order(order_record)
                
                # Attempt placement with broker
                response = await self.broker_manager.place_order(broker_order)
                
                # Record attempt
                attempt_time_ms = (time.time() - attempt_start) * 1000
                attempt = OrderAttempt(
                    attempt_number=order_record.current_attempt,
                    timestamp=datetime.now(timezone.utc),
                    broker_used=str(self.broker_manager.primary_broker),
                    response_time_ms=attempt_time_ms,
                    success=response.status.name == 'COMPLETE',
                    broker_response=response.raw_response
                )
                
                order_record.attempts.append(attempt)
                order_record.broker_response_times.append(attempt_time_ms)
                
                if response.status.name == 'COMPLETE':
                    # Success
                    order_record.filled_quantity = response.filled_quantity
                    order_record.average_fill_price = response.average_price
                    order_record.remaining_quantity = order_record.quantity - response.filled_quantity
                    order_record.filled_time = datetime.now(timezone.utc)
                    
                    self._update_order_state(order_record, OrderState.FILLED)
                    await self._notify_order_filled(order_record)
                    
                    # Move to completed orders
                    self.completed_orders[order_record.order_id] = order_record
                    self.active_orders.pop(order_record.order_id, None)
                    
                    return True
                    
                elif response.status.name == 'REJECTED':
                    # Permanent failure
                    error_info = self.error_classifier.classify_error(response.message)
                    order_record.last_error = error_info
                    
                    self._update_order_state(order_record, OrderState.REJECTED)
                    await self._handle_order_failure(
                        order_record.order_id, 
                        error_info.error_type, 
                        response.message
                    )
                    return False
                
                else:
                    # Temporary failure - check if retryable
                    error_info = self.error_classifier.classify_error(response.message)
                    order_record.last_error = error_info
                    
                    if not error_info.is_retryable:
                        self._update_order_state(order_record, OrderState.FAILED)
                        await self._handle_order_failure(
                            order_record.order_id, 
                            error_info.error_type, 
                            response.message
                        )
                        return False
                    
                    # Schedule retry
                    await self._schedule_retry(order_record, error_info)
            
            except Exception as e:
                # Handle unexpected errors
                error_info = self.error_classifier.classify_error(str(e))
                order_record.last_error = error_info
                
                attempt_time_ms = (time.time() - attempt_start) * 1000
                attempt = OrderAttempt(
                    attempt_number=order_record.current_attempt,
                    timestamp=datetime.now(timezone.utc),
                    broker_used="UNKNOWN",
                    response_time_ms=attempt_time_ms,
                    success=False,
                    error=error_info
                )
                order_record.attempts.append(attempt)
                
                if not error_info.is_retryable:
                    await self._handle_order_failure(order_record.order_id, error_info.error_type, str(e))
                    return False
                
                await self._schedule_retry(order_record, error_info)
        
        # All attempts exhausted
        self._update_order_state(order_record, OrderState.FAILED)
        await self._handle_order_failure(
            order_record.order_id, 
            ErrorType.SYSTEM_ERROR, 
            "Maximum retry attempts exceeded"
        )
        return False
    
    async def _schedule_retry(self, order_record: OrderRecord, error_info: ErrorInfo):
        """Schedule order retry with appropriate delay"""
        retry_config = self.error_classifier.get_retry_config(error_info.error_type)
        delay = self.retry_manager.calculate_delay(order_record.current_attempt, retry_config)
        
        order_record.next_retry_time = datetime.now(timezone.utc) + timedelta(seconds=delay)
        
        logger.info(f"Scheduling retry for order {order_record.order_id} in {delay:.2f} seconds")
        
        # Add to retry queue
        await self.retry_queue.put((order_record.order_id, order_record.next_retry_time))
    
    async def _process_retry_queue(self):
        """Process retry queue"""
        while self.system_active:
            try:
                # Get item from queue with timeout
                try:
                    order_id, retry_time = await asyncio.wait_for(
                        self.retry_queue.get(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Wait until retry time
                now = datetime.now(timezone.utc)
                if retry_time > now:
                    delay = (retry_time - now).total_seconds()
                    await asyncio.sleep(delay)
                
                # Retry order if still active
                if order_id in self.active_orders:
                    order_record = self.active_orders[order_id]
                    logger.info(f"Retrying order {order_id}, attempt {order_record.current_attempt + 1}")
                    
                    await self._attempt_order_placement(order_record)
                
            except Exception as e:
                logger.error(f"Error processing retry queue: {e}")
                await asyncio.sleep(1.0)
    
    async def _monitor_order_timeouts(self):
        """Monitor and handle order timeouts"""
        while self.system_active:
            try:
                current_time = datetime.now(timezone.utc)
                timeout_orders = []
                
                for order_id, order_record in self.active_orders.items():
                    # Check for timeout
                    order_age = (current_time - order_record.created_time).total_seconds()
                    if order_age > self.order_timeout_seconds:
                        timeout_orders.append(order_id)
                
                # Handle timeout orders
                for order_id in timeout_orders:
                    order_record = self.active_orders[order_id]
                    self._update_order_state(order_record, OrderState.EXPIRED)
                    await self._handle_order_failure(order_id, ErrorType.TIMEOUT_ERROR, "Order timeout")
                    
                await asyncio.sleep(5.0)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error monitoring order timeouts: {e}")
                await asyncio.sleep(10.0)
    
    def _convert_to_broker_order(self, order_record: OrderRecord) -> Any:
        """Convert order record to broker-specific format"""
        # This would convert to broker's expected format
        # For now, returning a mock format
        return {
            'symbol': order_record.symbol,
            'instrument_key': order_record.instrument_key,
            'quantity': order_record.quantity,
            'order_type': order_record.order_type,
            'side': order_record.side,
            'price': order_record.price,
            'trigger_price': order_record.trigger_price
        }
    
    def _update_order_state(self, order_record: OrderRecord, new_state: OrderState):
        """Update order state with history tracking"""
        order_record.state_history.append((order_record.current_state, datetime.now(timezone.utc)))
        order_record.current_state = new_state
        logger.debug(f"Order {order_record.order_id} state: {new_state.value}")
    
    async def _handle_order_failure(self, order_id: str, error_type: ErrorType, error_message: str):
        """Handle order failure"""
        logger.error(f"Order {order_id} failed: {error_type.value} - {error_message}")
        
        # Update statistics
        self.order_statistics['error_distribution'][error_type.value] += 1
        
        # Notify callbacks
        await self._notify_order_failed(order_id, error_type, error_message)
        
        # Move to completed orders if it exists in active orders
        if order_id in self.active_orders:
            self.completed_orders[order_id] = self.active_orders.pop(order_id)
    
    async def _notify_order_filled(self, order_record: OrderRecord):
        """Notify about order fill"""
        for callback in self.order_callbacks:
            try:
                await callback('ORDER_FILLED', order_record.order_id, asdict(order_record))
            except Exception as e:
                logger.error(f"Error in order callback: {e}")
    
    async def _notify_order_failed(self, order_id: str, error_type: ErrorType, error_message: str):
        """Notify about order failure"""
        for callback in self.order_callbacks:
            try:
                await callback('ORDER_FAILED', order_id, {
                    'error_type': error_type.value,
                    'error_message': error_message
                })
            except Exception as e:
                logger.error(f"Error in order callback: {e}")
    
    async def _update_order_statistics(self):
        """Update order statistics periodically"""
        while self.system_active:
            try:
                total_orders = len(self.completed_orders) + len(self.active_orders)
                filled_orders = len([o for o in self.completed_orders.values() 
                                   if o.current_state == OrderState.FILLED])
                failed_orders = len([o for o in self.completed_orders.values() 
                                   if o.current_state in [OrderState.FAILED, OrderState.REJECTED, OrderState.EXPIRED]])
                
                self.order_statistics.update({
                    'total_orders': total_orders,
                    'successful_orders': filled_orders,
                    'failed_orders': failed_orders
                })
                
                # Calculate success rate
                if total_orders > 0:
                    success_rate = filled_orders / total_orders * 100
                    self.order_statistics['success_rate'] = success_rate
                
                # Calculate average execution time
                execution_times = [o.total_execution_time_ms for o in self.completed_orders.values() 
                                 if o.total_execution_time_ms > 0]
                if execution_times:
                    self.order_statistics['avg_execution_time_ms'] = sum(execution_times) / len(execution_times)
                
                await asyncio.sleep(30.0)  # Update every 30 seconds
                
            except Exception as e:
                logger.error(f"Error updating order statistics: {e}")
                await asyncio.sleep(60.0)
    
    def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive order status"""
        order_record = self.active_orders.get(order_id) or self.completed_orders.get(order_id)
        
        if not order_record:
            return None
        
        return {
            'order_id': order_record.order_id,
            'symbol': order_record.symbol,
            'quantity': order_record.quantity,
            'filled_quantity': order_record.filled_quantity,
            'remaining_quantity': order_record.remaining_quantity,
            'current_state': order_record.current_state.value,
            'attempts': len(order_record.attempts),
            'avg_response_time_ms': (sum(order_record.broker_response_times) / len(order_record.broker_response_times) 
                                   if order_record.broker_response_times else 0.0),
            'last_error': asdict(order_record.last_error) if order_record.last_error else None,
            'created_time': order_record.created_time.isoformat(),
            'filled_time': order_record.filled_time.isoformat() if order_record.filled_time else None
        }
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            'system_active': self.system_active,
            'active_orders': len(self.active_orders),
            'completed_orders': len(self.completed_orders),
            'retry_queue_size': self.retry_queue.qsize(),
            'statistics': self.order_statistics.copy(),
            'active_order_details': [
                {
                    'order_id': o.order_id,
                    'symbol': o.symbol,
                    'state': o.current_state.value,
                    'attempts': o.current_attempt
                }
                for o in self.active_orders.values()
            ]
        }
    
    def add_order_callback(self, callback: Callable):
        """Add order event callback"""
        self.order_callbacks.append(callback)
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel active order"""
        if order_id not in self.active_orders:
            return False
        
        try:
            order_record = self.active_orders[order_id]
            
            # Attempt cancellation with broker
            success = await self.broker_manager.cancel_order(order_id)
            
            if success:
                self._update_order_state(order_record, OrderState.CANCELLED)
                self.completed_orders[order_id] = self.active_orders.pop(order_id)
                logger.info(f"Order cancelled successfully: {order_id}")
                return True
            else:
                logger.warning(f"Failed to cancel order: {order_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down Order Management System...")
        self.system_active = False
        
        # Cancel all active orders
        for order_id in list(self.active_orders.keys()):
            await self.cancel_order(order_id)
        
        logger.info("Order Management System shutdown complete")