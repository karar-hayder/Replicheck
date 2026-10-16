import sys
from pathlib import Path

from replicheck.utils import compute_severity

# The analyzer is built, not committed (see README, "C# Support"). Warn once so
# that a missing build is visible instead of looking like "no complex methods".
_analyzer_missing_warned = False

# Process start-up dominates this path: measured at ~214 ms per invocation and
# independent of file size, so one process per file would cost a large C#
# repository minutes. Batching amortises that across files.
DEFAULT_BATCH_SIZE = 50
BATCH_TIMEOUT_SECONDS = 60
SINGLE_TIMEOUT_SECONDS = 20


def _warn_missing_analyzer(exe_path: Path):
    global _analyzer_missing_warned
    if not _analyzer_missing_warned:
        print(
            f"[WARN] C# complexity analyzer not found at {exe_path}; C# "
            "cyclomatic complexity will be skipped. Build it with "
            "utils/C#/ComplexityAnalyzer/BuildAndCompile.cmd",
            file=sys.stderr,
        )
        _analyzer_missing_warned = True


def _analyzer_path():
    """
    Locate the built analyzer, or None.

    `dotnet build -c Release -r win-x64` writes it to win-x64/, while
    `dotnet publish` writes it to win-x64/publish/. Accept either, so a
    publish-only build is not reported as missing.
    """
    root = Path(__file__).parent.parent.parent.parent / "utils" / "C#"
    base = root / "ComplexityAnalyzer" / "bin" / "Release" / "net9.0" / "win-x64"
    for candidate in (
        base / "ComplexityAnalyzer.exe",
        base / "publish" / "ComplexityAnalyzer.exe",
    ):
        if candidate.exists():
            return candidate
    return base / "ComplexityAnalyzer.exe"


def _run_cs_analyzer(exe_path: Path, file_paths):
    """
    Run the analyzer over one or more paths.

    Returns a result object with `returncode` and `stdout`; a launch failure
    yields a stub with returncode 1 rather than raising.
    """
    import subprocess

    paths = [str(p) for p in file_paths]
    timeout = BATCH_TIMEOUT_SECONDS if len(paths) > 1 else SINGLE_TIMEOUT_SECONDS
    try:
        return subprocess.run(
            [str(exe_path), *paths],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except Exception:
        pass

    class DummyProc:
        returncode = 1
        stdout = ""

    return DummyProc()


def _load_payload(proc):
    """Parse the analyzer's JSON object, or None if the call did not succeed."""
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
            # None means the analyzer could not analyse that file.
            continue
        for fn in functions:
            complexity = fn.get("Complexity", 0)
            if complexity >= threshold:
                results.append(
                    {
                        "name": fn.get("Name", "<anonymous>"),
                        "complexity": complexity,
                        "lineno": fn.get("LineNo"),
                        "endline": fn.get("EndLine"),
                        "file": str(file_path),
                        "threshold": threshold,
                        "severity": compute_severity(complexity, threshold),
                    }
                )
    return results


def analyze_cs_cyclomatic_complexity_batch(
    file_paths, threshold: int = 10, batch_size: int = DEFAULT_BATCH_SIZE
):
    """
    Analyze many C# files in a few analyzer invocations instead of one per file.

    Falls back to one call per file if a batch fails as a unit, so a single
    pathological file cannot cost the whole batch its results.
    """
    exe_path = _analyzer_path()
    if not exe_path.exists():
        _warn_missing_analyzer(exe_path)
        return []

    paths = [Path(p) for p in file_paths]
    results = []

    for start in range(0, len(paths), batch_size):
        batch = paths[start : start + batch_size]
        payload = _load_payload(_run_cs_analyzer(exe_path, batch))

        if payload is None and len(batch) > 1:
            for single in batch:
                single_payload = _load_payload(_run_cs_analyzer(exe_path, [single]))
                if single_payload:
                    results.extend(_findings(single_payload, threshold))
            continue

        if payload:
            results.extend(_findings(payload, threshold))

    return results


def analyze_cs_cyclomatic_complexity(file_path: Path, threshold: int = 10):
    """
    Analyze cyclomatic complexity of a single C# file.

    Kept for callers that work file by file; a scan uses the batch entry point.
    """
    return analyze_cs_cyclomatic_complexity_batch([file_path], threshold)
