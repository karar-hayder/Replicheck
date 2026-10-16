#!/usr/bin/env python3
"""
Deterministic synthetic Python corpus generator for Replicheck benchmarks.

Emits realistic-looking Python modules containing:
  - imports, some deliberately unused (exercises flake8 F401)
  - classes with methods (exercises large-class detection)
  - module-level functions with varied cyclomatic complexity (exercises radon)
  - repeated function bodies copied verbatim across modules, which yield
    identical token tuples (exercises duplicate detection)
  - unused locals (exercises flake8 F841)
  - mutable default arguments, eval() and commented-out code (exercises the
    bugbear/bandit/eradicate selections behind bug&safety analysis)
  - TODO/FIXME comments (exercises the TODO/FIXME detector)

Output is fully determined by --seed, so runs are reproducible.

Usage:
    python benchmarks/generate_corpus.py --out benchmarks/corpus/small --loc 50000
"""

import argparse
import json
import random
import shutil
from pathlib import Path

DOMAINS = [
    "orders",
    "users",
    "billing",
    "inventory",
    "reports",
    "sync",
    "cache",
    "auth",
    "search",
    "export",
    "ingest",
    "ledger",
]

# Imports that are emitted but never referenced -> flake8 F401.
UNUSED_IMPORTS = [
    "import os",
    "import sys",
    "import json",
    "import hashlib",
    "import itertools",
    "import datetime",
    "import statistics",
]

# Imports that are referenced by generated helpers -> clean.
USED_IMPORTS = [
    "from typing import Any, Dict, List, Optional",
    "from pathlib import Path",
    "from dataclasses import dataclass, field",
    "from collections import defaultdict, Counter",
]

TODO_TEXTS = [
    "TODO: add error handling here",
    "FIXME: this is a hack, refactor later",
    "TODO: cache this lookup",
    "HACK: works around upstream bug",
    "XXX: revisit before release",
    "OPTIMIZE: replace with batch query",
    "NOTE: assumes sorted input",
    "TODO: extract into a helper",
]

DUP_TEMPLATE_COUNT = 4


def gen_dup_template(idx: int):
    """
    Build a function body that is byte-identical every time it is generated,
    so copies across modules produce identical token tuples and register as
    duplicates. Sized well above the default --min-size of 50 tokens.

    The function name is part of the token tuple, so the name must stay fixed
    for the copies to match.
    """
    name = f"process_batch_{idx}"
    lines = [
        f"def {name}(records, limit, flag):",
        f'    """Template {idx}: intentionally duplicated across modules."""',
        "    out = []",
    ]
    for i in range(20):
        lines.append(f"    item{i} = records[{i}] if len(records) > {i} else None")
        lines.append(f"    if item{i} is not None and flag == {i % 3}:")
        lines.append(f"        out.append(item{i})")
    lines.append("    return out[:limit]")
    lines.append("")
    return name, lines


def gen_bns_triggers(domain: str):
    """
    Constructs that bugbear, bandit and eradicate flag, so the bug&safety
    stage has real work to do rather than returning a vacuous zero.
    """
    return [
        f"def {domain}_mutable_default(cache={{}}, items=[]):",
        '    """Bugbear B006: mutable default argument."""',
        "    items.append(cache)",
        "    return items",
        "",
        f"def {domain}_dynamic_eval(expression):",
        '    """Bandit S307: use of eval."""',
        "    return eval(expression)",
        "",
        "# print('dead code left behind')",
        "",
    ]


def gen_simple_function(name: str, statements: int):
    """A plain helper with moderate branching."""
    lines = [f"def {name}(a, b, c):", '    """Auto-generated helper."""']
    for i in range(statements):
        lines.append(f"    v{i} = a + b * {i} + c")
        lines.append(f"    if v{i} > {i * 3}:")
        lines.append(f"        v{i} = v{i} - {i}")
    lines.append("    return v0 if v0 else 0")
    lines.append("")
    return lines


def gen_complex_function(name: str, branches: int):
    """A branch-heavy function whose cyclomatic complexity exceeds the default 10."""
    lines = [
        f"def {name}(value, mode, limit):",
        '    """Auto-generated branching logic."""',
        "    total = 0",
    ]
    for i in range(branches):
        kw = "if" if i == 0 else "elif"
        lines.append(f"    {kw} value % {branches + 1} == {i}:")
        lines.append(f"        total += {i} * limit")
    lines.append("    else:")
    lines.append("        total -= limit")
    lines.append("    return total")
    lines.append("")
    return lines


def gen_class(name: str, methods: int, statements: int):
    """A class with several methods, large enough to trip the class token threshold."""
    lines = [f"class {name}:", '    """Auto-generated handler."""', ""]
    lines.append("    def __init__(self, config, limit):")
    lines.append("        self.config = config")
    lines.append("        self.limit = limit")
    lines.append("")
    for m in range(methods):
        lines.append(f"    def handle_{m}(self, payload, ctx):")
        lines.append("        scratch = payload")
        for i in range(statements):
            lines.append(f"        step{i} = scratch.get({i}, {i * 2})")
            lines.append(f"        if step{i} > self.limit:")
            lines.append(f"            step{i} = self.limit")
        lines.append("        return scratch")
        lines.append("")
    return lines


def gen_file(rng, dup_templates):
    """Generate one module's source lines."""
    lines = ['"""Auto-generated module for Replicheck benchmarks."""', ""]

    for imp in rng.sample(USED_IMPORTS, 2):
        lines.append(imp)
    for imp in rng.sample(UNUSED_IMPORTS, rng.randint(1, 2)):
        lines.append(imp)
    lines.append("")

    lines.append(f"DEFAULT_LIMIT = {rng.randint(10, 500)}")
    lines.append(f"RETRY_COUNT = {rng.randint(1, 5)}")
    lines.append("")

    domain = rng.choice(DOMAINS)

    for c in range(rng.randint(0, 2)):
        lines.extend(
            gen_class(
                f"{domain.capitalize()}Handler{c}",
                methods=rng.randint(2, 5),
                statements=rng.randint(3, 8),
            )
        )

    lines.extend(gen_bns_triggers(domain))

    # Each duplicate template is emitted at most once per file: the template
    # name is fixed (it must be, for the token tuples to match across files),
    # so emitting it twice would redefine the function in the same module.
    available = list(range(len(dup_templates)))
    rng.shuffle(available)

    target = rng.randint(200, 380)
    counter = 0
    while len(lines) < target:
        roll = rng.random()
        if roll < 0.15 and available:
            lines.extend(dup_templates[available.pop()][1])
        elif roll < 0.35:
            lines.extend(
                gen_complex_function(
                    f"{domain}_route_{counter}", branches=rng.randint(11, 16)
                )
            )
        else:
            lines.extend(
                gen_simple_function(
                    f"{domain}_helper_{counter}", statements=rng.randint(4, 10)
                )
            )
        counter += 1

    # A function with an assigned-but-never-used local -> flake8 F841.
    lines.append(f"def {domain}_legacy_entry(rows):")
    lines.append('    """Legacy entry point kept for compatibility."""')
    lines.append("    unused_buffer = []")
    lines.append("    return len(rows)")
    lines.append("")

    for _ in range(rng.randint(1, 3)):
        lines.append(f"# {rng.choice(TODO_TEXTS)}")
    lines.append("")

    return lines


def _reset_output_dir(out: Path):
    """
    Remove only what this script generates, so a shrink-and-regrow cycle does
    not leave empty package directories or stale modules behind.
    """
    if not out.exists():
        return
    for path in out.iterdir():
        if path.is_dir() and path.name.startswith("pkg_"):
            shutil.rmtree(path)
        elif path.is_file() and (path.suffix == ".py" or path.name == "_manifest.json"):
            path.unlink()


def _count_lines(out: Path):
    """
    Count physical and effective lines by reading the generated files, so the
    manifest can never disagree with what a line counter reports.
    """
    physical = 0
    effective = 0
    files = 0
    for path in out.rglob("*.py"):
        files += 1
        for line in path.read_text(encoding="utf-8").splitlines():
            physical += 1
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                effective += 1
    return physical, effective, files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="Output directory for the corpus")
    parser.add_argument(
        "--loc", type=int, required=True, help="Approximate target physical line count"
    )
    parser.add_argument("--seed", type=int, default=1337, help="RNG seed")
    parser.add_argument(
        "--files-per-dir", type=int, default=40, help="Modules per package directory"
    )
    args = parser.parse_args()

    if args.loc < 1:
        parser.error("--loc must be at least 1")
    if args.files_per_dir < 1:
        parser.error("--files-per-dir must be at least 1")

    out = Path(args.out)
    _reset_output_dir(out)
    out.mkdir(parents=True, exist_ok=True)

    # Seeded PRNG: reproducibility is the point, not unpredictability.
    rng = random.Random(args.seed)  # noqa: S311
    dup_templates = [gen_dup_template(i) for i in range(DUP_TEMPLATE_COUNT)]

    written = 0
    dir_index = 0
    while written < args.loc:
        dir_index += 1
        pkg = out / f"pkg_{dir_index:03d}"
        pkg.mkdir(parents=True, exist_ok=True)
        (pkg / "__init__.py").write_text("", encoding="utf-8")
        for f in range(args.files_per_dir):
            lines = gen_file(rng, dup_templates)
            module = pkg / f"module_{f:03d}.py"
            module.write_text("\n".join(lines) + "\n", encoding="utf-8")
            written += len(lines)
            if written >= args.loc:
                break

    physical, effective, files = _count_lines(out)
    manifest = {
        "corpus": str(out),
        "seed": args.seed,
        "target_loc": args.loc,
        "physical_lines": physical,
        "effective_lines": effective,
        "files": files,
    }
    (out / "_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
