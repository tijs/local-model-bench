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

    # group by (model, backend, quant, config_hash) — NOT just (model, backend,
    # quant): two runs against the same model+backend under different configs
    # (e.g. before/after fixing sampling settings) are different experiments
    # and must never be silently averaged together.
    groups = defaultdict(list)
    for r in rows:
        key = (r["model"], r["backend"], r.get("quant"), r.get("config_hash"))
        groups[key].append(r)

    lines = [
        "# Leaderboard",
        "",
        "Regenerated from `log.jsonl` by `runner/build_leaderboard.py` — do not",
        "hand-edit rows below, edit the log and regenerate instead.",
        "",
        "Grouped by (model, backend, quant, config_hash) — never averaged across",
        "different configs, even for the same model+backend, since that would mix",
        "genuinely different experiments (e.g. before/after a settings fix).",
        "",
        "| model | backend | quant | config | tasks | pass rate | avg tok/s | avg TTFT (s) | hallucinated tools |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for (model, backend, quant, config_hash), group in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2] or "", kv[0][3] or "")):
        n = len(group)
        n_pass = sum(1 for r in group if r.get("pass"))
        pass_rate = f"{100 * n_pass / n:.0f}%"
        tps_values = [r["tokens_per_second"] for r in group if r.get("tokens_per_second") is not None]
        avg_tps = f"{mean(tps_values):.1f}" if tps_values else "—"
        ttft_values = [r["ttft_seconds"] for r in group if r.get("ttft_seconds") is not None]
        avg_ttft = f"{mean(ttft_values):.2f}" if ttft_values else "—"
        n_hallucinated = sum(1 for r in group if r.get("grade_output", "").startswith("FAIL: model called tool"))
        config_path = next((r.get("config_path") for r in group if r.get("config_path")), None)
        config_label = f"[{config_hash}]({config_path})" if config_hash else "—"
        lines.append(
            f"| {model} | {backend} | {quant or '—'} | {config_label} | {n} | {pass_rate} | {avg_tps} | {avg_ttft} | {n_hallucinated} |"
        )

    lines.append("")
    lines.append("## By suite")
    lines.append("")
    lines.append("| model | backend | config | suite | pass rate |")
    lines.append("|---|---|---|---|---|")
    suite_groups = defaultdict(list)
    for r in rows:
        key = (r["model"], r["backend"], r.get("config_hash"), r["suite"])
        suite_groups[key].append(r)
    for (model, backend, config_hash, suite), group in sorted(suite_groups.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2] or "", kv[0][3])):
        n = len(group)
        n_pass = sum(1 for r in group if r.get("pass"))
        lines.append(f"| {model} | {backend} | {config_hash or '—'} | {suite} | {n_pass}/{n} |")

    Path(REPO / "results" / "LEADERBOARD.md").write_text("\n".join(lines) + "\n")
    print(f"Wrote results/LEADERBOARD.md from {len(rows)} rows.")


if __name__ == "__main__":
    main()
