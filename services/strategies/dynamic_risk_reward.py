"""
Dynamic Risk & Reward Management - Phase 3 Implementation

Advanced position sizing and risk management for Fibonacci + EMA strategy with:
- Account-based position sizing (2% risk per trade maximum)
- Dynamic Fibonacci-based stop losses
- Trailing stop algorithms using Fibonacci levels
- Risk-reward optimization (1.5:1 minimum, 3:1 maximum)
- Portfolio heat management
- Emergency risk controls

Key Features:
- Options premium-based position sizing
- Fibonacci level trailing stops
- Dynamic target adjustments
- Portfolio correlation risk management
- Real-time P&L monitoring
"""

import numpy as np
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
import asyncio

logger = logging.getLogger(__name__)

@dataclass
class PositionSize:
    """Position sizing recommendation"""
    recommended_lots: int
    max_lots_allowed: int
    risk_amount: float
    risk_percentage: float
    position_value: float
    margin_required: float
    max_loss_amount: float
    confidence_adjustment: float

@dataclass
class RiskRewardProfile:
    """Complete risk-reward profile for a trade"""
    entry_price: float
    stop_loss: float
    target_1: float
    target_2: float
    risk_reward_ratio: float
    max_risk_amount: float
    potential_reward_1: float
    potential_reward_2: float
    
    # Dynamic adjustments
    trailing_stop: Optional[float] = None
    breakeven_level: Optional[float] = None
    partial_exit_level: Optional[float] = None
    
    # Fibonacci levels for management
    fibonacci_levels: Dict[str, float] = None
    key_support_resistance: List[float] = None

class DynamicRiskReward:
    """
    Dynamic Risk & Reward Management System
    
    Handles all aspects of position sizing, risk management, and reward optimization
    for the Fibonacci + EMA strategy with real-time adjustments.
    """
    
    def __init__(self, account_balance: float = 100000):
        self.account_balance = account_balance
        self.max_risk_per_trade = 0.02  # 2% maximum risk per trade
        self.max_portfolio_risk = 0.10  # 10% maximum total portfolio risk
        self.min_risk_reward_ratio = 1.5
        self.max_risk_reward_ratio = 3.0
        
        # Position sizing configuration
        self.position_config = {
            'min_lot_size': 1,
            'max_lot_size': 10,
            'option_premium_buffer': 0.10,  # 10% buffer for option premium fluctuations
            'margin_safety_factor': 1.2,    # 20% margin safety buffer
            'confidence_scaling': True,      # Scale position size by signal confidence
        }
        
        # Risk management rules
        self.risk_rules = {
            'max_correlated_positions': 3,   # Max positions in correlated stocks
            'sector_concentration_limit': 0.25,  # Max 25% of portfolio in one sector
            'daily_loss_limit': 0.05,       # 5% daily loss limit
            'consecutive_loss_limit': 3,    # Max 3 consecutive losses before reducing size
        }
        
        # Active positions tracking
        self.active_positions: Dict[str, Dict] = {}
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        
        logger.info(f"✅ DynamicRiskReward initialized with account balance: ₹{account_balance:,.2f}")
    
    async def calculate_position_size(self, signal_strength: float, entry_price: float, 
                                    stop_loss: float, option_premium: float, 
                                    lot_size: int = 1, symbol: str = "") -> PositionSize:
        """
        Calculate optimal position size based on risk management rules
        
        Args:
            signal_strength: Signal confidence (0-100)
            entry_price: Entry price of underlying
            stop_loss: Stop loss level
            option_premium: Current option premium
            lot_size: Contract lot size
            symbol: Symbol for correlation checking
            
        Returns:
            PositionSize object with recommendations
        """
        try:
            # Calculate base risk amount
            base_risk_amount = self.account_balance * self.max_risk_per_trade
            
            # Adjust risk based on signal strength and consecutive losses
            confidence_factor = signal_strength / 100
            loss_adjustment = max(0.5, 1 - (self.consecutive_losses * 0.15))
            
            adjusted_risk_amount = base_risk_amount * confidence_factor * loss_adjustment
            
            # For options, risk is the premium paid (max loss)
            risk_per_lot = option_premium * lot_size
            
            if risk_per_lot <= 0:
                logger.warning(f"❌ Invalid risk per lot: {risk_per_lot}")
                return self._create_zero_position()
            
            # Calculate recommended lot size
            recommended_lots = int(adjusted_risk_amount / risk_per_lot)
            
            # Apply position sizing constraints
            recommended_lots = max(self.position_config['min_lot_size'], 
                                 min(recommended_lots, self.position_config['max_lot_size']))
            
            # Check portfolio risk limits
            max_lots_by_portfolio_risk = await self._check_portfolio_risk_limits(
                risk_per_lot, symbol
            )
            
            final_lots = min(recommended_lots, max_lots_by_portfolio_risk)
            
            # Calculate position metrics
            total_position_value = option_premium * lot_size * final_lots
            total_risk_amount = total_position_value  # Max loss for options
            risk_percentage = (total_risk_amount / self.account_balance) * 100
            
            # Estimate margin requirements (for options)
            margin_required = self._calculate_option_margin(
                entry_price, option_premium, lot_size, final_lots
            )
            
            return PositionSize(
                recommended_lots=final_lots,
                max_lots_allowed=max_lots_by_portfolio_risk,
                risk_amount=total_risk_amount,
                risk_percentage=risk_percentage,
                position_value=total_position_value,
                margin_required=margin_required,
                max_loss_amount=total_risk_amount,
                confidence_adjustment=confidence_factor
            )
            
        except Exception as e:
            logger.error(f"❌ Position size calculation failed: {e}")
            return self._create_zero_position()
    
    def calculate_fibonacci_stop_loss(self, fibonacci_levels: Dict[str, float], 
                                    signal_type: str, entry_price: float) -> Dict[str, Any]:
        """
        Calculate dynamic stop loss using Fibonacci levels
        
        Args:
            fibonacci_levels: Dictionary of Fibonacci levels
            signal_type: 'BUY_CE' or 'BUY_PE'
            entry_price: Entry price
            
        Returns:
            Dict with stop loss recommendations
        """
        try:
            if signal_type == 'BUY_CE':
                # For bullish trades, stop loss below key Fibonacci support
                candidates = [
                    ('fib_61_8', fibonacci_levels.get('fib_61_8', 0)),
                    ('fib_78_6', fibonacci_levels.get('fib_78_6', 0)),
                    ('swing_low', fibonacci_levels.get('swing_low', 0))
                ]
                
                # Choose the highest level below entry price
                valid_stops = [(name, level) for name, level in candidates if level < entry_price and level > 0]
                
                if valid_stops:
                    stop_name, stop_level = max(valid_stops, key=lambda x: x[1])
                    # Add small buffer
                    final_stop = stop_level * 0.995  # 0.5% buffer below
                else:
                    # Fallback: 2% below entry
                    stop_name, final_stop = 'fallback_2%', entry_price * 0.98
                
            else:  # BUY_PE
                # For bearish trades, stop loss above key Fibonacci resistance
                candidates = [
                    ('fib_38_2', fibonacci_levels.get('fib_38_2', 0)),
                    ('fib_23_6', fibonacci_levels.get('fib_23_6', 0)),
                    ('swing_high', fibonacci_levels.get('swing_high', 0))
                ]
                
                # Choose the lowest level above entry price
                valid_stops = [(name, level) for name, level in candidates if level > entry_price]
                
                if valid_stops:
                    stop_name, stop_level = min(valid_stops, key=lambda x: x[1])
                    # Add small buffer
                    final_stop = stop_level * 1.005  # 0.5% buffer above
                else:
                    # Fallback: 2% above entry
                    stop_name, final_stop = 'fallback_2%', entry_price * 1.02
            
            return {
                'stop_loss': round(final_stop, 2),
                'stop_level_name': stop_name,
                'stop_reason': f'Fibonacci {stop_name} level with safety buffer',
                'risk_percentage': abs((final_stop - entry_price) / entry_price) * 100
            }
            
        except Exception as e:
            logger.error(f"❌ Fibonacci stop loss calculation failed: {e}")
            # Fallback stop loss
            fallback_stop = entry_price * (0.98 if signal_type == 'BUY_CE' else 1.02)
            return {
                'stop_loss': round(fallback_stop, 2),
                'stop_level_name': 'fallback',
                'stop_reason': 'Fallback 2% stop loss',
                'risk_percentage': 2.0
            }
    
    def calculate_dynamic_targets(self, fibonacci_levels: Dict[str, float], 
                                signal_type: str, entry_price: float, 
                                stop_loss: float) -> Dict[str, Any]:
        """
        Calculate dynamic profit targets using Fibonacci extensions
        
        Args:
            fibonacci_levels: Dictionary of Fibonacci levels
            signal_type: 'BUY_CE' or 'BUY_PE'
            entry_price: Entry price
            stop_loss: Stop loss level
            
        Returns:
            Dict with target levels and risk-reward ratios
        """
        try:
            risk_amount = abs(entry_price - stop_loss)
            swing_range = abs(fibonacci_levels.get('swing_high', entry_price) - 
                           fibonacci_levels.get('swing_low', entry_price))
            
            if signal_type == 'BUY_CE':
                # Bullish targets using Fibonacci extensions
                
                # Target 1: Conservative (1.618 extension or minimum R:R)
                fib_extension_1 = entry_price + (swing_range * 0.618)
                risk_reward_target_1 = entry_price + (risk_amount * self.min_risk_reward_ratio)
                target_1 = max(fib_extension_1, risk_reward_target_1)
                
                # Target 2: Aggressive (2.618 extension or maximum R:R)
                fib_extension_2 = entry_price + (swing_range * 1.000)
                risk_reward_target_2 = entry_price + (risk_amount * self.max_risk_reward_ratio)
                target_2 = max(fib_extension_2, risk_reward_target_2)
                
                # Target 3: Moonshot (3.618 extension)
                target_3 = entry_price + (swing_range * 1.618)
                
            else:  # BUY_PE
                # Bearish targets using Fibonacci extensions
                
                # Target 1: Conservative
                fib_extension_1 = entry_price - (swing_range * 0.618)
                risk_reward_target_1 = entry_price - (risk_amount * self.min_risk_reward_ratio)
                target_1 = min(fib_extension_1, risk_reward_target_1)
                
                # Target 2: Aggressive
                fib_extension_2 = entry_price - (swing_range * 1.000)
                risk_reward_target_2 = entry_price - (risk_amount * self.max_risk_reward_ratio)
                target_2 = min(fib_extension_2, risk_reward_target_2)
                
                # Target 3: Moonshot
                target_3 = entry_price - (swing_range * 1.618)
            
            # Calculate risk-reward ratios
            reward_1 = abs(target_1 - entry_price)
            reward_2 = abs(target_2 - entry_price)
            reward_3 = abs(target_3 - entry_price)
            
            rr_1 = reward_1 / risk_amount if risk_amount > 0 else 0
            rr_2 = reward_2 / risk_amount if risk_amount > 0 else 0
            rr_3 = reward_3 / risk_amount if risk_amount > 0 else 0
            
            return {
                'target_1': round(target_1, 2),
                'target_2': round(target_2, 2),
                'target_3': round(target_3, 2),
                'risk_reward_1': round(rr_1, 2),
                'risk_reward_2': round(rr_2, 2),
                'risk_reward_3': round(rr_3, 2),
                'reward_amounts': {
                    'target_1': round(reward_1, 2),
                    'target_2': round(reward_2, 2),
                    'target_3': round(reward_3, 2)
                },
                'exit_strategy': {
                    'partial_exit_1': 50,  # Exit 50% at target 1
                    'partial_exit_2': 75,  # Exit 75% at target 2
                    'final_exit': 100      # Exit remaining at target 3 or trailing stop
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Dynamic targets calculation failed: {e}")
            # Fallback targets
            fallback_reward = risk_amount * 2  # 1:2 R:R
            if signal_type == 'BUY_CE':
                target_1 = entry_price + fallback_reward
                target_2 = entry_price + (fallback_reward * 1.5)
            else:
                target_1 = entry_price - fallback_reward
                target_2 = entry_price - (fallback_reward * 1.5)
            
            return {
                'target_1': round(target_1, 2),
                'target_2': round(target_2, 2),
                'target_3': round(target_2 * 1.2, 2),
                'risk_reward_1': 2.0,
                'risk_reward_2': 3.0,
                'risk_reward_3': 3.6
            }
    
    async def fibonacci_trailing_stop(self, position: Dict[str, Any], 
                                    current_price: float, fibonacci_levels: Dict[str, float]) -> Dict[str, Any]:
        """
        Dynamic trailing stop using Fibonacci levels
        
        Args:
            position: Current position data
            current_price: Current market price
            fibonacci_levels: Current Fibonacci levels
            
        Returns:
            Dict with updated trailing stop information
        """
        try:
            entry_price = position.get('entry_price', 0)
            signal_type = position.get('signal_type', 'BUY_CE')
            current_stop = position.get('current_stop_loss', position.get('initial_stop_loss', 0))
            
            # Calculate profit percentage
            if signal_type == 'BUY_CE':
                profit_pct = ((current_price - entry_price) / entry_price) * 100
            else:
                profit_pct = ((entry_price - current_price) / entry_price) * 100
            
            new_trailing_stop = current_stop
            trailing_reason = "No change"
            
            if profit_pct > 15:  # 15% profit - aggressive trailing
                if signal_type == 'BUY_CE':
                    # Trail to Fibonacci 38.2% from current high
                    recent_high = max(current_price, position.get('highest_price', current_price))
                    fib_trail_level = fibonacci_levels.get('fib_38_2', recent_high * 0.95)
                    new_trailing_stop = max(current_stop, min(fib_trail_level, recent_high * 0.97))
                    trailing_reason = "15%+ profit - Fibonacci 38.2% trail"
                else:
                    # Trail to Fibonacci 61.8% from current low
                    recent_low = min(current_price, position.get('lowest_price', current_price))
                    fib_trail_level = fibonacci_levels.get('fib_61_8', recent_low * 1.05)
                    new_trailing_stop = min(current_stop, max(fib_trail_level, recent_low * 1.03))
                    trailing_reason = "15%+ profit - Fibonacci 61.8% trail"
                    
            elif profit_pct > 8:  # 8% profit - moderate trailing
                if signal_type == 'BUY_CE':
                    # Trail to breakeven + 2%
                    breakeven_plus = entry_price * 1.02
                    new_trailing_stop = max(current_stop, breakeven_plus)
                    trailing_reason = "8%+ profit - Breakeven + 2% trail"
                else:
                    # Trail to breakeven - 2%
                    breakeven_minus = entry_price * 0.98
                    new_trailing_stop = min(current_stop, breakeven_minus)
                    trailing_reason = "8%+ profit - Breakeven - 2% trail"
                    
            elif profit_pct > 4:  # 4% profit - conservative trailing
                if signal_type == 'BUY_CE':
                    # Trail to breakeven
                    new_trailing_stop = max(current_stop, entry_price)
                    trailing_reason = "4%+ profit - Breakeven trail"
                else:
                    # Trail to breakeven
                    new_trailing_stop = min(current_stop, entry_price)
                    trailing_reason = "4%+ profit - Breakeven trail"
            
            # Update position tracking
            if signal_type == 'BUY_CE':
                position['highest_price'] = max(current_price, position.get('highest_price', current_price))
            else:
                position['lowest_price'] = min(current_price, position.get('lowest_price', current_price))
            
            stop_moved = new_trailing_stop != current_stop
            
            return {
                'new_stop_loss': round(new_trailing_stop, 2),
                'stop_moved': stop_moved,
                'trailing_reason': trailing_reason,
                'profit_percentage': round(profit_pct, 2),
                'distance_to_stop': abs(current_price - new_trailing_stop),
                'stop_risk_pct': abs((new_trailing_stop - current_price) / current_price) * 100
            }
            
        except Exception as e:
            logger.error(f"❌ Trailing stop calculation failed: {e}")
            return {
                'new_stop_loss': current_stop,
                'stop_moved': False,
                'trailing_reason': f'Error: {str(e)}',
                'profit_percentage': 0,
                'distance_to_stop': 0,
                'stop_risk_pct': 0
            }
    
    async def validate_risk_before_trade(self, symbol: str, risk_amount: float, 
                                       sector: str = "") -> Dict[str, Any]:
        """
        Validate if trade meets all risk management criteria
        
        Args:
            symbol: Symbol to trade
            risk_amount: Proposed risk amount
            sector: Sector of the stock
            
        Returns:
            Dict with validation results and recommendations
        """
        try:
            validation_results = {
                'approved': True,
                'risk_checks': [],
                'warnings': [],
                'recommendations': []
            }
            
            # Check 1: Single trade risk limit
            risk_pct = (risk_amount / self.account_balance) * 100
            if risk_pct > self.max_risk_per_trade * 100:
                validation_results['approved'] = False
                validation_results['risk_checks'].append(
                    f"❌ Trade risk {risk_pct:.2f}% exceeds limit {self.max_risk_per_trade*100}%"
                )
            else:
                validation_results['risk_checks'].append(
                    f"✅ Trade risk {risk_pct:.2f}% within limit"
                )
            
            # Check 2: Daily loss limit
            daily_loss_pct = abs(self.daily_pnl / self.account_balance) * 100
            if self.daily_pnl < 0 and daily_loss_pct > self.risk_rules['daily_loss_limit'] * 100:
                validation_results['approved'] = False
                validation_results['risk_checks'].append(
                    f"❌ Daily loss {daily_loss_pct:.2f}% exceeds limit"
                )
            
            # Check 3: Portfolio heat
            total_risk = sum([pos.get('risk_amount', 0) for pos in self.active_positions.values()])
            portfolio_risk_pct = ((total_risk + risk_amount) / self.account_balance) * 100
            
            if portfolio_risk_pct > self.max_portfolio_risk * 100:
                validation_results['approved'] = False
                validation_results['risk_checks'].append(
                    f"❌ Portfolio risk {portfolio_risk_pct:.2f}% would exceed {self.max_portfolio_risk*100}%"
                )
            
            # Check 4: Consecutive losses
            if self.consecutive_losses >= self.risk_rules['consecutive_loss_limit']:
                validation_results['warnings'].append(
                    f"⚠️ {self.consecutive_losses} consecutive losses - consider reducing size"
                )
                validation_results['recommendations'].append("Reduce position size by 50%")
            
            # Check 5: Correlation risk
            correlated_positions = await self._count_correlated_positions(symbol)
            if correlated_positions >= self.risk_rules['max_correlated_positions']:
                validation_results['warnings'].append(
                    f"⚠️ {correlated_positions} correlated positions already active"
                )
                validation_results['recommendations'].append("Consider diversification")
            
            # Check 6: Sector concentration
            if sector:
                sector_exposure = await self._calculate_sector_exposure(sector)
                if sector_exposure > self.risk_rules['sector_concentration_limit']:
                    validation_results['warnings'].append(
                        f"⚠️ {sector} sector exposure {sector_exposure*100:.1f}% high"
                    )
            
            return validation_results
            
        except Exception as e:
            logger.error(f"❌ Risk validation failed: {e}")
            return {
                'approved': False,
                'risk_checks': [f"❌ Validation error: {str(e)}"],
                'warnings': [],
                'recommendations': ['Manual risk review required']
            }
    
    def update_position(self, symbol: str, position_data: Dict[str, Any]):
        """Update active position tracking"""
        try:
            self.active_positions[symbol] = position_data
            logger.debug(f"✅ Updated position for {symbol}")
        except Exception as e:
            logger.error(f"❌ Position update failed for {symbol}: {e}")
    
    def close_position(self, symbol: str, pnl: float):
        """Close position and update tracking"""
        try:
            if symbol in self.active_positions:
                del self.active_positions[symbol]
            
            self.daily_pnl += pnl
            
            if pnl < 0:
                self.consecutive_losses += 1
            else:
                self.consecutive_losses = 0  # Reset on profitable trade
            
            logger.info(f"✅ Closed position {symbol} with P&L: ₹{pnl:.2f}")
            
        except Exception as e:
            logger.error(f"❌ Position closure failed for {symbol}: {e}")
    
    async def _check_portfolio_risk_limits(self, risk_per_lot: float, symbol: str) -> int:
        """Check portfolio-level risk constraints"""
        try:
            # Calculate current total portfolio risk
            current_total_risk = sum([pos.get('risk_amount', 0) for pos in self.active_positions.values()])
            max_portfolio_risk_amount = self.account_balance * self.max_portfolio_risk
            
            available_risk = max_portfolio_risk_amount - current_total_risk
            
            if available_risk <= 0:
                logger.warning("⚠️ Portfolio risk limit reached")
                return 0
            
            max_lots_by_portfolio = int(available_risk / risk_per_lot)
            return max(0, min(max_lots_by_portfolio, self.position_config['max_lot_size']))
            
        except Exception as e:
            logger.error(f"❌ Portfolio risk check failed: {e}")
            return 1  # Conservative fallback
    
    def _calculate_option_margin(self, underlying_price: float, option_premium: float, 
                               lot_size: int, lots: int) -> float:
        """Estimate margin requirements for options"""
        try:
            # Simplified margin calculation for options
            # For buying options, margin = premium paid
            # This is a conservative estimate
            
            total_premium = option_premium * lot_size * lots
            margin_buffer = total_premium * self.position_config['margin_safety_factor']
            
            return round(margin_buffer, 2)
            
        except Exception as e:
            logger.error(f"❌ Margin calculation failed: {e}")
            return option_premium * lot_size * lots * 1.5  # Conservative fallback
    
    def _create_zero_position(self) -> PositionSize:
        """Create zero position size for error cases"""
        return PositionSize(
            recommended_lots=0,
            max_lots_allowed=0,
            risk_amount=0.0,
            risk_percentage=0.0,
            position_value=0.0,
            margin_required=0.0,
            max_loss_amount=0.0,
            confidence_adjustment=0.0
        )
    
    async def _count_correlated_positions(self, symbol: str) -> int:
        """Count positions in correlated instruments"""
        # Simplified correlation check - in real implementation,
        # this would check actual correlation coefficients
        try:
            sector_map = {
                'HDFC': 'BANKING',
                'ICICI': 'BANKING', 
                'SBI': 'BANKING',
                'RELIANCE': 'ENERGY',
                'ONGC': 'ENERGY',
                'TCS': 'IT',
                'INFY': 'IT',
                'WIPRO': 'IT'
            }
            
            target_sector = None
            for key, sector in sector_map.items():
                if key in symbol.upper():
                    target_sector = sector
                    break
            
            if not target_sector:
                return 0
            
            correlated_count = 0
            for pos_symbol in self.active_positions.keys():
                for key, sector in sector_map.items():
                    if key in pos_symbol.upper() and sector == target_sector:
                        correlated_count += 1
                        break
            
            return correlated_count
            
        except Exception as e:
            logger.error(f"❌ Correlation check failed: {e}")
            return 0
    
    async def _calculate_sector_exposure(self, sector: str) -> float:
        """Calculate current exposure to a sector"""
        try:
            sector_risk = 0.0
            total_risk = sum([pos.get('risk_amount', 0) for pos in self.active_positions.values()])
            
            # This would need sector classification data in real implementation
            # For now, return estimated exposure
            if total_risk > 0:
                estimated_sector_risk = total_risk * 0.3  # Estimate 30% sector exposure
                return estimated_sector_risk / self.account_balance
            
            return 0.0
            
        except Exception as e:
            logger.error(f"❌ Sector exposure calculation failed: {e}")
            return 0.0
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get comprehensive risk summary"""
        try:
            total_positions = len(self.active_positions)
            total_risk = sum([pos.get('risk_amount', 0) for pos in self.active_positions.values()])
            portfolio_risk_pct = (total_risk / self.account_balance) * 100
            daily_pnl_pct = (self.daily_pnl / self.account_balance) * 100
            
            return {
                'account_balance': self.account_balance,
                'active_positions': total_positions,
                'total_risk_amount': round(total_risk, 2),
                'portfolio_risk_percentage': round(portfolio_risk_pct, 2),
                'daily_pnl': round(self.daily_pnl, 2),
                'daily_pnl_percentage': round(daily_pnl_pct, 2),
                'consecutive_losses': self.consecutive_losses,
                'risk_limits': {
                    'max_risk_per_trade': self.max_risk_per_trade * 100,
                    'max_portfolio_risk': self.max_portfolio_risk * 100,
                    'daily_loss_limit': self.risk_rules['daily_loss_limit'] * 100
                },
                'available_risk': round((self.account_balance * self.max_portfolio_risk) - total_risk, 2)
            }
            
        except Exception as e:
            logger.error(f"❌ Risk summary generation failed: {e}")
            return {'error': str(e)}

# Global risk management instance
dynamic_risk_reward = DynamicRiskReward()