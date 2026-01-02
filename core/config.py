import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_env_variable(name, default=None, required=False):
    value = os.getenv(name, default)
    if required and not value:
        raise ValueError(f"ERROR: {name} is missing in .env file!")
    return value

# Secret Keys for JWT Tokens
JWT_SECRET = get_env_variable("JWT_SECRET", required=True)
REFRESH_SECRET = os.getenv("REFRESH_SECRET", JWT_SECRET)

# Token Expiry Settings
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 36000)) # 10 hours
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# ZeptoMail Configuration
ZEPTOMAIL_HOST = os.getenv("ZEPTOMAIL_HOST", "smtp.zeptomail.in")
ZEPTOMAIL_PORT = int(os.getenv("ZEPTOMAIL_PORT", "587"))
ZEPTOMAIL_USERNAME = os.getenv("ZEPTOMAIL_USERNAME")
ZEPTOMAIL_PASSWORD = os.getenv("ZEPTOMAIL_PASSWORD")
ZEPTOMAIL_FROM_EMAIL = os.getenv("ZEPTOMAIL_FROM_EMAIL", "noreply@growthquantix.com")

# Legacy Email Configuration
EMAIL_HOST = ZEPTOMAIL_HOST
EMAIL_PORT = ZEPTOMAIL_PORT
EMAIL_USERNAME = ZEPTOMAIL_USERNAME
EMAIL_PASSWORD = ZEPTOMAIL_PASSWORD

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

# Upstox API Configuration
API_KEY = os.getenv("UPSTOX_API_KEY")
API_SECRET = os.getenv("UPSTOX_API_SECRET")
REDIRECT_URI = os.getenv("UPSTOX_REDIRECT_URI")
ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")
WS_URL = os.getenv("UPSTOX_WS_URL", "wss://api.upstox.com/live/market-data")

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")

