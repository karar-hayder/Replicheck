# Replicheck benchmarks

Reproducible performance measurements for Replicheck.

## What is measured

1. **CLI end-to-end** (authoritative) — `python main.py --path <corpus>` run in a
   subprocess, so interpreter start-up and every external tool are included.
2. **Per-stage breakdown** — the same detector calls the runner makes, in the
   same order, timed individually.
3. **flake8 probe** — replays the exact flake8 commands the tool builds and
   captures stderr, which the production code discards. Detects silent
   failures such as an over-long Windows command line.

No production code is modified. `bench.py` imports `ReplicheckRunner` and the
individual detectors and times them directly.

## Reproduce

**Development check (fast).** Defaults are tuned for this: one CLI scan, one
per-stage scan, no warm-up, no flake8 probe.

```bash
python benchmarks/bench.py --corpus benchmarks/corpus/small
python benchmarks/bench.py --corpus benchmarks/corpus/self      # seconds
python benchmarks/bench.py --corpus benchmarks/corpus/small --cli-only  # fastest
```

**Full measurement (slow).** One published sweep scans roughly 48 times in
total, because each corpus is scanned once per warm-up and per repetition, for
both the CLI and the stage replay. Budget 20-40 minutes and run it only when
updating `results.md`:

```bash
# 1. Corpora (deterministic; seeded)
python benchmarks/generate_corpus.py --out benchmarks/corpus/small  --loc 50000
python benchmarks/generate_corpus.py --out benchmarks/corpus/medium --loc 150000
python benchmarks/generate_corpus.py --out benchmarks/corpus/large  --loc 375000
python benchmarks/generate_corpus.py --out benchmarks/corpus/xlarge --loc 750000

# 2. Real-world corpus (real code, for accuracy)
python benchmarks/collect_real_corpus.py \
    --source .venv/Lib/site-packages --out benchmarks/corpus/real

# 3. The tool's own source (tracked files, no vendored trees)
python benchmarks/collect_real_corpus.py --source . --out benchmarks/corpus/self \
    --extensions .py --include replicheck tests benchmarks \
    --skip-dirs node_modules .venv __pycache__

# 4. Full sweep: 3 reps, 1 warm-up, probe enabled. Stops at the first problem.
python benchmarks/sweep.py --full

# 5. Render the report
python benchmarks/report.py --results benchmarks/results --out benchmarks/results.md
```

`benchmarks/sweep.py` verifies every corpus up front, then runs them in order
and **stops at the first failure** instead of carrying on. A plain shell loop
would ignore `bench.py`'s exit code and keep going.

### Flags

| Flag | Default | Notes |
| --- | --- | --- |
| `--reps` | `1` | Timed repetitions. Use `3` for a published measurement. |
| `--warmup` | `0` | Warm-up runs before timing. Use `1` for a published measurement. |
| `--probe` | off | Replays the *pre-fix* flake8 command line and times the chunked alternative. Slow on large corpora; only needed when documenting the command-line limit. |
| `--cli-only` | off | Skips the per-stage replay and times the end-to-end CLI alone. Roughly halves a quick check, but the JSON then has no stage data and `report.py` skips it. |
| `--max-spread` | `0.25` | Abort if the spread across repetitions exceeds this fraction of the median. |
| `--no-guards` | off | Skip every check below. |

### Guards

A sweep is expensive, so it fails fast rather than discovering a problem at the
end. Every check exits with code **2**, and `sweep.py` treats that as a stop
signal, so a broken corpus costs seconds instead of the whole run.

Checked before any scanning starts:

- **The corpus still matches its `_manifest.json`.** Source file count, total
  lines, and whether any file is *newer than the manifest*. That last one is the
  load-bearing check: a formatter run over a corpus rewrites it silently, and
  every measurement afterwards is against a different corpus than the manifest
  describes. This has really happened — `isort` rewrote the corpora once, and
  the guard now catches exactly that.
- **flake8 is runnable.** It backs the two largest stages; if it cannot start,
  they would quietly report nothing and the timing would be meaningless.

Checked after the runs complete, before the JSON is written:

- **The flake8 stage actually ran.** flake8 start-up alone is ~1.5-2s, so a
  stage that reports `>0.05s` while the corpus has Python files did not run.
- **The repetitions agree.** If the spread across repetitions exceeds
  `--max-spread`, the machine was too busy to time on and the result is
  discarded rather than published. This is the contamination signal; absolute
  CPU load is not, because a consistently busy machine produces consistent — and
  consistently wrong — numbers.

Keep linters away from the corpora. `setup.cfg` excludes `benchmarks/corpus/**`
from flake8 and `extend_skip_glob`s it in isort, and Black skips it via
`.gitignore`. If that protection is ever removed, the integrity guard is what
tells you.

A `--json` file written with `--cli-only` cannot be rendered by `report.py`,
which needs the stage timings. A full sweep for `results.md` always uses
`--reps 3 --warmup 1 --probe`.

Corpora are gitignored. Regenerating with the same `--seed` produces identical
output.

Note that `--source .` for the self-scan picks up `node_modules` and `.venv`;
prefer copying only the tracked sources (see how `benchmarks/corpus/self` is
built) or pass `--include`.

## Corpus shape

`generate_corpus.py` emits Python modules containing classes with methods,
functions with varied branching, imports (some deliberately unused), repeated
verbatim function bodies, unused locals, mutable default arguments, `eval` calls,
commented-out code and TODO/FIXME comments. It is designed so that every
detector has real work to do — a corpus that produces no findings would measure
an unrealistic short-circuit.

`collect_real_corpus.py` copies source files out of a real tree, preserving
relative structure. It only reads and copies; nothing in the source tree is
imported or executed. Real code is the accuracy check on the synthetic corpora:
it has deeper nesting, larger functions, real import graphs and genuine
duplication.

Both **physical lines** (what an editor or `wc -l` reports) and **effective
lines** (non-blank, non-comment) are recorded, because "lines of code" is
ambiguous and the two differ by roughly 6%.

## Notes on interpretation

- Medians are reported, not best-case runs. The spread across repetitions is in
  the JSON and the report.
- **Measure on an idle machine.** These runs are wall-clock and nothing
  compensates for other load. On the machine that produced `results.md`,
  unrelated processes holding ~70% CPU inflated a 750k-line scan from ~90s to
  ~102s, about 12%. The per-corpus `min`/`max` in the report is the tell: a
  spread wider than a few percent means the machine was busy and the absolute
  numbers are pessimistic.
- External tools matter enormously to the result. A machine with Node.js or the
  .NET analyzer unavailable will report a *faster* time because those analyses
  return nothing. Both now print a warning, so this is visible rather than
  silent.
- Throughput depends heavily on corpus size. Small corpora are dominated by
  fixed flake8 process start-up (scanning the tool's own 4,550 lines is mostly
  flake8 start-up, not analysis), so a lines/sec figure is only meaningful
  alongside the corpus size and the stages included.
- The synthetic corpora are uniform by construction and **overstate
  duplication**: the 750k corpus has 420 distinct tokens against 99,911 in the
  real-world corpus, so nearly every generated function shares most of its
  vocabulary. Any duplication figure from the synthetic corpora is a property
  of the generator, not of real code. Use the real-world corpus for those.
- The real-world corpus exists to check the synthetic ones; on the measurements
  taken so far it agrees on the full scan, and real code is faster per line for
  the analysis pipeline alone.
