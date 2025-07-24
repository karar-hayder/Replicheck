# Project.md

## Overview

**Replicheck** is a Python tool designed to detect technical dept within a specified directory. Its primary goal is to help developers maintain code quality and reduce redundancy by technical dept across a codebase.

## Features

- **Duplicate Detection:** Finds duplicate code blocks within user-specified directories.
- **Configurable Thresholds:** Allows users to set the minimum similarity threshold and minimum code block size for comparison.
- **Language Support:** Supports Python, JavaScript/JSX, Typescript/TSX, and C# code natively.
- **Directory and File Filtering:** Ignores virtual environments and user-specified directories. Users can also specify which file extensions to analyze.
- **Reporting:** Generates detailed reports in either text or JSON format, with the option to output to a file or the console.
- **Robust Testing:** The project boasts 90%+ test coverage and robust error handling.
- **Developer Experience:** Includes pre-commit hooks, code formatting and testing (Black, pytest), and a clear development workflow.

## Architecture

- **CLI Entrypoint:** `main.py` provides a command-line interface for users to run Replicheck with various options.
- **Core Modules:**
  - `replicheck/config.py`: Handles configuration and validation.
  - `replicheck/parser.py`: Parses code files and extracts code blocks (Python, JavaScript/JSX, and C# fully supported).
  - `replicheck/detector.py`: Contains the logic for detecting duplicate code blocks using a Jaccard similarity metric.
  - `replicheck/reporter.py`: Handles report generation in text and JSON formats.
  - `replicheck/utils.py`: Provides utility functions for file discovery and similarity calculation.
  - `replicheck/tree_sitter_loader.py`: Loads and initializes Tree-sitter grammars (JavaScript, JSX, C#).
- **Testing:** Comprehensive tests for all modules are located in the `tests/` directory.

## Usage

Basic usage:

```bash
python main.py --path /path/to/code
```

Key options:

- `--path`: Directory to analyze (required)
- `--min-sim`: Minimum similarity threshold (default: 0.8)
- `--min-size`: Minimum code block size in tokens (default: 50)
- `--extensions`: File extensions to analyze (default: .py,.js,.ts,.jsx,.tsx)
- `--output-format`: Output format (text or json, default: text)
- `--output-file`: Path to save the report (optional)
- `--ignore-dirs`: Directories to ignore (default: .git .venv venv env ENV build dist node_modules)

## What Has Been Implemented

- **Code Parsing:** Uses the AST module for Python and Tree-sitter for JavaScript/JSX, Typescript/TSX and C# to extract functions and classes for comparison and analysis.
- **Duplicate Detection:** Compares code blocks using Jaccard similarity, with configurable thresholds.
- **Reporting:** Outputs results in both human-readable and machine-readable formats.
- **Comprehensive Testing:** All core modules have dedicated tests, including edge cases and error handling.
- **Pre-commit and Formatting:** Supports Black and pytest for code style and testing, and pre-commit hooks for consistency.
- **Robust CLI:** User-friendly command-line interface with helpful error messages and flexible options.

## What Can Be Added or Improved

### 1. **Multi-language Support**

- **Current State:** Python, JavaScript/JSX, Typescript/TSX, and C# are fully supported.
- **Improvement:** Add support for other languages (e.g., Java, C++, Go) by implementing or integrating language-specific parsers.

### 2. **Improved Similarity Metrics**

- **Current State:** Uses Jaccard similarity on token sets.
- **Improvement:** Explore more advanced similarity metrics (e.g., token sequence alignment, AST-based comparison, or machine learning approaches) for more accurate detection.

### 3. **Performance Optimization**

- **Current State:** Compares all code blocks pairwise, which may be slow for large codebases.
- **Improvement:** Implement indexing, hashing, or clustering to reduce the number of comparisons.

### 4. **Integration with CI/CD**

- **Current State:** Manual execution.
- **Improvement:** Provide GitHub Actions or other CI/CD integration examples to automate duplicate detection in pull requests.

### 5. **Enhanced Reporting**

- **Current State:** Text, Markdown, and JSON reports.
- **Improvement:** Add HTML reports with links and code highlighting, or integrate with code review tools.

### 6. **User Configuration File**

- **Current State:** All options are CLI arguments.
- **Improvement:** Allow configuration via a YAML or TOML file for easier reuse and sharing of settings.

### 7. **Refactoring Suggestions**

- **Current State:** Only detects duplicates, high cyclomatic complexity functions, large files and large classes by token count.
- **Improvement:** Suggest possible refactorings or code extraction opportunities based on reports.

## Notable Limitations

- **Similarity metric is basic and may not catch all forms of duplication.**
- **Performance may degrade on very large codebases due to pairwise comparison.**

## Testing

- Tests cover configuration, parsing, detection, reporting, and utility functions.
- Edge cases (empty files, syntax errors, unsupported extensions) are tested.
- Error handling in report generation and configuration is tested.

## Recent Milestone

### ✅ C# and TS/TSX Support Added (PR #3 - #4)

- Full support for C# and TS/TSX code metrics:
  - Cyclomatic complexity (via Tree-sitter)
  - Large file/class detection
  - Duplicate code blocks
- C# and TS/TSX added to core parsing, reporting, and CLI workflows

## License

MIT License

---

**This document provides a high-level summary and actionable roadmap for Replicheck.**  
For more details, see the [README.md](README.md) and the codebase itself.

---
