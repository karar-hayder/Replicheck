from pathlib import Path

from replicheck.parser import CodeParser
from replicheck.reporter import Reporter
from replicheck.tools.bugNsafety.BNS import BugNSafetyAnalyzer
from replicheck.tools.CyclomaticComplexity.CCA import CyclomaticComplexityAnalyzer
from replicheck.tools.Duplication.Duplication import DuplicateDetector
from replicheck.tools.LargeDetection.LC import LargeClassDetector
from replicheck.tools.LargeDetection.LF import LargeFileDetector
from replicheck.tools.TodoFixme.TDFM import TodoFixmeDetector
from replicheck.tools.Unused.Unused import UnusedCodeDetector
from replicheck.utils import find_files


class ReplicheckRunner:
    """
    Encapsulates the main logic for running Replicheck, using arguments similar to main.py.
    """

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            if k == "path":
                self.path = Path(v)
            else:
                setattr(self, k, v)

    def analyze_complexity(self, files):
        """
        Use CyclomaticComplexityAnalyzer from CCA.py to analyze all files.
        """
        if CyclomaticComplexityAnalyzer is None:
            return []
        analyzer = CyclomaticComplexityAnalyzer(
            files, threshold=self.complexity_threshold
        )
        analyzer.analyze()
        # Optionally, add threshold to each result for compatibility
        for result in analyzer.results:
            result["threshold"] = self.complexity_threshold
        return analyzer.results

    def analyze_large_files(self, files) -> list:
        detector = LargeFileDetector()
        detector.find_large_files(
            files, token_threshold=self.large_file_threshold, top_n=self.top_n_large
        )
        large_files = detector.results
        if self.top_n_large > 0:
            large_files = large_files[: self.top_n_large]
        return large_files

    def analyze_large_classes(self, files) -> list:
        detector = LargeClassDetector()
        detector.find_large_classes(
            files,
            token_threshold=self.large_class_threshold,
            top_n=self.top_n_large,
        )
        large_classes = detector.results
        if self.top_n_large > 0:
            large_classes = large_classes[: self.top_n_large]
        return large_classes

    def analyze_unused_imports_vars(self, files):
        # Use UnusedCodeDetector from Unused.py instead of old function
        detector = UnusedCodeDetector()
        detector.find_unused(
            files,
            ignore_dirs=self.ignore_dirs if hasattr(self, "ignore_dirs") else None,
        )
        return detector.results

    def analyze_bugs_and_safety(self, files):
        """
        Analyze for bugs and safety issues using BugNSafetyAnalyzer.
        Only runs if BugNSafetyAnalyzer is available.
        """
        if BugNSafetyAnalyzer is None:
            return []
        analyzer = BugNSafetyAnalyzer(files)
        analyzer.analyze()
        return analyzer.results

    def parse_code_files(self, files, parser):
        print("Parsing files...")
        code_blocks = []
        for file in files:
            try:
                blocks = parser.parse_file(file)
                code_blocks.extend(blocks)
            except Exception:
                pass  # Suppress all parsing errors, no print
        print(f"Found {len(code_blocks)} code blocks to analyze")
        return code_blocks

    def run(self) -> int:
        """
        Run the full Replicheck analysis and reporting pipeline.
        Returns 0 on success, 1 on error.
        """
        try:
            if not self.path.exists():
                print("Error: Path does not exist")
                return 1

            parser = CodeParser()
            detector = DuplicateDetector(
                min_similarity=self.min_similarity, min_size=self.min_size
            )
            reporter = Reporter(output_format=self.output_format)

            if self.extensions is None:
                extensions_set = {".py", ".js", ".jsx", ".cs", ".ts", ".tsx"}
            else:
                extensions_set = {
                    e if e.startswith(".") else f".{e}" for e in self.extensions
                }

            print("Finding files...")
            files = find_files(
                self.path, extensions=extensions_set, ignore_dirs=self.ignore_dirs
            )
            print(f"Found {len(files)} files to analyze")

            code_blocks = self.parse_code_files(files, parser)
            print("Analyzing code blocks...")

            high_complexity = self.analyze_complexity(files)
            large_files = self.analyze_large_files(files)
            large_classes = self.analyze_large_classes(files)
            duplicates = detector.find_duplicates(code_blocks)
            unused_imports_vars = self.analyze_unused_imports_vars(files)

            # Use TodoFixmeDetector instead of old function
            todo_fixme_detector = TodoFixmeDetector()
            todo_fixme_detector.find_todo_fixme_comments(files)
            todo_fixme_comments = todo_fixme_detector.results

            # --- Bugs and Safety Issues ---
            bns_results = self.analyze_bugs_and_safety(files)

            output_path = Path(self.output_file) if self.output_file else None
            reporter.generate_report(
                output_file=output_path,
                duplicates=duplicates,
                complexity_results=high_complexity,
                large_files=large_files,
                large_classes=large_classes,
                unused=unused_imports_vars,
                todo_fixme=todo_fixme_comments,
                bns_results=bns_results,
            )

            return 0

        except Exception:
            print("Error: An unexpected error occurred.")
            return 1
