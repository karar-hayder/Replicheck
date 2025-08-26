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


# --- analyze_cyclomatic_complexity coverage ---

# --- find_large_files coverage ---


def test_find_large_files(tmp_path):
    file = tmp_path / "large.py"
    file.write_text("def foo():\n    x = 1\n" * 300)
    from replicheck.utils import find_large_files

    results = find_large_files([file], token_threshold=500)
    assert results, "Should detect the file as large"
    assert results[0]["file"] == str(file)
    assert results[0]["token_count"] >= 500
    assert results[0]["threshold"] == 500
    assert results[0]["top_n"] is None or isinstance(results[0]["top_n"], int)


def test_find_large_files_empty(tmp_path):
    from replicheck.utils import find_large_files

    results = find_large_files([], token_threshold=10)
    assert results == []


def test_find_large_files_exception_handling(tmp_path):
    from replicheck.utils import find_large_files

    non_existent_file = tmp_path / "nonexistent.py"
    results = find_large_files([non_existent_file], token_threshold=500)
    assert results == []

    non_python_file = tmp_path / "test.txt"
    non_python_file.write_text("This is not Python code")
    results = find_large_files([non_python_file], token_threshold=500)
    assert results == []

    syntax_error_file = tmp_path / "syntax_error.py"
    syntax_error_file.write_text(
        "def foo(\n    return 1  # Missing closing parenthesis"
    )
    results = find_large_files([syntax_error_file], token_threshold=500)
    assert isinstance(results, list)


def test_find_large_files_encoding_error(tmp_path):
    from replicheck.utils import find_large_files

    file = tmp_path / "badenc.py"
    with open(file, "wb") as f:
        f.write(b"\xff\xfe")
    results = find_large_files([file], token_threshold=1)
    assert isinstance(results, list)


# --- find_large_classes coverage ---


def test_find_large_classes(tmp_path):
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


def test_find_large_classes_empty(tmp_path):
    from replicheck.utils import find_large_classes

    file = tmp_path / "empty.py"
    file.write_text("")
    results = find_large_classes(file, token_threshold=1)
    assert results == []


def test_find_large_classes_exception_handling(tmp_path):
    from replicheck.utils import find_large_classes

    non_existent_file = tmp_path / "nonexistent.py"
    results = find_large_classes(non_existent_file, token_threshold=300)
    assert results == []

    syntax_error_file = tmp_path / "syntax_error.py"
    syntax_error_file.write_text(
        "class Test(\n    def __init__(self):\n        pass  # Missing closing parenthesis"
    )
    results = find_large_classes(syntax_error_file, token_threshold=300)
    assert results == []


def test_find_large_classes_encoding_error(tmp_path):
    from replicheck.utils import find_large_classes

    file = tmp_path / "badenc.py"
    with open(file, "wb") as f:
        f.write(b"\xff\xfe")
    results = find_large_classes(file, token_threshold=1)
    assert isinstance(results, list)


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


# --- JS/TS/TSX/CS support ---


def test_find_large_files_js(tmp_path):
    js_code = """
    function foo() { var x = 1; var y = 2; }
    class Bar { method() { return 42; } }
    // Add more tokens to exceed threshold
    """ + (
        "var a = 1;\n" * 500
    )
    file = tmp_path / "big.js"
    file.write_text(js_code)
    from replicheck.utils import find_large_files

    results = find_large_files([file], token_threshold=50)
    assert results, "Should detect the JS file as large"
    assert results[0]["file"].endswith("big.js")
    assert results[0]["token_count"] >= 50


def test_find_large_classes_js(tmp_path):
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


def test_find_large_files_ts(tmp_path):
    ts_code = """
    function foo(): number { let x = 1; let y = 2; return x + y; }
    class Bar { method(): number { return 42; } }
    """ + (
        "let a: number = 1;\n" * 500
    )
    file = tmp_path / "big.ts"
    file.write_text(ts_code)
    from replicheck.utils import find_large_files

    results = find_large_files([file], token_threshold=50)
    assert results, "Should detect the TS file as large"
    assert results[0]["file"].endswith("big.ts")
    assert results[0]["token_count"] >= 50


def test_find_large_classes_ts(tmp_path):
    methods = "\n".join([f"  method{i}(): void {{ let x = {i}; }}" for i in range(60)])
    ts_code = f"""
    class BigClass {{
    {methods}
    }}
    """
    file = tmp_path / "bigclass.ts"
    file.write_text(ts_code)
    from replicheck.utils import find_large_classes

    results = find_large_classes(file, token_threshold=50)
    assert results, "Should detect the TS class as large"
    assert results[0]["name"] == "BigClass"
    assert results[0]["token_count"] >= 50


def test_find_large_files_tsx(tmp_path):
    tsx_code = """
    import React from 'react';
    const Component = ({ name }: { name: string }) => <div>Hello {name}</div>;
    """ + (
        "const x = <span>text</span>;\n" * 500
    )
    file = tmp_path / "big.tsx"
    file.write_text(tsx_code)
    from replicheck.utils import find_large_files

    results = find_large_files([file], token_threshold=50)
    assert results, "Should detect the TSX file as large"
    assert results[0]["file"].endswith("big.tsx")
    assert results[0]["token_count"] >= 50


def test_find_large_classes_tsx(tmp_path):
    methods = "\n".join(
        [f"  method{i}(): void {{ console.log({i}); }}" for i in range(60)]
    )
    tsx_code = f"""
    import React from 'react';

    class BigComponent extends React.Component {{
    {methods}
    render() {{
        return <div>Big Component</div>;
    }}
    }}
    """
    file = tmp_path / "bigcomponent.tsx"
    file.write_text(tsx_code)
    from replicheck.utils import find_large_classes

    results = find_large_classes(file, token_threshold=50)
    assert results, "Should detect the TSX class as large"
    assert results[0]["name"] == "BigComponent"
    assert results[0]["token_count"] >= 50


# --- C# support ---


def test_find_large_files_cs(tmp_path):
    cs_code = (
        """
using System;
namespace TestNamespace {
    class SmallClass { void SmallMethod() { int x = 1; } }

"""
        + ("    int a = 1;\n" * 100)
        + "}\n"
    )
    file = tmp_path / "big.cs"
    file.write_text(cs_code)
    from replicheck.utils import find_large_files

    results = find_large_files([file], token_threshold=50)
    assert results, "Should detect the C# file as large"
    assert results[0]["file"].endswith("big.cs")
    assert results[0]["token_count"] >= 50


def test_find_large_classes_cs(tmp_path):
    methods = "\n".join([f"  void Method{i}() {{ int x = {i}; }}" for i in range(60)])
    cs_code = f"""
    namespace TestNamespace {{
        class BigClass {{
        {methods}
        }}
    }}
    """
    file = tmp_path / "bigclass.cs"
    file.write_text(cs_code)
    from replicheck.utils import find_large_classes

    results = find_large_classes(file, token_threshold=50)
    assert results, "Should detect the C# class as large"
    assert results[0]["name"] == "BigClass"
    assert results[0]["token_count"] >= 50


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
