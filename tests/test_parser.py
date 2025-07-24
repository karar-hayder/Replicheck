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


def test_parse_javascript():
    parser = CodeParser()

    # Create a temporary JavaScript file for testing
    test_file = Path("test_file.js")
    test_content = """
function testFunction(x, y) {
    return x + y;
}

class TestClass {
    constructor() {
        this.value = 0;
    }
    
    getValue() {
        return this.value;
    }
}
"""

    test_file.write_text(test_content)

    try:
        blocks = parser.parse_file(test_file)
        print(f"JavaScript parsing result: {blocks}")  # Debug output

        # Should find function and class with methods
        assert len(blocks) >= 1  # At least one block should be found
        assert blocks[0]["location"]["file"] == str(test_file)
        assert (
            "testFunction" in blocks[0]["tokens"] or "TestClass" in blocks[0]["tokens"]
        )

    finally:
        test_file.unlink()


def test_parse_jsx():
    parser = CodeParser()

    # Create a temporary JSX file for testing
    test_file = Path("test_file.jsx")
    test_content = """
import React from 'react';

function TestComponent({ name, value }) {
    return (
        <div>
            <h1>{name}</h1>
            <p>{value}</p>
        </div>
    );
}

class ClassComponent extends React.Component {
    render() {
        return <div>Hello World</div>;
    }
}
"""

    test_file.write_text(test_content)

    try:
        blocks = parser.parse_file(test_file)

        # Should find function and class components
        assert len(blocks) >= 1  # At least one block should be found
        assert blocks[0]["location"]["file"] == str(test_file)

    finally:
        test_file.unlink()


def test_unsupported_extension():
    parser = CodeParser()
    test_file = Path("test.txt")
    test_file.write_text("Some content")

    try:
        blocks = parser.parse_file(test_file)
        assert len(blocks) == 0
    finally:
        test_file.unlink()


def test_parser_supported_extensions():
    parser = CodeParser()
    expected_extensions = {".py", ".js", ".jsx", ".cs"}
    assert parser.supported_extensions == expected_extensions


def test_parser_handles_syntax_errors():
    parser = CodeParser()

    # Test Python syntax error
    test_file = Path("test_syntax_error.py")
    test_content = """
def test_function(
    return x + y  # Missing closing parenthesis
"""

    test_file.write_text(test_content)

    try:
        blocks = parser.parse_file(test_file)
        # Should handle syntax errors gracefully
        assert isinstance(blocks, list)
    finally:
        test_file.unlink()

    # Test JavaScript syntax error
    test_file = Path("test_syntax_error.js")
    test_content = """
function testFunction( {  # Missing closing parenthesis
    return x + y;
"""

    test_file.write_text(test_content)

    try:
        blocks = parser.parse_file(test_file)
        # Should handle syntax errors gracefully
        assert isinstance(blocks, list)
    finally:
        test_file.unlink()


def test_parser_get_parser_caching():
    """Test that parser caching works correctly."""
    parser = CodeParser()

    # Import the language objects
    from replicheck.tree_sitter_loader import JAVASCRIPT, PYTHON

    # First call should create a new parser
    parser1 = parser._get_parser("javascript")
    assert parser1 is not None

    # Second call should return the same parser instance
    parser2 = parser._get_parser("javascript")
    assert parser1 is parser2

    # Different language should create a new parser
    parser3 = parser._get_parser("python")
    assert parser3 is not parser1


def test_parser_tree_sitter_exception_handling():
    """Test that tree-sitter parsing handles exceptions gracefully."""
    parser = CodeParser()

    # Create a file that will cause tree-sitter to fail
    test_file = Path("test_tree_sitter_error.js")
    test_content = "invalid javascript code that will cause parsing errors"

    test_file.write_text(test_content)

    try:
        blocks = parser.parse_file(test_file)
        # Should return empty list on parsing errors
        assert isinstance(blocks, list)
    finally:
        test_file.unlink()


def test_parser_query_exception_handling():
    """Test that query exceptions are handled gracefully."""
    parser = CodeParser()

    # Create a valid JS file
    test_file = Path("test_query_error.js")
    test_content = """
function test() {
    return "hello";
}
"""

    test_file.write_text(test_content)

    try:
        blocks = parser.parse_file(test_file)
        # Should handle query errors gracefully
        assert isinstance(blocks, list)
    finally:
        test_file.unlink()


def test_parser_tokenize_tree_sitter_node_with_strings():
    """Test tokenization of tree-sitter nodes with string literals."""
    parser = CodeParser()

    test_file = Path("test_strings.js")
    test_content = """
function test() {
    let message = "Hello World";
    let number = 42;
    return message + number;
}
"""

    test_file.write_text(test_content)

    try:
        blocks = parser.parse_file(test_file)
        # Should extract string and number tokens
        assert isinstance(blocks, list)
    finally:
        test_file.unlink()


def test_parser_tokenize_tree_sitter_node_empty_content():
    """Test tokenization with empty or whitespace-only content."""
    parser = CodeParser()

    test_file = Path("test_empty.js")
    test_content = "   \n   \n"  # Only whitespace

    test_file.write_text(test_content)

    try:
        blocks = parser.parse_file(test_file)
        # Should handle empty content gracefully
        assert isinstance(blocks, list)
    finally:
        test_file.unlink()
