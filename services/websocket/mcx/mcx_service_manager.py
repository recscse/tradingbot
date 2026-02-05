"""
MCX Service Manager - Similar to ws_client pattern with automatic management
"""

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
from typing import Optional, Dict, List
from .mcx_ws_client import MCXWebSocketClient

logger = logging.getLogger(__name__)


class MCXServiceManager:
    """
    MCX Service Manager following the ws_client pattern
    Manages lifecycle, data processing, and integration
    """

    def __init__(self):
        self.mcx_client: Optional[MCXWebSocketClient] = None
        self.is_running = False
        self.auto_restart = True
        self.service_start_time: Optional[datetime] = None

        # Market hours for MCX (extended for commodities)
        self.market_hours = {
            "start": time(9, 0),      # 9:00 AM
            "end": time(23, 30)       # 11:30 PM
        }

        # Service statistics
        self.service_stats = {
            'total_uptime_seconds': 0,
            'restart_count': 0,
            'last_restart_time': None,
            'data_points_processed': 0,
            'errors': 0
        }

        # Data aggregation and analytics
        self.aggregated_data = {
            'daily_summary': None,
            'symbol_performance': {},
            'volume_analysis': {},
            'last_aggregation': None
        }

        # Background tasks
        self.background_tasks = set()

    async def start_service(self) -> bool:
        """Start the MCX service with full lifecycle management"""
        try:
            if self.is_running:
                logger.warning("⚠️ MCX service is already running")
                return True

            logger.info("🚀 Starting MCX Service Manager")
            self.service_start_time = datetime.now()

            # Check market hours
            if not await self._check_and_wait_for_market():
                return False

            # Initialize MCX client
            self.mcx_client = MCXWebSocketClient(callback=self._handle_mcx_data)

            if await self.mcx_client.initialize():
                self.is_running = True

                # Start background monitoring and data processing
                await self._start_background_services()

                # Start the main client
                self._create_background_task(self._run_client_with_monitoring())

                logger.info("✅ MCX service started successfully")
                return True
            else:
                logger.error("❌ Failed to initialize MCX client")
                return False

        except Exception as e:
            logger.error(f"❌ Error starting MCX service: {e}")
            self.service_stats['errors'] += 1
            return False

    async def _check_and_wait_for_market(self) -> bool:
        """Check market hours and wait if needed"""
        try:
            if not self._is_market_hours():
                logger.info("🕒 Outside market hours, checking schedule...")

                # Check if we should wait or skip
                next_market_open = self._get_next_market_open()
                wait_time = (next_market_open - datetime.now()).total_seconds()

                if wait_time > 3600:  # More than 1 hour wait
                    logger.info(f"🕒 Market opens in {wait_time/3600:.1f} hours. Service will wait.")
                    await self._wait_for_market_hours()
                else:
                    logger.info(f"🕒 Market opens in {wait_time/60:.1f} minutes. Starting soon...")
                    await asyncio.sleep(wait_time)

            return True

        except Exception as e:
            logger.error(f"❌ Error in market hours check: {e}")
            return False

    async def _start_background_services(self):
        """Start background services for data processing and monitoring"""
        try:
            # Data aggregation service
            self._create_background_task(self._data_aggregation_service())

            # Health monitoring service
            self._create_background_task(self._health_monitoring_service())

            # Periodic data export service
            self._create_background_task(self._periodic_export_service())

            logger.info("✅ Background services started")

        except Exception as e:
            logger.error(f"❌ Error starting background services: {e}")

    def _create_background_task(self, coro):
        """Create and track background tasks"""
        task = asyncio.create_task(coro)
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)

    async def _run_client_with_monitoring(self):
        """Run MCX client with automatic restart and monitoring"""
        while self.is_running and self.auto_restart:
            try:
                if self._is_market_hours():
                    logger.info("📡 Starting MCX WebSocket connection...")
                    await self.mcx_client.start()
                else:
                    logger.info("🕒 Market closed, waiting for next session")
                    await self._wait_for_market_hours()

            except Exception as e:
                logger.error(f"❌ MCX client error: {e}")
                self.service_stats['errors'] += 1

                if self.auto_restart:
                    self.service_stats['restart_count'] += 1
                    self.service_stats['last_restart_time'] = datetime.now()

                    logger.info("🔄 Restarting MCX client in 30 seconds...")
                    await asyncio.sleep(30)

                    # Reinitialize client if needed
                    if not self.mcx_client or not self.mcx_client.access_token:
                        self.mcx_client = MCXWebSocketClient(callback=self._handle_mcx_data)
                        await self.mcx_client.initialize()
                else:
                    break

    async def _handle_mcx_data(self, data: Dict):
        """Enhanced MCX data handler with pandas/numpy processing"""
        try:
            self.service_stats['data_points_processed'] += data.get('count', 0)

            # Process DataFrames for analysis
            dataframes = data.get('dataframes', {})
            if dataframes:
                await self._process_dataframes(dataframes)

            # Update real-time analytics
            await self._update_real_time_analytics(data)

            # Broadcast to connected systems
            await self._broadcast_mcx_data(data)

            # Log performance
            if self.service_stats['data_points_processed'] % 100 == 0:
                logger.info(f"📊 Processed {self.service_stats['data_points_processed']} data points")

        except Exception as e:
            logger.error(f"❌ Error handling MCX data: {e}")
            self.service_stats['errors'] += 1

    async def _process_dataframes(self, dataframes: Dict):
        """Process pandas DataFrames for advanced analytics"""
        try:
            current_snapshot = dataframes.get('current_snapshot')
            futures_chain = dataframes.get('futures_chain')
            volume_data = dataframes.get('volume_data')

            if current_snapshot is not None and len(current_snapshot) > 0:
                # Symbol performance analysis
                symbol_performance = current_snapshot.groupby('symbol').agg({
                    'change_percent': ['mean', 'std', 'count'],
                    'volume': 'sum',
                    'ltp': 'last'
                }).round(2)

                self.aggregated_data['symbol_performance'] = symbol_performance.to_dict()

                # Volume analysis using numpy
                if 'volume' in current_snapshot.columns:
                    volumes = current_snapshot['volume'].dropna()
                    if len(volumes) > 0:
                        self.aggregated_data['volume_analysis'] = {
                            'total_volume': float(np.sum(volumes)),
                            'avg_volume': float(np.mean(volumes)),
                            'volume_std': float(np.std(volumes)),
                            'high_volume_threshold': float(np.percentile(volumes, 90)),
                            'top_volume_instruments': current_snapshot.nlargest(5, 'volume')[
                                ['instrument_key', 'symbol', 'volume']
                            ].to_dict('records')
                        }

            self.aggregated_data['last_aggregation'] = datetime.now()

        except Exception as e:
            logger.error(f"❌ Error processing DataFrames: {e}")

    async def _update_real_time_analytics(self, data: Dict):
        """Update real-time analytics"""
        try:
            analytics = data.get('analytics', {})

            if analytics:
                # Create daily summary
                self.aggregated_data['daily_summary'] = {
                    'timestamp': datetime.now().isoformat(),
                    'total_instruments': analytics.get('total_instruments', 0),
                    'total_symbols': analytics.get('total_symbols', 0),
                    'price_analytics': analytics.get('price_stats', {}),
                    'volume_analytics': analytics.get('volume_stats', {}),
                    'uptime_hours': self._get_uptime_hours()
                }

        except Exception as e:
            logger.error(f"❌ Error updating real-time analytics: {e}")

    async def _broadcast_mcx_data(self, data: Dict):
        """Broadcast MCX data to other systems"""
        try:
            # Integration with centralized WebSocket manager
            try:
                from services.centralized_ws_manager import centralized_manager
                if centralized_manager and centralized_manager.is_running:
                    # Add MCX data to centralized cache for frontend
                    mcx_summary = {
                        'type': 'mcx_update',
                        'count': data.get('count', 0),
                        'analytics': data.get('analytics', {}),
                        'timestamp': data.get('timestamp')
                    }

                    # Broadcast to dashboard clients
                    await centralized_manager._send_to_client_group(
                        centralized_manager.dashboard_clients,
                        mcx_summary
                    )

                    logger.debug("📡 MCX data broadcasted to centralized manager")

            except (ImportError, AttributeError):
                logger.debug("Centralized manager not available for MCX broadcast")

            # Integration with unified WebSocket manager
            try:
                from services.unified_websocket_manager import unified_manager
                if unified_manager:
                    await unified_manager.broadcast_data({
                        'type': 'mcx_data',
                        'data': data.get('analytics', {}),
                        'source': 'mcx_service'
                    })
                    logger.debug("📡 MCX data sent to unified manager")

            except (ImportError, AttributeError):
                logger.debug("Unified manager not available for MCX broadcast")

        except Exception as e:
            logger.error(f"❌ Error broadcasting MCX data: {e}")

    async def _data_aggregation_service(self):
        """Background service for data aggregation"""
        try:
            while self.is_running:
                try:
                    if self.mcx_client and self.mcx_client.data_processor:
                        # Generate comprehensive analytics every 5 minutes
                        analytics = self.mcx_client.data_processor.get_analytics()

                        if analytics:
                            # Save analytics snapshot
                            snapshot = {
                                'timestamp': datetime.now().isoformat(),
                                'analytics': analytics,
                                'service_stats': self.service_stats.copy()
                            }

                            # Store in aggregated data
                            self.aggregated_data['daily_summary'] = snapshot

                            logger.debug("📊 Data aggregation completed")

                    await asyncio.sleep(300)  # 5 minutes

                except Exception as e:
                    logger.error(f"❌ Error in data aggregation service: {e}")
                    await asyncio.sleep(60)

        except asyncio.CancelledError:
            logger.info("Data aggregation service stopped")

    async def _health_monitoring_service(self):
        """Background health monitoring service"""
        heartbeat_counter = 0
        try:
            while self.is_running:
                try:
                    # Update uptime
                    if self.service_start_time:
                        uptime = (datetime.now() - self.service_start_time).total_seconds()
                        self.service_stats['total_uptime_seconds'] = uptime

                    # Heartbeat every 15 minutes
                    heartbeat_counter += 1
                    if heartbeat_counter >= 15:
                        logger.info(f"💓 MCX Service Heartbeat: Health monitor active at {datetime.now().strftime('%H:%M:%S')}")
                        logger.info(f"📊 MCX Stats: Uptime={uptime/3600:.1f}h, Data Points={self.service_stats['data_points_processed']}")
                        heartbeat_counter = 0

                    # Check client health
                    if self.mcx_client:
                        client_stats = self.mcx_client.stats

                        # Check for stale data
                        if client_stats.get('last_message_time'):
                            time_since_last = (datetime.now() - client_stats['last_message_time']).total_seconds()

                            if time_since_last > 300:  # 5 minutes without data
                                logger.warning(f"⚠️ No MCX data received for {time_since_last/60:.1f} minutes")

                    await asyncio.sleep(60)  # Check every minute

                except Exception as e:
                    logger.error(f"❌ Error in health monitoring: {e}")
                    await asyncio.sleep(60)

        except asyncio.CancelledError:
            logger.info("Health monitoring service stopped")

    async def _periodic_export_service(self):
        """Background service for periodic data export"""
        try:
            while self.is_running:
                try:
                    # Export data every hour during market hours
                    if self._is_market_hours() and self.mcx_client:
                        export_path = f"data/mcx_export/{datetime.now().strftime('%Y%m%d')}"
                        self.mcx_client.export_data(export_path)
                        logger.info(f"📁 MCX data exported to {export_path}")

                    await asyncio.sleep(3600)  # 1 hour

                except Exception as e:
                    logger.error(f"❌ Error in periodic export: {e}")
                    await asyncio.sleep(3600)

        except asyncio.CancelledError:
            logger.info("Periodic export service stopped")

    def _is_market_hours(self) -> bool:
        """Check if current time is within market hours"""
        current_time = datetime.now().time()
        return self.market_hours["start"] <= current_time <= self.market_hours["end"]

    def _get_next_market_open(self) -> datetime:
        """Get next market opening time"""
        now = datetime.now()
        today_open = datetime.combine(now.date(), self.market_hours["start"])

        if now.time() < self.market_hours["start"]:
            return today_open
        else:
            return today_open + timedelta(days=1)

    def _get_uptime_hours(self) -> float:
        """Get service uptime in hours"""
        if self.service_start_time:
            return (datetime.now() - self.service_start_time).total_seconds() / 3600
        return 0

    async def _wait_for_market_hours(self):
        """Wait until market opens"""
        while not self._is_market_hours() and self.is_running:
            await asyncio.sleep(60)  # Check every minute

    # Public API methods

    def get_service_status(self) -> Dict:
        """Get comprehensive service status"""
        return {
            "is_running": self.is_running,
            "market_hours": self._is_market_hours(),
            "auto_restart": self.auto_restart,
            "client_status": self.mcx_client.is_running if self.mcx_client else False,
            "service_stats": self.service_stats,
            "uptime_hours": self._get_uptime_hours(),
            "instruments_count": len(self.mcx_client.mcx_instruments) if self.mcx_client else 0,
            "last_data_time": self.mcx_client.stats.get('last_message_time') if self.mcx_client else None
        }

    def get_analytics_summary(self) -> Dict:
        """Get analytics summary"""
        return self.aggregated_data

    def get_symbol_data(self, symbol: str) -> Dict:
        """Get all data for a specific symbol"""
        if self.mcx_client:
            return self.mcx_client.get_symbol_dataframes(symbol)
        return {}

    def get_market_overview(self) -> Dict:
        """Get market overview with pandas analytics"""
        try:
            if not self.mcx_client or not self.mcx_client.data_processor.price_data_df is not None:
                return {"error": "No data available"}

            df = self.mcx_client.data_processor.price_data_df
            latest_data = df.groupby('instrument_key').last()

            return {
                "total_instruments": len(latest_data),
                "active_symbols": latest_data['symbol'].nunique(),
                "avg_change_percent": float(latest_data['change_percent'].mean()),
                "max_change_percent": float(latest_data['change_percent'].max()),
                "min_change_percent": float(latest_data['change_percent'].min()),
                "total_volume": float(latest_data['volume'].sum()),
                "top_performers": latest_data.nlargest(5, 'change_percent')[
                    ['symbol', 'change_percent', 'volume']
                ].to_dict('records'),
                "last_update": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error generating market overview: {e}")
            return {"error": str(e)}

    async def export_all_data(self, base_path: str = None):
        """Export all data to CSV files"""
        if self.mcx_client:
            export_path = base_path or f"data/mcx_export/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.mcx_client.export_data(export_path)
            logger.info(f"📁 All MCX data exported to {export_path}")

    async def stop_service(self):
        """Stop the MCX service and cleanup"""
        logger.info("🛑 Stopping MCX service")
        self.is_running = False
        self.auto_restart = False

        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()

        # Stop MCX client
        if self.mcx_client:
            await self.mcx_client.stop()
            self.mcx_client = None

        logger.info("✅ MCX service stopped successfully")


# Singleton instance
mcx_service_manager = MCXServiceManager()


# Integration functions for app startup
async def start_mcx_service_auto():
    """Auto-start MCX service during app initialization"""
    try:
        logger.info("🚀 Auto-starting MCX service...")
        success = await mcx_service_manager.start_service()

        if success:
            logger.info("✅ MCX service auto-started successfully")
        else:
            logger.warning("⚠️ MCX service auto-start failed")

        return success

    except Exception as e:
        logger.error(f"❌ Error in MCX auto-start: {e}")
        return False


async def integrate_mcx_with_app():
    """Integrate MCX service with main application"""
    try:
        logger.info("🔧 Integrating MCX service with application...")

        # Schedule MCX service startup
        asyncio.create_task(start_mcx_service_auto())

        logger.info("✅ MCX service integrated with application")

    except Exception as e:
        logger.error(f"❌ MCX integration error: {e}")


# Health check endpoint integration
def get_mcx_health() -> Dict:
    """Health check for MCX service"""
    return mcx_service_manager.get_service_status()