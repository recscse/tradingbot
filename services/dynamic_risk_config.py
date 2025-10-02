"""
Dynamic Risk Configuration Service
Allows runtime configuration of risk parameters per strategy
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import json

logger = logging.getLogger(__name__)


class RiskProfile(Enum):
    """Risk profile types"""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    CUSTOM = "custom"


class MarketVolatility(Enum):
    """Market volatility levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass
class DynamicRiskConfig:
    """Dynamic risk configuration with strategy-based parameters"""

    # Core risk parameters (dynamic per strategy)
    max_loss_per_position: float = 0.02        # Default 2% - can be changed
    max_total_exposure: float = 0.10           # Default 10% - can be changed
    max_daily_loss: float = 0.05               # Default 5% - can be changed

    # Position sizing parameters
    position_size_multiplier: float = 1.0      # Default 1x - can be scaled
    max_positions: int = 5                     # Maximum concurrent positions
    min_capital_per_position: float = 10000    # Minimum ₹10K per position
    max_capital_per_position: float = 100000   # Maximum ₹1L per position

    # Profit management
    profit_booking_levels: list = None         # [0.5, 1.0, 1.5] - 50%, 100%, 150%
    trailing_stop_activation: float = 0.5      # Activate at 50% profit
    trailing_stop_percentage: float = 0.20     # Trail by 20%

    # Time-based risk
    time_decay_exit_days: int = 1              # Exit 1 day before expiry
    max_holding_days: int = 30                 # Maximum holding period

    # Volatility-based adjustments
    high_iv_threshold: float = 40.0            # High IV threshold
    low_iv_threshold: float = 15.0             # Low IV threshold
    volatility_multiplier: float = 1.0         # Adjust position size based on volatility

    # Market condition adjustments
    bear_market_multiplier: float = 0.7        # Reduce exposure in bear market
    bull_market_multiplier: float = 1.2        # Increase exposure in bull market

    # Risk profile
    risk_profile: RiskProfile = RiskProfile.MODERATE

    # Metadata
    created_at: str = ""
    updated_at: str = ""
    created_by: str = "system"
    strategy_name: str = "default"

    def __post_init__(self):
        if self.profit_booking_levels is None:
            self.profit_booking_levels = [0.5, 1.0, 1.5]
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()


class DynamicRiskManager:
    """
    Manages dynamic risk configurations for different strategies
    """

    def __init__(self):
        # Store multiple risk configurations by strategy name
        self.risk_configs: Dict[str, DynamicRiskConfig] = {}

        # Current active configuration
        self.active_config: DynamicRiskConfig = DynamicRiskConfig()
        self.active_strategy_name: str = "default"

        # Risk profile templates
        self.risk_templates = self._create_risk_templates()

        # Market volatility adjustment factors
        self.volatility_adjustments = {
            MarketVolatility.LOW: {"exposure_multiplier": 1.2, "position_size_multiplier": 1.1},
            MarketVolatility.MEDIUM: {"exposure_multiplier": 1.0, "position_size_multiplier": 1.0},
            MarketVolatility.HIGH: {"exposure_multiplier": 0.8, "position_size_multiplier": 0.9},
            MarketVolatility.EXTREME: {"exposure_multiplier": 0.6, "position_size_multiplier": 0.7},
        }

        logger.info("🔒 Dynamic Risk Manager initialized")

    def _create_risk_templates(self) -> Dict[RiskProfile, DynamicRiskConfig]:
        """Create predefined risk profile templates"""
        templates = {}

        # Conservative template
        templates[RiskProfile.CONSERVATIVE] = DynamicRiskConfig(
            max_loss_per_position=0.01,      # 1% max loss per position
            max_total_exposure=0.05,         # 5% total exposure
            max_daily_loss=0.03,             # 3% daily loss limit
            position_size_multiplier=0.8,    # Smaller positions
            max_positions=3,                 # Fewer positions
            trailing_stop_activation=0.3,    # Early profit booking
            trailing_stop_percentage=0.15,   # Tighter trailing stop
            risk_profile=RiskProfile.CONSERVATIVE,
            strategy_name="conservative"
        )

        # Moderate template (default)
        templates[RiskProfile.MODERATE] = DynamicRiskConfig(
            max_loss_per_position=0.02,      # 2% max loss per position
            max_total_exposure=0.10,         # 10% total exposure
            max_daily_loss=0.05,             # 5% daily loss limit
            position_size_multiplier=1.0,    # Normal positions
            max_positions=5,                 # Standard positions
            trailing_stop_activation=0.5,    # Standard profit booking
            trailing_stop_percentage=0.20,   # Standard trailing stop
            risk_profile=RiskProfile.MODERATE,
            strategy_name="moderate"
        )

        # Aggressive template
        templates[RiskProfile.AGGRESSIVE] = DynamicRiskConfig(
            max_loss_per_position=0.03,      # 3% max loss per position
            max_total_exposure=0.15,         # 15% total exposure
            max_daily_loss=0.08,             # 8% daily loss limit
            position_size_multiplier=1.3,    # Larger positions
            max_positions=8,                 # More positions
            trailing_stop_activation=0.7,    # Later profit booking
            trailing_stop_percentage=0.25,   # Wider trailing stop
            risk_profile=RiskProfile.AGGRESSIVE,
            strategy_name="aggressive"
        )

        return templates

    def create_strategy_config(
        self,
        strategy_name: str,
        base_profile: RiskProfile = RiskProfile.MODERATE,
        custom_overrides: Dict[str, Any] = None
    ) -> DynamicRiskConfig:
        """
        Create a new risk configuration for a strategy
        """
        try:
            # Start with base template
            base_config = self.risk_templates[base_profile]

            # Create new config
            new_config = DynamicRiskConfig(**asdict(base_config))
            new_config.strategy_name = strategy_name
            new_config.created_at = datetime.now().isoformat()
            new_config.updated_at = datetime.now().isoformat()

            # Apply custom overrides
            if custom_overrides:
                for key, value in custom_overrides.items():
                    if hasattr(new_config, key):
                        setattr(new_config, key, value)
                        logger.info(f"Applied override: {key} = {value}")

                new_config.risk_profile = RiskProfile.CUSTOM
                new_config.updated_at = datetime.now().isoformat()

            # Store the configuration
            self.risk_configs[strategy_name] = new_config

            logger.info(f"✅ Created risk config for strategy '{strategy_name}' with profile '{base_profile.value}'")
            return new_config

        except Exception as e:
            logger.error(f"Error creating strategy config: {e}")
            return self.risk_templates[RiskProfile.MODERATE]  # Fallback

    def activate_strategy_config(self, strategy_name: str) -> bool:
        """
        Activate a specific risk configuration
        """
        try:
            if strategy_name in self.risk_configs:
                self.active_config = self.risk_configs[strategy_name]
                self.active_strategy_name = strategy_name
                logger.info(f"🔄 Activated risk config for strategy: {strategy_name}")
                return True
            else:
                logger.error(f"Strategy config '{strategy_name}' not found")
                return False

        except Exception as e:
            logger.error(f"Error activating strategy config: {e}")
            return False

    def update_active_config(self, updates: Dict[str, Any]) -> bool:
        """
        Update the currently active risk configuration
        """
        try:
            updated_fields = []

            for key, value in updates.items():
                if hasattr(self.active_config, key):
                    old_value = getattr(self.active_config, key)
                    setattr(self.active_config, key, value)
                    updated_fields.append(f"{key}: {old_value} → {value}")
                else:
                    logger.warning(f"Invalid config key: {key}")

            if updated_fields:
                self.active_config.updated_at = datetime.now().isoformat()
                self.active_config.risk_profile = RiskProfile.CUSTOM

                # Update stored config
                self.risk_configs[self.active_strategy_name] = self.active_config

                logger.info(f"✅ Updated active config: {', '.join(updated_fields)}")
                return True
            else:
                logger.warning("No valid updates provided")
                return False

        except Exception as e:
            logger.error(f"Error updating active config: {e}")
            return False

    def adjust_for_market_conditions(
        self,
        market_sentiment: str,
        volatility_level: MarketVolatility
    ) -> DynamicRiskConfig:
        """
        Adjust risk configuration based on market conditions
        """
        try:
            # Create adjusted config (don't modify the original)
            adjusted_config = DynamicRiskConfig(**asdict(self.active_config))

            # Volatility adjustments
            volatility_adj = self.volatility_adjustments[volatility_level]
            adjusted_config.max_total_exposure *= volatility_adj["exposure_multiplier"]
            adjusted_config.position_size_multiplier *= volatility_adj["position_size_multiplier"]

            # Market sentiment adjustments
            if market_sentiment.lower() in ["bearish", "very_bearish"]:
                adjusted_config.max_total_exposure *= adjusted_config.bear_market_multiplier
                adjusted_config.max_loss_per_position *= 0.8  # More conservative in bear market
                logger.info("🐻 Applied bear market risk adjustments")

            elif market_sentiment.lower() in ["bullish", "very_bullish"]:
                adjusted_config.max_total_exposure *= adjusted_config.bull_market_multiplier
                adjusted_config.position_size_multiplier *= 1.1  # Slightly more aggressive
                logger.info("🐂 Applied bull market risk adjustments")

            # Cap the adjustments to reasonable limits
            adjusted_config.max_total_exposure = min(0.25, max(0.02, adjusted_config.max_total_exposure))  # 2-25%
            adjusted_config.max_loss_per_position = min(0.05, max(0.005, adjusted_config.max_loss_per_position))  # 0.5-5%

            adjusted_config.updated_at = datetime.now().isoformat()
            logger.info(f"📊 Adjusted config for {market_sentiment} market, {volatility_level.value} volatility")

            return adjusted_config

        except Exception as e:
            logger.error(f"Error adjusting for market conditions: {e}")
            return self.active_config  # Return original if error

    def get_position_size_limits(self, capital: float) -> Dict[str, float]:
        """
        Calculate position size limits based on current config
        """
        try:
            config = self.active_config

            # Calculate limits
            max_position_capital = min(
                capital * config.max_loss_per_position / 0.01,  # Based on max loss percentage (assume 1% default risk)
                config.max_capital_per_position,
                capital * config.max_total_exposure / config.max_positions  # Equal allocation
            )

            min_position_capital = max(
                config.min_capital_per_position,
                capital * 0.001  # Minimum 0.1% of capital
            )

            total_max_exposure = capital * config.max_total_exposure

            return {
                "min_position_capital": min_position_capital,
                "max_position_capital": max_position_capital,
                "total_max_exposure": total_max_exposure,
                "recommended_position_capital": max_position_capital * 0.8,  # 80% of max for safety
                "max_positions": config.max_positions,
                "position_size_multiplier": config.position_size_multiplier
            }

        except Exception as e:
            logger.error(f"Error calculating position size limits: {e}")
            return {
                "min_position_capital": 10000,
                "max_position_capital": 50000,
                "total_max_exposure": capital * 0.1,
                "recommended_position_capital": 40000,
                "max_positions": 5,
                "position_size_multiplier": 1.0
            }

    def get_risk_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive risk configuration summary
        """
        try:
            config = self.active_config

            return {
                "active_strategy": self.active_strategy_name,
                "risk_profile": config.risk_profile.value,
                "created_at": config.created_at,
                "updated_at": config.updated_at,

                "position_risk": {
                    "max_loss_per_position_percent": config.max_loss_per_position * 100,
                    "max_total_exposure_percent": config.max_total_exposure * 100,
                    "max_daily_loss_percent": config.max_daily_loss * 100,
                    "max_positions": config.max_positions,
                    "position_size_multiplier": config.position_size_multiplier,
                },

                "profit_management": {
                    "profit_booking_levels": config.profit_booking_levels,
                    "trailing_stop_activation_percent": config.trailing_stop_activation * 100,
                    "trailing_stop_percentage": config.trailing_stop_percentage * 100,
                },

                "time_risk": {
                    "time_decay_exit_days": config.time_decay_exit_days,
                    "max_holding_days": config.max_holding_days,
                },

                "market_adjustments": {
                    "bear_market_multiplier": config.bear_market_multiplier,
                    "bull_market_multiplier": config.bull_market_multiplier,
                    "volatility_multiplier": config.volatility_multiplier,
                },

                "available_strategies": list(self.risk_configs.keys()),
                "available_profiles": [profile.value for profile in RiskProfile],
            }

        except Exception as e:
            logger.error(f"Error getting risk summary: {e}")
            return {"error": str(e)}

    def save_config_to_file(self, filepath: str) -> bool:
        """Save all configurations to file"""
        try:
            config_data = {
                "active_strategy": self.active_strategy_name,
                "configurations": {
                    name: asdict(config)
                    for name, config in self.risk_configs.items()
                },
                "saved_at": datetime.now().isoformat()
            }

            with open(filepath, 'w') as f:
                json.dump(config_data, f, indent=2)

            logger.info(f"✅ Saved risk configurations to {filepath}")
            return True

        except Exception as e:
            logger.error(f"Error saving config to file: {e}")
            return False

    def load_config_from_file(self, filepath: str) -> bool:
        """Load configurations from file"""
        try:
            with open(filepath, 'r') as f:
                config_data = json.load(f)

            # Load configurations
            for name, config_dict in config_data.get("configurations", {}).items():
                # Convert dict back to DynamicRiskConfig
                risk_profile = RiskProfile(config_dict.get("risk_profile", "moderate"))
                config_dict["risk_profile"] = risk_profile

                config = DynamicRiskConfig(**config_dict)
                self.risk_configs[name] = config

            # Set active strategy
            active_strategy = config_data.get("active_strategy", "default")
            if active_strategy in self.risk_configs:
                self.activate_strategy_config(active_strategy)

            logger.info(f"✅ Loaded risk configurations from {filepath}")
            return True

        except Exception as e:
            logger.error(f"Error loading config from file: {e}")
            return False


# Global instance
dynamic_risk_manager = DynamicRiskManager()