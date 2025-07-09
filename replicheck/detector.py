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
            List of duplicate code blocks with their locations and similarity scores
        """
        duplicates = []

        # Sort blocks by size to compare similar-sized blocks first
        code_blocks.sort(key=lambda x: len(x["tokens"]))

        # Early filtering: skip blocks that are too different in size
        for i, block1 in enumerate(tqdm(code_blocks, desc="Comparing", leave=False)):
            size1 = len(block1["tokens"])

            # Skip empty blocks or blocks smaller than min_size
            if size1 < self.min_size:
                continue

            for block2 in code_blocks[i + 1 :]:
                size2 = len(block2["tokens"])

                # Skip empty blocks or blocks smaller than min_size
                if size2 < self.min_size:
                    continue

                # Skip if size difference is too large
                if abs(size1 - size2) / max(size1, size2) > (1 - self.min_similarity):
                    continue

                similarity = calculate_similarity(block1["tokens"], block2["tokens"])

                if similarity >= self.min_similarity:
                    duplicates.append(
                        {
                            "block1": block1["location"],
                            "block2": block2["location"],
                            "similarity": similarity,
                            "size": size1,
                        }
                    )

        return duplicates
