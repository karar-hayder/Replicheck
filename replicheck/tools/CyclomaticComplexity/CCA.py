# --- Cyclomatic Complexity Analysis ---

from pathlib import Path
from typing import Any, Dict, List


class CyclomaticComplexityAnalyzer:
    """
    Analyze code files for high cyclomatic complexity functions.
    Supports Python, JS/TS/JSX/TSX, and C#.
    """

    def __init__(self, files: List[Path], threshold: int = 10):
        self.files = files
        self.threshold = threshold
        self.results: List[Dict[str, Any]] = []

    def analyze(self) -> None:
        """
        Run cyclomatic complexity analysis on all files.
        Populates self.results with findings.
        """
        results = []
        py_files = [f for f in self.files if str(f).lower().endswith(".py")]
        js_files = [
            f
            for f in self.files
            if str(f).lower().endswith((".js", ".jsx", ".ts", ".tsx"))
        ]
        cs_files = [f for f in self.files if str(f).lower().endswith(".cs")]

        for f in py_files:
            results.extend(self._analyze_python(f))
        for f in js_files:
            results.extend(self._analyze_js(f))
        for f in cs_files:
            results.extend(self._analyze_cs(f))
        self.results = results

    def _analyze_python(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Analyze cyclomatic complexity of a Python file.
        """
        from .py_utils import analyze_py_cyclomatic_complexity

        return analyze_py_cyclomatic_complexity(file_path, self.threshold)

    def _analyze_js(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Analyze cyclomatic complexity of a JS/TS/JSX/TSX file.
        """
        from .js_utils import analyze_js_cyclomatic_complexity

        return analyze_js_cyclomatic_complexity(file_path, self.threshold)

    def _analyze_cs(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Analyze cyclomatic complexity of a C# file.
        """
        from .cs_utils import analyze_cs_cyclomatic_complexity

        return analyze_cs_cyclomatic_complexity(file_path, self.threshold)
