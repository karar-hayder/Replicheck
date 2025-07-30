"""
Tests for the code detector functionality.
"""

from replicheck.detector import DuplicateDetector


def test_find_duplicates():
    detector = DuplicateDetector(min_similarity=0.8, min_size=3)

    code_blocks = [
        {
            "location": {"file": "test1.py", "start_line": 1, "end_line": 5},
            "tokens": ["def", "test", "x", "y", "return"],
        },
        {
            "location": {"file": "test2.py", "start_line": 10, "end_line": 14},
            "tokens": ["def", "test", "x", "y", "return"],
        },
        {
            "location": {"file": "test3.py", "start_line": 20, "end_line": 25},
            "tokens": ["def", "other", "a", "b", "print"],
        },
    ]

    duplicates = detector.find_duplicates(code_blocks)

    assert len(duplicates) == 1
    assert duplicates[0]["similarity"] == 1.0
    assert duplicates[0]["size"] == 5
    assert len(duplicates[0]["locations"]) == 2
    files = {loc["file"] for loc in duplicates[0]["locations"]}
    assert "test1.py" in files and "test2.py" in files
