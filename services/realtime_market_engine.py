import bisect
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class EventEmitter:
    """Lightweight event emitter for push-based updates"""

    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = defaultdict(list)
        self._async_listeners: Dict[str, List[Callable]] = defaultdict(list)

    def on(self, event: str, callback: Callable):
        if callable(callback):
            self._listeners[event].append(callback)

    def off(self, event: str, callback: Callable):
        if callback in self._listeners[event]:
            self._listeners[event].remove(callback)

    def emit(self, event: str, data: Any):
        for callback in self._listeners[event]:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in event listener for {event}: {e}")


@dataclass
class Instrument:
    # Required fields (no defaults)
    instrument_key: str
    symbol: str
    name: str
    sector: str
    exchange: str

    # Price fields (with defaults)
    current_price: float = 0.0
    open_price: float = 0.0
    high_price: float = 0.0
    low_price: float = 0.0
    close_price: float = 0.0

    # Volume fields (with defaults)
    volume: int = 0
    avg_volume: int = 0
    total_traded_value: int = 0

    # Calculated fields (with defaults)
    change: float = 0.0
    change_percent: float = 0.0
    volume_ratio: float = 0.0

    # Metadata fields (with defaults)
    market_cap: int = 0
    lot_size: int = 1
    tick_size: float = 0.05
    last_update: float = field(default_factory=time.time)
    last_trade_time: Optional[str] = None
    is_52_week_high: bool = False
    is_52_week_low: bool = False
    unusual_volume: bool = False

    def update_price(
        self,
        new_price: float,
        volume: int = 0,
        timestamp: Optional[str] = None,
        close_price: Optional[float] = None,
        open_price: Optional[float] = None,
        high_price: Optional[float] = None,
        low_price: Optional[float] = None,
    ):
        new_price_decimal = float(new_price)
        if close_price and self.close_price == 0:
            self.close_price = float(close_price)
        if open_price:
            self.open_price = float(open_price)

        if self.current_price == 0:
            self.current_price = new_price_decimal
            if self.open_price == 0:
                self.open_price = new_price_decimal
            self.high_price = new_price_decimal
            self.low_price = new_price_decimal
        else:
            self.current_price = new_price_decimal
            self.high_price = max(self.high_price, new_price_decimal)
            self.low_price = min(self.low_price, new_price_decimal)

        if high_price:
            self.high_price = max(self.high_price, float(high_price))
        if low_price:
            self.low_price = min(self.low_price, float(low_price))

        if volume > 0:
            self.volume = volume
            self.volume_ratio = (
                float(volume) / float(self.avg_volume)
                if self.avg_volume
                else 1.0
            )
            self.unusual_volume = (
                self.volume > self.avg_volume * 2 if self.avg_volume else False
            )

        if self.close_price > 0:
            self.change = self.current_price - self.close_price
            self.change_percent = (self.change / self.close_price) * 100

        self.last_update = time.time()
        if timestamp:
            self.last_trade_time = timestamp

    def get_heatmap_data(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "sector": self.sector,
            "market_cap": self.market_cap,
            "performance": float(self.change_percent),
            "volume_ratio": float(self.volume_ratio),
            "price": float(self.current_price),
            "is_unusual": self.unusual_volume,
            "last_update": self.last_update,
        }


class SortedInstrumentList:
    """Optimized sorted list using bisect and precomputed keys"""

    def __init__(self, key_func, reverse=False):
        self.instruments: List[Instrument] = []
        self.keys: List[float] = []
        self.key_func = key_func
        self.reverse = reverse
        self._instrument_positions: Dict[str, int] = {}

    def update_instrument(self, instrument: Instrument):
        instrument_key = instrument.instrument_key
        key_value = float(self.key_func(instrument))
        if self.reverse:
            key_value = -key_value

        if instrument_key in self._instrument_positions:
            pos = self._instrument_positions[instrument_key]
            self.instruments.pop(pos)
            self.keys.pop(pos)
            for i in range(pos, len(self.instruments)):
                self._instrument_positions[self.instruments[i].instrument_key] = i

        insert_pos = bisect.bisect_left(self.keys, key_value)
        self.instruments.insert(insert_pos, instrument)
        self.keys.insert(insert_pos, key_value)
        self._instrument_positions[instrument_key] = insert_pos
        for i in range(insert_pos + 1, len(self.instruments)):
            self._instrument_positions[self.instruments[i].instrument_key] = i

    def get_top(self, n: int) -> List[Instrument]:
        return self.instruments[:n]

    def get_bottom(self, n: int) -> List[Instrument]:
        return self.instruments[-n:] if n <= len(self.instruments) else self.instruments


@dataclass
class MarketAnalytics:
    top_gainers: List[Dict[str, Any]] = field(default_factory=list)
    top_losers: List[Dict[str, Any]] = field(default_factory=list)
    volume_leaders: List[Dict[str, Any]] = field(default_factory=list)
    total_stocks: int = 0
    advancing_stocks: int = 0
    declining_stocks: int = 0
    unchanged_stocks: int = 0
    advance_decline_ratio: float = 1.0
    sector_performance: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    sector_heatmap: Dict[str, Any] = field(default_factory=dict)
    total_volume: int = 0
    total_traded_value: int = 0
    avg_volume_ratio: float = 1.0
    market_sentiment: str = "neutral"
    sentiment_score: int = 5000
    last_calculation: float = field(default_factory=time.time)
    calculation_latency_ms: float = 0.0
    unusual_volume_stocks: List[Dict[str, Any]] = field(default_factory=list)
    new_52_week_highs: List[Dict[str, Any]] = field(default_factory=list)
    new_52_week_lows: List[Dict[str, Any]] = field(default_factory=list)
    high_volatility_stocks: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "top_movers": {
                "gainers": self.top_gainers,
                "losers": self.top_losers,
                "volume_leaders": self.volume_leaders,
            },
            "market_breadth": {
                "total_stocks": self.total_stocks,
                "advancing": self.advancing_stocks,
                "declining": self.declining_stocks,
                "unchanged": self.unchanged_stocks,
                "advance_decline_ratio": float(self.advance_decline_ratio),
            },
            "sector_analytics": {
                "performance": self.sector_performance,
                "heatmap": self.sector_heatmap,
            },
            "volume_analytics": {
                "total_volume": self.total_volume,
                "avg_volume_ratio": float(self.avg_volume_ratio),
                "unusual_activity": self.unusual_volume_stocks,
            },
            "market_sentiment": {
                "sentiment": self.market_sentiment,
                "score": self.sentiment_score / 100,
            },
            "highlights": {
                "new_highs": self.new_52_week_highs,
                "new_lows": self.new_52_week_lows,
                "high_volatility": self.high_volatility_stocks,
            },
            "metadata": {
                "last_calculation": self.last_calculation,
                "calculation_latency_ms": self.calculation_latency_ms,
                "timestamp": datetime.now().isoformat(),
            },
        }


class RealtimeMarketEngine:
    """Real-Time Market Analytics Engine"""

    def __init__(self):
        self.instruments: Dict[str, Instrument] = {}
        self.sector_groups: Dict[str, Set[str]] = defaultdict(set)
        self.sorted_by_change = SortedInstrumentList(
            lambda inst: float(inst.change_percent), reverse=True
        )
        self.sorted_by_volume = SortedInstrumentList(
            lambda inst: inst.volume, reverse=True
        )
        self.analytics = MarketAnalytics()
        self.last_analytics_update = 0
        self.analytics_update_interval = 1.0
        self.event_emitter = EventEmitter()
        self._last_broadcast_data = {
            "top_movers": None,
            "sentiment": None,
            "heatmap": None,
            "volume_analysis": None,
        }
        logger.info("RealtimeMarketEngine initialized")

    def initialize_instruments(self, instruments_metadata: List[Dict[str, Any]]):
        for metadata in instruments_metadata:
            instrument = Instrument(
                instrument_key=metadata["instrument_key"],
                symbol=metadata["symbol"],
                name=metadata["name"],
                sector=metadata.get("sector", "UNKNOWN"),
                exchange=metadata.get("exchange", "NSE"),
                market_cap=metadata.get("market_cap", 0),
                lot_size=metadata.get("lot_size", 1),
                avg_volume=metadata.get("avg_volume", 0),
                tick_size=float(metadata.get("tick_size", 0.05)),
            )
            self.instruments[instrument.instrument_key] = instrument
            self.sector_groups[instrument.sector].add(instrument.instrument_key)
        self._calculate_analytics()

    def update_market_data(self, updates: Dict[str, Dict[str, Any]]):
        updated_instruments = []
        for key, data in updates.items():
            if key in self.instruments:
                inst = self.instruments[key]
                inst.update_price(
                    new_price=data.get("ltp", 0),
                    volume=data.get("volume", 0),
                    timestamp=data.get("timestamp"),
                    close_price=data.get("close")
                    or data.get("prev_close")
                    or data.get("cp"),
                    open_price=data.get("open"),
                    high_price=data.get("high"),
                    low_price=data.get("low"),
                )
                updated_instruments.append(inst)
            else:
                # Auto-initialize instrument if not found
                symbol = key.split("|")[-1] if "|" in key else key
                exchange = key.split("|")[0] if "|" in key else "NSE"

                inst = Instrument(
                    instrument_key=key,
                    symbol=symbol,
                    name=symbol,
                    sector="UNKNOWN",
                    exchange=exchange,
                )
                self.instruments[key] = inst
                inst.update_price(
                    new_price=data.get("ltp", 0),
                    volume=data.get("volume", 0),
                    timestamp=data.get("timestamp"),
                    close_price=data.get("cp"),
                    open_price=data.get("open"),
                    high_price=data.get("high"),
                    low_price=data.get("low"),
                )
                updated_instruments.append(inst)
                logger.debug(f"Auto-initialized instrument: {key}")
        for inst in updated_instruments:
            self.sorted_by_change.update_instrument(inst)
            self.sorted_by_volume.update_instrument(inst)
        self.event_emitter.emit(
            "price_update",
            {
                i.instrument_key: {
                    "instrument_key": i.instrument_key,
                    "symbol": i.symbol,
                    "name": i.name,
                    "ltp": float(i.current_price),
                    "last_price": float(i.current_price),
                    "change": float(i.change),
                    "change_percent": float(i.change_percent),
                    "volume": i.volume,
                    "high": float(i.high_price),
                    "low": float(i.low_price),
                    "open": float(i.open_price),
                    "close": float(i.close_price),
                    "sector": i.sector,
                    "exchange": i.exchange,
                    "timestamp": i.last_update,
                }
                for i in updated_instruments
            },
        )
        if time.time() - self.last_analytics_update >= self.analytics_update_interval:
            self._calculate_analytics()
            self.last_analytics_update = time.time()

    def _calculate_analytics(self):
        calc_start = time.time()
        advancing = declining = unchanged = total_volume = 0
        unusual_volume_stocks = []
        new_highs = []
        new_lows = []
        sector_stats = defaultdict(
            lambda: {
                "total_change_percent": 0.0,
                "stock_count": 0,
                "total_volume": 0,
                "total_market_cap": 0,
                "advancing": 0,
                "declining": 0,
            }
        )

        for inst in self.instruments.values():
            if inst.change_percent > 0:
                advancing += 1
            elif inst.change_percent < 0:
                declining += 1
            else:
                unchanged += 1
            total_volume += inst.volume
            if inst.unusual_volume:
                unusual_volume_stocks.append(inst.get_heatmap_data())
            if inst.is_52_week_high:
                new_highs.append(inst.get_heatmap_data())
            if inst.is_52_week_low:
                new_lows.append(inst.get_heatmap_data())
            s = inst.sector
            sector_stats[s]["total_change_percent"] += inst.change_percent
            sector_stats[s]["stock_count"] += 1
            sector_stats[s]["total_volume"] += inst.volume
            sector_stats[s]["total_market_cap"] += inst.market_cap
            if inst.change_percent > 0:
                sector_stats[s]["advancing"] += 1
            elif inst.change_percent < 0:
                sector_stats[s]["declining"] += 1

        total_stocks = len(self.instruments)
        advance_decline_ratio = (
            float(advancing) / float(declining) if declining else 1.0
        )

        # sector performance
        sector_performance = {
            sec: {
                "avg_change_percent": (
                    float(stats["total_change_percent"] / stats["stock_count"])
                    if stats["stock_count"]
                    else 0.0
                ),
                "advancing": stats["advancing"],
                "declining": stats["declining"],
            }
            for sec, stats in sector_stats.items()
        }

        # Deduplicate by symbol to avoid showing same stock multiple times
        seen_symbols_gainers = set()
        top_gainers_dedup = []
        for i in self.sorted_by_change.get_top(50):  # Get more to account for duplicates
            if i.symbol not in seen_symbols_gainers and i.change_percent > 0:
                top_gainers_dedup.append(i.get_heatmap_data())
                seen_symbols_gainers.add(i.symbol)
                if len(top_gainers_dedup) >= 10:
                    break

        seen_symbols_losers = set()
        top_losers_dedup = []
        for i in reversed(self.sorted_by_change.get_bottom(50)):  # Get more to account for duplicates
            if i.symbol not in seen_symbols_losers and i.change_percent < 0:
                top_losers_dedup.append(i.get_heatmap_data())
                seen_symbols_losers.add(i.symbol)
                if len(top_losers_dedup) >= 10:
                    break

        seen_symbols_volume = set()
        volume_leaders_dedup = []
        for i in self.sorted_by_volume.get_top(50):  # Get more to account for duplicates
            if i.symbol not in seen_symbols_volume and i.volume > 0:
                volume_leaders_dedup.append(i.get_heatmap_data())
                seen_symbols_volume.add(i.symbol)
                if len(volume_leaders_dedup) >= 10:
                    break

        self.analytics.top_gainers = top_gainers_dedup
        self.analytics.top_losers = top_losers_dedup
        self.analytics.volume_leaders = volume_leaders_dedup
        self.analytics.total_stocks = total_stocks
        self.analytics.advancing_stocks = advancing
        self.analytics.declining_stocks = declining
        self.analytics.unchanged_stocks = unchanged
        self.analytics.advance_decline_ratio = advance_decline_ratio
        self.analytics.total_volume = total_volume
        self.analytics.avg_volume_ratio = (
            float(total_volume) / float(total_stocks)
            if total_stocks
            else 1.0
        )
        self.analytics.sector_performance = sector_performance
        self.analytics.unusual_volume_stocks = unusual_volume_stocks
        self.analytics.new_52_week_highs = new_highs
        self.analytics.new_52_week_lows = new_lows
        self.analytics.calculation_latency_ms = (time.time() - calc_start) * 1000
        self.analytics.last_calculation = time.time()

        logger.info(
            f"Analytics calculated: {len(top_gainers_dedup)} gainers, {len(top_losers_dedup)} losers"
        )

        gainer_symbols = [g.get('symbol') for g in top_gainers_dedup]
        loser_symbols = [l.get('symbol') for l in top_losers_dedup]

        logger.info(f"Top gainers: {gainer_symbols}")
        logger.info(f"Top losers: {loser_symbols}")

        # Check for duplicates
        if len(gainer_symbols) != len(set(gainer_symbols)):
            logger.warning(f"DUPLICATE GAINERS DETECTED: {gainer_symbols}")
        if len(loser_symbols) != len(set(loser_symbols)):
            logger.warning(f"DUPLICATE LOSERS DETECTED: {loser_symbols}")

        self.event_emitter.emit("analytics_update", self.analytics.to_dict())

    def get_instrument(self, instrument_key: str) -> Optional[Instrument]:
        """Get instrument by key"""
        return self.instruments.get(instrument_key)

    def get_all_instruments(self) -> Dict[str, Instrument]:
        """Get all instruments as dictionary"""
        return self.instruments.copy()

    def get_live_prices(self) -> Dict[str, Dict[str, Any]]:
        """Get all live prices in dictionary format for WebSocket broadcast"""
        return {
            key: {
                "instrument_key": key,
                "symbol": inst.symbol,
                "name": inst.name,
                "ltp": float(inst.current_price),
                "last_price": float(inst.current_price),
                "change": float(inst.change),
                "change_percent": float(inst.change_percent),
                "volume": inst.volume,
                "high": float(inst.high_price),
                "low": float(inst.low_price),
                "open": float(inst.open_price),
                "close": float(inst.close_price),
                "sector": inst.sector,
                "exchange": inst.exchange,
                "last_update": inst.last_update,
                "timestamp": inst.last_update,
            }
            for key, inst in self.instruments.items()
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics and metadata"""
        current_time = time.time()
        analytics_latency = (
            (current_time - self.last_analytics_update) * 1000
            if self.last_analytics_update > 0
            else 0
        )

        return {
            "total_instruments": len(self.instruments),
            "sectors": len(self.sector_groups),
            "analytics_latency_ms": analytics_latency,
            "last_update": self.last_analytics_update,
            "instruments_with_prices": sum(
                1 for inst in self.instruments.values() if inst.current_price > 0
            ),
        }


# Singleton instance
_market_engine_instance: Optional[RealtimeMarketEngine] = None


def get_market_engine() -> RealtimeMarketEngine:
    """Get or create singleton market engine instance"""
    global _market_engine_instance
    if _market_engine_instance is None:
        _market_engine_instance = RealtimeMarketEngine()
        logger.info("Market engine singleton created")
    return _market_engine_instance


def get_live_analytics() -> Optional[Dict[str, Any]]:
    """Get current analytics from market engine"""
    engine = get_market_engine()
    if engine and engine.analytics:
        return engine.analytics.to_dict()
    return None


def initialize_market_engine(instruments_metadata: List[Dict[str, Any]]) -> None:
    """Initialize market engine with instruments metadata"""
    engine = get_market_engine()
    engine.initialize_instruments(instruments_metadata)
    logger.info(
        f"Market engine initialized with {len(instruments_metadata)} instruments"
    )


def update_market_data(updates: Dict[str, Dict[str, Any]]) -> None:
    """Update market data in the engine"""
    engine = get_market_engine()
    engine.update_market_data(updates)


def get_market_sentiment() -> Dict[str, Any]:
    """
    Calculate market sentiment based on advance/decline ratio and market breadth.

    Returns:
        Dict containing sentiment classification, confidence, and metrics
    """
    engine = get_market_engine()
    analytics = engine.analytics

    advancing = analytics.advancing_stocks
    declining = analytics.declining_stocks
    total_stocks = analytics.total_stocks
    ad_ratio = analytics.advance_decline_ratio

    if total_stocks == 0:
        return {
            "sentiment": "neutral",
            "confidence": 0,
            "metrics": {
                "advance_decline_ratio": 1.0,
                "market_breadth_percent": 0,
                "advancing": 0,
                "declining": 0,
                "total_stocks": 0
            }
        }

    # Calculate market breadth percentage
    market_breadth_percent = ((advancing - declining) / total_stocks) * 100

    # Determine sentiment based on multiple factors
    if market_breadth_percent > 15 and ad_ratio > 2.0:
        sentiment = "very_bullish"
        confidence = min(95, abs(market_breadth_percent) * 4)
    elif market_breadth_percent > 5 and ad_ratio > 1.3:
        sentiment = "bullish"
        confidence = min(85, abs(market_breadth_percent) * 5)
    elif market_breadth_percent < -15 and ad_ratio < 0.5:
        sentiment = "very_bearish"
        confidence = min(95, abs(market_breadth_percent) * 4)
    elif market_breadth_percent < -5 and ad_ratio < 0.8:
        sentiment = "bearish"
        confidence = min(85, abs(market_breadth_percent) * 5)
    else:
        sentiment = "neutral"
        confidence = 50 + abs(market_breadth_percent)

    return {
        "sentiment": sentiment,
        "confidence": round(confidence, 1),
        "metrics": {
            "advance_decline_ratio": round(ad_ratio, 2),
            "market_breadth_percent": round(market_breadth_percent, 2),
            "advancing": advancing,
            "declining": declining,
            "total_stocks": total_stocks
        }
    }


def get_sector_performance() -> Dict[str, Any]:
    """
    Get sector-wise performance metrics.

    Returns:
        Dict with sector names as keys and performance metrics as values
    """
    engine = get_market_engine()
    analytics = engine.analytics

    sector_performance = {}
    for sector, perf_data in analytics.sector_performance.items():
        sector_performance[sector] = {
            "avg_change_percent": perf_data.get("avg_change_percent", 0),
            "advancing": perf_data.get("advancing", 0),
            "declining": perf_data.get("declining", 0),
            "total_stocks": perf_data.get("advancing", 0) + perf_data.get("declining", 0),
            "strength_score": perf_data.get("avg_change_percent", 0) * 10  # Normalized strength score
        }

    return sector_performance


def get_sector_stocks(sector: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get all stocks in a specific sector with their live data.

    Args:
        sector: Sector name to filter by

    Returns:
        Dict with sector name as key and list of stock data as value
    """
    engine = get_market_engine()

    if sector not in engine.sector_groups:
        return {sector: []}

    sector_stocks = []
    for instrument_key in engine.sector_groups[sector]:
        if instrument_key in engine.instruments:
            inst = engine.instruments[instrument_key]
            sector_stocks.append({
                "symbol": inst.symbol,
                "name": inst.name,
                "instrument_key": inst.instrument_key,
                "ltp": float(inst.current_price),
                "change_percent": float(inst.change_percent),
                "change": float(inst.change),
                "volume": inst.volume,
                "value_crores": float(inst.total_traded_value) / 1e7,  # Convert to crores
                "high": float(inst.high_price),
                "low": float(inst.low_price),
                "previous_close": float(inst.close_price),
                "sector": inst.sector,
                "is_fno": inst.lot_size > 1,  # Assume F&O if lot_size > 1
                "lot_size": inst.lot_size
            })

    # Sort by change_percent descending (gainers first)
    sector_stocks.sort(key=lambda x: x["change_percent"], reverse=True)

    return {sector: sector_stocks}
