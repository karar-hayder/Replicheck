import sys
from pathlib import Path

from replicheck.utils import compute_severity

# The analyzer is built, not committed (see README, "C# Support"). Warn once so
# that a missing build is visible instead of looking like "no complex methods".
_analyzer_missing_warned = False


def _warn_missing_analyzer(exe_path: Path):
    global _analyzer_missing_warned
    if not _analyzer_missing_warned:
        print(
            f"[WARN] C# complexity analyzer not found at {exe_path}; C# "
            "cyclomatic complexity will be skipped. Build it with "
            "utils/C#/ComplexityAnalyzer/BuildAndCompile.bash",
            file=sys.stderr,
        )
        _analyzer_missing_warned = True


def _run_cs_analyzer(exe_path: Path, file_path: Path):
    import subprocess

    try:
        proc = subprocess.run(
            [str(exe_path), str(file_path)],
            capture_output=True,
            text=True,
            timeout=20,
        )
        return proc
    except Exception:

        class DummyProc:
            returncode = 1
            stdout = ""

        return DummyProc()


def _parse_cs_complexity_output(proc, file_path, threshold):
    import json

    results = []
    if getattr(proc, "returncode", 1) != 0:
        return []
    try:
        functions = json.loads(proc.stdout)
    except Exception:
        return []
    for fn in functions:
        if fn.get("Complexity", 0) >= threshold:
            results.append(
                {
                    "name": fn.get("Name", "<anonymous>"),
                    "complexity": fn.get("Complexity"),
                    "lineno": fn.get("LineNo"),
                    "endline": fn.get("EndLine"),
                    "file": str(file_path),
                    "threshold": threshold,
                    "severity": compute_severity(fn.get("Complexity", 0), threshold),
                }
            )
    return results


def analyze_cs_cyclomatic_complexity(file_path: Path, threshold: int = 10):
    """
    Analyze cyclomatic complexity of a C# file using the compiled ComplexityAnalyzer.exe.
    """
    from pathlib import Path

    exe_path = (
        Path(__file__).parent.parent.parent.parent
        / "utils"
        / "C#"
        / "ComplexityAnalyzer"
        / "bin"
        / "Release"
        / "net9.0"
        / "win-x64"
        / "ComplexityAnalyzer.exe"
    )
    try:
        if not exe_path.exists():
            _warn_missing_analyzer(exe_path)
            return []
        proc = _run_cs_analyzer(exe_path, file_path)
        return _parse_cs_complexity_output(proc, file_path, threshold)
    except Exception:
        return []
