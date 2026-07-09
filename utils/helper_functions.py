"""
General auxiliary helper functions for formatting and displaying data.
"""

from typing import Dict, Any

def get_status_color(status: str) -> str:
    """
    Returns hex codes or emojis corresponding to Green, Yellow, and Red health statuses.
    """
    status_lower = status.lower()
    if "green" in status_lower or status_lower == "completed":
        return "🟢"
    elif "yellow" in status_lower or "progress" in status_lower:
        return "🟡"
    elif "red" in status_lower or "delay" in status_lower or "block" in status_lower:
        return "🔴"
    return "⚪"

def format_currency(amount: float, currency_symbol: str = "$") -> str:
    """Formats float numbers as currency values."""
    try:
        return f"{currency_symbol}{amount:,.2f}"
    except (ValueError, TypeError):
        return f"{currency_symbol}0.00"

def calculate_percentage(part: float, whole: float) -> float:
    """Calculates percentage safely, avoiding division by zero."""
    if not whole:
        return 0.0
    return round((part / whole) * 100.0, 2)
