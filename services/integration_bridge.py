# # services/integration_bridge.py
# """
# Bridge between existing centralized manager and new unified system
# """


# async def setup_integration():
#     from services.centralized_ws_manager import centralized_manager
#     from services.unified_websocket_manager import unified_manager

#     # Forward price updates from centralized to unified
#     def price_update_forwarder(data):
#         unified_manager.emit_event("price_update", data.get("data", {}))

#     centralized_manager.register_callback("price_update", price_update_forwarder)
