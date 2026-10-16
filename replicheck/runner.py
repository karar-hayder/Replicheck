from pathlib import Path

from replicheck.cache import CACHE_FILENAME, ScanCache
from replicheck.parser import CodeParser
from replicheck.reporter import Reporter
from replicheck.tools.bugNsafety.BNS import BugNSafetyAnalyzer
from replicheck.tools.CyclomaticComplexity.CCA import CyclomaticComplexityAnalyzer
from replicheck.tools.Duplication.Duplication import DuplicateDetector
from replicheck.tools.flake8_runner import (
    BUG_SAFETY_CODES,
    UNUSED_CODES,
    run_flake8_for_scan,
)
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

        if getattr(self, "full_scan", False):
            # An explicit request for a complete scan overrides the opt-in fast
            # paths: no cache, and every flake8 code a detector needs.
            self.cache = False
            self.flake8_codes = None

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

    def _collect_large_files(self, files) -> list:
        """Every file over the threshold, largest first, before any top-N cut."""
        detector = LargeFileDetector()
        detector.find_large_files(
            files, token_threshold=self.large_file_threshold, top_n=None
        )
        return detector.results

    def analyze_large_files(self, files) -> list:
        large_files = self._collect_large_files(files)
        if self.top_n_large > 0:
            large_files = large_files[: self.top_n_large]
        return large_files

    def _collect_large_classes(self, files) -> list:
        """Every class over the threshold, largest first, before any top-N cut."""
        detector = LargeClassDetector()
        detector.find_large_classes(
            files, token_threshold=self.large_class_threshold, top_n=None
        )
        return detector.results

    def analyze_large_classes(self, files) -> list:
        large_classes = self._collect_large_classes(files)
        if self.top_n_large > 0:
            large_classes = large_classes[: self.top_n_large]
        return large_classes

    def analyze_unused_imports_vars(self, files, findings=None):
        # Use UnusedCodeDetector from Unused.py instead of old function
        detector = UnusedCodeDetector()
        detector.find_unused(
            files,
            ignore_dirs=self.ignore_dirs if hasattr(self, "ignore_dirs") else None,
            findings=findings,
        )
        return detector.results

    def analyze_bugs_and_safety(self, files, findings=None):
        """
        Analyze for bugs and safety issues using BugNSafetyAnalyzer.
        Only runs if BugNSafetyAnalyzer is available.
        """
        if BugNSafetyAnalyzer is None:
            return []
        analyzer = BugNSafetyAnalyzer(files, findings=findings)
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

    # Result groups that belong to a single file, and so can be cached and
    # reused. Duplicate groups are deliberately absent: they are cross-file.
    CACHED_GROUPS = (
        "blocks",
        "complexity",
        "large_files",
        "large_classes",
        "unused",
        "todo",
        "bns",
    )

    @staticmethod
    def _empty_groups():
        return {group: [] for group in ReplicheckRunner.CACHED_GROUPS}

    def _extensions_set(self) -> set:
        if self.extensions is None:
            return {".py", ".js", ".jsx", ".cs", ".ts", ".tsx"}
        return {e if e.startswith(".") else f".{e}" for e in self.extensions}

    def _flake8_codes(self) -> str:
        """The codes flake8 is asked for; defaults to every code a detector needs."""
        return getattr(self, "flake8_codes", None) or ",".join(
            UNUSED_CODES + BUG_SAFETY_CODES
        )

    def _open_cache(self, extensions_set):
        """A loaded cache, or None when caching was not asked for."""
        if not getattr(self, "cache", False):
            return None
        cache_file = getattr(self, "cache_file", None) or (self.path / CACHE_FILENAME)
        cache = ScanCache(
            cache_file,
            self.path,
            {
                "min_size": self.min_size,
                "complexity_threshold": self.complexity_threshold,
                "large_file_threshold": self.large_file_threshold,
                "large_class_threshold": self.large_class_threshold,
                "flake8_codes": self._flake8_codes(),
                "extensions": sorted(extensions_set),
            },
        )
        cache.load()
        return cache

    def _split_cached(self, files, cache):
        """(reused artifacts, files still needing analysis)."""
        reused = self._empty_groups()
        fresh = []
        for file_path in files:
            artifacts = cache.get(file_path)
            if artifacts is None:
                fresh.append(file_path)
                continue
            for group in self.CACHED_GROUPS:
                values = artifacts.get(group)
                if values:
                    reused[group].extend(values)
        return reused, fresh

    def _analyse_files(self, files):
        """Run every detector over `files`, grouped by which file produced what."""
        produced = self._empty_groups()
        if not files:
            return produced

        produced["blocks"] = self.parse_code_files(files, CodeParser())
        print("Analyzing code blocks...")

        # One flake8 pass serves both the unused-import and bug&safety
        # detectors. Running them separately made flake8 parse every file
        # twice, which was the dominant cost of a scan.
        unused_findings, bug_safety_findings = run_flake8_for_scan(
            files,
            ignore_dirs=self.ignore_dirs if hasattr(self, "ignore_dirs") else None,
            codes=self._flake8_codes(),
        )

        produced["complexity"] = self.analyze_complexity(files)
        produced["large_files"] = self._collect_large_files(files)
        produced["large_classes"] = self._collect_large_classes(files)
        produced["unused"] = self.analyze_unused_imports_vars(
            files, findings=unused_findings
        )

        todo_fixme_detector = TodoFixmeDetector()
        todo_fixme_detector.find_todo_fixme_comments(files)
        produced["todo"] = todo_fixme_detector.results

        produced["bns"] = self.analyze_bugs_and_safety(
            files, findings=bug_safety_findings
        )
        return produced

    @staticmethod
    def _item_file(item):
        """The file a finding or block belongs to."""
        location = item.get("location")
        if isinstance(location, dict):
            return location.get("file")
        return item.get("file")

    def _store(self, cache, files, produced):
        """Record each analysed file's own results for the next run to reuse."""
        per_file = {str(f): self._empty_groups() for f in files}
        for group in self.CACHED_GROUPS:
            for item in produced.get(group, []):
                key = self._item_file(item)
                if key in per_file:
                    per_file[key][group].append(item)
        for file_path in files:
            cache.put(file_path, per_file[str(file_path)])

    def _report(self, reused, produced):
        """Merge reused and fresh results, then write the report."""
        merged = {}
        for group in self.CACHED_GROUPS:
            values = list(reused.get(group, [])) + list(produced.get(group, []))
            if group in ("large_files", "large_classes"):
                # Collected untruncated so the cache holds every file's own
                # facts; the top-N cut belongs here, after the merge.
                values.sort(key=lambda x: x["token_count"], reverse=True)
                if self.top_n_large > 0:
                    values = values[: self.top_n_large]
            merged[group] = values

        detector = DuplicateDetector(
            min_similarity=self.min_similarity, min_size=self.min_size
        )
        duplicates = detector.find_duplicates(merged["blocks"])

        reporter = Reporter(output_format=self.output_format)
        output_path = Path(self.output_file) if self.output_file else None
        reporter.generate_report(
            output_file=output_path,
            duplicates=duplicates,
            complexity_results=merged["complexity"],
            large_files=merged["large_files"],
            large_classes=merged["large_classes"],
            unused=merged["unused"],
            todo_fixme=merged["todo"],
            bns_results=merged["bns"],
        )
        return 0

    def run(self) -> int:
        """
        Run the full Replicheck analysis and reporting pipeline.
        Returns 0 on success, 1 on error.
        """
        try:
            if not self.path.exists():
                print("Error: Path does not exist")
                return 1

            extensions_set = self._extensions_set()

            print("Finding files...")
            files = find_files(
                self.path, extensions=extensions_set, ignore_dirs=self.ignore_dirs
            )
            print(f"Found {len(files)} files to analyze")

            cache = self._open_cache(extensions_set)
            if cache is None:
                reused = self._empty_groups()
                fresh = files
            else:
                reused, fresh = self._split_cached(files, cache)
                print(
                    f"Cache: reusing {cache.hits} unchanged file(s), "
                    f"analysing {len(fresh)}"
                )

            produced = self._analyse_files(fresh)

            if cache is not None:
                self._store(cache, fresh, produced)
                cache.prune_to(files)
                cache.save()

            return self._report(reused, produced)

        except Exception:
            print("Error: An unexpected error occurred.")
            return 1
