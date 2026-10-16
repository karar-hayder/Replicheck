"""
Tests for the shared chunked flake8 runner.

The regression these guard against: a single command line listing every file in
a large repository exceeds the OS argument limit (32767 chars on Windows), so
flake8 never runs and the detectors silently report nothing.
"""

import subprocess

from replicheck.tools.flake8_runner import PATH_BUDGET_CHARS, chunk_paths, run_flake8


class FakeCompleted:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def test_chunk_paths_splits_when_budget_exceeded():
    paths = [f"file_{i}.py" for i in range(10)]  # 11 chars each
    chunks = chunk_paths(paths, budget=40)
    assert len(chunks) > 1
    # Every path survives, in order, exactly once.
    assert [p for chunk in chunks for p in chunk] == paths


def test_chunk_paths_single_oversized_path_is_kept():
    chunks = chunk_paths(["a_very_long_path_that_exceeds_the_budget.py"], budget=5)
    assert chunks == [["a_very_long_path_that_exceeds_the_budget.py"]]


def test_chunk_paths_empty_input():
    assert chunk_paths([]) == []


def test_chunk_paths_respects_budget():
    paths = [f"path/number_{i:03d}.py" for i in range(200)]
    for chunk in chunk_paths(paths, budget=500):
        assert sum(len(p) + 1 for p in chunk) <= 500


def test_run_flake8_finds_files_in_every_chunk(monkeypatch, tmp_path):
    """
    Regression: with a small budget the file list is split, and findings from
    the later chunks must still be returned.
    """
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        # Emit one finding for the last path in the chunk.
        target = cmd[-1]
        return FakeCompleted(
            stdout=f"{target}:1:1: F401 'os' imported but unused\n", returncode=1
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    paths = [tmp_path / f"f{i:02d}.py" for i in range(20)]
    findings = run_flake8(paths, select="F401,F841", budget=120)

    assert len(calls) > 1, "expected the file list to be chunked"
    # One finding per chunk, and every path is covered across the chunks.
    assert len(findings) == len(calls)
    covered = {cmd[-1] for cmd in calls}
    assert len(covered) == 20
    assert all(f["code"] == "F401" for f in findings)


def test_run_flake8_returns_empty_when_no_paths():
    assert run_flake8([], select="F401,F841") == []


def test_run_flake8_passes_ignore_dirs_as_exclude(monkeypatch, tmp_path):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return FakeCompleted()

    monkeypatch.setattr(subprocess, "run", fake_run)
    run_flake8([tmp_path / "a.py"], select="F401", ignore_dirs=["build", "dist"])

    assert "--exclude=build" in captured["cmd"]
    assert "--exclude=dist" in captured["cmd"]
    assert "--select=F401" in captured["cmd"]


def test_run_flake8_exit_code_one_is_not_a_failure(monkeypatch, tmp_path, capsys):
    """flake8 exits 1 when it reports findings; that is normal, not an error."""

    def fake_run(cmd, **kwargs):
        return FakeCompleted(
            stdout=f"{cmd[-1]}:1:1: F841 local variable 'x' is assigned to but never used\n",
            returncode=1,
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    findings = run_flake8([tmp_path / "a.py"], select="F401,F841")

    assert len(findings) == 1
    assert "WARN" not in capsys.readouterr().err


def test_run_flake8_warns_on_unexpected_exit_code(monkeypatch, tmp_path, capsys):
    def fake_run(cmd, **kwargs):
        return FakeCompleted(stderr="flake8 exploded", returncode=2)

    monkeypatch.setattr(subprocess, "run", fake_run)
    findings = run_flake8([tmp_path / "a.py"], select="F401")

    assert findings == []
    assert "WARN" in capsys.readouterr().err


def test_run_flake8_warns_and_continues_when_a_chunk_cannot_run(
    monkeypatch, tmp_path, capsys
):
    """
    A chunk that cannot run must not abort the whole scan, and the failure must
    be visible rather than silently yielding nothing.
    """
    state = {"n": 0}

    def fake_run(cmd, **kwargs):
        state["n"] += 1
        if state["n"] == 1:
            raise FileNotFoundError("[WinError 206] filename or extension too long")
        return FakeCompleted(
            stdout=f"{cmd[-1]}:1:1: F401 'os' imported but unused\n", returncode=1
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    paths = [tmp_path / f"f{i:02d}.py" for i in range(20)]
    findings = run_flake8(paths, select="F401,F841", budget=120)

    err = capsys.readouterr().err
    assert "WARN" in err
    assert "WinError 206" in err
    # The surviving chunks still contribute findings.
    assert findings


def test_run_flake8_handles_result_without_returncode(monkeypatch, tmp_path):
    """Existing tests stub subprocess.run with objects lacking a returncode."""

    class Bare:
        stdout = ""
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: Bare())
    assert run_flake8([tmp_path / "a.py"], select="F401") == []


def test_default_budget_fits_windows_limit():
    # The whole command line must stay well under the 32767-char OS ceiling.
    assert PATH_BUDGET_CHARS < 32767
