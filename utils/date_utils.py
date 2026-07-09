"""
Utility functions for parsing, formatting, and calculating date ranges for reports.
"""

from datetime import datetime, timedelta
from typing import Optional
from utils.logger import get_logger

logger = get_logger(__name__)

def parse_date(date_str: str, formats: Optional[list] = None) -> datetime:
    """
    Attempts to parse a date string using standard project date formats.
    """
    if not formats:
        formats = ["%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d"]
        
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
            
    logger.warning(f"Could not parse date '{date_str}' with standard formats. Returning current date.")
    return datetime.now()

def format_date(date: datetime, fmt: str = "%Y-%m-%d") -> str:
    """Formats a datetime object to string."""
    return date.strftime(fmt)

def get_current_week_ending(date: Optional[datetime] = None) -> str:
    """
    Returns the Friday date of the week for the given date (defaulting to current local date) 
    in YYYY-MM-DD format.
    """
    if not date:
        date = datetime.now()
        
    # Calculate days to Friday (where Monday is 0, Friday is 4)
    weekday = date.weekday()
    days_to_friday = 4 - weekday
    
    friday = date + timedelta(days=days_to_friday)
    return format_date(friday)

def calculate_days_between(start_date: str, end_date: str) -> int:
    """Calculates difference in days between two date strings (YYYY-MM-DD)."""
    try:
        start = parse_date(start_date)
        end = parse_date(end_date)
        return (end - start).days
    except Exception as e:
        logger.error(f"Error calculating days between {start_date} and {end_date}: {e}")
        return 0
