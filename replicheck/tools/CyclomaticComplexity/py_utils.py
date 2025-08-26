from pathlib import Path

from replicheck.utils import compute_severity


def _read_file_content(file_path: Path, mode="r", encoding="utf-8"):
    with open(file_path, mode, encoding=encoding) as f:
        return f.read()


def _analyze_python_cyclomatic_complexity(code: str, file_path: Path, threshold: int):
    from radon.complexity import cc_visit

    results = []
    for block in cc_visit(code):
        if getattr(block, "complexity", 0) >= threshold:
            results.append(
                {
                    "name": getattr(block, "name", "<unknown>"),
                    "complexity": getattr(block, "complexity", 0),
                    "lineno": getattr(block, "lineno", None),
                    "endline": getattr(block, "endline", None),
                    "file": str(file_path),
                    "threshold": threshold,
                    "severity": compute_severity(
                        getattr(block, "complexity", 0), threshold
                    ),
                }
            )
    return results


def analyze_py_cyclomatic_complexity(file_path: Path, threshold: int = 10):
    """
    Analyze cyclomatic complexity of a Python file using radon.
    """
    try:
        code = _read_file_content(file_path)
        return _analyze_python_cyclomatic_complexity(code, file_path, threshold)
    except Exception:
        return []
