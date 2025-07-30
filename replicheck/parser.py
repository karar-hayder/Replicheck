"""
Code parsing and tokenization logic.
"""

import ast
from pathlib import Path
from typing import Any, Dict, List

from tree_sitter_language_pack import get_parser

from .tree_sitter_loader import get_language


class CodeParser:
    def __init__(self):
        self.supported_extensions = {".py", ".js", ".jsx", ".cs", ".ts", ".tsx"}
        self._parsers = {}

    def _get_parser(self, language_name):
        if language_name not in self._parsers:
            parser = get_parser(language_name)
            self._parsers[language_name] = parser
        return self._parsers[language_name]

    def parse_file(self, file_path: Path) -> List[Dict[str, Any]]:
        if file_path.suffix not in self.supported_extensions:
            return []
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        if file_path.suffix == ".py":
            return self._parse_python(content, file_path)
        elif file_path.suffix in {".js", ".jsx"}:
            return self._parse_with_tree_sitter(content, file_path, "javascript")
        elif file_path.suffix == ".ts":
            return self._parse_with_tree_sitter(content, file_path, "typescript")
        elif file_path.suffix == ".tsx":
            return self._parse_with_tree_sitter(content, file_path, "tsx")
        elif file_path.suffix == ".cs":
            return self._parse_with_tree_sitter(content, file_path, "csharp")
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
        self, content: str, file_path: Path, language_name: str
    ) -> List[Dict[str, Any]]:
        parser = self._get_parser(language_name)
        language = get_language(language_name)

        try:
            tree = parser.parse(bytes(content, "utf8"))
            root = tree.root_node
            blocks = []
            language_queries = {
                "javascript": """
                (function_declaration) @function
                (method_definition) @function
                (class_declaration) @class
            """,
                "typescript": """
                (function_declaration) @function
                (method_definition) @function
                (class_declaration) @class
                (interface_declaration) @interface
                (type_alias_declaration) @type
                (enum_declaration) @enum
                (variable_declarator) @declaration
            """,
                "tsx": """
                (function_declaration) @function
                (method_definition) @function
                (class_declaration) @class
                (jsx_element) @jsx
                (interface_declaration) @interface
                (type_alias_declaration) @type
                (enum_declaration) @enum
                (variable_declarator) @declaration
            """,
                "csharp": """
                (class_declaration) @class
                (method_declaration) @function
                (constructor_declaration) @function
                (enum_declaration) @enum
            """,
            }
            query_str = language_queries.get(language_name)
            if not query_str:
                print(f"[WARN] Unsupported language for tree-sitter: {language_name}")
                return []

            query = language.query(query_str)
            captures = query.captures(root)
            if isinstance(captures, dict):
                for capture_name, nodes in captures.items():
                    for node in nodes:
                        tokens = self._tokenize_tree_sitter_node(node, content)
                        if tokens:
                            blocks.append(
                                {
                                    "location": {
                                        "file": str(file_path),
                                        "start_line": node.start_point[0] + 1,
                                        "end_line": node.end_point[0] + 1,
                                    },
                                    "tokens": tokens,
                                    "type": capture_name,
                                }
                            )
            elif isinstance(captures, list):
                for node, capture_name in captures:
                    tokens = self._tokenize_tree_sitter_node(node, content)
                    if tokens:
                        blocks.append(
                            {
                                "location": {
                                    "file": str(file_path),
                                    "start_line": node.start_point[0] + 1,
                                    "end_line": node.end_point[0] + 1,
                                },
                                "tokens": tokens,
                                "type": capture_name,
                            }
                        )
            else:
                print(f"Unexpected captures format: {type(captures)}")
                return []

            return blocks

        except Exception as e:
            print(f"[ERROR] Tree-sitter parse error in {file_path}: {e}")
            return []

    def _tokenize_tree_sitter_node(self, node, content: str) -> List[str]:
        tokens = []

        def extract_tokens(n):
            if n.type in [
                "identifier",
                "property_identifier",
                "shorthand_property_identifier",
                "type_identifier",
            ]:

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
