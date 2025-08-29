# services/websocket_auth_service.py
"""
JWT-based WebSocket Authentication Service
Integrates with existing auth_service.py for seamless user identification
"""

import jwt
import logging
from typing import List, Optional, Dict, Any
from fastapi import WebSocket, WebSocketException, status
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import User
from services.auth_service import SECRET_KEY, ALGORITHM, decode_access_token
from datetime import datetime

logger = logging.getLogger(__name__)


class WebSocketAuthService:
    """
    Handles JWT-based authentication for WebSocket connections
    Integrates with existing auth_service.py
    """

    def __init__(self):
        self.active_sessions = {}  # user_id -> {ws, last_activity, page_contexts}

    async def authenticate_websocket(
        self,
        websocket: WebSocket,
        token: Optional[str] = None,
        query_params: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Authenticate WebSocket connection using multiple methods:
        1. JWT token from query params
        2. JWT token from headers
        3. Fallback to anonymous user
        """
        user_info = None

        try:
            # Method 1: Token from query parameters
            if not token and query_params:
                token = query_params.get("token") or query_params.get("access_token")

            # Method 2: Token from WebSocket headers (if available)
            if not token:
                headers = dict(websocket.headers)
                auth_header = headers.get("authorization", "")
                if auth_header.startswith("Bearer "):
                    token = auth_header[7:]

            # Method 3: Try to decode token if available
            if token:
                try:
                    payload = decode_access_token(token)
                    user_email = payload.get("sub")

                    if user_email:
                        # Get user from database
                        db: Session = next(get_db())
                        user = db.query(User).filter(User.email == user_email).first()

                        if user:
                            user_info = {
                                "user_id": str(user.id),
                                "email": user.email,
                                "username": user.username or user.email.split("@")[0],
                                "auth_method": "jwt",
                                "is_authenticated": True,
                            }
                            logger.info(
                                f"✅ Authenticated WebSocket user: {user.email} (ID: {user.id})"
                            )
                        else:
                            logger.warning(
                                f"⚠️ JWT valid but user not found: {user_email}"
                            )

                except jwt.ExpiredSignatureError:
                    logger.warning("⚠️ WebSocket JWT token expired")
                except jwt.InvalidTokenError as e:
                    logger.warning(f"⚠️ Invalid WebSocket JWT token: {e}")
                except Exception as e:
                    logger.error(f"❌ Error validating WebSocket JWT: {e}")

            # Fallback: Anonymous user with session tracking
            if not user_info:
                anonymous_id = self._generate_anonymous_id(query_params)
                user_info = {
                    "user_id": anonymous_id,
                    "email": None,
                    "username": f"anonymous_{anonymous_id[:8]}",
                    "auth_method": "anonymous",
                    "is_authenticated": False,
                }
                logger.info(f"🔓 Anonymous WebSocket connection: {anonymous_id}")

        except Exception as e:
            logger.error(f"❌ WebSocket authentication error: {e}")
            # Still allow connection with anonymous user
            anonymous_id = self._generate_anonymous_id(query_params)
            user_info = {
                "user_id": anonymous_id,
                "email": None,
                "username": f"guest_{anonymous_id[:8]}",
                "auth_method": "fallback",
                "is_authenticated": False,
            }

        return user_info

    def _generate_anonymous_id(self, query_params: Dict[str, Any] = None) -> str:
        """Generate consistent anonymous ID from session info"""

        # Try to use existing session identifiers
        if query_params:
            session_id = query_params.get("session_id") or query_params.get("user_id")
            if session_id and session_id.startswith(("user_", "session_")):
                return session_id

        # Generate new anonymous ID
        import uuid

        return f"anonymous_{uuid.uuid4().hex[:12]}"

    def register_user_session(
        self, user_id: str, websocket: WebSocket, page_context: str = "dashboard"
    ):
        """Register user session with page context tracking"""

        if user_id not in self.active_sessions:
            self.active_sessions[user_id] = {
                "websocket": websocket,
                "last_activity": datetime.now(),
                "page_contexts": {page_context},
                "connection_count": 1,
            }
            logger.info(f"📱 New user session: {user_id} (context: {page_context})")
        else:
            # Update existing session
            session = self.active_sessions[user_id]
            session["websocket"] = websocket  # Replace with latest connection
            session["last_activity"] = datetime.now()
            session["page_contexts"].add(page_context)
            session["connection_count"] = session.get("connection_count", 0) + 1

            logger.info(
                f"🔄 Updated user session: {user_id} (contexts: {session['page_contexts']})"
            )

    def unregister_user_session(self, user_id: str, page_context: str = None):
        """Unregister user session"""
        if user_id in self.active_sessions:
            session = self.active_sessions[user_id]

            if page_context and page_context in session["page_contexts"]:
                session["page_contexts"].discard(page_context)

            # Remove session if no more page contexts
            if not session["page_contexts"]:
                del self.active_sessions[user_id]
                logger.info(f"🗑️ Removed user session: {user_id}")
            else:
                logger.info(
                    f"📱 Updated user session contexts: {user_id} -> {session['page_contexts']}"
                )

    def get_active_sessions(self) -> Dict[str, Any]:
        """Get statistics about active sessions"""
        stats = {
            "total_sessions": len(self.active_sessions),
            "authenticated_users": 0,
            "anonymous_users": 0,
            "page_contexts": {},
        }

        for user_id, session in self.active_sessions.items():
            if user_id.startswith("anonymous_"):
                stats["anonymous_users"] += 1
            else:
                stats["authenticated_users"] += 1

            # Count page contexts
            for context in session["page_contexts"]:
                stats["page_contexts"][context] = (
                    stats["page_contexts"].get(context, 0) + 1
                )

        return stats

    def broadcast_to_user_contexts(
        self, user_id: str, message: Dict[str, Any], target_contexts: List[str] = None
    ):
        """
        Send message to user's WebSocket if they're viewing specific page contexts
        """
        if user_id not in self.active_sessions:
            return False

        session = self.active_sessions[user_id]
        websocket = session["websocket"]
        user_contexts = session["page_contexts"]

        # Check if user has any of the target contexts
        if target_contexts:
            if not any(context in user_contexts for context in target_contexts):
                return False  # User not viewing relevant pages

        try:
            # Send message to user's single WebSocket connection
            import asyncio

            asyncio.create_task(websocket.send_json(message))
            session["last_activity"] = datetime.now()
            return True

        except Exception as e:
            logger.error(f"❌ Error sending message to user {user_id}: {e}")
            # Clean up broken session
            self.unregister_user_session(user_id)
            return False


# Global instance
websocket_auth_service = WebSocketAuthService()
