"""
Broker Profile Service
Unified service to handle broker profile and funds information across different brokers
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from database.models import BrokerConfig, User
from services.upstox_service import get_upstox_user_profile, get_upstox_funds_and_margin

logger = logging.getLogger(__name__)


class BrokerProfileService:
    """
    Unified service for broker profile and funds management
    Supports multiple brokers with a common interface
    """

    def __init__(self, db: Session):
        self.db = db

    def get_user_broker_profile(self, user_id: int, broker_name: str) -> Dict[str, Any]:
        """
        Get user profile information for a specific broker
        
        Args:
            user_id: User ID
            broker_name: Broker name (upstox, angel, dhan, etc.)
            
        Returns:
            Dict containing profile information
        """
        try:
            # Get broker configuration
            broker_config = self._get_active_broker_config(user_id, broker_name)
            
            # Route to appropriate broker service
            if broker_name.lower() == "upstox":
                return self._get_upstox_profile(broker_config)
            elif broker_name.lower() == "angel":
                return self._get_angel_profile(broker_config)
            elif broker_name.lower() == "dhan":
                return self._get_dhan_profile(broker_config)
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Profile service not implemented for broker: {broker_name}"
                )

        except Exception as e:
            logger.error(f"Error fetching profile for user {user_id}, broker {broker_name}: {e}")
            raise

    def get_user_funds_and_margin(
        self, 
        user_id: int, 
        broker_name: str, 
        segment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get user funds and margin information for a specific broker
        
        Args:
            user_id: User ID
            broker_name: Broker name
            segment: Market segment (if applicable)
            
        Returns:
            Dict containing funds and margin information
        """
        try:
            # Get broker configuration
            broker_config = self._get_active_broker_config(user_id, broker_name)
            
            # Route to appropriate broker service
            if broker_name.lower() == "upstox":
                return self._get_upstox_funds(broker_config, segment)
            elif broker_name.lower() == "angel":
                return self._get_angel_funds(broker_config, segment)
            elif broker_name.lower() == "dhan":
                return self._get_dhan_funds(broker_config, segment)
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Funds service not implemented for broker: {broker_name}"
                )

        except Exception as e:
            logger.error(f"Error fetching funds for user {user_id}, broker {broker_name}: {e}")
            raise

    def get_all_user_broker_profiles(self, user_id: int) -> Dict[str, Any]:
        """
        Get profile information for all active brokers of a user
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with broker profiles
        """
        try:
            # Get all active broker configurations for user
            broker_configs = self.db.query(BrokerConfig).filter(
                BrokerConfig.user_id == user_id,
                BrokerConfig.is_active == True
            ).all()

            if not broker_configs:
                return {"profiles": {}, "message": "No active broker configurations found"}

            profiles = {}
            for config in broker_configs:
                try:
                    profile = self.get_user_broker_profile(user_id, config.broker_name)
                    profiles[config.broker_name.lower()] = {
                        "profile": profile,
                        "config_id": config.id,
                        "last_updated": datetime.now().isoformat()
                    }
                except Exception as e:
                    logger.warning(f"Failed to fetch profile for {config.broker_name}: {e}")
                    profiles[config.broker_name.lower()] = {
                        "error": str(e),
                        "config_id": config.id
                    }

            return {
                "profiles": profiles,
                "total_brokers": len(broker_configs),
                "successful_fetches": len([p for p in profiles.values() if "profile" in p])
            }

        except Exception as e:
            logger.error(f"Error fetching all profiles for user {user_id}: {e}")
            raise

    def get_combined_funds_summary(self, user_id: int) -> Dict[str, Any]:
        """
        Get combined funds summary across all active brokers
        
        Args:
            user_id: User ID
            
        Returns:
            Combined funds summary
        """
        try:
            logger.info(f"🔍 DEBUG: get_combined_funds_summary called for user_id: {user_id}")
            logger.info(f"🔍 DEBUG: Database session: {self.db}")
            logger.info(f"🔍 DEBUG: Service instance: {self}")
            logger.info(f"🔍 DEBUG: Method being called: get_combined_funds_summary")
            
            # TEMP DEBUG: Check what this method actually does
            import inspect
            logger.info(f"🔍 DEBUG: Method source file: {inspect.getfile(self.get_combined_funds_summary)}")
            
            
            broker_configs = self.db.query(BrokerConfig).filter(
                BrokerConfig.user_id == user_id,
                BrokerConfig.is_active == True
            ).all()

            if not broker_configs:
                return {"funds": {}, "message": "No active broker configurations found"}

            funds_data = {}
            total_available = 0
            total_used = 0

            for config in broker_configs:
                try:
                    funds = self.get_user_funds_and_margin(user_id, config.broker_name)
                    funds_data[config.broker_name.lower()] = funds
                    
                    # Extract and sum available/used margins (broker-specific logic)
                    if config.broker_name.lower() == "upstox" and "data" in funds:
                        equity_data = funds["data"].get("equity", {})
                        total_available += equity_data.get("available_margin", 0)
                        total_used += equity_data.get("used_margin", 0)

                except Exception as e:
                    logger.warning(f"Failed to fetch funds for {config.broker_name}: {e}")
                    funds_data[config.broker_name.lower()] = {"error": str(e)}

            return {
                "broker_funds": funds_data,
                "summary": {
                    "total_available_margin": total_available,
                    "total_used_margin": total_used,
                    "utilization_percentage": (total_used / total_available * 100) if total_available > 0 else 0
                },
                "last_updated": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error fetching combined funds for user {user_id}: {e}")
            raise

    def _get_active_broker_config(self, user_id: int, broker_name: str) -> BrokerConfig:
        """Get active broker configuration for user"""
        config = self.db.query(BrokerConfig).filter(
            BrokerConfig.user_id == user_id,
            BrokerConfig.broker_name.ilike(broker_name),
            BrokerConfig.is_active == True
        ).first()
        
        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"{broker_name} broker configuration not found or inactive"
            )
        
        if not config.access_token:
            raise HTTPException(
                status_code=400,
                detail=f"{broker_name} access token not available. Please re-authenticate."
            )
        
        # Check token expiry
        if config.access_token_expiry and config.access_token_expiry <= datetime.now():
            raise HTTPException(
                status_code=401,
                detail=f"{broker_name} access token expired. Please re-authenticate."
            )
        
        return config

    def _get_upstox_profile(self, config: BrokerConfig) -> Dict[str, Any]:
        """Get Upstox user profile and store in database"""
        profile_data = get_upstox_user_profile(config.access_token)
        
        # Update the broker config with profile data
        config.update_profile_data(profile_data)
        self.db.commit()
        
        return {
            "broker": "upstox",
            "data": profile_data,
            "config_id": config.id
        }

    def _get_upstox_funds(self, config: BrokerConfig, segment: Optional[str]) -> Dict[str, Any]:
        """Get Upstox funds and margin and store in database"""
        funds_data = get_upstox_funds_and_margin(config.access_token, segment)
        
        # Update the broker config with funds data
        config.update_funds_data(funds_data)
        self.db.commit()
        
        return {
            "broker": "upstox",
            "data": funds_data,
            "segment": segment,
            "config_id": config.id
        }

    def _get_angel_profile(self, config: BrokerConfig) -> Dict[str, Any]:
        """Get Angel One profile - To be implemented"""
        raise HTTPException(
            status_code=501,
            detail="Angel One profile service not yet implemented"
        )

    def _get_angel_funds(self, config: BrokerConfig, segment: Optional[str]) -> Dict[str, Any]:
        """Get Angel One funds - To be implemented"""
        raise HTTPException(
            status_code=501,
            detail="Angel One funds service not yet implemented"
        )

    def _get_dhan_profile(self, config: BrokerConfig) -> Dict[str, Any]:
        """Get Dhan profile - To be implemented"""
        raise HTTPException(
            status_code=501,
            detail="Dhan profile service not yet implemented"
        )

    def _get_dhan_funds(self, config: BrokerConfig, segment: Optional[str]) -> Dict[str, Any]:
        """Get Dhan funds - To be implemented"""
        raise HTTPException(
            status_code=501,
            detail="Dhan funds service not yet implemented"
        )