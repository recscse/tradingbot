"""
Margin-Aware Trading Service
Integrates real-time margin data with trading decisions
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session

from database.models import BrokerConfig, User
from services.broker_funds_sync_service import broker_funds_sync_service

logger = logging.getLogger(__name__)


class MarginAwareTradingService:
    """
    Trading service that uses real-time margin data for intelligent position sizing
    and risk management during live trading
    """

    def __init__(self, db: Session):
        self.db = db
        self.max_margin_utilization = 0.8  # 80% max utilization
        self.risk_per_trade = 0.02  # 2% of available margin per trade

    def calculate_position_size(
        self, 
        user_id: int, 
        stock_price: float, 
        broker_name: str = None,
        risk_percentage: float = None
    ) -> Dict[str, Any]:
        """
        Calculate optimal position size based on available margin
        
        Args:
            user_id: User ID
            stock_price: Current stock price
            broker_name: Specific broker to use (optional)
            risk_percentage: Custom risk percentage (optional)
            
        Returns:
            Dict with position sizing recommendations
        """
        try:
            # Get current margin status
            margin_check = broker_funds_sync_service.can_place_trade(user_id, 0, broker_name)
            
            if not margin_check["can_trade"]:
                return {
                    "can_trade": False,
                    "reason": margin_check["reason"],
                    "recommended_quantity": 0,
                    "required_margin": 0,
                    "available_margin": margin_check["available_margin"]
                }

            available_margin = margin_check["available_margin"]
            risk_pct = risk_percentage or self.risk_per_trade

            # Calculate maximum position size based on margin limits
            max_margin_per_trade = available_margin * risk_pct
            
            # Estimate required margin (simplified - actual calculation depends on broker)
            # For equity: ~20% of stock value, for F&O: depends on contract
            estimated_margin_per_share = stock_price * 0.2  # 20% margin requirement
            
            if estimated_margin_per_share <= 0:
                return {
                    "can_trade": False,
                    "reason": "Invalid stock price",
                    "recommended_quantity": 0
                }

            # Calculate recommended quantity
            max_quantity = int(max_margin_per_trade / estimated_margin_per_share)
            
            # Ensure we don't exceed margin limits
            recommended_quantity = min(max_quantity, 1000)  # Cap at 1000 shares for safety
            
            required_margin = recommended_quantity * estimated_margin_per_share

            return {
                "can_trade": True,
                "recommended_quantity": recommended_quantity,
                "required_margin": required_margin,
                "available_margin": available_margin,
                "margin_utilization_after_trade": (required_margin / available_margin) * 100,
                "risk_percentage": risk_pct * 100,
                "stock_price": stock_price,
                "broker_recommendation": margin_check.get("broker_name"),
                "safety_checks": self._get_safety_checks(required_margin, available_margin)
            }

        except Exception as e:
            logger.error(f"Error calculating position size for user {user_id}: {e}")
            return {
                "can_trade": False,
                "reason": f"Error in position calculation: {str(e)}",
                "recommended_quantity": 0
            }

    def validate_trade_order(
        self, 
        user_id: int, 
        quantity: int, 
        stock_price: float,
        order_type: str = "BUY",
        broker_name: str = None
    ) -> Dict[str, Any]:
        """
        Validate if a trade order can be placed based on current margins
        
        Returns:
            Dict with validation results and recommendations
        """
        try:
            # Calculate required margin for this order
            estimated_margin = quantity * stock_price * 0.2  # Simplified calculation
            
            # Check if user has sufficient margin
            margin_check = broker_funds_sync_service.can_place_trade(
                user_id, estimated_margin, broker_name
            )

            if not margin_check["can_trade"]:
                return {
                    "valid": False,
                    "reason": margin_check["reason"],
                    "required_margin": estimated_margin,
                    "available_margin": margin_check["available_margin"],
                    "suggested_quantity": self._suggest_alternative_quantity(
                        margin_check["available_margin"], stock_price
                    )
                }

            # Additional safety checks
            utilization_after = margin_check.get("utilization_after", 0)
            
            warnings = []
            if utilization_after > 90:
                warnings.append("High margin utilization (>90%) - consider reducing position size")
            elif utilization_after > 70:
                warnings.append("Moderate margin utilization (>70%) - monitor closely")

            return {
                "valid": True,
                "required_margin": estimated_margin,
                "available_margin": margin_check["available_margin"],
                "margin_after_trade": margin_check["margin_after_trade"],
                "utilization_after": utilization_after,
                "broker_id": margin_check["broker_id"],
                "broker_name": margin_check["broker_name"],
                "warnings": warnings,
                "order_details": {
                    "quantity": quantity,
                    "price": stock_price,
                    "order_type": order_type,
                    "estimated_value": quantity * stock_price
                }
            }

        except Exception as e:
            logger.error(f"Error validating trade order for user {user_id}: {e}")
            return {
                "valid": False,
                "reason": f"Validation error: {str(e)}"
            }

    def get_trading_limits(self, user_id: int) -> Dict[str, Any]:
        """
        Get current trading limits based on available margin
        """
        try:
            margin_summary = broker_funds_sync_service.get_user_margin_summary(user_id)
            
            if "error" in margin_summary:
                return {"error": margin_summary["error"]}

            free_margin = margin_summary["total_free_margin"]
            utilization = margin_summary["overall_utilization"]

            # Calculate trading limits
            max_trade_value = free_margin * self.risk_per_trade
            max_daily_trades = min(10, int(free_margin / (max_trade_value * 0.2)))  # Max 10 trades per day

            # Adjust limits based on current utilization
            if utilization > 80:
                max_trade_value *= 0.5  # Reduce by 50% if high utilization
                max_daily_trades = min(3, max_daily_trades)
            elif utilization > 60:
                max_trade_value *= 0.7  # Reduce by 30%
                max_daily_trades = min(5, max_daily_trades)

            return {
                "max_trade_value": max_trade_value,
                "max_daily_trades": max_daily_trades,
                "current_utilization": utilization,
                "free_margin": free_margin,
                "risk_level": self._get_risk_level(utilization),
                "recommendations": self._get_trading_recommendations(utilization),
                "margin_summary": margin_summary
            }

        except Exception as e:
            logger.error(f"Error getting trading limits for user {user_id}: {e}")
            return {"error": str(e)}

    def monitor_margin_during_trade(self, user_id: int, trade_id: str) -> Dict[str, Any]:
        """
        Monitor margin levels during an active trade
        Used for stop-loss and risk management
        """
        try:
            margin_summary = broker_funds_sync_service.get_user_margin_summary(user_id)
            
            if "error" in margin_summary:
                return {"status": "error", "message": margin_summary["error"]}

            utilization = margin_summary["overall_utilization"]
            free_margin = margin_summary["total_free_margin"]

            # Determine actions based on margin levels
            if utilization > 95:
                return {
                    "status": "critical",
                    "action": "close_positions",
                    "message": "Critical margin level - close positions immediately",
                    "utilization": utilization,
                    "free_margin": free_margin
                }
            elif utilization > 85:
                return {
                    "status": "warning",
                    "action": "reduce_positions",
                    "message": "High margin utilization - consider reducing positions",
                    "utilization": utilization,
                    "free_margin": free_margin
                }
            elif utilization > 70:
                return {
                    "status": "caution",
                    "action": "monitor_closely",
                    "message": "Moderate margin utilization - monitor closely",
                    "utilization": utilization,
                    "free_margin": free_margin
                }
            else:
                return {
                    "status": "safe",
                    "action": "continue",
                    "message": "Margin levels are safe",
                    "utilization": utilization,
                    "free_margin": free_margin
                }

        except Exception as e:
            logger.error(f"Error monitoring margin for trade {trade_id}: {e}")
            return {"status": "error", "message": str(e)}

    def _suggest_alternative_quantity(self, available_margin: float, stock_price: float) -> int:
        """Suggest alternative quantity based on available margin"""
        if available_margin <= 0 or stock_price <= 0:
            return 0
        
        estimated_margin_per_share = stock_price * 0.2
        max_affordable = int((available_margin * 0.5) / estimated_margin_per_share)  # Use 50% of available
        return max(0, max_affordable)

    def _get_safety_checks(self, required_margin: float, available_margin: float) -> List[str]:
        """Get list of safety check results"""
        checks = []
        
        utilization = (required_margin / available_margin) * 100 if available_margin > 0 else 100
        
        if utilization < 30:
            checks.append("✅ Low margin utilization - Safe to trade")
        elif utilization < 60:
            checks.append("⚠️ Moderate margin utilization - Monitor position")
        else:
            checks.append("🚨 High margin utilization - High risk")

        if available_margin > required_margin * 3:
            checks.append("✅ Sufficient margin buffer available")
        else:
            checks.append("⚠️ Limited margin buffer - Be cautious")

        return checks

    def _get_risk_level(self, utilization: float) -> str:
        """Get risk level based on margin utilization"""
        if utilization < 30:
            return "LOW"
        elif utilization < 60:
            return "MEDIUM"
        elif utilization < 80:
            return "HIGH"
        else:
            return "CRITICAL"

    def _get_trading_recommendations(self, utilization: float) -> List[str]:
        """Get trading recommendations based on margin utilization"""
        recommendations = []
        
        if utilization < 30:
            recommendations.append("Safe to take new positions")
            recommendations.append("Consider scaling up successful strategies")
        elif utilization < 60:
            recommendations.append("Be selective with new positions")
            recommendations.append("Monitor existing positions closely")
        elif utilization < 80:
            recommendations.append("Avoid new positions unless high-confidence trades")
            recommendations.append("Consider closing some positions to free up margin")
        else:
            recommendations.append("Stop taking new positions immediately")
            recommendations.append("Close positions to reduce margin utilization")
            recommendations.append("Review risk management strategy")

        return recommendations

    async def sync_and_calculate(self, user_id: int, stock_price: float) -> Dict[str, Any]:
        """
        Force sync margin data and then calculate position size
        Use this for critical trading decisions
        """
        try:
            # Force sync user's broker data
            sync_result = await broker_funds_sync_service.force_sync_user_brokers(user_id)
            
            if sync_result["failed_brokers"] > 0:
                logger.warning(f"Some brokers failed to sync for user {user_id}")

            # Calculate position size with fresh data
            position_calc = self.calculate_position_size(user_id, stock_price)
            
            return {
                "sync_result": sync_result,
                "position_calculation": position_calc,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error in sync_and_calculate for user {user_id}: {e}")
            return {"error": str(e)}


# Helper function for easy integration
def get_margin_aware_trading_service(db: Session) -> MarginAwareTradingService:
    """Get instance of MarginAwareTradingService"""
    return MarginAwareTradingService(db)