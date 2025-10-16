# # services/trading_stock_selector.py
# import logging
# import json
# from datetime import date, datetime
# from typing import List, Dict, Any

# try:
#     import polars as pl

#     _USE_POLARS = True
# except Exception:
#     import pandas as pd

#     _USE_POLARS = False

# from sqlalchemy.orm import Session
# from database.connection import SessionLocal
# from database.models import SelectedStock, UserTradingConfig
# from services.enhanced_market_analytics import enhanced_analytics  # your singleton
# from services.upstox_option_service import upstox_option_service
# from services.strategy_engine import strategy_score

# logger = logging.getLogger(__name__)


# class TradingStockSelector:
#     def __init__(
#         self,
#         analytics=enhanced_analytics,
#         db_session_factory=SessionLocal,
#         option_service=None,
#         sectors_to_pick: int = 1,  # Only pick 1 top sector based on sentiment
#         per_sector_limit: int = 2,  # Exactly 2 middle-performing stocks
#         max_total_stocks: int = 2,  # Total output: exactly 2 stocks
#         user_id: int = None,  # NEW: User ID for personalized config
#     ):
#         self.analytics = analytics
#         self.db_session_factory = db_session_factory
#         self.sectors_to_pick = sectors_to_pick
#         self.per_sector_limit = per_sector_limit
#         self.max_total_stocks = max_total_stocks
#         self.option_service = option_service or upstox_option_service
#         self.user_id = user_id

#     def _map_sentiment_to_option_type(self, sentiment: str) -> str:
#         s = (sentiment or "").lower()
#         if "bull" in s:
#             return "CE"
#         if "bear" in s:
#             return "PE"
#         return "NEUTRAL"

#     def run_selection_sync(self) -> List[Dict[str, Any]]:
#         start = datetime.utcnow()

#         sentiment_obj = self.analytics.get_market_sentiment()
#         sentiment = (
#             sentiment_obj.get("sentiment", "neutral")
#             if isinstance(sentiment_obj, dict)
#             else str(sentiment_obj or "neutral")
#         )
#         sector_heatmap_obj = self.analytics.get_sector_heatmap()
#         if not sector_heatmap_obj or not isinstance(sector_heatmap_obj, dict):
#             logger.warning("Sector heatmap not available -> aborting selection")
#             return []

#         # Pick the single TOP performing sector based on market sentiment
#         top_sector = self._choose_top_sector_by_sentiment(sector_heatmap_obj, sentiment)
#         if not top_sector:
#             logger.warning("No top sector found -> aborting selection")
#             return []

#         logger.info("Selected TOP sector: %s (sentiment=%s)", top_sector, sentiment)

#         # Get stocks from the TOP sector only
#         stocks = self._safe_get_stocks_by_sector(top_sector)
#         if not stocks:
#             logger.warning(f"No stocks found for top sector {top_sector}")
#             return []

#         df = self._to_frame(stocks)
#         if df is None or len(df) == 0:
#             logger.warning(f"No valid data frame for top sector {top_sector}")
#             return []

#         df = self._ensure_pct_change(df)

#         # Sort by percentage change to find middle performers
#         df = (
#             df.sort("pct_change", reverse=False)
#             if _USE_POLARS
#             else df.sort_values("pct_change", ascending=True)
#         )

#         # Select exactly 2 middle-performing stocks
#         selected_frame = self._select_midrange(df, self.per_sector_limit)
#         candidates = self._frame_to_dicts(selected_frame)

#         # Enhance each candidate with metadata and analysis
#         for d in candidates:
#             d["sector"] = top_sector
#             d["selection_reason"] = (
#                 f"{sentiment} market → {top_sector} top sector, mid-performer"
#             )

#             # decide CE/PE based on sentiment
#             opt_type = self._map_sentiment_to_option_type(sentiment)
#             d["option_type"] = opt_type

#             # compute simple strategy score using historical price series from analytics
#             try:
#                 hist_prices = self.analytics.get_historical_prices(
#                     d["symbol"], lookback=60
#                 )  # last 60 ticks/periods
#                 score, details = strategy_score(
#                     hist_prices, "bullish" if opt_type == "CE" else "bearish"
#                 )
#                 d["strategy_score"] = score
#                 d["strategy_details"] = details
#             except Exception as e:
#                 logger.exception(
#                     "Strategy scoring failed for %s: %s", d.get("symbol"), e
#                 )
#                 d["strategy_score"] = 0
#                 d["strategy_details"] = {}

#             # fetch option contracts and option chain based on instrument key and option type
#             d["option_contract"] = None
#             d["option_contracts_available"] = 0
#             d["option_chain_data"] = None
#             d["option_expiry_date"] = None
#             d["option_expiry_dates"] = []
#             if opt_type in ("CE", "PE") and self.option_service:
#                 try:
#                     # Get option contracts using the instrument key
#                     instrument_key = d.get("instrument_key")
#                     symbol = d.get("symbol")

#                     if instrument_key and symbol:
#                         # Use database session for option service calls
#                         db = self.db_session_factory()
#                         try:
#                             # First check if this instrument has valid expiry dates
#                             logger.info(
#                                 f"Checking expiry dates for {symbol} ({instrument_key})"
#                             )
#                             expiry_dates = self.option_service.get_expiry_dates(
#                                 instrument_key, db
#                             )

#                             if not expiry_dates:
#                                 logger.warning(
#                                     f"No valid expiry dates found for {symbol}, skipping option contracts"
#                                 )
#                                 d["option_contract"] = None
#                                 d["option_contracts_available"] = 0
#                                 d["option_chain_data"] = None
#                                 d["option_expiry_date"] = None
#                                 d["option_expiry_dates"] = []
#                             else:
#                                 # Store all available expiry dates
#                                 d["option_expiry_dates"] = expiry_dates

#                                 # Use the nearest expiry for option contracts
#                                 nearest_expiry = expiry_dates[
#                                     0
#                                 ]  # Already sorted by nearest first
#                                 d["option_expiry_date"] = nearest_expiry
#                                 logger.info(
#                                     f"Using nearest expiry {nearest_expiry} for {symbol}"
#                                 )

#                                 # Get option contracts for the nearest expiry
#                                 option_contracts = (
#                                     self.option_service.get_option_contracts(
#                                         instrument_key, db, nearest_expiry
#                                     )
#                                 )

#                                 # Also fetch complete option chain for this expiry
#                                 logger.info(
#                                     f"Fetching complete option chain for {symbol} with expiry {nearest_expiry}"
#                                 )
#                                 option_chain = self.option_service.get_option_chain(
#                                     instrument_key, nearest_expiry, db
#                                 )

#                                 if option_chain:
#                                     # Store complete option chain data
#                                     option_chain_json = {
#                                         "underlying_symbol": option_chain.underlying_symbol,
#                                         "underlying_key": option_chain.underlying_key,
#                                         "spot_price": option_chain.spot_price,
#                                         "expiry_dates": option_chain.expiry_dates,
#                                         "strike_prices": option_chain.strike_prices,
#                                         "options_count": len(option_chain.options),
#                                         "futures_count": len(option_chain.futures),
#                                         "generated_at": (
#                                             option_chain.generated_at.isoformat()
#                                             if option_chain.generated_at
#                                             else None
#                                         ),
#                                         # Note: Full options data is too large, storing summary only
#                                         # Individual contracts are stored separately
#                                     }
#                                     d["option_chain_data"] = option_chain_json
#                                     logger.info(
#                                         f"Stored option chain data for {symbol}: {len(option_chain.strike_prices)} strikes, spot={option_chain.spot_price}"
#                                     )
#                                 else:
#                                     logger.warning(
#                                         f"Could not fetch option chain for {symbol} with expiry {nearest_expiry}"
#                                     )
#                                     d["option_chain_data"] = None

#                                 if option_contracts:
#                                     # Filter for the desired option type (CE/PE)
#                                     matching_contracts = [
#                                         contract
#                                         for contract in option_contracts
#                                         if contract.option_type == opt_type
#                                     ]

#                                     d["option_contracts_available"] = len(
#                                         matching_contracts
#                                     )

#                                     # Get ATM (At The Money) option contract
#                                     atm_contract = self._get_atm_contract(
#                                         matching_contracts, d.get("last_price", 0)
#                                     )

#                                     if atm_contract:
#                                         d["option_contract"] = {
#                                             "instrument_key": atm_contract.instrument_key,
#                                             "strike_price": atm_contract.strike_price,
#                                             "option_type": atm_contract.option_type,
#                                             "expiry": atm_contract.expiry,
#                                             "trading_symbol": atm_contract.trading_symbol,
#                                             "lot_size": atm_contract.lot_size,
#                                         }
#                                         logger.info(
#                                             f"Found ATM {opt_type} contract for {symbol}: Strike {atm_contract.strike_price}"
#                                         )
#                                     else:
#                                         logger.warning(
#                                             f"No ATM {opt_type} contract found for {symbol}"
#                                         )
#                                 else:
#                                     logger.warning(
#                                         f"No option contracts found for {symbol} with key {instrument_key}"
#                                     )

#                                     # Fallback: try to get contracts from local data using symbol
#                                     fallback_contracts = self.option_service._get_contracts_from_local_data(
#                                         symbol, db
#                                     )
#                                     if fallback_contracts:
#                                         matching_contracts = [
#                                             contract
#                                             for contract in fallback_contracts
#                                             if contract.option_type == opt_type
#                                         ]
#                                         d["option_contracts_available"] = len(
#                                             matching_contracts
#                                         )

#                                         atm_contract = self._get_atm_contract(
#                                             matching_contracts, d.get("last_price", 0)
#                                         )

#                                         if atm_contract:
#                                             d["option_contract"] = {
#                                                 "instrument_key": atm_contract.instrument_key,
#                                                 "strike_price": atm_contract.strike_price,
#                                                 "option_type": atm_contract.option_type,
#                                                 "expiry": atm_contract.expiry,
#                                                 "trading_symbol": atm_contract.trading_symbol,
#                                                 "lot_size": atm_contract.lot_size,
#                                             }
#                                             logger.info(
#                                                 f"Found fallback ATM {opt_type} contract for {symbol}: Strike {atm_contract.strike_price}"
#                                             )
#                         finally:
#                             db.close()

#                 except Exception as e:
#                     logger.warning(
#                         "Option chain fetch failed for %s: %s", d.get("symbol"), e
#                     )

#         # Since we're only selecting from 1 sector with 2 stocks, no need for final limit
#         # But keep the method for logging/validation
#         final_candidates = candidates if len(candidates) <= 2 else candidates[:2]

#         if len(final_candidates) != 2:
#             logger.warning(
#                 f"Expected 2 stocks, got {len(final_candidates)} from sector {top_sector}"
#             )

#         persisted = self._persist_selected(final_candidates)
#         elapsed_ms = (datetime.utcnow() - start).total_seconds() * 1000
#         logger.info(
#             "Selection complete: %d persisted in %.1f ms", len(persisted), elapsed_ms
#         )
#         return persisted

#     def _apply_final_stock_limit(
#         self, candidates: List[Dict[str, Any]]
#     ) -> List[Dict[str, Any]]:
#         """Apply final stock limit across all sectors based on strategy score"""
#         if len(candidates) <= self.max_total_stocks:
#             return candidates

#         logger.info(
#             f"Applying final limit: {len(candidates)} candidates → {self.max_total_stocks} stocks"
#         )

#         # Sort by composite score: strategy_score + selection_score
#         def get_composite_score(candidate):
#             strategy_score = float(candidate.get("strategy_score", 0))
#             price_change = abs(float(candidate.get("pct_change", 0)))
#             volume_score = (
#                 min(float(candidate.get("volume", 0)) / 1e5, 50)
#                 if candidate.get("volume")
#                 else 0
#             )
#             return strategy_score + price_change + volume_score

#         sorted_candidates = sorted(candidates, key=get_composite_score, reverse=True)
#         final_selection = sorted_candidates[: self.max_total_stocks]

#         selected_symbols = [c.get("symbol") for c in final_selection]
#         logger.info(
#             f"✅ Final selection limited to {len(final_selection)} stocks: {selected_symbols}"
#         )

#         return final_selection

#         # def _get_atm_contract(
#         #     self, contracts: List[], spot_price: float
#         # ) -> OptionContract:
#         #     """Get the At-The-Money (ATM) option contract closest to spot price"""
#         #     if not contracts or spot_price <= 0:
#         #         return None

#         # Find the contract with strike price closest to spot price
#         closest_contract = min(
#             contracts, key=lambda c: abs(c.strike_price - spot_price)
#         )

#         return closest_contract

#     def _get_user_trading_config(self, db: Session) -> Dict[str, Any]:
#         """Get user-specific trading configuration with fallback to global config"""
#         try:
#             config_data = {
#                 "trade_mode": TRADE_MODE,
#                 "default_qty": DEFAULT_QTY,
#                 "stop_loss_percent": 2.0,
#                 "target_percent": 4.0,
#                 "option_strategy": "BUY",
#                 "option_expiry_preference": "NEAREST",
#                 "enable_option_trading": True,
#             }

#             if self.user_id:
#                 # Try to get user-specific configuration
#                 user_config = (
#                     db.query(UserTradingConfig)
#                     .filter(UserTradingConfig.user_id == self.user_id)
#                     .first()
#                 )

#                 if user_config:
#                     # Override defaults with user-specific settings
#                     config_data.update(
#                         {
#                             "trade_mode": user_config.trade_mode or TRADE_MODE,
#                             "default_qty": user_config.default_qty or DEFAULT_QTY,
#                             "stop_loss_percent": user_config.stop_loss_percent or 2.0,
#                             "target_percent": user_config.target_percent or 4.0,
#                             "option_strategy": user_config.option_strategy or "BUY",
#                             "option_expiry_preference": user_config.option_expiry_preference
#                             or "NEAREST",
#                             "enable_option_trading": user_config.enable_option_trading,
#                         }
#                     )
#                     logger.info(
#                         f"Using user-specific trading config for user {self.user_id}"
#                     )
#                 else:
#                     logger.info(
#                         f"No user config found for user {self.user_id}, using defaults"
#                     )
#             else:
#                 logger.info("No user ID provided, using global config defaults")

#             return config_data

#         except Exception as e:
#             logger.error(f"Error getting user trading config: {e}")
#             return {
#                 "trade_mode": TRADE_MODE,
#                 "default_qty": DEFAULT_QTY,
#                 "stop_loss_percent": 2.0,
#                 "target_percent": 4.0,
#                 "option_strategy": "BUY",
#                 "option_expiry_preference": "NEAREST",
#                 "enable_option_trading": True,
#             }

#     # -- helpers are the same but included for completeness --
#     def _choose_top_sector_by_sentiment(
#         self, heatmap: Dict[str, float], sentiment: str
#     ) -> str:
#         """Choose the single TOP performing sector based on market sentiment"""
#         if not heatmap:
#             return None

#         items = list(heatmap.items())
#         s = sentiment.lower()

#         if s in ("bullish", "very_bullish"):
#             # In bullish market, pick the TOP performing sector (highest positive change)
#             items.sort(key=lambda x: x[1], reverse=True)
#             logger.info(f"Bullish market → selecting top performing sector")
#         elif s in ("bearish", "very_bearish"):
#             # In bearish market, pick the LEAST declining sector (highest in bearish context)
#             items.sort(
#                 key=lambda x: x[1], reverse=True
#             )  # Still highest, but in bearish market
#             logger.info(f"Bearish market → selecting least declining sector")
#         else:
#             # In neutral market, pick sector with highest volatility (absolute change)
#             items.sort(key=lambda x: abs(x[1]), reverse=True)
#             logger.info(f"Neutral market → selecting most volatile sector")

#         top_sector = items[0][0] if items else None
#         sector_performance = items[0][1] if items else 0

#         logger.info(
#             f"TOP sector selected: {top_sector} (performance: {sector_performance:.2f}%)"
#         )
#         return top_sector

#     def _choose_sectors(
#         self, heatmap: Dict[str, float], sentiment: str, top_n: int
#     ) -> List[str]:
#         """Legacy method - kept for compatibility"""
#         items = list(heatmap.items())
#         s = sentiment.lower()
#         if s in ("bullish", "very_bullish"):
#             items.sort(key=lambda x: x[1], reverse=True)
#         elif s in ("bearish", "very_bearish"):
#             items.sort(key=lambda x: x[1])
#         else:
#             items.sort(key=lambda x: abs(x[1]), reverse=True)
#         return [sec for sec, _ in items[:top_n]]

#     def _safe_get_stocks_by_sector(self, sector: str) -> List[Dict[str, Any]]:
#         try:
#             return self.analytics.get_stocks_by_sector(sector) or []
#         except Exception as e:
#             logger.exception("Error fetching stocks for sector %s: %s", sector, e)
#             return []

#     def _to_frame(self, list_of_dicts):
#         if _USE_POLARS:
#             try:
#                 return pl.DataFrame(list_of_dicts)
#             except Exception as e:
#                 logger.warning("Polars creation failed, falling back to pandas: %s", e)
#         try:
#             return pd.DataFrame(list_of_dicts)
#         except Exception as e:
#             logger.error("Pandas DataFrame creation failed: %s", e)
#             return None

#     def _ensure_pct_change(self, df):
#         if _USE_POLARS:
#             if "pct_change" not in df.columns:
#                 if "change_percent" in df.columns:
#                     df = df.with_columns(
#                         pl.col("change_percent").cast(pl.Float64).alias("pct_change")
#                     )
#                 else:
#                     df = df.with_columns(pl.lit(0.0).alias("pct_change"))
#             else:
#                 df = df.with_columns(pl.col("pct_change").cast(pl.Float64))
#             return df
#         else:
#             if "pct_change" not in df.columns:
#                 if "change_percent" in df.columns:
#                     df["pct_change"] = df["change_percent"].astype(float)
#                 else:
#                     df["pct_change"] = 0.0
#             else:
#                 df["pct_change"] = df["pct_change"].astype(float)
#             return df

#     def _select_midrange(self, df, limit: int):
#         n = len(df)
#         if n <= limit:
#             return df.slice(0, n) if _USE_POLARS else df.iloc[:n]
#         mid = n // 2
#         start = max(0, mid - (limit // 2))
#         if _USE_POLARS:
#             return df.slice(start, limit)
#         else:
#             return df.iloc[start : start + limit]

#     def _frame_to_dicts(self, df):
#         if _USE_POLARS:
#             return df.to_dicts()
#         else:
#             return df.to_dict(orient="records")

#     def _persist_selected(
#         self, candidates: List[Dict[str, Any]]
#     ) -> List[Dict[str, Any]]:
#         if not candidates:
#             return []
#         db: Session = self.db_session_factory()
#         persisted = []
#         try:
#             today = date.today()
#             db.query(SelectedStock).filter(
#                 SelectedStock.selection_date == today, SelectedStock.is_active == True
#             ).update({"is_active": False})
#             db.flush()
#             for c in candidates:
#                 instrument_key = c.get("instrument_key") or ""
#                 price = float(
#                     c.get("last_price") or c.get("price") or c.get("ltp") or 0.0
#                 )
#                 volume = int(c.get("volume") or 0)
#                 change_pct = float(
#                     c.get("pct_change") or c.get("change_percent") or 0.0
#                 )
#                 score = round(
#                     abs(change_pct)
#                     + (0 if volume == 0 else min(volume / 1e5, 50))
#                     + float(c.get("strategy_score", 0)),
#                     2,
#                 )

#                 row = SelectedStock(
#                     symbol=c.get("symbol"),
#                     instrument_key=instrument_key,
#                     selection_date=today,
#                     selection_score=score,
#                     selection_reason=c.get("selection_reason", ""),
#                     price_at_selection=price,
#                     volume_at_selection=volume,
#                     change_percent_at_selection=change_pct,
#                     sector=c.get("sector", "OTHER"),
#                     option_type=c.get("option_type"),
#                     option_contract=(
#                         json.dumps(c.get("option_contract"))
#                         if c.get("option_contract")
#                         else None
#                     ),
#                     option_contracts_available=c.get("option_contracts_available", 0),
#                     option_chain_data=(
#                         json.dumps(c.get("option_chain_data"))
#                         if c.get("option_chain_data")
#                         else None
#                     ),
#                     option_expiry_date=c.get("option_expiry_date"),
#                     option_expiry_dates=(
#                         json.dumps(c.get("option_expiry_dates"))
#                         if c.get("option_expiry_dates")
#                         else None
#                     ),
#                     score_breakdown=json.dumps(c),
#                     is_active=True,
#                     created_at=datetime.utcnow(),
#                     updated_at=datetime.utcnow(),
#                 )
#                 db.add(row)
#                 persisted.append(
#                     {
#                         "symbol": row.symbol,
#                         "instrument_key": row.instrument_key,
#                         "sector": row.sector,
#                         "selection_score": row.selection_score,
#                         "price_at_selection": row.price_at_selection,
#                         "option_type": row.option_type,
#                         "option_contracts_available": row.option_contracts_available,
#                         "option_expiry_date": row.option_expiry_date,
#                         "has_option_chain": row.option_chain_data is not None,
#                     }
#                 )
#             db.commit()
#             return persisted
#         except Exception as e:
#             db.rollback()
#             logger.exception("Error persisting selected stocks: %s", e)
#             return []
#         finally:
#             db.close()

#     def get_selected_stocks_with_options(
#         self, selection_date: date = None
#     ) -> List[Dict[str, Any]]:
#         """Get selected stocks with their option chain data"""
#         try:
#             if not selection_date:
#                 selection_date = date.today()

#             db = self.db_session_factory()
#             try:
#                 selected_stocks = (
#                     db.query(SelectedStock)
#                     .filter(
#                         SelectedStock.selection_date == selection_date,
#                         SelectedStock.is_active == True,
#                     )
#                     .all()
#                 )

#                 result = []
#                 for stock in selected_stocks:
#                     stock_data = {
#                         "symbol": stock.symbol,
#                         "instrument_key": stock.instrument_key,
#                         "sector": stock.sector,
#                         "selection_score": stock.selection_score,
#                         "selection_reason": stock.selection_reason,
#                         "price_at_selection": stock.price_at_selection,
#                         "option_type": stock.option_type,
#                         "option_contracts_available": stock.option_contracts_available,
#                         "option_expiry_date": stock.option_expiry_date,
#                         "selection_date": stock.selection_date.isoformat(),
#                         "created_at": (
#                             stock.created_at.isoformat() if stock.created_at else None
#                         ),
#                     }

#                     # Parse JSON fields
#                     if stock.option_contract:
#                         try:
#                             stock_data["option_contract"] = json.loads(
#                                 stock.option_contract
#                             )
#                         except json.JSONDecodeError:
#                             stock_data["option_contract"] = None

#                     if stock.option_chain_data:
#                         try:
#                             stock_data["option_chain_data"] = json.loads(
#                                 stock.option_chain_data
#                             )
#                         except json.JSONDecodeError:
#                             stock_data["option_chain_data"] = None

#                     if stock.option_expiry_dates:
#                         try:
#                             stock_data["option_expiry_dates"] = json.loads(
#                                 stock.option_expiry_dates
#                             )
#                         except json.JSONDecodeError:
#                             stock_data["option_expiry_dates"] = []

#                     if stock.score_breakdown:
#                         try:
#                             stock_data["score_breakdown"] = json.loads(
#                                 stock.score_breakdown
#                             )
#                         except json.JSONDecodeError:
#                             stock_data["score_breakdown"] = {}

#                     result.append(stock_data)

#                 logger.info(
#                     f"Retrieved {len(result)} selected stocks with option data for {selection_date}"
#                 )
#                 return result

#             finally:
#                 db.close()

#         except Exception as e:
#             logger.error(f"Error retrieving selected stocks with options: {e}")
#             return []

#     @staticmethod
#     def create_default_user_trading_config(
#         user_id: int, db: Session
#     ) -> UserTradingConfig:
#         """Create default trading configuration for a new user"""
#         try:
#             # Check if config already exists
#             existing_config = (
#                 db.query(UserTradingConfig)
#                 .filter(UserTradingConfig.user_id == user_id)
#                 .first()
#             )

#             if existing_config:
#                 logger.info(f"Trading config already exists for user {user_id}")
#                 return existing_config

#             # Create new default config
#             default_config = UserTradingConfig(
#                 user_id=user_id,
#                 trade_mode=TRADE_MODE,  # Default from global config
#                 default_qty=DEFAULT_QTY,  # Default from global config
#                 stop_loss_percent=2.0,
#                 target_percent=4.0,
#                 max_positions=3,
#                 risk_per_trade_percent=1.0,
#                 default_strategy="MOMENTUM",
#                 default_timeframe="5M",
#                 option_strategy="BUY",
#                 option_expiry_preference="NEAREST",
#                 enable_option_trading=True,
#                 enable_auto_square_off=True,
#                 enable_bracket_orders=False,
#                 enable_trailing_stop=False,
#                 enable_trade_notifications=True,
#                 enable_profit_loss_alerts=True,
#                 created_at=datetime.utcnow(),
#                 updated_at=datetime.utcnow(),
#             )

#             db.add(default_config)
#             db.commit()
#             db.refresh(default_config)

#             logger.info(f"Created default trading config for user {user_id}")
#             return default_config

#         except Exception as e:
#             db.rollback()
#             logger.error(
#                 f"Error creating default trading config for user {user_id}: {e}"
#             )
#             raise

#     @staticmethod
#     def get_user_trading_config(user_id: int, db: Session) -> Dict[str, Any]:
#         """Get user trading configuration as dictionary"""
#         try:
#             user_config = (
#                 db.query(UserTradingConfig)
#                 .filter(UserTradingConfig.user_id == user_id)
#                 .first()
#             )

#             if not user_config:
#                 # Create default config if none exists
#                 user_config = TradingStockSelector.create_default_user_trading_config(
#                     user_id, db
#                 )

#             return {
#                 "trade_mode": user_config.trade_mode,
#                 "default_qty": user_config.default_qty,
#                 "stop_loss_percent": user_config.stop_loss_percent,
#                 "target_percent": user_config.target_percent,
#                 "max_positions": user_config.max_positions,
#                 "risk_per_trade_percent": user_config.risk_per_trade_percent,
#                 "default_strategy": user_config.default_strategy,
#                 "default_timeframe": user_config.default_timeframe,
#                 "option_strategy": user_config.option_strategy,
#                 "option_expiry_preference": user_config.option_expiry_preference,
#                 "enable_option_trading": user_config.enable_option_trading,
#                 "enable_auto_square_off": user_config.enable_auto_square_off,
#                 "enable_bracket_orders": user_config.enable_bracket_orders,
#                 "enable_trailing_stop": user_config.enable_trailing_stop,
#                 "enable_trade_notifications": user_config.enable_trade_notifications,
#                 "enable_profit_loss_alerts": user_config.enable_profit_loss_alerts,
#             }

#         except Exception as e:
#             logger.error(f"Error getting user trading config for user {user_id}: {e}")
#             # Return default values if error occurs
#             return {
#                 "trade_mode": TRADE_MODE,
#                 "default_qty": DEFAULT_QTY,
#                 "stop_loss_percent": 2.0,
#                 "target_percent": 4.0,
#                 "max_positions": 3,
#                 "risk_per_trade_percent": 1.0,
#                 "default_strategy": "MOMENTUM",
#                 "default_timeframe": "5M",
#                 "option_strategy": "BUY",
#                 "option_expiry_preference": "NEAREST",
#                 "enable_option_trading": True,
#                 "enable_auto_square_off": True,
#                 "enable_bracket_orders": False,
#                 "enable_trailing_stop": False,
#                 "enable_trade_notifications": True,
#                 "enable_profit_loss_alerts": True,
#             }
