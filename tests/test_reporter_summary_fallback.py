"""
Tests for the generic summary fallback in Reporter.

DEFAULT_CONFIG gives every section a callable ``summary``, so the fallback
branch in ``_generate_summary`` (used when a section supplies none) is only
reachable through a custom config. The constructor documents that parameter, so
it is worth covering.
"""

from replicheck.reporter import Reporter


def _custom_config():
    """A section with no callable summary, forcing the generic fallback."""
    return {
        "widgets": {
            "title": "Widgets",
            "formatter": lambda item: f"- {item['name']}",
            "empty_message": "No widgets found.",
        }
    }


def test_generic_summary_counts_items_without_severity():
    reporter = Reporter(config=_custom_config())
    summary = reporter._generate_summary(widgets=[{"name": "a"}, {"name": "b"}])
    assert "- 2 widgets" in summary


def test_generic_summary_includes_severity_breakdown():
    reporter = Reporter(config=_custom_config())
    items = [
        {"name": "a", "severity": "High 🟠"},
        {"name": "b", "severity": "High 🟠"},
        {"name": "c", "severity": "Low 🟢"},
    ]
    summary = reporter._generate_summary(widgets=items)
    widget_line = next(line for line in summary if "widgets" in line)
    assert widget_line.startswith("- 3 widgets (")
    assert "2 High 🟠" in widget_line
    assert "1 Low 🟢" in widget_line


def test_generic_summary_empty_items_uses_tick():
    reporter = Reporter(config=_custom_config())
    assert "- 0 widgets ✅" in reporter._generate_summary(widgets=[])
    assert "- 0 widgets ✅" in reporter._generate_summary(widgets=None)


def test_generic_summary_falls_back_to_title_from_key():
    config = {"odd_section_name": {"formatter": lambda item: str(item)}}
    reporter = Reporter(config=config)
    summary = reporter._generate_summary(odd_section_name=[{"a": 1}])
    assert "- 1 odd section name" in summary


def test_summary_error_in_custom_summary_is_reported_not_raised():
    def exploding_summary(items):
        raise RuntimeError("boom")

    config = {"widgets": {"title": "Widgets", "summary": exploding_summary}}
    reporter = Reporter(config=config)
    summary = reporter._generate_summary(widgets=[{"name": "a"}])
    error_line = next(line for line in summary if "Error in summary" in line)
    assert "Error in summary for widgets" in error_line
    assert "boom" in error_line


def test_generic_summary_renders_through_a_full_report(tmp_path):
    """The fallback must work end to end, not just in isolation."""
    reporter = Reporter(output_format="markdown", config=_custom_config())
    out_file = tmp_path / "report.md"
    reporter.generate_report(
        output_file=out_file,
        duplicates=[],
        complexity_results=[],
        large_files=[],
        large_classes=[],
        unused=[],
        todo_fixme=[],
        bns_results=[],
        widgets=[{"name": "a"}, {"name": "b"}],
    )
    content = out_file.read_text(encoding="utf-8")
    assert "- 2 widgets" in content
    assert "## Widgets" in content
