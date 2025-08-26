"""
Reporting logic for code duplication and code quality results, with configurable template-driven output.
"""

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from colorama import Fore, Style, init

init(autoreset=True)


class Reporter:
    """
    Flexible, production-level reporter for code duplication and code quality results.
    Uses a config-driven template system for output formatting.
    """

    DEFAULT_CONFIG = {
        "complexity_results": {
            "title": "High Cyclomatic Complexity Functions",
            "color": Fore.MAGENTA,
            "formatter": lambda item: (
                f"- {item['file']}:{item['lineno']} {item['name']} "
                f"(complexity: {item['complexity']}) [{item['severity']}]"
            ),
            "empty_message": "No high cyclomatic complexity functions found.",
            "summary": lambda items: (
                f"- {len(items) if items else 0} high cyclomatic complexity functions"
                + (
                    " ("
                    + ", ".join(
                        f"{sum(1 for x in items if x.get('severity') == sev)} {sev}"
                        for sev in Reporter.severity_order
                        if items and any(x.get("severity") == sev for x in items)
                    )
                    + ")"
                    if items and any(x.get("severity") for x in items)
                    else ""
                )
                if items
                else "- 0 high cyclomatic complexity functions ✅"
            ),
        },
        "large_files": {
            "title": "Large Files",
            "color": Fore.MAGENTA,
            "formatter": lambda item: (
                f"- {item['file']} (tokens: {item['token_count']}) [{item['severity']}]"
            ),
            "empty_message": "No large files found.",
            "summary": lambda items: (
                f"- {len(items) if items else 0} large files"
                + (
                    " ("
                    + ", ".join(
                        f"{sum(1 for x in items if x.get('severity') == sev)} {sev}"
                        for sev in Reporter.severity_order
                        if items and any(x.get("severity") == sev for x in items)
                    )
                    + ")"
                    if items and any(x.get("severity") for x in items)
                    else ""
                )
                if items
                else "- 0 large files ✅"
            ),
        },
        "large_classes": {
            "title": "Large Classes",
            "color": Fore.MAGENTA,
            "formatter": lambda item: (
                f"- {item['file']}:{item['start_line']} {item['name']} "
                f"(tokens: {item['token_count']}) [{item['severity']}]"
            ),
            "empty_message": "No large classes found.",
            "summary": lambda items: (
                f"- {len(items) if items else 0} large classes"
                + (
                    " ("
                    + ", ".join(
                        f"{sum(1 for x in items if x.get('severity') == sev)} {sev}"
                        for sev in Reporter.severity_order
                        if items and any(x.get("severity") == sev for x in items)
                    )
                    + ")"
                    if items and any(x.get("severity") for x in items)
                    else ""
                )
                if items
                else "- 0 large classes ✅"
            ),
        },
        "unused": {
            "title": "Unused Imports and Vars",
            "color": Fore.MAGENTA,
            "formatter": lambda item: (
                f"- {item['file']}:{item['line']} [{item['code']}] {item['message']}"
            ),
            "empty_message": "No unused imports or variables found.",
            "summary": lambda items: (
                f"- {len(items) if items else 0} unused imports/variables"
                if items
                else "- 0 unused imports/variables ✅"
            ),
        },
        "todo_fixme": {
            "title": "TODO/FIXME Comments",
            "color": Fore.MAGENTA,
            "formatter": lambda item: (
                f"- {item['file']}:{item['line']} [{item['type']}] {item['text']}"
            ),
            "empty_message": "No TODO/FIXME comments found.",
            "summary": lambda items: (
                f"- {len(items) if items else 0} TODO/FIXME comments"
                if items
                else "- 0 TODO/FIXME comments ✅"
            ),
        },
        "duplicates": {
            "title": "Code Duplications",
            "color": Fore.MAGENTA,
            "formatter": None,  # Special handling
            "empty_message": "No code duplications found!",
            "summary": lambda items: (
                f"- {len(items) if items else 0} duplicate code blocks"
                if items
                else "- 0 duplicate code blocks ✅"
            ),
        },
        "bns_results": {
            "title": "Bugs and Safety Issues",
            "color": Fore.MAGENTA,
            "formatter": lambda item: (
                f"- {item.get('file', 'Unknown')}:{item.get('line', '?')} {item.get('message', '')}"
            ),
            "empty_message": "No Bugs and Safety Issues found.",
            "summary": lambda items: (
                f"- {len(items) if items else 0} Bugs and Safety Issues"
                if items
                else "- 0 Bugs and Safety Issues ✅"
            ),
        },
    }

    severity_order = {
        "Critical 🔴": 4,
        "High 🟠": 3,
        "Medium 🟡": 2,
        "Low 🟢": 1,
        "None": 0,
    }

    def __init__(
        self, output_format: str = "text", config: Optional[Dict[str, Any]] = None
    ):
        allowed_formats = {"text", "json", "markdown"}
        if output_format not in allowed_formats:
            raise ValueError(f"Output format must be one of {allowed_formats}")
        self.output_format = output_format
        self.config = self.DEFAULT_CONFIG.copy()
        if config:
            self.config.update(config)

    def _format_path(self, file, line=None, mode="plain"):
        path_str = f"{file}:{line}" if line is not None else file
        if mode == "markdown":
            if line is not None:
                return f"[{file}:{line}]({file}#L{line})"
            return f"[{file}]({file})"
        elif mode == "terminal":
            url = f"file://{file}"
            if line is not None:
                url += f"#L{line}"
            return f"\033]8;;{url}\033\\{path_str}\033]8;;\033\\"
        return path_str

    def _count_severity(self, items, key="severity", level=None):
        if not items:
            return 0
        if level is not None:
            return sum(1 for x in items if x.get(key) == level)
        return len(items)

    def _generate_summary(self, **kwargs) -> List[str]:
        """
        Dynamically generate a summary for all configured sections.
        Uses per-section summary logic if provided in config, otherwise falls back to a generic summary.
        """
        summary = []
        for key, section in self.config.items():
            items = kwargs.get(key)
            summary_func = section.get("summary")
            if callable(summary_func):
                try:
                    summary.append(summary_func(items))
                    continue
                except Exception as e:
                    summary.append(f"[Error in summary for {key}: {e}]")
                    continue

            n = len(items) if items else 0

            # Try to extract severity levels if present
            levels = {}
            if (
                items
                and isinstance(items, list)
                and items
                and isinstance(items[0], dict)
            ):
                for sev in self.severity_order:
                    count = sum(1 for x in items if x.get("severity") == sev)
                    if count:
                        levels[sev] = count

            # Compose summary line dynamically
            title = section.get("title", key.replace("_", " ").title())
            sev_str = (
                " (" + ", ".join(f"{v} {k}" for k, v in levels.items()) + ")"
                if levels
                else ""
            )
            if n:
                summary.append(f"- {n} {title.lower()}{sev_str}")
            else:
                summary.append(f"- 0 {title.lower()} ✅")
        return summary

    def _render_section(
        self,
        key: str,
        items: Optional[List[Dict[str, Any]]],
        output: List[str],
        color: Optional[str] = None,
        mode: str = "text",
    ):
        section = self.config[key]
        title = section["title"]
        color = section.get("color", color)
        formatter: Optional[Callable[[Dict[str, Any]], str]] = section.get("formatter")
        empty_message = section.get("empty_message", "No results found.")

        if items is not None:
            if items:
                output.append(
                    f"{color}{title}:{Style.RESET_ALL}"
                    if color and mode == "text"
                    else f"{title}:"
                )
                if key == "duplicates" and formatter is None:
                    # Special handling for duplicates group format
                    for i, group in enumerate(items, 1):
                        cross = " (cross-file)" if group.get("cross_file") else ""
                        line = (
                            f"Clone #{i}: size={group.get('size', '?')} tokens, "
                            f"count={group.get('num_duplicates', '?')}{cross}"
                        )
                        output.append(line)
                        for loc in group.get("locations", []):
                            loc_line = f"    - {loc.get('file', '?')}:{loc.get('start_line', '?')}-{loc.get('end_line', '?')}"
                            output.append(loc_line)
                        tokens = group.get("tokens", [])
                        snippet = " ".join(tokens[:10]) + (
                            " ..." if len(tokens) > 10 else ""
                        )
                        output.append(f"    Tokens: {snippet}")
                        output.append("")
                else:
                    for item in items:
                        try:
                            output.append(formatter(item))
                        except Exception as e:
                            output.append(f"[Error formatting item: {e}]")
            else:
                msg = (
                    f"{color}{empty_message}{Style.RESET_ALL}"
                    if color and mode == "text"
                    else empty_message
                )
                output.append(msg)
            output.append("")

    def _generate_text_report(self, output_file: Optional[Path] = None, **kwargs):
        output = []
        # Header
        output.append(f"{Fore.CYAN}\nCode Quality Report\n{Style.RESET_ALL}")
        # Summary
        output.append(f"{Fore.YELLOW}Summary:{Style.RESET_ALL}")
        for line in self._generate_summary(**kwargs):
            output.append(line)
        output.append("")
        # Sections
        for key in self.config:
            self._render_section(key, kwargs.get(key), output, mode="text")
        output_str = "\n".join(output)
        if output_file:
            try:
                output_file.write_text(output_str, encoding="utf-8")
                print(f"\nReport written to: {output_file}")
            except Exception as e:
                print(f"Error writing report: {e}\n{output_str}")
        else:
            print(output_str)

    def _generate_json_report(self, output_file: Optional[Path] = None, **kwargs):
        # Compose a dict with all results
        report = {k: kwargs.get(k, []) for k in self.config}
        report["summary"] = self._generate_summary(**kwargs)
        json_str = json.dumps(report, indent=2)
        if output_file:
            try:
                output_file.write_text(json_str, encoding="utf-8")
                print(f"\nReport written to: {output_file}")
            except Exception as e:
                print(f"Error writing report: {e}\n{json_str}")
        else:
            print(json_str)

    def _generate_markdown_report(self, output_file: Optional[Path] = None, **kwargs):
        md = []
        md.append("# Code Quality Report\n")
        md.append("## Summary")
        for line in self._generate_summary(**kwargs):
            md.append(line)
        md.append("")
        for key, section in self.config.items():
            title = section["title"]
            formatter = section.get("formatter")
            items = kwargs.get(key)
            if items is not None:
                if items:
                    md.append(f"## {title}")
                    if key == "duplicates" and formatter is None:
                        for i, group in enumerate(items, 1):
                            cross = " (cross-file)" if group.get("cross_file") else ""
                            md.append(
                                f"- Clone #{i}: size={group.get('size', '?')} tokens, count={group.get('num_duplicates', '?')}{cross}"
                            )
                            for loc in group.get("locations", []):
                                md.append(
                                    f"    - {self._format_path(loc.get('file', '?'), loc.get('start_line', '?'), 'markdown')} - {loc.get('file', '?')}:{loc.get('start_line', '?')}-{loc.get('end_line', '?')}"
                                )
                            tokens = group.get("tokens", [])
                            snippet = " ".join(tokens[:10]) + (
                                " ..." if len(tokens) > 10 else ""
                            )
                            md.append(f"    Tokens: {snippet}")
                            md.append("")
                    else:
                        for item in items:
                            try:
                                md.append(formatter(item))
                            except Exception as e:
                                md.append(f"[Error formatting item: {e}]")
                else:
                    md.append(
                        f"**{section.get('empty_message', 'No results found.')}**"
                    )
                md.append("")
        md_str = "\n".join(md)
        if output_file:
            try:
                output_file.write_text(md_str, encoding="utf-8")
                print(f"\nReport written to: {output_file}")
            except Exception as e:
                print(f"Error writing report: {e}\n{md_str}")
        else:
            print(md_str)

    def generate_report(
        self,
        output_file: Optional[Path] = None,
        **kwargs,
    ):
        """
        Generate a report of code duplications and code quality issues.

        Args:
            duplicates: List of duplicate code blocks
            output_file: Optional path to save the report
            complexity_results: List of high-complexity functions (optional)
            large_files: List of large files (optional)
            large_classes: List of large classes (optional)
            unused: List of unused imports and vars (optional)
            todo_fixme: List of TODO/FIXME comments (optional)
            bns_results: List of Bugs and Safety issues (optional)
            kwargs: Additional result types for custom templates/config
        """
        # Compose all results into a dict for template-driven rendering
        results = {}
        results.update(kwargs)
        try:
            if self.output_format == "json":
                self._generate_json_report(output_file=output_file, **results)
            elif self.output_format == "markdown":
                self._generate_markdown_report(output_file=output_file, **results)
            else:
                self._generate_text_report(output_file=output_file, **results)
        except Exception as e:
            print(f"\nError writing report: {e}")
            # Fallback to console output
            try:
                if self.output_format == "json":
                    self._generate_json_report(output_file=None, **results)
                elif self.output_format == "markdown":
                    self._generate_markdown_report(output_file=None, **results)
                else:
                    self._generate_text_report(output_file=None, **results)
            except Exception as fallback_e:
                print(f"Failed to generate fallback report: {fallback_e}")
