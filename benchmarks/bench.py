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
from replicheck.tools.flake8_runner import run_flake8_for_scan  # noqa: E402
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
    "flake8_checks",
    "todo_fixme",
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


class GuardError(RuntimeError):
    """A pre-flight or sanity check failed. Abort rather than waste a sweep."""


MANIFEST_NAME = "_manifest.json"
# Must match what the generators record as "files"/"physical_lines".
CORPUS_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".cs"}
# flake8 process start-up alone is ~1.5-2s, so a stage this fast did not run.
MIN_FLAKE8_SECONDS = 0.05
# Distinct from 1 (bad usage) so a sweep driver can tell them apart.
EXIT_GUARD_FAILED = 2


def verify_corpus(corpus: Path, check_lines: bool = True):
    """
    Fail fast when a corpus no longer matches how it was generated.

    A formatter run over a corpus rewrites it silently - isort collapsing
    multi-line imports is how this actually happened - and every measurement
    afterwards is against a different corpus than the manifest describes, while
    the reported line count quietly drifts. Both are checked here, before any
    time is spent scanning.
    """
    files = sorted(
        p for p in corpus.rglob("*") if p.is_file() and p.suffix in CORPUS_EXTENSIONS
    )
    if not files:
        raise GuardError(f"{corpus} contains no source files to scan")

    manifest_path = corpus / MANIFEST_NAME
    if not manifest_path.exists():
        return

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise GuardError(f"{manifest_path} could not be read: {exc}") from exc

    expected_files = manifest.get("files")
    if expected_files is not None and len(files) != expected_files:
        raise GuardError(
            f"{corpus.name}: {len(files)} source file(s) on disk but the "
            f"manifest records {expected_files}. Regenerate the corpus."
        )

    manifest_mtime = manifest_path.stat().st_mtime
    rewritten = [p for p in files if p.stat().st_mtime > manifest_mtime]
    if rewritten:
        raise GuardError(
            f"{corpus.name}: {len(rewritten)} file(s) are newer than "
            f"{MANIFEST_NAME} (e.g. {rewritten[0].name}). Something rewrote the "
            "corpus after it was generated - a linter is the usual cause. "
            "Regenerate the corpus before measuring it."
        )

    if check_lines:
        physical = sum(
            len(p.read_text(encoding="utf-8", errors="replace").splitlines())
            for p in files
        )
        expected_lines = manifest.get("physical_lines")
        if expected_lines is not None and physical != expected_lines:
            raise GuardError(
                f"{corpus.name}: {physical} lines on disk but the manifest "
                f"records {expected_lines}. Regenerate the corpus."
            )


def verify_flake8_runnable():
    """The two largest stages depend on flake8; if it cannot run, abort."""
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "flake8", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            check=False,
        )
    except Exception as exc:  # noqa: BLE001 - surface any launch failure as a guard
        raise GuardError(f"flake8 could not be launched: {exc}") from exc
    if proc.returncode != 0:
        raise GuardError(
            "flake8 is not runnable, so the unused-import and bug&safety stages "
            "would silently report nothing and the timings would be meaningless."
        )


def verify_plausible(stage_summary, python_files, cli, max_spread):
    """
    Catch the two failures that make a result worthless rather than merely
    slow: a stage that did not actually run, and a machine too busy to time on.
    """
    flake8_median = (stage_summary.get("flake8_checks") or {}).get("median")
    if (
        python_files
        and flake8_median is not None
        and flake8_median < MIN_FLAKE8_SECONDS
    ):
        raise GuardError(
            f"flake8_checks took {flake8_median:.3f}s for {python_files} Python "
            "file(s). flake8 cannot start that fast, so the stage did not run."
        )

    if len(cli["all"]) >= 2 and cli["median"]:
        spread = (cli["max"] - cli["min"]) / cli["median"]
        if spread > max_spread:
            raise GuardError(
                f"repetition spread {spread:.1%} exceeds the {max_spread:.0%} "
                "limit: the machine was busy and these timings are not "
                "reportable. Close other work and re-run, or raise --max-spread."
            )


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

    # One flake8 pass now serves both detectors, mirroring ReplicheckRunner.run().
    t0 = time.perf_counter()
    unused_findings, bug_safety_findings = run_flake8_for_scan(
        files, ignore_dirs=DEFAULTS["ignore_dirs"]
    )
    unused = runner.analyze_unused_imports_vars(files, findings=unused_findings)
    bns = runner.analyze_bugs_and_safety(files, findings=bug_safety_findings)
    timings["flake8_checks"] = time.perf_counter() - t0
    counts["unused_findings"] = len(unused)
    counts["bns_findings"] = len(bns)

    todo_detector = TodoFixmeDetector()
    t0 = time.perf_counter()
    todo_detector.find_todo_fixme_comments(files)
    timings["todo_fixme"] = time.perf_counter() - t0
    counts["todo_findings"] = len(todo_detector.results)

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
    """Median/min/max over the repetition samples; empty means "not measured"."""
    if not samples:
        return {"median": None, "min": None, "max": None, "all": []}
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


def build_parser():
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=(
            "Defaults are tuned for a quick development check: one scan each of "
            "the CLI and the per-stage replay, no warm-up, no flake8 probe. A "
            "full measurement for results.md needs --reps 3 --warmup 1 --probe, "
            "which costs roughly 4x as much per corpus."
        ),
    )
    parser.add_argument("--corpus", required=True)
    parser.add_argument(
        "--reps",
        type=int,
        default=1,
        help="timed repetitions (default: 1; use 3 for a published measurement)",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=0,
        help="warm-up runs before timing (default: 0; use 1 for a published measurement)",
    )
    parser.add_argument("--json", dest="json_out", default=None)
    parser.add_argument(
        "--probe",
        action="store_true",
        help=(
            "replay the pre-fix flake8 command line and time the chunked "
            "alternative. Slow on large corpora; only needed when documenting "
            "the command-line limit."
        ),
    )
    parser.add_argument(
        "--cli-only",
        action="store_true",
        help=(
            "skip the per-stage replay and time the end-to-end CLI alone. "
            "Roughly halves a quick check, but the JSON then lacks stage data "
            "and report.py will skip it."
        ),
    )
    parser.add_argument(
        "--max-spread",
        type=float,
        default=0.25,
        help=(
            "abort if the spread across repetitions exceeds this fraction of "
            "the median, which means the machine was too busy to time on "
            "(default: 0.25)"
        ),
    )
    parser.add_argument(
        "--no-guards",
        action="store_true",
        help="skip the integrity, environment and sanity checks",
    )
    return parser


def validate_args(parser, args):
    if args.reps < 1:
        parser.error("--reps must be at least 1")
    if args.warmup < 0:
        parser.error("--warmup cannot be negative")
    if args.cli_only and args.json_out:
        print(
            "[note] --cli-only omits stage data, so report.py will skip this "
            "JSON file.",
            file=sys.stderr,
        )


def print_summary(cli, core_median, stage_summary, result):
    print()
    print(
        f"CLI end-to-end median: {cli['median']:.3f}s "
        f"(min {cli['min']:.3f}s, max {cli['max']:.3f}s)"
    )
    if core_median is None:
        print("Core stages:           skipped (--cli-only)")
    else:
        print(f"Core stages median:    {core_median:.3f}s")
    print(
        f"CLI throughput:        {result['throughput']['cli_lines_per_sec']:,.0f} lines/sec"
    )
    if core_median is None:
        return
    print()
    print("Per-stage medians:")
    for stage in STAGE_ORDER:
        s = stage_summary[stage]
        print(
            f"  {stage:20s} {s['median']:8.3f}s  "
            f"({s['median'] / core_median * 100:5.1f}%)"
        )


def guarded_preflight(args, corpus):
    """True if the scan may proceed. Prints and returns False on a guard failure."""
    if args.no_guards:
        return True
    try:
        verify_corpus(corpus)
        verify_flake8_runnable()
    except GuardError as exc:
        print(f"[ABORT] {exc}", file=sys.stderr)
        return False
    return True


def guarded_plausibility(args, stage_summary, python_file_count, cli):
    """True if the result is worth keeping. Prints and returns False otherwise."""
    if args.no_guards:
        return True
    try:
        verify_plausible(stage_summary, python_file_count, cli, args.max_spread)
    except GuardError as exc:
        print(f"[ABORT] {exc}", file=sys.stderr)
        return False
    return True


def main():
    parser = build_parser()
    args = parser.parse_args()
    validate_args(parser, args)

    corpus = Path(args.corpus).resolve()
    if not corpus.exists():
        print(f"Error: corpus not found: {corpus}")
        return 1

    if not guarded_preflight(args, corpus):
        return EXIT_GUARD_FAILED

    physical, effective, n_files = count_lines(corpus)
    python_file_count = sum(1 for _ in corpus.rglob("*.py"))
    print(f"Corpus: {corpus}")
    print(f"  files={n_files} physical_lines={physical} effective_lines={effective}")

    # Scratch reports go to a temporary directory that cleans itself up; each
    # one is a full report and a sweep would otherwise leave tens of MB behind.
    with tempfile.TemporaryDirectory(prefix="replicheck-bench-") as scratch:
        tmp_dir = Path(scratch)

        # Warm-up (populate caches, page in the interpreter and plugins).
        for _ in range(args.warmup):
            run_cli_once(corpus, tmp_dir / "warmup.txt")
            if not args.cli_only:
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
        if not args.cli_only:
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

    if not guarded_plausibility(args, stage_summary, python_file_count, cli):
        return EXIT_GUARD_FAILED

    if args.probe:
        print("Probing flake8 invocations...")
        result["flake8_probe"] = probe_flake8(corpus)

    print_summary(cli, core_median, stage_summary, result)

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"\nWrote {out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
