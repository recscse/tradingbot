# 📊 Real-Time Data Hub - End-to-End Implementation Guide

## Complete Data Flow Journey: From WebSocket to UI

### 🔄 Phase-by-Phase Data Transformation

---

## Phase 1: Data Source Ingestion

### WebSocket Connections Setup
```python
# services/centralized_ws_manager.py
class CentralizedWebSocketManager:
    def __init__(self):
        self.hft_system = get_hft_system()
        self.upstox_client = UpstoxWSClient()
        self.angel_client = AngelOneWSClient()
        
    async def start_all_feeds(self):
        """Start all broker WebSocket connections"""
        await asyncio.gather(
            self._start_upstox_feed(),
            self._start_angel_feed(),
            self._start_dhan_feed()
        )
```

### Live Data Reception
```python
async def _process_upstox_feed(self, message: dict):
    """Process incoming Upstox WebSocket data"""
    try:
        # Raw data from Upstox WebSocket
        raw_feed = {
            "type": "live_feed",
            "feeds": {
                "NSE_EQ|INE318A01026": {
                    "fullFeed": {
                        "marketFF": {
                            "ltpc": {"ltp": 3097.7, "ltt": "1757308567467"},
                            "marketOHLC": {"ohlc": [...]}
                        }
                    }
                }
            }
        }
        
        # Extract instrument keys and process each feed
        for instrument_key, feed_data in raw_feed.get("feeds", {}).items():
            await self._hft_kafka_stream(instrument_key, raw_feed)
            
    except Exception as e:
        logger.error(f"Upstox feed processing error: {e}")
```

---

## Phase 2: Kafka Topic Publishing

### Raw Data Standardization
```python
async def _hft_kafka_stream(self, instrument_key: str, live_feed_data: dict):
    """Standardize and publish to hft.raw.market_data"""
    
    # Step 1: Create standardized message
    kafka_message = {
        "instrument_key": instrument_key,
        "timestamp": int(time.time() * 1000),
        "source": "centralized_ws_manager",
        "broker": "upstox",  # or "angel_one", "dhan"
        "message_id": str(uuid.uuid4()),
        "data": live_feed_data,
        "processing_stage": "raw_ingestion"
    }
    
    # Step 2: Validate message format
    if not self._validate_kafka_message(kafka_message):
        logger.warning(f"Invalid message format for {instrument_key}")
        return
    
    # Step 3: Publish to Kafka
    try:
        await self.hft_system.publish_to_topic(
            "hft.raw.market_data",
            kafka_message
        )
        logger.debug(f"Published raw data for {instrument_key}")
        
    except Exception as e:
        logger.error(f"Kafka publishing failed for {instrument_key}: {e}")
        # Fallback to direct service notification
        await self._fallback_direct_notification(instrument_key, live_feed_data)
```

---

## Phase 3: Memory Bridge Processing

### Consumer Setup and Data Enrichment
```python
# services/hft/memory_bridge.py
class HFTMemoryBridge:
    def __init__(self):
        self.consumer = None
        self.producer = None
        self.technical_calculator = TechnicalIndicatorCalculator()
        
    async def start_consuming(self):
        """Start consuming from hft.raw.market_data"""
        self.consumer = AIOKafkaConsumer(
            "hft.raw.market_data",
            bootstrap_servers=self.config.bootstrap_servers,
            group_id="hft_memory_bridge",
            auto_offset_reset="latest"
        )
        
        await self.consumer.start()
        logger.info("Memory Bridge consumer started")
        
        try:
            async for message in self.consumer:
                await self._process_raw_message(message)
        finally:
            await self.consumer.stop()

    async def _process_raw_message(self, kafka_message):
        """Process raw Kafka message and enrich data"""
        try:
            # Step 1: Parse raw message
            raw_data = json.loads(kafka_message.value.decode('utf-8'))
            instrument_key = raw_data["instrument_key"]
            
            # Step 2: Extract market data from broker format
            market_data = await self._extract_market_data(raw_data)
            
            # Step 3: Calculate technical indicators
            technical_data = await self._calculate_technicals(market_data)
            
            # Step 4: Create enriched message
            enriched_message = {
                "instrument_key": instrument_key,
                "timestamp": int(time.time() * 1000),
                "source": "memory_bridge",
                "original_timestamp": raw_data["timestamp"],
                "processing_latency_ms": int(time.time() * 1000) - raw_data["timestamp"],
                "processed_data": market_data,
                "technical_indicators": technical_data,
                "processing_stage": "enriched_memory",
                "correlation_id": raw_data.get("message_id")
            }
            
            # Step 5: Publish to shared memory feed
            await self._publish_to_shared_feed(enriched_message)
            
        except Exception as e:
            logger.error(f"Memory bridge processing error: {e}")

    async def _extract_market_data(self, raw_data: dict) -> dict:
        """Extract standardized market data from broker-specific format"""
        instrument_key = raw_data["instrument_key"]
        broker_data = raw_data["data"]
        
        # Handle different broker formats
        if raw_data.get("broker") == "upstox":
            return await self._extract_upstox_data(instrument_key, broker_data)
        elif raw_data.get("broker") == "angel_one":
            return await self._extract_angel_data(instrument_key, broker_data)
        else:
            return await self._extract_generic_data(instrument_key, broker_data)

    async def _extract_upstox_data(self, instrument_key: str, broker_data: dict) -> dict:
        """Extract Upstox-specific market data"""
        try:
            feeds = broker_data.get("feeds", {})
            feed_data = feeds.get(instrument_key, {}).get("fullFeed", {})
            
            if "marketFF" in feed_data:
                market_ff = feed_data["marketFF"]
                ltpc = market_ff.get("ltpc", {})
                ohlc_data = market_ff.get("marketOHLC", {}).get("ohlc", [])
                bid_ask = market_ff.get("marketLevel", {}).get("bidAskQuote", [])
                
                # Extract OHLC for different intervals
                daily_ohlc = next((o for o in ohlc_data if o.get("interval") == "1d"), {})
                minute_ohlc = next((o for o in ohlc_data if o.get("interval") == "I1"), {})
                
                # Get best bid/ask
                best_bid_ask = bid_ask[0] if bid_ask else {}
                
                return {
                    "symbol": await self._resolve_symbol(instrument_key),
                    "exchange": instrument_key.split("|")[0] if "|" in instrument_key else "NSE",
                    "ltp": float(ltpc.get("ltp", 0)),
                    "change": float(ltpc.get("ltp", 0)) - float(ltpc.get("cp", 0)),
                    "change_percent": ((float(ltpc.get("ltp", 0)) - float(ltpc.get("cp", 0))) / float(ltpc.get("cp", 1))) * 100,
                    "volume": int(market_ff.get("vtt", "0")),
                    "high": float(daily_ohlc.get("high", 0)),
                    "low": float(daily_ohlc.get("low", 0)),
                    "open": float(daily_ohlc.get("open", 0)),
                    "previous_close": float(ltpc.get("cp", 0)),
                    "bid_price": float(best_bid_ask.get("bidP", 0)),
                    "ask_price": float(best_bid_ask.get("askP", 0)),
                    "bid_quantity": int(best_bid_ask.get("bidQ", "0")),
                    "ask_quantity": int(best_bid_ask.get("askQ", "0")),
                    "atp": float(market_ff.get("atp", 0)),
                    "total_buy_qty": float(market_ff.get("tbq", 0)),
                    "total_sell_qty": float(market_ff.get("tsq", 0)),
                    "last_trade_time": int(ltpc.get("ltt", "0")),
                    "last_trade_quantity": int(ltpc.get("ltq", "0"))
                }
                
            else:
                logger.warning(f"No marketFF data for {instrument_key}")
                return {}
                
        except Exception as e:
            logger.error(f"Upstox data extraction error for {instrument_key}: {e}")
            return {}

    async def _calculate_technicals(self, market_data: dict) -> dict:
        """Calculate technical indicators for enriched data"""
        symbol = market_data.get("symbol")
        if not symbol:
            return {}
        
        try:
            # Get historical data for calculations
            price_history = await self._get_price_history(symbol, periods=50)
            current_price = market_data.get("ltp", 0)
            
            # Calculate indicators
            sma_20 = self.technical_calculator.sma(price_history, 20)
            ema_12 = self.technical_calculator.ema(price_history, 12)
            rsi = self.technical_calculator.rsi(price_history, 14)
            macd = self.technical_calculator.macd(price_history)
            bollinger = self.technical_calculator.bollinger_bands(price_history, 20)
            
            return {
                "sma_20": round(sma_20, 2) if sma_20 else 0,
                "ema_12": round(ema_12, 2) if ema_12 else 0,
                "rsi": round(rsi, 2) if rsi else 0,
                "macd": round(macd, 2) if macd else 0,
                "bollinger_upper": round(bollinger.get("upper", 0), 2),
                "bollinger_lower": round(bollinger.get("lower", 0), 2),
                "bollinger_middle": round(bollinger.get("middle", 0), 2)
            }
            
        except Exception as e:
            logger.error(f"Technical calculation error for {symbol}: {e}")
            return {}

    async def _publish_to_shared_feed(self, enriched_message: dict):
        """Publish enriched data to hft.shared_memory.feed"""
        try:
            await self.hft_system.publish_to_topic(
                "hft.shared_memory.feed",
                enriched_message
            )
            
            # Update in-memory registry for immediate access
            await self._update_memory_registry(enriched_message)
            
        except Exception as e:
            logger.error(f"Shared feed publishing error: {e}")
```

---

## Phase 4: Service Distribution

### Service Consumer Registration
```python
# services/hft/core.py - Service Registration
class HFTKafkaCore:
    def __init__(self):
        self.service_consumers = {}
        self.consumer_tasks = {}
        
    async def register_service_consumer(self, service_name: str, topics: List[str], handler):
        """Register a service to consume from specific topics"""
        consumer_config = {
            "service_name": service_name,
            "topics": topics,
            "group_id": f"{service_name}_group",
            "handler": handler
        }
        
        self.service_consumers[service_name] = consumer_config
        logger.info(f"Registered service consumer: {service_name} for topics: {topics}")

    async def start_all_consumers(self):
        """Start all registered service consumers"""
        for service_name, config in self.service_consumers.items():
            task = asyncio.create_task(
                self._start_service_consumer(service_name, config)
            )
            self.consumer_tasks[service_name] = task
        
        logger.info(f"Started {len(self.service_consumers)} service consumers")

    async def _start_service_consumer(self, service_name: str, config: dict):
        """Start individual service consumer"""
        consumer = AIOKafkaConsumer(
            *config["topics"],
            bootstrap_servers=self.config.bootstrap_servers,
            group_id=config["group_id"],
            **self.consumer_config
        )
        
        await consumer.start()
        logger.info(f"Service consumer started: {service_name}")
        
        try:
            async for message in consumer:
                await self._handle_service_message(service_name, config, message)
        finally:
            await consumer.stop()
            logger.info(f"Service consumer stopped: {service_name}")

    async def _handle_service_message(self, service_name: str, config: dict, message):
        """Handle message for specific service"""
        try:
            # Parse message
            data = json.loads(message.value.decode('utf-8'))
            
            # Add metadata
            service_context = {
                "service_name": service_name,
                "topic": message.topic,
                "partition": message.partition,
                "offset": message.offset,
                "timestamp": message.timestamp,
                "processing_time": time.time()
            }
            
            # Call service handler
            await config["handler"](data, service_context)
            
        except Exception as e:
            logger.error(f"Service {service_name} message handling error: {e}")
```

### Instrument Registry Consumer
```python
# services/instrument_registry.py - Enhanced for Kafka
class InstrumentRegistry:
    async def initialize_kafka_consumer(self):
        """Initialize as Kafka consumer"""
        hft_system = get_hft_system()
        await hft_system.register_service_consumer(
            "instrument_registry",
            ["hft.shared_memory.feed"],
            self.process_shared_memory_update
        )

    async def process_shared_memory_update(self, data: dict, context: dict):
        """Process shared memory feed updates"""
        try:
            instrument_key = data["instrument_key"]
            processed_data = data["processed_data"]
            technical_indicators = data.get("technical_indicators", {})
            
            # Update in-memory price tracking
            await self._update_live_price(instrument_key, processed_data)
            
            # Update technical indicators
            await self._update_technical_data(instrument_key, technical_indicators)
            
            # Check for alerts and notifications
            await self._check_price_alerts(instrument_key, processed_data)
            
            # Broadcast to UI clients if needed
            await self._notify_ui_clients(instrument_key, processed_data)
            
        except Exception as e:
            logger.error(f"Instrument registry processing error: {e}")

    async def _update_live_price(self, instrument_key: str, market_data: dict):
        """Update live price data with high performance"""
        symbol = market_data.get("symbol")
        if not symbol:
            return
        
        # Update in-memory cache
        price_update = {
            "symbol": symbol,
            "ltp": market_data["ltp"],
            "change": market_data["change"],
            "change_percent": market_data["change_percent"],
            "volume": market_data["volume"],
            "timestamp": int(time.time() * 1000),
            "instrument_key": instrument_key
        }
        
        # Store in Redis with TTL
        await self.redis_client.setex(
            f"live_price:{symbol}",
            300,  # 5 minute TTL
            json.dumps(price_update)
        )
        
        # Update local memory cache
        self.live_prices[symbol] = price_update
```

### Breakout Engine Consumer
```python
# services/enhanced_breakout_engine.py - Kafka Integration
class EnhancedBreakoutEngine:
    async def initialize_kafka_consumer(self):
        """Initialize as Kafka consumer"""
        hft_system = get_hft_system()
        await hft_system.register_service_consumer(
            "breakout_engine",
            ["hft.shared_memory.feed"],
            self.process_market_update
        )

    async def process_market_update(self, data: dict, context: dict):
        """Process market updates for breakout detection"""
        try:
            instrument_key = data["instrument_key"]
            processed_data = data["processed_data"]
            technical_data = data.get("technical_indicators", {})
            
            # Check for breakout patterns
            breakout_signals = await self._detect_breakout_patterns(
                instrument_key, 
                processed_data, 
                technical_data
            )
            
            # Process each signal
            for signal in breakout_signals:
                await self._process_breakout_signal(signal)
                
        except Exception as e:
            logger.error(f"Breakout engine processing error: {e}")

    async def _detect_breakout_patterns(self, instrument_key: str, market_data: dict, technical_data: dict) -> List[dict]:
        """Detect various breakout patterns"""
        signals = []
        symbol = market_data.get("symbol")
        current_price = market_data.get("ltp", 0)
        
        if not symbol or not current_price:
            return signals
        
        try:
            # Get historical data for pattern analysis
            price_history = await self._get_price_history(symbol)
            
            # Resistance/Support Breakout
            resistance_level = await self._calculate_resistance(price_history)
            support_level = await self._calculate_support(price_history)
            
            if current_price > resistance_level * 1.005:  # 0.5% breakout threshold
                signals.append({
                    "type": "RESISTANCE_BREAKOUT",
                    "symbol": symbol,
                    "price": current_price,
                    "level": resistance_level,
                    "strength": self._calculate_breakout_strength(current_price, resistance_level),
                    "timestamp": int(time.time() * 1000)
                })
            
            if current_price < support_level * 0.995:  # 0.5% breakdown threshold
                signals.append({
                    "type": "SUPPORT_BREAKDOWN",
                    "symbol": symbol,
                    "price": current_price,
                    "level": support_level,
                    "strength": self._calculate_breakout_strength(current_price, support_level),
                    "timestamp": int(time.time() * 1000)
                })
            
            # Volume Breakout
            avg_volume = await self._calculate_average_volume(symbol)
            current_volume = market_data.get("volume", 0)
            
            if current_volume > avg_volume * 2:  # 2x average volume
                signals.append({
                    "type": "VOLUME_BREAKOUT",
                    "symbol": symbol,
                    "volume": current_volume,
                    "avg_volume": avg_volume,
                    "volume_ratio": current_volume / avg_volume,
                    "timestamp": int(time.time() * 1000)
                })
            
            return signals
            
        except Exception as e:
            logger.error(f"Breakout detection error for {symbol}: {e}")
            return []

    async def _process_breakout_signal(self, signal: dict):
        """Process and publish breakout signal"""
        try:
            # Validate signal strength
            if signal.get("strength", 0) < 0.5:  # Minimum strength threshold
                return
            
            # Create signal message
            signal_message = {
                "signal_id": str(uuid.uuid4()),
                "timestamp": int(time.time() * 1000),
                "source": "enhanced_breakout_engine",
                "signal": signal,
                "processing_stage": "strategy_signal"
            }
            
            # Publish to strategy topic
            await self.hft_system.publish_to_topic(
                "hft.strategy.breakout",
                signal_message
            )
            
            # Send immediate notification for strong signals
            if signal.get("strength", 0) > 0.8:
                await self._send_immediate_notification(signal)
                
        except Exception as e:
            logger.error(f"Breakout signal processing error: {e}")
```

---

## Phase 5: UI Data Broadcasting

### Unified WebSocket Manager Integration
```python
# services/unified_websocket_manager.py - Kafka Integration
class UnifiedWebSocketManager:
    def __init__(self):
        self.connected_clients = set()
        self.client_subscriptions = {}
        self.hft_system = None
        
    async def initialize_kafka_consumers(self):
        """Initialize Kafka consumers for UI broadcasting"""
        self.hft_system = get_hft_system()
        
        # Register multiple consumers for different data types
        await self.hft_system.register_service_consumer(
            "ui_price_updates",
            ["hft.shared_memory.feed"],
            self.process_price_updates
        )
        
        await self.hft_system.register_service_consumer(
            "ui_strategy_signals",
            ["hft.strategy.breakout", "hft.strategy.momentum"],
            self.process_strategy_signals
        )
        
        await self.hft_system.register_service_consumer(
            "ui_analytics",
            ["hft.analytics.market_data"],
            self.process_analytics_updates
        )

    async def process_price_updates(self, data: dict, context: dict):
        """Process price updates for UI broadcasting"""
        try:
            processed_data = data["processed_data"]
            symbol = processed_data.get("symbol")
            
            if not symbol:
                return
            
            # Create UI-friendly price update
            price_update = {
                "type": "PRICE_UPDATE",
                "symbol": symbol,
                "data": {
                    "ltp": processed_data["ltp"],
                    "change": processed_data["change"],
                    "change_percent": round(processed_data["change_percent"], 2),
                    "volume": processed_data["volume"],
                    "high": processed_data["high"],
                    "low": processed_data["low"],
                    "bid": processed_data["bid_price"],
                    "ask": processed_data["ask_price"]
                },
                "timestamp": int(time.time() * 1000)
            }
            
            # Broadcast to subscribed clients
            await self._broadcast_to_subscribers(f"price:{symbol}", price_update)
            
        except Exception as e:
            logger.error(f"UI price update processing error: {e}")

    async def process_strategy_signals(self, data: dict, context: dict):
        """Process strategy signals for UI broadcasting"""
        try:
            signal = data["signal"]
            
            # Create UI-friendly signal update
            strategy_update = {
                "type": "STRATEGY_SIGNAL",
                "strategy": context["topic"].split(".")[-1],  # Extract strategy name
                "data": signal,
                "timestamp": int(time.time() * 1000)
            }
            
            # Broadcast to strategy subscribers
            await self._broadcast_to_subscribers("strategies", strategy_update)
            
        except Exception as e:
            logger.error(f"UI strategy signal processing error: {e}")

    async def _broadcast_to_subscribers(self, channel: str, message: dict):
        """Broadcast message to subscribed clients"""
        if not self.connected_clients:
            return
        
        # Find clients subscribed to this channel
        subscribed_clients = []
        for client_id, subscriptions in self.client_subscriptions.items():
            if channel in subscriptions:
                subscribed_clients.append(client_id)
        
        if not subscribed_clients:
            return
        
        # Broadcast message
        broadcast_tasks = []
        for client_id in subscribed_clients:
            if client_id in self.connected_clients:
                task = self._send_to_client(client_id, message)
                broadcast_tasks.append(task)
        
        if broadcast_tasks:
            await asyncio.gather(*broadcast_tasks, return_exceptions=True)

    async def _send_to_client(self, client_id: str, message: dict):
        """Send message to specific client"""
        try:
            websocket = self._get_client_websocket(client_id)
            if websocket:
                await websocket.send(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to send message to client {client_id}: {e}")
            # Remove disconnected client
            self.connected_clients.discard(client_id)
```

---

## Complete End-to-End Flow Summary

### Data Journey Timeline
```
1. WebSocket Message Received (t=0ms)
   ↓
2. Raw Data Validation & Standardization (t=0.1ms)
   ↓
3. Kafka Topic Publishing - hft.raw.market_data (t=0.5ms)
   ↓
4. Memory Bridge Consumer Processing (t=1ms)
   ↓ 
5. Technical Indicator Calculations (t=2ms)
   ↓
6. Shared Memory Feed Publishing - hft.shared_memory.feed (t=3ms)
   ↓
7. Service Consumers Processing (t=4ms)
   │
   ├─ Instrument Registry Updates
   ├─ Breakout Engine Analysis  
   ├─ Analytics Engine Processing
   └─ Premarket Candle Building
   ↓
8. Strategy Signal Generation (t=5ms)
   ↓
9. UI WebSocket Broadcasting (t=6ms)
   ↓
10. Frontend React Component Updates (t=7ms)
```

### Performance Targets
- **Total Latency**: < 10ms end-to-end
- **Throughput**: 100,000 messages/second
- **Availability**: 99.99% uptime
- **Data Accuracy**: 100% message integrity

### Key Features
- **Zero Data Loss**: Kafka persistence ensures no message loss
- **Horizontal Scaling**: Add consumers for increased throughput
- **Fault Tolerance**: Automatic failover and recovery
- **Real-time Processing**: Sub-10ms latency targets
- **Rich Analytics**: Technical indicators and strategy signals