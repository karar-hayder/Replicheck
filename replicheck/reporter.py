"""
Reporting logic for code duplication results.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

from colorama import Fore, Style, init

init()


class Reporter:
    severity_order = {
        "Critical 🔴": 4,
        "High 🟠": 3,
        "Medium 🟡": 2,
        "Low 🟢": 1,
        "None": 0,
    }

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
                # Sort by severity (Critical > High > Medium > Low > None), then by complexity descending
                complexity_results = sorted(
                    complexity_results,
                    key=lambda x: (
                        self.severity_order.get(x.get("severity"), 0),
                        x.get("complexity", 0),
                    ),
                    reverse=True,
                )
                console_output.append(
                    f"{Fore.MAGENTA}High Cyclomatic Complexity Functions (threshold: >= {complexity_results[0].get('threshold', 'N/A')}):{Style.RESET_ALL}"
                )
                file_output.append(
                    f"High Cyclomatic Complexity Functions (threshold: >= {complexity_results[0].get('threshold', 'N/A')}):"
                )
                for item in complexity_results:
                    line = f"- {item['file']}:{item['lineno']} {item['name']} (complexity: {item['complexity']}) [{item['severity']}]"
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
                # Sort by severity, then by token_count descending
                large_files = sorted(
                    large_files,
                    key=lambda x: (
                        self.severity_order.get(x.get("severity"), 0),
                        x.get("token_count", 0),
                    ),
                    reverse=True,
                )
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
                    line = f"- {item['file']} (tokens: {item['token_count']}) [{item['severity']}]"
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
                # Sort by severity, then by token_count descending
                large_classes = sorted(
                    large_classes,
                    key=lambda x: (
                        self.severity_order.get(x.get("severity"), 0),
                        x.get("token_count", 0),
                    ),
                    reverse=True,
                )
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
                    line = f"- {item['file']}:{item['start_line']} {item['name']} (tokens: {item['token_count']}) [{item['severity']}]"
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

        # Add duplication section
        if duplicates:
            # Check if new or legacy format
            is_group_format = (
                "num_duplicates" in duplicates[0] and "locations" in duplicates[0]
            )
            if is_group_format:
                console_output.append(
                    f"{Fore.MAGENTA}Code Duplications:{Style.RESET_ALL}"
                )
                file_output.append("Code Duplications:")
                for i, group in enumerate(duplicates, 1):
                    cross = " (cross-file)" if group.get("cross_file") else ""
                    line = f"Clone #{i}: size={group['size']} tokens, count={group['num_duplicates']}{cross}"
                    console_output.append(line)
                    file_output.append(line)
                    for loc in group["locations"]:
                        loc_line = (
                            f"    - {loc['file']}:{loc['start_line']}-{loc['end_line']}"
                        )
                        console_output.append(loc_line)
                        file_output.append(loc_line)
                    snippet = " ".join(group["tokens"][:10]) + (
                        " ..." if len(group["tokens"]) > 10 else ""
                    )
                    console_output.append(f"    Tokens: {snippet}")
                    file_output.append(f"    Tokens: {snippet}")
                    console_output.append("")
                    file_output.append("")
            else:
                # Legacy format: block1, block2, similarity
                for i, dup in enumerate(duplicates, 1):
                    sim = dup.get("similarity", 0)
                    sim_pct = f"{sim*100:.2f}%" if isinstance(sim, float) else str(sim)
                    line = f"Duplication #{i}: Similarity: {sim_pct}, size={dup.get('size', '?')} tokens"
                    console_output.append(line)
                    file_output.append(line)
                    for block_key in ("block1", "block2"):
                        block = dup.get(block_key)
                        if block:
                            loc_line = f"    - {block['file']}:{block['start_line']}-{block['end_line']}"
                            console_output.append(loc_line)
                            file_output.append(loc_line)
                    tokens = dup.get("tokens")
                    if tokens:
                        snippet = " ".join(tokens[:10]) + (
                            " ..." if len(tokens) > 10 else ""
                        )
                        console_output.append(f"    Tokens: {snippet}")
                        file_output.append(f"    Tokens: {snippet}")
                    console_output.append("")
                    file_output.append("")
        else:
            console_output.append(
                f"{Fore.GREEN}No code duplications found!{Style.RESET_ALL}"
            )
            file_output.append("No code duplications found!")

        if output_file:
            output_file.write_text("\n".join(file_output), encoding="utf-8")
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
        # Check if new or legacy format
        is_group_format = bool(
            duplicates
            and "num_duplicates" in duplicates[0]
            and "locations" in duplicates[0]
        )
        if not is_group_format:
            # Convert legacy format to group-like for JSON output
            new_duplicates = []
            for dup in duplicates:
                group = {
                    "size": dup.get("size", 0),
                    "num_duplicates": 2,
                    "locations": [dup.get("block1", {}), dup.get("block2", {})],
                    "cross_file": dup.get("block1", {}).get("file")
                    != dup.get("block2", {}).get("file"),
                    "tokens": dup.get("tokens", []),
                    "similarity": dup.get("similarity"),
                }
                new_duplicates.append(group)
            duplicates = new_duplicates

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
            output_file.write_text(json_str, encoding="utf-8")
        else:
            print(json_str)
