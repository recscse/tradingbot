"""
Socket.IO Manager for Auto-Trading System
Centralizes all real-time communication between frontend and backend
Standardizes event names and data structures for consistency
"""

import asyncio
import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict
import socketio
from fastapi import FastAPI

logger = logging.getLogger(__name__)

# Standardized WebSocket Event Names
class SocketEvents:
    # Auto Trading Events
    AUTO_STOCK_UPDATE = "auto_stock_update"
    TRADING_SESSION_UPDATE = "trading_session_update" 
    MARKET_SENTIMENT_UPDATE = "market_sentiment_update"
    
    # Strategy Events
    FIBONACCI_SIGNAL = "fibonacci_signal"
    NIFTY_STRATEGY_UPDATE = "nifty_strategy_update"
    STRATEGY_STATUS_CHANGE = "strategy_status_change"
    
    # Position & Trading Events
    POSITION_UPDATE = "position_update"
    TRADE_EXECUTED = "trade_executed"
    ORDER_UPDATE = "order_update"
    PRICE_UPDATE = "price_update"
    
    # System Events
    SYSTEM_STATUS = "system_status"
    EMERGENCY_ALERT = "emergency_alert"
    PERFORMANCE_UPDATE = "performance_update"
    RISK_ALERT = "risk_alert"
    
    # Connection Events
    CLIENT_CONNECTED = "client_connected"
    CLIENT_DISCONNECTED = "client_disconnected"

@dataclass
class SocketMessage:
    """Standardized message structure for all Socket.IO events"""
    event: str
    data: Dict[str, Any]
    timestamp: str
    source: str = "auto_trading_system"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class AutoTradingSocketManager:
    """
    Socket.IO Manager for Auto-Trading System
    Handles all real-time communication with consistent event structure
    """
    
    def __init__(self):
        self.sio = socketio.AsyncServer(
            async_mode='asgi',
            cors_allowed_origins="*",
            logger=logger,
            engineio_logger=False
        )
        self.connected_clients = {}  # {session_id: client_info}
        self.namespaces = {
            '/auto-trading': 'Auto Trading System',
            '/market-data': 'Market Data Feed', 
            '/strategy': 'Trading Strategies',
            '/performance': 'Performance Monitoring'
        }
        self.setup_handlers()
        
    def setup_handlers(self):
        """Setup Socket.IO event handlers"""
        
        @self.sio.event
        async def connect(sid, environ, auth):
            """Handle client connection"""
            try:
                client_info = {
                    'session_id': sid,
                    'connected_at': datetime.now(timezone.utc).isoformat(),
                    'namespace': '/',
                    'user_agent': environ.get('HTTP_USER_AGENT', 'Unknown')
                }
                self.connected_clients[sid] = client_info
                
                logger.info(f"✅ Client connected: {sid}")
                
                # Send initial system status
                await self.emit_system_status(sid)
                
            except Exception as e:
                logger.error(f"❌ Error handling connection: {e}")
        
        @self.sio.event
        async def disconnect(sid):
            """Handle client disconnection"""
            try:
                if sid in self.connected_clients:
                    client_info = self.connected_clients.pop(sid)
                    logger.info(f"🔌 Client disconnected: {sid}")
                
            except Exception as e:
                logger.error(f"❌ Error handling disconnection: {e}")
        
        # Namespace handlers
        for namespace in self.namespaces:
            self.setup_namespace_handlers(namespace)
    
    def setup_namespace_handlers(self, namespace: str):
        """Setup handlers for specific namespace"""
        
        @self.sio.event(namespace=namespace)
        async def connect(sid, environ, auth):
            """Handle namespace connection"""
            try:
                client_info = {
                    'session_id': sid,
                    'connected_at': datetime.now(timezone.utc).isoformat(),
                    'namespace': namespace,
                    'user_agent': environ.get('HTTP_USER_AGENT', 'Unknown')
                }
                self.connected_clients[f"{namespace}:{sid}"] = client_info
                
                logger.info(f"✅ Client connected to {namespace}: {sid}")
                
                # Send namespace-specific initial data
                if namespace == '/auto-trading':
                    await self.emit_auto_trading_status(sid, namespace)
                elif namespace == '/market-data':
                    await self.emit_market_data_status(sid, namespace)
                elif namespace == '/strategy':
                    await self.emit_strategy_status(sid, namespace)
                elif namespace == '/performance':
                    await self.emit_performance_status(sid, namespace)
                    
            except Exception as e:
                logger.error(f"❌ Error handling {namespace} connection: {e}")
        
        @self.sio.event(namespace=namespace)
        async def disconnect(sid):
            """Handle namespace disconnection"""
            try:
                key = f"{namespace}:{sid}"
                if key in self.connected_clients:
                    self.connected_clients.pop(key)
                    logger.info(f"🔌 Client disconnected from {namespace}: {sid}")
                    
            except Exception as e:
                logger.error(f"❌ Error handling {namespace} disconnection: {e}")
    
    async def emit_to_namespace(self, namespace: str, event: str, data: Dict[str, Any]):
        """Emit event to all clients in a namespace"""
        try:
            message = SocketMessage(
                event=event,
                data=data,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            await self.sio.emit(event, message.to_dict(), namespace=namespace)
            logger.debug(f"📡 Emitted {event} to {namespace}")
            
        except Exception as e:
            logger.error(f"❌ Error emitting to {namespace}: {e}")
    
    async def emit_to_all(self, event: str, data: Dict[str, Any]):
        """Emit event to all connected clients"""
        try:
            message = SocketMessage(
                event=event,
                data=data,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            await self.sio.emit(event, message.to_dict())
            logger.debug(f"📡 Broadcasted {event} to all clients")
            
        except Exception as e:
            logger.error(f"❌ Error broadcasting event: {e}")
    
    # Auto-Trading Specific Events
    async def emit_fibonacci_signal(self, signal_data: Dict[str, Any]):
        """Emit Fibonacci signal to auto-trading clients"""
        await self.emit_to_namespace('/auto-trading', SocketEvents.FIBONACCI_SIGNAL, signal_data)
    
    async def emit_position_update(self, position_data: Dict[str, Any]):
        """Emit position update to auto-trading clients"""
        await self.emit_to_namespace('/auto-trading', SocketEvents.POSITION_UPDATE, position_data)
    
    async def emit_trade_executed(self, trade_data: Dict[str, Any]):
        """Emit trade execution notification"""
        await self.emit_to_namespace('/auto-trading', SocketEvents.TRADE_EXECUTED, trade_data)
    
    async def emit_auto_stock_update(self, stocks_data: Dict[str, Any]):
        """Emit auto stock selection update"""
        await self.emit_to_namespace('/auto-trading', SocketEvents.AUTO_STOCK_UPDATE, stocks_data)
    
    async def emit_emergency_alert(self, alert_data: Dict[str, Any]):
        """Emit emergency alert to all clients"""
        await self.emit_to_all(SocketEvents.EMERGENCY_ALERT, alert_data)
    
    async def emit_system_status(self, sid: str = None, namespace: str = "/"):
        """Emit current system status"""
        try:
            status_data = {
                'system_health': 'HEALTHY',
                'active_clients': len(self.connected_clients),
                'uptime': 'System Running',
                'last_update': datetime.now(timezone.utc).isoformat()
            }
            
            if sid:
                message = SocketMessage(
                    event=SocketEvents.SYSTEM_STATUS,
                    data=status_data,
                    timestamp=datetime.now(timezone.utc).isoformat()
                )
                await self.sio.emit(SocketEvents.SYSTEM_STATUS, message.to_dict(), to=sid, namespace=namespace)
            else:
                await self.emit_to_all(SocketEvents.SYSTEM_STATUS, status_data)
                
        except Exception as e:
            logger.error(f"❌ Error emitting system status: {e}")
    
    async def emit_auto_trading_status(self, sid: str, namespace: str):
        """Emit auto-trading specific status"""
        try:
            status_data = {
                'trading_active': False,
                'selected_stocks': [],
                'active_strategies': [],
                'daily_pnl': 0.0,
                'active_positions': 0
            }
            
            message = SocketMessage(
                event=SocketEvents.TRADING_SESSION_UPDATE,
                data=status_data,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            await self.sio.emit(
                SocketEvents.TRADING_SESSION_UPDATE, 
                message.to_dict(), 
                to=sid, 
                namespace=namespace
            )
            
        except Exception as e:
            logger.error(f"❌ Error emitting auto-trading status: {e}")
    
    async def emit_market_data_status(self, sid: str, namespace: str):
        """Emit market data status"""
        try:
            status_data = {
                'feed_status': 'CONNECTED',
                'instruments_subscribed': 0,
                'last_price_update': None
            }
            
            message = SocketMessage(
                event=SocketEvents.PRICE_UPDATE,
                data=status_data,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            await self.sio.emit(
                SocketEvents.PRICE_UPDATE, 
                message.to_dict(), 
                to=sid, 
                namespace=namespace
            )
            
        except Exception as e:
            logger.error(f"❌ Error emitting market data status: {e}")
    
    async def emit_strategy_status(self, sid: str, namespace: str):
        """Emit strategy status"""
        try:
            status_data = {
                'fibonacci_active': False,
                'nifty_strategy_active': False,
                'signals_generated': 0,
                'last_signal': None
            }
            
            message = SocketMessage(
                event=SocketEvents.STRATEGY_STATUS_CHANGE,
                data=status_data,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            await self.sio.emit(
                SocketEvents.STRATEGY_STATUS_CHANGE, 
                message.to_dict(), 
                to=sid, 
                namespace=namespace
            )
            
        except Exception as e:
            logger.error(f"❌ Error emitting strategy status: {e}")
    
    async def emit_performance_status(self, sid: str, namespace: str):
        """Emit performance monitoring status"""
        try:
            status_data = {
                'system_latency': 0,
                'execution_speed': 0,
                'memory_usage': 0,
                'active_connections': len(self.connected_clients)
            }
            
            message = SocketMessage(
                event=SocketEvents.PERFORMANCE_UPDATE,
                data=status_data,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            await self.sio.emit(
                SocketEvents.PERFORMANCE_UPDATE, 
                message.to_dict(), 
                to=sid, 
                namespace=namespace
            )
            
        except Exception as e:
            logger.error(f"❌ Error emitting performance status: {e}")
    
    def get_app(self, fastapi_app: FastAPI):
        """Get Socket.IO ASGI app integrated with FastAPI"""
        return socketio.ASGIApp(self.sio, other_asgi_app=fastapi_app)
    
    def get_connection_count(self) -> int:
        """Get total number of connected clients"""
        return len(self.connected_clients)
    
    def get_namespace_clients(self, namespace: str) -> List[str]:
        """Get clients connected to specific namespace"""
        return [
            key.split(':')[1] for key in self.connected_clients.keys() 
            if key.startswith(f"{namespace}:")
        ]

# Global Socket.IO manager instance
auto_trading_socket_manager = AutoTradingSocketManager()

# Convenience functions for easy integration
async def emit_fibonacci_signal(signal_data: Dict[str, Any]):
    """Convenience function to emit Fibonacci signal"""
    await auto_trading_socket_manager.emit_fibonacci_signal(signal_data)

async def emit_position_update(position_data: Dict[str, Any]):
    """Convenience function to emit position update"""
    await auto_trading_socket_manager.emit_position_update(position_data)

async def emit_trade_executed(trade_data: Dict[str, Any]):
    """Convenience function to emit trade execution"""
    await auto_trading_socket_manager.emit_trade_executed(trade_data)

async def emit_auto_stock_update(stocks_data: Dict[str, Any]):
    """Convenience function to emit stock update"""
    await auto_trading_socket_manager.emit_auto_stock_update(stocks_data)

async def emit_emergency_alert(alert_data: Dict[str, Any]):
    """Convenience function to emit emergency alert"""
    await auto_trading_socket_manager.emit_emergency_alert(alert_data)

async def emit_system_status():
    """Convenience function to emit system status"""
    await auto_trading_socket_manager.emit_system_status()

logger.info("✅ Auto-Trading Socket.IO Manager initialized")