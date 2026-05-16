import pytest

def test_example():
    """Basic example test to verify pytest is working."""
    assert True

def test_addition():
    """Test basic arithmetic."""
    assert 1 + 1 == 2

def test_string_operations():
    """Test string operations."""
    text = "Hello, World!"
    assert text.lower() == "hello, world!"
    assert len(text) == 13
