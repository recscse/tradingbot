from datetime import datetime, time
from utils.timezone_utils import get_ist_now


def is_market_open():
    """
    Check if NSE market is currently open

    Market hours: Monday to Friday, 9:15 AM to 3:30 PM IST

    Returns:
        bool: True if market is open, False otherwise
    """
    # Get current time in IST
    now_ist = get_ist_now()

    # Check if it's a weekend (Saturday=5, Sunday=6)
    if now_ist.weekday() >= 5:
        return False

    # Check market hours (9:15 AM to 3:30 PM)
    current_time = now_ist.time()
    return time(9, 15) <= current_time <= time(15, 30)
