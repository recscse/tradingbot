# services/breakout/scanner_service.py
"""
Modular BreakoutScannerService - Integrated with Live Data Sources

This service provides real-time breakout detection using modular data adapters
to connect with multiple live data sources in the trading system.

Key Features:
- Modular data source integration (Market Data Hub, WebSocket Manager, etc.)
- Multiple breakout strategies (ORB, Donchian, Pivots, CPR, Yesterday levels)
- Multi-layer confirmation filters (Volume, Momentum, EMA)
- Real-time signal broadcasting (WebSocket + Redis)
- Production-grade performance and error handling

Integration Points:
- Market Data Hub (NumPy/Pandas high-performance processing)
- Centralized WebSocket Manager (Live broker feeds)
- Instrument Registry (Metadata and cached price data)
- Redis Pub/Sub (Distributed data sharing)
- Unified WebSocket Manager (UI broadcasting)
"""

import asyncio
import logging
import json
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta, time
from typing import Dict, List, Any, Optional, Deque, Tuple
from decimal import Decimal, ROUND_HALF_UP

import pandas as pd
import numpy as np
from pandas import DataFrame

from .data_adapters import (
    TickData,
    MultiSourceDataManager,
    MarketDataHubAdapter,
    CentralizedWebSocketAdapter,
    InstrumentRegistryAdapter,
    RedisStreamAdapter,
    create_multi_source_manager
)

# Indian timezone
from zoneinfo import ZoneInfo
IST = ZoneInfo("Asia/Kolkata")

logger = logging.getLogger(__name__)


@dataclass
class BreakoutSignal:
    """
    Structured breakout signal with complete trading information
    
    Attributes:
        symbol: Trading symbol (e.g., "RELIANCE")
        strategy: Breakout strategy type ("ORB15", "Donchian", "PivotBreakout", etc.)
        signal: Trading direction ("BUY" or "SELL")
        breakout_level: Price level that was broken
        entry_price: Recommended entry price
        stop_loss: Stop loss price
        target: Target price
        volume: Current volume at breakout
        timestamp: ISO 8601 timestamp string with timezone
        confidence_score: Confidence level (0.0 to 1.0)
        data_source: Which data source generated this signal
    """
    symbol: str
    strategy: str
    signal: str  # "BUY" or "SELL"
    breakout_level: float
    entry_price: float
    stop_loss: float
    target: float
    volume: int
    timestamp: str  # ISO 8601 string
    confidence_score: float = 1.0
    data_source: str = "unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), default=str)


class TickStore:
    """
    High-performance tick storage with rolling buffers
    
    Optimized for real-time breakout detection with memory efficiency
    """
    
    def __init__(self, max_ticks: int = 5000):
        """Initialize tick storage with configurable buffer size"""
        self._ticks: Dict[str, Deque[Dict[str, Any]]] = defaultdict(
            lambda: deque(maxlen=max_ticks)
        )
        self._last_prices: Dict[str, float] = {}
        self._last_update: Dict[str, datetime] = {}
        self._tick_counts: Dict[str, int] = defaultdict(int)
        
        logger.info(f"✅ TickStore initialized with max_ticks={max_ticks}")
    
    def add_tick_data(self, tick_data: TickData) -> None:
        """
        Add TickData object to storage
        
        Args:
            tick_data: TickData object with standardized format
            
        Raises:
            ValueError: If tick data is invalid
        """
        if tick_data.ltp <= 0:
            raise ValueError(f"Invalid LTP for {tick_data.instrument_key}: {tick_data.ltp}")
        
        try:
            # Convert timestamp if needed
            if tick_data.timestamp:
                tick_time = tick_data.timestamp
            else:
                tick_time = datetime.fromtimestamp(tick_data.ltt / 1000.0, tz=IST)
        except (ValueError, OSError) as e:
            raise ValueError(f"Invalid timestamp {tick_data.ltt} for {tick_data.instrument_key}: {e}") from e
        
        # Store processed tick data
        processed_tick = {
            "price": Decimal(str(tick_data.ltp)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            "quantity": tick_data.ltq,
            "volume": tick_data.volume,
            "timestamp": tick_time,
            "unix_time": tick_data.ltt,
            "open": tick_data.open_price,
            "high": tick_data.high,
            "low": tick_data.low,
            "prev_close": tick_data.prev_close,
            "change": tick_data.change,
            "change_percent": tick_data.change_percent
        }
        
        self._ticks[tick_data.instrument_key].append(processed_tick)
        self._last_prices[tick_data.instrument_key] = float(processed_tick["price"])
        self._last_update[tick_data.instrument_key] = tick_time
        self._tick_counts[tick_data.instrument_key] += 1
    
    def get_recent_ticks(self, instrument_key: str, count: int = 100) -> List[Dict[str, Any]]:
        """Get recent ticks for an instrument"""
        if instrument_key not in self._ticks:
            return []
        
        ticks = list(self._ticks[instrument_key])
        return ticks[-count:] if count < len(ticks) else ticks
    
    def get_tick_count(self, instrument_key: str) -> int:
        """Get total tick count for instrument"""
        return self._tick_counts.get(instrument_key, 0)
    
    def get_last_price(self, instrument_key: str) -> Optional[float]:
        """Get last traded price for instrument"""
        return self._last_prices.get(instrument_key)
    
    def get_instruments(self) -> List[str]:
        """Get list of all instruments with tick data"""
        return list(self._ticks.keys())


class CandleBuilder:
    """
    OHLC candle aggregation using Pandas resample functionality
    
    Builds 1-minute and 5-minute candles from tick data for
    technical analysis and breakout detection.
    """
    
    def __init__(self):
        """Initialize candle builder with DataFrame storage"""
        self._candles: Dict[str, Dict[str, DataFrame]] = defaultdict(
            lambda: {"1min": DataFrame(), "5min": DataFrame()}
        )
        self._last_candle_time: Dict[str, Dict[str, datetime]] = defaultdict(dict)
        
        logger.info("✅ CandleBuilder initialized with 1m and 5m timeframes")
    
    def build_candles(self, instrument_key: str, ticks: List[Dict[str, Any]]) -> Dict[str, DataFrame]:
        """
        Build OHLC candles from tick data using Pandas resample
        
        Args:
            instrument_key: Instrument identifier
            ticks: List of tick data with timestamp and price
            
        Returns:
            Dictionary with "1min" and "5min" DataFrame candles
            
        Raises:
            ValueError: If ticks data is invalid
        """
        if not ticks:
            return self._candles[instrument_key]
        
        try:
            # Convert ticks to DataFrame
            df_data = []
            for tick in ticks:
                df_data.append({
                    "timestamp": tick["timestamp"],
                    "price": float(tick["price"]),
                    "quantity": tick["quantity"],
                    "volume": tick.get("volume", tick["quantity"])
                })
            
            if not df_data:
                return self._candles[instrument_key]
            
            df = DataFrame(df_data)
            df.set_index("timestamp", inplace=True)
            df.index = pd.to_datetime(df.index)
            
            # Build candles for both timeframes
            timeframes = {"1min": "1min", "5min": "5min"}
            
            for tf_key, tf_name in timeframes.items():
                try:
                    # Resample to OHLC
                    ohlc = df["price"].resample(tf_key).agg({
                        "open": "first",
                        "high": "max", 
                        "low": "min",
                        "close": "last"
                    }).dropna()
                    
                    # Add volume (sum of quantities and volumes)
                    volume_qty = df["quantity"].resample(tf_key).sum()
                    volume_vol = df["volume"].resample(tf_key).sum()
                    
                    # Use the larger of quantity sum or volume sum
                    volume = pd.concat([volume_qty, volume_vol], axis=1).max(axis=1)
                    
                    # Combine OHLC and volume
                    candles_df = pd.concat([ohlc, volume.rename("volume")], axis=1)
                    candles_df.dropna(inplace=True)
                    
                    if not candles_df.empty:
                        # Update stored candles (keep last 200 candles for memory efficiency)
                        self._candles[instrument_key][tf_key] = candles_df.tail(200).copy()
                        self._last_candle_time[instrument_key][tf_key] = candles_df.index[-1].to_pydatetime()
                        
                        logger.debug(f"📊 Built {len(candles_df)} {tf_name} candles for {instrument_key}")
                
                except Exception as e:
                    logger.error(f"❌ Error building {tf_name} candles for {instrument_key}: {e}")
                    continue
            
            return self._candles[instrument_key]
            
        except Exception as e:
            logger.error(f"❌ Error in build_candles for {instrument_key}: {e}")
            raise ValueError(f"Failed to build candles for {instrument_key}: {e}") from e
    
    def get_candles(self, instrument_key: str, timeframe: str = "1min") -> DataFrame:
        """Get recent candles for instrument and timeframe"""
        if timeframe not in ["1min", "5min"]:
            raise ValueError(f"Invalid timeframe: {timeframe}. Use '1min' or '5min'")
        
        return self._candles[instrument_key][timeframe].copy()
    
    def has_sufficient_data(self, instrument_key: str, timeframe: str = "1min", min_candles: int = 20) -> bool:
        """Check if instrument has sufficient candle data for analysis"""
        candles = self.get_candles(instrument_key, timeframe)
        return len(candles) >= min_candles


# Import the level calculation and strategy classes from the original implementation
# (BreakoutStrategies, ConfirmationFilters, LevelCalculator remain the same)


class BreakoutScannerService:
    """
    Modular BreakoutScannerService with integrated data source adapters
    
    This service coordinates:
    - Multiple data source adapters for live feed integration
    - Tick storage and OHLC candle building
    - Support/resistance level calculations
    - Breakout strategy detection with confirmation filters
    - Real-time signal broadcasting
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize breakout scanner service with configuration
        
        Args:
            config: Configuration dictionary for adapters and settings
        """
        self.config = config or {}
        
        # Core components
        self.tick_store = TickStore(max_ticks=self.config.get('max_ticks', 5000))
        self.candle_builder = CandleBuilder()
        
        # TODO: Move these classes to modular system to remove legacy dependency
        # For now, importing from legacy file until we extract these components
        try:
            from ..breakout_scanner_service import LevelCalculator, BreakoutStrategies, ConfirmationFilters
            self.level_calculator = LevelCalculator()
            self.breakout_strategies = BreakoutStrategies()
            self.confirmation_filters = ConfirmationFilters()
            logger.info("✅ Imported legacy breakout components (temporary)")
        except ImportError as e:
            logger.error(f"❌ Failed to import legacy breakout components: {e}")
            # Fallback to basic implementations
            self.level_calculator = None
            self.breakout_strategies = None
            self.confirmation_filters = None
        
        # Data source management
        self.data_manager = MultiSourceDataManager()
        self._setup_data_adapters()
        
        # Signal tracking
        self._recent_signals: Dict[str, List[BreakoutSignal]] = defaultdict(list)
        self._signal_cooldown: Dict[str, datetime] = {}
        self._processing_stats = {
            "ticks_processed": 0,
            "signals_generated": 0,
            "last_update": None,
            "data_sources": {}
        }
        
        # Performance tracking
        self._performance_metrics = {
            "avg_processing_time": 0.0,
            "max_processing_time": 0.0,
            "error_count": 0,
            "success_count": 0
        }
        
        # External integrations (WebSocket, Redis)
        self.websocket_manager = None
        self.redis_client = None
        self._setup_external_integrations()
        
        # Service state
        self.is_running = False
        self.subscribed_instruments: List[str] = []
        
        logger.info("🚀 Modular BreakoutScannerService initialized successfully")
    
    def _setup_data_adapters(self) -> None:
        """Setup and configure data source adapters based on config"""
        try:
            # Configure adapter settings based on config
            enable_market_hub = self.config.get('enable_market_hub', True)
            enable_centralized_ws = self.config.get('enable_centralized_ws', True)
            enable_registry = self.config.get('enable_registry', True) 
            enable_redis_stream = self.config.get('enable_redis_stream', False)
            redis_url = self.config.get('redis_url', 'redis://localhost:6379')
            
            # Log configuration
            logger.info(f"📊 Data adapter configuration: Hub={enable_market_hub}, WS={enable_centralized_ws}, "
                       f"Registry={enable_registry}, Redis={enable_redis_stream}")
            
            # Create specific adapters based on configuration
            if enable_market_hub:
                hub_adapter = MarketDataHubAdapter()
                self.data_manager.add_adapter(hub_adapter, is_primary=True)
                logger.info("📊 Added Market Data Hub adapter (primary)")
            
            if enable_centralized_ws:
                ws_adapter = CentralizedWebSocketAdapter()
                self.data_manager.add_adapter(ws_adapter, is_primary=(not enable_market_hub))
                logger.info("📊 Added Centralized WebSocket adapter")
            
            if enable_registry:
                registry_adapter = InstrumentRegistryAdapter()
                self.data_manager.add_adapter(registry_adapter, is_primary=False)
                logger.info("📊 Added Instrument Registry adapter")
            
            if enable_redis_stream:
                redis_adapter = RedisStreamAdapter(redis_url)
                self.data_manager.add_adapter(redis_adapter, is_primary=False)
                logger.info("📊 Added Redis Stream adapter")
            
            # Add tick data handler for processing
            self.data_manager.add_tick_handler(self._handle_tick_data)
            logger.info("✅ Data adapter setup completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Error setting up data adapters: {e}")
            # Don't raise exception - allow service to continue with available adapters
    
    def _setup_external_integrations(self) -> None:
        """Setup external integrations for signal broadcasting"""
        try:
            # WebSocket Manager for UI broadcasting
            try:
                from services.unified_websocket_manager import unified_manager
                self.websocket_manager = unified_manager
                logger.info("✅ Connected to Unified WebSocket Manager")
            except ImportError:
                logger.warning("⚠️ Unified WebSocket Manager not available")
            
            # Redis for pub/sub broadcasting
            if self.config.get('enable_redis_broadcast', True):
                try:
                    import redis.asyncio as redis
                    redis_url = self.config.get('redis_url', 'redis://localhost:6379')
                    self.redis_client = redis.from_url(redis_url, decode_responses=True)
                    logger.info("✅ Connected to Redis for broadcasting")
                except ImportError:
                    logger.warning("⚠️ Redis not available for broadcasting")
            
        except Exception as e:
            logger.error(f"❌ Error setting up external integrations: {e}")
    
    async def initialize(self) -> bool:
        """
        Initialize the breakout scanner service
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            logger.info("🔄 Initializing BreakoutScannerService...")
            
            # Initialize data adapters
            successful_adapters = await self.data_manager.initialize_all()
            
            if not successful_adapters:
                logger.error("❌ No data adapters initialized successfully")
                return False
            
            logger.info(f"✅ Initialized {len(successful_adapters)} data adapters: {successful_adapters}")
            
            # Test Redis connection if enabled
            if self.redis_client:
                try:
                    await self.redis_client.ping()
                    logger.info("✅ Redis connection verified")
                except Exception as e:
                    logger.warning(f"⚠️ Redis connection failed: {e}")
                    self.redis_client = None
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error initializing BreakoutScannerService: {e}")
            return False
    
    async def start(self, instrument_keys: List[str] = None) -> None:
        """
        Start the breakout scanner service
        
        Args:
            instrument_keys: List of instruments to monitor (optional)
        """
        if self.is_running:
            logger.info("🔍 BreakoutScannerService already running")
            return
        
        try:
            logger.info("🚀 Starting BreakoutScannerService...")
            
            # Start data adapters
            await self.data_manager.start_all()
            
            # Subscribe to instruments if provided
            if instrument_keys:
                self.subscribed_instruments = instrument_keys
                self.data_manager.subscribe_instruments(instrument_keys)
                logger.info(f"📊 Subscribed to {len(instrument_keys)} instruments")
            else:
                # Get instruments from registry or use defaults
                try:
                    from services.centralized_ws_manager import get_instrument_keys_safely
                    self.subscribed_instruments = get_instrument_keys_safely()
                    if self.subscribed_instruments:
                        self.data_manager.subscribe_instruments(self.subscribed_instruments)
                        logger.info(f"📊 Auto-subscribed to {len(self.subscribed_instruments)} instruments")
                except Exception as e:
                    logger.warning(f"⚠️ Could not auto-subscribe to instruments: {e}")
            
            self.is_running = True
            logger.info("✅ BreakoutScannerService started successfully")
            
        except Exception as e:
            logger.error(f"❌ Error starting BreakoutScannerService: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the breakout scanner service"""
        if not self.is_running:
            return
        
        try:
            logger.info("🛑 Stopping BreakoutScannerService...")
            
            # Stop data adapters
            await self.data_manager.stop_all()
            
            # Close Redis connection
            if self.redis_client:
                await self.redis_client.close()
            
            self.is_running = False
            logger.info("✅ BreakoutScannerService stopped successfully")
            
        except Exception as e:
            logger.error(f"❌ Error stopping BreakoutScannerService: {e}")
    
    async def _handle_tick_data(self, tick_data: TickData) -> None:
        """
        Handle incoming tick data from data adapters
        
        Args:
            tick_data: Standardized tick data from any data source
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Store tick data
            self.tick_store.add_tick_data(tick_data)
            self._processing_stats["ticks_processed"] += 1
            
            # Track data source statistics
            if tick_data.data_source not in self._processing_stats["data_sources"]:
                self._processing_stats["data_sources"][tick_data.data_source] = 0
            self._processing_stats["data_sources"][tick_data.data_source] += 1
            
            # Process for breakout detection (only if we have enough data)
            if self.tick_store.get_tick_count(tick_data.instrument_key) >= 20:
                signals = await self._process_instrument_for_breakouts(tick_data)
                
                # Broadcast any detected signals
                for signal in signals:
                    await self._broadcast_signal(signal)
            
            # Update performance metrics
            processing_time = (asyncio.get_event_loop().time() - start_time) * 1000  # ms
            self._update_performance_metrics(processing_time, success=True)
            
        except Exception as e:
            logger.error(f"❌ Error handling tick data for {tick_data.instrument_key}: {e}")
            self._update_performance_metrics(0, success=False)
    
    async def _process_instrument_for_breakouts(self, tick_data: TickData) -> List[BreakoutSignal]:
        """
        Process instrument for breakout detection
        
        Args:
            tick_data: Current tick data for the instrument
            
        Returns:
            List of detected breakout signals
        """
        signals = []
        
        try:
            # Check signal cooldown (prevent spam)
            if self._is_in_cooldown(tick_data.instrument_key):
                return signals
            
            # Get recent ticks and build candles
            recent_ticks = self.tick_store.get_recent_ticks(tick_data.instrument_key)
            if not recent_ticks:
                return signals
            
            # Build candles
            candles = self.candle_builder.build_candles(tick_data.instrument_key, recent_ticks)
            
            # Check if we have sufficient candle data
            if not self.candle_builder.has_sufficient_data(tick_data.instrument_key, "1min", min_candles=5):
                return signals
            
            # Get historical data from recent ticks for level calculations
            historical_data = self._extract_historical_data(recent_ticks)
            
            # Calculate all support/resistance levels
            await self._calculate_all_levels(tick_data.instrument_key, candles, historical_data)
            
            # Run breakout detection strategies
            strategies = [
                ("yesterday", self.level_calculator._daily_levels),
                ("orb_15", self.level_calculator._orb_levels),
                ("orb_30", self.level_calculator._orb_levels), 
                ("donchian", self.level_calculator._donchian_levels),
                ("pivot", self.level_calculator._pivot_levels),
                ("cpr", self.level_calculator._cpr_levels)
            ]
            
            for strategy_name, level_source in strategies:
                try:
                    signal = await self._detect_breakout(
                        strategy_name,
                        candles["1min"],
                        level_source.get(tick_data.instrument_key, {}),
                        tick_data.ltp,
                        tick_data.symbol,
                        tick_data.data_source
                    )
                    
                    if signal:
                        signals.append(signal)
                        self._set_signal_cooldown(tick_data.instrument_key)
                        logger.info(f"🚨 {strategy_name} breakout: {tick_data.symbol} {signal.signal} @ {signal.entry_price}")
                
                except Exception as e:
                    logger.error(f"❌ Error in {strategy_name} strategy for {tick_data.symbol}: {e}")
                    continue
            
            # Update stats
            self._processing_stats["signals_generated"] += len(signals)
            self._processing_stats["last_update"] = datetime.now(tz=IST)
            
            return signals
            
        except Exception as e:
            logger.error(f"❌ Error processing breakouts for {tick_data.instrument_key}: {e}")
            return signals
    
    def _extract_historical_data(self, recent_ticks: List[Dict[str, Any]]) -> Dict[str, float]:
        """Extract historical OHLC data from recent ticks for level calculations"""
        if not recent_ticks:
            return {}
        
        try:
            prices = [float(tick["price"]) for tick in recent_ticks]
            
            # Use recent data as proxy for historical data
            return {
                "prev_high": max(prices),
                "prev_low": min(prices),
                "prev_close": float(recent_ticks[-1]["price"]) if recent_ticks else 0.0
            }
        except Exception as e:
            logger.error(f"❌ Error extracting historical data: {e}")
            return {}
    
    async def _calculate_all_levels(
        self,
        instrument_key: str,
        candles: Dict[str, DataFrame],
        historical_data: Dict[str, float]
    ) -> None:
        """Calculate all support/resistance levels for an instrument"""
        try:
            candles_1m = candles["1min"]
            
            # Yesterday levels (using historical data proxy)
            if historical_data and all(k in historical_data for k in ["prev_high", "prev_low", "prev_close"]):
                prev_high = historical_data["prev_high"]
                prev_low = historical_data["prev_low"] 
                prev_close = historical_data["prev_close"]
                
                self.level_calculator.calculate_yesterday_levels(instrument_key, prev_high, prev_low)
                self.level_calculator.calculate_pivot_levels(instrument_key, prev_high, prev_low, prev_close)
                self.level_calculator.calculate_cpr_levels(instrument_key, prev_high, prev_low, prev_close)
            
            # ORB levels (15m and 30m) and Donchian levels
            if not candles_1m.empty:
                self.level_calculator.calculate_orb_levels(instrument_key, candles_1m, orb_minutes=15)
                self.level_calculator.calculate_orb_levels(instrument_key, candles_1m, orb_minutes=30)
                self.level_calculator.calculate_donchian_levels(instrument_key, candles_1m, period=20)
        
        except Exception as e:
            logger.error(f"❌ Error calculating levels for {instrument_key}: {e}")
    
    async def _detect_breakout(
        self,
        strategy_name: str,
        candles: DataFrame,
        levels: Dict[str, float],
        current_price: float,
        symbol: str,
        data_source: str
    ) -> Optional[BreakoutSignal]:
        """Detect breakout using specific strategy"""
        try:
            # Import breakout strategies from original implementation
            from ..breakout_scanner_service import BreakoutStrategies, ConfirmationFilters
            
            # Strategy dispatch
            breakout_data = None
            if strategy_name == "yesterday":
                breakout_data = BreakoutStrategies.yesterday_breakout(candles, levels, current_price)
            elif strategy_name == "orb_15":
                breakout_data = BreakoutStrategies.orb_breakout(candles, levels, current_price, orb_period=15)
            elif strategy_name == "orb_30":
                breakout_data = BreakoutStrategies.orb_breakout(candles, levels, current_price, orb_period=30)
            elif strategy_name == "donchian":
                breakout_data = BreakoutStrategies.donchian_breakout(candles, levels, current_price)
            elif strategy_name == "pivot":
                breakout_data = BreakoutStrategies.pivot_breakout(candles, levels, current_price)
            elif strategy_name == "cpr":
                breakout_data = BreakoutStrategies.cpr_breakout(candles, levels, current_price)
            else:
                return None
            
            if not breakout_data:
                return None
            
            # Apply confirmation filters
            confirmation = ConfirmationFilters.apply_all_filters(
                candles,
                breakout_data["direction"],
                volume_multiplier=2.0,
                momentum_threshold=0.015
            )
            
            # Only proceed if breakout is confirmed
            if not confirmation["overall_confirmed"]:
                return None
            
            # Calculate trade levels (use simplified version for now)
            entry_price = current_price
            stop_loss = breakout_data["level"] * (0.995 if breakout_data["direction"] == "BUY" else 1.005)
            risk = abs(entry_price - stop_loss)
            target = entry_price + (2 * risk) if breakout_data["direction"] == "BUY" else entry_price - (2 * risk)
            
            # Get current volume
            current_volume = int(candles.iloc[-1]["volume"]) if not candles.empty else 0
            
            # Calculate confidence score
            confidence_score = min(1.0, breakout_data.get("strength", 0.5) * 2)
            
            # Create breakout signal
            signal = BreakoutSignal(
                symbol=symbol,
                strategy=breakout_data["strategy"],
                signal=breakout_data["direction"],
                breakout_level=breakout_data["level"],
                entry_price=round(entry_price, 2),
                stop_loss=round(stop_loss, 2),
                target=round(target, 2),
                volume=current_volume,
                timestamp=datetime.now(tz=IST).isoformat(),
                confidence_score=confidence_score,
                data_source=data_source
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"❌ Error detecting breakout ({strategy_name}) for {symbol}: {e}")
            return None
    
    async def _broadcast_signal(self, signal: BreakoutSignal) -> None:
        """Broadcast breakout signal to WebSocket and Redis"""
        try:
            signal_data = signal.to_dict()
            
            # Redis pub/sub broadcasting
            if self.redis_client:
                try:
                    await self.redis_client.publish("breakout_signals", signal.to_json())
                    logger.debug(f"📡 Signal broadcasted to Redis: {signal.symbol}")
                except Exception as e:
                    logger.error(f"❌ Redis broadcast error for {signal.symbol}: {e}")
            
            # WebSocket broadcasting
            if self.websocket_manager:
                try:
                    await self.websocket_manager.emit_event(
                        "breakout_signals_update",  # ✅ FIXED: Correct event type with "_update" suffix
                        {
                            "signals": [signal_data],  # ✅ FIXED: Array format expected by UI
                            "count": 1,
                            "timestamp": signal.timestamp,
                            "source": "modular_breakout_scanner", 
                            "data_source": signal.data_source,
                            "market_hours": True  # Add market hours indicator
                        },
                        priority=1  # High priority for trading signals
                    )
                    logger.debug(f"📡 Signal broadcasted to WebSocket UI: {signal.symbol}")
                except Exception as e:
                    logger.error(f"❌ WebSocket broadcast error for {signal.symbol}: {e}")
        
        except Exception as e:
            logger.error(f"❌ Error broadcasting signal for {signal.symbol}: {e}")
    
    def _is_in_cooldown(self, instrument_key: str, cooldown_minutes: int = 5) -> bool:
        """Check if instrument is in signal cooldown period"""
        if instrument_key not in self._signal_cooldown:
            return False
        
        last_signal_time = self._signal_cooldown[instrument_key]
        cooldown_end = last_signal_time + timedelta(minutes=cooldown_minutes)
        
        return datetime.now(tz=IST) < cooldown_end
    
    def _set_signal_cooldown(self, instrument_key: str) -> None:
        """Set signal cooldown for instrument"""
        self._signal_cooldown[instrument_key] = datetime.now(tz=IST)
    
    def _update_performance_metrics(self, processing_time: float, success: bool) -> None:
        """Update internal performance metrics"""
        if success:
            self._performance_metrics["success_count"] += 1
            
            # Update average processing time
            current_avg = self._performance_metrics["avg_processing_time"]
            success_count = self._performance_metrics["success_count"]
            
            new_avg = ((current_avg * (success_count - 1)) + processing_time) / success_count
            self._performance_metrics["avg_processing_time"] = new_avg
            
            # Update max processing time
            if processing_time > self._performance_metrics["max_processing_time"]:
                self._performance_metrics["max_processing_time"] = processing_time
        else:
            self._performance_metrics["error_count"] += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive service statistics"""
        return {
            "service_status": "running" if self.is_running else "stopped",
            "processing_stats": self._processing_stats.copy(),
            "performance_metrics": self._performance_metrics.copy(),
            "data_adapters": self.data_manager.get_status(),
            "active_instruments": len(self.tick_store.get_instruments()),
            "subscribed_instruments": len(self.subscribed_instruments),
            "signals_in_cooldown": len(self._signal_cooldown),
            "candle_data_available": sum(
                1 for instrument in self.tick_store.get_instruments()
                if self.candle_builder.has_sufficient_data(instrument)
            )
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Comprehensive health check for the breakout scanner service
        
        Returns:
            Health status dictionary with detailed component status
        """
        try:
            health_status = {
                "timestamp": datetime.now(tz=IST).isoformat(),
                "overall_status": "healthy",
                "service_running": self.is_running,
                "components": {}
            }
            
            # Check data adapters
            adapter_status = self.data_manager.get_status()
            health_status["components"]["data_adapters"] = {
                "status": "healthy" if adapter_status["active_adapters"] > 0 else "unhealthy",
                "active_count": adapter_status["active_adapters"],
                "total_count": adapter_status["total_adapters"],
                "details": adapter_status["adapter_status"]
            }
            
            # Check tick store
            active_instruments = len(self.tick_store.get_instruments())
            health_status["components"]["tick_store"] = {
                "status": "healthy" if active_instruments > 0 else "warning",
                "active_instruments": active_instruments,
                "total_ticks": sum(self.tick_store.get_tick_count(instrument) 
                                 for instrument in self.tick_store.get_instruments())
            }
            
            # Check candle builder
            instruments_with_data = sum(
                1 for instrument in self.tick_store.get_instruments()
                if self.candle_builder.has_sufficient_data(instrument)
            )
            health_status["components"]["candle_builder"] = {
                "status": "healthy" if instruments_with_data > 0 else "warning",
                "instruments_with_candle_data": instruments_with_data
            }
            
            # Check external integrations
            health_status["components"]["external_integrations"] = {
                "redis_client": "connected" if self.redis_client else "not_configured",
                "websocket_manager": "connected" if self.websocket_manager else "not_configured"
            }
            
            # Check recent processing activity
            last_update = self._processing_stats.get("last_update")
            if last_update and (datetime.now(tz=IST) - last_update).total_seconds() > 60:
                health_status["components"]["processing"] = {
                    "status": "stale",
                    "last_update": last_update.isoformat(),
                    "warning": "No processing activity in the last 60 seconds"
                }
            else:
                health_status["components"]["processing"] = {
                    "status": "active" if last_update else "waiting",
                    "last_update": last_update.isoformat() if last_update else None
                }
            
            # Determine overall status
            component_statuses = []
            for component, details in health_status["components"].items():
                if isinstance(details, dict) and "status" in details:
                    component_statuses.append(details["status"])
            
            if any(status in ["unhealthy", "error"] for status in component_statuses):
                health_status["overall_status"] = "unhealthy"
            elif any(status == "warning" for status in component_statuses):
                health_status["overall_status"] = "degraded"
            
            return health_status
            
        except Exception as e:
            logger.error(f"❌ Error during health check: {e}")
            return {
                "timestamp": datetime.now(tz=IST).isoformat(),
                "overall_status": "error",
                "error": str(e),
                "service_running": self.is_running
            }
    
    async def recover_unhealthy_adapters(self) -> Dict[str, Any]:
        """
        Attempt to recover unhealthy data adapters
        
        Returns:
            Recovery attempt results
        """
        recovery_results = {
            "timestamp": datetime.now(tz=IST).isoformat(),
            "attempts": {},
            "successful_recoveries": 0,
            "failed_recoveries": 0
        }
        
        try:
            # Get current adapter status
            adapter_status = self.data_manager.get_status()
            
            # Attempt to recover inactive adapters
            for adapter_name, is_active in adapter_status["adapter_status"].items():
                if not is_active and adapter_name in self.data_manager.adapters:
                    logger.info(f"🔄 Attempting recovery of {adapter_name} adapter")
                    
                    try:
                        adapter = self.data_manager.adapters[adapter_name]
                        
                        # Reinitialize and restart the adapter
                        if await adapter.initialize():
                            await adapter.start()
                            
                            if adapter.is_active:
                                recovery_results["attempts"][adapter_name] = "success"
                                recovery_results["successful_recoveries"] += 1
                                logger.info(f"✅ Successfully recovered {adapter_name} adapter")
                            else:
                                recovery_results["attempts"][adapter_name] = "failed_to_start"
                                recovery_results["failed_recoveries"] += 1
                        else:
                            recovery_results["attempts"][adapter_name] = "failed_to_initialize"
                            recovery_results["failed_recoveries"] += 1
                            
                    except Exception as e:
                        recovery_results["attempts"][adapter_name] = f"error: {str(e)}"
                        recovery_results["failed_recoveries"] += 1
                        logger.error(f"❌ Recovery failed for {adapter_name}: {e}")
            
            logger.info(f"🔄 Recovery attempt completed: {recovery_results['successful_recoveries']} successful, "
                       f"{recovery_results['failed_recoveries']} failed")
            
        except Exception as e:
            logger.error(f"❌ Error during adapter recovery: {e}")
            recovery_results["error"] = str(e)
        
        return recovery_results


# Global service instance and management functions
_breakout_system: Optional[BreakoutScannerService] = None


async def initialize_breakout_system(config: Dict[str, Any] = None) -> BreakoutScannerService:
    """
    Initialize the global breakout detection system
    
    Args:
        config: Configuration dictionary for the system
        
    Returns:
        Initialized BreakoutScannerService instance
    """
    global _breakout_system
    
    try:
        if _breakout_system is not None:
            logger.info("🔄 BreakoutScannerService already initialized")
            return _breakout_system
        
        # Create and initialize the service
        _breakout_system = BreakoutScannerService(config)
        
        # Initialize the service
        success = await _breakout_system.initialize()
        if not success:
            raise RuntimeError("Failed to initialize BreakoutScannerService")
        
        logger.info("🚀 Global BreakoutScannerService initialized successfully")
        return _breakout_system
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize BreakoutScannerService: {e}")
        _breakout_system = None
        raise


def get_breakout_system() -> Optional[BreakoutScannerService]:
    """Get the global breakout scanner service instance"""
    return _breakout_system


async def start_breakout_system(instrument_keys: List[str] = None) -> None:
    """Start the global breakout detection system"""
    global _breakout_system
    
    if _breakout_system is None:
        raise RuntimeError("BreakoutScannerService not initialized. Call initialize_breakout_system() first.")
    
    await _breakout_system.start(instrument_keys)


async def stop_breakout_system() -> None:
    """Stop the global breakout detection system"""
    global _breakout_system
    
    if _breakout_system is not None:
        await _breakout_system.stop()


async def health_check_breakout_system() -> Dict[str, Any]:
    """Perform health check on the global breakout detection system"""
    global _breakout_system
    
    if _breakout_system is None:
        return {
            "timestamp": datetime.now(tz=IST).isoformat(),
            "overall_status": "not_initialized",
            "error": "BreakoutScannerService not initialized"
        }
    
    return await _breakout_system.health_check()


async def recover_breakout_system() -> Dict[str, Any]:
    """Attempt to recover unhealthy components of the breakout detection system"""
    global _breakout_system
    
    if _breakout_system is None:
        return {
            "timestamp": datetime.now(tz=IST).isoformat(),
            "error": "BreakoutScannerService not initialized",
            "successful_recoveries": 0,
            "failed_recoveries": 1
        }
    
    return await _breakout_system.recover_unhealthy_adapters()


def get_breakout_system_statistics() -> Dict[str, Any]:
    """Get statistics for the global breakout detection system"""
    global _breakout_system
    
    if _breakout_system is None:
        return {
            "service_status": "not_initialized",
            "error": "BreakoutScannerService not initialized"
        }
    
    return _breakout_system.get_statistics()


# Demonstration and testing function
async def demo_modular_breakout_detection() -> None:
    """Demonstration of the modular breakout detection system"""
    logger.info("🧪 Starting modular breakout detection demo...")
    
    try:
        # Initialize with demo configuration
        config = {
            'enable_market_hub': True,
            'enable_centralized_ws': True,
            'enable_registry': True,
            'enable_redis_stream': False,  # Disable for demo
            'enable_redis_broadcast': False,  # Disable for demo
            'max_ticks': 1000
        }
        
        # Initialize the system
        service = await initialize_breakout_system(config)
        
        # Start with demo instruments
        demo_instruments = [
            "NSE_EQ|INE002A01018",  # RELIANCE
            "NSE_EQ|INE467B01029",  # TCS
            "NSE_EQ|INE040A01034"   # HDFC
        ]
        
        await start_breakout_system(demo_instruments)
        
        # Let it run for a few seconds to collect data
        logger.info("📊 Demo running... collecting live data for 30 seconds")
        await asyncio.sleep(30)
        
        # Get statistics
        stats = service.get_statistics()
        logger.info(f"📊 Demo statistics: {stats}")
        
        # Stop the system
        await stop_breakout_system()
        
        logger.info("✅ Modular breakout detection demo completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Demo error: {e}")
        raise