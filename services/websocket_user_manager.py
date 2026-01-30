# services/websocket_user_manager.py
"""
Enhanced WebSocket User Management
Handles user registration, connection tracking, and cleanup
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Set, Optional
from dataclasses import dataclass, field
from fastapi import WebSocket

logger = logging.getLogger(__name__)

@dataclass
class UserConnection:
    client_id: str
    client_type: str
    websocket: WebSocket
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    message_count: int = 0
    is_active: bool = True

@dataclass 
class UserSession:
    user_id: str
    connections: Dict[str, UserConnection] = field(default_factory=dict)  # client_type -> UserConnection
    first_connected: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    total_connections: int = 0
    
    def get_active_connections(self) -> Dict[str, UserConnection]:
        return {k: v for k, v in self.connections.items() if v.is_active}
    
    def update_activity(self):
        self.last_activity = datetime.now()
        
    def add_connection(self, client_type: str, connection: UserConnection):
        # Close existing connection of same type
        if client_type in self.connections:
            old_connection = self.connections[client_type]
            old_connection.is_active = False
            
        self.connections[client_type] = connection
        self.total_connections += 1
        self.update_activity()
        
    def remove_connection(self, client_type: str):
        if client_type in self.connections:
            self.connections[client_type].is_active = False
            del self.connections[client_type]


class WebSocketUserManager:
    def __init__(self):
        self.users: Dict[str, UserSession] = {}
        self.client_to_user: Dict[str, str] = {}  # client_id -> user_id
        self.connection_metadata: Dict[str, Dict] = {}
        self.cleanup_task = None
        self._locks = {}
        
    def _get_lock(self):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return None
            
        if not hasattr(loop, '_websocket_user_manager_lock'):
            loop._websocket_user_manager_lock = asyncio.Lock()
        return loop._websocket_user_manager_lock
    
    async def register_user_connection(
        self, 
        user_id: str, 
        client_type: str, 
        client_id: str,
        websocket: WebSocket
    ) -> bool:
        """Register a new user connection, cleaning up duplicates"""
        # Ensure cleanup task is running
        self.start_cleanup_task()
        
        lock = self._get_lock()
        if not lock:
            logger.error("❌ No event loop running for registration")
            return False

        async with lock:
            try:
                # Create user session if doesn't exist
                if user_id not in self.users:
                    self.users[user_id] = UserSession(user_id=user_id)
                    logger.info(f"👤 New user session created: {user_id}")
                
                user_session = self.users[user_id]
                
                # Close existing connection of same type
                await self._cleanup_user_connection_type(user_id, client_type)
                
                # Create new connection
                connection = UserConnection(
                    client_id=client_id,
                    client_type=client_type,
                    websocket=websocket
                )
                
                # Register connection
                user_session.add_connection(client_type, connection)
                self.client_to_user[client_id] = user_id
                
                # Store connection metadata
                self.connection_metadata[client_id] = {
                    'user_id': user_id,
                    'client_type': client_type,
                    'created_at': datetime.now(),
                    'connection_count': user_session.total_connections
                }
                
                logger.info(
                    f"✅ Registered connection: {client_id} "
                    f"(user: {user_id}, type: {client_type}, total: {len(user_session.get_active_connections())})"
                )
                
                return True
                
            except Exception as e:
                logger.error(f"❌ Error registering user connection: {e}")
                return False
    
    async def _cleanup_user_connection_type(self, user_id: str, client_type: str):
        """Close existing connection of same type for a user"""
        if user_id not in self.users:
            return
            
        user_session = self.users[user_id]
        if client_type not in user_session.connections:
            return
            
        old_connection = user_session.connections[client_type]
        if not old_connection.is_active:
            return
            
        try:
            logger.info(f"🧹 Closing existing {client_type} connection: {old_connection.client_id}")
            
            # Close WebSocket
            if old_connection.websocket and hasattr(old_connection.websocket, 'close'):
                await old_connection.websocket.close(
                    code=1000, 
                    reason=f"New {client_type} connection established"
                )
            
            # Clean up tracking
            old_connection.is_active = False
            if old_connection.client_id in self.client_to_user:
                del self.client_to_user[old_connection.client_id]
            if old_connection.client_id in self.connection_metadata:
                del self.connection_metadata[old_connection.client_id]
                
        except Exception as e:
            logger.error(f"❌ Error closing existing connection: {e}")
    
    async def unregister_connection(self, client_id: str):
        """Unregister a connection when it closes"""
        lock = self._get_lock()
        if not lock: return
        async with lock:
            try:
                if client_id not in self.client_to_user:
                    return
                    
                user_id = self.client_to_user[client_id]
                if user_id not in self.users:
                    return
                    
                user_session = self.users[user_id]
                metadata = self.connection_metadata.get(client_id, {})
                client_type = metadata.get('client_type', 'unknown')
                
                # Remove connection
                user_session.remove_connection(client_type)
                
                # Clean up tracking
                del self.client_to_user[client_id]
                if client_id in self.connection_metadata:
                    del self.connection_metadata[client_id]
                
                # Remove user session if no active connections
                active_connections = user_session.get_active_connections()
                if not active_connections:
                    del self.users[user_id]
                    logger.info(f"🗑️ Removed user session (no active connections): {user_id}")
                else:
                    logger.info(f"🔌 Connection closed: {client_id} (user: {user_id}, remaining: {len(active_connections)})")
                    
            except Exception as e:
                logger.error(f"❌ Error unregistering connection: {e}")
    
    def update_connection_activity(self, client_id: str):
        """Update last activity timestamp for a connection"""
        try:
            if client_id not in self.client_to_user:
                return
                
            user_id = self.client_to_user[client_id]
            if user_id not in self.users:
                return
                
            user_session = self.users[user_id]
            user_session.update_activity()
            
            # Update connection activity
            metadata = self.connection_metadata.get(client_id, {})
            client_type = metadata.get('client_type')
            if client_type and client_type in user_session.connections:
                user_session.connections[client_type].last_activity = datetime.now()
                user_session.connections[client_type].message_count += 1
                
        except Exception as e:
            logger.error(f"❌ Error updating connection activity: {e}")
    
    def get_user_connections(self, user_id: str) -> Dict[str, UserConnection]:
        """Get all active connections for a user"""
        if user_id not in self.users:
            return {}
        return self.users[user_id].get_active_connections()
    
    def get_connection_info(self, client_id: str) -> Optional[Dict]:
        """Get information about a specific connection"""
        if client_id not in self.connection_metadata:
            return None
            
        metadata = self.connection_metadata[client_id].copy()
        
        # Add runtime info
        if client_id in self.client_to_user:
            user_id = self.client_to_user[client_id]
            if user_id in self.users:
                user_session = self.users[user_id]
                client_type = metadata.get('client_type')
                if client_type and client_type in user_session.connections:
                    connection = user_session.connections[client_type]
                    metadata.update({
                        'is_active': connection.is_active,
                        'last_activity': connection.last_activity.isoformat(),
                        'message_count': connection.message_count,
                        'uptime_minutes': (datetime.now() - connection.created_at).total_seconds() / 60
                    })
        
        return metadata
    
    def get_system_stats(self) -> Dict:
        """Get system-wide connection statistics"""
        total_users = len(self.users)
        total_connections = sum(len(user.get_active_connections()) for user in self.users.values())
        
        connection_types = {}
        active_users = 0
        idle_connections = 0
        now = datetime.now()
        
        for user_session in self.users.values():
            user_has_recent_activity = (now - user_session.last_activity).total_seconds() < 300  # 5 minutes
            if user_has_recent_activity:
                active_users += 1
                
            for client_type, connection in user_session.get_active_connections().items():
                connection_types[client_type] = connection_types.get(client_type, 0) + 1
                
                # Check if connection is idle (no activity in 10 minutes)
                if (now - connection.last_activity).total_seconds() > 600:
                    idle_connections += 1
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'total_connections': total_connections,
            'idle_connections': idle_connections,
            'connection_types': connection_types,
            'avg_connections_per_user': round(total_connections / max(total_users, 1), 2),
            'system_uptime': self.get_uptime(),
            'last_updated': now.isoformat()
        }
    
    def get_uptime(self) -> str:
        """Get system uptime (placeholder - would track actual start time)"""
        # This would track actual system start time in a real implementation
        return "System uptime tracking not implemented"
    
    def start_cleanup_task(self):
        """Start background cleanup task"""
        if self.cleanup_task is None:
            self.cleanup_task = asyncio.create_task(self._periodic_cleanup())
            logger.info("🧹 Started periodic cleanup task")
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of stale connections and users"""
        while True:
            try:
                await asyncio.sleep(120)  # Run every 2 minutes
                await self._cleanup_stale_connections()
                await self._cleanup_inactive_users()
                
            except asyncio.CancelledError:
                logger.info("🛑 Cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Error in periodic cleanup: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _cleanup_stale_connections(self):
        """Clean up connections that are stale or dead"""
        stale_connections = []
        now = datetime.now()
        stale_threshold = timedelta(minutes=10)
        
        lock = self._get_lock()
        if not lock: return
        async with lock:
            for client_id, user_id in list(self.client_to_user.items()):
                if user_id not in self.users:
                    stale_connections.append(client_id)
                    continue
                    
                user_session = self.users[user_id]
                metadata = self.connection_metadata.get(client_id, {})
                client_type = metadata.get('client_type')
                
                if not client_type or client_type not in user_session.connections:
                    stale_connections.append(client_id)
                    continue
                
                connection = user_session.connections[client_type]
                
                # Check if connection is stale
                if now - connection.last_activity > stale_threshold:
                    # Verify WebSocket is actually dead
                    if hasattr(connection.websocket, 'client_state'):
                        try:
                            state = connection.websocket.client_state
                            if state.value > 1:  # CLOSING or CLOSED
                                stale_connections.append(client_id)
                        except:
                            stale_connections.append(client_id)
        
        # Clean up stale connections
        for client_id in stale_connections:
            logger.info(f"🧹 Cleaning up stale connection: {client_id}")
            await self.unregister_connection(client_id)
        
        if stale_connections:
            logger.info(f"🧹 Cleaned up {len(stale_connections)} stale connections")
    
    async def _cleanup_inactive_users(self):
        """Clean up users who have been inactive for a long time"""
        inactive_users = []
        now = datetime.now()
        inactive_threshold = timedelta(hours=1)
        
        lock = self._get_lock()
        if not lock: return
        async with lock:
            for user_id, user_session in list(self.users.items()):
                if now - user_session.last_activity > inactive_threshold:
                    # Only remove if no active connections
                    active_connections = user_session.get_active_connections()
                    if not active_connections:
                        inactive_users.append(user_id)
        
        # Clean up inactive users
        for user_id in inactive_users:
            if user_id in self.users:
                del self.users[user_id]
                logger.info(f"🗑️ Cleaned up inactive user: {user_id}")
        
        if inactive_users:
            logger.info(f"🗑️ Cleaned up {len(inactive_users)} inactive users")
    
    async def shutdown(self):
        """Graceful shutdown of the user manager"""
        logger.info("🛑 Shutting down WebSocket User Manager")
        
        # Cancel cleanup task
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        lock = self._get_lock()
        if not lock: return
        async with lock:
            for user_session in self.users.values():
                for connection in user_session.connections.values():
                    if connection.is_active and connection.websocket:
                        try:
                            await connection.websocket.close(1001, "Server shutting down")
                        except:
                            pass
        
        self.users.clear()
        self.client_to_user.clear()
        self.connection_metadata.clear()


# Global instance
websocket_user_manager = WebSocketUserManager()