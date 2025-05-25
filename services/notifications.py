from services.email.email_service import email_service
from twilio.rest import Client
from core.config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER
import logging

logger = logging.getLogger(__name__)


def send_trade_email(
    subject: str, body: str, recipient_email: str, trade_data: dict = None
) -> bool:
    """Send trade execution alert via Email using ZeptoMail"""
    try:
        success = email_service.send_trade_alert(
            recipient_email=recipient_email,
            subject=subject,
            message=body,
            trade_data=trade_data,
        )

        if success:
            logger.info(f"✅ Trade email sent successfully to {recipient_email}")
        else:
            logger.error(f"❌ Failed to send trade email to {recipient_email}")

        return success

    except Exception as e:
        logger.error(f"❌ Trade Email Alert Failed: {e}")
        return False


def send_notification_email(subject: str, body: str, recipient_email: str) -> bool:
    """Send general notification via Email"""
    try:
        success = email_service.send_notification(
            recipient_email=recipient_email, subject=subject, message=body
        )

        if success:
            logger.info(f"✅ Notification email sent successfully to {recipient_email}")
        else:
            logger.error(f"❌ Failed to send notification email to {recipient_email}")

        return success

    except Exception as e:
        logger.error(f"❌ Notification Email Failed: {e}")
        return False


def send_welcome_email(recipient_email: str, user_name: str) -> bool:
    """Send welcome email after successful registration"""
    try:
        success = email_service.send_welcome_email(recipient_email, user_name)

        if success:
            logger.info(f"✅ Welcome email sent successfully to {recipient_email}")
        else:
            logger.error(f"❌ Failed to send welcome email to {recipient_email}")

        return success

    except Exception as e:
        logger.error(f"❌ Welcome Email Failed: {e}")
        return False


def send_password_reset_email(recipient_email: str, reset_token: str) -> bool:
    """Send password reset email"""
    try:
        success = email_service.send_password_reset_email(recipient_email, reset_token)

        if success:
            logger.info(
                f"✅ Password reset email sent successfully to {recipient_email}"
            )
        else:
            logger.error(f"❌ Failed to send password reset email to {recipient_email}")

        return success

    except Exception as e:
        logger.error(f"❌ Password reset Email Failed: {e}")
        return False


def send_trade_sms(message: str, recipient_number: str) -> bool:
    """Send trade execution alert via SMS"""
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
        logger.warning("⚠️ Twilio credentials not configured, skipping SMS")
        return False

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message_instance = client.messages.create(
            body=message, from_=TWILIO_PHONE_NUMBER, to=recipient_number
        )

        logger.info(
            f"✅ SMS sent successfully to {recipient_number}, SID: {message_instance.sid}"
        )
        return True

    except Exception as e:
        logger.error(f"❌ SMS Alert Failed: {e}")
        return False


def send_multi_channel_alert(
    email: str, phone: str, subject: str, message: str, trade_data: dict = None
) -> dict:
    """Send alert via both email and SMS"""
    email_success = False
    sms_success = False

    # Send email
    if email:
        email_success = send_trade_email(subject, message, email, trade_data)

    # Send SMS
    if phone:
        # Create shorter message for SMS
        if trade_data:
            sms_message = f"Trade Alert: {trade_data.get('symbol', 'Unknown')} {trade_data.get('trade_type', '')} @ ₹{trade_data.get('price', 'N/A')}"
        else:
            sms_message = message[:160]  # SMS character limit
        sms_success = send_trade_sms(sms_message, phone)

    return {
        "email_sent": email_success,
        "sms_sent": sms_success,
        "success": email_success or sms_success,
    }


def send_broker_connection_alert(
    recipient_email: str, broker_name: str, status: str
) -> bool:
    """Send broker connection status alert"""
    subject = f"Broker Connection Update - {broker_name}"

    if status == "connected":
        message = f"✅ Your {broker_name} account has been successfully connected to the trading bot."
    elif status == "disconnected":
        message = (
            f"❌ Your {broker_name} account connection has been lost. Please reconnect."
        )
    elif status == "error":
        message = f"⚠️ There was an error with your {broker_name} account connection. Please check your credentials."
    else:
        message = f"📊 {broker_name} account status: {status}"

    return send_notification_email(subject, message, recipient_email)


def send_daily_trading_summary(recipient_email: str, summary_data: dict) -> bool:
    """Send daily trading summary email"""
    subject = f"📊 Daily Trading Summary - {summary_data.get('date', 'Today')}"

    message = f"""
Daily Trading Summary:
- Total Trades: {summary_data.get('total_trades', 0)}
- Profitable Trades: {summary_data.get('profitable_trades', 0)}
- Total P&L: ₹{summary_data.get('total_pnl', 0):,.2f}
- Win Rate: {summary_data.get('win_rate', 0):.1f}%
- Active Positions: {summary_data.get('active_positions', 0)}
"""

    return send_notification_email(subject, message, recipient_email)
