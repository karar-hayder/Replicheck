#!/usr/bin/env python3
"""
Build a real-world corpus for benchmarking by copying source files out of a
directory tree, preserving relative structure.

The synthetic corpora from generate_corpus.py are uniform by construction. Real
code has deeper nesting, larger functions, real import graphs and genuine
duplication, so scanning it gives a better estimate of real-world performance.

The files are only ever read and copied — nothing in the source tree is
executed or imported. Point it at an installed-packages directory or a checkout:

    python benchmarks/collect_real_corpus.py \\
        --source .venv/Lib/site-packages --out benchmarks/corpus/real

The output directory is gitignored; the corpus is not committed.
"""

import argparse
import json
import shutil
from pathlib import Path

SUPPORTED = {".py", ".js", ".jsx", ".ts", ".tsx", ".cs"}


def count_lines(out: Path, extensions):
    physical = 0
    effective = 0
    files = 0
    per_extension = {}
    for path in sorted(out.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in extensions:
            continue
        files += 1
        per_extension[path.suffix.lower()] = (
            per_extension.get(path.suffix.lower(), 0) + 1
        )
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            physical += 1
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                effective += 1
    return physical, effective, files, per_extension


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Directory to collect from")
    parser.add_argument("--out", required=True, help="Destination corpus directory")
    parser.add_argument(
        "--extensions",
        nargs="+",
        default=sorted(SUPPORTED),
        help=f"Extensions to collect (default: {' '.join(sorted(SUPPORTED))})",
    )
    parser.add_argument(
        "--include",
        nargs="*",
        default=None,
        help="Only copy from these top-level entries of the source directory",
    )
    parser.add_argument(
        "--skip-dirs",
        nargs="*",
        default=[],
        help=(
            "Directory names to skip wherever they appear. Needed when the "
            "source is a project root, so vendored trees like node_modules and "
            ".venv are left out."
        ),
    )
    args = parser.parse_args()

    source = Path(args.source).resolve()
    if not source.is_dir():
        parser.error(f"--source is not a directory: {source}")

    extensions = {e if e.startswith(".") else f".{e}" for e in args.extensions}
    out = Path(args.out)

    # Rebuild from scratch so repeated runs are idempotent.
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    copied = 0
    skipped = 0
    skip_dirs = set(args.skip_dirs)
    for path in source.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in extensions:
            continue
        relative = path.relative_to(source)
        if args.include and relative.parts[0] not in args.include:
            skipped += 1
            continue
        if skip_dirs and any(part in skip_dirs for part in relative.parts):
            skipped += 1
            continue
        destination = out / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copyfile(path, destination)
            copied += 1
        except OSError:
            skipped += 1

    physical, effective, files, per_extension = count_lines(out, extensions)
    manifest = {
        "corpus": str(out),
        "source": str(source),
        "origin": "real-world source tree (copied, not executed)",
        "physical_lines": physical,
        "effective_lines": effective,
        "files": files,
        "files_copied": copied,
        "files_skipped": skipped,
        "by_extension": per_extension,
    }
    (out / "_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
