import pytest

from replicheck.tools.LargeDetection.LC import LargeClassDetector


def create_file(tmp_path, name, content):
    file_path = tmp_path / name
    file_path.write_text(content)
    return file_path


@pytest.mark.parametrize(
    "code,threshold,expected_count",
    [
        # One large class, threshold 10, should be detected
        (
            "class Foo:\n" + "\n".join(f"    a{i} = {i}" for i in range(15)),
            10,
            1,
        ),
        # No class exceeds threshold
        (
            "class Bar:\n    x = 1\n    y = 2\n",
            10,
            0,
        ),
        # Multiple large classes
        (
            "class A:\n"
            + "\n".join(f"    a{i} = {i}" for i in range(12))
            + "\nclass B:\n"
            + "\n".join(f"    b{i} = {i}" for i in range(13)),
            10,
            2,
        ),
    ],
)
def test_find_large_python_classes(tmp_path, code, threshold, expected_count):
    file = create_file(tmp_path, "foo.py", code)
    detector = LargeClassDetector()
    results = detector._find_large_python_classes(file, threshold)
    assert isinstance(results, list)
    assert len(results) == expected_count
    for r in results:
        assert r["token_count"] >= threshold
        assert r["file"].endswith("foo.py")
        assert "name" in r
        assert "severity" in r


def test_find_large_python_classes_handles_syntax_error(tmp_path):
    file = create_file(tmp_path, "bad.py", "class X: this is not valid python")
    detector = LargeClassDetector()
    # Should not raise, should return []
    results = detector._find_large_python_classes(file, 1)
    assert results == []


def test_find_large_js_classes(tmp_path):
    # Minimal JS class with enough tokens
    js_code = "class Foo { constructor() { this.x = 1; this.y = 2; this.z = 3; } }"
    file = create_file(tmp_path, "foo.js", js_code)
    detector = LargeClassDetector()
    # Should not raise, may return [] if tree-sitter not available
    results = detector._find_large_js_classes(file, "js", 3)
    assert isinstance(results, list)


def test_find_large_js_classes_handles_error(tmp_path):
    file = create_file(tmp_path, "bad.js", "class {")
    detector = LargeClassDetector()
    results = detector._find_large_js_classes(file, "js", 1)
    assert isinstance(results, list)


def test_find_large_cs_classes(tmp_path):
    cs_code = "public class Foo { public int X = 1; public int Y = 2; }"
    file = create_file(tmp_path, "foo.cs", cs_code)
    detector = LargeClassDetector()
    results = detector._find_large_cs_classes(file, 2)
    assert isinstance(results, list)


def test_find_large_cs_classes_handles_error(tmp_path):
    file = create_file(tmp_path, "bad.cs", "public class {")
    detector = LargeClassDetector()
    results = detector._find_large_cs_classes(file, 1)
    assert isinstance(results, list)


def test_find_large_classes_top_n(tmp_path):
    code1 = "class A:\n" + "\n".join(f"    a{i} = {i}" for i in range(20))
    code2 = "class B:\n" + "\n".join(f"    b{i} = {i}" for i in range(15))
    file1 = create_file(tmp_path, "a.py", code1)
    file2 = create_file(tmp_path, "b.py", code2)
    detector = LargeClassDetector()
    detector.find_large_classes([file1, file2], token_threshold=10, top_n=1)
    results = detector.results
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]["name"] == "A"


def test_find_large_classes_mixed_types(tmp_path):
    py_code = "class Py:\n" + "\n".join(f"    x{i} = {i}" for i in range(12))
    js_code = "class Js { constructor() { this.x = 1; this.y = 2; this.z = 3; } }"
    cs_code = "public class Cs { public int X = 1; public int Y = 2; }"
    py_file = create_file(tmp_path, "foo.py", py_code)
    js_file = create_file(tmp_path, "foo.js", js_code)
    cs_file = create_file(tmp_path, "foo.cs", cs_code)
    detector = LargeClassDetector()
    detector.find_large_classes([py_file, js_file, cs_file], token_threshold=3)
    results = detector.results
    assert isinstance(results, list)
    # At least the Python class should be detected
    assert any(r.get("name") == "Py" for r in results)


def test_find_large_classes_empty(tmp_path):
    file = create_file(tmp_path, "empty.py", "")
    detector = LargeClassDetector()
    detector.find_large_classes([file], token_threshold=1)
    assert detector.results == []


def test_find_large_classes_nonexistent_file(tmp_path):
    file = tmp_path / "doesnotexist.py"
    detector = LargeClassDetector()
    # Should not raise
    detector.find_large_classes([file], token_threshold=1)
    assert isinstance(detector.results, list)
