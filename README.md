# Replicheck

A Python tool for detecting code duplications and code quality issues in your projects. Replicheck analyzes your codebase to identify similar or identical code blocks, high complexity functions, large files/classes, and TODO/FIXME comments, helping you maintain code quality and reduce redundancy.

## Features

- Detect duplicate code blocks within specified directories
- Detect high cyclomatic complexity functions (Python)
- Detect large files and large classes by token count
- Find TODO/FIXME comments across your codebase
- Configurable similarity threshold and minimum block size
- Support for Python, JavaScript, TypeScript, JSX, and TSX files
- Ignores virtual environments and user-specified directories
- Detailed reporting in text, JSON, or Markdown format
- Summary section at the top of every report
- Hyperlinkable file paths in Markdown and supported terminals
- 98%+ test coverage and robust error handling

## Installation

1. Clone this repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Basic usage:

```bash
python main.py --path /path/to/code
```

### Options

- `--path`: Directory to analyze (required)
- `--min-similarity`: Minimum similarity threshold (0.0 to 1.0, default: 0.8)
- `--min-size`: Minimum code block size in tokens (default: 50)
- `--output-format`: Output format (`text`, `json`, or `markdown`, default: `text`)
- `--output-file`: Path to save the report (optional)
- `--ignore-dirs`: Space-separated list of directories to ignore (default: .git .venv venv env ENV build dist)
- `--complexity-threshold`: Cyclomatic complexity threshold to flag functions (default: 10)
- `--large-file-threshold`: Token count threshold to flag large files (default: 500)
- `--large-class-threshold`: Token count threshold to flag large classes (default: 300)
- `--top-n-large`: Show only the top N largest files/classes (default: 10, 0=all)

Example:

```bash
python main.py --path ./src --min-similarity 0.85 --min-size 30 --output-format markdown --output-file report.md --ignore-dirs .git .venv node_modules --complexity-threshold 12 --large-file-threshold 800 --large-class-threshold 400 --top-n-large 5
```

## Report Output

### Summary Section

Every report starts with a summary, e.g.:

```text
Summary:
- 2 high complexity functions (1 Critical 🔴)
- 3 large files (1 Critical 🔴)
- 1 large classes (1 High 🟠)
- 4 TODO/FIXME comments
- 1 duplicate code blocks
```

### Markdown Output Example

```markdown
# Code Duplication Report

## Summary
- 2 high complexity functions (1 Critical 🔴)
- 3 large files (1 Critical 🔴)
- 1 large classes (1 High 🟠)
- 4 TODO/FIXME comments
- 1 duplicate code blocks

## High Cyclomatic Complexity Functions
- [src/foo.py:12](src/foo.py#L12) foo (complexity: 15) [Critical 🔴]

## Large Files
- [src/big.py](src/big.py) (tokens: 900) [Critical 🔴]

## Large Classes
- [src/big.py:10](src/big.py#L10) BigClass (tokens: 400) [High 🟠]

## TODO/FIXME Comments
- [src/foo.py:20](src/foo.py#L20) [TODO] Refactor this

## Code Duplications
- Clone #1: size=50 tokens, count=2 (cross-file)
    - [src/foo.py:10](src/foo.py#L10) - src/foo.py:10-20
    - [src/bar.py:30](src/bar.py#L30) - src/bar.py:30-40
    Tokens: def foo ( ) : x = 1 y = ...
```

- In Markdown reports, file paths are clickable and link to the relevant file/line (works in GitHub, VSCode, etc.).
- In supported terminals, file paths are clickable if your terminal supports OSC 8 hyperlinks.

## Development

To run tests:

```bash
pytest
```

To check code style and sort imports:

```bash
black .
isort .
```

## Pre-commit Hooks (Recommended)

You can use [pre-commit](https://pre-commit.com/) to automatically format and lint your code before each commit. This is free and easy to set up:

1. Install pre-commit:

   ```bash
   pip install pre-commit
   ```

2. Install the hooks:

   ```bash
   pre-commit install
   ```

3. Now, every time you commit, `black` and `isort` will run automatically.

If you want to run the hooks manually on all files:

```bash
pre-commit run --all-files
```

## License

MIT License
