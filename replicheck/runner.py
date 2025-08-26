from pathlib import Path

from replicheck.parser import CodeParser
from replicheck.reporter import Reporter
from replicheck.tools.Duplication.Duplication import DuplicateDetector
from replicheck.utils import (
    analyze_cs_cyclomatic_complexity,
    analyze_cyclomatic_complexity,
    analyze_js_cyclomatic_complexity,
    find_files,
    find_flake8_unused,
    find_large_classes,
    find_large_files,
    find_todo_fixme_comments,
)

# --- Bugs and Safety Issues ---
try:
    from replicheck.tools.bugNsafety.BNS import BugNSafetyAnalyzer
except ImportError:
    BugNSafetyAnalyzer = None


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
        high_complexity = []
        for file in files:
            suffix = str(file).split(".")[-1].lower()
            if suffix == "py":
                for result in analyze_cyclomatic_complexity(
                    file, threshold=self.complexity_threshold
                ):
                    result["threshold"] = self.complexity_threshold
                    high_complexity.append(result)
            elif suffix in ["js", "jsx", "ts", "tsx"]:
                for result in analyze_js_cyclomatic_complexity(
                    file, threshold=self.complexity_threshold
                ):
                    result["threshold"] = self.complexity_threshold
                    high_complexity.append(result)
            elif suffix == "cs":
                for result in analyze_cs_cyclomatic_complexity(
                    file, threshold=self.complexity_threshold
                ):
                    result["threshold"] = self.complexity_threshold
                    high_complexity.append(result)
        return high_complexity

    def analyze_large_files(self, files):
        large_files = find_large_files(
            files, token_threshold=self.large_file_threshold, top_n=self.top_n_large
        )
        large_files = sorted(large_files, key=lambda x: x["token_count"], reverse=True)
        if self.top_n_large > 0:
            large_files = large_files[: self.top_n_large]
        return large_files

    def analyze_large_classes(self, files):
        large_classes = []
        for file in files:
            suffix = str(file).split(".")[-1].lower()
            if suffix in ["py", "js", "jsx", "cs", "ts", "tsx"]:
                large_classes.extend(
                    find_large_classes(
                        file,
                        token_threshold=self.large_class_threshold,
                        top_n=self.top_n_large,
                    )
                )
        large_classes = sorted(
            large_classes, key=lambda x: x["token_count"], reverse=True
        )
        if self.top_n_large > 0:
            large_classes = large_classes[: self.top_n_large]
        return large_classes

    def analyze_unused_imports_vars(self, files):
        # Only process Python files for now
        suffix_map = {
            ".py": [],
            ".js": [],
            ".jsx": [],
            ".ts": [],
            ".tsx": [],
            ".cs": [],
        }
        for f in files:
            lower = str(f).lower()
            for ext in suffix_map:
                if lower.endswith(ext):
                    suffix_map[ext].append(f)
                    break
        py_files = suffix_map[".py"]
        py_results = find_flake8_unused(py_files) if py_files else []
        return py_results

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
            todo_fixme_comments = find_todo_fixme_comments(files)

            # --- Bugs and Safety Issues ---
            bns_results = self.analyze_bugs_and_safety(files)

            output_path = Path(self.output_file) if self.output_file else None
            reporter.generate_report(
                duplicates,
                output_path,
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
