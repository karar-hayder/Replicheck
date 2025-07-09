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
        if output_format not in {"text", "json", "markdown"}:
            raise ValueError(
                "Output format must be either 'text', 'json', or 'markdown'"
            )
        self.output_format = output_format

    def _format_path(self, file, line=None, mode="plain"):
        # mode: 'plain', 'markdown', 'terminal'
        if line is not None:
            path_str = f"{file}:{line}"
        else:
            path_str = file
        if mode == "markdown":
            if line is not None:
                return f"[{file}:{line}]({file}#L{line})"
            else:
                return f"[{file}]({file})"
        elif mode == "terminal":
            # OSC 8 hyperlink (if supported)
            # https://gist.github.com/robertknight/2c8c2a6b9236dba7b21c
            url = f"file://{file}"
            if line is not None:
                url += f"#L{line}"
            return f"\033]8;;{url}\033\\{path_str}\033]8;;\033\\"
        else:
            return path_str

    def _generate_summary(
        self, complexity_results, large_files, large_classes, todo_fixme, duplicates
    ):
        def count_severity(items, key="severity", level=None):
            if not items:
                return 0
            if level:
                return sum(1 for x in items if x.get(key) == level)
            return len(items)

        summary = []
        # Complexity
        n_complex = count_severity(complexity_results)
        n_crit_complex = count_severity(complexity_results, level="Critical 🔴")
        if n_complex:
            summary.append(
                f"- {n_complex} high complexity functions ({n_crit_complex} Critical 🔴)"
            )
        else:
            summary.append("- 0 high complexity functions ✅")
        # Large files
        n_large_files = count_severity(large_files)
        n_crit_files = count_severity(large_files, level="Critical 🔴")
        if n_large_files:
            summary.append(
                f"- {n_large_files} large files ({n_crit_files} Critical 🔴)"
            )
        else:
            summary.append("- 0 large files ✅")
        # Large classes
        n_large_classes = count_severity(large_classes)
        n_high_classes = count_severity(large_classes, level="High 🟠")
        if n_large_classes:
            summary.append(
                f"- {n_large_classes} large classes ({n_high_classes} High 🟠)"
            )
        else:
            summary.append("- 0 large classes ✅")
        # TODO/FIXME
        n_todo = len(todo_fixme) if todo_fixme else 0
        summary.append(
            f"- {n_todo} TODO/FIXME comments"
            if n_todo
            else "- 0 TODO/FIXME comments ✅"
        )
        # Duplicates
        n_dupes = len(duplicates) if duplicates else 0
        summary.append(
            f"- {n_dupes} duplicate code blocks"
            if n_dupes
            else "- 0 duplicate code blocks ✅"
        )
        return summary

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

        # Add summary section at the top
        summary_lines = self._generate_summary(
            complexity_results, large_files, large_classes, todo_fixme, duplicates
        )
        console_output.append(f"{Fore.YELLOW}Summary:{Style.RESET_ALL}")
        file_output.append("Summary:")
        for line in summary_lines:
            console_output.append(line)
            file_output.append(line)
        console_output.append("")
        file_output.append("")

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

    def _generate_markdown_report(
        self,
        duplicates: List[Dict[str, Any]],
        output_file: Path = None,
        complexity_results: List[Dict[str, Any]] = None,
        large_files: List[Dict[str, Any]] = None,
        large_classes: List[Dict[str, Any]] = None,
        todo_fixme: List[Dict[str, Any]] = None,
    ):
        """Generate a Markdown report."""
        md = []
        md.append("# Code Duplication Report\n")
        # Summary
        md.append("## Summary")
        for line in self._generate_summary(
            complexity_results, large_files, large_classes, todo_fixme, duplicates
        ):
            md.append(f"- {line}")
        md.append("")
        # Complexity
        if complexity_results:
            md.append("## High Cyclomatic Complexity Functions")
            for item in complexity_results:
                md.append(
                    f"- {self._format_path(item['file'], item['lineno'], 'markdown')} {item['name']} (complexity: {item['complexity']}) [{item['severity']}]"
                )
        # Large files
        if large_files:
            md.append("\n## Large Files")
            for item in large_files:
                md.append(
                    f"- {self._format_path(item['file'], None, 'markdown')} (tokens: {item['token_count']}) [{item['severity']}]"
                )
        # Large classes
        if large_classes:
            md.append("\n## Large Classes")
            for item in large_classes:
                md.append(
                    f"- {self._format_path(item['file'], item['start_line'], 'markdown')} {item['name']} (tokens: {item['token_count']}) [{item['severity']}]"
                )
        # TODO/FIXME
        if todo_fixme:
            md.append("\n## TODO/FIXME Comments")
            for item in todo_fixme:
                md.append(
                    f"- {self._format_path(item['file'], item['line'], 'markdown')} [{item['type']}] {item['text']}"
                )
        # Duplicates
        if duplicates:
            md.append("\n## Code Duplications")
            is_group_format = (
                "num_duplicates" in duplicates[0] and "locations" in duplicates[0]
            )
            if is_group_format:
                for i, group in enumerate(duplicates, 1):
                    cross = " (cross-file)" if group.get("cross_file") else ""
                    md.append(
                        f"- Clone #{i}: size={group['size']} tokens, count={group['num_duplicates']}{cross}"
                    )
                    for loc in group["locations"]:
                        md.append(
                            f"    - {self._format_path(loc['file'], loc['start_line'], 'markdown')} - {loc['file']}:{loc['start_line']}-{loc['end_line']}"
                        )
                    snippet = " ".join(group["tokens"][:10]) + (
                        " ..." if len(group["tokens"]) > 10 else ""
                    )
                    md.append(f"    Tokens: {snippet}")
            else:
                for i, dup in enumerate(duplicates, 1):
                    sim = dup.get("similarity", 0)
                    sim_pct = f"{sim*100:.2f}%" if isinstance(sim, float) else str(sim)
                    md.append(
                        f"- Duplication #{i}: Similarity: {sim_pct}, size={dup.get('size', '?')} tokens"
                    )
                    for block_key in ("block1", "block2"):
                        block = dup.get(block_key)
                        if block:
                            md.append(
                                f"    - {self._format_path(block['file'], block['start_line'], 'markdown')} - {block['file']}:{block['start_line']}-{block['end_line']}"
                            )
                    tokens = dup.get("tokens")
                    if tokens:
                        snippet = " ".join(tokens[:10]) + (
                            " ..." if len(tokens) > 10 else ""
                        )
                        md.append(f"    Tokens: {snippet}")
        else:
            md.append("No code duplications found!")
        md_str = "\n".join(md)
        if output_file:
            output_file.write_text(md_str, encoding="utf-8")
        else:
            print(md_str)

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
            elif self.output_format == "markdown":
                self._generate_markdown_report(
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
