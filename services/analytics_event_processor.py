# # services/analytics_event_processor.py
# """
# Process analytics events and emit to unified WebSocket
# """

# import asyncio
# import logging
# from services.enhanced_market_analytics import enhanced_analytics
# from services.unified_websocket_manager import unified_manager


# class AnalyticsEventProcessor:
#     def __init__(self):
#         self.is_running = False

#     async def start(self):
#         self.is_running = True
#         # Process analytics every 30 seconds
#         asyncio.create_task(self._process_analytics())

#     async def _process_analytics(self):
#         while self.is_running:
#             try:
#                 # Get complete analytics
#                 analytics = enhanced_analytics.get_complete_analytics()

#                 # Emit individual events
#                 unified_manager.emit_event(
#                     "top_movers_update", analytics.get("top_movers", {})
#                 )
#                 unified_manager.emit_event(
#                     "gap_analysis_update", analytics.get("gap_analysis", {})
#                 )
#                 unified_manager.emit_event(
#                     "breakout_analysis_update", analytics.get("breakout_analysis", {})
#                 )
#                 unified_manager.emit_event(
#                     "market_sentiment_update", analytics.get("market_sentiment", {})
#                 )
#                 unified_manager.emit_event(
#                     "heatmap_update", analytics.get("sector_heatmap", {})
#                 )
#                 unified_manager.emit_event(
#                     "intraday_stocks_update", analytics.get("intraday_stocks", {})
#                 )

#                 await asyncio.sleep(30)

#             except Exception as e:
#                 logging.error(f"Analytics processing error: {e}")
#                 await asyncio.sleep(60)
