from datetime import datetime, time


def is_market_open():
    """
    Check if NSE market is currently open

    Market hours: Monday to Friday, 9:15 AM to 3:30 PM IST

    Returns:
        bool: True if market is open, False otherwise
    """
    now = datetime.now()

    # Check if it's a weekend (Saturday=5, Sunday=6)
    if now.weekday() >= 5:
        return False

    # Check market hours (9:15 AM to 3:30 PM)
    current_time = now.time()
    return time(9, 15) <= current_time <= time(15, 30)
