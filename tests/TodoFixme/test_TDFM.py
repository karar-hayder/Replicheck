import pytest

from replicheck.tools.TodoFixme.TDFM import TodoFixmeDetector


def make_file(tmp_path, name, content):
    file_path = tmp_path / name
    file_path.write_text(content, encoding="utf-8")
    return file_path


def test_find_todo_fixme_in_python_basic(tmp_path):
    content = """
# TODO: Refactor this function
# This is a placeholder line
#FIXME this is broken
# bug: something
# NOTE just a note
# HACK: workaround
# tbd
# to-do: dash
# to do: space
# optimize: speed
# review: check
# warning: be careful
# temp: temp code
# xxx: marker
# to_fix: underscore
# tofix: together
# fix_me: underscore
# fixme: lower
# TO DO: upper
# TO-DO: dash
# TOFIX: upper
# random comment
    """
    file_path = make_file(tmp_path, "a.py", content)
    detector = TodoFixmeDetector()
    detector.find_todo_fixme_comments([file_path])
    found_types = {r["type"] for r in detector.results}
    # Should find all the variants
    # Some variants will be normalized to their base (e.g., TO-DO -> TODO)
    # Accept at least the main ones
    assert "TODO" in found_types
    assert "FIXME" in found_types
    assert "BUG" in found_types
    assert "NOTE" in found_types
    assert "HACK" in found_types
    assert "TBD" in found_types
    assert "OPTIMIZE" in found_types
    assert "REVIEW" in found_types
    assert "WARNING" in found_types
    assert "TEMP" in found_types
    assert "XXX" in found_types
    assert "TOFIX" in found_types or "TO_FIX" in found_types

    # Check that the text is stripped
    for r in detector.results:
        assert isinstance(r["text"], str)
        assert r["text"] == r["text"].strip()

    # Check that file and line are present
    for r in detector.results:
        assert r["file"].endswith("a.py")
        assert isinstance(r["line"], int)
        assert r["line"] > 0


def test_find_todo_fixme_in_python_multifile(tmp_path):
    file1 = make_file(tmp_path, "a.py", "# TODO: one\n")
    file2 = make_file(tmp_path, "b.py", "# FIXME: two\n")
    detector = TodoFixmeDetector()
    detector.find_todo_fixme_comments([file1, file2])
    files = {r["file"] for r in detector.results}
    assert any("a.py" in f for f in files)
    assert any("b.py" in f for f in files)
    types = {r["type"] for r in detector.results}
    assert "TODO" in types
    assert "FIXME" in types


def test_find_todo_fixme_in_python_no_match(tmp_path):
    file_path = make_file(tmp_path, "c.py", "# just a comment\nprint('hi')\n")
    detector = TodoFixmeDetector()
    detector.find_todo_fixme_comments([file_path])
    assert detector.results == []


def test_find_todo_fixme_in_python_encoding(tmp_path):
    # Should not crash on utf-8
    file_path = make_file(tmp_path, "d.py", "# TODO: café\n")
    detector = TodoFixmeDetector()
    detector.find_todo_fixme_comments([file_path])
    assert any("TODO" == r["type"] for r in detector.results)


def test_find_todo_fixme_in_python_permission_error(tmp_path, monkeypatch):
    file_path = make_file(tmp_path, "e.py", "# TODO: secret\n")

    def raise_exc(*a, **k):
        raise PermissionError("nope")

    monkeypatch.setattr("builtins.open", raise_exc)
    detector = TodoFixmeDetector()
    # Should not raise
    detector.find_todo_fixme_comments([file_path])
    # Should be empty due to error
    assert detector.results == []


def test_find_todo_fixme_in_treesitter_skipped(monkeypatch, tmp_path):
    # If .js file, but tree-sitter not available, should not raise
    file_path = make_file(tmp_path, "a.js", "// TODO: js todo\n")
    # Patch get_parser to raise ImportError
    monkeypatch.setattr(
        "replicheck.tools.TodoFixme.TDFM.get_parser",
        lambda lang: (_ for _ in ()).throw(ImportError()),
    )
    detector = TodoFixmeDetector()
    # Should not raise, should skip
    try:
        detector.find_todo_fixme_comments([file_path])
    except Exception:
        pytest.fail("Should not raise even if tree-sitter is missing")


def test_find_todo_fixme_in_treesitter_basic(monkeypatch, tmp_path):
    # Simulate tree-sitter for .js file
    content = "// TODO: js todo\n// FIXME: fix this\n"
    file_path = make_file(tmp_path, "b.js", content)

    # Calculate the byte offsets for each comment in the content
    comment_lines = content.splitlines(keepends=True)
    offsets = []
    current = 0
    for line in comment_lines:
        offsets.append((current, current + len(line)))
        current += len(line)

    # Fake parser and language objects
    class FakeNode:
        def __init__(self, start_byte, end_byte, start_line):
            self.start_byte = start_byte
            self.end_byte = end_byte
            self.start_point = (start_line, 0)

    class FakeQuery:
        def __init__(self, text):
            self.text = text

        def captures(self, root):
            # Simulate two comments with correct byte offsets
            return [
                (FakeNode(offsets[0][0], offsets[0][1], 0), None),
                (FakeNode(offsets[1][0], offsets[1][1], 1), None),
            ]

    class FakeLanguage:
        def query(self, q):
            return FakeQuery(q)

    class FakeParser:
        def parse(self, b):
            class FakeTree:
                @property
                def root_node(self):
                    return None

            return FakeTree()

    monkeypatch.setattr(
        "replicheck.tools.TodoFixme.TDFM.get_parser", lambda lang: FakeParser()
    )
    monkeypatch.setattr(
        "replicheck.tools.TodoFixme.TDFM.get_language", lambda lang: FakeLanguage()
    )
    detector = TodoFixmeDetector()
    detector.find_todo_fixme_comments([file_path])
    types = {r["type"] for r in detector.results}
    assert "TODO" in types
    assert "FIXME" in types
    for r in detector.results:
        assert r["file"].endswith("b.js")
        assert isinstance(r["line"], int)
        assert r["line"] in (1, 2)


def test_find_todo_fixme_in_python_handles_empty_file(tmp_path):
    file_path = make_file(tmp_path, "empty.py", "")
    detector = TodoFixmeDetector()
    detector.find_todo_fixme_comments([file_path])
    assert detector.results == []


def test_find_todo_fixme_in_python_handles_non_py_file(tmp_path):
    file_path = make_file(tmp_path, "notpy.txt", "# TODO: not python\n")
    detector = TodoFixmeDetector()
    detector.find_todo_fixme_comments([file_path])
    # Should not find anything, as extension is not .py or supported
    assert detector.results == []
