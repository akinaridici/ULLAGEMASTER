"""
Decimal Utilities for UllageMaster.

Provides locale-independent decimal handling to ensure consistent behavior
across different Windows regional settings (e.g., Turkish uses comma,
English uses dot as decimal separator).

Maritime standard: Always use DOT (period) as decimal separator.
"""

from typing import Union
from PyQt6.QtWidgets import QDoubleSpinBox
from PyQt6.QtGui import QValidator
from PyQt6.QtCore import QLocale


def parse_decimal(value: Union[str, int, float]) -> float:
    """
    Parse a string to float, accepting both comma and dot as decimal separator.
    
    This ensures consistent parsing regardless of Windows locale settings.
    Maritime industry standard uses DOT as decimal separator.
    
    Args:
        value: String, int, or float to parse
        
    Returns:
        Parsed float value
        
    Raises:
        ValueError: If value cannot be parsed to float
        
    Examples:
        >>> parse_decimal("123.45")
        123.45
        >>> parse_decimal("123,45")
        123.45
        >>> parse_decimal(123.45)
        123.45
    """
    if isinstance(value, (int, float)):
        return float(value)
    
    if not value or not str(value).strip():
        raise ValueError("Cannot parse empty value to decimal")
    
    # Replace comma with dot for consistency
    normalized = str(value).strip().replace(',', '.')
    return float(normalized)


def parse_decimal_or_zero(value: Union[str, int, float, None]) -> float:
    """
    Parse a string to float, returning 0.0 for empty/None values.
    
    Convenience wrapper around parse_decimal that doesn't raise on empty input.
    
    Args:
        value: String, int, float, or None to parse
        
    Returns:
        Parsed float value, or 0.0 if value is empty/None
        
    Examples:
        >>> parse_decimal_or_zero("123.45")
        123.45
        >>> parse_decimal_or_zero("")
        0.0
        >>> parse_decimal_or_zero(None)
        0.0
    """
    if value is None:
        return 0.0
    
    try:
        return parse_decimal(value)
    except (ValueError, TypeError):
        return 0.0


class LocaleIndependentDoubleSpinBox(QDoubleSpinBox):
    """
    A QDoubleSpinBox that always uses DOT as the decimal separator,
    regardless of system locale settings.
    
    This ensures consistent display and input across different Windows
    regional settings (Turkish, English, etc.).
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Set C locale which uses DOT as decimal separator
        c_locale = QLocale(QLocale.Language.C)
        self.setLocale(c_locale)
    
    def textFromValue(self, value: float) -> str:
        """Format value using DOT as decimal separator."""
        # Use C locale formatting (DOT separator)
        decimals = self.decimals()
        return f"{value:.{decimals}f}"
    
    def valueFromText(self, text: str) -> float:
        """Parse text accepting both comma and dot as separator."""
        try:
            return parse_decimal(text)
        except ValueError:
            return 0.0


class DotDecimalValidator(QValidator):
    """
    A QValidator that validates decimal numbers using DOT as separator.
    
    Unlike QDoubleValidator, this always uses DOT regardless of locale settings.
    It also accepts comma input and treats it as a decimal separator.
    """
    
    def __init__(self, bottom: float = 0.0, top: float = 999999999.0, 
                 decimals: int = 3, parent=None):
        """
        Initialize the validator.
        
        Args:
            bottom: Minimum allowed value
            top: Maximum allowed value
            decimals: Maximum number of decimal places
            parent: Parent QObject
        """
        super().__init__(parent)
        self._bottom = bottom
        self._top = top
        self._decimals = decimals
    
    def validate(self, input_str: str, pos: int) -> tuple:
        """
        Validate the input string.
        
        Returns:
            Tuple of (State, string, position)
        """
        if not input_str:
            return (QValidator.State.Intermediate, input_str, pos)
        
        # Replace comma with dot for validation
        normalized = input_str.replace(',', '.')
        
        # Check for valid number format
        # Allow: digits, single dot, optional leading minus
        if normalized == '-' or normalized == '.':
            return (QValidator.State.Intermediate, input_str, pos)
        
        # Count decimal points
        dot_count = normalized.count('.')
        if dot_count > 1:
            return (QValidator.State.Invalid, input_str, pos)
        
        # Check decimal places
        if '.' in normalized:
            parts = normalized.split('.')
            if len(parts[1]) > self._decimals:
                return (QValidator.State.Invalid, input_str, pos)
        
        # Try to parse as float
        try:
            value = float(normalized)
            
            # Check range
            if value < self._bottom or value > self._top:
                return (QValidator.State.Intermediate, input_str, pos)
            
            return (QValidator.State.Acceptable, input_str, pos)
            
        except ValueError:
            # Check if it's a partial valid input (e.g., "123." or "-")
            if normalized.endswith('.') or normalized == '-':
                return (QValidator.State.Intermediate, input_str, pos)
            return (QValidator.State.Invalid, input_str, pos)
    
    def fixup(self, input_str: str) -> str:
        """
        Fix invalid input by replacing comma with dot.
        """
        return input_str.replace(',', '.')
