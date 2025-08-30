"""
Broker Funds Sync Service
Automatically syncs broker funds and profile data for live trading
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from database.connection import SessionLocal
from database.models import BrokerConfig, User
from services.broker_profile_service import BrokerProfileService

logger = logging.getLogger(__name__)


class BrokerFundsSyncService:
    """
    Service to automatically sync broker funds and profile data
    Used by live trading system for real-time margin management
    """

    def __init__(self):
        self.sync_interval_minutes = 5  # Sync every 5 minutes during market hours
        self.profile_sync_interval_hours = 24  # Sync profile once per day
        self.is_running = False

    async def start_background_sync(self):
        """Start background sync process"""
        if self.is_running:
            logger.warning("Broker funds sync is already running")
            return

        self.is_running = True
        logger.info("🚀 Starting broker funds sync service")

        while self.is_running:
            try:
                await self.sync_all_active_brokers()
                await asyncio.sleep(self.sync_interval_minutes * 60)
            except Exception as e:
                logger.error(f"Error in background sync: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def stop_background_sync(self):
        """Stop background sync process"""
        self.is_running = False
        logger.info("🛑 Stopped broker funds sync service")

    async def sync_all_active_brokers(self):
        """Sync funds data for all active brokers"""
        try:
            with SessionLocal() as db:
                # Get all active broker configurations
                active_brokers = db.query(BrokerConfig).filter(
                    BrokerConfig.is_active == True,
                    BrokerConfig.access_token.isnot(None)
                ).all()

                logger.info(f"📊 Syncing funds for {len(active_brokers)} active brokers")

                sync_results = {
                    "success_count": 0,
                    "error_count": 0,
                    "total_count": len(active_brokers),
                    "errors": []
                }

                for broker_config in active_brokers:
                    try:
                        await self.sync_broker_data(db, broker_config)
                        sync_results["success_count"] += 1
                    except Exception as e:
                        error_msg = f"Failed to sync {broker_config.broker_name} for user {broker_config.user_id}: {e}"
                        logger.error(error_msg)
                        sync_results["error_count"] += 1
                        sync_results["errors"].append(error_msg)

                logger.info(
                    f"✅ Sync completed: {sync_results['success_count']}/{sync_results['total_count']} successful"
                )

                return sync_results

        except Exception as e:
            logger.error(f"Failed to sync all brokers: {e}")
            raise

    async def sync_broker_data(self, db: Session, broker_config: BrokerConfig):
        """Sync funds and profile data for a specific broker"""
        try:
            service = BrokerProfileService(db)

            # Check if token is expired
            if broker_config.access_token_expiry and broker_config.access_token_expiry <= datetime.now():
                logger.warning(f"Token expired for {broker_config.broker_name} user {broker_config.user_id}")
                return

            # Sync funds data (always)
            try:
                funds_data = service.get_user_funds_and_margin(
                    broker_config.user_id, 
                    broker_config.broker_name
                )
                logger.debug(f"✅ Synced funds for {broker_config.broker_name}")
            except Exception as e:
                logger.error(f"Failed to sync funds for {broker_config.broker_name}: {e}")

            # Sync profile data (less frequently)
            should_sync_profile = (
                not broker_config.profile_last_updated or 
                broker_config.profile_last_updated < datetime.now() - timedelta(hours=self.profile_sync_interval_hours)
            )

            if should_sync_profile:
                try:
                    profile_data = service.get_user_broker_profile(
                        broker_config.user_id,
                        broker_config.broker_name
                    )
                    logger.debug(f"✅ Synced profile for {broker_config.broker_name}")
                except Exception as e:
                    logger.error(f"Failed to sync profile for {broker_config.broker_name}: {e}")

        except Exception as e:
            logger.error(f"Error syncing broker {broker_config.broker_name}: {e}")
            raise

    def get_broker_available_margin(self, user_id: int, broker_name: str = None) -> float:
        """
        Get available margin for trading
        Used by live trading system before placing orders
        """
        try:
            with SessionLocal() as db:
                query = db.query(BrokerConfig).filter(
                    BrokerConfig.user_id == user_id,
                    BrokerConfig.is_active == True,
                    BrokerConfig.available_margin.isnot(None)
                )

                if broker_name:
                    query = query.filter(BrokerConfig.broker_name.ilike(broker_name))

                broker_configs = query.all()

                if not broker_configs:
                    logger.warning(f"No active brokers with funds data found for user {user_id}")
                    return 0.0

                # Sum available margin across all brokers
                total_margin = sum(
                    (config.available_margin or 0) - (config.used_margin or 0) 
                    for config in broker_configs
                )

                return max(0.0, total_margin)

        except Exception as e:
            logger.error(f"Error getting available margin for user {user_id}: {e}")
            return 0.0

    def can_place_trade(self, user_id: int, required_margin: float, broker_name: str = None) -> Dict[str, Any]:
        """
        Check if user has sufficient margin to place a trade
        Returns detailed info for trading system decision
        """
        try:
            with SessionLocal() as db:
                query = db.query(BrokerConfig).filter(
                    BrokerConfig.user_id == user_id,
                    BrokerConfig.is_active == True
                )

                if broker_name:
                    query = query.filter(BrokerConfig.broker_name.ilike(broker_name))

                broker_configs = query.all()

                if not broker_configs:
                    return {
                        "can_trade": False,
                        "reason": "No active broker configurations found",
                        "available_margin": 0.0,
                        "required_margin": required_margin
                    }

                # Find the best broker for this trade
                best_broker = None
                best_free_margin = 0

                for config in broker_configs:
                    free_margin = config.get_free_margin()
                    if free_margin >= required_margin and free_margin > best_free_margin:
                        best_broker = config
                        best_free_margin = free_margin

                if best_broker:
                    return {
                        "can_trade": True,
                        "broker_id": best_broker.id,
                        "broker_name": best_broker.broker_name,
                        "available_margin": best_free_margin,
                        "required_margin": required_margin,
                        "margin_after_trade": best_free_margin - required_margin,
                        "utilization_after": ((best_broker.used_margin or 0) + required_margin) / (best_broker.available_margin or 1) * 100
                    }
                else:
                    total_available = sum(config.get_free_margin() for config in broker_configs)
                    return {
                        "can_trade": False,
                        "reason": f"Insufficient margin. Required: ₹{required_margin:,.2f}, Available: ₹{total_available:,.2f}",
                        "available_margin": total_available,
                        "required_margin": required_margin
                    }

        except Exception as e:
            logger.error(f"Error checking trade capability for user {user_id}: {e}")
            return {
                "can_trade": False,
                "reason": f"Error checking margin: {str(e)}",
                "available_margin": 0.0,
                "required_margin": required_margin
            }

    def get_user_margin_summary(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive margin summary for user"""
        try:
            with SessionLocal() as db:
                broker_configs = db.query(BrokerConfig).filter(
                    BrokerConfig.user_id == user_id,
                    BrokerConfig.is_active == True
                ).all()

                if not broker_configs:
                    return {"error": "No active broker configurations found"}

                summary = {
                    "total_available_margin": 0.0,
                    "total_used_margin": 0.0,
                    "total_free_margin": 0.0,
                    "overall_utilization": 0.0,
                    "brokers": [],
                    "last_updated": None
                }

                for config in broker_configs:
                    available = config.available_margin or 0
                    used = config.used_margin or 0
                    free = max(0, available - used)

                    broker_info = {
                        "broker_name": config.broker_name,
                        "available_margin": available,
                        "used_margin": used,
                        "free_margin": free,
                        "utilization": config.get_margin_utilization(),
                        "last_updated": config.funds_last_updated.isoformat() if config.funds_last_updated else None
                    }

                    summary["brokers"].append(broker_info)
                    summary["total_available_margin"] += available
                    summary["total_used_margin"] += used
                    summary["total_free_margin"] += free

                    # Track most recent update
                    if config.funds_last_updated:
                        if not summary["last_updated"] or config.funds_last_updated > datetime.fromisoformat(summary["last_updated"]):
                            summary["last_updated"] = config.funds_last_updated.isoformat()

                # Calculate overall utilization
                if summary["total_available_margin"] > 0:
                    summary["overall_utilization"] = (
                        summary["total_used_margin"] / summary["total_available_margin"] * 100
                    )

                return summary

        except Exception as e:
            logger.error(f"Error getting margin summary for user {user_id}: {e}")
            return {"error": str(e)}

    async def force_sync_user_brokers(self, user_id: int) -> Dict[str, Any]:
        """Force immediate sync of all brokers for a specific user"""
        try:
            with SessionLocal() as db:
                user_brokers = db.query(BrokerConfig).filter(
                    BrokerConfig.user_id == user_id,
                    BrokerConfig.is_active == True,
                    BrokerConfig.access_token.isnot(None)
                ).all()

                logger.info(f"🔄 Force syncing {len(user_brokers)} brokers for user {user_id}")

                results = {
                    "user_id": user_id,
                    "synced_brokers": 0,
                    "failed_brokers": 0,
                    "errors": [],
                    "timestamp": datetime.now().isoformat()
                }

                for broker_config in user_brokers:
                    try:
                        await self.sync_broker_data(db, broker_config)
                        results["synced_brokers"] += 1
                        logger.info(f"✅ Force synced {broker_config.broker_name}")
                    except Exception as e:
                        error_msg = f"Failed to sync {broker_config.broker_name}: {str(e)}"
                        results["errors"].append(error_msg)
                        results["failed_brokers"] += 1
                        logger.error(error_msg)

                return results

        except Exception as e:
            logger.error(f"Error in force sync for user {user_id}: {e}")
            raise


# Global instance
broker_funds_sync_service = BrokerFundsSyncService()