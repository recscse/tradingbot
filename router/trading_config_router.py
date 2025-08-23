# # router/trading_config_router.py
# """Trading Configuration Router - User Trading Preferences API"""

# from fastapi import APIRouter, Depends, HTTPException, status
# from sqlalchemy.orm import Session
# from typing import Dict, Any
# import logging

# from database.connection import get_db
# from database.models import UserTradingConfig
# from services.auth_service import get_current_user
# from services.trading_stock_selector import TradingStockSelector

# logger = logging.getLogger(__name__)

# router = APIRouter(prefix="/trading", tags=["Trading Configuration"])


# @router.get("/config")
# async def get_trading_config(
#     current_user=Depends(get_current_user), db: Session = Depends(get_db)
# ) -> Dict[str, Any]:
#     """Get user's trading configuration"""
#     try:
#         user_config = TradingStockSelector.get_user_trading_config(current_user.id, db)

#         logger.info(f"Retrieved trading config for user {current_user.id}")
#         return {"status": "success", "data": user_config}

#     except Exception as e:
#         logger.error(f"Error getting trading config for user {current_user.id}: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Error retrieving trading configuration",
#         )


# @router.post("/config")
# async def save_trading_config(
#     config_data: Dict[str, Any],
#     current_user=Depends(get_current_user),
#     db: Session = Depends(get_db),
# ) -> Dict[str, Any]:
#     """Save user's trading configuration"""
#     try:
#         # Get or create user config
#         user_config = (
#             db.query(UserTradingConfig)
#             .filter(UserTradingConfig.user_id == current_user.id)
#             .first()
#         )

#         if not user_config:
#             # Create new config
#             user_config = TradingStockSelector.create_default_user_trading_config(
#                 current_user.id, db
#             )

#         # Update configuration fields
#         for field, value in config_data.items():
#             if hasattr(user_config, field):
#                 setattr(user_config, field, value)

#         # Special validation for LIVE trading mode
#         if config_data.get("trade_mode") == "LIVE":
#             logger.warning(f"User {current_user.id} enabled LIVE trading mode")

#             # Additional validation for live trading
#             if not _validate_live_trading_requirements(current_user, db):
#                 raise HTTPException(
#                     status_code=status.HTTP_400_BAD_REQUEST,
#                     detail="Live trading requirements not met. Please ensure broker is connected and verified.",
#                 )

#         db.commit()
#         db.refresh(user_config)

#         logger.info(
#             f"Updated trading config for user {current_user.id}: mode={config_data.get('trade_mode')}"
#         )

#         return {
#             "status": "success",
#             "message": "Trading configuration saved successfully",
#             "data": {
#                 "trade_mode": user_config.trade_mode,
#                 "updated_at": (
#                     user_config.updated_at.isoformat()
#                     if user_config.updated_at
#                     else None
#                 ),
#             },
#         }

#     except HTTPException:
#         raise
#     except Exception as e:
#         db.rollback()
#         logger.error(f"Error saving trading config for user {current_user.id}: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Error saving trading configuration",
#         )


# @router.get("/config/reset")
# async def reset_trading_config(
#     current_user=Depends(get_current_user), db: Session = Depends(get_db)
# ) -> Dict[str, Any]:
#     """Reset user's trading configuration to defaults"""
#     try:
#         # Delete existing config
#         db.query(UserTradingConfig).filter(
#             UserTradingConfig.user_id == current_user.id
#         ).delete()

#         # Create new default config
#         default_config = TradingStockSelector.create_default_user_trading_config(
#             current_user.id, db
#         )

#         logger.info(f"Reset trading config to defaults for user {current_user.id}")

#         return {
#             "status": "success",
#             "message": "Trading configuration reset to defaults",
#             "data": TradingStockSelector.get_user_trading_config(current_user.id, db),
#         }

#     except Exception as e:
#         db.rollback()
#         logger.error(f"Error resetting trading config for user {current_user.id}: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Error resetting trading configuration",
#         )


# @router.get("/config/validate")
# async def validate_trading_config(
#     current_user=Depends(get_current_user), db: Session = Depends(get_db)
# ) -> Dict[str, Any]:
#     """Validate user's trading configuration and requirements"""
#     try:
#         user_config = TradingStockSelector.get_user_trading_config(current_user.id, db)

#         validation_results = {"is_valid": True, "warnings": [], "requirements": []}

#         # Check live trading requirements
#         if user_config.get("trade_mode") == "LIVE":
#             if not _validate_live_trading_requirements(current_user, db):
#                 validation_results["is_valid"] = False
#                 validation_results["requirements"].append(
#                     "Broker connection required for live trading"
#                 )

#             validation_results["warnings"].append(
#                 "LIVE trading mode enabled - real money will be used"
#             )

#         # Check risk management settings
#         if user_config.get("stop_loss_percent", 0) < 0.5:
#             validation_results["warnings"].append(
#                 "Very low stop loss percentage - high risk"
#             )

#         if user_config.get("risk_per_trade_percent", 0) > 3:
#             validation_results["warnings"].append(
#                 "High risk per trade - consider reducing"
#             )

#         return {"status": "success", "data": validation_results}

#     except Exception as e:
#         logger.error(f"Error validating trading config for user {current_user.id}: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Error validating trading configuration",
#         )


# def _validate_live_trading_requirements(user, db: Session) -> bool:
#     """Validate requirements for live trading"""
#     try:
#         from database.models import BrokerConfig

#         # Check if user has at least one active broker configuration
#         active_broker = (
#             db.query(BrokerConfig)
#             .filter(
#                 BrokerConfig.user_id == user.id,
#                 BrokerConfig.is_active == True,
#                 BrokerConfig.access_token.isnot(None),
#             )
#             .first()
#         )

#         return active_broker is not None

#     except Exception as e:
#         logger.error(f"Error validating live trading requirements: {e}")
#         return False


# @router.get("/mode/current")
# async def get_current_trading_mode(
#     current_user=Depends(get_current_user), db: Session = Depends(get_db)
# ) -> Dict[str, Any]:
#     """Get current trading mode for quick access"""
#     try:
#         user_config = TradingStockSelector.get_user_trading_config(current_user.id, db)

#         return {
#             "status": "success",
#             "data": {
#                 "trade_mode": user_config.get("trade_mode", "PAPER"),
#                 "is_live": user_config.get("trade_mode") == "LIVE",
#                 "default_qty": user_config.get("default_qty", 1),
#             },
#         }

#     except Exception as e:
#         logger.error(
#             f"Error getting current trading mode for user {current_user.id}: {e}"
#         )
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Error getting trading mode",
#         )
