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


def test_analyze_cyclomatic_complexity_detects_high(tmp_path):
    code = """
def foo():
    if True:
        for i in range(10):
            if i % 2 == 0:
                print(i)
    else:
        print('no')
    for j in range(5):
        if j > 2:
            print(j)
    return 1
"""
    file = tmp_path / "complex.py"
    file.write_text(code)
    from replicheck.utils import analyze_cyclomatic_complexity

    results = analyze_cyclomatic_complexity(file, threshold=5)
    assert results, "Should detect at least one high-complexity function"
    assert results[0]["name"] == "foo"
    assert results[0]["complexity"] >= 5
    assert results[0]["file"] == str(file)
    assert results[0]["threshold"] == 5


def test_analyze_cyclomatic_complexity_none_found(tmp_path):
    code = """
def bar():
    return 1
"""
    file = tmp_path / "simple.py"
    file.write_text(code)
    from replicheck.utils import analyze_cyclomatic_complexity

    results = analyze_cyclomatic_complexity(file, threshold=5)
    assert results == [], "Should return empty list if no function exceeds threshold"


def test_find_large_files(tmp_path):
    code = """
def foo():
    pass
"""
    # Create a file with many tokens
    file = tmp_path / "large.py"
    file.write_text(
        "def foo():\n    x = 1\n" * 300
    )  # 300 lines, each with several tokens
    from replicheck.utils import find_large_files

    results = find_large_files([file], token_threshold=500)
    assert results, "Should detect the file as large"
    assert results[0]["file"] == str(file)
    assert results[0]["token_count"] >= 500
    assert results[0]["threshold"] == 500
    assert results[0]["top_n"] is None or isinstance(results[0]["top_n"], int)


def test_find_large_classes(tmp_path):
    code = """
class Big:
    def foo(self):
        x = 1
"""
    # Create a class with many tokens
    class_code = "class Big:\n    def foo(self):\n        x = 1\n" + (
        "    def bar(self):\n        y = 2\n" * 150
    )
    file = tmp_path / "bigclass.py"
    file.write_text(class_code)
    from replicheck.utils import find_large_classes

    results = find_large_classes(file, token_threshold=300)
    assert results, "Should detect the class as large"
    assert results[0]["name"] == "Big"
    assert results[0]["token_count"] >= 300
    assert results[0]["threshold"] == 300
    assert results[0]["top_n"] is None or isinstance(results[0]["top_n"], int)


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


def test_severity_ranking_complexity():
    from replicheck.utils import compute_severity

    assert compute_severity(10, 10) == "Low 🟢"
    assert compute_severity(15, 10) == "Medium 🟡"
    assert compute_severity(20, 10) == "High 🟠"
    assert compute_severity(30, 10) == "Critical 🔴"
    assert compute_severity(5, 10) == "None"


def test_analyze_cyclomatic_complexity_severity(tmp_path):
    code = """
def foo():
    if True:
        for i in range(10):
            if i % 2 == 0:
                print(i)
    else:
        print('no')
    for j in range(5):
        if j > 2:
            print(j)
    return 1
"""
    file = tmp_path / "complex.py"
    file.write_text(code)
    from replicheck.utils import analyze_cyclomatic_complexity

    results = analyze_cyclomatic_complexity(file, threshold=5)
    assert results
    assert results[0]["severity"] in {"Low 🟢", "Medium 🟡", "High 🟠", "Critical 🔴"}


def test_find_large_files_severity(tmp_path):
    file = tmp_path / "large.py"
    file.write_text("def foo():\n    x = 1\n" * 300)
    from replicheck.utils import find_large_files

    results = find_large_files([file], token_threshold=500)
    assert results
    assert results[0]["severity"] in {"Low 🟢", "Medium 🟡", "High 🟠", "Critical 🔴"}


def test_find_large_classes_severity(tmp_path):
    class_code = "class Big:\n    def foo(self):\n        x = 1\n" + (
        "    def bar(self):\n        y = 2\n" * 150
    )
    file = tmp_path / "bigclass.py"
    file.write_text(class_code)
    from replicheck.utils import find_large_classes

    results = find_large_classes(file, token_threshold=300)
    assert results
    assert results[0]["severity"] in {"Low 🟢", "Medium 🟡", "High 🟠", "Critical 🔴"}


def test_analyze_cyclomatic_complexity_exception_handling(tmp_path):
    """Test that analyze_cyclomatic_complexity handles exceptions gracefully."""
    from replicheck.utils import analyze_cyclomatic_complexity

    # Test with a file that doesn't exist
    non_existent_file = tmp_path / "nonexistent.py"
    results = analyze_cyclomatic_complexity(non_existent_file, threshold=5)
    assert results == []

    # Test with a file that has syntax errors
    syntax_error_file = tmp_path / "syntax_error.py"
    syntax_error_file.write_text(
        "def foo(\n    return 1  # Missing closing parenthesis"
    )

    results = analyze_cyclomatic_complexity(syntax_error_file, threshold=5)
    assert results == []


def test_find_large_files_exception_handling(tmp_path):
    """Test that find_large_files handles exceptions gracefully."""
    from replicheck.utils import find_large_files

    # Test with a file that doesn't exist
    non_existent_file = tmp_path / "nonexistent.py"
    results = find_large_files([non_existent_file], token_threshold=500)
    assert results == []

    # Test with a non-Python file
    non_python_file = tmp_path / "test.txt"
    non_python_file.write_text("This is not Python code")
    results = find_large_files([non_python_file], token_threshold=500)
    assert results == []

    # Test with a file that has syntax errors
    syntax_error_file = tmp_path / "syntax_error.py"
    syntax_error_file.write_text(
        "def foo(\n    return 1  # Missing closing parenthesis"
    )

    results = find_large_files([syntax_error_file], token_threshold=500)
    assert isinstance(results, list)


def test_find_large_classes_exception_handling(tmp_path):
    """Test that find_large_classes handles exceptions gracefully."""
    from replicheck.utils import find_large_classes

    # Test with a file that doesn't exist
    non_existent_file = tmp_path / "nonexistent.py"
    results = find_large_classes(non_existent_file, token_threshold=300)
    assert results == []

    # Test with a file that has syntax errors
    syntax_error_file = tmp_path / "syntax_error.py"
    syntax_error_file.write_text(
        "class Test(\n    def __init__(self):\n        pass  # Missing closing parenthesis"
    )

    results = find_large_classes(syntax_error_file, token_threshold=300)
    assert results == []


def test_find_todo_fixme_comments_exception_handling(tmp_path):
    """Test that find_todo_fixme_comments handles exceptions gracefully."""
    from replicheck.utils import find_todo_fixme_comments

    # Test with a file that doesn't exist
    non_existent_file = tmp_path / "nonexistent.py"
    results = find_todo_fixme_comments([non_existent_file])
    assert results == []

    # Test with a non-Python file
    non_python_file = tmp_path / "test.txt"
    non_python_file.write_text("# TODO: This won't be found")
    results = find_todo_fixme_comments([non_python_file])
    assert results == []

    # Test with a file that has encoding issues
    encoding_error_file = tmp_path / "encoding_error.py"
    # Create a file with invalid encoding
    with open(encoding_error_file, "wb") as f:
        f.write(b"# TODO: This has invalid encoding \xff\xfe")

    results = find_todo_fixme_comments([encoding_error_file])
    assert isinstance(results, list)


def test_compute_severity_edge_cases():
    """Test compute_severity with edge cases."""
    from replicheck.utils import compute_severity

    # Test with zero threshold
    assert compute_severity(0, 0) == "None"
    assert compute_severity(10, 0) == "None"

    # Test with negative values
    assert compute_severity(-5, 10) == "None"
    assert compute_severity(5, -10) == "None"

    # Test with very large ratios
    assert compute_severity(100, 1) == "Critical 🔴"
    assert compute_severity(50, 1) == "Critical 🔴"

    # Test exact threshold values
    assert compute_severity(10, 10) == "Low 🟢"
    assert compute_severity(15, 10) == "Medium 🟡"
    assert compute_severity(20, 10) == "High 🟠"
    assert compute_severity(30, 10) == "Critical 🔴"


def test_find_large_files_js(tmp_path):
    js_code = """
    function foo() { var x = 1; var y = 2; }
    class Bar { method() { return 42; } }
    // Add more tokens to exceed threshold
    """ + (
        "var a = 1;\n" * 100
    )
    file = tmp_path / "big.js"
    file.write_text(js_code)
    from replicheck.utils import find_large_files

    results = find_large_files([file], token_threshold=50)
    assert results, "Should detect the JS file as large"
    assert results[0]["file"].endswith("big.js")
    assert results[0]["token_count"] >= 50


def test_find_large_classes_js(tmp_path):
    # Add many methods inside the class to exceed the threshold
    methods = "\n".join([f"  method{i}() {{ var x = {i}; }}" for i in range(60)])
    js_code = f"""
    class BigClass {{
    {methods}
    }}
    """
    file = tmp_path / "bigclass.js"
    file.write_text(js_code)
    from replicheck.utils import find_large_classes

    results = find_large_classes(file, token_threshold=50)
    assert results, "Should detect the JS class as large"
    assert results[0]["name"] == "BigClass"
    assert results[0]["token_count"] >= 50


def test_analyze_js_cyclomatic_complexity(tmp_path):
    js_code = """
    function foo(x) { if (x) { return 1; } else { return 2; } }
    function bar() { for (var i=0;i<10;i++) { if (i%2) { continue; } } }
    """
    file = tmp_path / "complex.js"
    file.write_text(js_code)
    from replicheck.utils import analyze_js_cyclomatic_complexity

    results = analyze_js_cyclomatic_complexity(file, threshold=2)
    assert results, "Should detect at least one high-complexity function"
    assert any(r["name"] == "bar" or r["name"] == "foo" for r in results)
    assert all("complexity" in r for r in results)
    assert all("file" in r for r in results)
