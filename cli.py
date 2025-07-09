#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

from tqdm import tqdm

from replicheck import CodeParser, Config, DuplicateDetector, Reporter
from replicheck.utils import find_files


def parse_args():
    parser = argparse.ArgumentParser(
        description="Replicheck - Code Duplication Detection Tool"
    )
    parser.add_argument(
        "--path",
        required=True,
        help="Directory to analyze",
    )
    parser.add_argument(
        "--min-sim",
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
        "--extensions",
        default=".py,.js,.jsx",
        help="Comma-separated file extensions to analyze",
    )
    parser.add_argument(
        "--output-format",
        choices=["text", "json"],
        default="text",
        help="Output format (text or json)",
    )
    parser.add_argument(
        "--output-file",
        help="Path to save the report (if not specified, prints to console)",
    )
    parser.add_argument(
        "--ignore-dirs",
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
        ],
        help="Directories to ignore",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    try:
        path = Path(args.path)
        if not path.exists():
            print(f"Error: Path '{path}' does not exist")
            return 1

        parser = CodeParser()
        detector = DuplicateDetector(
            min_similarity=args.min_sim, min_size=args.min_size
        )
        reporter = Reporter(output_format=args.output_format)

        print("\nFinding files...")
        files = find_files(
            path,
            extensions=set(args.extensions.split(",")),
            ignore_dirs=args.ignore_dirs,
        )
        print(f"Found {len(files)} files to analyze")

        if not files:
            print("No files found to analyze. Check your path and extensions.")
            return 0

        print("\nParsing files...")
        all_blocks = []
        for file_path in tqdm(files, desc="Parsing"):
            try:
                blocks = parser.parse_file(file_path)
                all_blocks.extend(blocks)
            except Exception as e:
                print(f"Warning: Error parsing {file_path}: {e}")

        print(f"\nFound {len(all_blocks)} code blocks to analyze")

        if not all_blocks:
            print("No code blocks found to analyze.")
            return 0

        print("\nAnalyzing code blocks...")
        duplicates = detector.find_duplicates(all_blocks)

        # Generate report
        output_path = Path(args.output_file) if args.output_file else None
        reporter.generate_report(duplicates, output_path)

        if duplicates:
            print(f"\nFound {len(duplicates)} duplicate code blocks")
            if output_path:
                print(f"Report written to: {output_path}")
        else:
            print("\nNo duplicate code blocks found")

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
