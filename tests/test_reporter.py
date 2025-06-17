"""
Tests for the reporter module.
"""

import json
from pathlib import Path

import pytest

from replicheck.reporter import Reporter


def test_reporter_text_output(tmp_path):
    """Test text report generation."""
    reporter = Reporter(output_format="text")
    duplicates = [
        {
            "similarity": 0.95,
            "size": 10,
            "block1": {"file": "file1.py", "start_line": 1, "end_line": 5},
            "block2": {"file": "file2.py", "start_line": 10, "end_line": 14},
        }
    ]
    output_file = tmp_path / "report.txt"
    reporter.generate_report(duplicates, output_file)

    content = output_file.read_text()
    assert "Code Duplication Report" in content
    assert "Duplication #1" in content
    assert "Similarity: 95.00%" in content
    assert "Size: 10 tokens" in content
    assert "Location 1: file1.py:1-5" in content
    assert "Location 2: file2.py:10-14" in content


def test_reporter_json_output(tmp_path):
    """Test JSON report generation."""
    reporter = Reporter(output_format="json")
    duplicates = [
        {
            "similarity": 0.95,
            "size": 10,
            "block1": {"file": "file1.py", "start_line": 1, "end_line": 5},
            "block2": {"file": "file2.py", "start_line": 10, "end_line": 14},
        }
    ]
    output_file = tmp_path / "report.json"
    reporter.generate_report(duplicates, output_file)

    content = json.loads(output_file.read_text())
    assert "duplicates" in content
    assert "total_duplications" in content
    assert content["total_duplications"] == 1
    assert len(content["duplicates"]) == 1
    assert content["duplicates"][0]["similarity"] == 0.95


def test_reporter_no_duplicates(tmp_path):
    """Test report generation with no duplicates."""
    reporter = Reporter(output_format="text")
    output_file = tmp_path / "report.txt"
    reporter.generate_report([], output_file)

    content = output_file.read_text()
    assert "Code Duplication Report" in content
    assert "No code duplications found!" in content


def test_reporter_console_output(capsys):
    """Test report generation to console."""
    reporter = Reporter(output_format="text")
    duplicates = [
        {
            "similarity": 0.95,
            "size": 10,
            "block1": {"file": "file1.py", "start_line": 1, "end_line": 5},
            "block2": {"file": "file2.py", "start_line": 10, "end_line": 14},
        }
    ]
    reporter.generate_report(duplicates)

    captured = capsys.readouterr()
    assert "Code Duplication Report" in captured.out
    assert "Duplication #1" in captured.out
    assert "Similarity: 95.00%" in captured.out


def test_reporter_error_handling(tmp_path):
    """Test error handling in report generation."""
    reporter = Reporter(output_format="text")
    duplicates = [
        {
            "similarity": 0.95,
            "size": 10,
            "block1": {"file": "file1.py", "start_line": 1, "end_line": 5},
            "block2": {"file": "file2.py", "start_line": 10, "end_line": 14},
        }
    ]

    # Create a directory instead of a file to force an error
    output_file = tmp_path / "report.txt"
    output_file.mkdir()

    # Should fall back to console output
    reporter.generate_report(duplicates, output_file)

    # Clean up
    output_file.rmdir()


def test_reporter_invalid_format():
    """Test reporter with invalid output format."""
    with pytest.raises(ValueError):
        Reporter(output_format="invalid")
