#!/usr/bin/env python3
"""Regenerates results/LEADERBOARD.md from results/log.jsonl. Never hand-edit
the leaderboard — edit the log (or just append new runs) and regenerate."""
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

REPO = Path(__file__).resolve().parent.parent


def main():
    log_path = REPO / "results" / "log.jsonl"
    rows = []
    for line in log_path.read_text().splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))

    if not rows:
        Path(REPO / "results" / "LEADERBOARD.md").write_text(
            "# Leaderboard\n\nNo runs yet.\n"
        )
        print("No rows in log.jsonl — wrote empty leaderboard.")
        return

    # group by (model, backend, quant)
    groups = defaultdict(list)
    for r in rows:
        key = (r["model"], r["backend"], r.get("quant"))
        groups[key].append(r)

    lines = [
        "# Leaderboard",
        "",
        "Regenerated from `log.jsonl` by `runner/build_leaderboard.py` — do not",
        "hand-edit rows below, edit the log and regenerate instead.",
        "",
        "| model | backend | quant | tasks | pass rate | avg tok/s | avg TTFT (s) | hallucinated tools |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for (model, backend, quant), group in sorted(groups.items()):
        n = len(group)
        n_pass = sum(1 for r in group if r.get("pass"))
        pass_rate = f"{100 * n_pass / n:.0f}%"
        tps_values = [r["tokens_per_second"] for r in group if r.get("tokens_per_second") is not None]
        avg_tps = f"{mean(tps_values):.1f}" if tps_values else "—"
        ttft_values = [r["ttft_seconds"] for r in group if r.get("ttft_seconds") is not None]
        avg_ttft = f"{mean(ttft_values):.2f}" if ttft_values else "—"
        n_hallucinated = sum(1 for r in group if r.get("grade_output", "").startswith("FAIL: model called tool"))
        lines.append(
            f"| {model} | {backend} | {quant or '—'} | {n} | {pass_rate} | {avg_tps} | {avg_ttft} | {n_hallucinated} |"
        )

    lines.append("")
    lines.append("## By suite")
    lines.append("")
    lines.append("| model | backend | suite | pass rate |")
    lines.append("|---|---|---|---|")
    suite_groups = defaultdict(list)
    for r in rows:
        key = (r["model"], r["backend"], r["suite"])
        suite_groups[key].append(r)
    for (model, backend, suite), group in sorted(suite_groups.items()):
        n = len(group)
        n_pass = sum(1 for r in group if r.get("pass"))
        lines.append(f"| {model} | {backend} | {suite} | {n_pass}/{n} |")

    Path(REPO / "results" / "LEADERBOARD.md").write_text("\n".join(lines) + "\n")
    print(f"Wrote results/LEADERBOARD.md from {len(rows)} rows.")


if __name__ == "__main__":
    main()
