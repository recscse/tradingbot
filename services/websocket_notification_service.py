# services/websocket_notification_service.py
"""
WebSocket-based notification service that integrates with the Global WebSocket system
Replaces polling-based notifications with real-time push notifications
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from services.unified_websocket_manager import unified_manager

logger = logging.getLogger(__name__)

class WebSocketNotificationService:
    """
    Service for sending real-time notifications via WebSocket connections
    """
    
    def __init__(self):
        self.notification_types = {
            'trade': 'Trade Execution',
            'alert': 'Price Alert',
            'system': 'System Update',
            'info': 'Information',
            'warning': 'Warning',
            'error': 'Error',
            'success': 'Success'
        }
        # Cache for deduplication: key -> timestamp
        self._sent_cache = {}
        self._dedup_window = 5.0  # 5 seconds deduplication window
        self._cleanup_counter = 0

    def _is_duplicate(self, unique_key: str) -> bool:
        """
        Check if a notification is a duplicate within the time window.
        Also handles cache cleanup periodically.
        """
        import time
        current_time = time.time()
        
        # Periodic cleanup (every 100 checks)
        self._cleanup_counter += 1
        if self._cleanup_counter > 100:
            self._cleanup_counter = 0
            # Remove expired entries
            expired_keys = [k for k, ts in self._sent_cache.items() if current_time - ts > self._dedup_window]
            for k in expired_keys:
                del self._sent_cache[k]
        
        # Check for duplicate
        if unique_key in self._sent_cache:
            last_sent = self._sent_cache[unique_key]
            if current_time - last_sent < self._dedup_window:
                return True
        
        # Update cache
        self._sent_cache[unique_key] = current_time
        return False
    
    def send_notification_to_user(
        self, 
        user_id: str,
        notification_type: str = 'info',
        title: str = '',
        message: str = '',
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send a real-time notification to a specific user via WebSocket
        
        Args:
            user_id: Target user ID
            notification_type: Type of notification (info, success, error, warning, etc.)
            title: Notification title
            message: Notification message
            data: Additional data payload
            
        Returns:
            bool: True if sent successfully to at least one client
        """
        try:
            # Deduplication check
            unique_key = f"{user_id}:{notification_type}:{title}:{message}"
            if self._is_duplicate(unique_key):
                logger.debug(f"🔇 Suppressed duplicate notification for user {user_id}: {title}")
                return False

            notification_payload = {
                'id': f"notif_{datetime.now().timestamp()}_{user_id}",
                'type': notification_type,
                'title': title,
                'message': message,
                'created_at': datetime.utcnow().isoformat(),
                'is_read': False,
                'priority': 'normal',
                'data': data or {}
            }
            
            # Find user's active WebSocket connections
            user_clients = self._get_user_clients(user_id)
            
            if not user_clients:
                logger.warning(f"📭 No active WebSocket connections found for user {user_id}")
                return False
            
            # Send to all user's active connections
            sent_count = 0
            for client_id in user_clients:
                if self._send_to_client(client_id, 'new_notification', notification_payload):
                    sent_count += 1
            
            logger.info(f"📨 Sent notification '{title}' to {sent_count}/{len(user_clients)} clients for user {user_id}")
            return sent_count > 0
            
        except Exception as e:
            logger.error(f"❌ Failed to send notification to user {user_id}: {e}")
            return False
    
    def send_trade_notification(
        self,
        user_id: str,
        symbol: str,
        action: str,
        quantity: int,
        price: float,
        status: str = 'executed'
    ) -> bool:
        """
        Send a trade execution notification
        """
        title = f"Trade {status.title()}: {symbol}"
        message = f"{action.upper()} {quantity} shares of {symbol} at ₹{price:.2f}"
        
        data = {
            'symbol': symbol,
            'action': action,
            'quantity': quantity,
            'price': price,
            'status': status,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return self.send_notification_to_user(
            user_id=user_id,
            notification_type='trade',
            title=title,
            message=message,
            data=data
        )
    
    def send_price_alert(
        self,
        user_id: str,
        symbol: str,
        current_price: float,
        target_price: float,
        alert_type: str = 'target_reached'
    ) -> bool:
        """
        Send a price alert notification
        """
        direction = 'above' if current_price > target_price else 'below'
        title = f"Price Alert: {symbol}"
        message = f"{symbol} is now trading at ₹{current_price:.2f} ({direction} your target of ₹{target_price:.2f})"
        
        data = {
            'symbol': symbol,
            'current_price': current_price,
            'target_price': target_price,
            'alert_type': alert_type,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return self.send_notification_to_user(
            user_id=user_id,
            notification_type='alert',
            title=title,
            message=message,
            data=data
        )
    
    def send_system_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        notification_type: str = 'system'
    ) -> bool:
        """
        Send a system notification (e.g., maintenance, updates, etc.)
        """
        return self.send_notification_to_user(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message
        )
    
    def broadcast_notification(
        self,
        notification_type: str = 'system',
        title: str = '',
        message: str = '',
        data: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Broadcast a notification to all connected users
        
        Returns:
            int: Number of clients notified
        """
        try:
            # Deduplication check
            unique_key = f"broadcast:{notification_type}:{title}:{message}"
            if self._is_duplicate(unique_key):
                logger.debug(f"🔇 Suppressed duplicate broadcast: {title}")
                return 0

            notification_payload = {
                'id': f"broadcast_{datetime.now().timestamp()}",
                'type': notification_type,
                'title': title,
                'message': message,
                'created_at': datetime.utcnow().isoformat(),
                'is_read': False,
                'priority': 'high',
                'data': data or {},
                'broadcast': True
            }
            
            # Get all active connections
            if not hasattr(unified_manager, 'connections') or not unified_manager.connections:
                logger.warning("📭 No active WebSocket connections for broadcast")
                return 0
            
            sent_count = 0
            for client_id in unified_manager.connections:
                if self._send_to_client(client_id, 'new_notification', notification_payload):
                    sent_count += 1
            
            logger.info(f"📢 Broadcast notification '{title}' sent to {sent_count} clients")
            return sent_count
            
        except Exception as e:
            logger.error(f"❌ Failed to broadcast notification: {e}")
            return 0
    
    def _get_user_clients(self, user_id: str) -> List[str]:
        """
        Get all active WebSocket client IDs for a specific user
        """
        try:
            if not hasattr(unified_manager, 'connections') or not unified_manager.connections:
                return []
            
            user_clients = []
            for client_id in unified_manager.connections:
                # Check if client_id contains the user_id
                # Client IDs follow pattern: {client_type}_{user_id}_{session_suffix}
                if user_id in client_id:
                    user_clients.append(client_id)
            
            return user_clients
            
        except Exception as e:
            logger.error(f"❌ Error getting user clients for {user_id}: {e}")
            return []
    
    def _send_to_client(self, client_id: str, message_type: str, data: Dict[str, Any]) -> bool:
        """
        Send a message to a specific WebSocket client
        """
        try:
            if not hasattr(unified_manager, 'connections') or client_id not in unified_manager.connections:
                return False
            
            websocket = unified_manager.connections[client_id]
            
            # Check if WebSocket is still open
            if websocket.client_state.name != 'CONNECTED':
                logger.warning(f"⚠️ WebSocket {client_id} is not connected")
                return False
            
            # Send the notification
            message = {
                'type': message_type,
                'data': data,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Use unified_manager's send method
            unified_manager.send_to_client(client_id, json.dumps(message))
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send message to client {client_id}: {e}")
            return False
    
    def get_notification_stats(self) -> Dict[str, Any]:
        """
        Get statistics about notification delivery
        """
        try:
            total_connections = len(unified_manager.connections) if hasattr(unified_manager, 'connections') else 0
            
            # Group connections by user (approximate)
            unique_users = set()
            for client_id in (unified_manager.connections or []):
                # Extract user part from client_id
                parts = client_id.split('_')
                if len(parts) >= 2:
                    unique_users.add(parts[1])  # Assuming format: type_user_session
            
            return {
                'total_connections': total_connections,
                'unique_users': len(unique_users),
                'service_status': 'active',
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting notification stats: {e}")
            return {
                'total_connections': 0,
                'unique_users': 0,
                'service_status': 'error',
                'error': str(e),
                'last_updated': datetime.utcnow().isoformat()
            }

# Create singleton instance
websocket_notification_service = WebSocketNotificationService()

# Convenience functions for easy usage
def send_trade_notification(user_id: str, symbol: str, action: str, quantity: int, price: float) -> bool:
    """Send trade execution notification via WebSocket"""
    return websocket_notification_service.send_trade_notification(user_id, symbol, action, quantity, price)

def send_price_alert(user_id: str, symbol: str, current_price: float, target_price: float) -> bool:
    """Send price alert notification via WebSocket"""
    return websocket_notification_service.send_price_alert(user_id, symbol, current_price, target_price)

def send_user_notification(user_id: str, title: str, message: str, notification_type: str = 'info') -> bool:
    """Send general notification to user via WebSocket"""
    return websocket_notification_service.send_notification_to_user(user_id, notification_type, title, message)

def broadcast_system_notification(title: str, message: str) -> int:
    """Broadcast system notification to all users"""
    return websocket_notification_service.broadcast_notification('system', title, message)