"""
Tests for the code parser functionality.
"""

from pathlib import Path

import pytest

from replicheck.parser import CodeParser


def test_parse_python():
    parser = CodeParser()

    # Create a temporary Python file for testing
    test_file = Path("test_file.py")
    test_content = """
def test_function(x, y):
    return x + y

class TestClass:
    def __init__(self):
        self.value = 0
    """

    test_file.write_text(test_content)

    try:
        blocks = parser.parse_file(test_file)

        assert len(blocks) == 3  # One function and two methods
        assert blocks[0]["location"]["file"] == str(test_file)
        assert blocks[0]["location"]["start_line"] == 2
        assert "test_function" in blocks[0]["tokens"]
        assert "TestClass" in blocks[1]["tokens"]

    finally:
        test_file.unlink()  # Clean up


def test_unsupported_extension():
    parser = CodeParser()
    test_file = Path("test.txt")
    test_file.write_text("Some content")

    try:
        blocks = parser.parse_file(test_file)
        assert len(blocks) == 0
    finally:
        test_file.unlink()
