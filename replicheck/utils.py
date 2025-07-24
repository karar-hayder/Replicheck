"""
Helper functions for code analysis.
"""

import hashlib
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import List, Optional, Set


def calculate_similarity(tokens1: List[str], tokens2: List[str]) -> float:
    """
    Calculate similarity between two token lists using Jaccard similarity.
    Much faster than SequenceMatcher for code comparison.

    Args:
        tokens1: First list of tokens
        tokens2: Second list of tokens

    Returns:
        Similarity score between 0 and 1
    """
    # Convert to sets for faster intersection/union operations
    set1 = set(tokens1)
    set2 = set(tokens2)

    # Calculate Jaccard similarity
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))

    return intersection / union if union > 0 else 0.0


def get_file_hash(file_path: Path) -> str:
    """
    Calculate SHA-256 hash of a file.

    Args:
        file_path: Path to the file

    Returns:
        SHA-256 hash of the file content
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def find_files(
    directory: Path,
    extensions: Set[str] = {".py"},
    ignore_dirs: Optional[List[str]] = None,
) -> List[Path]:
    """
    Find all files with specified extensions in a directory.
    Ignores specified directories and virtual environment folders.

    Args:
        directory: Directory to search in
        extensions: Set of file extensions to include (default: {".py"})
        ignore_dirs: List of directory names to ignore (default: None)

    Returns:
        List of file paths
    """
    files = []
    # Default ignored directories
    venv_dirs = {".venv", "venv", "env", "ENV"}
    # Add user-specified directories to ignore
    if ignore_dirs:
        venv_dirs.update(ignore_dirs)

    for ext in extensions:
        for file_path in directory.glob(f"**/*{ext}"):
            # Skip files in ignored directories
            if not any(ignored_dir in file_path.parts for ignored_dir in venv_dirs):
                files.append(file_path)

    return files


def compute_severity(value, threshold):
    """
    Compute severity level and emoji based on how much value exceeds threshold.
    Returns a string like 'Low 🟢', 'Medium 🟡', 'High 🟠', 'Critical 🔴'.
    """
    ratio = value / threshold if threshold else 0
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


def analyze_cyclomatic_complexity(file_path: Path, threshold: int = 10):
    """
    Analyze cyclomatic complexity of a Python file using radon.

    Args:
        file_path: Path to the Python file
        threshold: Complexity threshold to flag

    Returns:
        List of dicts with function/method name, complexity, and location if above threshold
    """
    from radon.complexity import cc_visit

    results = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
        for block in cc_visit(code):
            if block.complexity >= threshold:
                results.append(
                    {
                        "name": block.name,
                        "complexity": block.complexity,
                        "lineno": block.lineno,
                        "endline": getattr(block, "endline", None),
                        "file": str(file_path),
                        "threshold": threshold,
                        "severity": compute_severity(block.complexity, threshold),
                    }
                )
    except Exception as e:
        pass
    return results


def analyze_js_cyclomatic_complexity(file_path: Path, threshold: int = 10):
    """
    Analyze cyclomatic complexity of a JS file using typhonjs-escomplex via Node.js helper script.

    Args:
        file_path: Path to the JS file
        threshold: Complexity threshold to flag

    Returns:
        List of dicts with function/method name, complexity, and location if above threshold
    """
    import subprocess
    import json
    import sys
    from pathlib import Path

    results = []
    helper_path = Path(__file__).parent.parent / "utils" / "helpers.js"
    try:
        proc = subprocess.run(
            ["node", str(helper_path), str(file_path)],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if proc.returncode != 0:
            return []
        functions = json.loads(proc.stdout)
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
                        "severity": compute_severity(
                            fn.get("complexity", 0), threshold
                        ),
                    }
                )
    except Exception:
        pass
    return results


def analyze_cs_cyclomatic_complexity(file_path: Path, threshold: int = 10):
    """
    Analyze cyclomatic complexity of a C# file using the compiled ComplexityAnalyzer.exe.

    Args:
        file_path: Path to the C# (.cs) file
        threshold: Complexity threshold to flag

    Returns:
        List of dicts with function/method name, complexity, and location if above threshold
    """
    import subprocess
    import json
    from pathlib import Path

    results = []
    # Path to the compiled C# analyzer executable
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
        proc = subprocess.run(
            [str(exe_path), str(file_path)],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if proc.returncode != 0:
            return []

        functions = json.loads(proc.stdout)
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
                        "severity": compute_severity(
                            fn.get("Complexity", 0), threshold
                        ),
                    }
                )
    except Exception:
        pass
    return results


def find_large_files(files, token_threshold=500, top_n=None):
    """
    Find files whose total token count exceeds the threshold.
    Returns a list of dicts with file path and token count, including threshold and top_n for reporting.
    """
    import tokenize
    import re
    from replicheck.parser import CodeParser

    large_files = []
    parser = CodeParser()

    def js_tokenize(code):
        return re.findall(r"\w+|[^\s\w]", code, re.UNICODE)

    large_files = []
    for file_path in files:
        suffix = str(file_path).lower()
        if suffix.endswith(".py"):
            try:
                with open(file_path, "rb") as f:
                    tokens = list(tokenize.tokenize(f.readline))
                # Exclude ENCODING/ENDMARKER tokens
                token_count = sum(
                    1
                    for t in tokens
                    if t.type not in (tokenize.ENCODING, tokenize.ENDMARKER)
                )
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
            except Exception:
                pass
        elif suffix.endswith((".js", ".jsx", ".ts", ".tsx")):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    code = f.read()
                if suffix.endswith(".ts") or suffix.endswith(".tsx"):
                    lang = "tsx" if suffix.endswith(".tsx") else "typescript"
                    blocks = parser._parse_with_tree_sitter(code, file_path, lang)
                    token_count = sum(len(block["tokens"]) for block in blocks)
                else:
                    tokens = js_tokenize(code)
                    token_count = len(tokens)
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
            except Exception:
                pass

        elif suffix.endswith(".cs"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                blocks = parser._parse_with_tree_sitter(content, file_path, "csharp")
                token_count = sum(len(block["tokens"]) for block in blocks)
                if token_count < token_threshold // 2:
                    import re

                    raw_tokens = re.findall(r"\w+|[^\s\w]", content, re.UNICODE)
                    token_count = len(raw_tokens)
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
            except Exception:
                pass
    return large_files


def find_large_classes(file_path, token_threshold=300, top_n=None):
    """
    Find classes in a Python or JS/JSX file whose token count exceeds the threshold.
    Returns a list of dicts with class name, file, start/end line, and token count, including threshold and top_n for reporting.
    """
    import ast
    from replicheck.parser import CodeParser

    large_classes = []
    suffix = str(file_path).split(".")[-1].lower()
    parser = CodeParser()
    if suffix == "py":
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Get all tokens in the class node
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
                                "start_line": node.lineno,
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
    elif suffix in {"js", "jsx", "ts", "tsx"}:
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
                if block["type"] != "class":
                    continue
                tokens = block["tokens"]
                if tokens:
                    class_name = tokens[0]
                    token_count = len(tokens)
                    if token_count >= token_threshold:
                        large_classes.append(
                            {
                                "name": class_name,
                                "file": str(file_path),
                                "start_line": block["location"]["start_line"],
                                "end_line": block["location"].get("end_line"),
                                "token_count": token_count,
                                "threshold": token_threshold,
                                "top_n": top_n,
                                "severity": compute_severity(
                                    token_count, token_threshold
                                ),
                            }
                        )
        except Exception:
            pass

    elif suffix == "cs":
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            blocks = parser._parse_with_tree_sitter(content, file_path, "csharp")

            for block in blocks:
                tokens = block["tokens"]
                if tokens:
                    class_name = tokens[0] if tokens else "unknown"
                    token_count = len(tokens)
                    if token_count >= token_threshold:
                        large_classes.append(
                            {
                                "name": class_name,
                                "file": str(file_path),
                                "start_line": block["location"]["start_line"],
                                "end_line": block["location"].get("end_line"),
                                "token_count": token_count,
                                "threshold": token_threshold,
                                "top_n": top_n,
                                "severity": compute_severity(
                                    token_count, token_threshold
                                ),
                            }
                        )
        except Exception:
            pass
    return large_classes


def find_todo_fixme_comments(files):
    """
    Scan files for TODO and FIXME comments.
    Uses tree-sitter for JS/TS/TSX/JSX/C# and regex for Python.
    Returns list of dicts: file, line number, comment type, and comment text.
    """
    import re
    from replicheck.parser import get_language, get_parser

    results = []

    py_pattern = re.compile(r"#.*?(TODO|FIXME)(:|\b)(.*)", re.IGNORECASE)

    # Languages using tree-sitter to extract comments
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

            # Python handled with regex
            if ext == ".py":
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

            # Use Tree-sitter for typed languages
            elif ext in ts_languages:
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
                    match = re.search(
                        r"(TODO|FIXME)(:|\b)(.*)", comment_text, re.IGNORECASE
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

        except Exception as e:
            pass

    return results
