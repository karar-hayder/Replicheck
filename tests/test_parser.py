"""
Tests for the code parser functionality, including coverage for more branches.
"""

from pathlib import Path

from replicheck.parser import CodeParser


def test_parse_python_blocks_and_tokenize_python(tmp_path):
    parser = CodeParser()
    test_file = tmp_path / "test_file.py"
    test_content = """
def test_function(x, y):
    return x + y

class TestClass:
    def __init__(self):
        self.value = 0

def another_func():
    pass
    """
    test_file.write_text(test_content)
    blocks = parser.parse_file(test_file)
    # Should find 4 blocks: test_function, TestClass, __init__, another_func
    assert len(blocks) == 4
    # Check block types and tokens
    names = [b["tokens"][0] for b in blocks if b["tokens"]]
    assert "test_function" in names
    assert "TestClass" in names
    assert "another_func" in names
    # Check location keys
    for b in blocks:
        assert "file" in b["location"]
        assert "start_line" in b["location"]
        assert "end_line" in b["location"]


def test_parse_python_syntax_error_returns_empty(tmp_path):
    parser = CodeParser()
    test_file = tmp_path / "bad.py"
    test_file.write_text("def bad(:\n    pass")
    blocks = parser.parse_file(test_file)
    assert blocks == []


def test_parse_with_tree_sitter_consumes_run_query_pairs(monkeypatch):
    """
    _parse_with_tree_sitter builds blocks from the (node, capture_name) pairs
    that run_query returns, whatever shape the installed runtime produced.
    """
    parser = CodeParser()

    class DummyNode:
        def __init__(self):
            self.start_point = (0, 0)
            self.end_point = (1, 0)
            self.children = []
            self.type = "identifier"
            self.start_byte = 0
            self.end_byte = 4

    class DummyTree:
        @property
        def root_node(self):
            return DummyNode()

    class DummyParser:
        def parse(self, content):
            return DummyTree()

    monkeypatch.setattr(parser, "_get_parser", lambda lang: DummyParser())
    monkeypatch.setattr("replicheck.parser.get_language", lambda lang: object())
    monkeypatch.setattr(
        "replicheck.parser.run_query",
        lambda language, query_str, root: [(DummyNode(), "function")],
    )

    blocks = parser._parse_with_tree_sitter("abcd", Path("f.js"), "javascript")
    assert isinstance(blocks, list)
    assert blocks and blocks[0]["type"] == "function"


def test_run_query_normalises_dict_and_list_captures(monkeypatch):
    """
    run_query must return (node, capture_name) pairs whether the runtime hands
    back {capture_name: [nodes]} (tree-sitter >= 0.25) or a list of tuples.
    """
    from replicheck.parser import run_query

    node_a, node_b = object(), object()

    class FakeCursor:
        def __init__(self, query):
            pass

        def captures(self, root):
            return {"function": [node_a, node_b]}

    class FakeQuery:
        def __init__(self, language, query_str):
            pass

    import tree_sitter

    monkeypatch.setattr(tree_sitter, "Query", FakeQuery)
    monkeypatch.setattr(tree_sitter, "QueryCursor", FakeCursor)

    pairs = run_query(object(), "(function_declaration) @function", object())
    assert sorted(pairs, key=lambda p: id(p[0])) == sorted(
        [(node_a, "function"), (node_b, "function")], key=lambda p: id(p[0])
    )


def test_parse_with_tree_sitter_unsupported_language(monkeypatch, capsys):
    parser = CodeParser()
    monkeypatch.setattr(parser, "_get_parser", lambda lang: None)

    class DummyLanguage:
        def query(self, query_str):
            raise Exception("Should not be called")

    monkeypatch.setattr("replicheck.parser.get_language", lambda lang: DummyLanguage())
    blocks = parser._parse_with_tree_sitter("abcd", Path("f.unknown"), "unknownlang")
    assert blocks == []
    captured = capsys.readouterr()
    # The error message may include the exception string, so just check for the prefix
    assert (
        "Unsupported language" in captured.out
        or "Tree-sitter parse error" in captured.out
    )


def test_parse_with_tree_sitter_skips_capture_without_tokens(monkeypatch):
    """A capture whose node yields no tokens must not produce a block."""
    parser = CodeParser()

    class DummyNode:
        def __init__(self):
            self.start_point = (0, 0)
            self.end_point = (1, 0)
            self.children = []
            self.type = "identifier"
            self.start_byte = 0
            self.end_byte = 4

    class DummyTree:
        @property
        def root_node(self):
            return DummyNode()

    class DummyParser:
        def parse(self, content):
            return DummyTree()

    monkeypatch.setattr(parser, "_get_parser", lambda lang: DummyParser())
    monkeypatch.setattr("replicheck.parser.get_language", lambda lang: object())
    monkeypatch.setattr(
        "replicheck.parser.run_query", lambda language, query_str, root: []
    )

    assert parser._parse_with_tree_sitter("abcd", Path("f.js"), "javascript") == []


def test_parse_with_tree_sitter_exception(monkeypatch, capsys):
    parser = CodeParser()

    class DummyParser:
        def parse(self, content):
            raise RuntimeError("fail")

    monkeypatch.setattr(parser, "_get_parser", lambda lang: DummyParser())
    monkeypatch.setattr("replicheck.parser.get_language", lambda lang: None)
    blocks = parser._parse_with_tree_sitter("abcd", Path("f.js"), "javascript")
    assert blocks == []
    captured = capsys.readouterr()
    assert "Tree-sitter parse error" in captured.out


def test_tokenize_tree_sitter_node_variants():
    parser = CodeParser()

    # Node with identifier
    class Node:
        def __init__(self, type_, text, start_byte=0, end_byte=None, children=None):
            self.type = type_
            self.children = children or []
            self.start_byte = start_byte
            self.end_byte = end_byte if end_byte is not None else 0

    # Helper to set correct byte offsets for children
    def make_node(type_, text, children=None, offset=0):
        # Each node's start_byte is offset, end_byte is offset+len(text)
        node = Node(
            type_,
            text,
            start_byte=offset,
            end_byte=offset + len(text),
            children=children,
        )
        return node

    n1 = make_node("identifier", "foo")
    tokens = parser._tokenize_tree_sitter_node(n1, "foo")
    assert tokens == ["foo"]
    # Node with string
    n2 = make_node("string", "bar")
    tokens = parser._tokenize_tree_sitter_node(n2, "bar")
    assert tokens == ["bar"]
    # Node with number
    n3 = make_node("number", "123")
    tokens = parser._tokenize_tree_sitter_node(n3, "123")
    assert tokens == ["123"]
    # Node with children, ensure correct byte offsets for both
    child = make_node("identifier", "bar", offset=3)
    n4 = make_node("identifier", "foo", children=[child], offset=0)
    tokens = parser._tokenize_tree_sitter_node(n4, "foobar")
    # Should contain both "foo" and "bar" (order may vary, but both present)
    assert set(tokens) == {"foo", "bar"}


def test_tokenize_python_variants():
    parser = CodeParser()
    import ast

    node = ast.parse("def f():\n    x = 1\n    y = 'a'\n    return x")
    func_node = [n for n in ast.walk(node) if isinstance(n, ast.FunctionDef)][0]
    tokens = parser._tokenize_python(func_node)
    # Should include variable names and constants
    assert "x" in tokens
    assert "y" in tokens
    assert "1" in tokens
    assert "a" in tokens


def test_parse_file_unsupported_extension(tmp_path):
    parser = CodeParser()
    test_file = tmp_path / "test.unsupported"
    test_file.write_text("some content")
    blocks = parser.parse_file(test_file)
    assert blocks == []


def test_supported_extensions_property():
    parser = CodeParser()
    assert ".py" in parser.supported_extensions
    assert ".js" in parser.supported_extensions
    assert ".cs" in parser.supported_extensions


def test_get_parser_caching():
    parser = CodeParser()
    # Should cache per language
    p1 = parser._get_parser("javascript")
    p2 = parser._get_parser("javascript")
    assert p1 is p2
    p3 = parser._get_parser("typescript")
    assert p3 is not p1


def test_parse_file_all_supported(monkeypatch, tmp_path):
    parser = CodeParser()
    # Patch _parse_python and _parse_with_tree_sitter to check all branches
    called = {}

    def fake_parse_python(content, file_path):
        called["py"] = True
        return [
            {
                "location": {"file": str(file_path), "start_line": 1, "end_line": 2},
                "tokens": ["foo"],
            }
        ]

    def fake_parse_with_tree_sitter(content, file_path, lang):
        called[lang] = True
        return [
            {
                "location": {"file": str(file_path), "start_line": 1, "end_line": 2},
                "tokens": ["bar"],
            }
        ]

    parser._parse_python = fake_parse_python
    parser._parse_with_tree_sitter = fake_parse_with_tree_sitter
    for ext, _ in [
        (".py", "py"),
        (".js", "javascript"),
        (".jsx", "javascript"),
        (".ts", "typescript"),
        (".tsx", "tsx"),
        (".cs", "csharp"),
    ]:
        test_file = tmp_path / f"test{ext}"
        test_file.write_text("dummy")
        parser.parse_file(test_file)
    # All branches should be called
    assert called["py"]
    assert called["javascript"]
    assert called["typescript"]
    assert called["tsx"]
    assert called["csharp"]
