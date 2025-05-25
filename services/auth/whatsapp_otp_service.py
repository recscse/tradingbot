# services/whatsapp_otp_service.py
import os
import random
import requests
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from database.models import OTP
from dotenv import load_dotenv

load_dotenv()

# WhatsApp Configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

META_ACCESS_TOKEN = os.getenv("META_WHATSAPP_ACCESS_TOKEN")
META_PHONE_NUMBER_ID = os.getenv("META_WHATSAPP_PHONE_NUMBER_ID")


def generate_whatsapp_otp():
    return str(random.randint(100000, 999999))


def send_whatsapp_otp_twilio(
    phone_number: str, country_code: str, otp: str, name: str = "User"
):
    """Send WhatsApp OTP using Twilio (Paid service)"""
    try:
        from twilio.rest import Client

        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
            return False

        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        full_phone_number = f"whatsapp:{country_code}{phone_number}"

        message_body = f"""🤖 *Trading Bot Verification*

Hello {name}! 👋

Your verification code is: *{otp}*

This code will expire in 10 minutes.

🔐 Keep this code secure and don't share it with anyone.

Happy Trading! 📈"""

        message = client.messages.create(
            body=message_body, from_=TWILIO_WHATSAPP_NUMBER, to=full_phone_number
        )

        print(f"✅ WhatsApp OTP sent via Twilio to {full_phone_number}")
        return True

    except Exception as e:
        print(f"❌ Failed to send WhatsApp OTP via Twilio: {str(e)}")
        return False


def send_whatsapp_otp_meta(
    phone_number: str, country_code: str, otp: str, name: str = "User"
):
    """Send WhatsApp OTP using Meta Business API (Free tier available)"""
    try:
        if not META_ACCESS_TOKEN or not META_PHONE_NUMBER_ID:
            return False

        url = f"https://graph.facebook.com/v18.0/{META_PHONE_NUMBER_ID}/messages"

        headers = {
            "Authorization": f"Bearer {META_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }

        clean_country_code = country_code.replace("+", "")
        full_phone_number = f"{clean_country_code}{phone_number}"

        message_text = f"""🤖 *Trading Bot Verification*

Hello {name}! 👋

Your verification code is: *{otp}*

This code will expire in 10 minutes.

🔐 Keep this code secure and don't share it with anyone.

Happy Trading! 📈"""

        payload = {
            "messaging_product": "whatsapp",
            "to": full_phone_number,
            "type": "text",
            "text": {"body": message_text},
        }

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            print(f"✅ WhatsApp OTP sent via Meta to {full_phone_number}")
            return True
        else:
            print(
                f"❌ Meta WhatsApp API error: {response.status_code} - {response.text}"
            )
            return False

    except Exception as e:
        print(f"❌ Failed to send WhatsApp OTP via Meta: {str(e)}")
        return False


def send_whatsapp_otp(
    phone_number: str, country_code: str, otp: str, name: str = "User"
):
    """Try to send WhatsApp OTP using available providers"""
    # Try Twilio first (more reliable)
    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
        if send_whatsapp_otp_twilio(phone_number, country_code, otp, name):
            return True

    # Fallback to Meta WhatsApp
    if META_ACCESS_TOKEN and META_PHONE_NUMBER_ID:
        if send_whatsapp_otp_meta(phone_number, country_code, otp, name):
            return True

    return False


def store_whatsapp_otp(db: Session, phone_number: str, otp_code: str):
    existing_otp = db.query(OTP).filter(OTP.phone_number == phone_number).first()

    if existing_otp:
        existing_otp.otp_code = otp_code
        existing_otp.expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        existing_otp.verification_method = "whatsapp"
    else:
        new_otp = OTP(
            phone_number=phone_number,
            otp_code=otp_code,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            verification_method="whatsapp",
        )
        db.add(new_otp)

    db.commit()


def send_and_store_whatsapp_otp(
    db: Session, phone_number: str, country_code: str, name: str = "User"
):
    try:
        otp_code = generate_whatsapp_otp()

        if send_whatsapp_otp(phone_number, country_code, otp_code, name):
            store_whatsapp_otp(db, phone_number, otp_code)
            return {"success": True, "message": "WhatsApp OTP sent successfully"}
        else:
            return {"success": False, "message": "Failed to send WhatsApp OTP"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}
