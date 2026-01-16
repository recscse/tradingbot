
import logging
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cleanup_mock_data")

from database.connection import SessionLocal
from database.models import SelectedStock
from utils.timezone_utils import get_ist_now_naive

def cleanup():
    """
    Remove the mock selected stock inserted for testing.
    """
    db = SessionLocal()
    try:
        today = get_ist_now_naive().date()
        logger.info(f"📅 Cleaning up mock data for date: {today}")

        # Delete by the specific reason we used
        deleted_count = db.query(SelectedStock).filter(
            SelectedStock.selection_date == today,
            SelectedStock.selection_reason == "MOCK_TEST_FOR_CONNECTIVITY"
        ).delete()
        
        db.commit()
        
        if deleted_count > 0:
            logger.info(f"✅ Successfully removed {deleted_count} mock stock record(s).")
        else:
            logger.info("ℹ️ No mock records found to delete.")

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    cleanup()
