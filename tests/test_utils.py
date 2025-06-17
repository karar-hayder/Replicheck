"""
Tests for the utils module.
"""

import tempfile
from pathlib import Path

from replicheck.utils import calculate_similarity, find_files, get_file_hash


def test_calculate_similarity_identical():
    tokens1 = ["def", "foo", "(", ")", ":"]
    tokens2 = ["def", "foo", "(", ")", ":"]
    assert calculate_similarity(tokens1, tokens2) == 1.0


def test_calculate_similarity_partial():
    tokens1 = ["def", "foo", "(", ")", ":"]
    tokens2 = ["def", "bar", "(", ")", ":"]
    # 4 out of 6 unique tokens overlap
    assert 0 < calculate_similarity(tokens1, tokens2) < 1.0


def test_calculate_similarity_empty():
    assert calculate_similarity([], []) == 0.0
    assert calculate_similarity(["a"], []) == 0.0
    assert calculate_similarity([], ["a"]) == 0.0


def test_get_file_hash(tmp_path):
    file1 = tmp_path / "a.txt"
    file2 = tmp_path / "b.txt"
    file1.write_text("hello world")
    file2.write_text("hello world")
    assert get_file_hash(file1) == get_file_hash(file2)
    file2.write_text("something else")
    assert get_file_hash(file1) != get_file_hash(file2)


def test_find_files_basic(tmp_path):
    # Create files
    (tmp_path / "a.py").write_text("print('a')")
    (tmp_path / "b.js").write_text("console.log('b')")
    (tmp_path / "c.txt").write_text("not code")
    files = find_files(tmp_path, extensions={".py", ".js"})
    found = {f.name for f in files}
    assert "a.py" in found
    assert "b.js" in found
    assert "c.txt" not in found


def test_find_files_ignore_dirs(tmp_path):
    # Create ignored dir and file inside
    ignored = tmp_path / "venv"
    ignored.mkdir()
    (ignored / "d.py").write_text("print('ignore me')")
    (tmp_path / "e.py").write_text("print('keep me')")
    files = find_files(tmp_path, extensions={".py"}, ignore_dirs=["venv"])
    found = {f.name for f in files}
    assert "e.py" in found
    assert "d.py" not in found
