# --- TODO/FIXME Comments ---
from replicheck.parser import get_language, get_parser


class TodoFixmeDetector:
    def __init__(self):
        self.results = []

    def _find_todo_fixme_in_python(self, file_path, content, py_pattern, results):
        for lineno, line in enumerate(content.splitlines(), 1):
            match = py_pattern.search(line)
            if match:
                results.append(
                    {
                        "file": str(file_path),
                        "line": lineno,
                        "type": match.group(1).upper(),
                        "text": match.group(3).strip(),
                    }
                )

    def _find_todo_fixme_in_treesitter(
        self, file_path, content, ext, ts_languages, results
    ):
        import re

        language_name = ts_languages[ext]
        parser = get_parser(language_name)
        language = get_language(language_name)
        tree = parser.parse(bytes(content, "utf-8"))
        root = tree.root_node
        query = language.query(
            """
            (comment) @comment
        """
        )
        captures = query.captures(root)
        for node, _ in captures:
            comment_text = content[node.start_byte : node.end_byte]
            # Expanded: match all TODO/FIXME and common variants, optionally with leading/trailing whitespace, and allow for case-insensitive matches
            # Also, allow for possible leading comment markers (//, /*, *, #) and whitespace before the keyword
            # Variants include: TODO, FIXME, BUG, HACK, XXX, NOTE, OPTIMIZE, REVIEW, WARNING, TEMP, TBD, TO-DO, TO DO, TOFIX, TO_FIX, TO-FIX, etc.
            match = re.search(
                r"(?:^|[\s#/*])\b("
                r"TODO|TO[\s_-]?DO|TO[\s_-]?FIX|FIXME|FIX[\s_-]?ME|TOFIX|BUG|HACK|XXX|NOTE|OPTIMIZE|REVIEW|WARNING|TEMP|TBD"
                r")\b\s*(:)?\s*(.*)",
                comment_text,
                re.IGNORECASE,
            )
            if match:
                results.append(
                    {
                        "file": str(file_path),
                        "line": node.start_point[0] + 1,
                        "type": match.group(1).upper(),
                        "text": match.group(3).strip(),
                    }
                )

    def find_todo_fixme_comments(self, files):
        """
        Scan files for TODO and FIXME comments.
        Uses tree-sitter for JS/TS/TSX/JSX/C# and regex for Python.
        Returns list of dicts: file, line number, comment type, and comment text.
        Also sets self.results to the list of findings.
        """
        import re

        results = []
        py_pattern = re.compile(
            r"#.*?(TODO|TO[\s_-]?DO|TO[\s_-]?FIX|FIXME|FIX[\s_-]?ME|TOFIX|BUG|HACK|XXX|NOTE|OPTIMIZE|REVIEW|WARNING|TEMP|TBD)(:|\b)(.*)",
            re.IGNORECASE,
        )
        ts_languages = {
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".cs": "csharp",
        }
        for file_path in files:
            ext = file_path.suffix.lower()
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if ext == ".py":
                    self._find_todo_fixme_in_python(
                        file_path, content, py_pattern, results
                    )
                elif ext in ts_languages:
                    self._find_todo_fixme_in_treesitter(
                        file_path, content, ext, ts_languages, results
                    )
            except Exception:
                pass
        self.results = results
