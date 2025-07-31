"""
Tests for the reporter module.
"""

import json

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
    ]
    output_file = tmp_path / "report.json"
    reporter.generate_report(
        duplicates, output_file, complexity_results=complexity_results
    )
    content = json.loads(output_file.read_text(encoding="utf-8"))
    assert "high_cyclomatic_complexity" in content
    assert content["high_cyclomatic_complexity"][0]["name"] == "foo"


def test_reporter_format_path_methods():
    """Test the _format_path method with different modes."""
    reporter = Reporter()

    # Test plain mode (default)
    assert reporter._format_path("test.py", 10) == "test.py:10"
    assert reporter._format_path("test.py") == "test.py"

    # Test markdown mode
    assert (
        reporter._format_path("test.py", 10, "markdown") == "[test.py:10](test.py#L10)"
    )
    assert reporter._format_path("test.py", None, "markdown") == "[test.py](test.py)"

    # Test terminal mode
    terminal_result = reporter._format_path("test.py", 10, "terminal")
    assert "test.py:10" in terminal_result
    assert terminal_result.startswith("\033]8;;")
    assert terminal_result.endswith("\033\\")

    terminal_result_no_line = reporter._format_path("test.py", None, "terminal")
    assert "test.py" in terminal_result_no_line
    assert terminal_result_no_line.startswith("\033]8;;")


def test_reporter_generate_summary_edge_cases():
    """Test _generate_summary with various edge cases."""
    reporter = Reporter()

    # All None
    summary = reporter._generate_summary(None, None, None, None, None, None)
    assert len(summary) == 6
    assert "0 high complexity functions ✅" in summary[0]
    assert "0 large files ✅" in summary[1]
    assert "0 large classes ✅" in summary[2]
    assert "0 unused imports/variables ✅" in summary[3]
    assert "0 TODO/FIXME comments ✅" in summary[4]
    assert "0 duplicate code blocks ✅" in summary[5]

    # Test with empty lists
    summary = reporter._generate_summary([], [], [], [], [], [])
    assert len(summary) == 6
    assert "0 high complexity functions ✅" in summary[0]

    # Test with some data
    complexity_results = [
        {"severity": "Critical 🔴"},
        {"severity": "High 🟠"},
        {"severity": "Medium 🟡"},
    ]
    large_files = [
        {"severity": "Critical 🔴"},
        {"severity": "Low 🟢"},
    ]
    large_classes = [
        {"severity": "High 🟠"},
    ]
    unused = [
        {"file": "test.py", "line": 1, "code": "F401", "message": "unused import"},
    ]
    todo_fixme = [
        {"file": "test.py", "line": 1, "type": "TODO", "text": "test"},
    ]
    duplicates = [
        {"size": 10, "locations": [{"file": "test.py"}]},
    ]

    summary = reporter._generate_summary(
        complexity_results, large_files, large_classes, unused, todo_fixme, duplicates
    )
    assert "3 high complexity functions (1 Critical 🔴)" in summary[0]
    assert "2 large files (1 Critical 🔴)" in summary[1]
    assert "1 large classes (1 High 🟠)" in summary[2]
    assert "1 unused imports/variables" in summary[3]
    assert "1 TODO/FIXME comments" in summary[4]
    assert "1 duplicate code blocks" in summary[5]


def test_reporter_markdown_output(tmp_path):
    """Test markdown report generation."""
    reporter = Reporter(output_format="markdown")
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
    output_file = tmp_path / "report.md"
    reporter.generate_report(
        duplicates,
        output_file,
        complexity_results=complexity_results,
        large_files=large_files,
        large_classes=large_classes,
        todo_fixme=todo_fixme,
    )

    content = output_file.read_text()
    assert "# Code Duplication Report" in content
    assert "## Summary" in content
    assert "## Code Duplications" in content
    assert "## High Cyclomatic Complexity Functions" in content
    assert "## Large Files" in content
    assert "## Large Classes" in content
    assert "## TODO/FIXME Comments" in content
    # Check for the actual markdown link format
    assert "[file1.py:1](file1.py#L1)" in content or "file1.py:1-5" in content


def test_reporter_generate_report_file_error(tmp_path):
    """Test report generation when file writing fails."""
    reporter = Reporter(output_format="text")
    duplicates = [
        {
            "size": 10,
            "num_duplicates": 2,
            "locations": [
                {"file": "file1.py", "start_line": 1, "end_line": 5},
            ],
            "cross_file": False,
            "tokens": ["def", "foo", "(", ")", ":"],
        }
    ]

    output_file = tmp_path / "report.txt"
    output_file.mkdir()

    # Should fall back to console output
    reporter.generate_report(duplicates, output_file)

    output_file.rmdir()


def test_reporter_generate_report_with_duplication_groups(tmp_path, capsys):
    """Test report generation with duplication groups."""
    reporter = Reporter(output_format="text")
    duplicates = [
        {
            "size": 10,
            "num_duplicates": 3,
            "locations": [
                {"file": "file1.py", "start_line": 1, "end_line": 5},
                {"file": "file2.py", "start_line": 10, "end_line": 14},
                {"file": "file3.py", "start_line": 20, "end_line": 24},
            ],
            "cross_file": True,
            "tokens": ["def", "foo", "(", ")", ":", "x", "=", "1"],
        }
    ]

    reporter.generate_report(duplicates, None)
    captured = capsys.readouterr()
    assert "Clone #1: size=10 tokens, count=3 (cross-file)" in captured.out
    assert "file1.py:1-5" in captured.out
    assert "file2.py:10-14" in captured.out
    assert "file3.py:20-24" in captured.out


def test_reporter_json_with_duplication_groups(tmp_path):
    """Test JSON report generation with duplication groups."""
    reporter = Reporter(output_format="json")
    duplicates = [
        {
            "size": 10,
            "num_duplicates": 3,
            "locations": [
                {"file": "file1.py", "start_line": 1, "end_line": 5},
                {"file": "file2.py", "start_line": 10, "end_line": 14},
                {"file": "file3.py", "start_line": 20, "end_line": 24},
            ],
            "cross_file": True,
            "tokens": ["def", "foo", "(", ")", ":", "x", "=", "1"],
        }
    ]

    output_file = tmp_path / "report.json"
    reporter.generate_report(duplicates, output_file)

    content = json.loads(output_file.read_text(encoding="utf-8"))
    assert "duplicates" in content
    assert content["duplicates"][0]["size"] == 10
    assert content["duplicates"][0]["num_duplicates"] == 3
    assert content["duplicates"][0]["cross_file"] is True
    assert len(content["duplicates"][0]["locations"]) == 3


def test_reporter_json_legacy_format(tmp_path):
    """Test JSON report generation with legacy format."""
    reporter = Reporter(output_format="json")
    duplicates = [
        {
            "size": 10,
            "similarity": 0.95,
            "block1": {"file": "file1.py", "start_line": 1, "end_line": 5},
            "block2": {"file": "file2.py", "start_line": 10, "end_line": 14},
            "tokens": ["def", "foo", "(", ")", ":", "x", "=", "1"],
        }
    ]

    output_file = tmp_path / "report.json"
    reporter.generate_report(duplicates, output_file)

    content = json.loads(output_file.read_text(encoding="utf-8"))
    assert "duplicates" in content
    assert content["duplicates"][0]["size"] == 10
    assert content["duplicates"][0]["num_duplicates"] == 2
    assert content["duplicates"][0]["cross_file"] is True


def test_reporter_markdown_legacy_format(tmp_path):
    """Test markdown report generation with legacy format."""
    reporter = Reporter(output_format="markdown")
    duplicates = [
        {
            "size": 10,
            "similarity": 0.95,
            "block1": {"file": "file1.py", "start_line": 1, "end_line": 5},
            "block2": {"file": "file2.py", "start_line": 10, "end_line": 14},
            "tokens": ["def", "foo", "(", ")", ":", "x", "=", "1"],
        }
    ]

    output_file = tmp_path / "report.md"
    reporter.generate_report(duplicates, output_file)

    content = output_file.read_text()
    assert "# Code Duplication Report" in content
    assert "## Code Duplications" in content
    assert "Duplication #1: Similarity: 95.00%" in content


def test_reporter_text_legacy_format(tmp_path, capsys):
    """Test text report generation with legacy format."""
    reporter = Reporter(output_format="text")
    duplicates = [
        {
            "size": 10,
            "similarity": 0.95,
            "block1": {"file": "file1.py", "start_line": 1, "end_line": 5},
            "block2": {"file": "file2.py", "start_line": 10, "end_line": 14},
            "tokens": ["def", "foo", "(", ")", ":", "x", "=", "1"],
        }
    ]

    reporter.generate_report(duplicates, None)
    captured = capsys.readouterr()
    assert "Duplication #1" in captured.out
    assert "Similarity: 95.00%" in captured.out
    assert "file1.py:1-5" in captured.out
    assert "file2.py:10-14" in captured.out


def test_reporter_generate_report_exception_handling(tmp_path, capsys):
    """Test that generate_report handles exceptions gracefully."""
    reporter = Reporter(output_format="text")
    duplicates = [
        {
            "size": 10,
            "num_duplicates": 2,
            "locations": [
                {"file": "file1.py", "start_line": 1, "end_line": 5},
            ],
            "cross_file": False,
            "tokens": ["def", "foo", "(", ")", ":"],
        }
    ]

    output_file = tmp_path / "report.txt"
    output_file.mkdir()

    reporter.generate_report(duplicates, output_file)
    captured = capsys.readouterr()
    assert (
        "Report written to:" in captured.out or "Error writing report:" in captured.out
    )

    output_file.rmdir()


def test_reporter_json_console_output(capsys):
    """Test JSON report generation to console."""
    reporter = Reporter(output_format="json")
    duplicates = [
        {
            "size": 10,
            "num_duplicates": 2,
            "locations": [
                {"file": "file1.py", "start_line": 1, "end_line": 5},
            ],
            "cross_file": False,
            "tokens": ["def", "foo", "(", ")", ":"],
        }
    ]

    reporter.generate_report(duplicates, None)
    captured = capsys.readouterr()
    assert '"duplicates"' in captured.out
    assert '"size": 10' in captured.out


def test_reporter_markdown_console_output(capsys):
    """Test markdown report generation to console."""
    reporter = Reporter(output_format="markdown")
    duplicates = [
        {
            "size": 10,
            "num_duplicates": 2,
            "locations": [
                {"file": "file1.py", "start_line": 1, "end_line": 5},
            ],
            "cross_file": False,
            "tokens": ["def", "foo", "(", ")", ":"],
        }
    ]

    reporter.generate_report(duplicates, None)
    captured = capsys.readouterr()
    assert "# Code Duplication Report" in captured.out
    assert "## Code Duplications" in captured.out


def test_reporter_text_section_unused(capsys):
    # Test the _text_section_unused method in Reporter
    from replicheck.reporter import Reporter

    unused = [
        {
            "file": "foo.py",
            "line": 2,
            "code": "F401",
            "message": "imported but unused",
        },
        {
            "file": "foo.py",
            "line": 3,
            "code": "F841",
            "message": "assigned to but never used",
        },
    ]
    reporter = Reporter(output_format="text")
    console_output = []
    file_output = []
    reporter._text_section_unused(unused, console_output, file_output)
    # Should mention both F401 and F841
    assert any("F401" in line for line in console_output)
    assert any("F841" in line for line in console_output)
    assert any("imported but unused" in line for line in console_output)
    assert any("assigned to but never used" in line for line in console_output)
    # Should have section header
    assert any("Unused Imports and Vars" in line for line in console_output)


def test_reporter_text_section_unused_empty():
    from replicheck.reporter import Reporter

    reporter = Reporter(output_format="text")
    console_output = []
    file_output = []
    reporter._text_section_unused([], console_output, file_output)
    # Should mention no unused imports or variables found
    assert any(
        "No unused imports or variables found" in line for line in console_output
    )
    assert any("No unused imports or variables found" in line for line in file_output)
