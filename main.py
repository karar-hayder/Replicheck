#!/usr/bin/env python3
"""
Replicheck - A tool for detecting code duplications in projects.
"""

import argparse
import sys

from replicheck.cache import CACHE_FILENAME
from replicheck.runner import ReplicheckRunner


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
    parser.add_argument(
        "--cache",
        action="store_true",
        help=(
            "reuse per-file results from the previous run in this directory and "
            "analyse only the files that changed. Off by default: a cache that "
            "answers with stale findings is worse than a slow scan."
        ),
    )
    parser.add_argument(
        "--cache-file",
        type=str,
        default=None,
        help=(
            "where to keep the cache. Defaults to "
            f"{CACHE_FILENAME} inside the scanned directory"
        ),
    )
    parser.add_argument(
        "--flake8-codes",
        type=str,
        default=None,
        help=(
            "comma-separated flake8 codes to select, e.g. F401,F841. flake8 is "
            "the largest cost of a scan, so narrowing this is the main speed "
            "lever. Omitted means every code the detectors need "
            "(F401,F841,B,S,E800) - trimming drops findings, so it is opt-in."
        ),
    )
    parser.add_argument(
        "--full-scan",
        action="store_true",
        help=(
            "force a complete scan: ignore any cache and use the full flake8 "
            "code set. This is already the default; the flag is an explicit "
            "override for when the fast paths are enabled elsewhere."
        ),
    )
    return parser.parse_args()


def main(**kwargs) -> int:
    """
    Main entry point for the Replicheck tool.
    Accepts all ReplicheckRunner arguments as keyword arguments.
    """
    runner = ReplicheckRunner(**kwargs)
    return runner.run()


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
            cache=args.cache,
            cache_file=args.cache_file,
            flake8_codes=args.flake8_codes,
            full_scan=args.full_scan,
        )
    )
