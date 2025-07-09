"""
Reporting logic for code duplication results.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

from colorama import Fore, Style, init

init()


class Reporter:
    def __init__(self, output_format: str = "text"):
        if output_format not in {"text", "json"}:
            raise ValueError("Output format must be either 'text' or 'json'")
        self.output_format = output_format

    def generate_report(
        self,
        duplicates: List[Dict[str, Any]],
        output_file: Path = None,
        complexity_results: List[Dict[str, Any]] = None,
        large_files: List[Dict[str, Any]] = None,
        large_classes: List[Dict[str, Any]] = None,
        todo_fixme: List[Dict[str, Any]] = None,
    ):
        """
        Generate a report of code duplications.

        Args:
            duplicates: List of duplicate code blocks
            output_file: Optional path to save the report
            complexity_results: List of high-complexity functions (optional)
            large_files: List of large files (optional)
            large_classes: List of large classes (optional)
            todo_fixme: List of TODO/FIXME comments (optional)
        """
        try:
            if self.output_format == "json":
                self._generate_json_report(
                    duplicates,
                    output_file,
                    complexity_results,
                    large_files,
                    large_classes,
                    todo_fixme,
                )
            else:
                self._generate_text_report(
                    duplicates,
                    output_file,
                    complexity_results,
                    large_files,
                    large_classes,
                    todo_fixme,
                )

            if output_file:
                print(f"\nReport written to: {output_file}")
        except Exception as e:
            print(f"\nError writing report: {e}")
            # Fallback to console output
            if self.output_format == "json":
                self._generate_json_report(duplicates, None)
            else:
                self._generate_text_report(duplicates, None)

    def _generate_text_report(
        self,
        duplicates: List[Dict[str, Any]],
        output_file: Path = None,
        complexity_results: List[Dict[str, Any]] = None,
        large_files: List[Dict[str, Any]] = None,
        large_classes: List[Dict[str, Any]] = None,
        todo_fixme: List[Dict[str, Any]] = None,
    ):
        """Generate a human-readable text report."""
        # Create two versions: one for console (with colors) and one for file (plain text)
        console_output = []
        file_output = []

        # Add header
        console_output.append(
            f"\n{Fore.CYAN}Code Duplication Report{Style.RESET_ALL}\n"
        )
        file_output.append("\nCode Duplication Report\n")

        # Add cyclomatic complexity section
        if complexity_results is not None:
            if complexity_results:
                console_output.append(
                    f"{Fore.MAGENTA}High Cyclomatic Complexity Functions (threshold: >= {complexity_results[0].get('threshold', 'N/A')}):{Style.RESET_ALL}"
                )
                file_output.append(
                    f"High Cyclomatic Complexity Functions (threshold: >= {complexity_results[0].get('threshold', 'N/A')}):"
                )
                for item in complexity_results:
                    line = f"- {item['file']}:{item['lineno']} {item['name']} (complexity: {item['complexity']})"
                    console_output.append(line)
                    file_output.append(line)
            else:
                console_output.append(
                    f"{Fore.GREEN}No high cyclomatic complexity functions found.{Style.RESET_ALL}"
                )
                file_output.append("No high cyclomatic complexity functions found.")
            console_output.append("")
            file_output.append("")
        # Add large files section
        if large_files is not None:
            if large_files:
                threshold = (
                    large_files[0].get("threshold", "N/A") if large_files else "N/A"
                )
                top_n = large_files[0].get("top_n", "N/A") if large_files else "N/A"
                console_output.append(
                    f"{Fore.MAGENTA}Large Files (threshold: >= {threshold}, top N: {top_n}):{Style.RESET_ALL}"
                )
                file_output.append(
                    f"Large Files (threshold: >= {threshold}, top N: {top_n}):"
                )
                for item in large_files:
                    line = f"- {item['file']} (tokens: {item['token_count']})"
                    console_output.append(line)
                    file_output.append(line)
            else:
                console_output.append(
                    f"{Fore.GREEN}No large files found.{Style.RESET_ALL}"
                )
                file_output.append("No large files found.")
            console_output.append("")
            file_output.append("")
        # Add large classes section
        if large_classes is not None:
            if large_classes:
                threshold = (
                    large_classes[0].get("threshold", "N/A") if large_classes else "N/A"
                )
                top_n = large_classes[0].get("top_n", "N/A") if large_classes else "N/A"
                console_output.append(
                    f"{Fore.MAGENTA}Large Classes (threshold: >= {threshold}, top N: {top_n}):{Style.RESET_ALL}"
                )
                file_output.append(
                    f"Large Classes (threshold: >= {threshold}, top N: {top_n}):"
                )
                for item in large_classes:
                    line = f"- {item['file']}:{item['start_line']} {item['name']} (tokens: {item['token_count']})"
                    console_output.append(line)
                    file_output.append(line)
            else:
                console_output.append(
                    f"{Fore.GREEN}No large classes found.{Style.RESET_ALL}"
                )
                file_output.append("No large classes found.")
            console_output.append("")
            file_output.append("")
        # Add TODO/FIXME section
        if todo_fixme is not None:
            if todo_fixme:
                console_output.append(
                    f"{Fore.MAGENTA}TODO/FIXME Comments:{Style.RESET_ALL}"
                )
                file_output.append("TODO/FIXME Comments:")
                for item in todo_fixme:
                    line = f"- {item['file']}:{item['line']} [{item['type']}] {item['text']}"
                    console_output.append(line)
                    file_output.append(line)
            else:
                console_output.append(
                    f"{Fore.GREEN}No TODO/FIXME comments found.{Style.RESET_ALL}"
                )
                file_output.append("No TODO/FIXME comments found.")
            console_output.append("")
            file_output.append("")

        if not duplicates:
            console_output.append(
                f"{Fore.GREEN}No code duplications found!{Style.RESET_ALL}\n"
            )
            file_output.append("No code duplications found!\n")

            if output_file:
                output_file.write_text("\n".join(file_output))
            else:
                print("\n".join(console_output))
            return

        for i, dup in enumerate(duplicates, 1):
            # Console version with colors
            console_output.append(f"{Fore.YELLOW}Duplication #{i}{Style.RESET_ALL}")
            console_output.append(f"Similarity: {dup['similarity']:.2%}")
            console_output.append(f"Size: {dup['size']} tokens")
            console_output.append(
                f"Location 1: {dup['block1']['file']}:{dup['block1']['start_line']}-{dup['block1']['end_line']}"
            )
            console_output.append(
                f"Location 2: {dup['block2']['file']}:{dup['block2']['start_line']}-{dup['block2']['end_line']}\n"
            )

            # File version without colors
            file_output.append(f"Duplication #{i}")
            file_output.append(f"Similarity: {dup['similarity']:.2%}")
            file_output.append(f"Size: {dup['size']} tokens")
            file_output.append(
                f"Location 1: {dup['block1']['file']}:{dup['block1']['start_line']}-{dup['block1']['end_line']}"
            )
            file_output.append(
                f"Location 2: {dup['block2']['file']}:{dup['block2']['start_line']}-{dup['block2']['end_line']}\n"
            )

        if output_file:
            output_file.write_text("\n".join(file_output))
        else:
            print("\n".join(console_output))

    def _generate_json_report(
        self,
        duplicates: List[Dict[str, Any]],
        output_file: Path = None,
        complexity_results: List[Dict[str, Any]] = None,
        large_files: List[Dict[str, Any]] = None,
        large_classes: List[Dict[str, Any]] = None,
        todo_fixme: List[Dict[str, Any]] = None,
    ):
        """Generate a JSON report."""
        report = {
            "duplicates": duplicates,
            "total_duplications": len(duplicates),
            "high_cyclomatic_complexity": complexity_results or [],
            "large_files": large_files or [],
            "large_classes": large_classes or [],
            "large_file_threshold": (
                large_files[0].get("threshold", "N/A") if large_files else None
            ),
            "large_class_threshold": (
                large_classes[0].get("threshold", "N/A") if large_classes else None
            ),
            "top_n_large": large_files[0].get("top_n", "N/A") if large_files else None,
            "todo_fixme_comments": todo_fixme or [],
        }
        json_str = json.dumps(report, indent=2)
        if output_file:
            output_file.write_text(json_str)
        else:
            print(json_str)
