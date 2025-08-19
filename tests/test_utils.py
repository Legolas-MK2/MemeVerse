import pytest
import asyncio
from utils.helpers import format_number

def test_format_number():
    """Test the format_number helper function."""
    # Test basic numbers
    assert format_number(0) == "0"
    assert format_number(1) == "1"
    assert format_number(999) == "999"
    
    # Test thousands
    assert format_number(1000) == "1.0K"
    assert format_number(1500) == "1.5K"
    assert format_number(1999) == "2.0K"
    
    # Test millions
    assert format_number(1000000) == "1.0M"
    assert format_number(1500000) == "1.5M"
    assert format_number(9999999) == "10.0M"
    
    # Test with None
    assert format_number(None) == "0"
