class UnusedCodeDetector:
    """
    Detect unused imports and variables in code files.
    Currently supports Python via flake8, with room for other languages.
    """

    def __init__(self):
        self.results = []

    def find_unused(self, files, ignore_dirs=None):
        """
        Find unused imports and variables in the given files.
        Sets self.results to a list of findings.
        """
        py_files = [f for f in files if str(f).lower().endswith(".py")]
        # Room for other languages: js_files, ts_files, cs_files, etc.

        results = []
        if py_files:
            results.extend(self._find_unused_python(py_files, ignore_dirs=ignore_dirs))
        # TODO: Add support for JS/TS/CS unused detection here in the future.
        self.results = results

    def _find_unused_python(self, files, ignore_dirs=None):
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

        if not files:
            return []

        cmd = [sys.executable, "-m", "flake8", "--select=F401,F841"]
        if ignore_dirs:
            for d in ignore_dirs:
                cmd.append(f"--exclude={d}")
        cmd.extend([str(f) for f in files])

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
