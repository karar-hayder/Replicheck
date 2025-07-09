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
                    }
                )
    except Exception as e:
        # Optionally log or print error
        pass
    return results


def find_large_files(files, token_threshold=500, top_n=None):
    """
    Find files whose total token count exceeds the threshold.
    Returns a list of dicts with file path and token count, including threshold and top_n for reporting.
    """
    import tokenize

    large_files = []
    for file_path in files:
        if str(file_path).endswith(".py"):
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
                        }
                    )
            except Exception:
                pass
    return large_files


def find_large_classes(file_path, token_threshold=300, top_n=None):
    """
    Find classes in a Python file whose token count exceeds the threshold.
    Returns a list of dicts with class name, file, start/end line, and token count, including threshold and top_n for reporting.
    """
    import ast

    large_classes = []
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
                        }
                    )
    except Exception:
        pass
    return large_classes


def find_todo_fixme_comments(files):
    """
    Scan files for TODO and FIXME comments.
    Returns a list of dicts with file, line number, and comment text.
    """
    import re

    results = []
    pattern = re.compile(r"#.*?(TODO|FIXME)(:|\b)(.*)", re.IGNORECASE)
    for file_path in files:
        if str(file_path).endswith(".py"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for lineno, line in enumerate(f, 1):
                        match = pattern.search(line)
                        if match:
                            results.append(
                                {
                                    "file": str(file_path),
                                    "line": lineno,
                                    "type": match.group(1).upper(),
                                    "text": match.group(3).strip(),
                                }
                            )
            except Exception:
                pass
    return results
