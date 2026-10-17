"""
Tests for the cross-run cache.

The hazard this feature has to avoid is answering with stale findings, which is
worse than being slow, so most of these tests are about what *invalidates* an
entry rather than about the speed-up.
"""

import json

import pytest

from replicheck.cache import CACHE_SCHEMA, FINGERPRINT_KEYS, ScanCache, file_digest
from replicheck.runner import ReplicheckRunner


def write(path, name, content):
    target = path / name
    target.write_text(content, encoding="utf-8")
    return target


def make_cache(root, settings=None, cache_file=None):
    defaults = {
        "min_size": 5,
        "complexity_threshold": 10,
        "large_file_threshold": 500,
        "large_class_threshold": 300,
        "flake8_codes": "F401,F841",
        "extensions": [".py"],
    }
    return ScanCache(
        cache_file or (root / ".replicheck-cache.json"),
        root,
        settings or defaults,
    )


def runner_kwargs(path, **overrides):
    kwargs = {
        "path": path,
        "min_similarity": 0.8,
        "min_size": 5,
        "output_format": "json",
        "complexity_threshold": 10,
        "large_file_threshold": 500,
        "large_class_threshold": 300,
        "top_n_large": 10,
        "extensions": None,
        "ignore_dirs": [],
        "output_file": None,
    }
    kwargs.update(overrides)
    return kwargs


# ----------------------------------------------------------------------
# Digest and entry validity
# ----------------------------------------------------------------------


def test_file_digest_changes_with_content(tmp_path):
    a = write(tmp_path, "a.py", "x = 1\n")
    before = file_digest(a)
    a.write_text("x = 2\n", encoding="utf-8")
    assert before != file_digest(a)


def test_file_digest_of_missing_file_is_empty(tmp_path):
    assert file_digest(tmp_path / "absent.py") == ""


def test_matching_content_hits_and_changed_content_misses(tmp_path):
    a = write(tmp_path, "a.py", "x = 1\n")
    cache = make_cache(tmp_path)
    cache.put(a, {"unused": [{"file": str(a)}]})

    assert cache.get(a) == {"unused": [{"file": str(a)}]}
    assert cache.hits == 1

    a.write_text("x = 2\n", encoding="utf-8")
    assert cache.get(a) is None
    assert cache.misses == 1


def test_a_file_outside_the_root_is_never_cached(tmp_path):
    inside = tmp_path / "tree"
    inside.mkdir()
    outside = write(tmp_path, "elsewhere.py", "x = 1\n")

    cache = make_cache(inside)
    cache.put(outside, {"unused": []})
    assert cache.get(outside) is None
    assert cache.entries == {}


# ----------------------------------------------------------------------
# What invalidates the whole cache
# ----------------------------------------------------------------------


def test_schema_change_discards_the_cache(tmp_path):
    a = write(tmp_path, "a.py", "x = 1\n")
    cache = make_cache(tmp_path)
    cache.put(a, {"unused": []})
    cache.save()

    raw = json.loads((tmp_path / ".replicheck-cache.json").read_text(encoding="utf-8"))
    raw["schema"] = CACHE_SCHEMA + 1
    (tmp_path / ".replicheck-cache.json").write_text(json.dumps(raw), encoding="utf-8")

    reloaded = make_cache(tmp_path)
    reloaded.load()
    assert reloaded.get(a) is None


def test_a_different_root_discards_the_cache(tmp_path):
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    root_a.mkdir()
    root_b.mkdir()
    write(root_a, "f.py", "x = 1\n")

    cache = make_cache(root_a)
    cache.put(root_a / "f.py", {"unused": []})
    cache.save()

    # Same cache file, but now presented as belonging to another tree.
    other = ScanCache(root_a / ".replicheck-cache.json", root_b, cache.settings)
    other.load()
    assert other.entries == {}


def test_a_settings_change_discards_the_cache(tmp_path):
    a = write(tmp_path, "a.py", "x = 1\n")
    cache = make_cache(tmp_path)
    cache.put(a, {"unused": []})
    cache.save()

    changed = make_cache(tmp_path)
    changed.settings["complexity_threshold"] = 99
    changed.load()
    assert changed.get(a) is None


def test_a_corrupt_cache_is_ignored_with_a_warning(tmp_path, capsys):
    a = write(tmp_path, "a.py", "x = 1\n")
    (tmp_path / ".replicheck-cache.json").write_text("{not json", encoding="utf-8")

    cache = make_cache(tmp_path)
    cache.load()
    assert cache.entries == {}
    assert cache.get(a) is None
    assert "unreadable cache" in capsys.readouterr().err


def test_an_unwritable_cache_location_warns_instead_of_crashing(tmp_path, capsys):
    blocker = write(tmp_path, "blocker", "not a directory\n")
    cache = make_cache(tmp_path, cache_file=blocker / "cache.json")
    cache.put(tmp_path / "x.py", {})
    cache.save()
    assert "could not write cache" in capsys.readouterr().err


def test_prune_to_drops_files_no_longer_scanned(tmp_path):
    kept = write(tmp_path, "kept.py", "x = 1\n")
    dropped = write(tmp_path, "dropped.py", "y = 1\n")
    cache = make_cache(tmp_path)
    cache.put(kept, {})
    cache.put(dropped, {})
    assert len(cache.entries) == 2

    cache.prune_to([kept])
    assert list(cache.entries) == ["kept.py"]


# ----------------------------------------------------------------------
# The integration that matters: cached vs uncached results
# ----------------------------------------------------------------------


BODY = (
    "def shared(alpha, beta):\n"
    "    if alpha:\n"
    "        return beta\n"
    "    total = alpha + beta\n"
    "    return total\n"
)
EXTRA = "import json\n\n\ndef only_here(x=[]):\n    return x\n"


def test_a_warm_cached_run_matches_an_uncached_run(tmp_path):
    """
    The whole point: reusing cached per-file results must produce the same
    report as analysing everything - including cross-file duplicate groups,
    which are built from blocks that came partly out of the cache.
    """
    write(tmp_path, "one.py", BODY)
    write(tmp_path, "two.py", BODY + EXTRA)

    def reports(prefix, **overrides):
        runner = ReplicheckRunner(
            **runner_kwargs(
                tmp_path, output_file=str(tmp_path / f"{prefix}.json"), **overrides
            )
        )
        assert runner.run() == 0
        return json.loads((tmp_path / f"{prefix}.json").read_text(encoding="utf-8"))

    uncached = reports("uncached")
    cold = reports("cold", cache=True)
    warm = reports("warm", cache=True)

    assert cold == uncached
    assert warm == uncached
    # The duplicate group spanning both files survived the cache round-trip.
    assert uncached["duplicates"]
    assert warm["duplicates"] == uncached["duplicates"]
    assert warm["unused"] == uncached["unused"]


def test_editing_a_file_after_a_cached_run_reports_the_new_finding(tmp_path, capsys):
    write(tmp_path, "a.py", "def f(x):\n    return x\n")
    write(tmp_path, "b.py", "def g(y):\n    return y\n")

    def run(prefix):
        runner = ReplicheckRunner(
            **runner_kwargs(
                tmp_path, cache=True, output_file=str(tmp_path / f"{prefix}.json")
            )
        )
        assert runner.run() == 0
        return json.loads((tmp_path / f"{prefix}.json").read_text(encoding="utf-8"))

    first = run("first")
    assert first["unused"] == []

    write(tmp_path, "a.py", "import os\n\n\ndef f(x):\n    return x\n")
    second = run("second")

    assert [r["code"] for r in second["unused"]] == ["F401"]
    capsys.readouterr()


def test_caching_is_off_unless_asked_for(tmp_path):
    """No cache file is written when caching was not requested."""
    write(tmp_path, "a.py", "def f(x):\n    return x\n")
    runner = ReplicheckRunner(
        **runner_kwargs(tmp_path, output_file=str(tmp_path / "r.json"))
    )
    assert runner.run() == 0
    assert not (tmp_path / ".replicheck-cache.json").exists()


def test_full_scan_overrides_the_cache(tmp_path, capsys):
    write(tmp_path, "a.py", "def f(x):\n    return x\n")
    runner = ReplicheckRunner(
        **runner_kwargs(
            tmp_path,
            cache=True,
            full_scan=True,
            output_file=str(tmp_path / "r.json"),
        )
    )
    assert runner.run() == 0
    assert not (tmp_path / ".replicheck-cache.json").exists()
    capsys.readouterr()


def test_flake8_codes_narrows_the_selection(tmp_path):
    """Trimming is honoured, and is how a caller trades findings for speed."""
    write(tmp_path, "a.py", "import os\n\n\ndef f(x=[]):\n    return x\n")

    def bns_count(prefix, **overrides):
        runner = ReplicheckRunner(
            **runner_kwargs(
                tmp_path, output_file=str(tmp_path / f"{prefix}.json"), **overrides
            )
        )
        assert runner.run() == 0
        return json.loads((tmp_path / f"{prefix}.json").read_text(encoding="utf-8"))[
            "bns_results"
        ]

    assert bns_count("full")  # a mutable default argument is reported
    assert bns_count("trimmed", flake8_codes="F401") == []
    assert bns_count("forced", flake8_codes="F401", full_scan=True)


def test_top_n_large_zero_means_all_not_none(tmp_path):
    """
    --top-n-large documents 0 as "all", and it must actually mean all - the
    cache collects untruncated and cuts after merging, so a wrong reading here
    would silently drop every large file.
    """
    body = "\n".join(f"v{i} = {i}" for i in range(400))
    write(tmp_path, "big.py", body)

    def large_count(top_n):
        runner = ReplicheckRunner(
            **runner_kwargs(
                tmp_path,
                large_file_threshold=10,
                top_n_large=top_n,
                output_file=str(tmp_path / f"t{top_n}.json"),
            )
        )
        assert runner.run() == 0
        return json.loads((tmp_path / f"t{top_n}.json").read_text(encoding="utf-8"))[
            "large_files"
        ]

    assert large_count(0)
    assert large_count(1) == large_count(0)[:1]


@pytest.mark.parametrize("threshold", [0, 1])
def test_cache_respects_the_smallest_round_trip(tmp_path, threshold):
    write(tmp_path, "a.py", "def f(x):\n    return x\n")

    def run(prefix, **overrides):
        runner = ReplicheckRunner(
            **runner_kwargs(
                tmp_path,
                cache=True,
                output_file=str(tmp_path / f"{prefix}.json"),
                **overrides,
            )
        )
        assert runner.run() == 0
        return json.loads((tmp_path / f"{prefix}.json").read_text(encoding="utf-8"))

    first = run("a", complexity_threshold=threshold)
    second = run("b", complexity_threshold=threshold)
    assert first == second


def test_a_mixed_cached_run_matches_an_uncached_run(tmp_path):
    """
    The earlier regression test only exercised a full cache hit, so it could
    not see that a mixed run emits cached results before fresh ones and is
    therefore not byte-identical to an uncached run.
    """
    for name in ("one.py", "two.py", "three.py"):
        write(tmp_path, name, BODY)

    def report(prefix, **overrides):
        runner = ReplicheckRunner(
            **runner_kwargs(
                tmp_path,
                cache=overrides.pop("cache", False),
                output_file=str(tmp_path / f"{prefix}.json"),
                **overrides,
            )
        )
        assert runner.run() == 0
        return json.loads((tmp_path / f"{prefix}.json").read_text(encoding="utf-8"))

    report("cold", cache=True)
    write(tmp_path, "one.py", BODY + "import json\n")
    warm = report("warm", cache=True)
    uncached = report("uncached")

    assert warm == uncached


def test_a_tool_becoming_available_invalidates_the_cache(tmp_path, monkeypatch):
    """
    A missing tool makes its detector return nothing. Those empty results must
    never be answered to a later run made with the tool installed: that is a
    silent false negative, which is the failure caching exists to avoid.

    Both states are forced rather than resting on the real build. On a machine
    where the analyzer was never built - CI, for one - patching the path to a
    missing file and then restoring it leaves the marker "absent" either way,
    so no invalidation is expected and the test would fail for the wrong
    reason.
    """
    import replicheck.tools.CyclomaticComplexity.cs_utils as cs_utils

    write(tmp_path, "a.cs", "public class C { public int F(int a) { return 1; } }")

    def run(prefix):
        runner = ReplicheckRunner(
            **runner_kwargs(
                tmp_path,
                cache=True,
                complexity_threshold=1,
                output_file=str(tmp_path / f"{prefix}.json"),
            )
        )
        assert runner.run() == 0
        return json.loads((tmp_path / f"{prefix}.json").read_text(encoding="utf-8"))[
            "complexity_results"
        ]

    # Absent: a path that does not exist, so the detector finds nothing and that
    # emptiness gets cached.
    monkeypatch.setattr(cs_utils, "_analyzer_path", lambda: tmp_path / "absent.exe")
    assert run("absent") == []

    # Present: a path that does exist, so the tool marker changes, plus a stubbed
    # detector - this test is about the cache key, not about running the binary.
    built = write(tmp_path, "built.exe", "")
    monkeypatch.setattr(cs_utils, "_analyzer_path", lambda: built)
    monkeypatch.setattr(
        cs_utils,
        "analyze_cs_cyclomatic_complexity_batch",
        lambda files, threshold=10: [
            {
                "name": "F",
                "complexity": 3,
                "lineno": 1,
                "endline": 1,
                "file": str(path),
                "threshold": threshold,
                "severity": "Low 🟢",
            }
            for path in files
        ],
    )
    assert run("present")  # must not reuse the empty results


def test_min_size_is_not_part_of_the_fingerprint():
    """
    min_size only filters duplicate candidates after the per-file results are
    merged, so changing it cannot change what a file's own results mean and
    need not discard the cache. Flagged by review as an over-invalidation.
    """
    assert "min_size" not in FINGERPRINT_KEYS
