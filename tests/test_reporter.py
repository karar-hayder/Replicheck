"""
Tests for the reporter module.
"""

import json
from pathlib import Path

import pytest

from replicheck.reporter import Reporter


def test_reporter_text_output(capsys):
    """Test text report generation."""
    reporter = Reporter(output_format="text")
    duplicates = [
        {
            "size": 10,
            "num_duplicates": 2,
            "locations": [
                {"file": "file1.py", "start_line": 1, "end_line": 5},
                {"file": "file2.py", "start_line": 10, "end_line": 14},
            ],
            "cross_file": True,
            "tokens": ["def", "foo", "(", ")", ":", "x", "=", "1", "y", "=", "2"],
        }
    ]
    complexity_results = [
        {
            "name": "foo",
            "complexity": 12,
            "lineno": 2,
            "endline": 15,
            "file": "file1.py",
            "threshold": 10,
            "severity": "Low 🟢",
        },
    ]
    large_files = [
        {
            "file": "big.py",
            "token_count": 600,
            "threshold": 500,
            "top_n": 10,
            "severity": "Low 🟢",
        },
    ]
    large_classes = [
        {
            "name": "BigClass",
            "file": "big.py",
            "start_line": 1,
            "end_line": 100,
            "token_count": 350,
            "threshold": 300,
            "top_n": 10,
            "severity": "Low 🟢",
        },
    ]
    todo_fixme = [
        {"file": "a.py", "line": 2, "type": "TODO", "text": "Refactor this"},
    ]
    reporter.generate_report(
        duplicates,
        None,
        complexity_results=complexity_results,
        large_files=large_files,
        large_classes=large_classes,
        todo_fixme=todo_fixme,
    )
    captured = capsys.readouterr()
    assert "Code Duplications" in captured.out
    assert "Clone #1: size=10 tokens, count=2 (cross-file)" in captured.out
    assert "file1.py:1-5" in captured.out and "file2.py:10-14" in captured.out
    assert "Tokens: def foo ( ) : x = 1 y =" in captured.out
    assert "High Cyclomatic Complexity Functions" in captured.out
    assert "Large Files" in captured.out
    assert "Large Classes" in captured.out
    assert "TODO/FIXME Comments" in captured.out


def test_reporter_json_output(tmp_path):
    """Test JSON report generation."""
    reporter = Reporter(output_format="json")
    duplicates = [
        {
            "size": 10,
            "num_duplicates": 2,
            "locations": [
                {"file": "file1.py", "start_line": 1, "end_line": 5},
                {"file": "file2.py", "start_line": 10, "end_line": 14},
            ],
            "cross_file": True,
            "tokens": ["def", "foo", "(", ")", ":", "x", "=", "1", "y", "=", "2"],
        }
    ]
    complexity_results = [
        {
            "name": "foo",
            "complexity": 12,
            "lineno": 2,
            "endline": 15,
            "file": "file1.py",
            "threshold": 10,
            "severity": "Low 🟢",
        },
    ]
    large_files = [
        {
            "file": "big.py",
            "token_count": 600,
            "threshold": 500,
            "top_n": 10,
            "severity": "Low 🟢",
        },
    ]
    large_classes = [
        {
            "name": "BigClass",
            "file": "big.py",
            "start_line": 1,
            "end_line": 100,
            "token_count": 350,
            "threshold": 300,
            "top_n": 10,
            "severity": "Low 🟢",
        },
    ]
    todo_fixme = [
        {"file": "a.py", "line": 2, "type": "TODO", "text": "Refactor this"},
    ]
    output_file = tmp_path / "report.json"
    reporter.generate_report(
        duplicates,
        output_file,
        complexity_results=complexity_results,
        large_files=large_files,
        large_classes=large_classes,
        todo_fixme=todo_fixme,
    )
    import json

    content = json.loads(output_file.read_text(encoding="utf-8"))
    assert "duplicates" in content
    assert content["duplicates"][0]["size"] == 10
    assert content["duplicates"][0]["num_duplicates"] == 2
    assert content["duplicates"][0]["cross_file"] is True
    assert len(content["duplicates"][0]["locations"]) == 2
    assert "high_cyclomatic_complexity" in content
    assert "large_files" in content
    assert "large_classes" in content
    assert "todo_fixme_comments" in content


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


def test_reporter_text_with_complexity(tmp_path, capsys):
    reporter = Reporter(output_format="text")
    duplicates = []
    complexity_results = [
        {
            "name": "foo",
            "complexity": 12,
            "lineno": 2,
            "endline": 15,
            "file": "file1.py",
            "threshold": 10,
            "severity": "Low 🟢",
        },
        {
            "name": "bar",
            "complexity": 15,
            "lineno": 10,
            "endline": 30,
            "file": "file2.py",
            "threshold": 10,
            "severity": "Medium 🟡",
        },
    ]
    reporter.generate_report(duplicates, None, complexity_results=complexity_results)
    captured = capsys.readouterr()
    assert "High Cyclomatic Complexity Functions" in captured.out
    assert "foo" in captured.out and "bar" in captured.out
    assert "complexity: 12" in captured.out and "complexity: 15" in captured.out
    assert "[Medium 🟡]" in captured.out


def test_reporter_json_with_complexity(tmp_path):
    reporter = Reporter(output_format="json")
    duplicates = []
    complexity_results = [
        {
            "name": "foo",
            "complexity": 12,
            "lineno": 2,
            "endline": 15,
            "file": "file1.py",
            "threshold": 10,
            "severity": "Low 🟢",
        },
        {
            "name": "bar",
            "complexity": 15,
            "lineno": 10,
            "endline": 30,
            "file": "file2.py",
            "threshold": 10,
            "severity": "Medium 🟡",
        },
    ]
    output_file = tmp_path / "report.json"
    reporter.generate_report(
        duplicates, output_file, complexity_results=complexity_results
    )
    import json

    content = json.loads(output_file.read_text())
    assert "high_cyclomatic_complexity" in content
    assert len(content["high_cyclomatic_complexity"]) == 2
    assert content["high_cyclomatic_complexity"][0]["name"] == "foo"
    assert content["high_cyclomatic_complexity"][1]["name"] == "bar"


def test_reporter_text_with_large_files_and_classes(tmp_path, capsys):
    reporter = Reporter(output_format="text")
    duplicates = []
    large_files = [
        {
            "file": "big.py",
            "token_count": 600,
            "threshold": 500,
            "top_n": 10,
            "severity": "Low 🟢",
        },
    ]
    large_classes = [
        {
            "name": "BigClass",
            "file": "big.py",
            "start_line": 1,
            "end_line": 100,
            "token_count": 350,
            "threshold": 300,
            "top_n": 10,
            "severity": "Low 🟢",
        },
    ]
    reporter.generate_report(
        duplicates,
        None,
        complexity_results=[],
        large_files=large_files,
        large_classes=large_classes,
    )
    captured = capsys.readouterr()
    assert "Large Files" in captured.out
    assert "big.py" in captured.out
    assert "Large Classes" in captured.out
    assert "BigClass" in captured.out
    assert "[Low 🟢]" in captured.out


def test_reporter_json_with_large_files_and_classes(tmp_path):
    reporter = Reporter(output_format="json")
    duplicates = []
    large_files = [
        {"file": "big.py", "token_count": 600},
    ]
    large_classes = [
        {
            "name": "BigClass",
            "file": "big.py",
            "start_line": 1,
            "end_line": 100,
            "token_count": 350,
        },
    ]
    output_file = tmp_path / "report.json"
    reporter.generate_report(
        duplicates,
        output_file,
        complexity_results=[],
        large_files=large_files,
        large_classes=large_classes,
    )
    import json

    content = json.loads(output_file.read_text())
    assert "large_files" in content
    assert len(content["large_files"]) == 1
    assert content["large_files"][0]["file"] == "big.py"
    assert "large_classes" in content
    assert len(content["large_classes"]) == 1
    assert content["large_classes"][0]["name"] == "BigClass"


def test_reporter_text_with_todo_fixme(tmp_path, capsys):
    reporter = Reporter(output_format="text")
    duplicates = []
    todo_fixme = [
        {"file": "a.py", "line": 2, "type": "TODO", "text": "Refactor this"},
        {"file": "b.py", "line": 5, "type": "FIXME", "text": "Fix this bug"},
    ]
    reporter.generate_report(
        duplicates,
        None,
        complexity_results=[],
        large_files=[],
        large_classes=[],
        todo_fixme=todo_fixme,
    )
    captured = capsys.readouterr()
    assert "TODO/FIXME Comments" in captured.out
    assert "a.py:2 [TODO] Refactor this" in captured.out
    assert "b.py:5 [FIXME] Fix this bug" in captured.out


def test_reporter_json_with_todo_fixme(tmp_path):
    reporter = Reporter(output_format="json")
    duplicates = []
    todo_fixme = [
        {"file": "a.py", "line": 2, "type": "TODO", "text": "Refactor this"},
        {"file": "b.py", "line": 5, "type": "FIXME", "text": "Fix this bug"},
    ]
    output_file = tmp_path / "report.json"
    reporter.generate_report(
        duplicates,
        output_file,
        complexity_results=[],
        large_files=[],
        large_classes=[],
        todo_fixme=todo_fixme,
    )
    import json

    content = json.loads(output_file.read_text())
    assert "todo_fixme_comments" in content
    assert len(content["todo_fixme_comments"]) == 2
    assert content["todo_fixme_comments"][0]["type"] == "TODO"
    assert content["todo_fixme_comments"][1]["type"] == "FIXME"


def test_reporter_text_with_duplication_group(tmp_path, capsys):
    reporter = Reporter(output_format="text")
    duplicates = [
        {
            "size": 12,
            "num_duplicates": 3,
            "locations": [
                {"file": "a.py", "start_line": 1, "end_line": 5},
                {"file": "b.py", "start_line": 10, "end_line": 15},
                {"file": "a.py", "start_line": 20, "end_line": 25},
            ],
            "cross_file": True,
            "tokens": [
                "def",
                "foo",
                "(",
                ")",
                ":",
                "x",
                "=",
                "1",
                "y",
                "=",
                "2",
                "return",
            ],
        }
    ]
    reporter.generate_report(
        duplicates,
        None,
        complexity_results=[],
        large_files=[],
        large_classes=[],
        todo_fixme=[],
    )
    captured = capsys.readouterr()
    assert "Code Duplications" in captured.out
    assert "Clone #1: size=12 tokens, count=3 (cross-file)" in captured.out
    assert "a.py:1-5" in captured.out and "b.py:10-15" in captured.out
    assert "Tokens: def foo ( ) : x = 1 y =" in captured.out


def test_reporter_json_with_duplication_group(tmp_path):
    reporter = Reporter(output_format="json")
    duplicates = [
        {
            "size": 12,
            "num_duplicates": 3,
            "locations": [
                {"file": "a.py", "start_line": 1, "end_line": 5},
                {"file": "b.py", "start_line": 10, "end_line": 15},
                {"file": "a.py", "start_line": 20, "end_line": 25},
            ],
            "cross_file": True,
            "tokens": [
                "def",
                "foo",
                "(",
                ")",
                ":",
                "x",
                "=",
                "1",
                "y",
                "=",
                "2",
                "return",
            ],
        }
    ]
    output_file = tmp_path / "report.json"
    reporter.generate_report(
        duplicates,
        output_file,
        complexity_results=[],
        large_files=[],
        large_classes=[],
        todo_fixme=[],
    )
    import json

    content = json.loads(output_file.read_text(encoding="utf-8"))
    assert "duplicates" in content
    assert content["duplicates"][0]["size"] == 12
    assert content["duplicates"][0]["num_duplicates"] == 3
    assert content["duplicates"][0]["cross_file"] is True
    assert len(content["duplicates"][0]["locations"]) == 3
