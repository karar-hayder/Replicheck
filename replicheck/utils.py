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
