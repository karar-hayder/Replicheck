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
            url = f"file://{file}"
            if line is not None:
                url += f"#L{line}"
            return f"\033]8;;{url}\033\\{path_str}\033]8;;\033\\"
        else:
            return path_str

    def _count_severity(self, items, key="severity", level=None):
        if not items:
            return 0
        if level:
            return sum(1 for x in items if x.get(key) == level)
        return len(items)

    def _generate_summary(
        self,
        complexity_results,
        large_files,
        large_classes,
        unused,
        todo_fixme,
        duplicates,
        bns_results=None,
    ):
        summary = []
        # Complexity
        n_complex = self._count_severity(complexity_results)
        n_crit_complex = self._count_severity(complexity_results, level="Critical 🔴")
        if n_complex:
            summary.append(
                f"- {n_complex} high complexity functions ({n_crit_complex} Critical 🔴)"
            )
        else:
            summary.append("- 0 high complexity functions ✅")
        # Large files
        n_large_files = self._count_severity(large_files)
        n_crit_files = self._count_severity(large_files, level="Critical 🔴")
        if n_large_files:
            summary.append(
                f"- {n_large_files} large files ({n_crit_files} Critical 🔴)"
            )
        else:
            summary.append("- 0 large files ✅")
        # Large classes
        n_large_classes = self._count_severity(large_classes)
        n_high_classes = self._count_severity(large_classes, level="High 🟠")
        if n_large_classes:
            summary.append(
                f"- {n_large_classes} large classes ({n_high_classes} High 🟠)"
            )
        else:
            summary.append("- 0 large classes ✅")
        # Unused imports/variables
        n_unused = len(unused) if unused else 0
        summary.append(
            f"- {n_unused} unused imports/variables"
            if n_unused
            else "- 0 unused imports/variables ✅"
        )
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
        # BNS.py section
        if bns_results is not None:
            n_bns = len(bns_results)
            summary.append(
                f"- {n_bns} Bugs and Safety Issues."
                if n_bns
                else "- 0 Bugs and Safety Issues. ✅"
            )
        return summary

    # --- Section Generators for Text Report ---

    def _text_section_header(self, title, color=None):
        if color:
            return f"{color}{title}{Style.RESET_ALL}"
        return title

    def _text_section_complexity(self, complexity_results, console_output, file_output):
        if complexity_results is not None:
            if complexity_results:
                complexity_results = sorted(
                    complexity_results,
                    key=lambda x: (
                        self.severity_order.get(x.get("severity"), 0),
                        x.get("complexity", 0),
                    ),
                    reverse=True,
                )
                threshold = complexity_results[0].get("threshold", "N/A")
                console_output.append(
                    self._text_section_header(
                        f"High Cyclomatic Complexity Functions (threshold: >= {threshold}):",
                        Fore.MAGENTA,
                    )
                )
                file_output.append(
                    f"High Cyclomatic Complexity Functions (threshold: >= {threshold}):"
                )
                for item in complexity_results:
                    line = f"- {item['file']}:{item['lineno']} {item['name']} (complexity: {item['complexity']}) [{item['severity']}]"
                    console_output.append(line)
                    file_output.append(line)
            else:
                console_output.append(
                    self._text_section_header(
                        "No high cyclomatic complexity functions found.", Fore.GREEN
                    )
                )
                file_output.append("No high cyclomatic complexity functions found.")
            console_output.append("")
            file_output.append("")

    def _text_section_large_files(self, large_files, console_output, file_output):
        if large_files is not None:
            if large_files:
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
                    self._text_section_header(
                        f"Large Files (threshold: >= {threshold}, top N: {top_n}):",
                        Fore.MAGENTA,
                    )
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
                    self._text_section_header("No large files found.", Fore.GREEN)
                )
                file_output.append("No large files found.")
            console_output.append("")
            file_output.append("")

    def _text_section_large_classes(self, large_classes, console_output, file_output):
        if large_classes is not None:
            if large_classes:
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
                    self._text_section_header(
                        f"Large Classes (threshold: >= {threshold}, top N: {top_n}):",
                        Fore.MAGENTA,
                    )
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
                    self._text_section_header("No large classes found.", Fore.GREEN)
                )
                file_output.append("No large classes found.")
            console_output.append("")
            file_output.append("")

    def _text_section_unused(self, unused, console_output, file_output):
        if unused is not None:
            if unused:
                console_output.append(
                    self._text_section_header("Unused Imports and Vars:", Fore.MAGENTA)
                )
                file_output.append("Unused Imports and Vars:")
                for item in unused:
                    line = f"- {item['file']}:{item['line']} [{item['code']}] {item['message']}"
                    console_output.append(line)
                    file_output.append(line)
            else:
                console_output.append(
                    self._text_section_header(
                        "No unused imports or variables found.", Fore.GREEN
                    )
                )
                file_output.append("No unused imports or variables found.")
            console_output.append("")
            file_output.append("")

    def _text_section_todo_fixme(self, todo_fixme, console_output, file_output):
        if todo_fixme is not None:
            if todo_fixme:
                console_output.append(
                    self._text_section_header("TODO/FIXME Comments:", Fore.MAGENTA)
                )
                file_output.append("TODO/FIXME Comments:")
                for item in todo_fixme:
                    line = f"- {item['file']}:{item['line']} [{item['type']}] {item['text']}"
                    console_output.append(line)
                    file_output.append(line)
            else:
                console_output.append(
                    self._text_section_header(
                        "No TODO/FIXME comments found.", Fore.GREEN
                    )
                )
                file_output.append("No TODO/FIXME comments found.")
            console_output.append("")
            file_output.append("")

    def _text_section_duplicates(self, duplicates, console_output, file_output):
        if duplicates:
            is_group_format = (
                "num_duplicates" in duplicates[0] and "locations" in duplicates[0]
            )
            if is_group_format:
                console_output.append(
                    self._text_section_header("Code Duplications:", Fore.MAGENTA)
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
                self._text_section_header("No code duplications found!", Fore.GREEN)
            )
            file_output.append("No code duplications found!")

    def _text_section_bns(self, bns_results, console_output, file_output):
        if bns_results is not None:
            if bns_results:
                console_output.append(
                    self._text_section_header("Bugs and Safety Issues:", Fore.MAGENTA)
                )
                file_output.append("Bugs and Safety Issues:")
                for item in bns_results:
                    # You can customize the line format as needed
                    line = f"- {item.get('file', 'Unknown')}:{item.get('line', '?')} {item.get('message', '')}"
                    console_output.append(line)
                    file_output.append(line)
            else:
                console_output.append(
                    self._text_section_header(
                        "No Bugs and Safety Issues found.", Fore.GREEN
                    )
                )
                file_output.append("No Bugs and Safety Issues found.")
            console_output.append("")
            file_output.append("")

    def _generate_text_report(
        self,
        duplicates: List[Dict[str, Any]],
        output_file: Path = None,
        complexity_results: List[Dict[str, Any]] = None,
        large_files: List[Dict[str, Any]] = None,
        large_classes: List[Dict[str, Any]] = None,
        unused: List[Dict[str, Any]] = None,
        todo_fixme: List[Dict[str, Any]] = None,
        bns_results: List[Dict[str, Any]] = None,
    ):
        """Generate a human-readable text report."""
        console_output = []
        file_output = []

        # Header
        console_output.append(
            self._text_section_header("\nCode Duplication Report\n", Fore.CYAN)
        )
        file_output.append("\nCode Duplication Report\n")

        # Summary
        summary_lines = self._generate_summary(
            complexity_results,
            large_files,
            large_classes,
            unused,
            todo_fixme,
            duplicates,
            bns_results,
        )
        console_output.append(self._text_section_header("Summary:", Fore.YELLOW))
        file_output.append("Summary:")
        for line in summary_lines:
            console_output.append(line)
            file_output.append(line)
        console_output.append("")
        file_output.append("")

        # Sections
        self._text_section_complexity(complexity_results, console_output, file_output)
        self._text_section_large_files(large_files, console_output, file_output)
        self._text_section_large_classes(large_classes, console_output, file_output)
        self._text_section_unused(unused, console_output, file_output)
        self._text_section_todo_fixme(todo_fixme, console_output, file_output)
        self._text_section_duplicates(duplicates, console_output, file_output)
        self._text_section_bns(bns_results, console_output, file_output)

        # Output
        if output_file:
            output_file.write_text("\n".join(file_output), encoding="utf-8")
        else:
            print("\n".join(console_output))

    # --- JSON Report ---

    def _convert_legacy_duplicates_to_group(self, duplicates):
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
        return new_duplicates

    def _generate_json_report(
        self,
        duplicates: List[Dict[str, Any]],
        output_file: Path = None,
        complexity_results: List[Dict[str, Any]] = None,
        large_files: List[Dict[str, Any]] = None,
        large_classes: List[Dict[str, Any]] = None,
        unused: List[Dict[str, Any]] = None,
        todo_fixme: List[Dict[str, Any]] = None,
        bns_results: List[Dict[str, Any]] = None,
    ):
        """Generate a JSON report."""
        is_group_format = bool(
            duplicates
            and "num_duplicates" in duplicates[0]
            and "locations" in duplicates[0]
        )
        if not is_group_format:
            duplicates = self._convert_legacy_duplicates_to_group(duplicates)

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
            "unused": unused or [],
            "todo_fixme_comments": todo_fixme or [],
            "bugs_n_safety": bns_results or [],
        }
        json_str = json.dumps(report, indent=2)
        if output_file:
            output_file.write_text(json_str, encoding="utf-8")
        else:
            print(json_str)

    # --- Markdown Report ---

    def _markdown_section_complexity(self, complexity_results, md):
        if complexity_results:
            md.append("## High Cyclomatic Complexity Functions")
            for item in complexity_results:
                md.append(
                    f"- {self._format_path(item['file'], item['lineno'], 'markdown')} {item['name']} (complexity: {item['complexity']}) [{item['severity']}]"
                )

    def _markdown_section_large_files(self, large_files, md):
        if large_files:
            md.append("\n## Large Files")
            for item in large_files:
                md.append(
                    f"- {self._format_path(item['file'], None, 'markdown')} (tokens: {item['token_count']}) [{item['severity']}]"
                )

    def _markdown_section_large_classes(self, large_classes, md):
        if large_classes:
            md.append("\n## Large Classes")
            for item in large_classes:
                md.append(
                    f"- {self._format_path(item['file'], item['start_line'], 'markdown')} {item['name']} (tokens: {item['token_count']}) [{item['severity']}]"
                )

    def _markdown_section_unused(self, unused, md):
        if unused:
            md.append("## Unused Imports and Vars")
            for item in unused:
                md.append(
                    f"- {self._format_path(item['file'], item['line'], 'markdown')} [{item['code']}] {item['message']}"
                )

    def _markdown_section_todo_fixme(self, todo_fixme, md):
        if todo_fixme:
            md.append("\n## TODO/FIXME Comments")
            for item in todo_fixme:
                md.append(
                    f"- {self._format_path(item['file'], item['line'], 'markdown')} [{item['type']}] {item['text']}"
                )

    def _markdown_section_duplicates(self, duplicates, md):
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

    def _markdown_section_bns(self, bns_results, md):
        if bns_results is not None:
            md.append("\n## @BNS.py Issues")
            if bns_results:
                for item in bns_results:
                    md.append(
                        f"- {self._format_path(item.get('file', '@BNS.py'), item.get('line', None), 'markdown')} {item.get('message', '')}"
                    )
            else:
                md.append("No issues in @BNS.py found.")

    def _generate_markdown_report(
        self,
        duplicates: List[Dict[str, Any]],
        output_file: Path = None,
        complexity_results: List[Dict[str, Any]] = None,
        large_files: List[Dict[str, Any]] = None,
        large_classes: List[Dict[str, Any]] = None,
        unused: List[Dict[str, Any]] = None,
        todo_fixme: List[Dict[str, Any]] = None,
        bns_results: List[Dict[str, Any]] = None,
    ):
        """Generate a Markdown report."""
        md = []
        md.append("# Code Duplication Report\n")
        # Summary
        md.append("## Summary")
        for line in self._generate_summary(
            complexity_results,
            large_files,
            large_classes,
            unused,
            todo_fixme,
            duplicates,
            bns_results,
        ):
            md.append(f"{line}")
        md.append("")
        self._markdown_section_complexity(complexity_results, md)
        self._markdown_section_large_files(large_files, md)
        self._markdown_section_large_classes(large_classes, md)
        self._markdown_section_unused(unused, md)
        self._markdown_section_todo_fixme(todo_fixme, md)
        self._markdown_section_duplicates(duplicates, md)
        self._markdown_section_bns(bns_results, md)
        md_str = "\n".join(md)
        if output_file:
            output_file.write_text(md_str, encoding="utf-8")
        else:
            print(md_str)

    # --- Main Report Generator ---

    def generate_report(
        self,
        duplicates: List[Dict[str, Any]],
        output_file: Path = None,
        complexity_results: List[Dict[str, Any]] = None,
        large_files: List[Dict[str, Any]] = None,
        large_classes: List[Dict[str, Any]] = None,
        unused: List[Dict[str, Any]] = None,
        todo_fixme: List[Dict[str, Any]] = None,
        bns_results: List[Dict[str, Any]] = None,
    ):
        """
        Generate a report of code duplications.

        Args:
            duplicates: List of duplicate code blocks
            output_file: Optional path to save the report
            complexity_results: List of high-complexity functions (optional)
            large_files: List of large files (optional)
            large_classes: List of large classes (optional)
            unused: List of unused imports and vars (optional)
            todo_fixme: List of TODO/FIXME comments (optional)
            bns_results: List of Bugs and Seafety issues  (optional)

        """
        try:
            if self.output_format == "json":
                self._generate_json_report(
                    duplicates,
                    output_file,
                    complexity_results,
                    large_files,
                    large_classes,
                    unused,
                    todo_fixme,
                    bns_results,
                )
            elif self.output_format == "markdown":
                self._generate_markdown_report(
                    duplicates,
                    output_file,
                    complexity_results,
                    large_files,
                    large_classes,
                    unused,
                    todo_fixme,
                    bns_results,
                )
            else:
                self._generate_text_report(
                    duplicates,
                    output_file,
                    complexity_results,
                    large_files,
                    large_classes,
                    unused,
                    todo_fixme,
                    bns_results,
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
