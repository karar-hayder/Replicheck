import pytest

from main import main
from replicheck.runner import ReplicheckRunner
from replicheck.tools.LargeDetection.LC import LargeClassDetector
from replicheck.tools.LargeDetection.LF import LargeFileDetector
from replicheck.utils import (
    calculate_similarity,
    compute_severity,
    find_files,
    find_flake8_unused,
    find_todo_fixme_comments,
    get_file_hash,
)

# --- Cyclomatic Complexity Analyzer from CCA.py ---
try:
    from replicheck.tools.CyclomaticComplexity.CCA import CyclomaticComplexityAnalyzer
except ImportError:
    CyclomaticComplexityAnalyzer = None


def create_py_file(tmp_path, name, content):
    file_path = tmp_path / name
    file_path.write_text(content)
    return file_path


def test_runner_with_invalid_path(tmp_path):
    runner = ReplicheckRunner(
        path=tmp_path / "does_not_exist",
        min_similarity=0.8,
        min_size=10,
        output_format="text",
        complexity_threshold=10,
        large_file_threshold=500,
        large_class_threshold=300,
        top_n_large=10,
        extensions=None,
        ignore_dirs=[],
        output_file=None,
    )
    assert runner.run() == 1


def test_runner_with_empty_dir(tmp_path):
    runner = ReplicheckRunner(
        path=tmp_path,
        min_similarity=0.8,
        min_size=10,
        output_format="text",
        complexity_threshold=10,
        large_file_threshold=500,
        large_class_threshold=300,
        top_n_large=10,
        extensions=None,
        ignore_dirs=[],
        output_file=None,
    )
    assert runner.run() == 0


def test_runner_detects_duplicate(tmp_path):
    code = "def foo():\n    return 42\n"
    create_py_file(tmp_path, "a.py", code)
    create_py_file(tmp_path, "b.py", code)
    runner = ReplicheckRunner(
        path=tmp_path,
        min_similarity=0.8,
        min_size=5,
        output_format="text",
        complexity_threshold=10,
        large_file_threshold=500,
        large_class_threshold=300,
        top_n_large=10,
        extensions=None,
        ignore_dirs=[],
        output_file=None,
    )
    assert runner.run() == 0


def test_utils_calculate_similarity():
    assert calculate_similarity(["a", "b", "c"], ["a", "b", "d"]) == 2 / 4
    assert calculate_similarity([], []) == 0.0
    assert calculate_similarity("abc", ["a", "b"]) == 0.0


def test_utils_get_file_hash(tmp_path):
    file = create_py_file(tmp_path, "hashme.py", "print(1)")
    h = get_file_hash(file)
    assert isinstance(h, str) and len(h) == 64
    assert get_file_hash(tmp_path / "nope.py") is None


def test_utils_find_files(tmp_path):
    py = create_py_file(tmp_path, "x.py", "print(1)")
    js = create_py_file(tmp_path, "y.js", "console.log(1);")
    files = find_files(tmp_path, extensions={".py", ".js"})
    assert py in files and js in files


def test_utils_compute_severity():
    assert compute_severity(30, 10).startswith("Critical")
    assert compute_severity(20, 10).startswith("High")
    assert compute_severity(15, 10).startswith("Medium")
    assert compute_severity(10, 10).startswith("Low")
    assert compute_severity(5, 10) == "None"
    assert compute_severity("bad", 10) == "None"


def test_utils_analyze_cyclomatic_complexity_all_types_with_cca(tmp_path):
    py_code = (
        "def foo():\n    if True:\n        return 1\n    else:\n        return 2\n"
    )
    js_code = "function foo() { if (true) { return 1; } else { return 2; } }"
    cs_code = (
        "public class X { public int Foo() { if (true) return 1; else return 2; } }"
    )

    py_file = create_py_file(tmp_path, "cc.py", py_code)
    js_file = create_py_file(tmp_path, "cc.js", js_code)
    cs_file = create_py_file(tmp_path, "cc.cs", cs_code)

    files = [py_file, js_file, cs_file]
    analyzer = CyclomaticComplexityAnalyzer(files, threshold=1)
    analyzer.analyze()
    results = analyzer.results

    # Should have at least one result per file type if analyzers are present
    assert any(r["file"].endswith("cc.py") for r in results)
    assert any(r["file"].endswith("cc.js") for r in results)
    assert any(r["file"].endswith("cc.cs") for r in results)


def test_utils_find_large_files(tmp_path):
    code = "a = 1\n" * 600
    file = create_py_file(tmp_path, "big.py", code)
    detector = LargeFileDetector()
    detector.find_large_files([file], token_threshold=500)
    results = detector.results

    # Handle results: should be a list of dicts with at least 'file' and 'tokens'
    assert isinstance(results, list)
    assert results and isinstance(results[0], dict)
    assert results[0].get("file", "").endswith("big.py")
    assert results[0].get("token_count", 0) >= 500


def test_utils_find_large_classes(tmp_path):
    code = "class Big:\n" + "\n".join(f"    a{i} = {i}" for i in range(400))
    file = create_py_file(tmp_path, "bigclass.py", code)
    detector = LargeClassDetector()
    detector.find_large_classes([file], token_threshold=300)
    results = detector.results
    # Handle results: should be a list of dicts with at least 'name' and 'tokens'
    assert isinstance(results, list)
    assert results and isinstance(results[0], dict)
    assert results[0].get("name") == "Big"
    assert results[0].get("token_count", 0) >= 300


def test_utils_find_todo_fixme_comments(tmp_path):
    code = "# TODO: fix this\n# FIXME something else"
    file = create_py_file(tmp_path, "todo.py", code)
    results = find_todo_fixme_comments([file])
    assert any(r["type"] == "TODO" for r in results)
    assert any(r["type"] == "FIXME" for r in results)


def test_utils_find_flake8_unused(tmp_path):
    code = "import os\n"
    file = create_py_file(tmp_path, "unused.py", code)
    results = find_flake8_unused([file])
    assert isinstance(results, list)


def test_main_function(tmp_path):
    code = "def foo():\n    return 1\n"
    create_py_file(tmp_path, "main.py", code)
    result = main(
        path=str(tmp_path),
        min_similarity=0.8,
        min_size=5,
        output_format="text",
        complexity_threshold=10,
        large_file_threshold=500,
        large_class_threshold=300,
        top_n_large=10,
        extensions=None,
        ignore_dirs=[],
        output_file=None,
    )
    assert result == 0


# ---- Additional tests for runner.py coverage ----


def test_runner_extensions_and_ignore_dirs(tmp_path):
    # Test extensions argument and ignore_dirs filtering
    create_py_file(tmp_path, "x.py", "print(1)")
    create_py_file(tmp_path, "y.js", "console.log(1);")
    subdir = tmp_path / "ignoreme"
    subdir.mkdir()
    create_py_file(subdir, "z.py", "print(2)")
    runner = ReplicheckRunner(
        path=tmp_path,
        min_similarity=0.8,
        min_size=5,
        output_format="text",
        complexity_threshold=10,
        large_file_threshold=500,
        large_class_threshold=300,
        top_n_large=10,
        extensions=["py", "js"],
        ignore_dirs=[str(subdir)],
        output_file=None,
    )
    # Should not error, and should not include ignored file
    assert runner.run() == 0


def test_runner_parse_code_files_handles_exception(tmp_path, monkeypatch):
    # Simulate parser.parse_file raising
    class DummyParser:
        def parse_file(self, file):
            raise ValueError("fail")

    runner = ReplicheckRunner(
        path=tmp_path,
        min_similarity=0.8,
        min_size=5,
        output_format="text",
        complexity_threshold=10,
        large_file_threshold=500,
        large_class_threshold=300,
        top_n_large=10,
        extensions=None,
        ignore_dirs=[],
        output_file=None,
    )
    # Should not raise, should print and return empty
    assert runner.parse_code_files([tmp_path / "nofile.py"], DummyParser()) == []


def test_runner_analyze_unused_imports_vars_filters(tmp_path):
    py = create_py_file(tmp_path, "x.py", "import os\n")
    js = create_py_file(tmp_path, "x.js", "console.log(1);")
    runner = ReplicheckRunner(
        path=tmp_path,
        min_similarity=0.8,
        min_size=5,
        output_format="text",
        complexity_threshold=10,
        large_file_threshold=500,
        large_class_threshold=300,
        top_n_large=10,
        extensions=None,
        ignore_dirs=[],
        output_file=None,
    )
    # Should only analyze .py for unused imports/vars
    results = runner.analyze_unused_imports_vars([py, js])
    assert isinstance(results, list)


def test_runner_analyze_bugs_and_safety_none(monkeypatch, tmp_path):
    # Simulate BugNSafetyAnalyzer is None
    import replicheck.runner as runner_mod

    monkeypatch.setattr(runner_mod, "BugNSafetyAnalyzer", None)
    runner = ReplicheckRunner(
        path=tmp_path,
        min_similarity=0.8,
        min_size=5,
        output_format="text",
        complexity_threshold=10,
        large_file_threshold=500,
        large_class_threshold=300,
        top_n_large=10,
        extensions=None,
        ignore_dirs=[],
        output_file=None,
    )
    assert runner.analyze_bugs_and_safety([tmp_path / "x.py"]) == []


def test_runner_analyze_bugs_and_safety_available(tmp_path):
    # Simulate BugNSafetyAnalyzer present and returns dummy results
    class DummyBNS:
        def __init__(self, files, ignore_dirs=None):
            self.files = files
            self.ignore_dirs = ignore_dirs
            self.results = []

        def analyze(self):
            self.results = [
                {"file": str(self.files[0]), "code": "B999", "message": "dummy"}
            ]

    import replicheck.runner as runner_mod

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(runner_mod, "BugNSafetyAnalyzer", DummyBNS)
    runner = runner_mod.ReplicheckRunner(
        path=tmp_path,
        min_similarity=0.8,
        min_size=5,
        output_format="text",
        complexity_threshold=10,
        large_file_threshold=500,
        large_class_threshold=300,
        top_n_large=10,
        extensions=None,
        ignore_dirs=[],
        output_file=None,
    )
    file = create_py_file(tmp_path, "bns.py", "def foo(x=[]): pass\n")
    results = runner.analyze_bugs_and_safety([file])
    assert results and results[0]["code"] == "B999"
    monkeypatch.undo()


def test_runner_large_files_and_classes_top_n(tmp_path):
    # Test top_n_large truncation
    files = []
    for i in range(5):
        code = "a = 1\n" * (600 + i)
        files.append(create_py_file(tmp_path, f"big{i}.py", code))
    detector = LargeFileDetector()
    detector.find_large_files(files, token_threshold=500, top_n=2)
    large_files = detector.results
    # Handle results: should be a list of dicts, sorted by tokens descending, length 2
    assert isinstance(large_files, list)
    assert len(large_files) == 2
    assert all(isinstance(f, dict) for f in large_files)
    assert large_files[0]["token_count"] >= large_files[1]["token_count"]
    # For classes
    class_code = "class Big:\n" + "\n".join(f"    a{i} = {i}" for i in range(400))
    class_files = [
        create_py_file(tmp_path, f"bigclass{i}.py", class_code) for i in range(5)
    ]
    class_detector = LargeClassDetector()
    class_detector.find_large_classes(class_files, token_threshold=300, top_n=2)
    large_classes = detector.results
    # Handle results: should be a list of dicts, sorted by tokens descending, length 2
    assert isinstance(large_classes, list)
    assert len(large_classes) == 2
    assert all(isinstance(c, dict) for c in large_classes)
    assert large_classes[0]["token_count"] >= large_classes[1]["token_count"]


def test_runner_analyze_complexity_all_types(tmp_path):
    py = create_py_file(
        tmp_path, "x.py", "def foo():\n    if True:\n        return 1\n"
    )
    js = create_py_file(tmp_path, "x.js", "function foo() { if (true) { return 1; } }")
    cs = create_py_file(
        tmp_path, "x.cs", "public class X { public int Foo() { if (true) return 1; } }"
    )
    runner = ReplicheckRunner(
        path=tmp_path,
        min_similarity=0.8,
        min_size=5,
        output_format="text",
        complexity_threshold=1,
        large_file_threshold=500,
        large_class_threshold=300,
        top_n_large=10,
        extensions=None,
        ignore_dirs=[],
        output_file=None,
    )
    # Use the new CCA analyzer for cyclomatic complexity
    if CyclomaticComplexityAnalyzer is not None:
        results = runner.analyze_complexity([py, js, cs])
        assert any(r.get("threshold", None) == 1 for r in results)
    else:
        # If CCA is not available, the runner returns []
        assert runner.analyze_complexity([py, js, cs]) == []


def test_runner_run_catches_exception(tmp_path, monkeypatch):
    # Simulate an exception in run
    runner = ReplicheckRunner(
        path=tmp_path,
        min_similarity=0.8,
        min_size=5,
        output_format="text",
        complexity_threshold=1,
        large_file_threshold=500,
        large_class_threshold=300,
        top_n_large=10,
        extensions=None,
        ignore_dirs=[],
        output_file=None,
    )
    monkeypatch.setattr(
        "replicheck.runner.CodeParser",
        lambda *a, **k: (_ for _ in ()).throw(Exception("fail")),
    )
    assert runner.run() == 1
