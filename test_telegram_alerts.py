import asyncio
import os
import sys
from pathlib import Path

# Add project root to path so we can import services
sys.path.append(str(Path(__file__).parent))

from services.notifications.alert_manager import alert_manager
from database.connection import SessionLocal
from database.models import User

async def run_test():
    print("🚀 Starting Telegram Notification Production Test...")
    
    # --- TEST 1: ADMIN SYSTEM ALERTS ---
    print("\n📡 Phase 1: Testing Admin System Alerts...")
    try:
        await alert_manager.send_admin_system_status(
            component="Test Suite",
            status="OPERATIONAL",
            details="Admin notification system is verified and active."
        )
        print("✅ Admin System Status sent!")
        
        await alert_manager.send_market_intelligence(
            sentiment="bullish",
            ad_ratio=2.45,
            top_sectors=["BANKING", "IT", "ENERGY"]
        )
        print("✅ Market Intelligence report sent!")
    except Exception as e:
        print(f"❌ Admin Test Failed: {e}")

    # --- TEST 2: USER TRADE ALERTS ---
    print("\n🎯 Phase 2: Testing User Trade Alerts...")
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == 1).first()
        
        if user:
            print(f"👤 Found User: {user.email} (ID: {user.id})")
            
            await alert_manager.notify_trade_entry(
                user_id=user.id,
                trade_data={
                    "symbol": "NIFTY TEST",
                    "option_type": "CE",
                    "entry_price": 150.25,
                    "stop_loss": 130.00,
                    "target": 190.00,
                    "trading_mode": "paper",
                    "quantity": 50 # Add missing quantity
                }
            )
            print(f"✅ Trade alert routed for user {user.id}!")
        else:
            print("❌ No user with ID 1 found in database. Skipping user test.")
    except Exception as e:
        print(f"❌ User Test Failed: {e}")
    finally:
        db.close()

    print("\n✨ Test sequence finished!")

if __name__ == "__main__":
    asyncio.run(run_test())