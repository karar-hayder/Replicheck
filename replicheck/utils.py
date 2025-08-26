"""
Helper functions for code analysis.
"""

import hashlib
from pathlib import Path
from typing import List, Optional, Set


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
