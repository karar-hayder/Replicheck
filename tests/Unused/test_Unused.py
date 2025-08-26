import pytest

from replicheck.tools.Unused.Unused import UnusedCodeDetector


def make_py_file(tmp_path, name, content):
    file_path = tmp_path / name
    file_path.write_text(content, encoding="utf-8")
    return file_path


def test_unused_detector_finds_unused_import(tmp_path):
    code = "import os\nx = 1\n"
    file_path = make_py_file(tmp_path, "a.py", code)
    detector = UnusedCodeDetector()
    detector.find_unused([file_path])
    results = detector.results
    # Should find unused import 'os'
    assert any("imported but unused" in r["message"] for r in results)
    assert any(r["file"].endswith("a.py") for r in results)


def test_unused_detector_finds_unused_variable(tmp_path):
    code = "def foo():\n    x = 1\n    return 2\n"
    file_path = make_py_file(tmp_path, "b.py", code)
    detector = UnusedCodeDetector()
    detector.find_unused([file_path])
    results = detector.results
    # Should find unused variable 'x'
    assert any("assigned to but never used" in r["message"] for r in results)
    assert any(r["file"].endswith("b.py") for r in results)


def test_unused_detector_no_false_positives(tmp_path):
    code = "import sys\nprint(sys.version)\n"
    file_path = make_py_file(tmp_path, "c.py", code)
    detector = UnusedCodeDetector()
    detector.find_unused([file_path])
    results = detector.results
    # Should not report any unused import
    assert not results


def test_unused_detector_handles_non_py_files(tmp_path):
    file_path = make_py_file(tmp_path, "d.js", "var x = 1;")
    detector = UnusedCodeDetector()
    detector.find_unused([file_path])
    # Should not crash, should not report anything
    assert detector.results == []


def test_unused_detector_handles_empty_list():
    detector = UnusedCodeDetector()
    detector.find_unused([])
    assert detector.results == []


def test_unused_detector_handles_flake8_not_installed(monkeypatch, tmp_path):
    # Simulate flake8 not installed by patching subprocess.run to raise FileNotFoundError
    import subprocess

    def raise_fnf(*a, **k):
        raise FileNotFoundError("flake8 not found")

    monkeypatch.setattr(subprocess, "run", raise_fnf)
    file_path = tmp_path / "e.py"
    file_path.write_text("import os\n", encoding="utf-8")
    detector = UnusedCodeDetector()
    detector.find_unused([file_path])
    # Should not raise, should return empty
    assert detector.results == []


def test_unused_detector_ignore_dirs(tmp_path):
    code = "import os\n"
    file_path = make_py_file(tmp_path, "f.py", code)
    detector = UnusedCodeDetector()
    # Should still find unused import, ignore_dirs is just passed through
    detector.find_unused([file_path], ignore_dirs=["some_dir"])
    results = detector.results
    assert any("imported but unused" in r["message"] for r in results)


def test_unused_detector_multiple_files(tmp_path):
    code1 = "import os\n"
    code2 = "def foo():\n    y = 2\n"
    file1 = make_py_file(tmp_path, "g.py", code1)
    file2 = make_py_file(tmp_path, "h.py", code2)
    detector = UnusedCodeDetector()
    detector.find_unused([file1, file2])
    results = detector.results
    assert any(r["file"].endswith("g.py") for r in results)
    assert any(r["file"].endswith("h.py") for r in results)
    assert any(
        "imported but unused" in r["message"]
        or "assigned to but never used" in r["message"]
        for r in results
    )


def test_unused_detector_handles_flake8_output_format(tmp_path):
    # Simulate a flake8 output line that doesn't match the regex
    class FakeCompletedProcess:
        def __init__(self):
            self.stdout = "not a flake8 error line\n"
            self.stderr = ""

    def fake_run(*a, **k):
        return FakeCompletedProcess()

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr("subprocess.run", fake_run)
    file_path = make_py_file(tmp_path, "i.py", "import os\n")
    detector = UnusedCodeDetector()
    detector.find_unused([file_path])
    # Should not crash, should return empty
    assert detector.results == []
    monkeypatch.undo()
