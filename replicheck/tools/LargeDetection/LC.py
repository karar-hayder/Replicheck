# --- Large Classes ---

from replicheck.utils import compute_severity


class LargeClassDetector:
    def __init__(self):
        from replicheck.parser import CodeParser

        self.parser = CodeParser()
        self.results = []

    def _find_large_python_classes(self, file_path, token_threshold):
        import ast

        large_classes = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_tokens = []
                    for child in ast.walk(node):
                        if isinstance(child, ast.Name):
                            class_tokens.append(child.id)
                        elif isinstance(child, ast.Constant):
                            class_tokens.append(str(child.value))
                    if len(class_tokens) >= token_threshold:
                        large_classes.append(
                            {
                                "name": node.name,
                                "file": str(file_path),
                                "start_line": getattr(node, "lineno", None),
                                "end_line": getattr(node, "end_lineno", None),
                                "token_count": len(class_tokens),
                                "severity": compute_severity(
                                    len(class_tokens), token_threshold
                                ),
                            }
                        )
        except Exception:
            pass
        return large_classes

    def _find_large_js_classes(self, file_path, suffix, token_threshold):
        large_classes = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            lang = (
                "tsx"
                if suffix == "tsx"
                else "typescript" if suffix == "ts" else "javascript"
            )
            blocks = self.parser._parse_with_tree_sitter(content, file_path, lang)
            for block in blocks:
                if block.get("type") != "class":
                    continue
                tokens = block.get("tokens", [])
                if tokens:
                    class_name = tokens[0]
                    token_count = len(tokens)
                    if token_count >= token_threshold:
                        location = block.get("location", {})
                        large_classes.append(
                            {
                                "name": class_name,
                                "file": str(file_path),
                                "start_line": location.get("start_line"),
                                "end_line": location.get("end_line"),
                                "token_count": token_count,
                                "severity": compute_severity(
                                    token_count, token_threshold
                                ),
                            }
                        )
        except Exception:
            pass
        return large_classes

    def _find_large_cs_classes(self, file_path, token_threshold):
        large_classes = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            blocks = self.parser._parse_with_tree_sitter(content, file_path, "csharp")
            for block in blocks:
                tokens = block.get("tokens", [])
                if tokens:
                    class_name = tokens[0] if tokens else "unknown"
                    token_count = len(tokens)
                    if token_count >= token_threshold:
                        location = block.get("location", {})
                        large_classes.append(
                            {
                                "name": class_name,
                                "file": str(file_path),
                                "start_line": location.get("start_line"),
                                "end_line": location.get("end_line"),
                                "token_count": token_count,
                                "severity": compute_severity(
                                    token_count, token_threshold
                                ),
                            }
                        )
        except Exception:
            pass
        return large_classes

    def find_large_classes(self, files, token_threshold=300, top_n=None):
        """
        Main function: Find classes in a list of Python, JS/JSX/TS/TSX, or C# files whose token count exceeds the threshold.
        Returns a list of dicts with class name, file, start/end line, and token count, including threshold and top_n for reporting.
        """
        all_results = []
        for file_path in files:
            suffix = str(file_path).split(".")[-1].lower()
            results = []
            if suffix == "py":
                results = self._find_large_python_classes(file_path, token_threshold)
            elif suffix in {"js", "jsx", "ts", "tsx"}:
                results = self._find_large_js_classes(
                    file_path, suffix, token_threshold
                )
            elif suffix == "cs":
                results = self._find_large_cs_classes(file_path, token_threshold)
            all_results.extend(results)
        all_results = sorted(all_results, key=lambda x: x["token_count"], reverse=True)
        if top_n is not None:
            all_results = all_results[:top_n]
        self.results = all_results
