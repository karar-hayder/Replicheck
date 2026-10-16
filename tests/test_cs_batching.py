"""
Tests for C# complexity batching and analyzer discovery.

The analyzer is a compiled binary whose start-up costs ~204 ms per invocation
and does not depend on file size, so one process per file made a large C#
repository take minutes. These tests pin the batching, the fallback and the
path search without needing the binary built.
"""

import json
import subprocess
from pathlib import Path

from replicheck.tools.CyclomaticComplexity import cs_utils


class FakeCompleted:
    def __init__(self, stdout="{}", returncode=0):
        self.stdout = stdout
        self.returncode = returncode


def _fake_analyzer(monkeypatch, tmp_path):
    """Point the module at a path that exists so the guard passes."""
    fake = tmp_path / "ComplexityAnalyzer.exe"
    fake.write_text("", encoding="utf-8")
    monkeypatch.setattr(cs_utils, "_analyzer_path", lambda: fake)
    return fake


def test_analyzer_path_prefers_win_x64_then_publish(monkeypatch):
    """
    `dotnet build -c Release -r win-x64` writes to win-x64/ while `dotnet
    publish` writes to win-x64/publish/. A publish-only build must still be
    found rather than reported as missing.
    """
    real_exists = Path.exists

    def only_publish(self):
        if "win-x64" in str(self):
            return "publish" in str(self)
        return real_exists(self)

    monkeypatch.setattr(Path, "exists", only_publish)
    assert cs_utils._analyzer_path().parent.name == "publish"

    monkeypatch.setattr(Path, "exists", real_exists)


def test_files_are_batched_into_few_invocations(monkeypatch, tmp_path):
    _fake_analyzer(monkeypatch, tmp_path)
    calls = []

    def fake_run(cmd, *args, **kwargs):
        calls.append(cmd)
        return FakeCompleted()

    monkeypatch.setattr(subprocess, "run", fake_run)

    files = [tmp_path / f"f{i}.cs" for i in range(60)]
    cs_utils.analyze_cs_cyclomatic_complexity_batch(files, 10, batch_size=25)

    assert len(calls) == 3
    passed = [p for cmd in calls for p in cmd[1:]]
    assert sorted(passed) == sorted(str(f) for f in files)


def test_findings_are_read_from_the_batched_payload(monkeypatch, tmp_path):
    _fake_analyzer(monkeypatch, tmp_path)
    payload = {
        "a.cs": [{"Name": "Big", "Complexity": 14, "LineNo": 3, "EndLine": 20}],
        "b.cs": [{"Name": "Small", "Complexity": 2, "LineNo": 1, "EndLine": 4}],
        "c.cs": None,
    }
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: FakeCompleted(stdout=json.dumps(payload)),
    )

    results = cs_utils.analyze_cs_cyclomatic_complexity_batch(
        [tmp_path / "a.cs", tmp_path / "b.cs", tmp_path / "c.cs"], threshold=10
    )

    assert [r["file"] for r in results] == ["a.cs"]
    assert results[0]["name"] == "Big"
    assert results[0]["complexity"] == 14
    assert results[0]["severity"]


def test_batch_failure_falls_back_to_one_call_per_file(monkeypatch, tmp_path):
    _fake_analyzer(monkeypatch, tmp_path)
    state = {"batch": 0, "single": 0}

    def fake_run(cmd, *args, **kwargs):
        if len(cmd) - 1 > 1:
            state["batch"] += 1
            return FakeCompleted(stdout="", returncode=1)
        state["single"] += 1
        payload = {
            cmd[-1]: [{"Name": "f", "Complexity": 11, "LineNo": 1, "EndLine": 2}]
        }
        return FakeCompleted(stdout=json.dumps(payload))

    monkeypatch.setattr(subprocess, "run", fake_run)

    files = [tmp_path / f"f{i}.cs" for i in range(4)]
    results = cs_utils.analyze_cs_cyclomatic_complexity_batch(files, 10, batch_size=4)

    assert state["batch"] == 1
    assert state["single"] == 4
    assert len(results) == 4


def test_missing_analyzer_warns_and_returns_empty(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cs_utils, "_analyzer_missing_warned", False)
    monkeypatch.setattr(cs_utils, "_analyzer_path", lambda: tmp_path / "absent.exe")

    assert (
        cs_utils.analyze_cs_cyclomatic_complexity_batch([tmp_path / "a.cs"], 10) == []
    )
    assert "not found" in capsys.readouterr().err
