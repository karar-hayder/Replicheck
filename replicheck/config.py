"""
Configuration management for the tool.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Set


@dataclass
class Config:
    """Configuration settings for code duplication detection."""

    path: Path
    threshold: float = 0.8
    extensions: Set[str] = frozenset({".py", ".js"})
    output_format: str = "text"
    output_file: Path = None

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not isinstance(self.path, Path):
            self.path = Path(self.path)

        if not self.path.exists():
            raise ValueError(f"Path does not exist: {self.path}")

        if not self.path.is_dir():
            raise ValueError(f"Path is not a directory: {self.path}")

        if not 0 <= self.threshold <= 1:
            raise ValueError("Threshold must be between 0 and 1")

        if self.output_format not in {"text", "json"}:
            raise ValueError("Output format must be either 'text' or 'json'")

        if self.output_file and not isinstance(self.output_file, Path):
            self.output_file = Path(self.output_file)
