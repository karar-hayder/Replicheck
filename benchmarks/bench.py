#!/usr/bin/env python3
"""
Replicheck benchmark harness.

Measures the real code paths without modifying any production code:

  1. End-to-end CLI   - `python main.py --path <corpus>` in a subprocess.
                        This is the authoritative number; it includes
                        interpreter start-up and every external tool.
  2. Per-stage timing - the same detector calls the runner makes, in the
                        same order, timed individually.
  3. Flake8 probe     - replays the exact flake8 command the tool builds so
                        stderr is visible (the tool swallows it), catching
                        silent failures such as an over-long Windows command
                        line.

Each measurement is repeated; median and spread are reported rather than a
single best-case run.

Usage:
    python benchmarks/bench.py --corpus benchmarks/corpus/large --reps 3 \
        --json benchmarks/results/large.json
"""

import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from replicheck.parser import CodeParser  # noqa: E402
from replicheck.reporter import Reporter  # noqa: E402
from replicheck.runner import ReplicheckRunner  # noqa: E402
from replicheck.tools.Duplication.Duplication import DuplicateDetector  # noqa: E402
from replicheck.tools.TodoFixme.TDFM import TodoFixmeDetector  # noqa: E402
from replicheck.utils import find_files  # noqa: E402

# Defaults mirror main.py exactly.
DEFAULTS = {
    "min_similarity": 0.8,
    "min_size": 50,
    "output_format": "text",
    "output_file": None,
    "ignore_dirs": [
        ".git",
        ".venv",
        "venv",
        "env",
        "ENV",
        "build",
        "dist",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        "coverage",
        "vendor",
        "bower_components",
        ".vscode",
        ".idea",
        ".vs",
        ".next",
    ],
    "complexity_threshold": 10,
    "large_file_threshold": 500,
    "large_class_threshold": 300,
    "top_n_large": 10,
    "extensions": None,
}

STAGE_ORDER = [
    "find_files",
    "parse_code_blocks",
    "complexity",
    "large_files",
    "large_classes",
    "duplicates",
    "unused_flake8",
    "todo_fixme",
    "bugs_and_safety",
    "report",
]


def count_lines(corpus: Path):
    """Physical lines and effective (non-blank, non-comment) lines."""
    physical = 0
    effective = 0
    files = 0
    for path in corpus.rglob("*.py"):
        files += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            physical += 1
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                effective += 1
    return physical, effective, files


def run_stages(corpus: Path, out_file: Path):
    """
    Replay the runner's pipeline with each stage timed separately.
    Returns (timings, counts). Counts let us spot stages that silently
    produced nothing because an external tool failed.
    """
    runner = ReplicheckRunner(path=str(corpus), **DEFAULTS)
    timings = {}
    counts = {}

    t0 = time.perf_counter()
    files = find_files(
        corpus,
        extensions={".py", ".js", ".jsx", ".cs", ".ts", ".tsx"},
        ignore_dirs=DEFAULTS["ignore_dirs"],
    )
    timings["find_files"] = time.perf_counter() - t0
    counts["files"] = len(files)

    parser = CodeParser()
    t0 = time.perf_counter()
    code_blocks = runner.parse_code_files(files, parser)
    timings["parse_code_blocks"] = time.perf_counter() - t0
    counts["code_blocks"] = len(code_blocks)

    t0 = time.perf_counter()
    complexity = runner.analyze_complexity(files)
    timings["complexity"] = time.perf_counter() - t0
    counts["complexity_findings"] = len(complexity)

    t0 = time.perf_counter()
    large_files = runner.analyze_large_files(files)
    timings["large_files"] = time.perf_counter() - t0
    counts["large_files"] = len(large_files)

    t0 = time.perf_counter()
    large_classes = runner.analyze_large_classes(files)
    timings["large_classes"] = time.perf_counter() - t0
    counts["large_classes"] = len(large_classes)

    detector = DuplicateDetector(
        min_similarity=DEFAULTS["min_similarity"], min_size=DEFAULTS["min_size"]
    )
    t0 = time.perf_counter()
    duplicates = detector.find_duplicates(code_blocks)
    timings["duplicates"] = time.perf_counter() - t0
    counts["duplicate_groups"] = len(duplicates)

    t0 = time.perf_counter()
    unused = runner.analyze_unused_imports_vars(files)
    timings["unused_flake8"] = time.perf_counter() - t0
    counts["unused_findings"] = len(unused)

    todo_detector = TodoFixmeDetector()
    t0 = time.perf_counter()
    todo_detector.find_todo_fixme_comments(files)
    timings["todo_fixme"] = time.perf_counter() - t0
    counts["todo_findings"] = len(todo_detector.results)

    t0 = time.perf_counter()
    bns = runner.analyze_bugs_and_safety(files)
    timings["bugs_and_safety"] = time.perf_counter() - t0
    counts["bns_findings"] = len(bns)

    reporter = Reporter(output_format=DEFAULTS["output_format"])
    t0 = time.perf_counter()
    with open(out_file, "w", encoding="utf-8") as fh, redirect_stdout(fh):
        reporter.generate_report(
            output_file=None,
            duplicates=duplicates,
            complexity_results=complexity,
            large_files=large_files,
            large_classes=large_classes,
            unused=unused,
            todo_fixme=todo_detector.results,
            bns_results=bns,
        )
    timings["report"] = time.perf_counter() - t0

    timings["sum_of_stages"] = sum(timings[k] for k in STAGE_ORDER)
    return timings, counts


def probe_flake8(corpus: Path):
    """
    Replay the exact flake8 invocations the tool builds, capturing stderr,
    which the production code discards. Detects silent failures such as an
    over-long command line on Windows.

    flake8 exit codes: 0 = no violations, 1 = violations found (both normal).
    Anything else, a non-empty stderr, or output on stdout when the run claims
    success is treated as suspicious.
    """
    files = find_files(corpus, extensions={".py"}, ignore_dirs=DEFAULTS["ignore_dirs"])
    paths = [str(f) for f in files]
    probes = {}
    windows_limit = 32767  # CreateProcess command-line ceiling on Windows

    commands = {
        "unused_F401_F841": [sys.executable, "-m", "flake8", "--select=F401,F841"]
        + [f"--exclude={d}" for d in DEFAULTS["ignore_dirs"]]
        + paths,
        # Production calls BugNSafetyAnalyzer(files) with no ignore_dirs, so it
        # passes no --exclude flags: find_files has already filtered the list.
        "bns_B_S_E800": [sys.executable, "-m", "flake8", "--select=B,S,E800"] + paths,
    }

    for label, cmd in commands.items():
        arg_chars = sum(len(c) + 1 for c in cmd)
        t0 = time.perf_counter()
        try:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
                check=False,
            )
            elapsed = time.perf_counter() - t0
            stderr = proc.stderr.strip()
            stdout_lines = len(proc.stdout.splitlines())
            suspicious = (
                proc.returncode not in (0, 1)
                or bool(stderr)
                or (proc.returncode == 0 and stdout_lines > 0)
            )
            probes[label] = {
                "returncode": proc.returncode,
                "seconds": elapsed,
                "command_line_chars": arg_chars,
                "over_windows_limit": arg_chars > windows_limit,
                "stdout_lines": stdout_lines,
                "stderr_head": stderr[:400],
                "suspicious": suspicious,
            }
        except Exception as exc:  # noqa: BLE001 - probe must never crash the bench
            probes[label] = {
                "returncode": None,
                "seconds": time.perf_counter() - t0,
                "command_line_chars": arg_chars,
                "over_windows_limit": arg_chars > windows_limit,
                "exception": f"{type(exc).__name__}: {exc}",
                "suspicious": True,
            }

    probes["files_passed"] = len(paths)
    probes["windows_command_line_limit"] = windows_limit
    probes["predicted_overflow"] = any(
        v.get("over_windows_limit") for k, v in probes.items() if isinstance(v, dict)
    )

    # If the single invocation overflows, measure the same work the way the
    # shipped fix performs it. replicheck/tools/flake8_runner.py splits the
    # file list by character budget, so this replays that exact strategy with
    # the same budget — it is the real post-fix cost, not a hypothetical.
    #
    # Note this pays one process start-up per chunk. A fix that used a response
    # file instead would run flake8 once and be cheaper; the start-up component
    # is recorded separately so that difference stays visible.
    if probes["predicted_overflow"]:
        from replicheck.tools.flake8_runner import PATH_BUDGET_CHARS, chunk_paths

        startup = _flake8_startup_seconds()
        chunk_totals = {}
        for label, select, excludes in (
            ("unused_F401_F841", "F401,F841", DEFAULTS["ignore_dirs"]),
            ("bns_B_S_E800", "B,S,E800", None),
        ):
            chunks = chunk_paths(paths, PATH_BUDGET_CHARS)
            total = 0.0
            failures = 0
            for chunk in chunks:
                cmd = [sys.executable, "-m", "flake8", f"--select={select}"]
                cmd += [f"--exclude={d}" for d in excludes or ()]
                cmd += chunk
                t0 = time.perf_counter()
                try:
                    proc = subprocess.run(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        encoding="utf-8",
                        check=False,
                    )
                    total += time.perf_counter() - t0
                    if proc.returncode not in (0, 1):
                        failures += 1
                except Exception:  # noqa: BLE001
                    failures += 1
                    total += time.perf_counter() - t0
            chunk_totals[label] = {
                "chunks": len(chunks),
                "path_budget_chars": PATH_BUDGET_CHARS,
                "total_seconds": total,
                "single_invocation_startup_seconds": startup,
                "estimated_startup_seconds": startup * len(chunks),
                "failed_chunks": failures,
            }
        probes["chunked_estimate"] = chunk_totals

    return probes


def _flake8_startup_seconds():
    """
    Time one flake8 run over a single trivial file. Exposes how much of a
    chunked run is process start-up rather than analysis.
    """
    with tempfile.TemporaryDirectory() as tmp:
        probe_file = Path(tmp) / "probe.py"
        probe_file.write_text("x = 1\n", encoding="utf-8")
        cmd = [sys.executable, "-m", "flake8", "--select=F401", str(probe_file)]
        t0 = time.perf_counter()
        try:
            subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
                check=False,
            )
        except Exception:  # noqa: BLE001 - probe must never crash the bench
            return 0.0
        return time.perf_counter() - t0


def run_cli_once(corpus: Path, out_file: Path):
    """One end-to-end CLI run in a subprocess. Returns elapsed seconds."""
    cmd = [
        sys.executable,
        str(ROOT / "main.py"),
        "--path",
        str(corpus),
        "--output-format",
        DEFAULTS["output_format"],
        "--output-file",
        str(out_file),
    ]
    t0 = time.perf_counter()
    proc = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8"
    )
    elapsed = time.perf_counter() - t0
    return elapsed, proc.returncode


def summarize(samples):
    return {
        "median": statistics.median(samples),
        "min": min(samples),
        "max": max(samples),
        "all": samples,
    }


def machine_metadata():
    meta = {
        "platform": platform.platform(),
        "processor": platform.processor(),
        "python": sys.version.split()[0],
        "cpu_count": os.cpu_count(),
    }
    for tool, cmd in (
        ("node", ["node", "--version"]),
        ("dotnet", ["dotnet", "--version"]),
    ):
        try:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
                check=False,
            )
            meta[tool] = proc.stdout.strip() or "unavailable"
        except Exception:
            meta[tool] = "unavailable"
    return meta


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--reps", type=int, default=3)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--json", dest="json_out", default=None)
    parser.add_argument("--skip-probe", action="store_true")
    args = parser.parse_args()

    if args.reps < 1:
        parser.error("--reps must be at least 1")
    if args.warmup < 0:
        parser.error("--warmup cannot be negative")

    corpus = Path(args.corpus).resolve()
    if not corpus.exists():
        print(f"Error: corpus not found: {corpus}")
        return 1

    physical, effective, n_files = count_lines(corpus)
    print(f"Corpus: {corpus}")
    print(f"  files={n_files} physical_lines={physical} effective_lines={effective}")

    # Scratch reports go to a temporary directory that cleans itself up; each
    # one is a full report and a sweep would otherwise leave tens of MB behind.
    with tempfile.TemporaryDirectory(prefix="replicheck-bench-") as scratch:
        tmp_dir = Path(scratch)

        # Warm-up (populate caches, page in the interpreter and plugins).
        for _ in range(args.warmup):
            run_cli_once(corpus, tmp_dir / "warmup.txt")
            run_stages(corpus, tmp_dir / "warmup_stages.txt")

        cli_samples = []
        for i in range(args.reps):
            elapsed, rc = run_cli_once(corpus, tmp_dir / f"cli_{i}.txt")
            if rc != 0:
                print(f"  [warn] CLI run {i} exited with code {rc}")
            cli_samples.append(elapsed)
            print(f"  cli run {i + 1}/{args.reps}: {elapsed:.3f}s")

        stage_runs = []
        counts = {}
        for i in range(args.reps):
            timings, counts = run_stages(corpus, tmp_dir / f"stages_{i}.txt")
            stage_runs.append(timings)

    stage_summary = {}
    for stage in STAGE_ORDER + ["sum_of_stages"]:
        stage_summary[stage] = summarize([r[stage] for r in stage_runs])

    cli = summarize(cli_samples)
    core_median = stage_summary["sum_of_stages"]["median"]

    result = {
        "corpus": {
            "path": str(corpus),
            "files": n_files,
            "physical_lines": physical,
            "effective_lines": effective,
        },
        "settings": {
            "min_similarity": DEFAULTS["min_similarity"],
            "min_size": DEFAULTS["min_size"],
            "output_format": DEFAULTS["output_format"],
            "output_destination": "file (to capture the report)",
            "complexity_threshold": DEFAULTS["complexity_threshold"],
            "large_file_threshold": DEFAULTS["large_file_threshold"],
            "large_class_threshold": DEFAULTS["large_class_threshold"],
            "top_n_large": DEFAULTS["top_n_large"],
            "extensions": "default (.py .js .jsx .cs .ts .tsx)",
        },
        "machine": machine_metadata(),
        "reps": args.reps,
        "warmup_runs": args.warmup,
        "probe_method": "single-shot (no repetitions, no warm-up)",
        "cli_end_to_end": cli,
        "stages": stage_summary,
        "counts": counts,
        "throughput": {
            "cli_lines_per_sec": (physical / cli["median"] if cli["median"] else None),
            "core_lines_per_sec": (physical / core_median if core_median else None),
        },
    }

    if not args.skip_probe:
        print("Probing flake8 invocations...")
        result["flake8_probe"] = probe_flake8(corpus)

    print()
    print(
        f"CLI end-to-end median: {cli['median']:.3f}s "
        f"(min {cli['min']:.3f}s, max {cli['max']:.3f}s)"
    )
    print(f"Core stages median:    {core_median:.3f}s")
    print(
        f"CLI throughput:        {result['throughput']['cli_lines_per_sec']:,.0f} lines/sec"
    )
    print()
    print("Per-stage medians:")
    for stage in STAGE_ORDER:
        s = stage_summary[stage]
        print(
            f"  {stage:20s} {s['median']:8.3f}s  ({s['median'] / core_median * 100:5.1f}%)"
        )

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"\nWrote {out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
