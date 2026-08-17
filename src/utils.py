"""
Formatting & Calculation Utility Module.

Provides standard string formatters, percentage helpers, date parsers,
and calculation helpers across the codebase.
"""

from typing import Union


def format_percentage(value: float, decimals: int = 1) -> str:
    """Formats float value as percentage string."""
    if value is None:
        return "0.0%"
    return f"{value * 100:.{decimals}f}%"


def format_kwh(value: float) -> str:
    """Formats floating kWh value with unit suffix."""
    if value is None:
        return "0.00 kWh"
    return f"{value:.2f} kWh"


def sanitize_id(identifier: str) -> str:
    """Sanitizes consumer or transformer ID string."""
    if not identifier:
        return "UNKNOWN"
    return str(identifier).strip().upper()
