"""
Shared flake8 invocation for the detectors that shell out to it.

flake8 is given explicit file paths rather than a directory so that the ignore
rules the caller already applied are respected. A single command line listing
every file in a large repository exceeds the operating system's argument limit
(32767 characters on Windows), which fails before flake8 starts. Because the
failure was swallowed, the affected detectors silently reported nothing.

The file list is therefore split into chunks that fit, and the results are
concatenated. A chunk that fails is reported on stderr instead of disappearing.
"""

import re
import subprocess
import sys
from typing import Any, Dict, Iterable, List, Optional

# Windows caps the entire command line at 32767 characters, and the interpreter
# path plus the flake8 flags take a slice of that. The paths get a smaller
# budget with a wide margin. Other platforms allow far more, so chunking is
# harmless there.
PATH_BUDGET_CHARS = 16000

_FINDING_PATTERN = re.compile(r"^(.*?):(\d+):\d+:\s+([A-Z]+\d+)\s+(.*)$")


def chunk_paths(paths: Iterable, budget: int = PATH_BUDGET_CHARS) -> List[List[str]]:
    """
    Split paths into groups whose combined command-line length fits `budget`.

    A single path longer than the budget still gets its own chunk rather than
    being dropped, so nothing is ever silently skipped.
    """
    chunks: List[List[str]] = []
    current: List[str] = []
    length = 0
    for path in paths:
        text = str(path)
        # +1 accounts for the space separating this argument from the previous.
        if current and length + len(text) + 1 > budget:
            chunks.append(current)
            current = []
            length = 0
        current.append(text)
        length += len(text) + 1
    if current:
        chunks.append(current)
    return chunks


def _build_command(paths, select: str, ignore_dirs: Optional[List[str]]):
    cmd = [sys.executable, "-m", "flake8", f"--select={select}"]
    for directory in ignore_dirs or ():
        cmd.append(f"--exclude={directory}")
    cmd.extend(paths)
    return cmd


def run_flake8(
    paths,
    select: str,
    ignore_dirs: Optional[List[str]] = None,
    budget: int = PATH_BUDGET_CHARS,
) -> List[Dict[str, Any]]:
    """
    Run flake8 over `paths` and return findings as dicts with file, line, code
    and message.

    The file list is chunked so that no command line exceeds the OS limit. A
    chunk that cannot run is reported on stderr and skipped, so a partial
    failure is visible rather than silently producing an empty result.
    """
    findings: List[Dict[str, Any]] = []

    for chunk in chunk_paths(paths, budget):
        try:
            result = subprocess.run(
                _build_command(chunk, select, ignore_dirs),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
                check=False,
            )
        except Exception as exc:  # noqa: BLE001 - one bad chunk must not abort the scan
            print(
                f"[WARN] flake8 could not run over {len(chunk)} file(s): {exc}",
                file=sys.stderr,
            )
            continue

        # flake8 exits 0 when clean and 1 when it reports findings; both are
        # normal. Anything else means the chunk did not really run.
        returncode = getattr(result, "returncode", 0)
        if returncode not in (0, 1):
            stderr = getattr(result, "stderr", "") or ""
            print(
                f"[WARN] flake8 exited {returncode} over {len(chunk)} file(s): "
                f"{stderr.strip()[:200]}",
                file=sys.stderr,
            )

        for line in (result.stdout or "").splitlines():
            match = _FINDING_PATTERN.match(line)
            if match:
                findings.append(
                    {
                        "file": match.group(1),
                        "line": int(match.group(2)),
                        "code": match.group(3),
                        "message": match.group(4).strip(),
                    }
                )

    return findings
