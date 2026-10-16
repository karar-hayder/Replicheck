"""
Tests for JS/TS complexity batching.

Node start-up costs ~200 ms per invocation and does not depend on file size, so
one process per file made a large JavaScript repository take minutes. These
tests pin the batching and its fallback without needing Node installed.
"""

import json
import subprocess

from replicheck.tools.CyclomaticComplexity import js_utils


class FakeCompleted:
    def __init__(self, stdout="{}", returncode=0):
        self.stdout = stdout
        self.returncode = returncode


def _capture(monkeypatch):
    calls = []

    def fake_run(cmd, *args, **kwargs):
        calls.append(cmd)
        return FakeCompleted()

    monkeypatch.setattr(subprocess, "run", fake_run)
    return calls


def test_files_are_batched_into_few_invocations(monkeypatch, tmp_path):
    calls = _capture(monkeypatch)

    files = [tmp_path / f"f{i}.js" for i in range(60)]
    js_utils.analyze_js_cyclomatic_complexity_batch(files, 10, batch_size=25)

    # 60 files at 25 per batch, not 60 invocations.
    assert len(calls) == 3
    assert all(cmd[0] == "node" for cmd in calls)
    # Every file is passed exactly once.
    passed = [p for cmd in calls for p in cmd[2:]]
    assert sorted(passed) == sorted(str(f) for f in files)


def test_single_file_uses_one_invocation(monkeypatch, tmp_path):
    calls = _capture(monkeypatch)
    js_utils.analyze_js_cyclomatic_complexity(tmp_path / "a.js", 10)
    assert len(calls) == 1


def test_findings_are_read_from_the_batched_payload(monkeypatch, tmp_path):
    payload = (
        '{"a.js": [{"name": "big", "complexity": 12, "lineno": 1, "endline": 9}],'
        ' "b.js": [{"name": "small", "complexity": 2, "lineno": 1, "endline": 3}],'
        ' "c.js": null}'
    )
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: FakeCompleted(stdout=payload)
    )

    results = js_utils.analyze_js_cyclomatic_complexity_batch(
        [tmp_path / "a.js", tmp_path / "b.js", tmp_path / "c.js"], threshold=10
    )

    assert [r["file"] for r in results] == ["a.js"]
    assert results[0]["complexity"] == 12
    assert results[0]["severity"]


def test_batch_failure_falls_back_to_one_call_per_file(monkeypatch, tmp_path):
    """
    A batch that fails as a unit must not cost its files their results; each is
    retried individually.
    """
    state = {"batch_calls": 0, "single_calls": 0}

    def fake_run(cmd, *args, **kwargs):
        if len(cmd) - 2 > 1:
            state["batch_calls"] += 1
            return FakeCompleted(stdout="", returncode=1)
        state["single_calls"] += 1
        # Built with json.dumps: Windows paths contain backslashes, which would
        # produce invalid JSON if interpolated by hand.
        payload = {
            cmd[-1]: [{"name": "f", "complexity": 11, "lineno": 1, "endline": 2}]
        }
        return FakeCompleted(stdout=json.dumps(payload))

    monkeypatch.setattr(subprocess, "run", fake_run)

    files = [tmp_path / f"f{i}.js" for i in range(4)]
    results = js_utils.analyze_js_cyclomatic_complexity_batch(files, 10, batch_size=4)

    assert state["batch_calls"] == 1
    assert state["single_calls"] == 4
    assert len(results) == 4


def test_unparseable_batch_output_is_not_a_crash(monkeypatch, tmp_path):
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: FakeCompleted(stdout="not json")
    )
    files = [tmp_path / "a.js", tmp_path / "b.js"]
    assert js_utils.analyze_js_cyclomatic_complexity_batch(files, 10) == []


def test_empty_file_list_makes_no_invocation(monkeypatch):
    calls = _capture(monkeypatch)
    assert js_utils.analyze_js_cyclomatic_complexity_batch([], 10) == []
    assert calls == []
