# Replicheck

A Python tool for detecting code duplications and code quality issues in your projects. Replicheck analyzes your codebase to identify similar or identical code blocks, high complexity functions, large files/classes, and TODO/FIXME comments, helping you maintain code quality and reduce redundancy.

## Features

- Detect high cyclomatic complexity functions (Python, JavaScript/JSX, Typescript/TSX, C#)
- Detect large files and large classes by token count (Python, JavaScript/JSX, Typescript/TSX, C#)
- Detect duplicate code blocks (Python, JavaScript/JSX, Typescript/TSX, C#)
- Detect Unused imports and vars (Python)
- Find TODO/FIXME comments across your codebase
- Support for Python, JavaScript, JSX, Typescript, TSX and C# files
- Configurable similarity threshold and minimum block size for duplicate detection
- Ignores virtual environments and user-specified directories
- Detailed reporting in text, JSON, or Markdown format
- Summary section at the top of every report
- Hyperlinkable file paths in Markdown and supported terminals
- 90%+ test coverage and robust error handling

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
- `--min-similarity`: Minimum similarity for two blocks to be reported together (0.0 to 1.0, default: 0.8). Similarity is the Jaccard ratio of the blocks' token sets, so `1.0` reports only exact matches and lower values also catch near-duplicates. A group reports the *lowest* similarity among its members.
- `--min-size`: Minimum code block size in tokens (default: 50)
- `--output-format`: Output format (`text`, `json`, or `markdown`, default: `text`)
- `--output-file`: Path to save the report (optional)
- `--ignore-dirs`: Space-separated list of directories to ignore (default: .git .venv venv env build dist node_modules __pycache__ .pytest_cache coverage vendor bower_components .vscode .idea .vs .next)
- `--extensions`: File extensions to include (default: .py .js .jsx .cs .ts .tsx)
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
## Summary
- 14 high complexity functions (0 Critical 🔴)
- 9 large files (7 Critical 🔴)
- 1 large classes (0 High 🟠)
- 0 unused imports/variables ✅
- 12 TODO/FIXME comments
- 0 duplicate code blocks ✅
```

### Markdown Output Example

```markdown
# Code Duplication Report

## Summary
- 2 high complexity functions (1 Critical 🔴)
- 3 large files (1 Critical 🔴)
- 1 large classes (1 High 🟠)
- 2 unused imports/variables
- 4 TODO/FIXME comments
- 1 duplicate code blocks

## High Cyclomatic Complexity Functions
- [src/example.py:42](src/example.py#L42) process_data (complexity: 18) [Critical 🔴]
- [src/utils.py:10](src/utils.py#L10) calculate (complexity: 12) [Medium 🟡]

## Large Files
- [src/huge_module.py](src/huge_module.py) (tokens: 2100) [Critical 🔴]
- [src/medium_module.py](src/medium_module.py) (tokens: 800) [High 🟠]

## Large Classes
- [src/huge_module.py:5](src/huge_module.py#L5) BigProcessor (tokens: 700) [Critical 🔴]
- [src/medium_module.py:20](src/medium_module.py#L20) MediumProcessor (tokens: 350) [High 🟠]

## Unused Imports and Vars
- [main.py:204](main.py#L204) [F841] local variable 'js_files' is assigned to but never used
- [main.py:207](main.py#L207) [F841] local variable 'cs_files' is assigned to but never used


## TODO/FIXME Comments
- [src/example.py:99](src/example.py#L99) [TODO] Add error handling
- [src/utils.py:25](src/utils.py#L25) [FIXME] This is a hack, refactor later

## Code Duplications
- Clone #1: size=50 tokens, count=2 (cross-file)
    - [src/foo.py:10](src/foo.py#L10) - src/foo.py:10-20
    - [src/bar.py:30](src/bar.py#L30) - src/bar.py:30-40
    Tokens: def foo ( ) : x = 1 y = ...
```

- In Markdown reports, file paths are clickable and link to the relevant file/line (works in GitHub, VSCode, etc.).
- In supported terminals, file paths are clickable if your terminal supports OSC 8 hyperlinks.
- A duplication group lists at most 20 locations, then `... and N more location(s)`. The `count=` on the group line is always the true total. A low `--min-similarity` on a repetitive codebase can chain many blocks into one large group, so this keeps the report readable.

## Benchmarks

Measured on Windows 11 with a 6-core / 12-thread Intel i5-12400F, Python 3.12.3 and Node.js
24.18.0. Default settings, median of 3 runs after a warm-up. Methodology, raw
JSON and reproduction steps: [benchmarks/README.md](benchmarks/README.md).

| Corpus | Lines of code | Files | Scan time | Throughput |
| --- | ---: | ---: | ---: | ---: |
| Replicheck's own repository | 6,901 | 45 | 2.4 s | 2,922 lines/sec |
| Synthetic | 50,211 | 166 | 8.5 s | 5,888 lines/sec |
| Synthetic | 150,170 | 485 | 19.3 s | 7,762 lines/sec |
| Synthetic | 375,144 | 1,213 | 44.7 s | 8,396 lines/sec |
| Synthetic | 750,093 | 2,426 | 92.2 s | 8,134 lines/sec |
| Real-world | 629,946 | 2,189 | 69.9 s | 9,007 lines/sec |

Runtime is linear in the amount of code, settling at roughly **8,100–9,000
lines/sec**. The real-world row is 630k lines of genuine third-party library
code (pip, pytest, black, Pygments, setuptools); it is the fastest per line,
because generated code repeats itself while real code does not.

Roughly 58% of a scan is flake8, not Replicheck's own analysis:

| Stage | Share of scan time (~750k corpus) |
| --- | ---: |
| Unused imports/variables and bugs/safety (one flake8 pass) | 58.5% |
| Parse code blocks | 12.5% |
| Cyclomatic complexity | 11.8% |
| Large class detection | 8.7% |
| Large file detection | 7.9% |
| Duplicate detection | 0.6% |

Excluding flake8, the analysis pipeline itself runs at about **20,000 lines/sec**
on synthetic code and **31,000 lines/sec** on real code.

Small repositories are start-up bound, not throughput bound: scanning
Replicheck's own 6,901 lines takes 2.4 s, of which 88% is flake8 process
start-up. Quote a throughput figure together with the scope and the size of the
corpus, or it will not mean much.

## Development

To run tests:

```bash
pytest --cov --cov-report=html
```

### JavaScript/JSX Support

Replicheck now supports duplicate detection, large file/class detection, and cyclomatic complexity analysis for JavaScript and JSX files. Cyclomatic complexity for JS/JSX requires Node.js and the npm package `typhonjs-escomplex` (see Development section).

### JavaScript/JSX Development

To enable JS/JSX metrics, install Node.js and run:

```bash
cd utils
npm install typhonjs-escomplex
```

This is required for cyclomatic complexity analysis of JS/JSX files.

### C# Support

Replicheck supports C# files for:

- Duplicate code block detection (tree-sitter)
- Large file and class detection (tree-sitter)
- Cyclomatic complexity analysis (a compiled Roslyn-based analyzer)

Cyclomatic complexity for C# is measured by a small companion .NET program,
`utils/C#/ComplexityAnalyzer`. It is **not** committed to the repository — build
it once before scanning C# files:

```bash
cd utils/C#/ComplexityAnalyzer
dotnet build
dotnet publish -c Release -r win-x64 --self-contained true /p:PublishSingleFile=true
```

This produces `bin/Release/net9.0/win-x64/ComplexityAnalyzer.exe`, which is the
path Replicheck looks for. Requires the .NET SDK (built and tested with .NET 9).
Duplicate and large-file/class detection for C# work without it; only the
complexity analysis needs the build. If the analyzer is missing, Replicheck
prints a warning and skips C# complexity rather than failing silently.

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

3. Now, every time you commit, the hooks defined in `.pre-commit-config.yaml` will run automatically.

If you want to run the hooks manually on all files (RECOMMENDED Before Commit):

```bash
pre-commit run --all-files
```

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines before submitting issues or pull requests.

## License

This project is licensed under the [Apache License 2.0](LICENSE).
