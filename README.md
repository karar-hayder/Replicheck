# Replicheck

A Python tool for detecting code duplications within a specified scope. Replicheck analyzes your codebase to identify similar or identical code blocks, helping you maintain code quality and reduce redundancy.

## Features

- Detect duplicate code blocks within specified directories
- Configurable similarity threshold and minimum block size
- Support for Python and JavaScript (extensible for more languages)
- Ignores virtual environments and user-specified directories
- Detailed reporting in text or JSON format
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
python cli.py --path /path/to/code
```

Options:

- `--path`: Directory to analyze (required)
- `--min-sim`: Minimum similarity threshold (0.0 to 1.0, default: 0.8)
- `--min-size`: Minimum code block size in tokens (default: 50)
- `--extensions`: Comma-separated file extensions to analyze (default: .py,.js)
- `--output-format`: Output format (json/text, default: text)
- `--output-file`: Path to save the report (optional)
- `--ignore-dirs`: Space-separated list of directories to ignore (default: .git .venv venv env ENV build dist node_modules)

Example:

```bash
python cli.py --path ./src --min-sim 0.85 --min-size 30 --extensions .py,.js --output-format json --output-file report.json --ignore-dirs .git .venv node_modules
```

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
