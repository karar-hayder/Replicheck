"""
Tests for the utils module.
"""

from replicheck.utils import find_files, get_file_hash

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


def test_get_file_hash_permission_error(tmp_path, monkeypatch):
    # Simulate a permission error when opening the file
    from replicheck.utils import get_file_hash

    file = tmp_path / "perm.txt"
    file.write_text("data")

    def raise_exc(*a, **k):
        raise PermissionError("nope")

    monkeypatch.setattr("builtins.open", raise_exc)
    assert get_file_hash(file) is None


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


def test__get_ignored_dirs_and__is_in_ignored_dirs():
    from pathlib import Path

    from replicheck.utils import _get_ignored_dirs, _is_in_ignored_dirs

    # Default venv dirs
    ignored = _get_ignored_dirs()
    assert ".venv" in ignored and "venv" in ignored
    # Add custom
    ignored2 = _get_ignored_dirs(["foo", "bar"])
    assert "foo" in ignored2 and "bar" in ignored2

    # _is_in_ignored_dirs
    p1 = Path("foo/bar/baz.py")
    p2 = Path("src/main.py")
    assert _is_in_ignored_dirs(p1, {"foo"})
    assert not _is_in_ignored_dirs(p2, {"foo"})


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


def test_compute_severity_zero_and_negative_threshold():
    from replicheck.utils import compute_severity

    # threshold equal 0
    assert compute_severity(10, 0) == "None"
    # value less than 0
    assert compute_severity(-1, 10) == "None"
    # threshold more than 0
    assert compute_severity(10, -1) == "None"


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
