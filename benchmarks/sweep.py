#!/usr/bin/env python3
"""
Run the benchmark across every corpus, stopping at the first sign of trouble.

`bench.py` aborts on a bad corpus, a broken environment or a contaminated
measurement. A plain shell loop would ignore that and carry on to the next
corpus, so this driver exists to honour the failure and stop.

It also verifies every corpus up front: a problem with the fifth corpus should
surface in seconds, not after twenty minutes of scanning the first four.

Usage:
    python benchmarks/sweep.py                 # development check (fast)
    python benchmarks/sweep.py --full          # publishable sweep for results.md
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from bench import GuardError, verify_corpus  # noqa: E402

CORPORA = ["small", "medium", "large", "xlarge", "real", "self"]
EXIT_GUARD_FAILED = 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-dir", default=str(ROOT / "benchmarks" / "corpus"))
    parser.add_argument("--results-dir", default=str(ROOT / "benchmarks" / "results"))
    parser.add_argument(
        "--corpora", nargs="+", default=CORPORA, help="which corpora to run, in order"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="publishable measurement: --reps 3 --warmup 1 --probe",
    )
    parser.add_argument("--reps", type=int, default=None)
    parser.add_argument("--warmup", type=int, default=None)
    parser.add_argument("--probe", action="store_true", default=None)
    parser.add_argument(
        "--skip-integrity-lines",
        action="store_true",
        help="check file counts and mtimes but not line counts (slightly faster)",
    )
    args = parser.parse_args()

    reps = args.reps if args.reps is not None else (3 if args.full else 1)
    warmup = args.warmup if args.warmup is not None else (1 if args.full else 0)
    probe = args.probe if args.probe is not None else bool(args.full)

    corpus_dir = Path(args.corpus_dir)
    results_dir = Path(args.results_dir)

    # Pre-flight every corpus before spending time on any of them.
    print("Verifying corpora...")
    for name in args.corpora:
        path = corpus_dir / name
        if not path.is_dir():
            print(f"[ABORT] corpus missing: {path}", file=sys.stderr)
            return EXIT_GUARD_FAILED
        try:
            verify_corpus(path, check_lines=not args.skip_integrity_lines)
        except GuardError as exc:
            print(f"[ABORT] {exc}", file=sys.stderr)
            print(
                "No corpora were benchmarked. Fix the corpus and re-run.",
                file=sys.stderr,
            )
            return EXIT_GUARD_FAILED
        print(f"  ok  {name}")
    print()

    print(
        f"Running {len(args.corpora)} corpora "
        f"(reps={reps}, warmup={warmup}, probe={'on' if probe else 'off'})..."
    )
    for index, name in enumerate(args.corpora, 1):
        print(f"\n########## {name} ({index}/{len(args.corpora)}) ##########")
        command = [
            sys.executable,
            str(ROOT / "benchmarks" / "bench.py"),
            "--corpus",
            str(corpus_dir / name),
            "--reps",
            str(reps),
            "--warmup",
            str(warmup),
            "--json",
            str(results_dir / f"{name}.json"),
        ]
        if probe:
            command.append("--probe")

        completed = subprocess.run(command, cwd=str(ROOT))
        if completed.returncode == EXIT_GUARD_FAILED:
            print(
                f"\n[ABORT] '{name}' failed its checks; stopping rather than "
                f"measuring the remaining {len(args.corpora) - index} corpora.",
                file=sys.stderr,
            )
            return EXIT_GUARD_FAILED
        if completed.returncode != 0:
            print(
                f"\n[ABORT] '{name}' exited with code {completed.returncode}; "
                "stopping.",
                file=sys.stderr,
            )
            return completed.returncode

    print("\nAll corpora completed. Render the report with:")
    print("  python benchmarks/report.py --results benchmarks/results")
    return 0


if __name__ == "__main__":
    sys.exit(main())
