# services/auth/google_auth_service.py
import requests
import logging
import os
from datetime import datetime, timedelta, timezone
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from services.auth_service import create_access_token, create_refresh_token
from database.models import User
from sqlalchemy.orm import Session
from passlib.context import CryptContext

# Import from config (which reads from .env)
try:
    from core.config import GOOGLE_CLIENT_ID
except ImportError:
    # Fallback to direct environment variable if config import fails
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class GoogleAuthService:
    @staticmethod
    def verify_google_token(token: str, token_type: str = "id_token"):
        """Verify Google token - handles both ID tokens and access tokens"""
        if not GOOGLE_CLIENT_ID:
            logger.error("Google Client ID not configured in .env file")
            return {
                "success": False,
                "message": "Google authentication not properly configured",
            }

        try:
            logger.info(f"🔍 Verifying {token_type} token...")

            if token_type == "id_token":
                # Verify ID token using Google's library
                user_info = id_token.verify_oauth2_token(
                    token, google_requests.Request(), GOOGLE_CLIENT_ID
                )

                logger.info(f"✅ ID token verified for user: {user_info.get('email')}")

                return {
                    "success": True,
                    "user_info": {
                        "id": user_info.get("sub"),
                        "email": user_info.get("email"),
                        "name": user_info.get("name"),
                        "picture": user_info.get("picture"),
                        "email_verified": user_info.get("email_verified", False),
                    },
                }

            elif token_type == "access_token":
                # Verify access token by calling Google's userinfo endpoint
                logger.info("🔍 Calling Google userinfo API...")

                response = requests.get(
                    f"https://www.googleapis.com/oauth2/v2/userinfo?access_token={token}",
                    timeout=10,
                )

                if response.status_code != 200:
                    logger.error(
                        f"❌ Google API error: {response.status_code} - {response.text}"
                    )
                    return {
                        "success": False,
                        "message": f"Failed to verify access token with Google (Status: {response.status_code})",
                    }

                user_data = response.json()
                logger.info(
                    f"✅ Access token verified for user: {user_data.get('email')}"
                )

                return {
                    "success": True,
                    "user_info": {
                        "id": user_data.get("id"),
                        "email": user_data.get("email"),
                        "name": user_data.get("name"),
                        "picture": user_data.get("picture"),
                        "email_verified": user_data.get("verified_email", False),
                    },
                }

            else:
                logger.error(f"❌ Unsupported token type: {token_type}")
                return {
                    "success": False,
                    "message": f"Unsupported token type: {token_type}",
                }

        except ValueError as e:
            logger.error(f"❌ Google token verification failed: {str(e)}")
            return {"success": False, "message": "Invalid Google token"}
        except requests.RequestException as e:
            logger.error(f"❌ Network error during token verification: {str(e)}")
            return {"success": False, "message": "Network error during verification"}
        except Exception as e:
            logger.error(f"❌ Unexpected error during token verification: {str(e)}")
            return {"success": False, "message": "Token verification failed"}

    @staticmethod
    def google_login(db: Session, token: str, token_type: str = "access_token"):
        """Handle Google login"""
        try:
            logger.info(f"🚀 Starting Google login with token type: {token_type}")

            # Verify the Google token
            verification_result = GoogleAuthService.verify_google_token(
                token, token_type
            )

            if not verification_result["success"]:
                logger.error(
                    f"❌ Token verification failed: {verification_result['message']}"
                )
                return {"success": False, "message": verification_result["message"]}

            user_info = verification_result["user_info"]
            logger.info(f"🔍 Looking for user with email: {user_info['email']}")

            # Check if user exists
            user = db.query(User).filter(User.email == user_info["email"]).first()

            if not user:
                logger.warning(f"❌ User not found for email: {user_info['email']}")
                return {
                    "success": False,
                    "message": "User not found. Please sign up first.",
                    "suggest_signup": True,
                    "user_email": user_info["email"],
                }

            logger.info(f"✅ User found: {user.email}")

            # Generate tokens
            access_token = create_access_token(user.email)
            refresh_token = create_refresh_token(user.email)

            # Update user info
            try:
                if user_info["email_verified"] and not user.isVerified:
                    user.isVerified = True
                    logger.info(f"✅ Marked user {user.email} as verified")

                user.last_login = datetime.now(timezone.utc)
                db.commit()

            except Exception as update_error:
                logger.warning(f"⚠️ Could not update user fields: {update_error}")
                db.rollback()

            logger.info(f"✅ Google login successful for user: {user.email}")
            return {
                "success": True,
                "message": "Google login successful",
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "phone_number": user.phone_number or "",
                    "isVerified": user.isVerified,
                },
            }

        except Exception as e:
            logger.error(f"❌ Google login error: {str(e)}")
            db.rollback()
            return {"success": False, "message": "Google login failed"}

    @staticmethod
    def google_signup(db: Session, token: str, token_type: str = "access_token"):
        """Handle Google signup"""
        try:
            logger.info(f"🚀 Starting Google signup with token type: {token_type}")

            # Verify the Google token
            verification_result = GoogleAuthService.verify_google_token(
                token, token_type
            )

            if not verification_result["success"]:
                logger.error(
                    f"❌ Token verification failed: {verification_result['message']}"
                )
                return {"success": False, "message": verification_result["message"]}

            user_info = verification_result["user_info"]
            logger.info(f"🔍 Checking if user exists with email: {user_info['email']}")

            # Check if user already exists
            existing_user = (
                db.query(User).filter(User.email == user_info["email"]).first()
            )

            if existing_user:
                # User exists, perform login instead
                logger.info(
                    f"✅ User already exists, performing login for: {user_info['email']}"
                )
                return GoogleAuthService.google_login(db, token, token_type)

            logger.info(f"✅ Creating new user for email: {user_info['email']}")

            # Create new user
            new_user = User(
                full_name=user_info["name"] or "",
                email=user_info["email"],
                phone_number=None,  # Will be updated later if needed
                password_hash=None,  # No password for Google users
                auth_provider="google",  # Add this field to track auth method
                google_id=user_info["id"],  # Store Google ID
                profile_picture=user_info.get("picture", ""),
                isVerified=user_info[
                    "email_verified"
                ],  # Verified if Google email is verified
                created_at=datetime.now(timezone.utc),
            )

            db.add(new_user)
            db.commit()
            db.refresh(new_user)

            logger.info(f"✅ Created new user: {new_user.email}")

            # Generate tokens
            access_token = create_access_token(new_user.email)
            refresh_token = create_refresh_token(new_user.email)

            logger.info(f"✅ Google signup successful for user: {new_user.email}")
            return {
                "success": True,
                "message": "Google signup successful",
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": {
                    "id": new_user.id,
                    "email": new_user.email,
                    "full_name": new_user.full_name,
                    "phone_number": new_user.phone_number or "",
                    "isVerified": new_user.isVerified,
                },
            }

        except Exception as e:
            logger.error(f"❌ Google signup error: {str(e)}")
            db.rollback()
            return {"success": False, "message": "Google signup failed"}
