# from fastapi import APIRouter, HTTPException
# from typing import List, Dict, Any, Optional
# from datetime import datetime
# import logging

# from services.instrument_registry import instrument_registry

# logger = logging.getLogger(__name__)

# router = APIRouter(prefix="/api/instruments", tags=["instruments"])


# @router.get("/dashboard")
# async def get_dashboard_data():
#     """Get dashboard data with live prices"""
#     try:
#         dashboard_data = instrument_registry.get_dashboard_data()

#         # Log data details for debugging
#         logger.info(
#             f"Dashboard data: {len(dashboard_data.get('indices', []))} indices, {len(dashboard_data.get('top_stocks', []))} top stocks"
#         )

#         return {
#             "success": True,
#             "data": dashboard_data,
#             "timestamp": datetime.now().isoformat(),
#         }
#     except Exception as e:
#         logger.error(f"Error getting dashboard data: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get("/search")
# async def search_instruments(query: Optional[str] = None, q: Optional[str] = None, limit: int = 20):
#     """Search for instruments by symbol or name"""
#     try:
#         # Support both 'query' and 'q' parameters for backward compatibility
#         search_query = query or q
#         if not search_query:
#             raise HTTPException(status_code=400, detail="Query parameter required (use 'query' or 'q')")

#         # Use the instrument registry to search
#         from services.instrument_refresh_service import get_trading_service

#         service = get_trading_service()
#         results = service.search_instruments(search_query)

#         # Limit the results
#         limited_results = results[:limit]

#         return {
#             "success": True,
#             "query": search_query,
#             "results": limited_results,
#             "count": len(limited_results),
#         }
#     except Exception as e:
#         logger.error(f"Error searching instruments: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get("/fno-stocks")
# async def get_fno_stocks(categorized: bool = False):
#     """FIXED: Get complete list of F&O stocks with consistent data structure"""
#     try:
#         logger.info(f"FNO stocks request - categorized: {categorized}")

#         if categorized:
#             # Return categorized data with indices and stocks separated
#             from services.fno_stock_service import get_categorized_fno_data

#             try:
#                 logger.info("Fetching categorized FNO data...")
#                 categorized_data = get_categorized_fno_data()

#                 # Ensure consistent structure
#                 return {
#                     "success": True,
#                     "data": categorized_data,
#                     "count": categorized_data.get("metadata", {}).get("total_count", 0),
#                     "source": "categorized_service",
#                     "timestamp": datetime.now().isoformat()
#                 }
#             except Exception as cat_error:
#                 logger.error(f"Failed to get categorized data: {cat_error}")
#                 # Fall through to regular logic

#         # FIXED: Simplified and more reliable data fetching
#         from services.fno_stock_service import get_fno_stocks_from_file
#         import json
#         from pathlib import Path

#         # Primary method: Use the reliable service function
#         try:
#             fno_stocks = get_fno_stocks_from_file()
#             if fno_stocks:
#                 # Get additional metadata from JSON file
#                 json_file_path = Path("data/fno_stock_list.json")
#                 metadata = {}
#                 if json_file_path.exists():
#                     try:
#                         with open(json_file_path, "r", encoding="utf-8") as f:
#                             json_data = json.load(f)
#                             metadata = {
#                                 "last_updated": json_data.get("last_updated"),
#                                 "data_source": json_data.get("data_source", "fno_service"),
#                                 "total_count": json_data.get("total_count", len(fno_stocks))
#                             }
#                     except Exception as meta_error:
#                         logger.warning(f"Could not load metadata: {meta_error}")
#                         metadata = {"total_count": len(fno_stocks)}

#                 # Count breakdown for verification
#                 indices_symbols = ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'MIDCPNIFTY', 'NIFTY-NEXT50']
#                 indices_count = sum(1 for s in fno_stocks if s.get('symbol') in indices_symbols)
#                 stocks_count = len(fno_stocks) - indices_count

#                 logger.info(f"FNO data served: {len(fno_stocks)} total ({stocks_count} stocks + {indices_count} indices)")

#                 return {
#                     "success": True,
#                     "stocks": fno_stocks,
#                     "count": len(fno_stocks),
#                     "breakdown": {
#                         "total": len(fno_stocks),
#                         "stocks": stocks_count,
#                         "indices": indices_count
#                     },
#                     "source": "fno_service",
#                     "metadata": metadata,
#                     "timestamp": datetime.now().isoformat()
#                 }
#         except Exception as service_error:
#             logger.error(f"Primary FNO service failed: {service_error}")

#         # Fallback: Direct JSON file access
#         json_file_path = Path("data/fno_stock_list.json")
#         if json_file_path.exists():
#             try:
#                 logger.info("Using fallback: direct JSON file access")
#                 with open(json_file_path, "r", encoding="utf-8") as f:
#                     data = json.load(f)
#                     securities = data.get("securities", [])

#                     # Count breakdown
#                     indices_symbols = ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'MIDCPNIFTY', 'NIFTY-NEXT50']
#                     indices_count = sum(1 for s in securities if s.get('symbol') in indices_symbols)
#                     stocks_count = len(securities) - indices_count

#                     return {
#                         "success": True,
#                         "stocks": securities,
#                         "count": len(securities),
#                         "breakdown": {
#                             "total": len(securities),
#                             "stocks": stocks_count,
#                             "indices": indices_count
#                         },
#                         "source": "direct_json",
#                         "metadata": {
#                             "last_updated": data.get("last_updated"),
#                             "data_source": data.get("data_source"),
#                             "total_count": data.get("total_count", len(securities))
#                         },
#                         "timestamp": datetime.now().isoformat()
#                     }
#             except Exception as file_error:
#                 logger.error(f"Fallback JSON file access failed: {file_error}")

#         # Last resort: Return error if all methods fail
#         logger.error("All FNO data fetching methods failed")
#         raise HTTPException(
#             status_code=503,
#             detail="FNO stock data is temporarily unavailable. Please try refreshing the data."
#         )

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Unexpected error getting F&O stocks: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


# @router.post("/fno-stocks/refresh")
# async def refresh_fno_stocks():
#     """Refresh F&O stocks list by fetching latest data and updating JSON file"""
#     try:
#         from services.fno_stock_service import update_fno_stock_list, fix_missing_symbols_in_json

#         # Update the FNO stock list
#         result = update_fno_stock_list()

#         if result.get("status") == "success":
#             # Try to fix any missing symbols
#             fix_result = fix_missing_symbols_in_json()

#             return {
#                 "success": True,
#                 "message": "F&O stocks list refreshed successfully",
#                 "update_result": result,
#                 "fix_result": fix_result,
#                 "timestamp": datetime.now().isoformat()
#             }
#         else:
#             return {
#                 "success": False,
#                 "message": "Failed to refresh F&O stocks list",
#                 "error": result.get("error"),
#                 "result": result,
#                 "timestamp": datetime.now().isoformat()
#             }

#     except Exception as e:
#         logger.error(f"Error refreshing F&O stocks: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get("/fno-stocks/stats")
# async def get_fno_stocks_stats():
#     """ENHANCED: Get comprehensive statistics about F&O stocks data"""
#     try:
#         import json
#         from pathlib import Path

#         json_file_path = Path("data/fno_stock_list.json")

#         if not json_file_path.exists():
#             return {
#                 "success": False,
#                 "message": "F&O stocks JSON file not found",
#                 "file_exists": False,
#                 "timestamp": datetime.now().isoformat()
#             }

#         # Read file stats
#         file_stat = json_file_path.stat()
#         file_size_mb = file_stat.st_size / (1024 * 1024)

#         with open(json_file_path, "r", encoding="utf-8") as f:
#             data = json.load(f)

#         securities = data.get("securities", [])

#         # ENHANCED: Detailed analysis
#         symbols_with_data = sum(1 for s in securities if s.get("symbol"))
#         symbols_missing = sum(1 for s in securities if not s.get("symbol"))
#         exchanges = set(s.get("exchange", "Unknown") for s in securities)

#         # Count indices vs stocks
#         indices_symbols = ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'MIDCPNIFTY', 'NIFTY-NEXT50']
#         indices = [s for s in securities if s.get('symbol') in indices_symbols]
#         stocks = [s for s in securities if s.get('symbol') not in indices_symbols]

#         # Data quality assessment
#         from services.fno_stock_service import FnoStockListService
#         service = FnoStockListService()
#         quality_assessment = service._assess_data_quality(securities)

#         # Expected vs actual counts
#         expected_total = 221  # 216 stocks + 5 indices
#         actual_total = len(securities)
#         discrepancy = expected_total - actual_total

#         return {
#             "success": True,
#             "stats": {
#                 "total_securities": len(securities),
#                 "breakdown": {
#                     "stocks": len(stocks),
#                     "indices": len(indices),
#                     "total": len(securities)
#                 },
#                 "expected_vs_actual": {
#                     "expected": expected_total,
#                     "actual": actual_total,
#                     "discrepancy": discrepancy,
#                     "percentage_complete": round((actual_total / expected_total) * 100, 1)
#                 },
#                 "data_quality": {
#                     "score": quality_assessment.get("score", 0),
#                     "symbols_with_data": symbols_with_data,
#                     "symbols_missing": symbols_missing,
#                     "issues": quality_assessment.get("issues", []),
#                     "recommendations": quality_assessment.get("recommendations", [])
#                 },
#                 "exchanges": list(exchanges),
#                 "file_size_mb": round(file_size_mb, 3),
#                 "last_updated": data.get("last_updated"),
#                 "data_source": data.get("data_source"),
#                 "json_total_count": data.get("total_count")
#             },
#             "indices_details": [
#                 {"name": idx.get("name"), "symbol": idx.get("symbol"), "exchange": idx.get("exchange")}
#                 for idx in indices
#             ],
#             "file_info": {
#                 "exists": True,
#                 "path": str(json_file_path),
#                 "modified_time": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
#                 "age_hours": round((datetime.now().timestamp() - file_stat.st_mtime) / 3600, 1)
#             },
#             "system_health": {
#                 "file_accessible": True,
#                 "data_valid": len(securities) > 200,
#                 "indices_complete": len(indices) == 5,
#                 "recent_update": (datetime.now().timestamp() - file_stat.st_mtime) < (7 * 24 * 3600)  # Within 7 days
#             },
#             "timestamp": datetime.now().isoformat()
#         }

#     except Exception as e:
#         logger.error(f"Error getting F&O stocks stats: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get("/chain")
# async def get_options_chain_legacy(symbol: str, range: Optional[str] = None):
#     """Legacy endpoint for options chain - backward compatibility"""
#     try:
#         # Call the new options chain endpoint
#         return await get_options_chain(symbol, range, False, True)
#     except Exception as e:
#         logger.error(f"Error in legacy chain endpoint for {symbol}: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get("/options-chain/{symbol}")
# async def get_options_chain(
#     symbol: str,
#     expiry: Optional[str] = None,
#     with_greeks: bool = False,
#     with_analytics: bool = True,
# ):
#     """Get enhanced options chain for a symbol with live prices"""
#     try:
#         # Add expiry parameter to get_options_chain
#         options_chain = instrument_registry.get_options_chain(symbol.upper(), expiry)

#         if "error" in options_chain:
#             raise HTTPException(status_code=404, detail=options_chain["error"])

#         # Get spot price for ATM identification
#         spot_data = instrument_registry.get_spot_price(symbol.upper())
#         spot_price = spot_data.get("last_price") if spot_data else None

#         # Add ATM strike identification
#         if spot_price and "strikes" in options_chain:
#             options_chain["atm_strike"] = min(
#                 options_chain["strikes"], key=lambda x: abs(x - spot_price)
#             )

#         # Add analytics if requested
#         if with_analytics:
#             analytics = {}

#             # Calculate Put-Call Ratio
#             call_volume = sum(
#                 call.get("volume", 0) or 0
#                 for call in options_chain.get("call_data", [])
#             )
#             put_volume = sum(
#                 put.get("volume", 0) or 0 for put in options_chain.get("put_data", [])
#             )

#             if call_volume > 0:
#                 analytics["pcr_volume"] = round(put_volume / call_volume, 2)

#             call_oi = sum(
#                 call.get("oi", 0) or 0 for call in options_chain.get("call_data", [])
#             )
#             put_oi = sum(
#                 put.get("oi", 0) or 0 for put in options_chain.get("put_data", [])
#             )

#             if call_oi > 0:
#                 analytics["pcr_oi"] = round(put_oi / call_oi, 2)

#             # Add analytics to response
#             options_chain["analytics"] = analytics

#         return {
#             "success": True,
#             "symbol": symbol.upper(),
#             "spot_price": spot_price,
#             "data": options_chain,
#         }
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error getting options chain for {symbol}: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get("/trading-data/{symbol}")
# async def get_trading_data(symbol: str):
#     """Get comprehensive trading data for a symbol"""
#     try:
#         # Get spot price
#         spot_data = instrument_registry.get_spot_price(symbol.upper())
#         if not spot_data:
#             raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")

#         # Get options chain
#         options_chain = instrument_registry.get_options_chain(symbol.upper())

#         # Return combined data
#         return {
#             "success": True,
#             "symbol": symbol.upper(),
#             "spot": spot_data,
#             "options_chain": options_chain,
#             "updated_at": datetime.now().isoformat(),
#         }
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error getting trading data for {symbol}: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get("/websocket-keys/dashboard")
# async def get_dashboard_websocket_keys():
#     """Get instrument keys for dashboard WebSocket subscription"""
#     try:
#         keys = instrument_registry.get_instrument_keys_for_dashboard()

#         return {
#             "success": True,
#             "keys": keys,
#             "count": len(keys),
#             "timestamp": datetime.now().isoformat(),
#         }
#     except Exception as e:
#         logger.error(f"Error getting dashboard WebSocket keys: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get("/websocket-keys/trading/{symbol}")
# async def get_trading_websocket_keys(symbol: str):
#     """Get instrument keys for trading a specific symbol"""
#     try:
#         keys = instrument_registry.get_instrument_keys_for_trading(symbol.upper())

#         return {
#             "success": True,
#             "symbol": symbol.upper(),
#             "keys": keys,
#             "count": len(keys),
#             "timestamp": datetime.now().isoformat(),
#         }
#     except Exception as e:
#         logger.error(f"Error getting trading WebSocket keys for {symbol}: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get("/live-prices/{symbol}")
# async def get_live_price(symbol: str):
#     """Get live price for a specific symbol"""
#     try:
#         price_data = instrument_registry.get_spot_price(symbol.upper())
#         if not price_data:
#             raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")

#         return {
#             "success": True,
#             "symbol": symbol.upper(),
#             "data": price_data,
#             "timestamp": datetime.now().isoformat(),
#         }
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error getting live price for {symbol}: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get("/stats")
# async def get_registry_stats():
#     """Get registry statistics"""
#     try:
#         stats = instrument_registry.get_stats()

#         # Add last update time in a more readable format
#         if "last_update" in stats and stats["last_update"]:
#             try:
#                 last_update = datetime.fromisoformat(stats["last_update"])
#                 stats["last_update_ago"] = (
#                     f"{(datetime.now() - last_update).total_seconds():.0f} seconds ago"
#                 )
#             except:
#                 pass

#         return {
#             "success": True,
#             "stats": stats,
#             "timestamp": datetime.now().isoformat(),
#         }
#     except Exception as e:
#         logger.error(f"Error getting registry stats: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


# @router.post("/refresh")
# async def refresh_registry():
#     """Manually refresh the instrument registry"""
#     try:
#         # Re-initialize the registry
#         result = await instrument_registry.initialize_registry()

#         return {
#             "success": result,
#             "message": (
#                 "Registry refresh completed" if result else "Registry refresh failed"
#             ),
#             "stats": instrument_registry.get_stats(),
#             "timestamp": datetime.now().isoformat(),
#         }
#     except Exception as e:
#         logger.error(f"Error refreshing registry: {e}")
#         raise HTTPException(status_code=500, detail=str(e))
