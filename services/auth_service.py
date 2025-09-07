# services/auth_service.py
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
import jwt
import os
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from database.connection import get_db
from database.models import User
from core.config import JWT_SECRET, REFRESH_SECRET, ACCESS_TOKEN_EXPIRE_MINUTES
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
ALGORITHM = "HS256"
REFRESH_TOKEN_EXPIRE_DAYS = 7
SECRET_KEY = JWT_SECRET or os.getenv("JWT_SECRET", "your-access-secret-key")
REFRESH_SECRET_KEY = REFRESH_SECRET or os.getenv(
    "REFRESH_SECRET", "your-refresh-secret-key"
)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(email: str) -> str:
    """Create JWT access token"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": email, "exp": expire, "type": "access"}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(email: str) -> str:
    """Create JWT refresh token"""
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": email, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, REFRESH_SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate access token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Access token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid access token")


def decode_refresh_token(token: str) -> dict:
    """Decode and validate refresh token"""
    try:
        payload = jwt.decode(token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """
    Extract current user from JWT token
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Decode the token
        payload = decode_access_token(token)
        email = payload.get("sub")

        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
            )

        # Get user from database
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
            )

        return user

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


def get_current_user_optional(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """
    Extract current user from JWT token (optional - returns None if no token)
    """
    if not token:
        return None

    try:
        return get_current_user(token, db)
    except HTTPException:
        return None


class AuthService:
    """Enhanced Authentication Service Class"""

    def __init__(self, db: Session):
        self.db = db

    def create_user(self, user_data: dict) -> dict:
        """Create a new user"""
        try:
            # Hash password
            hashed_password = hash_password(user_data["password"])

            # Create user object
            new_user = User(
                full_name=user_data.get("full_name", ""),
                email=user_data["email"],
                phone_number=user_data.get("phone_number", ""),
                password_hash=hashed_password,
                isVerified=False,
                created_at=datetime.now(timezone.utc),
            )

            self.db.add(new_user)
            self.db.commit()
            self.db.refresh(new_user)

            return {
                "success": True,
                "message": "User created successfully",
                "user_id": new_user.id,
            }

        except Exception as e:
            self.db.rollback()
            return {"success": False, "message": f"Failed to create user: {str(e)}"}


def authenticate_user(self, email: str, password: str) -> dict:
    """Authenticate user with email and password"""
    try:
        # Find user
        user = self.db.query(User).filter(User.email == email).first()

        if not user:
            return {"success": False, "message": "User not found"}

        # Verify password
        if not verify_password(password, user.password_hash):
            return {"success": False, "message": "Invalid password"}

        # Check if user is verified
        if not user.isVerified:
            return {"success": False, "message": "Account not verified"}

        # Update last login
        user.last_login = datetime.now(timezone.utc)
        self.db.commit()

        # Generate tokens
        access_token = create_access_token(user.email)
        refresh_token = create_refresh_token(user.email)

        return {
            "success": True,
            "message": "Authentication successful",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "phone_number": user.phone_number,
                "isVerified": user.isVerified,
            },
        }

    except Exception as e:
        return {"success": False, "message": f"Authentication failed: {str(e)}"}


def refresh_access_token(self, refresh_token: str) -> dict:
    """Generate new access token using refresh token"""
    try:
        # Decode refresh token
        payload = decode_refresh_token(refresh_token)
        email = payload.get("sub")

        if not email:
            return {"success": False, "message": "Invalid refresh token payload"}

        # Verify user exists
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            return {"success": False, "message": "User not found"}

        # Generate new access token
        new_access_token = create_access_token(email)

        return {
            "success": True,
            "access_token": new_access_token,
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES,
        }

    except HTTPException as e:
        return {"success": False, "message": e.detail}
    except Exception as e:
        return {"success": False, "message": f"Token refresh failed: {str(e)}"}
