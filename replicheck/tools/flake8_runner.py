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
        # normal. Exit 1 with nothing on stdout means it never really ran: a
        # missing install exits 1 with only a message on stderr, which would
        # otherwise be indistinguishable from "no findings".
        returncode = getattr(result, "returncode", 0)
        stdout = result.stdout or ""
        stderr = getattr(result, "stderr", "") or ""
        failed = returncode not in (0, 1) or (returncode == 1 and not stdout.strip())
        if failed:
            print(
                f"[WARN] flake8 exited {returncode} over {len(chunk)} file(s): "
                f"{stderr.strip()[:200]}",
                file=sys.stderr,
            )

        for line in stdout.splitlines():
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


# The codes the unused-import and bug&safety detectors need. They used to run
# flake8 separately over the same file list, so every file was parsed twice.
UNUSED_CODES = ("F401", "F841")
BUG_SAFETY_CODES = ("B", "S", "E800")


def split_findings(findings):
    """
    Partition flake8 findings into (unused, bug_safety) groups.

    B and S are selected by prefix, so any code starting with either letter
    belongs to bug&safety; E800 is eradicate's commented-out-code check.
    """
    unused = []
    bug_safety = []
    for finding in findings:
        code = finding["code"]
        if code in UNUSED_CODES:
            unused.append(finding)
        elif code in BUG_SAFETY_CODES or code[:1] in ("B", "S"):
            bug_safety.append(finding)
    return unused, bug_safety


def run_flake8_for_scan(paths, ignore_dirs=None, budget=PATH_BUDGET_CHARS):
    """
    Run flake8 once for every code both detectors need, and split the result.

    Only Python files are passed. flake8 ignores anything else, but handing it a
    large non-Python tree still costs a process start-up per chunk: a scan of a
    JavaScript-only repository was spending half its time in flake8 runs that
    could not produce a single finding. With no Python files, flake8 is not
    invoked at all.

    Returns (unused_findings, bug_safety_findings). One pass instead of two,
    which halves the dominant cost of a scan.
    """
    python_paths = [p for p in paths if str(p).lower().endswith(".py")]
    if not python_paths:
        return [], []

    findings = run_flake8(
        python_paths,
        select=",".join(UNUSED_CODES + BUG_SAFETY_CODES),
        ignore_dirs=ignore_dirs,
        budget=budget,
    )
    return split_findings(findings)
