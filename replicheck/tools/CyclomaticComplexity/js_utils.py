import sys
from pathlib import Path

from replicheck.utils import compute_severity

# Node.js and typhonjs-escomplex are setup steps, not bundled (see README,
# "JavaScript/JSX Development"). Warn once so a missing install is visible
# instead of looking like "no complex functions".
_node_missing_warned = False

# Node start-up dominates this path: measured at ~200 ms per invocation
# regardless of file size, so one process per file cost a large JS repository
# minutes. Batching amortises that start-up across many files. Measured on 100
# real files: 199.6 ms/file one-at-a-time, 29.3 ms at 10 per batch, 11.4 ms at
# 50, 8.7 ms at 100. 50 is the balance - a larger batch saves little more and
# widens the fallback if a batch as a whole fails.
DEFAULT_BATCH_SIZE = 50
# One batch does the same per-file work as the original single-file call, which
# allowed 20s, so the budget grows with the batch.
BATCH_TIMEOUT_SECONDS = 60
SINGLE_TIMEOUT_SECONDS = 20


def _warn_missing_node():
    global _node_missing_warned
    if not _node_missing_warned:
        print(
            "[WARN] Node.js not found; JS/TS cyclomatic complexity will be "
            "skipped. See README, 'JavaScript/JSX Development'.",
            file=sys.stderr,
        )
        _node_missing_warned = True


def _helper_path() -> Path:
    return Path(__file__).parent.parent.parent.parent / "utils" / "helpers.js"


def _run_node_helper(helper_path: Path, file_paths):
    """
    Run the helper over one or more paths.

    Returns a result object with `returncode` and `stdout`; a launch failure
    yields a stub with returncode 1 rather than raising.
    """
    import subprocess

    paths = [str(p) for p in file_paths]
    timeout = BATCH_TIMEOUT_SECONDS if len(paths) > 1 else SINGLE_TIMEOUT_SECONDS
    try:
        return subprocess.run(
            ["node", str(helper_path), *paths],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        _warn_missing_node()
    except Exception:
        pass

    class DummyProc:
        returncode = 1
        stdout = ""

    return DummyProc()


def _load_payload(proc):
    """Parse the helper's JSON object, or None if the call did not succeed."""
    import json

    if getattr(proc, "returncode", 1) != 0:
        return None
    try:
        payload = json.loads(proc.stdout)
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _findings(payload, threshold):
    """Flatten {path: [function, ...]} into reported findings."""
    results = []
    for file_path, functions in payload.items():
        if not functions:
            # None means the helper could not analyse that file.
            continue
        for fn in functions:
            complexity = fn.get("complexity", 0)
            if complexity >= threshold:
                results.append(
                    {
                        "name": fn.get("name", "<anonymous>"),
                        "complexity": complexity,
                        "lineno": fn.get("lineno"),
                        "endline": fn.get("endline"),
                        "file": str(file_path),
                        "threshold": threshold,
                        "severity": compute_severity(complexity, threshold),
                    }
                )
    return results


def analyze_js_cyclomatic_complexity_batch(
    file_paths, threshold: int = 10, batch_size: int = DEFAULT_BATCH_SIZE
):
    """
    Analyze many JS/TS files in a few Node invocations instead of one per file.

    Falls back to one call per file if a batch fails as a unit, so a single
    pathological file cannot cost the whole batch its results.
    """
    helper_path = _helper_path()
    paths = [Path(p) for p in file_paths]
    results = []

    for start in range(0, len(paths), batch_size):
        batch = paths[start : start + batch_size]
        payload = _load_payload(_run_node_helper(helper_path, batch))

        if payload is None and len(batch) > 1:
            for single in batch:
                single_payload = _load_payload(_run_node_helper(helper_path, [single]))
                if single_payload:
                    results.extend(_findings(single_payload, threshold))
            continue

        if payload:
            results.extend(_findings(payload, threshold))

    return results


def analyze_js_cyclomatic_complexity(file_path: Path, threshold: int = 10):
    """
    Analyze cyclomatic complexity of a single JS file via the Node.js helper.

    Kept for callers that work file by file; a scan uses the batch entry point.
    """
    return analyze_js_cyclomatic_complexity_batch([file_path], threshold)
