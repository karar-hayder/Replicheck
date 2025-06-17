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
        self, duplicates: List[Dict[str, Any]], output_file: Path = None
    ):
        """
        Generate a report of code duplications.

        Args:
            duplicates: List of duplicate code blocks
            output_file: Optional path to save the report
        """
        try:
            if self.output_format == "json":
                self._generate_json_report(duplicates, output_file)
            else:
                self._generate_text_report(duplicates, output_file)

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
        self, duplicates: List[Dict[str, Any]], output_file: Path = None
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
        self, duplicates: List[Dict[str, Any]], output_file: Path = None
    ):
        """Generate a JSON report."""
        report = {"duplicates": duplicates, "total_duplications": len(duplicates)}
        json_str = json.dumps(report, indent=2)

        if output_file:
            output_file.write_text(json_str)
        else:
            print(json_str)
