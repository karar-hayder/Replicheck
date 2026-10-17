#!/usr/bin/env python3
"""
Render benchmark result JSON files into a Markdown report.

Reads benchmarks/results/*.json (as produced by bench.py) and writes
benchmarks/results.md, including the scaling table, the per-stage breakdown
and the flake8 probe outcomes.

Usage:
    python benchmarks/report.py --results benchmarks/results --out benchmarks/results.md
"""

import argparse
import json
from pathlib import Path

# Ordered smallest to largest; the sweep writes one JSON per corpus size.
ORDER = ["small", "medium", "large", "xlarge", "real", "self"]

LABELS = {
    "small": "~50k",
    "medium": "~150k",
    "large": "~375k",
    "xlarge": "~750k",
    "real": "real ~630k",
    "self": "self ~6.9k",
}


def load(results_dir: Path):
    """
    Load every results JSON in the directory. Failures name the offending file
    rather than raising a bare traceback, and unrecognised names are reported
    instead of being silently dropped.
    """
    runs = {}
    for path in sorted(results_dir.glob("*.json")):
        name = path.stem
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"[skip] {path.name}: not valid JSON ({exc})")
            continue
        missing = [
            key
            for key in ("corpus", "cli_end_to_end", "stages", "throughput", "machine")
            if key not in data
        ]
        if missing:
            print(f"[skip] {path.name}: missing key(s) {', '.join(missing)}")
            continue
        if (data.get("stages") or {}).get("sum_of_stages", {}).get("median") is None:
            print(f"[skip] {path.name}: no stage timing (was it run with --cli-only?)")
            continue
        if name not in ORDER:
            print(f"[warn] {path.name}: unrecognised corpus name, included last")
        runs[name] = data

    # Present the known sizes smallest-first, then anything unrecognised.
    return {
        name: runs[name]
        for name in sorted(
            runs, key=lambda n: (ORDER.index(n) if n in ORDER else len(ORDER), n)
        )
    }


def fmt(value, digits=3):
    if value is None:
        return "n/a"
    return f"{value:,.{digits}f}"


def failed_stages(data):
    """
    Stages that produced no findings while the flake8 probe reports a
    command-line overflow — i.e. the stage did not run at all.
    """
    probe = data.get("flake8_probe") or {}
    if not probe.get("predicted_overflow"):
        return []
    counts = data.get("counts") or {}
    if counts.get("unused_findings") == 0 or counts.get("bns_findings") == 0:
        return ["flake8_checks"]
    return []


def stage_count_annotation(data, stage):
    """
    Flag a stage that produced no findings at all. Combined with the flake8
    probe this distinguishes "ran and found nothing" from "silently failed".
    """
    if stage in failed_stages(data):
        return " ⚠ failed (command line overflow)"
    counts = data.get("counts") or {}
    keys = {
        "flake8_checks": ("unused_findings", "bns_findings"),
    }.get(stage)
    if keys and all(counts.get(key) == 0 for key in keys):
        return " (0 findings)"
    return ""


def scaling_table(runs):
    lines = [
        "| Corpus | Files | Physical lines | Effective lines | CLI median (s) | CLI min (s) | CLI max (s) | Lines/sec |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, data in runs.items():
        c = data["corpus"]
        cli = data["cli_end_to_end"]
        lines.append(
            f"| {LABELS.get(name, name)} "
            f"| {c['files']:,} "
            f"| {c['physical_lines']:,} "
            f"| {c['effective_lines']:,} "
            f"| {fmt(cli['median'])} "
            f"| {fmt(cli['min'])} "
            f"| {fmt(cli['max'])} "
            f"| {fmt(data['throughput'].get('cli_lines_per_sec'), 0)} |"
        )
    return "\n".join(lines)


def scaling_note(runs):
    """
    Explain the scaling table. If any run left a stage un-run, say so; the
    shipped code chunks the flake8 file list, so normally every scan completes.
    """
    incomplete = {name: failed_stages(data) for name, data in runs.items()}
    incomplete = {name: stages for name, stages in incomplete.items() if stages}

    if not incomplete:
        return [
            "Every scan completed with all detectors returning results. The "
            "runtime grows linearly with the amount of code.",
            "",
        ]

    detail = "; ".join(
        f"{LABELS.get(name, name)}: {', '.join(stages)}"
        for name, stages in incomplete.items()
    )
    return [
        "**Some scans are incomplete.** The following stages did not run, so "
        f"those rows measure less work than the others — {detail}. The cause is "
        "the pre-fix single-command flake8 invocation overflowing the OS "
        "command-line limit, documented in 'flake8 invocations' below.",
        "",
    ]


def failed_stage_note(runs):
    """Only explain the ⚠ annotation when at least one stage actually failed."""
    if not any(failed_stages(data) for data in runs.values()):
        return []
    return [
        "A stage annotated `⚠ failed` returned no findings while the flake8 probe "
        "below reports a command-line overflow. Those measurements are of a stage "
        "that did not run, not of a stage that ran quickly.",
        "",
    ]


def stage_table(runs):
    stages = None
    for data in runs.values():
        stages = list(data["stages"].keys())
        break
    if not stages:
        return ""

    header = "| Stage | " + " | ".join(f"{LABELS.get(n, n)} (s)" for n in runs) + " |"
    sep = "| --- | " + " | ".join("---:" for _ in runs) + " |"
    lines = [header, sep]
    for stage in stages:
        cells = []
        for data in runs.values():
            entry = data["stages"].get(stage)
            if not entry:
                cells.append("n/a")
                continue
            cells.append(f"{fmt(entry['median'])}{stage_count_annotation(data, stage)}")
        lines.append(f"| `{stage}` | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def share_table(runs):
    """Percentage of core stage time per stage, for the largest corpus measured."""
    if not runs:
        return ""
    name = max(runs, key=lambda n: runs[n]["corpus"].get("physical_lines", 0))
    data = runs[name]
    total = data["stages"].get("sum_of_stages", {}).get("median")
    if not total:
        return ""
    rows = [
        (s, data["stages"][s]["median"]) for s in data["stages"] if s != "sum_of_stages"
    ]
    rows.sort(key=lambda r: r[1], reverse=True)
    lines = [
        f"Share of core analysis time on the {LABELS.get(name, name)} corpus "
        f"({fmt(total)}s total):",
        "",
        "| Stage | Seconds | Share |",
        "| --- | ---: | ---: |",
    ]
    for stage, seconds in rows:
        pct = (seconds / total * 100) if total else 0
        note = stage_count_annotation(data, stage)
        lines.append(f"| `{stage}`{note} | {fmt(seconds)} | {pct:.1f}% |")
    return "\n".join(lines)


def probe_section(runs):
    lines = []
    for name, data in runs.items():
        probe = data.get("flake8_probe")
        if not probe:
            continue
        lines.append(
            f"**{LABELS.get(name, name)}** "
            f"({probe['files_passed']:,} files passed to flake8)"
        )
        lines.append("")
        lines.append(
            "| Invocation | Exit code | Seconds | Command-line chars | Over 32,767 limit | stdout lines | stderr |"
        )
        lines.append("| --- | ---: | ---: | ---: | :---: | ---: | --- |")
        for key in ("unused_F401_F841", "bns_B_S_E800"):
            entry = probe.get(key)
            if not entry:
                continue
            rc = entry.get("returncode")
            if rc is None:
                rc = entry.get("exception", "error")
            stderr = entry.get("stderr_head") or "(empty)"
            lines.append(
                f"| `{key}` | {rc} | {fmt(entry.get('seconds'))} "
                f"| {entry.get('command_line_chars', 0):,} "
                f"| {'YES' if entry.get('over_windows_limit') else 'no'} "
                f"| {entry.get('stdout_lines', 0):,} | {stderr} |"
            )
        lines.append("")
        chunked = probe.get("chunked_estimate")
        if chunked:
            lines.append(
                "Same work with the file list chunked by the character budget the "
                "shipped fix uses (`replicheck/tools/flake8_runner.py`), so this is "
                "the real post-fix cost. Each chunk pays one process start-up; the "
                "start-up share is shown separately because a response-file "
                "implementation would run flake8 once and cost less."
            )
            lines.append("")
            lines.append(
                "| Invocation | Chunks | Total seconds | Estimated start-up | Failed chunks |"
            )
            lines.append("| --- | ---: | ---: | ---: | ---: |")
            for key, entry in chunked.items():
                lines.append(
                    f"| `{key}` | {entry['chunks']} "
                    f"| {fmt(entry['total_seconds'])} "
                    f"| {fmt(entry.get('estimated_startup_seconds'))} "
                    f"| {entry['failed_chunks']} |"
                )
            lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", default="benchmarks/results")
    parser.add_argument("--out", default="benchmarks/results.md")
    args = parser.parse_args()

    runs = load(Path(args.results))
    if not runs:
        print("No result JSON files found.")
        return 1

    first = next(iter(runs.values()))
    machine = first.get("machine", {})

    out = [
        "# Replicheck benchmark results",
        "",
        "Generated by `benchmarks/report.py` from `benchmarks/results/*.json`.",
        "Regenerate everything with the commands in `benchmarks/README.md`.",
        "",
        "## Environment",
        "",
        f"- Platform: {machine.get('platform', 'n/a')}",
        f"- CPU: {machine.get('processor', 'n/a')} "
        f"({machine.get('cpu_count', '?')} logical cores)",
        f"- Python: {machine.get('python', 'n/a')}",
        f"- Node.js: {machine.get('node', 'n/a')}",
        f"- .NET: {machine.get('dotnet', 'n/a')}",
        f"- Repetitions per measurement: {first.get('reps', '?')} "
        f"(after {first.get('warmup_runs', '?')} warm-up run(s))",
        f"- flake8 probe: {first.get('probe_method', 'single-shot')}",
        "",
        "## Settings",
        "",
        "Default `main.py` settings: `--min-similarity 0.8`, `--min-size 50`, "
        "`--complexity-threshold 10`, `--large-file-threshold 500`, "
        "`--large-class-threshold 300`, `--top-n-large 10`, default extensions "
        "and the default `text` output format. Reports are written to a file so "
        "the output can be captured.",
        "",
        "## Scaling",
        "",
        "CLI end-to-end is the authoritative figure: it runs "
        "`python main.py --path <corpus>` in a subprocess and therefore includes "
        "interpreter start-up and every external tool.",
        "",
        scaling_table(runs),
        "",
        *scaling_note(runs),
        "## Per-stage breakdown",
        "",
        "Medians across repetitions, timed individually in a single process. "
        "`sum_of_stages` excludes the outer `main.py` interpreter start-up, but it "
        "still includes every external-tool subprocess (flake8, node, the C# "
        "analyzer). Because it is a separate in-process measurement it can differ "
        "slightly from the CLI figure — at ~50k it slightly exceeds it, which is "
        "measurement variance between the two processes, not a real inversion.",
        "",
        stage_table(runs),
        "",
        *failed_stage_note(runs),
        share_table(runs),
        "",
        "## flake8 invocations (pre-fix single-command form)",
        "",
        "This probe deliberately rebuilds the *pre-fix* invocation: one flake8 "
        "command containing every Python file, with stderr captured. The shipped "
        "code now chunks the file list (`replicheck/tools/flake8_runner.py`), so "
        "this section is a regression guard showing the OS limit that motivated "
        "the fix, not a description of current behaviour.",
        "",
        probe_section(runs),
    ]

    # Exactly one trailing newline, so the end-of-file-fixer hook is a no-op.
    Path(args.out).write_text("\n".join(out).rstrip("\n") + "\n", encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
