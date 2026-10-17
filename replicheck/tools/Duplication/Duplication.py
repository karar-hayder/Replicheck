"""
Core duplication detection logic.

Two modes, chosen by ``min_similarity``:

* ``min_similarity >= 1.0`` groups blocks whose token sequences are identical,
  keyed on the token tuple. This is the original behaviour and is unchanged.
* ``min_similarity < 1.0`` groups blocks whose token *sets* have a Jaccard
  similarity of at least the threshold, and reports the weakest link in each
  group.

The second mode cannot compare every pair: a large repository has tens of
thousands of blocks above ``min_size``, which is hundreds of millions of pairs.
Candidates are generated with the standard prefix filter instead, which is
exact — no pair that meets the threshold can be missed:

    If |A| <= |B| and |B| >= t*|A|, then a Jaccard similarity of t implies
    |A & B| >= t*|A|, and therefore the first (|A| - ceil(t*|A|) + 1) tokens of
    A, ordered by increasing document frequency, must intersect B.

So blocks are visited in increasing set size, each indexed by its prefix, and
each probed against the prefixes of the blocks already indexed. Every candidate
pair is then verified with the exact Jaccard ratio, so the filter can never
produce a false positive.
"""

import math
from collections import Counter, defaultdict
from typing import Any, Dict, List


class DuplicateDetector:
    def __init__(self, min_similarity: float = 0.8, min_size: int = 50):
        """
        Initialize the duplicate detector.

        Args:
            min_similarity: Minimum Jaccard similarity for two blocks to be
                reported together. 1.0 means exact matches only.
            min_size: Minimum size of code blocks to compare (in tokens)
        """
        self.min_similarity = min_similarity
        self.min_size = min_size

    def find_duplicates(
        self, code_blocks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Find duplicate code blocks.

        Args:
            code_blocks: List of parsed code blocks with their metadata

        Returns:
            List of groups, each with its locations, size, similarity and
            cross-file flag.
        """
        candidates = [
            block
            for block in code_blocks
            if len(block.get("tokens", [])) >= self.min_size
        ]
        if self.min_similarity >= 1.0:
            return self._group_exact(candidates)
        return self._group_similar(candidates)

    # ------------------------------------------------------------------
    # Exact matching
    # ------------------------------------------------------------------

    def _group_exact(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group blocks whose token sequences are identical."""
        by_tokens = defaultdict(list)
        for block in candidates:
            by_tokens[tuple(block.get("tokens", []))].append(block)

        groups = []
        for token_key, blocks in by_tokens.items():
            if len(blocks) < 2:
                continue
            groups.append(self._build_group(token_key, blocks, 1.0))
        return groups

    def _build_group(self, tokens, blocks, similarity):
        """Assemble one reported group from its member blocks."""
        locations = []
        for block in blocks:
            loc = block.get("location", {})
            locations.append(
                {
                    "file": loc.get("file"),
                    "start_line": loc.get("start_line"),
                    "end_line": loc.get("end_line"),
                }
            )
        files = {loc["file"] for loc in locations}
        return {
            "size": len(tokens),
            "num_duplicates": len(blocks),
            "locations": locations,
            "cross_file": len(files) > 1,
            "tokens": list(tokens),
            "similarity": similarity,
        }

    # ------------------------------------------------------------------
    # Similarity matching
    # ------------------------------------------------------------------

    def _group_similar(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Group blocks whose token sets are at least min_similarity alike.

        Blocks sharing an identical token set collapse into one node first:
        they are already equal to each other, so they only need comparing once.
        Repetitive corpora collapse by an order of magnitude; real code barely
        collapses at all.
        """
        node_sets: List[frozenset] = []
        node_blocks: List[List[int]] = []
        seen: Dict[frozenset, int] = {}
        for i, block in enumerate(candidates):
            key = frozenset(block.get("tokens", []))
            node = seen.get(key)
            if node is None:
                node = len(node_sets)
                seen[key] = node
                node_sets.append(key)
                node_blocks.append([])
            node_blocks[node].append(i)

        pairs = self._similar_pairs(node_sets)
        return self._components_to_groups(candidates, pairs, node_blocks)

    def _components_to_groups(self, candidates, pairs, node_blocks):
        """
        Merge verified pairs into groups using union-find.

        Each group reports the *lowest* similarity among the pairs that formed
        it, so a group held together by one weak link does not look as strong
        as its best pair.
        """
        parent = list(range(len(node_blocks)))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        weakest = {}
        for a, b, similarity in pairs:
            root_a, root_b = find(a), find(b)

            if root_a == root_b:
                # Both ends already sit in one component, so this edge can only
                # lower that component's recorded minimum.
                if similarity < weakest.get(root_a, 1.0):
                    weakest[root_a] = similarity
                continue

            # Two components are merging. The new root has to inherit the lower
            # of the two minimums as well as this edge, because the component
            # being absorbed is about to stop being a root and its weakest link
            # would otherwise be stranded - the group would then report a
            # similarity higher than one of the pairs that formed it.
            merged = min(weakest.get(root_a, 1.0), weakest.get(root_b, 1.0), similarity)
            parent[max(root_a, root_b)] = min(root_a, root_b)
            weakest[find(a)] = merged

        members = defaultdict(list)
        for node in range(len(node_blocks)):
            members[find(node)].extend(node_blocks[node])

        groups = []
        for root in sorted(members):
            block_indexes = members[root]
            if len(block_indexes) < 2:
                continue
            # Report the largest member's size and tokens as representative.
            representative = max(
                block_indexes, key=lambda i: len(candidates[i].get("tokens", []))
            )
            blocks = [candidates[i] for i in block_indexes]
            groups.append(
                self._build_group(
                    candidates[representative].get("tokens", []),
                    blocks,
                    weakest.get(root, 1.0),
                )
            )
        return groups

    def _similar_pairs(self, token_sets: List[frozenset]) -> List[tuple]:
        """
        Return (i, j, similarity) for every pair at or above the threshold.

        Candidates come from a prefix filter; each one is then verified with the
        exact Jaccard ratio, so the filter cannot introduce a false positive and
        (by the prefix guarantee) cannot miss a true one.
        """
        threshold = self.min_similarity

        # Global token order: rarest first, so a prefix holds the most
        # selective tokens and the posting lists stay short.
        frequencies = Counter()
        for token_set in token_sets:
            frequencies.update(token_set)

        # Visit blocks smallest-first: the prefix filter's guarantee is stated
        # for the smaller set of a pair, so every already-indexed block is a
        # valid smaller partner for the one being probed.
        visit_order = sorted(range(len(token_sets)), key=lambda i: len(token_sets[i]))

        index: Dict[str, List[int]] = {}
        pairs: List[tuple] = []

        for i in visit_order:
            token_set = token_sets[i]
            size = len(token_set)
            if size == 0:
                continue

            # A partner smaller than threshold*size cannot reach the threshold.
            smallest_partner = threshold * size
            shared_counts: Dict[int, int] = {}
            for token in token_set:
                for other in index.get(token, ()):
                    shared_counts[other] = shared_counts.get(other, 0) + 1

            for other in shared_counts:
                other_size = len(token_sets[other])
                if other_size < smallest_partner:
                    continue
                intersection = len(token_set & token_sets[other])
                union = size + other_size - intersection
                if union and intersection / union >= threshold:
                    pairs.append((other, i, intersection / union))

            prefix_length = max(size - math.ceil(threshold * size) + 1, 1)
            prefix = sorted(token_set, key=lambda token: frequencies[token])
            for token in prefix[:prefix_length]:
                index.setdefault(token, []).append(i)

        return pairs
