from datetime import datetime
import smtplib
import ssl
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from typing import Optional
from core.config import (
    ZEPTOMAIL_HOST,
    ZEPTOMAIL_PORT,
    ZEPTOMAIL_USERNAME,
    ZEPTOMAIL_PASSWORD,
    ZEPTOMAIL_FROM_EMAIL,
)

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.smtp_server = ZEPTOMAIL_HOST
        self.port = ZEPTOMAIL_PORT
        self.username = ZEPTOMAIL_USERNAME
        self.password = ZEPTOMAIL_PASSWORD
        self.from_email = ZEPTOMAIL_FROM_EMAIL

    def send_trade_alert(
        self,
        recipient_email: str,
        subject: str,
        message: str,
        trade_data: Optional[dict] = None,
    ) -> bool:
        """Send trade execution alert via email"""
        try:
            html_content = self._create_trade_html(message, trade_data)

            return self._send_email(
                recipient_email=recipient_email,
                subject=subject,
                plain_content=message,
                html_content=html_content,
            )
        except Exception as e:
            logger.error(f"❌ Trade alert email failed: {e}")
            return False

    def send_notification(
        self, recipient_email: str, subject: str, message: str
    ) -> bool:
        """Send general notification email"""
        try:
            return self._send_email(
                recipient_email=recipient_email, subject=subject, plain_content=message
            )
        except Exception as e:
            logger.error(f"❌ Notification email failed: {e}")
            return False

    def send_otp_email(
        self, recipient_email: str, otp_code: str, purpose: str = "verification"
    ) -> bool:
        """Send OTP verification email - can be used for both signup and password reset"""
        if purpose == "password_reset":
            subject = "Password Reset OTP for Trading Bot"
            greeting = "🔑 Password Reset Request"
            description = "We received a request to reset your Trading Bot account password. Please use the following OTP to proceed:"
            warning_text = "If you didn't request a password reset, please ignore this email and your password will remain unchanged."
        else:
            subject = "Your OTP for Trading Bot Verification"
            greeting = "🔐 Trading Bot Verification"
            description = "Please use the following OTP to complete your verification:"
            warning_text = "If you didn't request this code, please ignore this email"

        message = f"Your OTP code is: {otp_code}. This code will expire in 5 minutes."

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                .container {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; }}
                .otp-box {{ background: white; padding: 20px; text-align: center; font-size: 32px; font-weight: bold; letter-spacing: 5px; margin: 20px 0; border-radius: 8px; border: 2px dashed #667eea; }}
                .footer {{ background: #333; color: #ccc; padding: 15px; text-align: center; font-size: 12px; border-radius: 0 0 8px 8px; }}
                .warning {{ background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 15px; border-radius: 4px; margin: 15px 0; }}
                .description {{ font-size: 16px; color: #333; margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{greeting}</h1>
                </div>
                <div class="content">
                    <h2>Your Verification Code</h2>
                    <p class="description">{description}</p>
                    <div class="otp-box">{otp_code}</div>
                    <div class="warning">
                        <strong>⚠️ Important:</strong>
                        <ul>
                            <li>This code will expire in <strong>5 minutes</strong></li>
                            <li>Do not share this code with anyone</li>
                            <li>{warning_text}</li>
                        </ul>
                    </div>
                </div>
                <div class="footer">
                    This is an automated message from Growth Quantix Trading Bot.<br>
                    Please do not reply to this email.
                </div>
            </div>
        </body>
        </html>
        """

        try:
            return self._send_email(
                recipient_email=recipient_email,
                subject=subject,
                plain_content=message,
                html_content=html_content,
            )
        except Exception as e:
            logger.error(f"❌ OTP email failed: {e}")
            return False

    def send_welcome_email(self, recipient_email: str, user_name: str) -> bool:
        """Send welcome email after successful registration"""
        subject = "Welcome to Growth Quantix Trading Bot! 🎉"
        message = f"Welcome {user_name}! Your account has been successfully verified."

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                .container {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; }}
                .header {{ background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%); color: white; padding: 30px; text-align: center; }}
                .content {{ padding: 30px; background: #f9f9f9; }}
                .feature {{ background: white; margin: 15px 0; padding: 20px; border-radius: 8px; border-left: 4px solid #4CAF50; }}
                .cta-button {{ background: #4CAF50; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Welcome to Growth Quantix!</h1>
                    <p>Your Trading Bot Account is Ready</p>
                </div>
                <div class="content">
                    <h2>Hello {user_name}! 👋</h2>
                    <p>Congratulations! Your Growth Quantix Trading Bot account has been successfully verified and is now active.</p>
                    
                    <div class="feature">
                        <h3>🚀 What's Next?</h3>
                        <ul>
                            <li>Connect your broker account (Upstox, Zerodha, etc.)</li>
                            <li>Configure your trading preferences</li>
                            <li>Start automated trading with AI signals</li>
                        </ul>
                    </div>
                    
                    <div class="feature">
                        <h3>🔧 Getting Started:</h3>
                        <ol>
                            <li>Log in to your dashboard</li>
                            <li>Complete broker integration</li>
                            <li>Set your risk parameters</li>
                            <li>Activate trading bot</li>
                        </ol>
                    </div>
                    
                    <center>
                        <a href="https://growthquantix.com/dashboard" class="cta-button">Go to Dashboard</a>
                    </center>
                    
                    <p><strong>Need Help?</strong> Contact our support team at support@growthquantix.com</p>
                </div>
            </div>
        </body>
        </html>
        """

        try:
            return self._send_email(
                recipient_email=recipient_email,
                subject=subject,
                plain_content=message,
                html_content=html_content,
            )
        except Exception as e:
            logger.error(f"❌ Welcome email failed: {e}")
            return False

    def send_password_reset_otp_email(
        self, recipient_email: str, otp_code: str
    ) -> bool:
        """Send OTP for password reset (replaces the old reset link method)"""
        return self.send_otp_email(recipient_email, otp_code, purpose="password_reset")

    def send_password_change_confirmation_email(
        self, recipient_email: str, user_name: str
    ) -> bool:
        """Send confirmation email after successful password change"""
        subject = "Password Changed Successfully - Trading Bot"
        message = f"Your Trading Bot account password has been successfully changed."

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                .container {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; }}
                .header {{ background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; }}
                .footer {{ background: #333; color: #ccc; padding: 15px; text-align: center; font-size: 12px; border-radius: 0 0 8px 8px; }}
                .success-box {{ background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 15px; border-radius: 4px; margin: 15px 0; }}
                .security-tip {{ background: #e2e3e5; border: 1px solid #d6d8db; color: #383d41; padding: 15px; border-radius: 4px; margin: 15px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✅ Password Changed Successfully</h1>
                </div>
                <div class="content">
                    <h2>Hello {user_name}!</h2>
                    <div class="success-box">
                        <strong>✅ Password Updated:</strong><br>
                        Your Trading Bot account password has been successfully changed on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}.
                    </div>
                    
                    <div class="security-tip">
                        <strong>🔐 Security Tips:</strong>
                        <ul>
                            <li>Keep your password secure and don't share it with anyone</li>
                            <li>Use a strong, unique password for your trading account</li>
                            <li>If you didn't make this change, contact support immediately</li>
                            <li>Consider enabling two-factor authentication for extra security</li>
                        </ul>
                    </div>
                    
                    <p><strong>Questions or concerns?</strong> Contact our support team at support@growthquantix.com</p>
                </div>
                <div class="footer">
                    This is an automated security notification from Growth Quantix Trading Bot.<br>
                    Please do not reply to this email.
                </div>
            </div>
        </body>
        </html>
        """

        try:
            return self._send_email(
                recipient_email=recipient_email,
                subject=subject,
                plain_content=message,
                html_content=html_content,
            )
        except Exception as e:
            logger.error(f"❌ Password change confirmation email failed: {e}")
            return False

    def _send_email(
        self,
        recipient_email: str,
        subject: str,
        plain_content: str,
        html_content: Optional[str] = None,
    ) -> bool:
        """Internal method to send email via SMTP"""
        try:
            if html_content:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = self.from_email
                msg["To"] = recipient_email

                part1 = MIMEText(plain_content, "plain")
                part2 = MIMEText(html_content, "html")

                msg.attach(part1)
                msg.attach(part2)
            else:
                msg = EmailMessage()
                msg["Subject"] = subject
                msg["From"] = self.from_email
                msg["To"] = recipient_email
                msg.set_content(plain_content)

            if self.port == 465:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(
                    self.smtp_server, self.port, context=context
                ) as server:
                    server.login(self.username, self.password)
                    server.send_message(msg)

            elif self.port == 587:
                with smtplib.SMTP(self.smtp_server, self.port) as server:
                    server.starttls()
                    server.login(self.username, self.password)
                    server.send_message(msg)
            else:
                logger.error("❌ Invalid port. Use 465 for SSL or 587 for TLS")
                return False

            logger.info(f"✅ Email sent successfully to {recipient_email}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"❌ SMTP Authentication failed: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"❌ SMTP error: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error sending email: {e}")
            return False

    def _create_trade_html(
        self, message: str, trade_data: Optional[dict] = None
    ) -> str:
        """Create HTML content for trade alerts"""
        if not trade_data:
            return f"<p>{message}</p>"

        status_color = (
            "#4CAF50" if trade_data.get("status") == "EXECUTED" else "#ff9800"
        )
        trade_type_emoji = "📈" if trade_data.get("trade_type") == "BUY" else "📉"

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                .container {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; }}
                .header {{ background: linear-gradient(135deg, {status_color} 0%, #45a049 100%); color: white; padding: 20px; text-align: center; }}
                .content {{ background: #f8f9fa; padding: 30px; }}
                .trade-details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .detail-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee; }}
                .detail-label {{ font-weight: bold; color: #333; }}
                .detail-value {{ color: #666; }}
                .status {{ background: {status_color}; color: white; padding: 5px 15px; border-radius: 20px; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{trade_type_emoji} Trade Execution Alert</h1>
                    <p>Your order has been processed</p>
                </div>
                <div class="content">
                    <div class="trade-details">
                        <h3 style="margin-top: 0; color: #333;">📊 Trade Details:</h3>
                        <div class="detail-row">
                            <span class="detail-label">Symbol:</span>
                            <span class="detail-value">{trade_data.get('symbol', 'N/A')}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Type:</span>
                            <span class="detail-value">{trade_data.get('trade_type', 'N/A')}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Price:</span>
                            <span class="detail-value">₹{trade_data.get('price', 'N/A')}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Quantity:</span>
                            <span class="detail-value">{trade_data.get('quantity', 'N/A')}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Status:</span>
                            <span class="status">{trade_data.get('status', 'N/A')}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Total Value:</span>
                            <span class="detail-value">₹{float(trade_data.get('price', 0)) * int(trade_data.get('quantity', 0)):,.2f}</span>
                        </div>
                    </div>
                    <p style="color: #666; text-align: center;">{message}</p>
                </div>
            </div>
        </body>
        </html>
        """


# Create singleton instance
email_service = EmailService()
