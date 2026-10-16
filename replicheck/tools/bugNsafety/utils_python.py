from pathlib import Path
from typing import Any, Dict, List, Optional

from replicheck.tools.flake8_runner import run_flake8


def _run_flake8_all(
    paths: List[Path], ignore_dirs: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Run flake8 once with all needed plugins (bugbear, bandit, eradicate) and parse all results.

    Returns a list of dicts with file, line, code, and message for all findings.
    """
    if not paths:
        return []

    return run_flake8(paths, select="B,S,E800", ignore_dirs=ignore_dirs)
