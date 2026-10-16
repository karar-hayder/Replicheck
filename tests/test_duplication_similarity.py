"""
Tests for similarity-based duplicate detection.

``min_similarity`` used to be stored and never read, so every threshold gave
the same answer and only byte-identical token sequences were reported. These
tests pin the behaviour that replaced it.
"""

import random

from replicheck.tools.Duplication.Duplication import DuplicateDetector


def block(tokens, file="a.py", start=1):
    return {
        "location": {"file": file, "start_line": start, "end_line": start + 5},
        "tokens": list(tokens),
    }


def brute_force_pairs(token_sets, threshold):
    """Reference implementation: compare every pair, no candidate generation."""
    pairs = set()
    for i in range(len(token_sets)):
        for j in range(i + 1, len(token_sets)):
            a, b = token_sets[i], token_sets[j]
            union = len(a | b)
            if union and len(a & b) / union >= threshold:
                pairs.add((i, j))
    return pairs


def random_token_sets(count, universe, max_size, seed):
    rng = random.Random(seed)  # noqa: S311 - deterministic test fixture
    return [
        frozenset(rng.sample(range(universe), rng.randint(1, max_size)))
        for _ in range(count)
    ]


# ----------------------------------------------------------------------
# The regression this feature exists to fix
# ----------------------------------------------------------------------


def test_min_similarity_actually_changes_the_result():
    """Before the fix every threshold returned the same groups."""
    near_a = ["def", "f", "x", "y", "z", "return", "x", "y"]
    near_b = ["def", "f", "x", "y", "z", "return", "x", "w"]
    blocks = [block(near_a, "a.py"), block(near_b, "b.py")]

    strict = DuplicateDetector(min_similarity=0.99, min_size=3).find_duplicates(blocks)
    loose = DuplicateDetector(min_similarity=0.5, min_size=3).find_duplicates(blocks)

    assert strict == []
    assert len(loose) == 1


def test_exact_mode_at_one_reports_only_identical_sequences():
    """min_similarity=1.0 keeps the original exact-tuple behaviour."""
    same = ["def", "f", "x", "return"]
    near = ["def", "f", "y", "return"]
    blocks = [block(same, "a.py"), block(same, "b.py"), block(near, "c.py")]

    groups = DuplicateDetector(min_similarity=1.0, min_size=3).find_duplicates(blocks)

    assert len(groups) == 1
    assert groups[0]["num_duplicates"] == 2
    assert groups[0]["similarity"] == 1.0
    files = {loc["file"] for loc in groups[0]["locations"]}
    assert files == {"a.py", "b.py"}


def test_token_order_is_ignored_below_one():
    """Set similarity means a reordered body still counts as a near-duplicate."""
    blocks = [
        block(["def", "f", "x", "y", "return"], "a.py"),
        block(["return", "y", "x", "f", "def"], "b.py"),
    ]
    exact = DuplicateDetector(min_similarity=1.0, min_size=3).find_duplicates(blocks)
    fuzzy = DuplicateDetector(min_similarity=0.9, min_size=3).find_duplicates(blocks)

    assert exact == []
    assert len(fuzzy) == 1
    assert fuzzy[0]["similarity"] == 1.0


# ----------------------------------------------------------------------
# Candidate generation must be exact
# ----------------------------------------------------------------------


def test_prefix_filter_matches_brute_force_across_thresholds():
    """
    The prefix filter may only *skip* pairs it can prove are below threshold.
    Compare against an exhaustive search over several thresholds and corpus
    shapes, including a heavily repetitive one.
    """
    for seed in (1, 7, 42):
        token_sets = random_token_sets(count=120, universe=40, max_size=12, seed=seed)
        for threshold in (0.3, 0.5, 0.7, 0.8, 0.9, 0.95, 1.0):
            detector = DuplicateDetector(min_similarity=threshold, min_size=1)
            found = {
                (min(a, b), max(a, b))
                for a, b, _ in detector._similar_pairs(token_sets)
            }
            expected = brute_force_pairs(token_sets, threshold)
            assert found == expected, (
                f"seed={seed} threshold={threshold}: "
                f"missing={len(expected - found)} extra={len(found - expected)}"
            )


def test_prefix_filter_matches_brute_force_on_duplicate_heavy_input():
    """A corpus where most sets are copies of a handful of shapes."""
    base = [
        frozenset(range(0, 10)),
        frozenset(range(5, 15)),
        frozenset(range(10, 20)),
        frozenset(range(0, 20)),
    ]
    token_sets = [base[i % len(base)] | frozenset({i + 100}) for i in range(60)]

    for threshold in (0.5, 0.8, 0.95):
        detector = DuplicateDetector(min_similarity=threshold, min_size=1)
        found = {
            (min(a, b), max(a, b)) for a, b, _ in detector._similar_pairs(token_sets)
        }
        assert found == brute_force_pairs(token_sets, threshold)


# ----------------------------------------------------------------------
# Group semantics
# ----------------------------------------------------------------------


def test_group_reports_the_weakest_link():
    """
    A chain A~B~C where A and C are below threshold must still report the
    weakest pair, not the best one.

    J(A,B) = 10/15 = 0.67, J(B,C) = 10/20 = 0.50, J(A,C) = 5/20 = 0.25.
    """
    a = {f"t{i}" for i in range(0, 10)}
    b = {f"t{i}" for i in range(0, 15)}
    c = {f"t{i}" for i in range(5, 20)}

    detector = DuplicateDetector(min_similarity=0.5, min_size=1)
    groups = detector.find_duplicates(
        [block(sorted(a), "a.py"), block(sorted(b), "b.py"), block(sorted(c), "c.py")]
    )

    assert len(groups) == 1
    assert groups[0]["num_duplicates"] == 3
    # The weakest of the two links that formed the group, not 1.0 or the best.
    assert groups[0]["similarity"] == 0.5


def test_identical_blocks_collapse_into_a_single_group():
    tokens = ["def", "f", "x", "return"]
    blocks = [block(tokens, f"m{i}.py") for i in range(5)]

    groups = DuplicateDetector(min_similarity=0.8, min_size=3).find_duplicates(blocks)

    assert len(groups) == 1
    assert groups[0]["num_duplicates"] == 5
    assert groups[0]["similarity"] == 1.0
    assert groups[0]["cross_file"] is True


def test_dissimilar_blocks_are_not_grouped():
    blocks = [
        block(["def", "alpha", "beta", "gamma"], "a.py"),
        block(["class", "delta", "epsilon", "zeta"], "b.py"),
    ]
    assert (
        DuplicateDetector(min_similarity=0.8, min_size=3).find_duplicates(blocks) == []
    )


def test_blocks_below_min_size_are_ignored():
    blocks = [block(["def", "f"], "a.py"), block(["def", "f"], "b.py")]
    assert (
        DuplicateDetector(min_similarity=0.8, min_size=50).find_duplicates(blocks) == []
    )


def test_empty_input():
    assert DuplicateDetector().find_duplicates([]) == []


def test_single_block_is_not_a_duplicate():
    assert (
        DuplicateDetector(min_similarity=0.8, min_size=1).find_duplicates(
            [block(["def", "f", "x"], "a.py")]
        )
        == []
    )


def test_groups_are_deterministic():
    token_sets = random_token_sets(count=60, universe=25, max_size=10, seed=3)
    blocks = [block(sorted(s), f"m{i}.py") for i, s in enumerate(token_sets)]

    first = DuplicateDetector(min_similarity=0.6, min_size=1).find_duplicates(blocks)
    second = DuplicateDetector(min_similarity=0.6, min_size=1).find_duplicates(blocks)

    assert first == second
