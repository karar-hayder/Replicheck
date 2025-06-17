# Replicheck

A Python tool for detecting code duplications within a specified scope. Replicheck analyzes your codebase to identify similar or identical code blocks, helping you maintain code quality and reduce redundancy.

## Features

- Detect duplicate code blocks within specified directories
- Configurable similarity threshold
- Support for multiple programming languages
- Detailed reporting of duplicate code locations
- Customizable scope for analysis

## Installation

1. Clone this repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Basic usage:

```bash
python main.py --path /path/to/code --threshold 0.8
```

Options:

- `--path`: Directory to analyze (required)
- `--threshold`: Similarity threshold (0.0 to 1.0, default: 0.8)
- `--extensions`: File extensions to analyze (default: .py,.js)
- `--output`: Output format (json/text, default: text)

## Development

To run tests:

```bash
pytest
```

## License

MIT License
