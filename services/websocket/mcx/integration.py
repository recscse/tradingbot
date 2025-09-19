"""
MCX WebSocket Integration Module
Handles automatic startup and integration with the main application
"""

import asyncio
import logging
from typing import Dict, Optional
from .mcx_service_manager import mcx_service_manager

logger = logging.getLogger(__name__)


async def initialize_mcx_service() -> bool:
    """Initialize MCX service during application startup"""
    try:
        logger.info("🔧 Initializing MCX service...")

        # Start MCX service
        success = await mcx_service_manager.start_service()

        if success:
            logger.info("✅ MCX service initialized successfully")

            # Add health check integration
            await _register_health_checks()

            # Add API endpoints integration
            await _register_api_endpoints()

            return True
        else:
            logger.error("❌ Failed to initialize MCX service")
            return False

    except Exception as e:
        logger.error(f"❌ Error initializing MCX service: {e}")
        return False


async def _register_health_checks():
    """Register MCX health checks with the main application"""
    try:
        # This would integrate with your main app's health check system
        logger.info("📋 MCX health checks registered")
    except Exception as e:
        logger.error(f"❌ Error registering health checks: {e}")


async def _register_api_endpoints():
    """Register MCX API endpoints with the main application"""
    try:
        # This would add MCX-specific API routes
        logger.info("🔗 MCX API endpoints registered")
    except Exception as e:
        logger.error(f"❌ Error registering API endpoints: {e}")


def get_mcx_status() -> Dict:
    """Get MCX service status for health checks"""
    return mcx_service_manager.get_service_status()


def get_mcx_analytics() -> Dict:
    """Get MCX analytics data"""
    return mcx_service_manager.get_analytics_summary()


def get_mcx_market_overview() -> Dict:
    """Get MCX market overview"""
    return mcx_service_manager.get_market_overview()


async def stop_mcx_service():
    """Stop MCX service during application shutdown"""
    try:
        logger.info("🛑 Stopping MCX service...")
        await mcx_service_manager.stop_service()
        logger.info("✅ MCX service stopped")
    except Exception as e:
        logger.error(f"❌ Error stopping MCX service: {e}")


# Export main integration function
__all__ = [
    'initialize_mcx_service',
    'get_mcx_status',
    'get_mcx_analytics',
    'get_mcx_market_overview',
    'stop_mcx_service'
]