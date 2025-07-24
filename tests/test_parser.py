"""
Tests for the code parser functionality.
"""

from pathlib import Path

import pytest

from replicheck.parser import CodeParser


def test_parse_python():
    parser = CodeParser()

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

        assert len(blocks) == 3
        assert blocks[0]["location"]["file"] == str(test_file)
        assert blocks[0]["location"]["start_line"] == 2
        assert "test_function" in blocks[0]["tokens"]
        assert "TestClass" in blocks[1]["tokens"]

    finally:
        test_file.unlink()


def test_parse_javascript():
    parser = CodeParser()

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

        assert len(blocks) >= 1
        assert blocks[0]["location"]["file"] == str(test_file)
        assert (
            "testFunction" in blocks[0]["tokens"] or "TestClass" in blocks[0]["tokens"]
        )

    finally:
        test_file.unlink()


def test_parse_typescript():
    parser = CodeParser()

    test_file = Path("test_file.ts")
    test_content = """
function greet(name: string): string {
    return `Hello, ${name}`;
}

class Greeter {
    private greeting: string;

    constructor(message: string) {
        this.greeting = message;
    }

    greet() {
        return "Hello, " + this.greeting;
    }
}
"""
    test_file.write_text(test_content)

    try:
        blocks = parser.parse_file(test_file)
        assert len(blocks) >= 2
        names = [t[0] for t in [b["tokens"] for b in blocks] if t]
        assert "greet" in names or "Greeter" in names
        assert all(b["location"]["file"] == str(test_file) for b in blocks)
    finally:
        test_file.unlink()


def test_parse_tsx():
    parser = CodeParser()

    test_file = Path("test_file.tsx")
    test_content = """
import React from "react";

type Props = {
  name: string;
};

export default function HelloWorld({ name }: Props) {
  return <div>Hello, {name}</div>;
}

class App extends React.Component {
  render() {
    return <HelloWorld name="TSX" />;
  }
}
"""
    test_file.write_text(test_content)

    try:
        blocks = parser.parse_file(test_file)
        assert len(blocks) >= 2
        names = [t[0] for t in [b["tokens"] for b in blocks] if t]
        assert "HelloWorld" in names or "App" in names
    finally:
        test_file.unlink()


def test_parse_csharp():
    parser = CodeParser()

    test_file = Path("test_file.cs")
    test_content = """
using System;

namespace HelloWorldApp {
    class Greeter {
        private string message;

        public Greeter(string message) {
            this.message = message;
        }

        public void SayHello() {
            Console.WriteLine("Hello " + message);
        }
    }
}
"""
    test_file.write_text(test_content)

    try:
        blocks = parser.parse_file(test_file)
        assert len(blocks) >= 2
        tokens_flat = [tok for b in blocks for tok in b["tokens"]]
        assert "Greeter" in tokens_flat or "SayHello" in tokens_flat
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
    expected_extensions = {".py", ".js", ".jsx", ".cs", ".ts", ".tsx"}
    assert parser.supported_extensions == expected_extensions


def test_parser_handles_syntax_errors():
    parser = CodeParser()
    test_file = Path("test_syntax_error.py")
    test_content = """
def test_function(
    return x + y  # Missing closing parenthesis
"""

    test_file.write_text(test_content)

    try:
        blocks = parser.parse_file(test_file)
        assert isinstance(blocks, list)
    finally:
        test_file.unlink()

    test_file = Path("test_syntax_error.js")
    test_content = """
function testFunction( {  # Missing closing parenthesis
    return x + y;
"""

    test_file.write_text(test_content)

    try:
        blocks = parser.parse_file(test_file)
        assert isinstance(blocks, list)
    finally:
        test_file.unlink()

    test_file = Path("test_syntax_error.ts")
    test_file.write_text("function greet(: string) { return 1; }")  # Invalid TS
    try:
        blocks = parser.parse_file(test_file)
        assert isinstance(blocks, list)
    finally:
        test_file.unlink()

    test_file = Path("test_syntax_error.tsx")
    test_file.write_text("<div><Component></div>")  # Mismatched JSX
    try:
        blocks = parser.parse_file(test_file)
        assert isinstance(blocks, list)
    finally:
        test_file.unlink()

    test_file = Path("test_syntax_error.cs")
    test_file.write_text("public class MyClass { void Method( )")  # Missing brace
    try:
        blocks = parser.parse_file(test_file)
        assert isinstance(blocks, list)
    finally:
        test_file.unlink()


def test_parser_get_parser_caching():
    """Test that parser caching works correctly."""
    parser = CodeParser()

    parser1 = parser._get_parser("javascript")
    assert parser1 is not None

    parser2 = parser._get_parser("javascript")
    assert parser1 is parser2

    parser3 = parser._get_parser("python")
    assert parser3 is not parser1


def test_parser_tree_sitter_exception_handling():
    """Test that tree-sitter parsing handles exceptions gracefully."""
    parser = CodeParser()

    test_file = Path("test_tree_sitter_error.js")
    test_content = "invalid javascript code that will cause parsing errors"

    test_file.write_text(test_content)

    try:
        blocks = parser.parse_file(test_file)
        assert isinstance(blocks, list)
    finally:
        test_file.unlink()


def test_parser_query_exception_handling():
    """Test that query exceptions are handled gracefully."""
    parser = CodeParser()

    test_file = Path("test_query_error.js")
    test_content = """
function test() {
    return "hello";
}
"""

    test_file.write_text(test_content)

    try:
        blocks = parser.parse_file(test_file)
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
        assert isinstance(blocks, list)
    finally:
        test_file.unlink()


def test_parser_tokenize_tree_sitter_node_empty_content():
    """Test tokenization with empty or whitespace-only content."""
    parser = CodeParser()

    test_file = Path("test_empty.js")
    test_content = "   \n   \n"

    test_file.write_text(test_content)

    try:
        blocks = parser.parse_file(test_file)
        assert isinstance(blocks, list)
    finally:
        test_file.unlink()


def test_parser_tokenize_tree_sitter_node_with_strings_ts():
    parser = CodeParser()

    test_file = Path("test_strings.ts")
    test_content = """
function greet(name: string): string {
    const message = "Hello, " + name;
    return message;
}
"""
    test_file.write_text(test_content)

    try:
        blocks = parser.parse_file(test_file)
        assert isinstance(blocks, list)
        assert any("message" in block["tokens"] for block in blocks)
    finally:
        test_file.unlink()


def test_parser_tokenize_tree_sitter_node_with_strings_tsx():
    parser = CodeParser()

    test_file = Path("test_strings.tsx")
    test_content = """
import React from 'react';

function Greet({ name }: { name: string }) {
    return <div>Hello, {name}</div>;
}
"""
    test_file.write_text(test_content)

    try:
        blocks = parser.parse_file(test_file)
        assert isinstance(blocks, list)
        assert any("Greet" in block["tokens"] for block in blocks)
    finally:
        test_file.unlink()


def test_parser_tokenize_tree_sitter_node_with_strings_cs():
    parser = CodeParser()

    test_file = Path("test_strings.cs")
    test_content = """
public class Greeter {
    public string Greet(string name) {
        string message = "Hello, " + name;
        return message;
    }
}
"""
    test_file.write_text(test_content)

    try:
        blocks = parser.parse_file(test_file)
        assert isinstance(blocks, list)
        assert any("Greet" in block["tokens"] for block in blocks)
    finally:
        test_file.unlink()
