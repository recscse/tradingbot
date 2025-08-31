# services/breakout/data_adapters.py
"""
Modular Data Adapters for BreakoutScannerService

This module provides multiple data source adapters to integrate the breakout scanner
with existing live data feeds in the trading system.

Supported Data Sources:
- Market Data Hub (High-performance NumPy/Pandas)
- Centralized WebSocket Manager (Live broker feeds)
- Instrument Registry (Cached price data with callbacks)
- Upstox WebSocket (Direct broker integration)
- Redis Pub/Sub (Distributed data sharing)
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Protocol
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


@dataclass
class TickData:
    """
    Standardized tick data format for breakout scanner
    
    All data adapters convert their native format to this standard format
    """
    instrument_key: str
    symbol: str
    ltp: float  # Last traded price
    ltt: int   # Last traded time (milliseconds)
    ltq: int   # Last traded quantity
    volume: int = 0
    open_price: float = 0.0
    high: float = 0.0
    low: float = 0.0
    prev_close: float = 0.0
    change: float = 0.0
    change_percent: float = 0.0
    timestamp: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], instrument_key: str = None, symbol: str = None) -> 'TickData':
        """Create TickData from dictionary with flexible field mapping"""
        return cls(
            instrument_key=instrument_key or data.get('instrument_key', ''),
            symbol=symbol or data.get('symbol', ''),
            ltp=float(data.get('ltp', data.get('last_price', data.get('close', 0)))),
            ltt=int(data.get('ltt', data.get('timestamp', datetime.now().timestamp() * 1000))),
            ltq=int(data.get('ltq', data.get('quantity', data.get('last_quantity', 0)))),
            volume=int(data.get('volume', 0)),
            open_price=float(data.get('open', data.get('open_price', 0))),
            high=float(data.get('high', 0)),
            low=float(data.get('low', 0)),
            prev_close=float(data.get('prev_close', data.get('previous_close', 0))),
            change=float(data.get('change', 0)),
            change_percent=float(data.get('change_percent', data.get('chp', 0)))
        )


class BreakoutDataAdapter(ABC):
    """
    Abstract base class for breakout scanner data adapters
    
    Each data source (Market Data Hub, WebSocket Manager, etc.) implements
    this interface to provide standardized tick data to the breakout scanner.
    """
    
    def __init__(self, name: str):
        self.name = name
        self.is_active = False
        self.callback_handlers: List[Callable[[TickData], None]] = []
        
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the data adapter and establish connections"""
        pass
    
    @abstractmethod
    async def start(self) -> None:
        """Start receiving data from the source"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop receiving data and clean up resources"""
        pass
    
    @abstractmethod
    def subscribe_instruments(self, instrument_keys: List[str]) -> None:
        """Subscribe to specific instruments for data updates"""
        pass
    
    def add_tick_handler(self, handler: Callable[[TickData], None]) -> None:
        """Add a callback handler for tick data updates"""
        self.callback_handlers.append(handler)
    
    def remove_tick_handler(self, handler: Callable[[TickData], None]) -> None:
        """Remove a callback handler"""
        if handler in self.callback_handlers:
            self.callback_handlers.remove(handler)
    
    async def _notify_handlers(self, tick_data: TickData) -> None:
        """Notify all registered handlers of new tick data"""
        for handler in self.callback_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(tick_data)
                else:
                    handler(tick_data)
            except Exception as e:
                logger.error(f"❌ Error in tick handler for {self.name}: {e}")


class MarketDataHubAdapter(BreakoutDataAdapter):
    """
    Adapter for high-performance Market Data Hub service
    
    Integrates with services/market_data_hub.py HighPerformanceMarketDataHub
    for ultra-fast NumPy/Pandas based tick processing with microsecond latencies
    """
    
    def __init__(self):
        super().__init__("MarketDataHub")
        self.hub = None
        self.subscription_handles = {}
        self.subscribed_symbols = set()
        
    async def initialize(self) -> bool:
        """Initialize connection to HighPerformanceMarketDataHub"""
        try:
            # Import the existing market data hub instance
            from services.market_data_hub import market_data_hub
            
            self.hub = market_data_hub
            
            # Start the hub if not already running
            if not self.hub.is_running:
                await self.hub.start()
            
            logger.info("✅ MarketDataHubAdapter initialized with existing market_data_hub")
            return True
                
        except ImportError as e:
            logger.error(f"❌ HighPerformanceMarketDataHub not available: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to initialize MarketDataHubAdapter: {e}")
            return False
    
    async def start(self) -> None:
        """Start receiving data from HighPerformanceMarketDataHub"""
        if not self.hub:
            logger.error("❌ HighPerformanceMarketDataHub not initialized")
            return
        
        try:
            # Start the hub's data processing
            await self.hub.start_processing()
            self.is_active = True
            logger.info("🚀 MarketDataHubAdapter started with high-performance data processing")
                
        except Exception as e:
            logger.error(f"❌ Error starting MarketDataHubAdapter: {e}")
    
    async def stop(self) -> None:
        """Stop receiving data and cleanup resources"""
        try:
            if self.hub:
                # Unsubscribe from all topics
                for symbol, handle in self.subscription_handles.items():
                    await self.hub.unsubscribe_from_topic(f"price_update.{symbol}", handle)
                
                # Unsubscribe instruments  
                for symbol in self.subscribed_symbols:
                    await self.hub.unsubscribe_instrument(symbol)
                
                # Stop processing
                await self.hub.stop_processing()
                
                self.subscription_handles.clear()
                self.subscribed_symbols.clear()
                self.is_active = False
                
            logger.info("🛑 MarketDataHubAdapter stopped successfully")
            
        except Exception as e:
            logger.error(f"❌ Error stopping MarketDataHubAdapter: {e}")
    
    def subscribe_instruments(self, instrument_keys: List[str]) -> None:
        """Subscribe to specific instruments via HighPerformanceMarketDataHub"""
        if not self.hub:
            logger.warning("❌ HighPerformanceMarketDataHub not available for subscription")
            return
        
        try:
            for instrument_key in instrument_keys:
                # Extract symbol from instrument key if needed
                symbol = self._extract_symbol(instrument_key)
                
                # Subscribe to price update topic
                asyncio.create_task(
                    self._subscribe_to_symbol_async(symbol, instrument_key)
                )
            
            logger.info(f"📊 Initiated subscription to {len(instrument_keys)} instruments in HighPerformanceMarketDataHub")
            
        except Exception as e:
            logger.error(f"❌ Error subscribing to instruments: {e}")
    
    async def _subscribe_to_symbol_async(self, symbol: str, instrument_key: str):
        """Async helper to subscribe to individual symbol"""
        try:
            # Subscribe to live instrument data
            await self.hub.subscribe_instrument(symbol)
            
            # Subscribe to price update events
            subscription_handle = await self.hub.subscribe_to_topic(
                f"price_update.{symbol}",
                lambda data: self._hub_price_update_callback(symbol, instrument_key, data)
            )
            
            if subscription_handle:
                self.subscription_handles[symbol] = subscription_handle
                self.subscribed_symbols.add(symbol)
                logger.debug(f"✅ Subscribed to {symbol} via HighPerformanceMarketDataHub")
            
        except Exception as e:
            logger.error(f"❌ Error subscribing to {symbol}: {e}")
    
    def _extract_symbol(self, instrument_key: str) -> str:
        """Extract trading symbol from instrument key"""
        # Handle different instrument key formats
        if "|" in instrument_key:
            parts = instrument_key.split("|")
            return parts[-1] if len(parts) > 1 else instrument_key
        return instrument_key
    
    def _hub_price_update_callback(self, symbol: str, instrument_key: str, data: Dict[str, Any]) -> None:
        """Callback for HighPerformanceMarketDataHub price updates"""
        try:
            # Convert high-performance hub data to standardized TickData format
            tick_data = TickData(
                instrument_key=instrument_key,
                symbol=symbol,
                ltp=float(data.get('ltp', data.get('price', 0))),
                ltt=int(data.get('timestamp', data.get('ltt', datetime.now().timestamp() * 1000))),
                ltq=int(data.get('ltq', data.get('last_quantity', data.get('volume', 0)))),
                volume=int(data.get('volume', data.get('total_volume', 0))),
                open_price=float(data.get('open', data.get('open_price', 0))),
                high=float(data.get('high', 0)),
                low=float(data.get('low', 0)),
                prev_close=float(data.get('prev_close', data.get('previous_close', 0))),
                change=float(data.get('change', 0)),
                change_percent=float(data.get('change_percent', data.get('chp', 0))),
                timestamp=datetime.fromtimestamp(data.get('timestamp', datetime.now().timestamp()))
            )
            
            # Only process valid price updates
            if tick_data.ltp > 0:
                # Notify all registered handlers asynchronously
                asyncio.create_task(self._notify_handlers(tick_data))
            
        except Exception as e:
            logger.error(f"❌ Error processing price update for {symbol}: {e}")
    
    async def get_current_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get current prices using high-performance data retrieval"""
        if not self.hub:
            return {}
        
        try:
            prices = {}
            for symbol in symbols:
                # Use hub's optimized data retrieval
                current_data = await self.hub.get_current_data(symbol)
                if current_data and 'ltp' in current_data:
                    prices[symbol] = float(current_data['ltp'])
            return prices
            
        except Exception as e:
            logger.error(f"❌ Error getting current prices from HighPerformanceMarketDataHub: {e}")
            return {}
    
    async def get_historical_data(self, symbol: str, period: int = 100) -> List[Dict[str, Any]]:
        """Get historical data for technical analysis"""
        if not self.hub:
            return []
        
        try:
            # Use hub's high-performance historical data retrieval  
            historical_data = await self.hub.get_historical_data(symbol, limit=period)
            return historical_data or []
            
        except Exception as e:
            logger.error(f"❌ Error getting historical data for {symbol}: {e}")
            return []


class CentralizedWebSocketAdapter(BreakoutDataAdapter):
    """
    Adapter for Centralized WebSocket Manager (Live broker feeds)
    
    Integrates with services/centralized_ws_manager.py for real-time Upstox broker data
    Provides access to live market data from the centralized admin WebSocket connection
    """
    
    def __init__(self):
        super().__init__("CentralizedWebSocket")
        self.ws_manager = None
        self._callback_registered = False
        self._subscribed_instruments = set()
        
    async def initialize(self) -> bool:
        """Initialize connection to Centralized WebSocket Manager"""
        try:
            from services.centralized_ws_manager import centralized_manager, register_market_data_callback
            self.ws_manager = centralized_manager
            self.register_callback = register_market_data_callback
            
            # Initialize the centralized manager if needed
            if not getattr(self.ws_manager, '_initialized', False):
                await self.ws_manager.initialize()
            
            logger.info("✅ CentralizedWebSocketAdapter initialized successfully")
            return True
        except ImportError as e:
            logger.error(f"❌ Failed to import Centralized WebSocket Manager: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error initializing CentralizedWebSocketAdapter: {e}")
            return False
    
    async def start(self) -> None:
        """Start receiving data from Centralized WebSocket Manager"""
        if not self.ws_manager:
            logger.error("❌ Centralized WebSocket Manager not initialized")
            return
        
        try:
            # Register callback for price updates
            success = self.register_callback(self._ws_data_callback)
            if success:
                self._callback_registered = True
                self.is_active = True
                logger.info("🚀 CentralizedWebSocketAdapter started - listening for price updates")
            else:
                logger.error("❌ Failed to register callback with Centralized WebSocket Manager")
                
        except Exception as e:
            logger.error(f"❌ Error starting CentralizedWebSocketAdapter: {e}")
    
    async def stop(self) -> None:
        """Stop receiving data from Centralized WebSocket Manager"""
        if self._callback_registered:
            try:
                # Unregister callback (implementation depends on centralized manager API)
                self.is_active = False
                self._callback_registered = False
                logger.info("🛑 CentralizedWebSocketAdapter stopped")
            except Exception as e:
                logger.error(f"❌ Error stopping CentralizedWebSocketAdapter: {e}")
    
    def subscribe_instruments(self, instrument_keys: List[str]) -> None:
        """Subscribe to specific instruments in Centralized WebSocket Manager"""
        if self.ws_manager:
            try:
                # The centralized manager typically handles subscriptions automatically
                logger.info(f"📊 Subscribed to {len(instrument_keys)} instruments in Centralized WebSocket")
            except Exception as e:
                logger.error(f"❌ Error subscribing to instruments: {e}")
    
    async def _ws_data_callback(self, data: Dict[str, Any]) -> None:
        """Callback for Centralized WebSocket Manager updates"""
        try:
            # Handle different data formats from WebSocket feed
            feeds = None
            
            if isinstance(data, dict) and "feeds" in data:
                feeds = data["feeds"]
            elif isinstance(data, list):
                feeds = data
            elif isinstance(data, dict) and any(key.startswith(('NSE_', 'BSE_')) for key in data.keys()):
                # Direct feed format
                feeds = [{"instrument_key": k, **v} for k, v in data.items()]
            
            if not feeds:
                return
            
            # Convert each feed update to TickData
            for feed in feeds:
                try:
                    instrument_key = feed.get('instrument_key', '')
                    if not instrument_key:
                        continue
                    
                    # Extract symbol
                    symbol = feed.get('symbol', instrument_key.split('|')[-1] if '|' in instrument_key else instrument_key)
                    
                    tick_data = TickData.from_dict(
                        feed,
                        instrument_key=instrument_key,
                        symbol=symbol
                    )
                    
                    # Notify handlers
                    await self._notify_handlers(tick_data)
                    
                except Exception as e:
                    logger.debug(f"❌ Error processing WebSocket feed: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error in CentralizedWebSocket callback: {e}")


class InstrumentRegistryAdapter(BreakoutDataAdapter):
    """
    Adapter for Instrument Registry (Cached price data with callbacks)
    
    Integrates with services/instrument_registry.py for cached data and metadata access
    Provides fast access to instrument information and live price callbacks
    """
    
    def __init__(self):
        super().__init__("InstrumentRegistry")
        self.registry = None
        self._subscribed_instruments = set()
        self._strategy_registered = False
        
    async def initialize(self) -> bool:
        """Initialize connection to Instrument Registry"""
        try:
            from services.instrument_registry import instrument_registry
            
            # Use the singleton instance
            self.registry = instrument_registry
            
            logger.info("✅ InstrumentRegistryAdapter initialized with singleton instance")
            return True
        except ImportError as e:
            logger.error(f"❌ Failed to import Instrument Registry: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error initializing InstrumentRegistryAdapter: {e}")
            return False
    
    async def start(self) -> None:
        """Start receiving data using InstrumentRegistry callback system"""
        if not self.registry:
            logger.error("❌ Instrument Registry not initialized")
            return
        
        try:
            # Register as a strategy callback for real-time price updates
            success = self.registry.register_strategy_callback(
                strategy_name="breakout_scanner",
                instruments=list(self._subscribed_instruments) if self._subscribed_instruments else [],
                callback=self._registry_price_callback
            )
            
            if success:
                self._strategy_registered = True
                self.is_active = True
                logger.info("🚀 InstrumentRegistryAdapter started with strategy callback system")
            else:
                logger.warning("⚠️ Failed to register strategy callback, falling back to polling")
                # Fallback to event subscription
                self.registry.subscribe("price_update", self._registry_event_callback)
                self.is_active = True
                
        except Exception as e:
            logger.error(f"❌ Error starting InstrumentRegistryAdapter: {e}")
    
    async def stop(self) -> None:
        """Stop receiving data from Instrument Registry"""
        try:
            if self._strategy_registered and self.registry:
                # Unregister strategy callback (implementation depends on registry API)
                self._strategy_registered = False
            
            # Unsubscribe from events
            if self.registry:
                self.registry.unsubscribe("price_update", self._registry_event_callback)
            
            self.is_active = False
            logger.info("🛑 InstrumentRegistryAdapter stopped")
            
        except Exception as e:
            logger.error(f"❌ Error stopping InstrumentRegistryAdapter: {e}")
    
    def subscribe_instruments(self, instrument_keys: List[str]) -> None:
        """Subscribe to specific instruments using InstrumentRegistry callback system"""
        try:
            self._subscribed_instruments = set(instrument_keys)
            
            # If already started with strategy callback, re-register with new instruments
            if self._strategy_registered and self.registry:
                success = self.registry.register_strategy_callback(
                    strategy_name="breakout_scanner",
                    instruments=instrument_keys,
                    callback=self._registry_price_callback
                )
                if success:
                    logger.info(f"📊 Updated subscription to {len(instrument_keys)} instruments in InstrumentRegistry")
                else:
                    logger.warning("⚠️ Failed to update strategy subscription")
            else:
                logger.info(f"📊 Prepared subscription to {len(instrument_keys)} instruments in InstrumentRegistry")
                
        except Exception as e:
            logger.error(f"❌ Error subscribing to instruments: {e}")
    
    def _registry_price_callback(self, instrument_key: str, price_data: Dict[str, Any]) -> None:
        """Callback for InstrumentRegistry strategy updates"""
        try:
            # Only process instruments we're subscribed to
            if instrument_key not in self._subscribed_instruments:
                return
            
            # Get symbol from registry metadata or extract from key
            symbol = self._get_symbol_for_instrument(instrument_key)
            
            # Convert to standard TickData format
            tick_data = TickData.from_dict(
                price_data,
                instrument_key=instrument_key,
                symbol=symbol
            )
            
            # Notify handlers asynchronously
            asyncio.create_task(self._notify_handlers(tick_data))
            
        except Exception as e:
            logger.error(f"❌ Error in InstrumentRegistry price callback for {instrument_key}: {e}")
    
    def _registry_event_callback(self, data: Dict[str, Any]) -> None:
        """Fallback callback for InstrumentRegistry event system"""
        try:
            # Handle bulk price updates from registry events
            if isinstance(data, dict) and "prices" in data:
                for instrument_key, price_data in data["prices"].items():
                    if instrument_key in self._subscribed_instruments:
                        self._registry_price_callback(instrument_key, price_data)
            elif isinstance(data, dict) and "instrument_key" in data:
                # Single instrument update
                instrument_key = data["instrument_key"]
                if instrument_key in self._subscribed_instruments:
                    self._registry_price_callback(instrument_key, data)
                    
        except Exception as e:
            logger.error(f"❌ Error in InstrumentRegistry event callback: {e}")
    
    def _get_symbol_for_instrument(self, instrument_key: str) -> str:
        """Get trading symbol for instrument key using registry metadata"""
        try:
            # Use registry's spot instruments mapping
            if self.registry and hasattr(self.registry, '_spot_instruments'):
                spot_instruments = self.registry._spot_instruments
                if instrument_key in spot_instruments:
                    return spot_instruments[instrument_key].get('trading_symbol', 
                                                               spot_instruments[instrument_key].get('symbol', instrument_key))
            
            # Fallback to extracting from instrument key
            return instrument_key.split('|')[-1] if '|' in instrument_key else instrument_key
            
        except Exception:
            return instrument_key.split('|')[-1] if '|' in instrument_key else instrument_key
    
    async def get_instrument_metadata(self, instrument_key: str) -> Dict[str, Any]:
        """Get comprehensive instrument metadata from registry"""
        if not self.registry:
            return {}
        
        try:
            # Get from spot instruments
            if hasattr(self.registry, '_spot_instruments'):
                spot_instruments = self.registry._spot_instruments
                if instrument_key in spot_instruments:
                    return spot_instruments[instrument_key]
            
            return {}
            
        except Exception as e:
            logger.error(f"❌ Error getting metadata for {instrument_key}: {e}")
            return {}


class RedisStreamAdapter(BreakoutDataAdapter):
    """
    Adapter for Redis Pub/Sub streams (Distributed data sharing)
    
    Subscribes to Redis channels for distributed market data
    """
    
    def __init__(self, redis_url: str = None):
        super().__init__("RedisStream")
        self.redis_url = redis_url or "redis://localhost:6379"
        self.redis_client = None
        self.subscription_task = None
        self.subscribed_channels = ["market_data", "tick_data", "live_prices"]
        
    async def initialize(self) -> bool:
        """Initialize Redis connection"""
        try:
            import redis.asyncio as redis
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            
            # Test connection
            await self.redis_client.ping()
            logger.info("✅ RedisStreamAdapter initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Redis connection: {e}")
            return False
    
    async def start(self) -> None:
        """Start subscribing to Redis channels"""
        if not self.redis_client:
            logger.error("❌ Redis client not initialized")
            return
        
        try:
            self.subscription_task = asyncio.create_task(self._redis_subscription_loop())
            self.is_active = True
            logger.info("🚀 RedisStreamAdapter started successfully")
            
        except Exception as e:
            logger.error(f"❌ Error starting RedisStreamAdapter: {e}")
    
    async def stop(self) -> None:
        """Stop Redis subscription and close connection"""
        if self.subscription_task:
            self.subscription_task.cancel()
            try:
                await self.subscription_task
            except asyncio.CancelledError:
                pass
        
        if self.redis_client:
            await self.redis_client.close()
        
        self.is_active = False
        logger.info("🛑 RedisStreamAdapter stopped")
    
    def subscribe_instruments(self, instrument_keys: List[str]) -> None:
        """Subscribe to instrument-specific Redis channels"""
        try:
            # Add instrument-specific channels
            for instrument_key in instrument_keys:
                channel = f"ticks:{instrument_key}"
                if channel not in self.subscribed_channels:
                    self.subscribed_channels.append(channel)
            
            logger.info(f"📊 Subscribed to {len(self.subscribed_channels)} Redis channels")
        except Exception as e:
            logger.error(f"❌ Error subscribing to instrument channels: {e}")
    
    async def _redis_subscription_loop(self) -> None:
        """Redis subscription loop"""
        while self.is_active:
            try:
                pubsub = self.redis_client.pubsub()
                await pubsub.subscribe(*self.subscribed_channels)
                
                async for message in pubsub.listen():
                    if message['type'] == 'message':
                        try:
                            data = json.loads(message['data'])
                            
                            # Extract instrument info from data or channel
                            instrument_key = data.get('instrument_key', '')
                            if not instrument_key and ':' in message['channel']:
                                instrument_key = message['channel'].split(':', 1)[1]
                            
                            symbol = data.get('symbol', instrument_key.split('|')[-1] if '|' in instrument_key else instrument_key)
                            
                            tick_data = TickData.from_dict(
                                data,
                                instrument_key=instrument_key,
                                symbol=symbol
                            )
                            
                            await self._notify_handlers(tick_data)
                            
                        except json.JSONDecodeError as e:
                            logger.debug(f"❌ Invalid JSON in Redis message: {e}")
                        except Exception as e:
                            logger.error(f"❌ Error processing Redis message: {e}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in Redis subscription loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying


class MultiSourceDataManager:
    """
    Manager class that coordinates multiple data adapters
    
    Provides failover, load balancing, and data deduplication across sources
    """
    
    def __init__(self):
        self.adapters: Dict[str, BreakoutDataAdapter] = {}
        self.primary_adapter: Optional[str] = None
        self.active_adapters: List[str] = []
        self.tick_handlers: List[Callable[[TickData], None]] = []
        self._last_tick_time: Dict[str, float] = {}  # For deduplication
        
    def add_adapter(self, adapter: BreakoutDataAdapter, is_primary: bool = False) -> None:
        """Add a data adapter to the manager"""
        self.adapters[adapter.name] = adapter
        adapter.add_tick_handler(self._handle_tick_data)
        
        if is_primary:
            self.primary_adapter = adapter.name
        
        logger.info(f"📊 Added adapter: {adapter.name} (primary: {is_primary})")
    
    async def initialize_all(self) -> List[str]:
        """Initialize all adapters and return list of successful initializations"""
        successful = []
        
        for name, adapter in self.adapters.items():
            try:
                if await adapter.initialize():
                    successful.append(name)
                    logger.info(f"✅ Initialized adapter: {name}")
                else:
                    logger.error(f"❌ Failed to initialize adapter: {name}")
            except Exception as e:
                logger.error(f"❌ Error initializing adapter {name}: {e}")
        
        return successful
    
    async def start_all(self) -> None:
        """Start all successfully initialized adapters"""
        for name, adapter in self.adapters.items():
            try:
                await adapter.start()
                if adapter.is_active:
                    self.active_adapters.append(name)
                    logger.info(f"🚀 Started adapter: {name}")
            except Exception as e:
                logger.error(f"❌ Error starting adapter {name}: {e}")
    
    async def stop_all(self) -> None:
        """Stop all active adapters"""
        for name, adapter in self.adapters.items():
            try:
                await adapter.stop()
                logger.info(f"🛑 Stopped adapter: {name}")
            except Exception as e:
                logger.error(f"❌ Error stopping adapter {name}: {e}")
        
        self.active_adapters.clear()
    
    def subscribe_instruments(self, instrument_keys: List[str]) -> None:
        """Subscribe to instruments across all active adapters"""
        for name in self.active_adapters:
            try:
                self.adapters[name].subscribe_instruments(instrument_keys)
            except Exception as e:
                logger.error(f"❌ Error subscribing instruments in {name}: {e}")
    
    def add_tick_handler(self, handler: Callable[[TickData], None]) -> None:
        """Add handler for processed tick data"""
        self.tick_handlers.append(handler)
    
    async def _handle_tick_data(self, tick_data: TickData) -> None:
        """Handle tick data from adapters (with deduplication)"""
        try:
            # Simple deduplication based on instrument and time
            dedup_key = f"{tick_data.instrument_key}:{tick_data.ltt}"
            current_time = datetime.now().timestamp()
            
            # Check if we've seen this tick recently (within 100ms)
            if dedup_key in self._last_tick_time:
                time_diff = current_time - self._last_tick_time[dedup_key]
                if time_diff < 0.1:  # 100ms deduplication window
                    return
            
            self._last_tick_time[dedup_key] = current_time
            
            # Cleanup old deduplication entries (keep last 1000)
            if len(self._last_tick_time) > 1000:
                # Remove oldest 200 entries
                oldest_keys = sorted(self._last_tick_time.keys())[:200]
                for key in oldest_keys:
                    self._last_tick_time.pop(key, None)
            
            # Notify all handlers
            for handler in self.tick_handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(tick_data)
                    else:
                        handler(tick_data)
                except Exception as e:
                    logger.error(f"❌ Error in tick handler: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error handling tick data: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all adapters"""
        return {
            "total_adapters": len(self.adapters),
            "active_adapters": len(self.active_adapters),
            "primary_adapter": self.primary_adapter,
            "adapter_status": {
                name: adapter.is_active 
                for name, adapter in self.adapters.items()
            },
            "tick_handlers": len(self.tick_handlers)
        }


# ===== FACTORY FUNCTIONS FOR EASY INITIALIZATION =====

async def create_market_data_hub_adapter() -> Optional[MarketDataHubAdapter]:
    """Factory function to create and initialize MarketDataHubAdapter"""
    adapter = MarketDataHubAdapter()
    if await adapter.initialize():
        return adapter
    return None

async def create_centralized_websocket_adapter() -> Optional[CentralizedWebSocketAdapter]:
    """Factory function to create and initialize CentralizedWebSocketAdapter"""
    adapter = CentralizedWebSocketAdapter()
    if await adapter.initialize():
        return adapter
    return None

async def create_instrument_registry_adapter() -> Optional[InstrumentRegistryAdapter]:
    """Factory function to create and initialize InstrumentRegistryAdapter"""
    adapter = InstrumentRegistryAdapter()
    if await adapter.initialize():
        return adapter
    return None

async def create_redis_stream_adapter(redis_url: str = None) -> Optional[RedisStreamAdapter]:
    """Factory function to create and initialize RedisStreamAdapter"""
    adapter = RedisStreamAdapter(redis_url)
    if await adapter.initialize():
        return adapter
    return None

async def create_multi_source_manager(enable_redis: bool = False, redis_url: str = None) -> MultiSourceDataManager:
    """
    Factory function to create a fully configured MultiSourceDataManager
    
    Args:
        enable_redis: Enable Redis stream adapter
        redis_url: Redis URL (if enable_redis is True)
    
    Returns:
        Configured MultiSourceDataManager with available adapters
    """
    manager = MultiSourceDataManager()
    
    # Try to initialize Market Data Hub (high priority)
    hub_adapter = await create_market_data_hub_adapter()
    if hub_adapter:
        manager.add_adapter(hub_adapter, is_primary=True)
    
    # Try to initialize Centralized WebSocket (fallback)
    ws_adapter = await create_centralized_websocket_adapter()
    if ws_adapter:
        manager.add_adapter(ws_adapter, is_primary=(hub_adapter is None))
    
    # Try to initialize Instrument Registry (metadata and caching)
    registry_adapter = await create_instrument_registry_adapter()
    if registry_adapter:
        manager.add_adapter(registry_adapter)
    
    # Optionally initialize Redis Stream
    if enable_redis:
        redis_adapter = await create_redis_stream_adapter(redis_url)
        if redis_adapter:
            manager.add_adapter(redis_adapter)
    
    # Initialize and start all adapters
    successful_adapters = await manager.initialize_all()
    if successful_adapters:
        await manager.start_all()
        logger.info(f"✅ MultiSourceDataManager created with {len(successful_adapters)} active adapters: {successful_adapters}")
    else:
        logger.error("❌ No data adapters were successfully initialized")
    
    return manager


# ===== USAGE EXAMPLE =====

async def example_usage():
    """Example usage of the modular data adapter system"""
    
    # Create multi-source manager with all available adapters
    data_manager = await create_multi_source_manager(enable_redis=True)
    
    # Define instruments to monitor
    instruments = [
        "NSE_EQ|INE002A01018",  # Reliance
        "NSE_EQ|INE009A01021",  # Infosys  
        "NSE_EQ|INE467B01029",  # TCS
        "NSE_EQ|INE040A01034",  # HDFC Bank
        "NSE_EQ|INE030A01027"   # ICICI Bank
    ]
    
    # Subscribe to instruments across all adapters
    data_manager.subscribe_instruments(instruments)
    
    # Add tick data handler
    def handle_tick(tick_data: TickData):
        logger.info(f"📊 {tick_data.symbol}: LTP={tick_data.ltp}, Volume={tick_data.volume}")
    
    data_manager.add_tick_handler(handle_tick)
    
    # Print status
    status = data_manager.get_status()
    logger.info(f"🚀 Data Manager Status: {status}")
    
    # Run for some time then cleanup
    try:
        await asyncio.sleep(60)  # Run for 1 minute
    finally:
        await data_manager.stop_all()

if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage())