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
from replicheck.utils import find_files


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
        choices=["text", "json"],
        default="text",
        help="Output format (text or json)",
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
        default=[".git", ".venv", "venv", "env", "ENV", "build", "dist"],
        help="Directories to ignore",
    )

    return parser.parse_args()


def main(
    path: str,
    min_similarity: float = 0.8,
    min_size: int = 50,
    output_format: str = "text",
    output_file: Optional[str] = None,
    ignore_dirs: Optional[list[str]] = None,
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
        # Convert path to Path object
        path = Path(path)
        if not path.exists():
            print(f"Error: Path '{path}' does not exist")
            return 1

        parser = CodeParser()
        detector = DuplicateDetector(min_similarity=min_similarity, min_size=min_size)
        reporter = Reporter(output_format=output_format)

        print("Finding files...")
        files = find_files(path, ignore_dirs=ignore_dirs)
        print(f"Found {len(files)} files to analyze")

        print("Parsing files...")
        code_blocks = []
        for file in files:
            try:
                blocks = parser.parse_file(file)
                code_blocks.extend(blocks)
            except Exception as e:
                print(f"Warning: Error parsing {file}: {e}")

        print(f"Found {len(code_blocks)} code blocks to analyze")

        print("Analyzing code blocks...")
        duplicates = detector.find_duplicates(code_blocks)

        # Generate report
        output_path = Path(output_file) if output_file else None
        reporter.generate_report(duplicates, output_path)

        return 0

    except Exception as e:
        print(f"Error: {e}")
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
        )
    )
