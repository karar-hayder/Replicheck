"""
Replicheck - A tool for detecting code duplications within a specified scope.
"""

__version__ = "0.1.0"

from .config import Config
from .detector import DuplicateDetector
from .parser import CodeParser
from .reporter import Reporter
