import concurrent.futures
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import utils_python as UP


def _filter_files_outside_ignored_dirs(
    files: List[Path], ignore_dirs: Optional[List[str]]
) -> List[Path]:
    """
    Helper to filter out files that are inside any of the ignore_dirs.
    """
    if not ignore_dirs:
        return files
    ignore_dirs_abs = [os.path.abspath(str(d)) for d in ignore_dirs]
    filtered = []
    for f in files:
        f_abs = os.path.abspath(str(f))
        if not any(os.path.commonpath([f_abs, d]) == d for d in ignore_dirs_abs):
            filtered.append(f)
    return filtered


class BugNSafetyAnalyzer:
    """
    Analyze code files for bugs and safety issues.
    Currently supports Python, JS/TS/JSX/TSX, and C# (stub).
    """

    def __init__(self, files: List[Path], ignore_dirs: Optional[List[str]] = None):
        self.files = files
        self.ignore_dirs = ignore_dirs
        self.results = []

    def analyze(self) -> None:
        """
        Run bug and safety analysis on all files.
        Returns a list of findings.
        """
        results = []
        filtered_files = _filter_files_outside_ignored_dirs(
            self.files, self.ignore_dirs
        )
        py_files = [f for f in filtered_files if str(f).lower().endswith(".py")]
        js_files = [
            f
            for f in filtered_files
            if str(f).lower().endswith((".js", ".jsx", ".ts", ".tsx"))
        ]
        cs_files = [f for f in filtered_files if str(f).lower().endswith(".cs")]

        # Parallelize the analysis of different language groups
        tasks = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            if py_files:
                tasks.append(executor.submit(self._analyze_python, py_files))
            if js_files:
                tasks.append(executor.submit(self._analyze_js, js_files))
            if cs_files:
                tasks.append(executor.submit(self._analyze_cs, cs_files))

            for future in concurrent.futures.as_completed(tasks):
                findings = future.result()
                if findings:
                    results.extend(findings)
        self.results = results

    def _analyze_python(self, files: List[Path]) -> List[Dict[str, Any]]:
        """
        Analyze Python files for bugs and safety issues.
        Uses flake8 (with bugbear, bandit, eradicate) for static analysis.
        """
        # Use the unified flake8 runner from utils_python.py
        return UP._run_flake8_all(files, ignore_dirs=self.ignore_dirs)

    def _analyze_js(self, files: List[Path]) -> List[Dict[str, Any]]:
        """
        Analyze JS/TS/JSX/TSX files for bugs and safety issues.
        Stub for future extension.
        """
        findings = []
        # TODO: Integrate ESLint or custom static analysis for JS/TS
        return findings

    def _analyze_cs(self, files: List[Path]) -> List[Dict[str, Any]]:
        """
        Analyze C# files for bugs and safety issues.
        Stub for future extension.
        """
        findings = []
        # TODO: Integrate Roslyn analyzers or custom static analysis for C#
        return findings
