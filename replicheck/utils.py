"""
Helper functions for code analysis.
"""

import hashlib
from pathlib import Path
from typing import List, Optional, Set


def calculate_similarity(tokens1: List[str], tokens2: List[str]) -> float:
    """
    Calculate similarity between two token lists using Jaccard similarity.
    Much faster than SequenceMatcher for code comparison.
    """
    set1 = set(tokens1)
    set2 = set(tokens2)
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union else 0.0


def get_file_hash(file_path: Path) -> str:
    """
    Calculate SHA-256 hash of a file.
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _get_ignored_dirs(ignore_dirs: Optional[List[str]] = None) -> set:
    venv_dirs = {".venv", "venv", "env", "ENV"}
    if ignore_dirs:
        venv_dirs.update(ignore_dirs)
    return venv_dirs


def _is_in_ignored_dirs(file_path: Path, ignored_dirs: set) -> bool:
    return any(ignored in file_path.parts for ignored in ignored_dirs)


def find_files(
    directory: Path,
    extensions: Optional[Set[str]] = None,
    ignore_dirs: Optional[List[str]] = None,
) -> List[Path]:
    """
    Find all files with specified extensions in a directory.
    Ignores specified directories and virtual environment folders.
    """
    if extensions is None:
        extensions = {".py"}
    files = []
    ignored_dirs = _get_ignored_dirs(ignore_dirs)
    for ext in extensions:
        for file_path in directory.glob(f"**/*{ext}"):
            if not _is_in_ignored_dirs(file_path, ignored_dirs):
                files.append(file_path)
    return files


def compute_severity(value, threshold):
    """
    Compute severity level and emoji based on how much value exceeds threshold.
    Returns a string like 'Low 🟢', 'Medium 🟡', 'High 🟠', 'Critical 🔴'.
    """
    if threshold == 0:
        return "None"
    ratio = value / threshold
    if ratio >= 3:
        return "Critical 🔴"
    elif ratio >= 2:
        return "High 🟠"
    elif ratio >= 1.5:
        return "Medium 🟡"
    elif ratio >= 1:
        return "Low 🟢"
    else:
        return "None"


# --- Cyclomatic Complexity Analysis ---


def _read_file_content(file_path: Path, mode="r", encoding="utf-8"):
    with open(file_path, mode, encoding=encoding) as f:
        return f.read()


def _analyze_python_cyclomatic_complexity(code: str, file_path: Path, threshold: int):
    from radon.complexity import cc_visit

    results = []
    for block in cc_visit(code):
        if getattr(block, "complexity", 0) >= threshold:
            results.append(
                {
                    "name": getattr(block, "name", "<unknown>"),
                    "complexity": getattr(block, "complexity", 0),
                    "lineno": getattr(block, "lineno", None),
                    "endline": getattr(block, "endline", None),
                    "file": str(file_path),
                    "threshold": threshold,
                    "severity": compute_severity(
                        getattr(block, "complexity", 0), threshold
                    ),
                }
            )
    return results


def analyze_cyclomatic_complexity(file_path: Path, threshold: int = 10):
    """
    Analyze cyclomatic complexity of a Python file using radon.
    """
    try:
        code = _read_file_content(file_path)
        return _analyze_python_cyclomatic_complexity(code, file_path, threshold)
    except Exception:
        return []


def _run_node_helper(helper_path: Path, file_path: Path):
    import subprocess

    try:
        proc = subprocess.run(
            ["node", str(helper_path), str(file_path)],
            capture_output=True,
            text=True,
            timeout=20,
        )
        return proc
    except Exception:

        class DummyProc:
            returncode = 1
            stdout = ""

        return DummyProc()


def _parse_js_complexity_output(proc, file_path, threshold):
    import json

    results = []
    if getattr(proc, "returncode", 1) != 0:
        return []
    try:
        functions = json.loads(proc.stdout)
    except Exception:
        return []
    for fn in functions:
        if fn.get("complexity", 0) >= threshold:
            results.append(
                {
                    "name": fn.get("name", "<anonymous>"),
                    "complexity": fn.get("complexity"),
                    "lineno": fn.get("lineno"),
                    "endline": fn.get("endline"),
                    "file": str(file_path),
                    "threshold": threshold,
                    "severity": compute_severity(fn.get("complexity", 0), threshold),
                }
            )
    return results


def analyze_js_cyclomatic_complexity(file_path: Path, threshold: int = 10):
    """
    Analyze cyclomatic complexity of a JS file using typhonjs-escomplex via Node.js helper script.
    """
    from pathlib import Path

    helper_path = Path(__file__).parent.parent / "utils" / "helpers.js"
    try:
        proc = _run_node_helper(helper_path, file_path)
        return _parse_js_complexity_output(proc, file_path, threshold)
    except Exception:
        return []


def _run_cs_analyzer(exe_path: Path, file_path: Path):
    import subprocess

    try:
        proc = subprocess.run(
            [str(exe_path), str(file_path)],
            capture_output=True,
            text=True,
            timeout=20,
        )
        return proc
    except Exception:

        class DummyProc:
            returncode = 1
            stdout = ""

        return DummyProc()


def _parse_cs_complexity_output(proc, file_path, threshold):
    import json

    results = []
    if getattr(proc, "returncode", 1) != 0:
        return []
    try:
        functions = json.loads(proc.stdout)
    except Exception:
        return []
    for fn in functions:
        if fn.get("Complexity", 0) >= threshold:
            results.append(
                {
                    "name": fn.get("Name", "<anonymous>"),
                    "complexity": fn.get("Complexity"),
                    "lineno": fn.get("LineNo"),
                    "endline": fn.get("EndLine"),
                    "file": str(file_path),
                    "threshold": threshold,
                    "severity": compute_severity(fn.get("Complexity", 0), threshold),
                }
            )
    return results


def analyze_cs_cyclomatic_complexity(file_path: Path, threshold: int = 10):
    """
    Analyze cyclomatic complexity of a C# file using the compiled ComplexityAnalyzer.exe.
    """
    from pathlib import Path

    exe_path = (
        Path(__file__).parent.parent
        / "utils"
        / "C#"
        / "ComplexityAnalyzer"
        / "bin"
        / "Release"
        / "net9.0"
        / "win-x64"
        / "ComplexityAnalyzer.exe"
    )
    try:
        proc = _run_cs_analyzer(exe_path, file_path)
        return _parse_cs_complexity_output(proc, file_path, threshold)
    except Exception:
        return []


# --- Large Files ---


def _token_count_python(file_path):
    import tokenize

    try:
        with open(file_path, "rb") as f:
            tokens = list(tokenize.tokenize(f.readline))
        return sum(
            1 for t in tokens if t.type not in (tokenize.ENCODING, tokenize.ENDMARKER)
        )
    except Exception:
        return 0


def _token_count_js(code):
    import re

    return len(re.findall(r"\w+|[^\s\w]", code, re.UNICODE))


def _token_count_ts(code, file_path, parser, lang):
    blocks = parser._parse_with_tree_sitter(code, file_path, lang)
    return sum(len(block["tokens"]) for block in blocks)


def _token_count_cs(content, file_path, parser):
    """
    Count tokens in a C# file. If tree-sitter fails to find any class/struct blocks,
    or the count is suspiciously low, fall back to counting all tokens in the file (including global statements).
    """
    import re

    blocks = parser._parse_with_tree_sitter(content, file_path, "csharp")
    block_token_count = sum(len(block["tokens"]) for block in blocks) if blocks else 0

    # Fallback: count all tokens in the file (including global statements)
    raw_tokens = re.findall(r"\w+|[^\s\w]", content, re.UNICODE)
    fallback_count = len(raw_tokens)

    # If tree-sitter found any blocks and the count is not suspiciously low, use it.
    # "Suspiciously low" is arbitrarily chosen as < 10 or less than 10% of fallback.
    if block_token_count >= 10 and block_token_count >= 0.1 * fallback_count:
        return block_token_count
    else:
        return fallback_count


def find_large_files(files, token_threshold=500, top_n=None):
    """
    Find files whose total token count exceeds the threshold.
    Returns a list of dicts with file path and token count, including threshold and top_n for reporting.
    """
    from replicheck.parser import CodeParser

    parser = CodeParser()
    large_files = []
    for file_path in files:
        suffix = str(file_path).lower()
        token_count = 0
        if suffix.endswith(".py"):
            token_count = _token_count_python(file_path)
        elif suffix.endswith((".js", ".jsx", ".ts", ".tsx")):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    code = f.read()
                if suffix.endswith(".ts") or suffix.endswith(".tsx"):
                    lang = "tsx" if suffix.endswith(".tsx") else "typescript"
                    token_count = _token_count_ts(code, file_path, parser, lang)
                else:
                    token_count = _token_count_js(code)
            except Exception:
                token_count = 0
        elif suffix.endswith(".cs"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                token_count = _token_count_cs(content, file_path, parser)
            except Exception:
                token_count = 0
        if token_count >= token_threshold:
            large_files.append(
                {
                    "file": str(file_path),
                    "token_count": token_count,
                    "threshold": token_threshold,
                    "top_n": top_n,
                    "severity": compute_severity(token_count, token_threshold),
                }
            )
    return large_files


# --- Large Classes ---


def _find_large_python_classes(file_path, token_threshold, top_n):
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
                            "threshold": token_threshold,
                            "top_n": top_n,
                            "severity": compute_severity(
                                len(class_tokens), token_threshold
                            ),
                        }
                    )
    except Exception:
        pass
    return large_classes


def _find_large_js_classes(file_path, suffix, token_threshold, top_n, parser):
    large_classes = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        lang = (
            "tsx"
            if suffix == "tsx"
            else "typescript" if suffix == "ts" else "javascript"
        )
        blocks = parser._parse_with_tree_sitter(content, file_path, lang)
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
                            "threshold": token_threshold,
                            "top_n": top_n,
                            "severity": compute_severity(token_count, token_threshold),
                        }
                    )
    except Exception:
        pass
    return large_classes


def _find_large_cs_classes(file_path, token_threshold, top_n, parser):
    large_classes = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        blocks = parser._parse_with_tree_sitter(content, file_path, "csharp")
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
                            "threshold": token_threshold,
                            "top_n": top_n,
                            "severity": compute_severity(token_count, token_threshold),
                        }
                    )
    except Exception:
        pass
    return large_classes


def find_large_classes(file_path, token_threshold=300, top_n=None):
    """
    Find classes in a Python or JS/JSX file whose token count exceeds the threshold.
    Returns a list of dicts with class name, file, start/end line, and token count, including threshold and top_n for reporting.
    """
    from replicheck.parser import CodeParser

    suffix = str(file_path).split(".")[-1].lower()
    parser = CodeParser()
    if suffix == "py":
        return _find_large_python_classes(file_path, token_threshold, top_n)
    elif suffix in {"js", "jsx", "ts", "tsx"}:
        return _find_large_js_classes(file_path, suffix, token_threshold, top_n, parser)
    elif suffix == "cs":
        return _find_large_cs_classes(file_path, token_threshold, top_n, parser)
    return []


# --- TODO/FIXME Comments ---


def _find_todo_fixme_in_python(file_path, content, py_pattern, results):
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


def _find_todo_fixme_in_treesitter(file_path, content, ext, ts_languages, results):
    import re

    from replicheck.parser import get_language, get_parser

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
        match = re.search(r"(TODO|FIXME)(:|\b)(.*)", comment_text, re.IGNORECASE)
        if match:
            results.append(
                {
                    "file": str(file_path),
                    "line": node.start_point[0] + 1,
                    "type": match.group(1).upper(),
                    "text": match.group(3).strip(),
                }
            )


def find_todo_fixme_comments(files):
    """
    Scan files for TODO and FIXME comments.
    Uses tree-sitter for JS/TS/TSX/JSX/C# and regex for Python.
    Returns list of dicts: file, line number, comment type, and comment text.
    """
    import re

    results = []
    py_pattern = re.compile(r"#.*?(TODO|FIXME)(:|\b)(.*)", re.IGNORECASE)
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
                _find_todo_fixme_in_python(file_path, content, py_pattern, results)
            elif ext in ts_languages:
                _find_todo_fixme_in_treesitter(
                    file_path, content, ext, ts_languages, results
                )
        except Exception:
            pass
    return results
