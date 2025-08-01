#!/usr/bin/env python3
"""
Replicheck - A tool for detecting code duplications in projects.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from replicheck.detector import DuplicateDetector
from replicheck.parser import CodeParser
from replicheck.reporter import Reporter
from replicheck.utils import (
    analyze_cs_cyclomatic_complexity,
    analyze_cyclomatic_complexity,
    analyze_js_cyclomatic_complexity,
    find_files,
    find_large_classes,
    find_large_files,
    find_todo_fixme_comments,
)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Replicheck - Detect code duplications in projects"
    )
    parser.add_argument(
        "--path",
        type=str,
        required=True,
        help="Path to the directory to analyze",
    )
    parser.add_argument(
        "--min-similarity",
        type=float,
        default=0.8,
        help="Minimum similarity threshold (0.0 to 1.0)",
    )
    parser.add_argument(
        "--min-size",
        type=int,
        default=50,
        help="Minimum size of code blocks to compare (in tokens)",
    )
    parser.add_argument(
        "--output-format",
        type=str,
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format (text, json, or markdown)",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        help="Path to output file (if not specified, prints to console)",
    )
    parser.add_argument(
        "--ignore-dirs",
        type=str,
        nargs="+",
        default=[
            ".git",
            ".venv",
            "venv",
            "env",
            "ENV",
            "build",
            "dist",
            "node_modules",
            "__pycache__",
            ".pytest_cache",
            "coverage",
            "vendor",
            "bower_components",
            ".vscode",
            ".idea",
            ".vs",
            ".next",
        ],
        help="Directories to ignore",
    )
    parser.add_argument(
        "--complexity-threshold",
        type=int,
        default=10,
        help="Cyclomatic complexity threshold to flag functions (default: 10)",
    )
    parser.add_argument(
        "--large-file-threshold",
        type=int,
        default=500,
        help="Token count threshold to flag large files (default: 500)",
    )
    parser.add_argument(
        "--large-class-threshold",
        type=int,
        default=300,
        help="Token count threshold to flag large classes (default: 300)",
    )
    parser.add_argument(
        "--top-n-large",
        type=int,
        default=10,
        help="Show only the top N largest files/classes (default: 10, 0=all)",
    )
    parser.add_argument(
        "--extensions",
        type=str,
        nargs="+",
        help="File extensions to include (default: .py, .js, .jsx, .cs, .ts, .tsx)",
    )
    return parser.parse_args()


def analyze_complexity(files, complexity_threshold):
    """Analyze cyclomatic complexity for all files."""
    high_complexity = []
    for file in files:
        suffix = str(file).split(".")[-1].lower()
        if suffix == "py":
            for result in analyze_cyclomatic_complexity(
                file, threshold=complexity_threshold
            ):
                result["threshold"] = complexity_threshold
                high_complexity.append(result)
        elif suffix in ["js", "jsx", "ts", "tsx"]:
            for result in analyze_js_cyclomatic_complexity(
                file, threshold=complexity_threshold
            ):
                result["threshold"] = complexity_threshold
                high_complexity.append(result)
        elif suffix == "cs":
            for result in analyze_cs_cyclomatic_complexity(
                file, threshold=complexity_threshold
            ):
                result["threshold"] = complexity_threshold
                high_complexity.append(result)
    return high_complexity


def analyze_large_files(files, large_file_threshold, top_n_large):
    """Analyze large files."""
    large_files = find_large_files(
        files, token_threshold=large_file_threshold, top_n=top_n_large
    )
    large_files = sorted(large_files, key=lambda x: x["token_count"], reverse=True)
    if top_n_large > 0:
        large_files = large_files[:top_n_large]
    return large_files


def analyze_large_classes(files, large_class_threshold, top_n_large):
    """Analyze large classes."""
    large_classes = []
    for file in files:
        suffix = str(file).split(".")[-1].lower()
        if suffix in ["py", "js", "jsx", "cs", "ts", "tsx"]:
            large_classes.extend(
                find_large_classes(
                    file, token_threshold=large_class_threshold, top_n=top_n_large
                )
            )
    large_classes = sorted(large_classes, key=lambda x: x["token_count"], reverse=True)
    if top_n_large > 0:
        large_classes = large_classes[:top_n_large]
    return large_classes


def analyze_unused_imports_vars(
    files,
) -> list:
    """
    Analyze files for unused imports and variables.
    Returns a list of dicts with file, line, code, and message.
        list: A list of dictionaries, each containing:
            {
                "file": str,      # The file path
                "line": int,      # The line number
                "code": str,      # The flake8 code (e.g., F401, F841)
                "message": str,   # The flake8 message
            }
    """
    from replicheck.utils import find_flake8_unused

    # Make separate lists for each language, but only process Python files for now
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
    # js_files = (
    # suffix_map[".js"] + suffix_map[".jsx"] + suffix_map[".ts"] + suffix_map[".tsx"]
    # )
    # cs_files = suffix_map[".cs"]
    py_results = find_flake8_unused(py_files) if py_files else []
    # js_results = []
    # cs_results = []
    return (
        py_results
        # + js_results + cs_results
    )


def parse_code_files(files, parser):
    """Parse all code files and extract code blocks."""
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


def main(
    path: str,
    min_similarity: float = 0.8,
    min_size: int = 50,
    output_format: str = "text",
    output_file: Optional[str] = None,
    ignore_dirs: Optional[list[str]] = None,
    complexity_threshold: int = 10,
    large_file_threshold: int = 500,
    large_class_threshold: int = 300,
    top_n_large: int = 10,
    extensions: Optional[list[str]] = None,
) -> int:
    """
    Main entry point for the Replicheck tool.

    Args:
        path: Path to the directory to analyze
        min_similarity: Minimum similarity threshold (0.0 to 1.0)
        min_size: Minimum size of code blocks to compare (in tokens)
        output_format: Output format ("text" or "json")
        output_file: Path to output file (if None, prints to console)
        ignore_dirs: List of directories to ignore

    Returns:
        int: Exit code (0 for success, 1 for error)
    """

    try:
        path = Path(path)
        if not path.exists():
            print("Error: Path does not exist")
            return 1

        parser = CodeParser()
        detector = DuplicateDetector(min_similarity=min_similarity, min_size=min_size)
        reporter = Reporter(output_format=output_format)

        if extensions is None:
            extensions_set = {".py", ".js", ".jsx", ".cs", ".ts", ".tsx"}
        else:
            extensions_set = {e if e.startswith(".") else f".{e}" for e in extensions}

        print("Finding files...")
        files = find_files(path, extensions=extensions_set, ignore_dirs=ignore_dirs)
        print(f"Found {len(files)} files to analyze")

        code_blocks = parse_code_files(files, parser)
        print("Analyzing code blocks...")

        high_complexity = analyze_complexity(files, complexity_threshold)
        large_files = analyze_large_files(files, large_file_threshold, top_n_large)
        large_classes = analyze_large_classes(files, large_class_threshold, top_n_large)
        duplicates = detector.find_duplicates(code_blocks)
        unused_imports_vars = analyze_unused_imports_vars(files)
        todo_fixme_comments = find_todo_fixme_comments(files)

        output_path = Path(output_file) if output_file else None
        reporter.generate_report(
            duplicates,
            output_path,
            complexity_results=high_complexity,
            large_files=large_files,
            large_classes=large_classes,
            unused=unused_imports_vars,
            todo_fixme=todo_fixme_comments,
        )

        return 0

    except Exception:
        # Only print progress and final report, so suppress error details
        print("Error: An unexpected error occurred.")
        return 1


if __name__ == "__main__":
    args = parse_args()
    sys.exit(
        main(
            path=args.path,
            min_similarity=args.min_similarity,
            min_size=args.min_size,
            output_format=args.output_format,
            output_file=args.output_file,
            ignore_dirs=args.ignore_dirs,
            complexity_threshold=args.complexity_threshold,
            large_file_threshold=args.large_file_threshold,
            large_class_threshold=args.large_class_threshold,
            top_n_large=args.top_n_large,
            extensions=args.extensions,
        )
    )
