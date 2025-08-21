import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def _run_flake8_all(
    paths: List[Path], ignore_dirs: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Run flake8 once with all needed plugins (bugbear, bandit, eradicate) and parse all results.

    Returns a list of dicts with file, line, code, and message for all findings.
    """
    if not paths:
        return []

    # Select all relevant codes in one run
    select_codes = ["B", "S", "E800"]
    cmd = [sys.executable, "-m", "flake8", f"--select={','.join(select_codes)}"]
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

    findings = []
    # flake8 output: path:line:col: code message
    pattern = re.compile(r"^(.*?):(\d+):\d+:\s+([BSE]\d+)\s+(.*)$")
    for line in result.stdout.splitlines():
        m = pattern.match(line)
        if m:
            findings.append(
                {
                    "file": m.group(1),
                    "line": int(m.group(2)),
                    "code": m.group(3),
                    "message": m.group(4).strip(),
                }
            )
    return findings
