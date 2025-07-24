"""
Extra tests for the parser module to improve coverage.
"""

from pathlib import Path

import pytest

from replicheck.parser import CodeParser


def test_parse_python_function(tmp_path):
    code = """
def foo(x, y):
    return x + y
"""
    file = tmp_path / "a.py"
    file.write_text(code)
    parser = CodeParser()
    blocks = parser.parse_file(file)
    assert len(blocks) == 1
    assert blocks[0]["location"]["file"] == str(file)
    assert blocks[0]["tokens"][0] == "foo"
    assert "x" in blocks[0]["tokens"]
    assert "y" in blocks[0]["tokens"]


def test_parse_python_class(tmp_path):
    code = """
class Bar:
    def method(self):
        pass
"""
    file = tmp_path / "b.py"
    file.write_text(code)
    parser = CodeParser()
    blocks = parser.parse_file(file)
    names = {block["tokens"][0] for block in blocks}
    assert "Bar" in names
    assert "method" in names


def test_parse_unsupported_extension(tmp_path):
    file = tmp_path / "a.txt"
    file.write_text("not code")
    parser = CodeParser()
    blocks = parser.parse_file(file)
    assert blocks == []


def test_parse_python_syntax_error(tmp_path):
    file = tmp_path / "bad.py"
    file.write_text("def broken(:\n    pass")
    parser = CodeParser()
    blocks = parser.parse_file(file)
    assert blocks == []


def test_parse_empty_file(tmp_path):
    file = tmp_path / "empty.py"
    file.write_text("")
    parser = CodeParser()
    blocks = parser.parse_file(file)
    assert blocks == []


def test_parse_python_only_comments(tmp_path):
    file = tmp_path / "comments.py"
    file.write_text("""# just a comment\n# another comment\n""")
    parser = CodeParser()
    blocks = parser.parse_file(file)
    assert blocks == []


def test_parse_javascript_placeholder(tmp_path):
    file = tmp_path / "a.js"
    file.write_text("function foo() { return 1; }")
    parser = CodeParser()
    blocks = parser.parse_file(file)
    assert len(blocks) >= 1
    assert blocks[0]["location"]["file"] == str(file)
    assert "foo" in blocks[0]["tokens"]
