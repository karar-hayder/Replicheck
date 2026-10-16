class UnusedCodeDetector:
    """
    Detect unused imports and variables in code files.
    Currently supports Python via flake8, with room for other languages.
    """

    def __init__(self):
        self.results = []

    def find_unused(self, files, ignore_dirs=None, findings=None):
        """
        Find unused imports and variables in the given files.
        Sets self.results to a list of findings.

        Args:
            files: Files to analyze.
            ignore_dirs: Directories to ignore, used only when running flake8 here.
            findings: Pre-computed findings from a shared flake8 pass. When
                given, flake8 is not invoked again.
        """
        py_files = [f for f in files if str(f).lower().endswith(".py")]
        # Room for other languages: js_files, ts_files, cs_files, etc.

        if findings is not None:
            # A scan already ran flake8 over every file; reuse that result.
            self.results = list(findings)
            return

        results = []
        if py_files:
            results.extend(self._find_unused_python(py_files, ignore_dirs=ignore_dirs))
        # TODO: Add support for JS/TS/CS unused detection here in the future.
        self.results = results

    def _find_unused_python(self, files, ignore_dirs=None):
        """
        Run flake8 on the given list of paths and return a list of unused imports and variables.

        Args:
            files (list[str or Path]): List of files to analyze.
            ignore_dirs (list[str], optional): Directories to ignore.

        Returns:
            List[dict]: Each dict contains file, line, code, and message for each unused import/var.
        """
        from replicheck.tools.flake8_runner import run_flake8

        if not files:
            return []

        return run_flake8(files, select="F401,F841", ignore_dirs=ignore_dirs)
