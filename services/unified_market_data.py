# # services/unified_market_data.py
# import logging
# from typing import Dict, List, Any, Optional, Callable
# from datetime import datetime

# from services.market_analytics_service import market_analytics
# from services.heatmap_service import heatmap_service

# logger = logging.getLogger(__name__)


# class MarketDataProcessor:
#     """
#     Unified market data processor that:
#     1. Receives WebSocket data
#     2. Normalizes it
#     3. Distributes to analytics services
#     """

#     def __init__(self):
#         self.last_update = None
#         self.registered_callbacks = []
#         self.current_data = {}

#     def extract_symbol_from_key(self, instrument_key: str) -> Optional[str]:
#         """Extract symbol from instrument key - delegates to analytics service"""
#         return market_analytics.extract_symbol_from_key(instrument_key)

#     def process_market_update(self, market_data: Dict[str, Any]) -> None:
#         """Process a market data update from WebSocket"""
#         try:
#             logger.debug(
#                 f"Processing market update with {len(market_data)} instruments"
#             )

#             # Update current data
#             self.current_data.update(market_data)
#             self.last_update = datetime.now()

#             # Process in market analytics service
#             market_analytics.process_market_data(self.current_data)

#             # Notify all callbacks
#             for callback in self.registered_callbacks:
#                 try:
#                     callback(self.current_data)
#                 except Exception as e:
#                     logger.error(f"Error in market data callback: {e}")

#         except Exception as e:
#             logger.error(f"Error processing market update: {e}")
#             import traceback

#             logger.error(traceback.format_exc())

#     def register_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
#         """Register a callback to be notified of market updates"""
#         if callback not in self.registered_callbacks:
#             self.registered_callbacks.append(callback)
#             logger.info("Registered new market data callback")

#     def unregister_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
#         """Unregister a callback"""
#         if callback in self.registered_callbacks:
#             self.registered_callbacks.remove(callback)
#             logger.info("Unregistered market data callback")

#     def get_current_data(self) -> Dict[str, Any]:
#         """Get the current market data"""
#         return self.current_data

#     def get_top_gainers(self, limit: int = 10) -> List[Dict[str, Any]]:
#         """Get top gainers - delegates to analytics service"""
#         return market_analytics.get_top_gainers(limit)

#     # services/unified_market_data.py (continued)
#     def get_top_losers(self, limit: int = 10) -> List[Dict[str, Any]]:
#         """Get top losers - delegates to analytics service"""
#         return market_analytics.get_top_losers(limit)

#     def get_volume_leaders(self, limit: int = 10) -> List[Dict[str, Any]]:
#         """Get volume leaders - delegates to analytics service"""
#         return market_analytics.get_volume_leaders(limit)

#     def get_intraday_picks(self, limit: int = 10) -> List[Dict[str, Any]]:
#         """Get intraday trading opportunities - delegates to analytics service"""
#         return market_analytics.get_intraday_picks(limit)

#     def get_sector_performance(self) -> Dict[str, Dict[str, Any]]:
#         """Get sector performance - delegates to analytics service"""
#         return market_analytics.get_sector_performance()

#     def get_heatmap_data(
#         self, size_metric: str = "market_cap", color_metric: str = "change_percent"
#     ) -> Dict[str, Any]:
#         """Get heatmap data - delegates to heatmap service"""
#         return heatmap_service.generate_sector_heatmap(
#             self.current_data, size_metric, color_metric
#         )

#     def get_market_cap_heatmap(self) -> Dict[str, Any]:
#         """Get market cap heatmap - delegates to heatmap service"""
#         return heatmap_service.generate_market_cap_heatmap(self.current_data)

#     def get_performance_heatmap(self, time_period: str = "1D") -> Dict[str, Any]:
#         """Get performance heatmap - delegates to heatmap service"""
#         return heatmap_service.generate_performance_heatmap(
#             self.current_data, time_period
#         )

#     def get_treemap_data(self) -> Dict[str, Any]:
#         """Get treemap data - delegates to heatmap service"""
#         return heatmap_service.get_treemap_data(self.current_data)

#     def filter_by_sector(
#         self, data: List[Dict[str, Any]], sector: str
#     ) -> List[Dict[str, Any]]:
#         """Filter data by sector - delegates to analytics service"""
#         return market_analytics.filter_by_sector(data, sector)

#     def get_market_status(self) -> Dict[str, Any]:
#         """Get market status - delegates to analytics service"""
#         return market_analytics.get_market_status()

#     def get_all_stocks_by_sector(self) -> Dict[str, List[Dict[str, Any]]]:
#         """Get all stocks grouped by sector"""
#         sector_performance = market_analytics.get_sector_performance()
#         result = {}

#         for sector_name, sector_info in sector_performance.items():
#             result[sector_name] = sector_info.get("stocks", [])

#         return result

#     def is_data_fresh(self) -> bool:
#         """Check if data is fresh (less than 1 minute old)"""
#         if not self.last_update:
#             return False

#         now = datetime.now()
#         diff = (now - self.last_update).total_seconds()
#         return diff < 60  # Less than 1 minute old


# # Create singleton instance
# market_data_processor = MarketDataProcessor()
