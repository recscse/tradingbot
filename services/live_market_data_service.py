# from services.instrument_refresh_service import instrument_registry
# from services.buffers.tick_buffer_manager import tick_buffer


# class LiveMarketDataService:
#     def __init__(self):
#         self._latest_data = {}

#     def route_tick(self, symbol: str, tick: dict):
#         """
#         Entry point for all parsed ticks
#         """
#         instrument_registry.update_live_prices(symbol, tick)
#         tick_buffer.add_tick(symbol, tick)

#         # Store locally (can include enrichment later)
#         self._latest_data[symbol] = tick

#     def get_latest_tick(self, symbol: str) -> dict:
#         return self._latest_data.get(symbol, {})

#     def get_all_latest_data(self) -> dict:
#         return self._latest_data

#     def get_mapped_tick_with_name(self, symbol: str) -> dict:
#         inst_info = instrument_registry.get_instrument_by_key(symbol)
#         tick = self._latest_data.get(symbol, {})
#         return {
#             **tick,
#             "symbol_name": inst_info.get("symbol", ""),
#             "instrument_key": symbol,
#         }
