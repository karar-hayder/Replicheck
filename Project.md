# Project.md

## Overview

**Replicheck** is a Python tool designed to detect technical dept within a specified directory. Its primary goal is to help developers maintain code quality and reduce redundancy by technical dept across a codebase.

## Features

- **Duplicate Detection:** Finds duplicate code blocks within user-specified directories.
- **Configurable Thresholds:** Allows users to set the minimum similarity (Jaccard over token sets) and the minimum code block size in tokens for comparison. At `1.0` only exact matches are reported; below that, near-duplicates are grouped too.
- **Language Support:** Supports Python, JavaScript/JSX, Typescript/TSX, and C# code natively.
- **Directory and File Filtering:** Ignores virtual environments and user-specified directories. Users can also specify which file extensions to analyze.
- **Reporting:** Generates detailed reports in either text or JSON format, with the option to output to a file or the console.
- **Robust Testing:** The project boasts 90%+ test coverage and robust error handling.
- **Developer Experience:** Includes pre-commit hooks, code formatting and testing (Black, pytest), and a clear development workflow.

## Architecture

- **CLI Entrypoint:** `main.py` provides a command-line interface for users to run Replicheck with various options.
- **Core Modules:**
  - `replicheck/config.py`: Handles configuration and validation.
  - `replicheck/parser.py`: Parses code files and extracts code blocks (Python, JavaScript/JSX, TypeScript/TSX and C# supported).
  - `replicheck/runner.py`: Orchestrates the analysis pipeline and report generation.
  - `replicheck/reporter.py`: Handles report generation in text, JSON and Markdown formats.
  - `replicheck/utils.py`: Provides utility functions for file discovery and severity calculation.
  - `replicheck/tree_sitter_loader.py`: Loads and initializes Tree-sitter grammars (JavaScript, TypeScript, C#).
  - `replicheck/tools/`: The individual detectors — duplication, cyclomatic complexity, large file/class, unused imports and variables, TODO/FIXME, and bugs and safety.
  - `replicheck/tools/flake8_runner.py`: Shared chunked flake8 invocation used by the unused-import and bug&safety detectors.
- **Testing:** Comprehensive tests for all modules are located in the `tests/` directory.

## Usage

Basic usage:

```bash
python main.py --path /path/to/code
```

Key options:

- `--path`: Directory to analyze (required)
- `--min-similarity`: Minimum similarity for two blocks to be reported together (0.0 to 1.0, default: 0.8). Similarity is the Jaccard ratio of token sets.
- `--min-size`: Minimum code block size in tokens (default: 50)
- `--extensions`: File extensions to analyze (default: .py,.js,.jsx,.cs,.ts,.tsx)
- `--output-format`: Output format (text, json or markdown, default: text)
- `--output-file`: Path to save the report (optional)
- `--ignore-dirs`: Directories to ignore (default: .git .venv venv env build dist node_modules __pycache__ .pytest_cache coverage vendor bower_components .vscode .idea .vs .next)

## What Has Been Implemented

- **Code Parsing:** Uses the AST module for Python and Tree-sitter for JavaScript/JSX, Typescript/TSX and C# to extract functions and classes for comparison and analysis.
- **Duplicate Detection:** Groups code blocks by Jaccard similarity over their token sets, reporting each group's locations and its weakest pairwise similarity. At `--min-similarity 1.0` this reduces to exact token-sequence matching.
- **Reporting:** Outputs results in both human-readable and machine-readable formats.
- **Comprehensive Testing:** All core modules have dedicated tests, including edge cases and error handling.
- **Pre-commit and Formatting:** Supports Black and pytest for code style and testing, and pre-commit hooks for consistency.
- **Robust CLI:** User-friendly command-line interface with helpful error messages and flexible options.

## What Can Be Added or Improved

### 1. **Multi-language Support**

- **Current State:** Python, JavaScript/JSX, Typescript/TSX, and C# are fully supported.
- **Improvement:** Add support for other languages (e.g., Java, C++, Go) by implementing or integrating language-specific parsers.

### 2. **Improved Similarity Metrics**

- **Current State:** Jaccard similarity over token *sets*, with an exact prefix-filter candidate generator so the whole set is never compared pairwise. Sets are order-insensitive, so a reordered body counts as a duplicate; near-duplicates below the threshold are still missed.
- **Improvement:** Sequence-aware comparison (token alignment, AST shape) to catch reordered or restructured code that set similarity rates too low.

### 3. **Performance Optimization**

- **Current State:** flake8 runs once for all selected codes instead of twice, JS/TS and C# complexity batch 50 files per helper invocation instead of spawning a process per file, and non-Python files are no longer handed to flake8. The remaining cost is that each Python file is still read and parsed four times over — once each by the block parser, the token counter, the class detector and radon — before flake8 parses it a fifth.
- **Improvement:** Share a single parse per file across the detectors. At 750k lines those four passes are ~37s of the ~90s stage sum, so it is the largest remaining win.

### 4. **Integration with CI/CD**

- **Current State:** A GitHub Actions workflow runs the test suite, the linters and the format checks on every push. Duplicate detection itself is still run manually.
- **Improvement:** Add a job that scans the repository with Replicheck itself and comments on the pull request.

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

- **Similarity is measured over token sets, so it is order-insensitive: a reordered body reads as an exact match, and restructured code that keeps the same vocabulary reads as a duplicate. Very repetitive corpora can also chain unrelated blocks into one large group through connected components.**
- **Performance is dominated by repeated parsing and by external tool invocations (flake8, Node.js, the C# analyzer); see the Benchmarks section of [README.md](README.md).**

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
