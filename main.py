#!/usr/bin/env python3
"""
Replicheck - A tool for detecting code duplications in projects.
"""

import argparse
import sys

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
        )
    )
