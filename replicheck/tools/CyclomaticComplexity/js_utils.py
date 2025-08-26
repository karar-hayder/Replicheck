from pathlib import Path

from replicheck.utils import compute_severity


def _run_node_helper(helper_path: Path, file_path: Path):
    import subprocess

    try:
        proc = subprocess.run(
            ["node", str(helper_path), str(file_path)],
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


def _parse_js_complexity_output(proc, file_path, threshold):
    import json

    results = []
    if getattr(proc, "returncode", 1) != 0:
        return []
    try:
        functions = json.loads(proc.stdout)
    except Exception:
        return []
    for fn in functions:
        if fn.get("complexity", 0) >= threshold:
            results.append(
                {
                    "name": fn.get("name", "<anonymous>"),
                    "complexity": fn.get("complexity"),
                    "lineno": fn.get("lineno"),
                    "endline": fn.get("endline"),
                    "file": str(file_path),
                    "threshold": threshold,
                    "severity": compute_severity(fn.get("complexity", 0), threshold),
                }
            )
    return results


def analyze_js_cyclomatic_complexity(file_path: Path, threshold: int = 10):
    """
    Analyze cyclomatic complexity of a JS file using typhonjs-escomplex via Node.js helper script.
    """
    from pathlib import Path

    helper_path = Path(__file__).parent.parent.parent.parent / "utils" / "helpers.js"
    try:
        proc = _run_node_helper(helper_path, file_path)
        return _parse_js_complexity_output(proc, file_path, threshold)
    except Exception:
        return []
