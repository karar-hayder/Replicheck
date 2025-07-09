"""
Code parsing and tokenization logic.
"""

import ast
from pathlib import Path
from typing import Any, Dict, List

from tree_sitter import Parser

from .tree_sitter_loader import JAVASCRIPT, PYTHON

# from tree_sitter_languages import get_parser


class CodeParser:
    def __init__(self):
        self.supported_extensions = {".py", ".js", ".jsx"}
        self._parsers = {}

    def _get_parser(self, language):
        if language not in self._parsers:
            parser = Parser(language)
            self._parsers[language] = parser
        return self._parsers[language]

    def parse_file(self, file_path: Path) -> List[Dict[str, Any]]:
        if file_path.suffix not in self.supported_extensions:
            # Gracefully skip unsupported extensions
            return []
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        if file_path.suffix == ".py":
            return self._parse_python(content, file_path)
        elif file_path.suffix in {".js", ".jsx"}:
            return self._parse_with_tree_sitter(content, file_path, JAVASCRIPT)
        # .ts and .tsx are not supported
        return []

    def _parse_python(self, content: str, file_path: Path) -> List[Dict[str, Any]]:
        try:
            tree = ast.parse(content)
            blocks = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    tokens = [node.name]
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

    def _parse_with_tree_sitter(
        self, content: str, file_path: Path, language
    ) -> List[Dict[str, Any]]:
        parser = self._get_parser(language)
        try:
            tree = parser.parse(bytes(content, "utf8"))
            root = tree.root_node
            blocks = []
            node_types = [
                "function_declaration",
                "method_definition",
                "class_declaration",
            ]
            for node_type in node_types:
                try:
                    query = language.query(f"({node_type}) @function")
                    captures = query.captures(tree.root_node)
                    if isinstance(captures, dict) and "function" in captures:
                        for capture_node in captures["function"]:
                            tokens = self._tokenize_tree_sitter_node(
                                capture_node, content
                            )
                            if tokens:
                                block = {
                                    "location": {
                                        "file": str(file_path),
                                        "start_line": capture_node.start_point[0] + 1,
                                        "end_line": capture_node.end_point[0] + 1,
                                    },
                                    "tokens": tokens,
                                }
                                blocks.append(block)
                except Exception:
                    pass
            return blocks
        except Exception:
            return []

    def _tokenize_tree_sitter_node(self, node, content: str) -> List[str]:
        tokens = []

        def extract_tokens(n):
            if n.type in ["identifier", "property_identifier"]:
                start_byte = n.start_byte
                end_byte = n.end_byte
                token_text = content[start_byte:end_byte]
                if token_text.strip():
                    tokens.append(token_text)
            elif n.type in ["string", "number"]:
                start_byte = n.start_byte
                end_byte = n.end_byte
                token_text = content[start_byte:end_byte]
                if token_text.strip():
                    tokens.append(token_text)
            for child in n.children:
                extract_tokens(child)

        extract_tokens(node)
        return tokens

    def _tokenize_python(self, node: ast.AST) -> List[str]:
        tokens = []
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                tokens.append(child.id)
            elif isinstance(child, ast.Constant):
                tokens.append(str(child.value))
        return tokens
