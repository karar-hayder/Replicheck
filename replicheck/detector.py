"""
Core duplication detection logic.
"""

from typing import Any, Dict, List

from tqdm import tqdm

from .utils import calculate_similarity


class DuplicateDetector:
    def __init__(self, min_similarity: float = 0.8, min_size: int = 50):
        """
        Initialize the duplicate detector.

        Args:
            min_similarity: Minimum similarity threshold (0.0 to 1.0)
            min_size: Minimum size of code blocks to compare (in tokens)
        """
        self.min_similarity = min_similarity
        self.min_size = min_size

    def find_duplicates(
        self, code_blocks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Find duplicate code blocks based on similarity threshold.
        Args:
            code_blocks: List of parsed code blocks with their metadata
        Returns:
            List of duplicate groups with their locations, similarity, size, and cross-file flag
        """
        # Group duplicates by hash of tokens for exact/near-exact matches
        from collections import defaultdict

        duplicates_by_hash = defaultdict(list)
        for block in code_blocks:
            if len(block["tokens"]) < self.min_size:
                continue
            # Use tuple of tokens as a hashable key for grouping
            key = tuple(block["tokens"])
            duplicates_by_hash[key].append(block)

        groups = []
        for token_key, blocks in duplicates_by_hash.items():
            if len(blocks) < 2:
                continue  # Only interested in actual duplicates
            files = {b["location"]["file"] for b in blocks}
            cross_file = len(files) > 1
            group = {
                "size": len(token_key),
                "num_duplicates": len(blocks),
                "locations": [b["location"] for b in blocks],
                "cross_file": cross_file,
                "tokens": token_key,
                "similarity": 1.0,  # Exact match
            }
            groups.append(group)
        return groups
