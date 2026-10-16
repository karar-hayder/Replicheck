"""
Tests that a missing external tool produces a visible warning.

The C# analyzer is built rather than committed (see README, "C# Support"), and
Node.js is a setup step, so both can legitimately be absent. Silence would be
indistinguishable from "this code has no complex functions", which is the same
class of bug as the flake8 command-line overflow.
"""

import subprocess
from pathlib import Path

from replicheck.tools.CyclomaticComplexity import cs_utils, js_utils


def test_missing_cs_analyzer_warns_once_and_returns_empty(
    monkeypatch, tmp_path, capsys
):
    monkeypatch.setattr(cs_utils, "_analyzer_missing_warned", False)
    real_exists = Path.exists
    monkeypatch.setattr(
        Path,
        "exists",
        lambda self: (
            False if "ComplexityAnalyzer.exe" in str(self) else real_exists(self)
        ),
    )

    assert cs_utils.analyze_cs_cyclomatic_complexity(tmp_path / "a.cs") == []
    assert cs_utils.analyze_cs_cyclomatic_complexity(tmp_path / "b.cs") == []

    err = capsys.readouterr().err
    assert err.count("C# complexity analyzer not found") == 1


def test_missing_node_warns_once_and_returns_empty(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(js_utils, "_node_missing_warned", False)

    def fake_run(*args, **kwargs):
        raise FileNotFoundError("node not found")

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert js_utils.analyze_js_cyclomatic_complexity(tmp_path / "a.js") == []
    assert js_utils.analyze_js_cyclomatic_complexity(tmp_path / "b.js") == []

    err = capsys.readouterr().err
    assert err.count("Node.js not found") == 1


def test_js_helper_failure_other_than_missing_node_is_quiet(
    monkeypatch, tmp_path, capsys
):
    """A timeout or crash is not a missing install, so it must not warn."""

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="node", timeout=20)

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert js_utils.analyze_js_cyclomatic_complexity(tmp_path / "a.js") == []
    assert "Node.js not found" not in capsys.readouterr().err
