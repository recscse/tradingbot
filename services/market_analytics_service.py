# services/market_analytics_service.py

import logging
from typing import List, Dict, Any, Optional
from services.sector_mapping import SECTOR_STOCKS, SYMBOL_TO_SECTOR
from services.instrument_registry import instrument_registry
from collections import defaultdict

logger = logging.getLogger(__name__)


class MarketAnalyticsService:
    """Centralized analytics for top gainers, losers, volume leaders, sector-wise data, and heatmap."""

    def __init__(self):
        self.registry = instrument_registry

    def get_all_live_stocks(self) -> List[Dict[str, Any]]:
        """Get all stocks with live data (excluding indices)."""
        stocks = []
        for symbol in self.registry._symbols_map:
            # Exclude indices
            if symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "MIDCPNIFTY"]:
                continue
            price = self.registry.get_spot_price(symbol)
            if price and price.get("last_price") is not None:
                stocks.append({**price, "symbol": symbol})
        return stocks

    def get_top_gainers(self, limit=10) -> List[Dict[str, Any]]:
        """Return top N gainers by percentage change."""
        stocks = self.get_all_live_stocks()
        sorted_stocks = sorted(
            stocks, key=lambda x: x.get("change_percent", 0), reverse=True
        )
        return [s for s in sorted_stocks if s.get("change_percent", 0) > 0][:limit]

    def get_top_losers(self, limit=10) -> List[Dict[str, Any]]:
        """Return top N losers by percentage change."""
        stocks = self.get_all_live_stocks()
        sorted_stocks = sorted(stocks, key=lambda x: x.get("change_percent", 0))
        return [s for s in sorted_stocks if s.get("change_percent", 0) < 0][:limit]

    def get_volume_leaders(self, limit=10) -> List[Dict[str, Any]]:
        """Return top N stocks by traded volume."""
        stocks = self.get_all_live_stocks()
        sorted_stocks = sorted(
            stocks, key=lambda x: x.get("volume", 0) or 0, reverse=True
        )
        return sorted_stocks[:limit]

    def get_intraday_picks(
        self, limit=10, min_change=2.0, min_volume=100000
    ) -> List[Dict[str, Any]]:
        """Return top intraday picks based on configurable filters."""
        stocks = self.get_all_live_stocks()
        filtered = []
        for s in stocks:
            try:
                change_percent = float(s.get("change_percent", 0))
            except (ValueError, TypeError):
                change_percent = 0
            try:
                volume = int(float(s.get("volume", 0)) or 0)
            except (ValueError, TypeError):
                volume = 0

            if abs(change_percent) >= min_change and volume >= min_volume:
                filtered.append(s)

        sorted_stocks = sorted(
            filtered,
            key=lambda x: abs(float(x.get("change_percent", 0) or 0)),
            reverse=True,
        )
        return sorted_stocks[:limit]

    def get_sector_performance(self) -> Dict[str, Any]:
        """Return sector-wise stats (requires sector info in your instrument metadata)."""
        # Example assumes you have sector as part of instrument data!
        sector_map = defaultdict(list)
        for symbol in self.registry._symbols_map:
            price = self.registry.get_spot_price(symbol)
            if not price or price.get("last_price") is None:
                continue
            # Try to get sector from metadata, fallback to "Unknown"
            instrument_keys = self.registry._symbols_map[symbol]["spot"]
            sector = "Unknown"
            if instrument_keys:
                key = instrument_keys[0]
                instrument = self.registry._spot_instruments.get(key) or {}
                sector = instrument.get("sector", "Unknown")
            sector_map[sector].append(price)

        sector_stats = []
        for sector, stocks in sector_map.items():
            total = len(stocks)
            adv = sum(1 for s in stocks if s.get("change_percent", 0) > 0)
            dec = sum(1 for s in stocks if s.get("change_percent", 0) < 0)
            unchanged = total - adv - dec
            avg_chg = (
                sum(s.get("change_percent", 0) or 0 for s in stocks) / total
                if total > 0
                else 0
            )
            sector_stats.append(
                {
                    "sector": sector,
                    "total": total,
                    "advancers": adv,
                    "decliners": dec,
                    "unchanged": unchanged,
                    "avg_change_percent": round(avg_chg, 2),
                }
            )
        return {"sectors": sector_stats}

    def get_heatmap_data(
        self, size_metric="market_cap", color_metric="change_percent"
    ) -> Dict[str, Any]:
        """Build sector heatmap (structure suitable for React d3/heatmap UI)."""
        # This example assumes instrument metadata contains 'sector' and 'market_cap'
        sector_data = defaultdict(list)
        for symbol in self.registry._symbols_map:
            price = self.registry.get_spot_price(symbol)
            if not price or price.get("last_price") is None:
                continue
            keys = self.registry._symbols_map[symbol]["spot"]
            sector = "Unknown"
            market_cap = 0
            if keys:
                key = keys[0]
                instrument = self.registry._spot_instruments.get(key) or {}
                sector = instrument.get("sector", "Unknown")
                market_cap = instrument.get("market_cap", 0)
            entry = {
                "symbol": symbol,
                "last_price": price.get("last_price"),
                "change_percent": price.get("change_percent"),
                "volume": price.get("volume"),
                "market_cap": market_cap,
            }
            sector_data[sector].append(entry)

        heatmap = []
        for sector, stocks in sector_data.items():
            # Sort by color metric, size metric
            for s in stocks:
                s["size"] = s.get(size_metric, 0) or 1
                s["color"] = s.get(color_metric, 0) or 0
            sector_block = {
                "sector": sector,
                "stocks": stocks,
            }
            heatmap.append(sector_block)
        return {"heatmap": heatmap}

    def get_market_status(self) -> Dict[str, Any]:
        """Return basic market status/breadth (adv/dec, etc)."""
        stocks = self.get_all_live_stocks()
        adv = sum(1 for s in stocks if s.get("change_percent", 0) > 0)
        dec = sum(1 for s in stocks if s.get("change_percent", 0) < 0)
        unchanged = len(stocks) - adv - dec
        nifty_data = self.registry.get_spot_price("NIFTY")
        return {
            "status": "open",  # TODO: Add actual market hours check
            "breadth": {
                "total": len(stocks),
                "advancers": adv,
                "decliners": dec,
                "unchanged": unchanged,
                "advance_decline_ratio": round(adv / dec, 2) if dec > 0 else 0,
            },
            "nifty": nifty_data,
            "last_update": (
                self.registry._last_update.isoformat()
                if self.registry._last_update
                else None
            ),
        }

    def get_symbols_for_sector(self, sector: str) -> list:
        """Return all symbols for a sector."""
        return SECTOR_STOCKS.get(sector.upper(), [])

    def get_sector_for_symbol(self, symbol: str) -> str:
        """Return sector for a stock symbol."""
        return SYMBOL_TO_SECTOR.get(symbol.upper(), "UNKNOWN")

    def get_sector_gainers_losers(self, sector: str, top_n: int = 20) -> dict:
        """Top gainers/losers for a sector."""
        sector_symbols = self.get_symbols_for_sector(sector)
        stock_data = []
        for symbol in sector_symbols:
            spot = self.registry.get_spot_price(symbol)
            if (
                spot
                and spot.get("last_price") is not None
                and spot.get("change_percent") is not None
            ):
                stock_data.append(
                    {
                        "symbol": symbol,
                        "name": spot.get("name", symbol),
                        "last_price": spot.get("last_price"),
                        "change_percent": spot.get("change_percent"),
                        "volume": spot.get("volume", 0),
                    }
                )

        gainers = sorted(stock_data, key=lambda x: x["change_percent"], reverse=True)[
            :top_n
        ]
        losers = sorted(stock_data, key=lambda x: x["change_percent"])[:top_n]

        return {"sector": sector, "gainers": gainers, "losers": losers}

    def get_sector_heatmap_data(self, metric: str = "change_percent") -> list:
        """Sector-wise heatmap for a metric (change_percent, volume, etc)."""
        heatmap = []
        for sector in SECTOR_STOCKS.keys():
            stocks = []
            for symbol in self.get_symbols_for_sector(sector):
                spot = self.registry.get_spot_price(symbol)
                if (
                    spot
                    and spot.get("last_price") is not None
                    and spot.get(metric) is not None
                ):
                    stocks.append(
                        {
                            "symbol": symbol,
                            "name": spot.get("name", symbol),
                            metric: spot.get(metric),
                            "volume": spot.get("volume", 0),
                        }
                    )
            sector_metric = None
            if stocks:
                sector_metric = sum(s[metric] for s in stocks) / len(stocks)
            heatmap.append(
                {"sector": sector, "metric": sector_metric, "stocks": stocks}
            )
        return heatmap

    def get_all_sectors(self) -> list:
        return list(SECTOR_STOCKS.keys())


# Singleton instance for import
market_analytics = MarketAnalyticsService()
