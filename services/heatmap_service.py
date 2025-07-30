# services/heatmap_service.py
import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict
import math

from fastapi import HTTPException, Query

logger = logging.getLogger(__name__)

# Import enhanced sector mapping service
try:
    from services.enhanced_sector_mapping_service import enhanced_sector_mapping_service

    SECTOR_SERVICE_AVAILABLE = True
except ImportError:
    SECTOR_SERVICE_AVAILABLE = False
    logger.warning("Enhanced sector mapping service not available")

# Import instrument registry
try:
    from services.instrument_registry import instrument_registry

    INSTRUMENT_REGISTRY_AVAILABLE = True
except ImportError:
    INSTRUMENT_REGISTRY_AVAILABLE = False
    logger.warning("Instrument registry not available")


class HeatmapService:
    """Centralized service for generating Bloomberg-style heatmaps"""

    def __init__(self):
        self.sector_service = (
            enhanced_sector_mapping_service if SECTOR_SERVICE_AVAILABLE else None
        )
        self.instrument_registry = (
            instrument_registry if INSTRUMENT_REGISTRY_AVAILABLE else None
        )

    def get_market_data(self) -> Dict[str, Any]:
        """Get market data from instrument registry"""
        if not self.instrument_registry:
            return {}

        market_data = {}
        try:
            for symbol in self.instrument_registry._symbols_map:
                price_data = self.instrument_registry.get_spot_price(symbol)
                if price_data and price_data.get("last_price") is not None:
                    market_data[symbol] = {
                        "symbol": symbol,
                        "ltp": price_data.get("last_price"),
                        "change_percent": price_data.get("change_percent", 0),
                        "volume": price_data.get("volume", 0),
                        "exchange": price_data.get("exchange", "NSE"),
                        "open": price_data.get("open", 0),
                        "high": price_data.get("high", 0),
                        "low": price_data.get("low", 0),
                        "prev_close": price_data.get("prev_close", 0),
                    }
        except Exception as e:
            logger.error(f"Error getting market data: {e}")

        return market_data

    def generate_treemap_data(
        self, market_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate treemap data for Bloomberg-style heatmap"""
        if market_data is None:
            market_data = self.get_market_data()

        if not self.sector_service:
            return {
                "sectors": [],
                "total_stocks": 0,
                "metadata": {"error": "Sector service not available"},
            }

        try:
            heatmap_data = self.sector_service.get_heatmap_data(market_data)
            sectors = heatmap_data.get("sectors", [])

            # Calculate positions for treemap layout
            treemap_sectors = []
            total_market_cap = sum(
                sector.get("total_market_cap", 0) for sector in sectors
            )

            for sector in sectors:
                sector_stocks = sector.get("stocks", [])
                if not sector_stocks:
                    continue

                # Calculate sector metrics
                sector_market_cap = sector.get("total_market_cap", 0)
                sector_avg_change = sector.get("avg_change", 0)

                # Process individual stocks
                processed_stocks = []
                for stock in sector_stocks:
                    stock_data = {
                        "symbol": stock["symbol"],
                        "name": stock["name"],
                        "price": stock["price"],
                        "change_percent": stock["change_percent"],
                        "market_cap": stock["market_cap"],
                        "volume": stock["volume"],
                        "color": self._get_performance_color(stock["change_percent"]),
                        "size_value": stock["market_cap"],
                        "subcategory": stock.get("subcategory", ""),
                        "lot_size": stock.get("lot_size", 0),
                        "isin": stock.get("isin", ""),
                    }
                    processed_stocks.append(stock_data)

                # Sort stocks by market cap for better layout
                processed_stocks.sort(key=lambda x: x["market_cap"], reverse=True)

                treemap_sector = {
                    "name": sector["name"],
                    "key": sector["key"],
                    "icon": sector["icon"],
                    "color": sector["color"],
                    "description": sector["description"],
                    "avg_change": sector_avg_change,
                    "stock_count": len(processed_stocks),
                    "total_market_cap": sector_market_cap,
                    "weight": (
                        sector_market_cap / total_market_cap
                        if total_market_cap > 0
                        else 0
                    ),
                    "performance_color": self._get_performance_color(sector_avg_change),
                    "stocks": processed_stocks,
                }
                treemap_sectors.append(treemap_sector)

            # Sort sectors by market cap
            treemap_sectors.sort(key=lambda x: x["total_market_cap"], reverse=True)

            return {
                "sectors": treemap_sectors,
                "total_stocks": sum(
                    len(sector["stocks"]) for sector in treemap_sectors
                ),
                "total_market_cap": total_market_cap,
                "timestamp": datetime.now().isoformat(),
                "metadata": {
                    "total_sectors": len(treemap_sectors),
                    "generation_time": datetime.now().isoformat(),
                    "data_source": "enhanced_sector_mapping_service",
                },
            }

        except Exception as e:
            logger.error(f"Error generating treemap data: {e}")
            return {"sectors": [], "total_stocks": 0, "metadata": {"error": str(e)}}

    def generate_layout_positions(
        self, sectors: List[Dict[str, Any]], width: int = 1200, height: int = 800
    ) -> List[Dict[str, Any]]:
        """Generate layout positions for treemap cells using squarified algorithm"""

        def squarify(data, x=0, y=0, width=1200, height=800):
            """Simple squarified treemap algorithm"""
            if not data:
                return []

            total_size = sum(item["weight"] for item in data)
            if total_size == 0:
                return []

            # Normalize weights to area
            area = width * height
            for item in data:
                item["normalized_size"] = (item["weight"] / total_size) * area

            result = []

            def layout_row(row_data, x, y, width, height, horizontal=True):
                if not row_data:
                    return []

                total_row_size = sum(item["normalized_size"] for item in row_data)
                positions = []

                if horizontal:
                    # Lay out horizontally
                    current_x = x
                    for item in row_data:
                        if total_row_size > 0:
                            item_width = (
                                item["normalized_size"] / total_row_size
                            ) * width
                            item_height = height
                        else:
                            item_width = width / len(row_data)
                            item_height = height

                        positions.append(
                            {
                                **item,
                                "x": current_x,
                                "y": y,
                                "width": item_width,
                                "height": item_height,
                            }
                        )
                        current_x += item_width
                else:
                    # Lay out vertically
                    current_y = y
                    for item in row_data:
                        if total_row_size > 0:
                            item_height = (
                                item["normalized_size"] / total_row_size
                            ) * height
                            item_width = width
                        else:
                            item_height = height / len(row_data)
                            item_width = width

                        positions.append(
                            {
                                **item,
                                "x": x,
                                "y": current_y,
                                "width": item_width,
                                "height": item_height,
                            }
                        )
                        current_y += item_height

                return positions

            # Simple layout - just arrange in rows
            return layout_row(data, x, y, width, height, True)

        return squarify(sectors, 0, 0, width, height)

    def _get_performance_color(self, change_percent: float) -> str:
        """Get color based on performance change percentage"""
        if change_percent > 5:
            return "#004d00"  # strong_positive
        elif change_percent > 2:
            return "#008000"  # positive
        elif change_percent > 0:
            return "#90EE90"  # light_positive
        elif change_percent == 0:
            return "#808080"  # neutral
        elif change_percent > -2:
            return "#FFB6C1"  # light_negative
        elif change_percent > -5:
            return "#FF0000"  # negative
        else:
            return "#8B0000"  # strong_negative

    def get_bloomberg_heatmap(
        self, width: int = 1200, height: int = 800
    ) -> Dict[str, Any]:
        """Generate Bloomberg-style heatmap with positioned cells"""
        try:
            # Get treemap data
            treemap_data = self.generate_treemap_data()
            sectors = treemap_data.get("sectors", [])

            if not sectors:
                return {
                    "success": False,
                    "message": "No sector data available",
                    "data": {
                        "cells": [],
                        "sectors": [],
                        "stats": {
                            "total_stocks": 0,
                            "total_sectors": 0,
                            "gainers": 0,
                            "losers": 0,
                            "unchanged": 0,
                        },
                    },
                }

            # Generate layout positions
            positioned_sectors = self.generate_layout_positions(sectors, width, height)

            # Generate individual cells for stocks
            cells = []
            stats = {"total_stocks": 0, "gainers": 0, "losers": 0, "unchanged": 0}

            for sector in positioned_sectors:
                sector_stocks = sector.get("stocks", [])
                if not sector_stocks:
                    continue

                # Calculate stock positions within sector
                sector_area = sector["width"] * sector["height"]
                stock_positions = self.generate_layout_positions(
                    [
                        {"weight": stock["market_cap"], **stock}
                        for stock in sector_stocks
                    ],
                    sector["width"],
                    sector["height"],
                )

                for stock_pos in stock_positions:
                    change_percent = stock_pos.get("change_percent", 0)

                    # Update stats
                    stats["total_stocks"] += 1
                    if change_percent > 0.1:
                        stats["gainers"] += 1
                    elif change_percent < -0.1:
                        stats["losers"] += 1
                    else:
                        stats["unchanged"] += 1

                    # Create cell data
                    cell = {
                        "symbol": stock_pos["symbol"],
                        "name": stock_pos["name"],
                        "price": stock_pos["price"],
                        "change_percent": change_percent,
                        "market_cap": stock_pos["market_cap"],
                        "volume": stock_pos["volume"],
                        "sector": sector["name"],
                        "sector_key": sector["key"],
                        "x": sector["x"] + stock_pos["x"],
                        "y": sector["y"] + stock_pos["y"],
                        "width": stock_pos["width"],
                        "height": stock_pos["height"],
                        "color": stock_pos["color"],
                        "subcategory": stock_pos.get("subcategory", ""),
                        "lot_size": stock_pos.get("lot_size", 0),
                        "isin": stock_pos.get("isin", ""),
                    }
                    cells.append(cell)

            return {
                "success": True,
                "data": {
                    "cells": cells,
                    "sectors": positioned_sectors,
                    "stats": stats,
                    "dimensions": {"width": width, "height": height},
                    "timestamp": datetime.now().isoformat(),
                    "metadata": treemap_data.get("metadata", {}),
                },
            }

        except Exception as e:
            logger.error(f"Error generating Bloomberg heatmap: {e}")
            return {
                "success": False,
                "message": str(e),
                "data": {
                    "cells": [],
                    "sectors": [],
                    "stats": {
                        "total_stocks": 0,
                        "total_sectors": 0,
                        "gainers": 0,
                        "losers": 0,
                        "unchanged": 0,
                    },
                },
            }

    def get_sector_summary(self) -> Dict[str, Any]:
        """Get sector-wise summary statistics"""
        try:
            market_data = self.get_market_data()
            if not self.sector_service:
                return {"sectors": [], "total": 0}

            sector_performance = self.sector_service.get_sector_performance(market_data)

            summary = []
            for sector_key, sector_data in sector_performance.items():
                summary.append(
                    {
                        "sector": sector_data["display_name"],
                        "key": sector_key,
                        "icon": sector_data["icon"],
                        "total_stocks": sector_data["total_stocks"],
                        "gainers": sector_data["gainers"],
                        "losers": sector_data["losers"],
                        "unchanged": sector_data["unchanged"],
                        "avg_change": sector_data["avg_change"],
                        "gainer_percentage": sector_data["gainer_percentage"],
                        "loser_percentage": sector_data["loser_percentage"],
                        "market_sentiment": sector_data["market_sentiment"],
                        "performance_color": sector_data["performance_color"],
                        "top_gainer": sector_data.get("top_gainer"),
                        "top_loser": sector_data.get("top_loser"),
                    }
                )

            # Sort by average change
            summary.sort(key=lambda x: x["avg_change"], reverse=True)

            return {
                "sectors": summary,
                "total": len(summary),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting sector summary: {e}")
            return {"sectors": [], "total": 0, "error": str(e)}


# Create singleton instance
heatmap_service = HeatmapService()
