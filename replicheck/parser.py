"""
Code parsing and tokenization logic.
"""

import ast
from pathlib import Path
from typing import Any, Dict, List


class CodeParser:
    def __init__(self):
        self.supported_extensions = {".py", ".js"}

    def parse_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Parse a file and extract code blocks.

        Args:
            file_path: Path to the file to parse

        Returns:
            List of code blocks with their metadata
        """
        if file_path.suffix not in self.supported_extensions:
            return []

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if file_path.suffix == ".py":
            return self._parse_python(content, file_path)
        elif file_path.suffix == ".js":
            return self._parse_javascript(content, file_path)

    def _parse_python(self, content: str, file_path: Path) -> List[Dict[str, Any]]:
        """Parse Python code using AST."""
        try:
            tree = ast.parse(content)
            blocks = []

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    # Add the function/class name as the first token
                    tokens = [node.name]
                    # Add the rest of the tokens
                    tokens.extend(self._tokenize_python(node))

                    block = {
                        "location": {
                            "file": str(file_path),
                            "start_line": node.lineno,
                            "end_line": node.end_lineno,
                        },
                        "tokens": tokens,
                    }
                    blocks.append(block)

            return blocks
        except SyntaxError:
            return []

    def _parse_javascript(self, content: str, file_path: Path) -> List[Dict[str, Any]]:
        """Parse JavaScript code (placeholder for now)."""
        # TODO: Implement JavaScript parsing
        return []

    def _tokenize_python(self, node: ast.AST) -> List[str]:
        """Convert Python AST node to tokens."""
        tokens = []
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                tokens.append(child.id)
            elif isinstance(child, ast.Constant):
                tokens.append(str(child.value))
        return tokens
