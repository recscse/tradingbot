# services/email_otp_service.py
import os
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from database.models import OTP
from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
FROM_EMAIL = os.getenv("FROM_EMAIL", EMAIL_USERNAME)


def generate_email_otp():
    return str(random.randint(100000, 999999))


def send_email_otp(email: str, otp: str, name: str = "User"):
    try:
        msg = MIMEMultipart()
        msg["From"] = FROM_EMAIL
        msg["To"] = email
        msg["Subject"] = "Email Verification - Trading Bot"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .logo {{ font-size: 24px; font-weight: bold; color: #3f8fff; }}
                .otp-code {{ font-size: 32px; font-weight: bold; color: #333; text-align: center; letter-spacing: 5px; margin: 20px 0; padding: 15px; background-color: #f8f9fa; border-radius: 8px; border: 2px dashed #3f8fff; }}
                .footer {{ margin-top: 30px; text-align: center; color: #666; font-size: 14px; }}
                .warning {{ background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; border-radius: 5px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">🤖 Trading Bot</div>
                    <h2>Email Verification</h2>
                </div>
                
                <p>Hello {name},</p>
                <p>Welcome to Trading Bot! Please use the following verification code:</p>
                
                <div class="otp-code">{otp}</div>
                
                <p>This code will expire in <strong>10 minutes</strong>.</p>
                
                <div class="warning">
                    <strong>Security Note:</strong> Never share this code with anyone.
                </div>
                
                <div class="footer">
                    <p>If you didn't request this verification, please ignore this email.</p>
                    <p>© 2024 Trading Bot. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_body, "html"))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()

        print(f"✅ Email OTP sent to {email}")
        return True

    except Exception as e:
        print(f"❌ Failed to send email OTP: {str(e)}")
        return False


def store_email_otp(db: Session, email: str, otp_code: str):
    existing_otp = db.query(OTP).filter(OTP.email == email).first()

    if existing_otp:
        existing_otp.otp_code = otp_code
        existing_otp.expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        existing_otp.otp_type = "email"
    else:
        new_otp = OTP(
            email=email,
            otp_code=otp_code,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            verification_method="email",
        )
        db.add(new_otp)

    db.commit()


def verify_email_otp(db: Session, email: str, otp_code: str):
    otp_record = (
        db.query(OTP).filter((OTP.email == email) & (OTP.otp_code == otp_code)).first()
    )

    if not otp_record:
        return {"success": False, "message": "Invalid OTP"}

    if otp_record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        db.delete(otp_record)
        db.commit()
        return {
            "success": False,
            "message": "OTP has expired. Please request a new one.",
        }

    db.delete(otp_record)
    db.commit()

    return {"success": True, "message": "Email verified successfully"}


def send_and_store_email_otp(db: Session, email: str, name: str = "User"):
    try:
        otp_code = generate_email_otp()

        if send_email_otp(email, otp_code, name):
            store_email_otp(db, email, otp_code)
            return {"success": True, "message": "OTP sent to your email"}
        else:
            return {"success": False, "message": "Failed to send email"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}
