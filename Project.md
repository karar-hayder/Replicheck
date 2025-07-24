# Project.md

## Overview

**Replicheck** is a Python tool designed to detect code duplications within a specified directory. Its primary goal is to help developers maintain code quality and reduce redundancy by identifying similar or identical code blocks across a codebase.

## Features

- **Duplicate Detection:** Finds duplicate code blocks within user-specified directories.
- **Configurable Thresholds:** Allows users to set the minimum similarity threshold and minimum code block size for comparison.
- **Language Support:** Supports Python, JavaScript/JSX, and C# code natively.
- **Directory and File Filtering:** Ignores virtual environments and user-specified directories. Users can also specify which file extensions to analyze.
- **Reporting:** Generates detailed reports in either text or JSON format, with the option to output to a file or the console.
- **Robust Testing:** The project boasts 98%+ test coverage and robust error handling.
- **Developer Experience:** Includes pre-commit hooks, code formatting (Black, isort), and a clear development workflow.

## Architecture

- **CLI Entrypoint:** `cli.py` provides a command-line interface for users to run Replicheck with various options.
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
python cli.py --path /path/to/code
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

- **Code Parsing:** Uses the AST module for Python and Tree-sitter for JavaScript/JSX and C# to extract functions and classes for comparison and analysis.
- **Duplicate Detection:** Compares code blocks using Jaccard similarity, with configurable thresholds.
- **Reporting:** Outputs results in both human-readable and machine-readable formats.
- **Comprehensive Testing:** All core modules have dedicated tests, including edge cases and error handling.
- **Pre-commit and Formatting:** Supports Black and isort for code style, and pre-commit hooks for consistency.
- **Robust CLI:** User-friendly command-line interface with helpful error messages and flexible options.

## What Can Be Added or Improved

### 1. **JavaScript/JSX Parsing**

- **Current State:** JavaScript and JSX parsing is implemented using Tree-sitter and `typhonjs-escomplex` for metrics.
- **Improvement:** Add support for TypeScript/TSX and expand metric coverage if needed.

### 2. **Multi-language Support**

- **Current State:** Python, JavaScript/JSX, and C# are fully supported.
- **Improvement:** Add support for other languages (e.g., TypeScript, Java, C++) by implementing or integrating language-specific parsers.

### 3. **Improved Similarity Metrics**

- **Current State:** Uses Jaccard similarity on token sets.
- **Improvement:** Explore more advanced similarity metrics (e.g., token sequence alignment, AST-based comparison, or machine learning approaches) for more accurate detection.

### 4. **Performance Optimization**

- **Current State:** Compares all code blocks pairwise, which may be slow for large codebases.
- **Improvement:** Implement indexing, hashing, or clustering to reduce the number of comparisons.

### 5. **Web/GUI Frontend**

- **Current State:** CLI only.
- **Improvement:** Build a simple web or desktop GUI for easier use and visualization of results.

### 6. **Integration with CI/CD**

- **Current State:** Manual execution.
- **Improvement:** Provide GitHub Actions or other CI/CD integration examples to automate duplicate detection in pull requests.

### 7. **Enhanced Reporting**

- **Current State:** Text and JSON reports.
- **Improvement:** Add HTML reports with links and code highlighting, or integrate with code review tools.

### 8. **User Configuration File**

- **Current State:** All options are CLI arguments.
- **Improvement:** Allow configuration via a YAML or TOML file for easier reuse and sharing of settings.

### 9. **Refactoring Suggestions**

- **Current State:** Only detects duplicates.
- **Improvement:** Suggest possible refactorings or code extraction opportunities based on detected duplications.

### 10. **Better JavaScript/TypeScript Support**

- **Current State:** JS/JSX support is implemented. No TS/TSX support yet.
- **Improvement:** Add robust parser and metrics for TS/TSX and add tests for these languages.

## Notable Limitations

- **Similarity metric is basic and may not catch all forms of duplication.**
- **Performance may degrade on very large codebases due to pairwise comparison.**

## Testing

- Tests cover configuration, parsing, detection, reporting, and utility functions.
- Edge cases (empty files, syntax errors, unsupported extensions) are tested.
- Error handling in report generation and configuration is tested.

## Recent Milestone

### ✅ C# Support Added (PR #3)

- Full support for C# code metrics:
  - Cyclomatic complexity (via Tree-sitter)
  - Large file/class detection
  - Duplicate code blocks
- C# added to core parsing, reporting, and CLI workflows

## License

MIT License

---

**This document provides a high-level summary and actionable roadmap for Replicheck.**  
For more details, see the [README.md](README.md) and the codebase itself.

---
