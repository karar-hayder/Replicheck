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
        if js_files:
            results.extend(self._analyze_js_batch(js_files))
        if cs_files:
            results.extend(self._analyze_cs_batch(cs_files))
        self.results = results

    def _analyze_python(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Analyze cyclomatic complexity of a Python file.
        """
        from .py_utils import analyze_py_cyclomatic_complexity

        return analyze_py_cyclomatic_complexity(file_path, self.threshold)

    def _analyze_js_batch(self, files: List[Path]) -> List[Dict[str, Any]]:
        """
        Analyze all JS/TS/JSX/TSX files in a few Node invocations.

        Node start-up is ~223 ms per invocation and does not depend on file
        size, so calling it once per file made a large JS repository take
        minutes. Batching amortises that across files.
        """
        from .js_utils import analyze_js_cyclomatic_complexity_batch

        return analyze_js_cyclomatic_complexity_batch(files, self.threshold)

    def _analyze_js(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Analyze cyclomatic complexity of a JS/TS/JSX/TSX file.
        """
        from .js_utils import analyze_js_cyclomatic_complexity

        return analyze_js_cyclomatic_complexity(file_path, self.threshold)

    def _analyze_cs_batch(self, files: List[Path]) -> List[Dict[str, Any]]:
        """
        Analyze all C# files in a few analyzer invocations.

        The analyzer's start-up is ~214 ms per invocation and does not depend
        on file size, so calling it once per file made a large C# repository
        take minutes.
        """
        from .cs_utils import analyze_cs_cyclomatic_complexity_batch

        return analyze_cs_cyclomatic_complexity_batch(files, self.threshold)

    def _analyze_cs(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Analyze cyclomatic complexity of a C# file.
        """
        from .cs_utils import analyze_cs_cyclomatic_complexity

        return analyze_cs_cyclomatic_complexity(file_path, self.threshold)
