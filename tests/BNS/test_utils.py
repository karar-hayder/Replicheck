from replicheck.tools.bugNsafety.BNS import BugNSafetyAnalyzer


def make_file(tmp_path, name, content):
    file = tmp_path / name
    file.write_text(content)
    return file


def get_findings(files, ignore_dirs=None):
    analyzer = BugNSafetyAnalyzer(files, ignore_dirs=ignore_dirs)
    analyzer.analyze()
    return analyzer.results


def test_bugbear_multiple_files(tmp_path):
    code1 = "def foo(x=[]): pass\n"
    code2 = "def bar(y={}): pass\n"
    f1 = make_file(tmp_path, "a.py", code1)
    f2 = make_file(tmp_path, "b.py", code2)
    results = get_findings([f1, f2])
    bugbear = [r for r in results if r["code"].startswith("B")]
    assert any(r["file"].endswith("a.py") for r in bugbear)
    assert any(r["file"].endswith("b.py") for r in bugbear)
    assert all("B" in r["code"] for r in bugbear)


def test_bandit_multiple_files(tmp_path):
    code1 = "def foo(): eval('2+2')\n"
    code2 = "def bar(): import os; os.system('ls')\n"
    f1 = make_file(tmp_path, "a.py", code1)
    f2 = make_file(tmp_path, "b.py", code2)
    results = get_findings([f1, f2])
    bandit = [r for r in results if r["code"].startswith("S")]
    assert any(r["file"].endswith("a.py") for r in bandit)
    assert any(r["file"].endswith("b.py") for r in bandit)
    assert all("S" in r["code"] for r in bandit)


def test_eradicate_multiple_files(tmp_path):
    code1 = "# print('dead code')\n"
    code2 = "# x = 1\n"
    f1 = make_file(tmp_path, "a.py", code1)
    f2 = make_file(tmp_path, "b.py", code2)
    results = get_findings([f1, f2])
    eradicate = [r for r in results if r["code"] == "E800"]
    assert any(r["file"].endswith("a.py") for r in eradicate)
    assert any(r["file"].endswith("b.py") for r in eradicate)
    assert all(r["code"] == "E800" for r in eradicate)


def test_bugbear_ignore_dirs(tmp_path):
    code = "def foo(x=[]): pass\n"
    subdir = tmp_path / "ignoreme"
    subdir.mkdir()
    f1 = make_file(tmp_path, "a.py", code)
    f2 = make_file(subdir, "b.py", code)
    results = get_findings([f1, f2], ignore_dirs=[str(subdir)])
    bugbear = [r for r in results if r["code"].startswith("B")]
    assert any(r["file"].endswith("a.py") for r in bugbear)
    assert not any(r["file"].endswith("b.py") for r in bugbear)


def test_bandit_ignore_dirs(tmp_path):
    code = "def foo(): eval('2+2')\n"
    subdir = tmp_path / "ignoreme"
    subdir.mkdir()
    f1 = make_file(tmp_path, "a.py", code)
    f2 = make_file(subdir, "b.py", code)
    results = get_findings([f1, f2], ignore_dirs=[str(subdir)])
    bandit = [r for r in results if r["code"].startswith("S")]
    assert any(r["file"].endswith("a.py") for r in bandit)
    assert not any(r["file"].endswith("b.py") for r in bandit)


def test_eradicate_ignore_dirs(tmp_path):
    code = "# print('dead code')\n"
    subdir = tmp_path / "ignoreme"
    subdir.mkdir()
    f1 = make_file(tmp_path, "a.py", code)
    f2 = make_file(subdir, "b.py", code)
    results = get_findings([f1, f2], ignore_dirs=[str(subdir)])
    eradicate = [r for r in results if r["code"] == "E800"]
    assert any(r["file"].endswith("a.py") for r in eradicate)
    assert not any(r["file"].endswith("b.py") for r in eradicate)


def test_bugbear_handles_flake8_failure(monkeypatch, tmp_path):
    # Simulate flake8 not installed or crashing
    import replicheck.tools.bugNsafety.utils_python as UP

    def fake_run(*a, **k):
        raise RuntimeError("flake8 not found")

    monkeypatch.setattr("subprocess.run", fake_run)
    file = make_file(tmp_path, "fail.py", "def foo(x=[]): pass\n")
    # Should return empty for bugbear
    assert UP._run_flake8_all([file]) == []


def test_bandit_handles_flake8_failure(monkeypatch, tmp_path):
    import replicheck.tools.bugNsafety.utils_python as UP

    def fake_run(*a, **k):
        raise RuntimeError("flake8 not found")

    monkeypatch.setattr("subprocess.run", fake_run)
    file = make_file(tmp_path, "fail.py", "def foo(): eval('2+2')\n")
    assert UP._run_flake8_all([file]) == []


def test_eradicate_handles_flake8_failure(monkeypatch, tmp_path):
    import replicheck.tools.bugNsafety.utils_python as UP

    def fake_run(*a, **k):
        raise RuntimeError("flake8 not found")

    monkeypatch.setattr("subprocess.run", fake_run)
    file = make_file(tmp_path, "fail.py", "# print('dead code')\n")
    # _run_flake8_all is now the only public runner, so use it
    assert UP._run_flake8_all([file]) == []


def test_bugbear_handles_non_utf8_output(monkeypatch, tmp_path):
    import replicheck.tools.bugNsafety.utils_python as UP

    class FakeResult:
        stdout = b"\xff\xfe".decode("utf-8", errors="ignore")
        stderr = ""

    def fake_run(*a, **k):
        return FakeResult()

    monkeypatch.setattr("subprocess.run", fake_run)
    file = make_file(tmp_path, "bad.py", "def foo(x=[]): pass\n")
    # _run_flake8_all is now the only public runner, so use it
    assert UP._run_flake8_all([file]) == []


def test_bandit_handles_non_utf8_output(monkeypatch, tmp_path):
    import replicheck.tools.bugNsafety.utils_python as UP

    class FakeResult:
        stdout = b"\xff\xfe".decode("utf-8", errors="ignore")
        stderr = ""

    def fake_run(*a, **k):
        return FakeResult()

    monkeypatch.setattr("subprocess.run", fake_run)
    file = make_file(tmp_path, "bad.py", "def foo(): eval('2+2')\n")
    # _run_flake8_all is now the only public runner, so use it
    assert UP._run_flake8_all([file]) == []


def test_eradicate_handles_non_utf8_output(monkeypatch, tmp_path):
    import replicheck.tools.bugNsafety.utils_python as UP

    class FakeResult:
        stdout = b"\xff\xfe".decode("utf-8", errors="ignore")
        stderr = ""

    def fake_run(*a, **k):
        return FakeResult()

    monkeypatch.setattr("subprocess.run", fake_run)
    file = make_file(tmp_path, "bad.py", "# print('dead code')\n")
    # _run_flake8_all is now the only public runner, so use it
    assert UP._run_flake8_all([file]) == []
