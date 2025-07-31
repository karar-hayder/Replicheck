import textwrap

from main import main


def test_main_with_invalid_path():
    """Test main function with invalid path."""
    result = main(path="/nonexistent/path")
    assert result == 1


def test_main_with_empty_directory(tmp_path):
    """Test main function with empty directory."""
    # Create and then delete the directory to ensure it's empty
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()

    result = main(
        path=str(tmp_path),
        min_similarity=0.8,
        min_size=50,
        output_format="text",
    )
    test_dir.rmdir()
    assert result == 0


def test_main_with_sample_code(tmp_path):
    """Test main function with sample code containing duplicates."""
    file1 = tmp_path / "file1.py"
    file2 = tmp_path / "file2.py"

    duplicate_code = """
def example_function():
    x = 1
    y = 2
    z = x + y
    return z
"""

    file1.write_text(duplicate_code)
    file2.write_text(duplicate_code)

    result = main(
        path=str(tmp_path),
        min_similarity=0.8,
        min_size=10,
        output_format="text",
    )
    assert result == 0


def test_analyze_unused_imports_vars_integration(tmp_path):
    # Simulate main.py's analyze_unused_imports_vars
    py_code = textwrap.dedent(
        """
        import math
        def bar():
            z = 42
            return 1
        """
    )
    py_file = tmp_path / "foo.py"
    py_file.write_text(py_code)
    from main import analyze_unused_imports_vars

    results = analyze_unused_imports_vars([py_file])
    assert any(r["code"] == "F401" for r in results)
    assert any(r["code"] == "F841" for r in results)
    assert all(str(py_file) in r["file"] for r in results)
