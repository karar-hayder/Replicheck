"""
Tests for the configuration module.
"""

from pathlib import Path

import pytest

from replicheck.config import Config


def test_config_valid_path(tmp_path):
    """Test Config with valid path."""
    config = Config(path=tmp_path)
    assert config.path == tmp_path
    assert config.threshold == 0.8
    assert config.extensions == frozenset({".py", ".js"})
    assert config.output_format == "text"
    assert config.output_file is None


def test_config_invalid_path():
    """Test Config with invalid path."""
    with pytest.raises(ValueError, match="Path does not exist"):
        Config(path="/nonexistent/path")


def test_config_file_path(tmp_path):
    """Test Config with file path instead of directory."""
    file_path = tmp_path / "test.txt"
    file_path.write_text("test")
    with pytest.raises(ValueError, match="Path is not a directory"):
        Config(path=file_path)


def test_config_invalid_threshold(tmp_path):
    """Test Config with invalid threshold."""
    with pytest.raises(ValueError, match="Threshold must be between 0 and 1"):
        Config(path=tmp_path, threshold=1.5)


def test_config_invalid_output_format(tmp_path):
    """Test Config with invalid output format."""
    with pytest.raises(
        ValueError, match="Output format must be either 'text' or 'json'"
    ):
        Config(path=tmp_path, output_format="invalid")


def test_config_custom_settings(tmp_path):
    """Test Config with custom settings."""
    output_file = tmp_path / "report.txt"
    config = Config(
        path=tmp_path,
        threshold=0.9,
        extensions={".py", ".ts"},
        output_format="json",
        output_file=output_file,
    )
    assert config.threshold == 0.9
    assert config.extensions == {".py", ".ts"}
    assert config.output_format == "json"
    assert config.output_file == output_file


def test_config_string_path(tmp_path):
    """Test Config with string path."""
    config = Config(path=str(tmp_path))
    assert isinstance(config.path, Path)
    assert config.path == tmp_path


def test_config_string_output_file(tmp_path):
    """Test Config with string output file path."""
    output_file = tmp_path / "report.txt"
    config = Config(path=tmp_path, output_file=str(output_file))
    assert isinstance(config.output_file, Path)
    assert config.output_file == output_file
