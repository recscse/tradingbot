"""
Timezone Utilities for IST (Indian Standard Time)
Ensures all timestamps are correctly stored and displayed in IST
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
import pytz

# Indian Standard Time timezone
IST = pytz.timezone('Asia/Kolkata')


def get_ist_now() -> datetime:
    """
    Get current datetime in IST timezone

    Returns:
        Timezone-aware datetime in IST
    """
    return datetime.now(IST)


def get_ist_now_naive() -> datetime:
    """
    Get current datetime in IST timezone (naive, without timezone info)
    Use this for database storage with DateTime columns

    Returns:
        Naive datetime in IST
    """
    return datetime.now(IST).replace(tzinfo=None)


def utc_to_ist(utc_dt: datetime) -> datetime:
    """
    Convert UTC datetime to IST

    Args:
        utc_dt: UTC datetime (naive or aware)

    Returns:
        IST datetime (naive)
    """
    if utc_dt is None:
        return None

    # If naive, assume it's UTC
    if utc_dt.tzinfo is None:
        utc_dt = pytz.utc.localize(utc_dt)

    # Convert to IST
    ist_dt = utc_dt.astimezone(IST)

    # Return naive datetime (without timezone info)
    return ist_dt.replace(tzinfo=None)


def ist_to_utc(ist_dt: datetime) -> datetime:
    """
    Convert IST datetime to UTC

    Args:
        ist_dt: IST datetime (naive or aware)

    Returns:
        UTC datetime (naive)
    """
    if ist_dt is None:
        return None

    # If naive, assume it's IST
    if ist_dt.tzinfo is None:
        ist_dt = IST.localize(ist_dt)

    # Convert to UTC
    utc_dt = ist_dt.astimezone(pytz.utc)

    # Return naive datetime (without timezone info)
    return utc_dt.replace(tzinfo=None)


def format_ist_datetime(dt: datetime, format_string: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format datetime in IST timezone

    Args:
        dt: Datetime to format (naive or aware)
        format_string: strftime format string

    Returns:
        Formatted datetime string in IST
    """
    if dt is None:
        return None

    # If naive, assume it's already IST
    if dt.tzinfo is None:
        return dt.strftime(format_string)

    # Convert to IST and format
    ist_dt = dt.astimezone(IST)
    return ist_dt.strftime(format_string)


def get_ist_isoformat(dt: Optional[datetime] = None) -> str:
    """
    Get ISO format string in IST timezone

    Args:
        dt: Datetime to format (if None, uses current time)

    Returns:
        ISO format string in IST (e.g., "2025-01-21T15:30:45")
    """
    if dt is None:
        dt = get_ist_now_naive()

    # If naive, assume it's already IST
    if dt.tzinfo is None:
        return dt.isoformat()

    # Convert to IST and get ISO format
    ist_dt = dt.astimezone(IST)
    return ist_dt.replace(tzinfo=None).isoformat()


def get_market_time_ist() -> datetime:
    """
    Get current market time in IST (for trading hours validation)

    Returns:
        Current IST time
    """
    return get_ist_now_naive()


def get_ist_date_today() -> str:
    """
    Get today's date in IST timezone (YYYY-MM-DD format)

    Returns:
        Date string in IST
    """
    return get_ist_now_naive().strftime("%Y-%m-%d")


def get_ist_time_now() -> str:
    """
    Get current time in IST timezone (HH:MM:SS format)

    Returns:
        Time string in IST
    """
    return get_ist_now_naive().strftime("%H:%M:%S")


# Legacy compatibility - can be removed after migration
def now() -> datetime:
    """
    Replacement for datetime.now() - returns IST time

    Returns:
        Naive datetime in IST
    """
    return get_ist_now_naive()
