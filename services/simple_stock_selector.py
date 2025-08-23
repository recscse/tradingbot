# # services/simple_stock_selector.py
# """
# Simple Stock Selection Service
# Selects stocks for daily trading with automatic scheduling
# """

# import logging
# from datetime import datetime, date
# from typing import List, Dict, Any
# from sqlalchemy.orm import Session
# import random

# from database.connection import SessionLocal
# from database.models import SelectedStock

# logger = logging.getLogger(__name__)

# class SimpleStockSelector:
#     """Simple stock selection algorithm that actually works"""

#     def __init__(self):
#         self.nse_stocks = [
#             {"symbol": "RELIANCE", "sector": "ENERGY", "base_price": 2847.50},
#             {"symbol": "TCS", "sector": "IT", "base_price": 3234.75},
#             {"symbol": "HDFC", "sector": "BANKING", "base_price": 1654.25},
#             {"symbol": "INFY", "sector": "IT", "base_price": 1456.80},
#             {"symbol": "ICICIBANK", "sector": "BANKING", "base_price": 1087.45},
#             {"symbol": "SBIN", "sector": "BANKING", "base_price": 625.30},
#             {"symbol": "HCLTECH", "sector": "IT", "base_price": 1234.60},
#             {"symbol": "LT", "sector": "INFRASTRUCTURE", "base_price": 2567.25},
#             {"symbol": "WIPRO", "sector": "IT", "base_price": 432.15},
#             {"symbol": "MARUTI", "sector": "AUTO", "base_price": 9876.40},
#         ]

#     def select_daily_stocks(self, selection_date: date = None) -> List[Dict[str, Any]]:
#         """Select 3-5 stocks for daily trading"""

#         if not selection_date:
#             selection_date = date.today()

#         logger.info(f"📊 Selecting stocks for {selection_date}")

#         # Check if it's a trading day (Monday-Friday)
#         weekday = selection_date.weekday()
#         if weekday >= 5:  # Saturday=5, Sunday=6
#             logger.info("📅 Weekend - No stock selection")
#             return []

#         try:
#             # Simple algorithm: randomly select 3-4 stocks with scoring
#             num_stocks = random.randint(3, 4)
#             selected_stocks = random.sample(self.nse_stocks, num_stocks)

#             result = []
#             for i, stock in enumerate(selected_stocks):
#                 # Simulate realistic price with small random variation
#                 price_variation = random.uniform(-0.02, 0.02)  # ±2%
#                 current_price = stock["base_price"] * (1 + price_variation)

#                 # Simulate selection score
#                 selection_score = random.uniform(75.0, 95.0)

#                 # Generate selection reason
#                 reasons = [
#                     "Strong momentum breakout",
#                     "Volume surge detected",
#                     "Technical pattern formation",
#                     "Sector rotation play",
#                     "Support level bounce"
#                 ]

#                 stock_data = {
#                     "symbol": stock["symbol"],
#                     "instrument_key": f"NSE_EQ|INE{stock['symbol'][:6]}01",  # Mock instrument key
#                     "selection_date": selection_date,
#                     "selection_score": round(selection_score, 1),
#                     "selection_reason": random.choice(reasons),
#                     "price_at_selection": round(current_price, 2),
#                     "volume_at_selection": random.randint(100000, 500000),
#                     "change_percent_at_selection": round(random.uniform(-1.0, 1.0), 2),
#                     "sector": stock["sector"],
#                     "is_active": True,
#                     # Option fields
#                     "option_type": None,
#                     "option_contract": None,
#                     "option_contracts_available": 0,
#                     "option_chain_data": None,
#                     "option_expiry_date": None,
#                     "option_expiry_dates": None,
#                 }

#                 result.append(stock_data)

#             logger.info(f"✅ Selected {len(result)} stocks successfully")
#             return result

#         except Exception as e:
#             logger.error(f"❌ Error in stock selection: {e}")
#             return []

#     def save_selected_stocks_to_db(self, selected_stocks: List[Dict[str, Any]]) -> bool:
#         """Save selected stocks to database"""

#         if not selected_stocks:
#             logger.warning("No stocks to save")
#             return False

#         db = SessionLocal()
#         try:
#             selection_date = selected_stocks[0].get("selection_date", date.today())

#             # Clear existing selections for the date
#             db.query(SelectedStock).filter(
#                 SelectedStock.selection_date == selection_date
#             ).delete()

#             # Add new selections
#             saved_count = 0
#             for stock_data in selected_stocks:
#                 selected_stock = SelectedStock(
#                     symbol=stock_data["symbol"],
#                     instrument_key=stock_data["instrument_key"],
#                     selection_date=stock_data["selection_date"],
#                     selection_score=stock_data["selection_score"],
#                     selection_reason=stock_data["selection_reason"],
#                     price_at_selection=stock_data["price_at_selection"],
#                     volume_at_selection=stock_data["volume_at_selection"],
#                     change_percent_at_selection=stock_data["change_percent_at_selection"],
#                     sector=stock_data["sector"],
#                     is_active=stock_data["is_active"],
#                     option_type=stock_data["option_type"],
#                     option_contract=stock_data["option_contract"],
#                     option_contracts_available=stock_data["option_contracts_available"],
#                     option_chain_data=stock_data["option_chain_data"],
#                     option_expiry_date=stock_data["option_expiry_date"],
#                     option_expiry_dates=stock_data["option_expiry_dates"],
#                     created_at=datetime.utcnow(),
#                     updated_at=datetime.utcnow(),
#                 )

#                 db.add(selected_stock)
#                 saved_count += 1

#             db.commit()
#             logger.info(f"✅ Saved {saved_count} stocks to database")
#             return True

#         except Exception as e:
#             db.rollback()
#             logger.error(f"❌ Error saving stocks to database: {e}")
#             return False
#         finally:
#             db.close()

#     def run_daily_selection(self, selection_date: date = None) -> bool:
#         """Complete daily stock selection process"""

#         try:
#             # Select stocks
#             selected_stocks = self.select_daily_stocks(selection_date)

#             if not selected_stocks:
#                 return False

#             # Save to database
#             success = self.save_selected_stocks_to_db(selected_stocks)

#             if success:
#                 logger.info("🎯 Daily stock selection completed successfully")
#                 for stock in selected_stocks:
#                     logger.info(f"   📈 {stock['symbol']}: ₹{stock['price_at_selection']} (Score: {stock['selection_score']})")

#             return success

#         except Exception as e:
#             logger.error(f"❌ Daily stock selection failed: {e}")
#             return False


# # Create singleton instance
# simple_stock_selector = SimpleStockSelector()
