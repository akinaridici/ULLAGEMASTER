"""
Test suite for decimal_utils.py

Tests the locale-independent decimal parsing and widgets.
"""

import sys
import os

# Add src to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from utils.decimal_utils import (
    parse_decimal,
    parse_decimal_or_zero,
    LocaleIndependentDoubleSpinBox,
    DotDecimalValidator
)


def test_parse_decimal_dot():
    """Test parsing with dot separator."""
    assert parse_decimal("123.456") == 123.456
    assert parse_decimal("0.5") == 0.5
    assert parse_decimal("1000.00") == 1000.0
    print("✓ parse_decimal with DOT works correctly")


def test_parse_decimal_comma():
    """Test parsing with comma separator (Turkish locale)."""
    assert parse_decimal("123,456") == 123.456
    assert parse_decimal("0,5") == 0.5
    assert parse_decimal("1000,00") == 1000.0
    print("✓ parse_decimal with COMMA works correctly")


def test_parse_decimal_numbers():
    """Test parsing actual numbers (int/float)."""
    assert parse_decimal(123.456) == 123.456
    assert parse_decimal(100) == 100.0
    print("✓ parse_decimal with numbers works correctly")


def test_parse_decimal_or_zero():
    """Test parse_decimal_or_zero for edge cases."""
    assert parse_decimal_or_zero("") == 0.0
    assert parse_decimal_or_zero(None) == 0.0
    assert parse_decimal_or_zero("invalid") == 0.0
    assert parse_decimal_or_zero("123.45") == 123.45
    assert parse_decimal_or_zero("123,45") == 123.45
    print("✓ parse_decimal_or_zero handles edge cases correctly")


def test_validator():
    """Test DotDecimalValidator."""
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    
    validator = DotDecimalValidator(0, 1000, 3)
    
    # Valid inputs
    result1 = validator.validate("123.456", 0)
    assert result1[0].name == "Acceptable", f"Expected Acceptable, got {result1[0]}"
    
    result2 = validator.validate("123,456", 0)  # Comma should be acceptable
    assert result2[0].name == "Acceptable", f"Expected Acceptable, got {result2[0]}"
    
    # Invalid - too many decimals
    result3 = validator.validate("123.45678", 0)
    assert result3[0].name == "Invalid", f"Expected Invalid, got {result3[0]}"
    
    print("✓ DotDecimalValidator works correctly")


def test_spinbox():
    """Test LocaleIndependentDoubleSpinBox."""
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    
    spinbox = LocaleIndependentDoubleSpinBox()
    spinbox.setDecimals(3)
    spinbox.setValue(123.456)
    
    # Text should always use DOT
    text = spinbox.textFromValue(123.456)
    assert "." in text, f"Expected dot in '{text}'"
    assert "," not in text, f"Unexpected comma in '{text}'"
    
    # Parsing should accept comma
    value = spinbox.valueFromText("123,789")
    assert value == 123.789, f"Expected 123.789, got {value}"
    
    print("✓ LocaleIndependentDoubleSpinBox works correctly")


if __name__ == "__main__":
    print("\n=== Decimal Utils Tests ===\n")
    
    test_parse_decimal_dot()
    test_parse_decimal_comma()
    test_parse_decimal_numbers()
    test_parse_decimal_or_zero()
    test_validator()
    test_spinbox()
    
    print("\n=== All Tests Passed! ===\n")
