import replicheck.tools.bugNsafety.utils_python as UP
from replicheck.tools.bugNsafety.BNS import BugNSafetyAnalyzer


def make_py_file(tmp_path, content):
    file = tmp_path / "test.py"
    file.write_text(content)
    return file


def make_files(tmp_path, files):
    paths = []
    for name, content in files.items():
        f = tmp_path / name
        f.write_text(content)
        paths.append(f)
    return paths


def test_bns_analyze_python(tmp_path):
    # File with mutable default arg (should trigger bugbear B006)
    code = "def foo(x=[]):\n    pass\n"
    py_file = make_py_file(tmp_path, code)
    analyzer = BugNSafetyAnalyzer([py_file])
    analyzer.analyze()
    bugbear = [r for r in analyzer.results if r.get("code", "").startswith("B")]
    assert any("mutable" in r["message"] for r in bugbear)


def test_bns_analyze_python_bandit(tmp_path):
    # File with dangerous eval (should trigger bandit S307)
    code = "def foo():\n    eval('2+2')\n"
    py_file = make_py_file(tmp_path, code)
    analyzer = BugNSafetyAnalyzer([py_file])
    analyzer.analyze()
    bandit = [r for r in analyzer.results if r.get("code", "").startswith("S")]
    assert any("eval" in r["message"] or "Use of" in r["message"] for r in bandit)


def test_bns_analyze_python_eradicate(tmp_path):
    # File with commented-out code (should trigger eradicate E800)
    code = "# print('dead code')\n"
    py_file = make_py_file(tmp_path, code)
    analyzer = BugNSafetyAnalyzer([py_file])
    analyzer.analyze()
    eradicate = [r for r in analyzer.results if r.get("code", "") == "E800"]
    assert any("commented out code" in r["message"].lower() for r in eradicate)


def test_bns_analyze_js_and_cs_are_stubs(tmp_path):
    js_file = tmp_path / "foo.js"
    js_file.write_text("function foo() { return 1; }")
    cs_file = tmp_path / "foo.cs"
    cs_file.write_text("class Foo { int Bar() { return 1; } }")
    analyzer = BugNSafetyAnalyzer([js_file, cs_file])
    analyzer.analyze()
    # Should not raise, and results should be empty (stubs)
    assert analyzer.results == []


def test_utils_python_bugbear(tmp_path):
    code = "def foo(x={}): pass\n"
    py_file = make_py_file(tmp_path, code)
    results = UP._run_flake8_all([py_file])
    assert any(r["code"].startswith("B") for r in results)


def test_utils_python_bandit(tmp_path):
    code = "def foo():\n    import os\n    os.system('ls')\n"
    py_file = make_py_file(tmp_path, code)
    results = UP._run_flake8_all([py_file])
    assert any(r["code"].startswith("S") for r in results)


def test_utils_python_eradicate(tmp_path):
    code = "# x = 1\n"
    py_file = make_py_file(tmp_path, code)
    results = UP._run_flake8_all([py_file])
    assert any(r["code"] == "E800" for r in results)


def test_utils_python_empty_input():
    assert UP._run_flake8_all([]) == []


def test_utils_python_handles_nonexistent_file(tmp_path):
    fake = tmp_path / "doesnotexist.py"
    assert UP._run_flake8_all([fake]) == []


def test_utils_python_handles_encoding_error(tmp_path):
    file = tmp_path / "badenc.py"
    with open(file, "wb") as f:
        f.write(b"\xff\xfe")
    assert UP._run_flake8_all([file]) == []
