"""
Core duplication detection logic.
"""

from typing import Any, Dict, List


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
            List of duplicate groups with their locations, similarity, size, and cross-file flag.
        """
        from collections import defaultdict

        # Group code blocks by their token sequence (as a tuple)
        duplicates_by_tokens = defaultdict(list)
        for block in code_blocks:
            tokens = block.get("tokens", [])
            if len(tokens) < self.min_size:
                continue
            key = tuple(tokens)
            duplicates_by_tokens[key].append(block)

        duplicate_groups = []
        for token_key, blocks in duplicates_by_tokens.items():
            if len(blocks) < 2:
                continue  # Only interested in actual duplicates

            files = {b["location"]["file"] for b in blocks}
            cross_file = len(files) > 1

            # Ensure each location is a dict with file, start_line, end_line
            locations = []
            for b in blocks:
                loc = b.get("location", {})
                # Defensive: ensure keys exist
                locations.append(
                    {
                        "file": loc.get("file"),
                        "start_line": loc.get("start_line"),
                        "end_line": loc.get("end_line"),
                    }
                )

            group = {
                "size": len(token_key),
                "num_duplicates": len(blocks),
                "locations": locations,
                "cross_file": cross_file,
                "tokens": list(token_key),
                "similarity": 1.0,  # Exact match
            }
            duplicate_groups.append(group)

        return duplicate_groups
