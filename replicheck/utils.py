"""
Helper functions for code analysis.
"""

import hashlib
from pathlib import Path
from typing import List, Optional, Set


def calculate_similarity(tokens1: List[str], tokens2: List[str]) -> float:
    """
    Calculate similarity between two token lists using Jaccard similarity.
    Much faster than SequenceMatcher for code comparison.
    Should handle non-list input gracefully (should not raise).
    """
    if not isinstance(tokens1, list) or not isinstance(tokens2, list):
        return 0.0
    set1 = set(tokens1)
    set2 = set(tokens2)
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union else 0.0


def get_file_hash(file_path: Path) -> Optional[str]:
    """
    Calculate SHA-256 hash of a file.
    Returns None if the file does not exist or cannot be read.
    """
    if not file_path.exists():
        return None
    sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception:
        return None


def _get_ignored_dirs(ignore_dirs: Optional[List[str]] = None) -> set:
    venv_dirs = {".venv", "venv", "env", "ENV"}
    if ignore_dirs:
        venv_dirs.update(ignore_dirs)
    return venv_dirs


def _is_in_ignored_dirs(file_path: Path, ignored_dirs: set) -> bool:
    return any(ignored in file_path.parts for ignored in ignored_dirs)


def find_files(
    directory: Path,
    extensions: Optional[Set[str]] = None,
    ignore_dirs: Optional[List[str]] = None,
) -> List[Path]:
    """
    Find all files with specified extensions in a directory.
    Ignores specified directories and virtual environment folders.
    """
    if extensions is None:
        extensions = {".py"}
    files = []
    ignored_dirs = _get_ignored_dirs(ignore_dirs)
    for ext in extensions:
        for file_path in directory.glob(f"**/*{ext}"):
            if not _is_in_ignored_dirs(file_path, ignored_dirs):
                files.append(file_path)
    return files


def compute_severity(value, threshold):
    """
    Compute severity level and emoji based on how much value exceeds threshold.
    Returns a string like 'Low 🟢', 'Medium 🟡', 'High 🟠', 'Critical 🔴'.
    """
    if not (isinstance(value, (int, float)) and isinstance(threshold, (int, float))):
        return "None"
    if threshold == 0 or value < 0 or threshold < 0:
        return "None"
    ratio = value / threshold
    if ratio >= 3:
        return "Critical 🔴"
    elif ratio >= 2:
        return "High 🟠"
    elif ratio >= 1.5:
        return "Medium 🟡"
    elif ratio >= 1:
        return "Low 🟢"
    else:
        return "None"


# --- TODO/FIXME Comments ---


def _find_todo_fixme_in_python(file_path, content, py_pattern, results):
    for lineno, line in enumerate(content.splitlines(), 1):
        match = py_pattern.search(line)
        if match:
            results.append(
                {
                    "file": str(file_path),
                    "line": lineno,
                    "type": match.group(1).upper(),
                    "text": match.group(3).strip(),
                }
            )


def _find_todo_fixme_in_treesitter(file_path, content, ext, ts_languages, results):
    import re

    from replicheck.parser import get_language, get_parser

    language_name = ts_languages[ext]
    parser = get_parser(language_name)
    language = get_language(language_name)
    tree = parser.parse(bytes(content, "utf-8"))
    root = tree.root_node
    query = language.query(
        """
        (comment) @comment
    """
    )
    captures = query.captures(root)
    for node, _ in captures:
        comment_text = content[node.start_byte : node.end_byte]
        match = re.search(r"(TODO|FIXME)(:|\b)(.*)", comment_text, re.IGNORECASE)
        if match:
            results.append(
                {
                    "file": str(file_path),
                    "line": node.start_point[0] + 1,
                    "type": match.group(1).upper(),
                    "text": match.group(3).strip(),
                }
            )


def find_todo_fixme_comments(files):
    """
    Scan files for TODO and FIXME comments.
    Uses tree-sitter for JS/TS/TSX/JSX/C# and regex for Python.
    Returns list of dicts: file, line number, comment type, and comment text.
    """
    import re

    results = []
    py_pattern = re.compile(r"#.*?(TODO|FIXME)(:|\b)(.*)", re.IGNORECASE)
    ts_languages = {
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".cs": "csharp",
    }
    for file_path in files:
        ext = file_path.suffix.lower()
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            if ext == ".py":
                _find_todo_fixme_in_python(file_path, content, py_pattern, results)
            elif ext in ts_languages:
                _find_todo_fixme_in_treesitter(
                    file_path, content, ext, ts_languages, results
                )
        except Exception:
            pass
    return results


def find_flake8_unused(paths, ignore_dirs=None):
    """
    Run flake8 on the given list of paths and return a list of unused imports and variables.

    Args:
        paths (list[str or Path]): List of files to analyze.
        ignore_dirs (list[str], optional): Directories to ignore.

    Returns:
        List[dict]: Each dict contains file, line, code, and message for each unused import/var.
    """
    import re
    import subprocess
    import sys

    if not paths:
        return []

    cmd = [sys.executable, "-m", "flake8", "--select=F401,F841"]
    if ignore_dirs:
        for d in ignore_dirs:
            cmd.append(f"--exclude={d}")
    cmd.extend([str(p) for p in paths])

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            check=False,
        )
    except Exception:
        return []

    unused = []
    # flake8 output: path:line:col: code message
    pattern = re.compile(r"^(.*?):(\d+):\d+:\s+(F401|F841)\s+(.*)$")
    for line in result.stdout.splitlines():
        m = pattern.match(line)
        if m:
            unused.append(
                {
                    "file": m.group(1),
                    "line": int(m.group(2)),
                    "code": m.group(3),
                    "message": m.group(4).strip(),
                }
            )
    return unused
