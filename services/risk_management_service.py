from typing import Dict, Optional
import logging
from decimal import Decimal
from services.trading_execution.trade_analytics_service import trade_analytics_service
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class RiskManagement:
    def __init__(self):
        self.max_risk_per_trade = 1000  # ₹1000 per trade (fallback)
        self.max_portfolio_risk = 5000   # ₹5000 total risk
        self.max_positions = 5
        self.max_drawdown = 0.20  # 20% max drawdown
        self.trailing_sl_percent = 0.10  # 10% trailing stop loss
        
        # Kelly Criterion Settings
        self.kelly_fraction_multiplier = 0.5  # Use "Half-Kelly" for safety
        self.min_kelly_fraction = 0.01        # Minimum 1% of capital
        self.max_kelly_fraction = 0.10        # Maximum 10% of capital per trade

    def calculate_kelly_fraction(self, user_id: int, db: Session) -> float:
        """
        Calculate the Kelly Criterion fraction based on historical performance.
        Formula: f* = (p * b - q) / b
        p = Win Rate, b = Win/Loss Ratio, q = 1 - p
        """
        try:
            # Fetch overall performance metrics
            performance = trade_analytics_service.get_overall_performance(user_id, db)
            if not performance.get("success") or performance["metrics"]["total_trades"] < 10:
                logger.info(f"Insufficient trade history for user {user_id}. Using default risk.")
                return self.min_kelly_fraction

            metrics = performance["metrics"]
            p = metrics["win_rate"] / 100.0
            
            # b = Average Profit / Average Loss
            avg_win = metrics["average_profit"]
            avg_loss = metrics["average_loss"]
            
            if avg_loss == 0:
                return self.max_kelly_fraction
                
            b = avg_win / avg_loss
            q = 1 - p
            
            # Kelly Formula
            kelly_f = (p * b - q) / b if b > 0 else 0
            
            # Apply safety multiplier (Half-Kelly)
            safe_kelly = kelly_f * self.kelly_fraction_multiplier
            
            # Constraints
            final_fraction = max(self.min_kelly_fraction, min(safe_kelly, self.max_kelly_fraction))
            
            logger.info(f"Kelly Calculation for user {user_id}: WinRate={p:.2%}, W/L Ratio={b:.2f}, Kelly Fraction={final_fraction:.2%}")
            return final_fraction

        except Exception as e:
            logger.error(f"Error calculating Kelly fraction: {e}")
            return self.min_kelly_fraction

    def calculate_position_size(
        self, 
        option_price: float, 
        volatility: float, 
        available_capital: float = 100000.0,
        user_id: Optional[int] = None,
        db: Optional[Session] = None
    ) -> int:
        """
        Calculate safe position size using Kelly Criterion if historical data exists.
        """
        risk_adjusted_price = option_price * (1 + volatility)
        
        # Calculate risk amount based on Kelly or Fallback
        if user_id and db:
            kelly_fraction = self.calculate_kelly_fraction(user_id, db)
            risk_amount = available_capital * kelly_fraction
        else:
            risk_amount = self.max_risk_per_trade

        max_quantity = int(risk_amount / risk_adjusted_price)
        
        # Apply hard caps for safety
        final_quantity = min(max_quantity, 50)  # Cap at 50 lots
        
        logger.info(f"Position Sizing: Risk Amount={risk_amount:.2f}, Price={option_price}, Qty={final_quantity}")
        return final_quantity

    def validate_trade(self, current_positions: Dict, new_trade: Dict) -> bool:
        """Validate if new trade meets risk parameters"""
        # Check total risk
        total_risk = sum(pos['risk'] for pos in current_positions.values())
        if total_risk + new_trade['risk'] > self.max_portfolio_risk:
            return False
            
        # Check number of positions
        if len(current_positions) >= self.max_positions:
            return False
            
        # Check correlation with existing positions
        if self._check_correlation(current_positions, new_trade):
            return False
            
        return True

    def _check_correlation(self, current_positions: Dict, new_trade: Dict) -> bool:
        """Check if new trade is highly correlated with existing positions"""
        # Implement correlation check logic
        return False