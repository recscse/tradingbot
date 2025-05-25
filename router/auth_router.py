# router/auth_router.py
from datetime import datetime, timedelta, timezone
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
import jwt
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from core.config import REFRESH_SECRET, JWT_SECRET, ACCESS_TOKEN_EXPIRE_MINUTES
from database.schemas import UserEmailLogin, UserSignup, OTPVerification
from database.connection import get_db
from database.models import OTP, User
from passlib.context import CryptContext
from services.otp_service import (
    check_reset_token_exists,
    generate_otp,
    send_otp_twilio,
    store_otp,
    store_reset_token,
    verify_email_otp,
    verify_reset_token,
)

from services.auth.google_auth_service import GoogleAuthService
from services.auth_service import (
    ALGORITHM,
    REFRESH_TOKEN_EXPIRE_DAYS,
    get_current_user,
    verify_password,
    create_access_token,
    create_refresh_token,
)

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

auth_router = APIRouter()


# Enhanced error handler
def format_error_response(message: str, success: bool = False, errors: list = None):
    """Standardized error response format"""
    return {
        "message": message,
        "success": success,
        "errors": errors or [],
    }


# ✅ Enhanced Signup Route
@auth_router.post("/signup", status_code=status.HTTP_201_CREATED)
def enhanced_signup(user: UserSignup, db: Session = Depends(get_db)):
    """Enhanced signup with email verification"""
    try:
        # Check for existing user
        existing_user = db.query(User).filter(User.email == user.email).first()
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail=format_error_response("Email already registered", False),
            )

        # Validate input
        if len(user.password) < 6:
            raise HTTPException(
                status_code=400,
                detail=format_error_response(
                    "Password must be at least 6 characters", False
                ),
            )

        # Create User with hashed password
        new_user = User(
            full_name=user.full_name,
            email=user.email,
            phone_number=user.phone_number if user.phone_number else None,
            country_code=user.country_code if user.phone_number else None,
            password_hash=pwd_context.hash(user.password),
            isVerified=False,  # Will be verified via email
            email_verified=False,
            phone_verified=False,
            created_at=datetime.now(timezone.utc),
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # Send email verification
        otp_code = generate_otp()
        if send_email_otp(user.email, otp_code, user.full_name):
            store_email_otp(db, user.email, otp_code)
            logger.info(f"✅ User created and email OTP sent: {user.email}")

            return {
                "success": True,
                "message": "Account created! Please check your email for verification code.",
                "email": user.email,
            }
        else:
            # If email fails, still create account but inform user
            logger.warning(f"⚠️ User created but email OTP failed: {user.email}")
            return {
                "success": True,
                "message": "Account created! Please contact support for email verification.",
                "email": user.email,
            }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Enhanced signup error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response("An error occurred during signup", False),
        )


# ✅ Enhanced OTP Verification Route
@auth_router.post("/verify-otp", status_code=status.HTTP_200_OK)
def verify_otp(data: OTPVerification, db: Session = Depends(get_db)):
    """Verifies OTP and activates user account."""
    try:
        # Find OTP record
        otp_record = (
            db.query(OTP)
            .filter(
                (OTP.phone_number == data.phone_number) & (OTP.otp_code == data.otp)
            )
            .first()
        )

        if not otp_record:
            raise HTTPException(
                status_code=400, detail=format_error_response("Invalid OTP", False)
            )

        # Check if OTP is expired
        if otp_record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(
            timezone.utc
        ):
            db.delete(otp_record)
            db.commit()
            raise HTTPException(
                status_code=400,
                detail=format_error_response(
                    "OTP has expired. Please request a new one.", False
                ),
            )

        # Mark user as verified
        user = db.query(User).filter(User.phone_number == data.phone_number).first()
        if user:
            user.isVerified = True
            user.updated_at = datetime.now(timezone.utc)
            db.commit()
            logger.info(f"✅ User verified successfully: {user.email}")

        # Delete OTP after verification
        db.delete(otp_record)
        db.commit()

        return format_error_response(
            "Phone number verified successfully. You can now log in.", True
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ OTP verification error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                "An error occurred during verification", False
            ),
        )


# ✅ Enhanced Login Route
@auth_router.post("/login")
def login(user: UserEmailLogin, response: Response, db: Session = Depends(get_db)):
    """Handles user login and returns JWT tokens."""
    try:
        # Find user
        db_user = db.query(User).filter(User.email == user.email).first()

        if not db_user:
            raise HTTPException(
                status_code=401,
                detail=format_error_response("Invalid email or password", False),
            )

        # Verify password
        if not verify_password(user.password, db_user.password_hash):
            raise HTTPException(
                status_code=401,
                detail=format_error_response("Invalid email or password", False),
            )

        # Check if account is verified
        if not db_user.isVerified:
            raise HTTPException(
                status_code=403,
                detail=format_error_response(
                    "Account not verified. Please verify OTP.", False
                ),
            )

        # Update last login
        db_user.last_login = datetime.now(timezone.utc)
        db.commit()

        # Generate JWT tokens
        access_token = create_access_token(db_user.email)
        refresh_token = create_refresh_token(db_user.email)

        logger.info(f"✅ Login successful for user: {db_user.email}")

        return {
            "message": "Login successful",
            "access_token": access_token,
            "token_type": "bearer",
            "refresh_token": refresh_token,
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES,
            "success": True,
            "user": {
                "id": db_user.id,
                "email": db_user.email,
                "full_name": db_user.full_name,
                "phone_number": db_user.phone_number,
                "isVerified": db_user.isVerified,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Login error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response("An error occurred during login", False),
        )


# ✅ Enhanced Refresh Token Route
@auth_router.post("/refresh-token")
def refresh_token(request: Request, db: Session = Depends(get_db)):
    """Refreshes the access token using a valid refresh token."""
    try:
        # Get refresh token from header
        refresh_token = request.headers.get("Refresh-Token")

        if not refresh_token:
            raise HTTPException(
                status_code=401,
                detail=format_error_response("Refresh token missing", False),
            )

        # Decode the refresh token
        try:
            payload = jwt.decode(refresh_token, REFRESH_SECRET, algorithms=[ALGORITHM])
            user_email = payload.get("sub")
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=401,
                detail=format_error_response("Refresh token expired", False),
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=401,
                detail=format_error_response("Invalid refresh token", False),
            )

        if not user_email:
            raise HTTPException(
                status_code=401,
                detail=format_error_response("Invalid refresh token payload", False),
            )

        # Find user
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            raise HTTPException(
                status_code=401, detail=format_error_response("User not found", False)
            )

        # Create new access token
        new_access_token = create_access_token(user_email)

        logger.info(f"✅ Token refreshed for user: {user_email}")

        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES,
            "success": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=500, detail=format_error_response("Token refresh failed", False)
        )


# ✅ Logout Route
@auth_router.post("/logout")
def logout(response: Response):
    """Logs out user and clears tokens."""
    try:
        # In a production app, you might want to blacklist the token
        return format_error_response("Logged out successfully", True)
    except Exception as e:
        logger.error(f"❌ Logout error: {str(e)}")
        raise HTTPException(
            status_code=500, detail=format_error_response("Logout failed", False)
        )


# ✅ Google Auth Models
class GoogleAuthRequest(BaseModel):
    token: str
    tokenType: str = "id_token"
    user: dict = {}
    isSignUp: bool = False


# ✅ Enhanced Google Login Route
@auth_router.post("/google/login")
def google_signin(request: GoogleAuthRequest, db: Session = Depends(get_db)):
    """Handle both Google login and signup with single endpoint"""
    try:
        logger.info(f"🚀 Google sign-in attempt with token type: {request.tokenType}")

        # First try login
        login_result = GoogleAuthService.google_login(
            db, request.token, request.tokenType
        )

        if login_result["success"]:
            logger.info(f"✅ Google login successful")
            return {
                "message": login_result["message"],
                "access_token": login_result["access_token"],
                "refresh_token": login_result["refresh_token"],
                "token_type": "bearer",
                "user": login_result["user"],
                "success": True,
            }

        # If login failed because user doesn't exist, try signup
        if login_result.get("suggest_signup"):
            logger.info(f"🔄 User not found, attempting signup...")
            signup_result = GoogleAuthService.google_signup(
                db, request.token, request.tokenType
            )

            if signup_result["success"]:
                logger.info(f"✅ Google signup successful")
                return {
                    "message": signup_result["message"],
                    "access_token": signup_result["access_token"],
                    "refresh_token": signup_result["refresh_token"],
                    "token_type": "bearer",
                    "user": signup_result["user"],
                    "success": True,
                }
            else:
                logger.warning(f"❌ Google signup failed: {signup_result['message']}")
                raise HTTPException(
                    status_code=400,
                    detail=format_error_response(signup_result["message"], False),
                )
        else:
            logger.warning(f"❌ Google login failed: {login_result['message']}")
            raise HTTPException(
                status_code=400,
                detail=format_error_response(login_result["message"], False),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Google sign-in endpoint error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response("Google authentication failed", False),
        )


# ✅ Enhanced Google Signup Route
@auth_router.post("/google/signup")
def google_signup(request: GoogleAuthRequest, db: Session = Depends(get_db)):
    """Handle Google OAuth signup"""
    try:
        logger.info(f"🚀 Google signup attempt with token type: {request.tokenType}")

        result = GoogleAuthService.google_signup(db, request.token, request.tokenType)

        if result["success"]:
            logger.info(f"✅ Google signup successful")
            return {
                "message": result["message"],
                "access_token": result["access_token"],
                "refresh_token": result["refresh_token"],
                "token_type": "bearer",
                "user": result["user"],
                "success": True,
            }
        else:
            logger.warning(f"❌ Google signup failed: {result['message']}")
            raise HTTPException(
                status_code=400, detail=format_error_response(result["message"], False)
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Google signup endpoint error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response("Google authentication failed", False),
        )


# ✅ Resend OTP Route
@auth_router.post("/resend-otp")
def resend_otp(request: dict, db: Session = Depends(get_db)):
    """Resend OTP to user's phone"""
    try:
        phone_number = request.get("phone_number")
        country_code = request.get("country_code")

        if not phone_number or not country_code:
            raise HTTPException(
                status_code=400,
                detail=format_error_response(
                    "Phone number and country code are required", False
                ),
            )

        # Check if user exists
        user = db.query(User).filter(User.phone_number == phone_number).first()
        if not user:
            raise HTTPException(
                status_code=404, detail=format_error_response("User not found", False)
            )

        # Generate and send new OTP
        otp_code = generate_otp()
        if not send_otp_twilio(country_code, phone_number, otp_code):
            raise HTTPException(
                status_code=500,
                detail=format_error_response(
                    "Failed to send OTP. Please try again.", False
                ),
            )

        # Delete old OTP and store new one
        old_otp = db.query(OTP).filter(OTP.phone_number == phone_number).first()
        if old_otp:
            db.delete(old_otp)

        store_otp(db, phone_number, otp_code)

        logger.info(f"✅ OTP resent to: {country_code}{phone_number}")

        return format_error_response("OTP sent successfully", True)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Resend OTP error: {str(e)}")
        raise HTTPException(
            status_code=500, detail=format_error_response("Failed to resend OTP", False)
        )


from services.otp_service import (
    send_email_otp,
    send_reset_password_email,
    store_email_otp,
)


@auth_router.post("/send-phone-verification")
def send_phone_verification_route(
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send phone verification OTP for profile update"""
    try:
        phone_number = request.get("phone_number")
        country_code = request.get("country_code")

        if not phone_number or not country_code:
            raise HTTPException(
                status_code=400,
                detail=format_error_response(
                    "Phone number and country code are required", False
                ),
            )

        # Generate and send OTP
        otp_code = generate_otp()
        if not send_otp_twilio(country_code, phone_number, otp_code):
            raise HTTPException(
                status_code=500,
                detail=format_error_response("Failed to send SMS OTP", False),
            )

        # Store OTP
        store_otp(db, phone_number, otp_code)

        logger.info(f"✅ Phone verification OTP sent to: {country_code}{phone_number}")
        return format_error_response("Verification code sent to your phone", True)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Send phone verification error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response("Failed to send verification code", False),
        )


@auth_router.post("/send-email-otp")
def send_email_otp_route(request: dict, db: Session = Depends(get_db)):
    """Send OTP to email for verification"""
    try:
        email = request.get("email")
        if not email:
            raise HTTPException(
                status_code=400,
                detail=format_error_response("Email is required", False),
            )

        # Generate and send OTP
        otp_code = generate_otp()
        if not send_email_otp(email, otp_code):
            raise HTTPException(
                status_code=500,
                detail=format_error_response("Failed to send email OTP", False),
            )

        # Store OTP
        store_email_otp(db, email, otp_code)

        logger.info(f"✅ Email OTP sent to: {email}")
        return format_error_response("OTP sent to your email", True)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Send email OTP error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response("Failed to send email OTP", False),
        )


@auth_router.post("/verify-email-otp")
def verify_email_otp_route(request: dict, db: Session = Depends(get_db)):
    """Verify email OTP and activate account"""
    try:
        email = request.get("email")
        otp = request.get("otp")

        if not email or not otp:
            raise HTTPException(
                status_code=400,
                detail=format_error_response("Email and OTP are required", False),
            )

        # Use the service function instead of inline query
        if not verify_email_otp(db, email, otp):
            raise HTTPException(
                status_code=400,
                detail=format_error_response("Invalid or expired OTP", False),
            )

        # Mark user as verified
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.isVerified = True
            user.email_verified = True
            user.updated_at = datetime.now(timezone.utc)

            # Generate tokens for login
            access_token = create_access_token(user.email)
            refresh_token = create_refresh_token(user.email)

            db.commit()

            logger.info(f"✅ Email verified successfully: {email}")

            return {
                "message": "Email verified successfully",
                "success": True,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "phone_number": user.phone_number,
                    "isVerified": user.isVerified,
                    "email_verified": True,
                },
            }
        else:
            raise HTTPException(
                status_code=404, detail=format_error_response("User not found", False)
            )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Email OTP verification error: {str(e)}")
        raise HTTPException(
            status_code=500, detail=format_error_response("Verification failed", False)
        )


@auth_router.post("/forgot-password")
def forgot_password_route(request: dict, db: Session = Depends(get_db)):
    """Send password reset code to email"""
    try:
        email = request.get("email")
        if not email:
            raise HTTPException(
                status_code=400,
                detail=format_error_response("Email is required", False),
            )

        # Check if user exists
        user = db.query(User).filter(User.email == email).first()
        if not user:
            # For security, don't reveal if email exists
            return format_error_response(
                "If email exists, reset code has been sent", True
            )

        # Generate and send reset code
        reset_code = generate_otp()
        if not send_reset_password_email(email, reset_code, user.full_name):
            raise HTTPException(
                status_code=500,
                detail=format_error_response("Failed to send reset code", False),
            )

        # Store reset code
        store_reset_token(db, email, reset_code)

        logger.info(f"✅ Password reset code sent to: {email}")
        return format_error_response("Reset code sent to your email", True)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Forgot password error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response("Failed to process request", False),
        )


@auth_router.post("/verify-reset-token")
def verify_reset_token_route(request: dict, db: Session = Depends(get_db)):
    """Verify password reset token without consuming it"""
    try:
        email = request.get("email")
        token = request.get("token") or request.get("otp")

        if not email or not token:
            raise HTTPException(
                status_code=400,
                detail=format_error_response("Email and token are required", False),
            )

        # Use the service function
        if not check_reset_token_exists(db, email, token):
            raise HTTPException(
                status_code=400,
                detail=format_error_response("Invalid or expired reset code", False),
            )

        logger.info(f"✅ Reset token verified for: {email}")
        return {"success": True, "message": "Reset code verified", "token": token}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Reset token verification error: {str(e)}")
        raise HTTPException(
            status_code=500, detail=format_error_response("Verification failed", False)
        )


@auth_router.post("/reset-password")
def reset_password_route(request: dict, db: Session = Depends(get_db)):
    """Reset user password"""
    try:
        email = request.get("email")
        new_password = request.get("new_password") or request.get("password")
        token = request.get("token") or request.get("reset_token")

        if not email or not new_password or not token:
            raise HTTPException(
                status_code=400,
                detail=format_error_response(
                    "Email, password, and token are required", False
                ),
            )

        # Use the service function to verify and consume the token
        if not verify_reset_token(db, email, token):
            raise HTTPException(
                status_code=400,
                detail=format_error_response("Invalid or expired reset code", False),
            )

        # Find user and update password
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(
                status_code=404, detail=format_error_response("User not found", False)
            )

        # Update password
        user.password_hash = pwd_context.hash(new_password)
        user.updated_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(f"✅ Password reset successful for: {email}")
        return format_error_response("Password reset successful", True)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Password reset error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response("Password reset failed", False),
        )


@auth_router.post("/verify-phone")
def verify_phone_route(
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Verify phone number for profile update"""
    try:
        phone_number = request.get("phone_number")
        country_code = request.get("country_code")
        otp = request.get("otp")

        if not phone_number or not country_code or not otp:
            raise HTTPException(
                status_code=400,
                detail=format_error_response(
                    "Phone number, country code, and OTP are required", False
                ),
            )

        # Find OTP record
        otp_record = (
            db.query(OTP)
            .filter((OTP.phone_number == phone_number) & (OTP.otp_code == otp))
            .first()
        )

        if not otp_record:
            raise HTTPException(
                status_code=400, detail=format_error_response("Invalid OTP", False)
            )

        # Check if OTP is expired
        if otp_record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(
            timezone.utc
        ):
            db.delete(otp_record)
            db.commit()
            raise HTTPException(
                status_code=400, detail=format_error_response("OTP has expired", False)
            )

        # Update user's phone number and mark as verified
        current_user.phone_number = phone_number
        current_user.country_code = country_code
        current_user.phone_verified = True
        current_user.updated_at = datetime.now(timezone.utc)

        # Delete OTP after verification
        db.delete(otp_record)
        db.commit()

        logger.info(f"✅ Phone verified successfully for user: {current_user.email}")

        return {
            "success": True,
            "message": "Phone number verified successfully",
            "user": {
                "id": current_user.id,
                "email": current_user.email,
                "full_name": current_user.full_name,
                "phone_number": current_user.phone_number,
                "country_code": current_user.country_code,
                "phone_verified": current_user.phone_verified,
                "email_verified": current_user.email_verified,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Phone verification error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response("Phone verification failed", False),
        )


@auth_router.put("/profile")
def update_profile_route(
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update user profile"""
    try:
        # Update allowed fields
        if "full_name" in request:
            current_user.full_name = request["full_name"]

        if "phone_number" in request and "country_code" in request:
            # If updating phone, mark as unverified until verified
            current_user.phone_number = request["phone_number"]
            current_user.country_code = request["country_code"]
            current_user.phone_verified = False

        current_user.updated_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(f"✅ Profile updated for user: {current_user.email}")

        return {
            "success": True,
            "message": "Profile updated successfully",
            "user": {
                "id": current_user.id,
                "email": current_user.email,
                "full_name": current_user.full_name,
                "phone_number": current_user.phone_number,
                "country_code": current_user.country_code,
                "phone_verified": current_user.phone_verified,
                "email_verified": current_user.email_verified,
            },
        }

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Profile update error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response("Profile update failed", False),
        )
