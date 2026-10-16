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

```bash
# 1. Generate corpora (deterministic; seeded)
python benchmarks/generate_corpus.py --out benchmarks/corpus/small  --loc 50000
python benchmarks/generate_corpus.py --out benchmarks/corpus/medium --loc 150000
python benchmarks/generate_corpus.py --out benchmarks/corpus/large  --loc 375000
python benchmarks/generate_corpus.py --out benchmarks/corpus/xlarge --loc 750000

# 2. Real-world corpus (real code, for accuracy)
python benchmarks/collect_real_corpus.py \
    --source .venv/Lib/site-packages --out benchmarks/corpus/real

# 3. The tool's own source
python benchmarks/collect_real_corpus.py \
    --source . --out benchmarks/corpus/self

# 4. Run the sweep
for size in small medium large xlarge real self; do
  python benchmarks/bench.py --corpus benchmarks/corpus/$size \
      --reps 3 --warmup 1 --json benchmarks/results/$size.json
done

# 5. Render the report
python benchmarks/report.py --results benchmarks/results --out benchmarks/results.md
```

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
- External tools matter enormously to the result. A machine with Node.js or the
  .NET analyzer unavailable will report a *faster* time because those analyses
  return nothing. Both now print a warning, so this is visible rather than
  silent.
- Throughput depends heavily on corpus size. Small corpora are dominated by
  fixed flake8 process start-up (scanning the tool's own 4,550 lines takes 5.2 s,
  97% of it start-up), so a lines/sec figure is only meaningful alongside the
  corpus size and the stages included.
- The synthetic corpora are uniform by construction. The real-world corpus exists
  to check them; on the measurements taken so far it agrees to within 3% on the
  full scan, and real code is *faster* per line for the analysis pipeline alone.
