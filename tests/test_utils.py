"""
Tests for the utils module.
"""

import textwrap

from replicheck.utils import calculate_similarity, find_files, get_file_hash

# --- calculate_similarity coverage ---


def test_calculate_similarity_identical():
    tokens1 = ["def", "foo", "(", ")", ":"]
    tokens2 = ["def", "foo", "(", ")", ":"]
    assert calculate_similarity(tokens1, tokens2) == 1.0


def test_calculate_similarity_partial():
    tokens1 = ["def", "foo", "(", ")", ":"]
    tokens2 = ["def", "bar", "(", ")", ":"]
    sim = calculate_similarity(tokens1, tokens2)
    assert 0 < sim < 1.0


def test_calculate_similarity_empty():
    assert calculate_similarity([], []) == 0.0
    assert calculate_similarity(["a"], []) == 0.0
    assert calculate_similarity([], ["a"]) == 0.0


def test_calculate_similarity_type_errors():
    # Should handle non-list input gracefully (should not raise)
    assert calculate_similarity("abc", "abc") == 0.0
    assert calculate_similarity(None, None) == 0.0
    assert calculate_similarity(["a"], None) == 0.0
    assert calculate_similarity(None, ["a"]) == 0.0


# --- get_file_hash coverage ---


def test_get_file_hash(tmp_path):
    file1 = tmp_path / "a.txt"
    file2 = tmp_path / "b.txt"
    file1.write_text("hello world")
    file2.write_text("hello world")
    assert get_file_hash(file1) == get_file_hash(file2)
    file2.write_text("something else")
    assert get_file_hash(file1) != get_file_hash(file2)


def test_get_file_hash_nonexistent(tmp_path):
    # Should not raise, should return None
    from replicheck.utils import get_file_hash

    file = tmp_path / "doesnotexist.txt"
    result = get_file_hash(file)
    assert result is None


def test_get_file_hash_binary(tmp_path):
    file = tmp_path / "binfile.bin"
    file.write_bytes(b"\x00\x01\x02\x03")
    result = get_file_hash(file)
    assert isinstance(result, str) or result is None


# --- find_files coverage ---


def test_find_files_basic(tmp_path):
    (tmp_path / "a.py").write_text("print('a')")
    (tmp_path / "b.js").write_text("console.log('b')")
    (tmp_path / "c.txt").write_text("not code")
    files = find_files(tmp_path, extensions={".py", ".js"})
    found = {f.name for f in files}
    assert "a.py" in found
    assert "b.js" in found
    assert "c.txt" not in found


def test_find_files_ignore_dirs(tmp_path):
    ignored = tmp_path / "venv"
    ignored.mkdir()
    (ignored / "d.py").write_text("print('ignore me')")
    (tmp_path / "e.py").write_text("print('keep me')")
    files = find_files(tmp_path, extensions={".py"}, ignore_dirs=["venv"])
    found = {f.name for f in files}
    assert "e.py" in found
    assert "d.py" not in found


def test_find_files_empty(tmp_path):
    files = find_files(tmp_path, extensions={".py"})
    assert files == []


def test_find_files_no_extensions(tmp_path):
    (tmp_path / "a.py").write_text("print('a')")
    files = find_files(tmp_path, extensions=None)
    assert any(f.name == "a.py" for f in files)


# --- find_todo_fixme_comments coverage ---


def test_find_todo_fixme_comments(tmp_path):
    code = """
# TODO: Refactor this function
# FIXME this is broken
# just a comment
# todo lowercase
# fixme: also lowercase
    """
    file = tmp_path / "todo.py"
    file.write_text(code)
    from replicheck.utils import find_todo_fixme_comments

    results = find_todo_fixme_comments([file])
    assert len(results) == 4
    types = {r["type"] for r in results}
    assert "TODO" in types and "FIXME" in types
    texts = [r["text"] for r in results]
    assert any("Refactor" in t for t in texts)
    assert any("broken" in t for t in texts)


def test_find_todo_fixme_comments_exception_handling(tmp_path):
    from replicheck.utils import find_todo_fixme_comments

    non_existent_file = tmp_path / "nonexistent.py"
    results = find_todo_fixme_comments([non_existent_file])
    assert results == []

    non_python_file = tmp_path / "test.txt"
    non_python_file.write_text("# TODO: This won't be found")
    results = find_todo_fixme_comments([non_python_file])
    assert results == []

    encoding_error_file = tmp_path / "encoding_error.py"
    with open(encoding_error_file, "wb") as f:
        f.write(b"# TODO: This has invalid encoding \xff\xfe")
    results = find_todo_fixme_comments([encoding_error_file])
    assert isinstance(results, list)


def test_find_todo_fixme_comments_variants(tmp_path):
    from replicheck.utils import find_todo_fixme_comments

    code = "# ToDo: mixed case\n# FixMe: mixed case\n# TODO\n# FIXME\n"
    file = tmp_path / "variants.py"
    file.write_text(code)
    results = find_todo_fixme_comments([file])
    assert len(results) == 4


# --- compute_severity coverage ---


def test_severity_ranking_complexity():
    from replicheck.utils import compute_severity

    assert compute_severity(10, 10) == "Low 🟢"
    assert compute_severity(15, 10) == "Medium 🟡"
    assert compute_severity(20, 10) == "High 🟠"
    assert compute_severity(30, 10) == "Critical 🔴"
    assert compute_severity(5, 10) == "None"


def test_compute_severity_edge_cases():
    from replicheck.utils import compute_severity

    assert compute_severity(0, 0) == "None"
    assert compute_severity(10, 0) == "None"
    assert compute_severity(-5, 10) == "None"
    assert compute_severity(5, -10) == "None"
    assert compute_severity(100, 1) == "Critical 🔴"
    assert compute_severity(50, 1) == "Critical 🔴"
    assert compute_severity(10, 10) == "Low 🟢"
    assert compute_severity(15, 10) == "Medium 🟡"
    assert compute_severity(20, 10) == "High 🟠"
    assert compute_severity(30, 10) == "Critical 🔴"


def test_compute_severity_types():
    from replicheck.utils import compute_severity

    # Should not raise, should return "None" for invalid types
    assert compute_severity("20", "10") == "None"
    assert compute_severity(None, 10) == "None"
    assert compute_severity(20, None) == "None"
    assert compute_severity("abc", 10) == "None"
    assert compute_severity(10, "xyz") == "None"


# --- severity in results ---


def test_find_large_files_severity(tmp_path):
    from replicheck.tools.LargeDetection.LF import LargeFileDetector

    file = tmp_path / "large.py"
    file.write_text("def foo():\n    x = 1\n" * 300)

    detector = LargeFileDetector()
    detector.find_large_files([file], token_threshold=500)
    results = detector.results
    assert results
    assert results[0]["severity"] in {"Low 🟢", "Medium 🟡", "High 🟠", "Critical 🔴"}


def test_find_large_classes_severity(tmp_path):
    from replicheck.tools.LargeDetection.LC import LargeClassDetector

    class_code = "class Big:\n    def foo(self):\n        x = 1\n" + (
        "    def bar(self):\n        y = 2\n" * 150
    )
    file = tmp_path / "bigclass.py"
    file.write_text(class_code)

    detector = LargeClassDetector()
    detector.find_large_classes([file], token_threshold=300)
    results = detector.results
    assert results
    assert results[0]["severity"] in {"Low 🟢", "Medium 🟡", "High 🟠", "Critical 🔴"}


# --- flake8 unused ---


def test_find_flake8_unused_imports(tmp_path):
    py_code = textwrap.dedent(
        """
        import os
        import sys

        def foo():
            x = 1
            y = 2  # unused
            return x
        """
    )
    py_file = tmp_path / "test_unused.py"
    py_file.write_text(py_code)
    from replicheck.utils import find_flake8_unused

    results = find_flake8_unused([py_file])
    messages = [r["message"] for r in results]
    assert any(r["code"] == "F401" for r in results), "Should detect unused import"
    assert any(r["code"] == "F841" for r in results), "Should detect unused variable"
    assert any("imported but unused" in m for m in messages)
    assert any("assigned to but never used" in m for m in messages)
    assert all(str(py_file) in r["file"] for r in results)


def test_find_flake8_unused_empty(tmp_path):
    from replicheck.utils import find_flake8_unused

    py_file = tmp_path / "empty.py"
    py_file.write_text("")
    results = find_flake8_unused([py_file])
    assert results == []


def test_find_flake8_unused_nonexistent(tmp_path):
    from replicheck.utils import find_flake8_unused

    py_file = tmp_path / "doesnotexist.py"
    results = find_flake8_unused([py_file])
    assert results == []


def test_find_flake8_unused_encoding_error(tmp_path):
    from replicheck.utils import find_flake8_unused

    py_file = tmp_path / "badenc.py"
    with open(py_file, "wb") as f:
        f.write(b"\xff\xfe")
    results = find_flake8_unused([py_file])
    assert isinstance(results, list)
