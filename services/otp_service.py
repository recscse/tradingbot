import os
import random
from sqlalchemy.orm import Session
from twilio.rest import Client
from datetime import datetime, timedelta, timezone
from database.connection import SessionLocal
from database.models import OTP
from services.email.email_service import email_service
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

# Twilio Credentials from .env
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE_NUMBER")


def generate_otp():
    """Generate a 6-digit OTP"""
    return str(random.randint(100000, 999999))


def send_email_otp(email: str, otp: str, user_name: str = "User") -> bool:
    """Send OTP via email using ZeptoMail"""
    try:
        success = email_service.send_otp_email(email, otp)
        if success:
            logger.info(f"✅ OTP email sent successfully to {email}")
        else:
            logger.error(f"❌ Failed to send OTP email to {email}")
        return success
    except Exception as e:
        logger.error(f"❌ OTP email error: {e}")
        return False


def send_reset_password_email(
    email: str, reset_code: str, user_name: str = "User"
) -> bool:
    """Send password reset email using ZeptoMail"""
    try:
        success = email_service.send_password_reset_otp_email(email, reset_code)
        if success:
            logger.info(f"✅ Password reset email sent successfully to {email}")
        else:
            logger.error(f"❌ Failed to send password reset email to {email}")
        return success
    except Exception as e:
        logger.error(f"❌ Password reset email error: {e}")
        return False


def send_welcome_email(email: str, user_name: str) -> bool:
    """Send welcome email using ZeptoMail"""
    try:
        success = email_service.send_welcome_email(email, user_name)
        if success:
            logger.info(f"✅ Welcome email sent successfully to {email}")
        else:
            logger.error(f"❌ Failed to send welcome email to {email}")
        return success
    except Exception as e:
        logger.error(f"❌ Welcome email error: {e}")
        return False


def send_otp_twilio(country_code: str, phone_number: str, otp: str) -> bool:
    """Send OTP via Twilio SMS"""
    if not all([TWILIO_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE]):
        logger.warning("⚠️ Twilio credentials not configured")
        return False

    full_phone_number = f"{country_code}{phone_number}"
    try:
        client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=f"Your Growth Quantix OTP: {otp}. Valid for 5 minutes. Do not share.",
            from_=TWILIO_PHONE,
            to=full_phone_number,
        )
        logger.info(f"✅ OTP SMS sent to {phone_number}, SID: {message.sid}")
        return True
    except Exception as e:
        logger.error(f"❌ SMS OTP error: {e}")
        return False


def store_otp(db: Session, phone_number: str, otp_code: str):
    """Store OTP for phone number"""
    try:
        # Delete any existing phone OTP for this number
        existing_otp = (
            db.query(OTP)
            .filter(OTP.phone_number == phone_number, OTP.otp_type == "phone")
            .first()
        )
        if existing_otp:
            db.delete(existing_otp)

        # Create new phone OTP record
        new_otp = OTP(
            phone_number=phone_number,  # ✅ Store phone in phone_number field
            email=None,  # ✅ Leave email field empty
            otp_code=otp_code,  # ✅ Store OTP in otp_code field
            otp_type="phone",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            created_at=datetime.now(timezone.utc),
        )
        db.add(new_otp)
        db.commit()
        logger.info(f"✅ Phone OTP stored for {phone_number}")

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to store phone OTP: {e}")
        raise


def store_email_otp(db: Session, email: str, otp_code: str):
    """Store OTP for email"""
    try:
        # Delete any existing email OTP for this email
        existing_otp = (
            db.query(OTP)
            .filter(OTP.email == email, OTP.otp_type.in_(["email", "reset"]))
            .first()
        )
        if existing_otp:
            db.delete(existing_otp)

        # Create new email OTP record
        new_otp = OTP(
            phone_number=None,  # ✅ Leave phone_number field empty
            email=email,  # ✅ Store email in email field
            otp_code=otp_code,  # ✅ Store OTP in otp_code field
            otp_type="email",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            created_at=datetime.now(timezone.utc),
        )
        db.add(new_otp)
        db.commit()
        logger.info(f"✅ Email OTP stored for {email}")

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to store email OTP: {e}")
        raise


def store_reset_token(db: Session, email: str, reset_token: str):
    """Store password reset token for email"""
    try:
        # Delete any existing reset token for this email
        existing_token = (
            db.query(OTP).filter(OTP.email == email, OTP.otp_type == "reset").first()
        )
        if existing_token:
            db.delete(existing_token)

        # Create new reset token record
        new_token = OTP(
            phone_number=None,  # ✅ Leave phone_number field empty
            email=email,  # ✅ Store email in email field
            otp_code=reset_token,  # ✅ Store reset token in otp_code field
            otp_type="reset",
            expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=30),  # 30 minutes for reset
            created_at=datetime.now(timezone.utc),
        )
        db.add(new_token)
        db.commit()
        logger.info(f"✅ Reset token stored for {email}")

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to store reset token: {e}")
        raise


def verify_phone_otp(db: Session, phone_number: str, submitted_otp: str) -> bool:
    """Verify phone OTP"""
    try:
        # Find OTP record using phone_number field and otp_code field
        otp_record = (
            db.query(OTP)
            .filter(
                OTP.phone_number == phone_number,  # ✅ Check phone_number field
                OTP.otp_code == submitted_otp,  # ✅ Check otp_code field
                OTP.otp_type == "phone",
            )
            .first()
        )

        if not otp_record:
            logger.warning(f"⚠️ Invalid phone OTP for {phone_number}")
            return False

        # Check if OTP has expired
        if otp_record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(
            timezone.utc
        ):
            db.delete(otp_record)
            db.commit()
            logger.warning(f"⚠️ Expired phone OTP for {phone_number}")
            return False

        # OTP is valid, delete it
        db.delete(otp_record)
        db.commit()
        logger.info(f"✅ Phone OTP verified successfully for {phone_number}")
        return True

    except Exception as e:
        logger.error(f"❌ Phone OTP verification error: {e}")
        return False


def verify_email_otp(db: Session, email: str, submitted_otp: str) -> bool:
    """Verify email OTP"""
    try:
        # Find OTP record using email field and otp_code field
        otp_record = (
            db.query(OTP)
            .filter(
                OTP.email == email,  # ✅ Check email field
                OTP.otp_code == submitted_otp,  # ✅ Check otp_code field
                OTP.otp_type == "email",
            )
            .first()
        )

        if not otp_record:
            logger.warning(f"⚠️ Invalid email OTP for {email}")
            return False

        # Check if OTP has expired
        if otp_record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(
            timezone.utc
        ):
            db.delete(otp_record)
            db.commit()
            logger.warning(f"⚠️ Expired email OTP for {email}")
            return False

        # OTP is valid, delete it
        db.delete(otp_record)
        db.commit()
        logger.info(f"✅ Email OTP verified successfully for {email}")
        return True

    except Exception as e:
        logger.error(f"❌ Email OTP verification error: {e}")
        return False


def verify_reset_token(db: Session, email: str, submitted_token: str) -> bool:
    """Verify password reset token"""
    try:
        # Find reset token using email field and otp_code field
        token_record = (
            db.query(OTP)
            .filter(
                OTP.email == email,  # ✅ Check email field
                OTP.otp_code == submitted_token,  # ✅ Check otp_code field
                OTP.otp_type == "reset",
            )
            .first()
        )

        if not token_record:
            logger.warning(f"⚠️ Invalid reset token for {email}")
            return False

        # Check if token has expired
        if token_record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(
            timezone.utc
        ):
            db.delete(token_record)
            db.commit()
            logger.warning(f"⚠️ Expired reset token for {email}")
            return False

        # Token is valid, delete it
        db.delete(token_record)
        db.commit()
        logger.info(f"✅ Reset token verified successfully for {email}")
        return True

    except Exception as e:
        logger.error(f"❌ Reset token verification error: {e}")
        return False


def check_reset_token_exists(db: Session, email: str, submitted_token: str) -> bool:
    """Check if reset token exists without deleting it"""
    try:
        token_record = (
            db.query(OTP)
            .filter(
                OTP.email == email,  # ✅ Check email field
                OTP.otp_code == submitted_token,  # ✅ Check otp_code field
                OTP.otp_type == "reset",
            )
            .first()
        )

        if not token_record:
            return False

        # Check if token has expired
        if token_record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(
            timezone.utc
        ):
            db.delete(token_record)
            db.commit()
            return False

        return True

    except Exception as e:
        logger.error(f"❌ Reset token check error: {e}")
        return False


def cleanup_expired_otps(db: Session):
    """Clean up expired OTPs (can be called periodically)"""
    try:
        expired_otps = (
            db.query(OTP).filter(OTP.expires_at < datetime.now(timezone.utc)).all()
        )

        for otp in expired_otps:
            db.delete(otp)

        db.commit()
        logger.info(f"✅ Cleaned up {len(expired_otps)} expired OTPs")

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to cleanup expired OTPs: {e}")
