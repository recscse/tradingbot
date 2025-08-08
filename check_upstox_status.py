#!/usr/bin/env python3
"""
Quick status check for Upstox automation system
Use this to quickly see if automation would trigger
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from database.connection import SessionLocal
from database.models import BrokerConfig, User


def check_upstox_status():
    """Check current status of Upstox brokers and automation trigger conditions"""

    print("🔍 UPSTOX AUTOMATION STATUS CHECK")
    print("=" * 50)

    # Check environment (login credentials)
    mobile = os.getenv("UPSTOX_MOBILE", "")
    pin = os.getenv("UPSTOX_PIN", "")
    totp_key = os.getenv("UPSTOX_TOTP_KEY", "")

    print("📋 Environment Configuration (Login Credentials):")
    env_ok = True
    if not mobile or mobile == "your_mobile_number":
        print("  ❌ UPSTOX_MOBILE: Not configured or using example value")
        env_ok = False
    else:
        print(f"  ✅ UPSTOX_MOBILE: {mobile[:4]}****{mobile[-2:]}")

    if not pin or pin == "your_6_digit_pin":
        print("  ❌ UPSTOX_PIN: Not configured or using example value")
        env_ok = False
    else:
        print(f"  ✅ UPSTOX_PIN: {'*' * len(pin)}")

    if not totp_key:
        print(
            "  ⚠️ UPSTOX_TOTP_KEY: Not configured or using example value (recommended for automation)"
        )
    else:
        print(f"  ✅ UPSTOX_TOTP_KEY: {totp_key[:8]}****")

    # Check database
    db = SessionLocal()
    try:
        print(f"\n📊 Database Brokers (API Credentials):")

        upstox_brokers = (
            db.query(BrokerConfig)
            .filter(BrokerConfig.broker_name.ilike("upstox"))
            .all()
        )

        if not upstox_brokers:
            print("  ❌ No Upstox brokers found in database")
            print(
                "  💡 You need to configure at least one Upstox broker through the UI"
            )
            return False

        now = datetime.now()
        tomorrow = now + timedelta(days=1)

        print(f"  📈 Total Upstox brokers: {len(upstox_brokers)}")

        would_trigger = False
        admin_expired = 0
        user_expired = 0
        missing_api_creds = 0

        for broker in upstox_brokers:
            # Check API credentials in database
            has_api_key = bool(
                broker.api_key and broker.api_key != "your_upstox_api_key"
            )
            has_api_secret = bool(
                broker.api_secret and broker.api_secret != "your_upstox_api_secret"
            )

            if not has_api_key or not has_api_secret:
                missing_api_creds += 1
            user = db.query(User).filter(User.id == broker.user_id).first()
            user_role = user.role if user else "Unknown"
            is_admin = user_role and user_role.lower() == "admin"

            if not broker.access_token_expiry:
                status = "❓ No expiry set"
                will_refresh = False
            elif broker.access_token_expiry <= tomorrow:
                if broker.access_token_expiry < now:
                    status = "🔴 EXPIRED"
                else:
                    status = "🟡 EXPIRES SOON"
                will_refresh = True
                would_trigger = True

                if is_admin:
                    admin_expired += 1
                else:
                    user_expired += 1
            else:
                status = "🟢 VALID"
                will_refresh = False

            expiry_str = (
                broker.access_token_expiry.strftime("%Y-%m-%d %H:%M:%S")
                if broker.access_token_expiry
                else "Not set"
            )
            active_str = "🟢 ACTIVE" if broker.is_active else "🔴 INACTIVE"

            # API credentials status
            api_key_status = "✅" if has_api_key else "❌"
            api_secret_status = "✅" if has_api_secret else "❌"

            print(
                f"\n    📋 Broker ID {broker.id} (User {broker.user_id} - {user_role}):"
            )
            print(f"      Status: {active_str}")
            print(
                f"      API Key: {api_key_status} {'Valid' if has_api_key else 'Missing/Invalid'}"
            )
            print(
                f"      API Secret: {api_secret_status} {'Valid' if has_api_secret else 'Missing/Invalid'}"
            )
            print(f"      Token Status: {status}")
            print(f"      Expires: {expiry_str}")

            can_refresh = (
                will_refresh and broker.is_active and has_api_key and has_api_secret
            )
            print(f"      Will refresh: {'✅ YES' if can_refresh else '❌ NO'}")

            if broker.last_error_message:
                print(f"      Last Error: {broker.last_error_message}")

            # Override would_trigger if missing API credentials
            if will_refresh and (not has_api_key or not has_api_secret):
                would_trigger = False

        print(f"\n📊 Summary:")
        print(f"  Total brokers: {len(upstox_brokers)}")
        print(f"  Missing API credentials: {missing_api_creds}")

        print(f"\n🎯 AUTOMATION TRIGGER STATUS:")
        if would_trigger and env_ok and missing_api_creds == 0:
            print("  ✅ AUTOMATION WOULD TRIGGER")
            print(f"  📊 Admin brokers to refresh: {admin_expired}")
            print(f"  📊 User brokers to refresh: {user_expired}")
            print(f"  🕐 Next scheduled run: Daily at 4:00 AM and 6:00 AM")
            print(f"  🔍 Monitoring: Every 2 hours for expired tokens")
        elif would_trigger and not env_ok:
            print("  ⚠️ TOKENS NEED REFRESH BUT LOGIN CREDENTIALS NOT CONFIGURED")
            print("  💡 Fix UPSTOX_MOBILE and UPSTOX_PIN in .env file")
        elif would_trigger and missing_api_creds > 0:
            print("  ⚠️ TOKENS NEED REFRESH BUT API CREDENTIALS MISSING")
            print("  💡 Configure API Key and Secret for brokers in database")
        elif not would_trigger:
            print("  ℹ️ No tokens need refresh currently")
            print("  ✅ All tokens are valid")
        else:
            print("  ⚠️ CONFIGURATION ISSUES DETECTED")
            print("  💡 Check the details above")

        return would_trigger and env_ok and missing_api_creds == 0

    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return False
    finally:
        db.close()


def main():
    """Main function"""
    try:
        result = check_upstox_status()

        print(f"\n{'='*50}")
        if result:
            print("🚀 AUTOMATION IS READY AND WOULD RUN")
            print("💡 To test manually: python test_upstox_automation_enhanced.py")
            print("💡 To start automation: python app.py")
        else:
            print("⚠️ AUTOMATION NEEDS CONFIGURATION")
            print("💡 Fix the issues above and run this check again")

        return result

    except Exception as e:
        print(f"💥 Status check failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
