#!/usr/bin/env python3
"""Generates results/score_chart.png: a horizontal bar chart of the "Best
overall" composite score per model, for embedding in results/LEADERBOARD.md
and results/SUMMARY.md. Reuses build_leaderboard.py's own
compute_group_stats()/rank_groups() so the chart and the markdown table can
never drift apart on what "the score" means (2026-08-27, user request).

Run standalone:
    uv run --locked python runner/plot_leaderboard.py
    uv run --locked python runner/plot_leaderboard.py --top 10
    uv run --locked python runner/plot_leaderboard.py --models "Ornith,Qwen3.6"

Normally invoked automatically by run_bench.py right after it regenerates
results/LEADERBOARD.md, so the chart stays current after every benchmark
pass without a manual step.
"""
import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless — no display available in this harness
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_leaderboard import compute_group_stats, _row_inference_engine  # noqa: E402

REPO = Path(__file__).resolve().parent.parent

# Colorblind-safe status pair (not a categorical palette — every bar already
# carries its own model-identity label via the y-axis, so color here encodes
# the ONE thing that isn't already visible per-bar: usefulness-gate status).
# Blue/orange rather than red/green specifically to stay legible for the
# most common (red-green) form of color vision deficiency.
COLOR_GATE_PASS = "#1f6fb2"
COLOR_GATE_FAIL = "#c8792a"
COLOR_TEXT = "#1a1a1a"
COLOR_GRID = "#d9d9d9"


def _group_label(key):
    model, inference_engine, quant, _config_hash, _runner_sha = key
    label = f"{model} ({inference_engine}"
    if quant:
        label += f", {quant}"
    label += ")"
    return label


def build_ranked_rows(log_path=None):
    """Returns a list of dicts, one per (model, engine, quant) group that
    made it into build_leaderboard.py's "Best overall" table (i.e. passed
    its eligibility check — all three axes present). Each dict has: label,
    gate_pass, score, coding_pass_rate, n_coding, avg_tps_val. Sorted
    descending the same way the markdown table is (gate status first, then
    score) -- imported straight from build_leaderboard so this can never
    silently diverge from the table."""
    from collections import defaultdict
    from build_leaderboard import rank_groups

    log_path = log_path or (REPO / "results" / "log.jsonl")
    rows = []
    for line in Path(log_path).read_text().splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    if not rows:
        return []

    groups = defaultdict(list)
    for r in rows:
        key = (r["model"], _row_inference_engine(r), r.get("quant"), r.get("config_hash"), r.get("runner_git_sha"))
        groups[key].append(r)

    group_stats = compute_group_stats(groups)
    ranked = rank_groups(group_stats)

    out = []
    for gate_pass, score, gs in sorted(ranked, key=lambda t: (t[0], t[1]), reverse=True):
        out.append({
            "label": _group_label(gs["key"]),
            "model": gs["key"][0],
            "gate_pass": gate_pass,
            "score": score,
            "coding_pass_rate": gs["coding_pass_rate"],
            "n_coding": gs["n_coding"],
            "avg_tps_val": gs["avg_tps_val"],
        })
    return out


def render_chart(entries, output_path, title="Best overall — composite score by model"):
    if not entries:
        raise SystemExit("No eligible groups to chart (need a completed run: sanity + hermes_ops + coding).")

    # Bottom-to-top drawing order for matplotlib barh, but we want rank #1
    # at the TOP of the image — reverse the already-sorted (best-first) list.
    entries = list(reversed(entries))
    labels = [e["label"] for e in entries]
    scores = [e["score"] for e in entries]
    colors = [COLOR_GATE_PASS if e["gate_pass"] else COLOR_GATE_FAIL for e in entries]

    fig_height = max(2.5, 0.42 * len(entries) + 1.2)
    fig, ax = plt.subplots(figsize=(11, fig_height), dpi=150)
    fig.patch.set_facecolor("white")  # explicit white bg: legible in both
    ax.set_facecolor("white")          # GitHub's light and dark reading modes

    bars = ax.barh(labels, scores, color=colors, height=0.62, edgecolor="none")

    for bar, e in zip(bars, entries):
        width = bar.get_width()
        if e["gate_pass"]:
            label = f"{width:.3f}"
        else:
            label = "gate failed"
        ax.text(
            width + 0.012, bar.get_y() + bar.get_height() / 2, label,
            va="center", ha="left", fontsize=8.5, color=COLOR_TEXT,
        )

    ax.set_xlim(0, 1.0)
    ax.set_xlabel("Composite score\n(pass 45% + speed 25% + time 20% + turns 10%, gate-passers only)", fontsize=9, color=COLOR_TEXT)
    ax.set_title(title, fontsize=12, color=COLOR_TEXT, pad=14, loc="left", fontweight="bold")
    ax.tick_params(axis="y", labelsize=8.5, colors=COLOR_TEXT)
    ax.tick_params(axis="x", labelsize=8, colors=COLOR_TEXT)
    ax.grid(axis="x", color=COLOR_GRID, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(COLOR_GRID)

    legend_handles = [
        plt.Rectangle((0, 0), 1, 1, color=COLOR_GATE_PASS, label="Usefulness gate: PASS (hermes_ops ≥ 50%)"),
        plt.Rectangle((0, 0), 1, 1, color=COLOR_GATE_FAIL, label="Usefulness gate: FAIL (ranked below all gate-passers)"),
    ]
    ax.legend(handles=legend_handles, loc="lower right", fontsize=8, frameon=False)

    fig.savefig(output_path, facecolor="white", bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", type=str, default=None,
                         help="Comma-separated case-insensitive substrings — only chart groups whose model name contains one of these.")
    parser.add_argument("--top", type=int, default=None,
                         help="Only chart the top N by score (applied after --models filtering).")
    parser.add_argument("--output", type=str, default=str(REPO / "results" / "score_chart.png"),
                         help="Output image path (default: results/score_chart.png).")
    parser.add_argument("--log", type=str, default=None,
                         help="Path to log.jsonl (default: results/log.jsonl).")
    args = parser.parse_args()

    entries = build_ranked_rows(Path(args.log) if args.log else None)

    if args.models:
        needles = [m.strip().lower() for m in args.models.split(",") if m.strip()]
        entries = [e for e in entries if any(n in e["model"].lower() for n in needles)]
        if not entries:
            raise SystemExit(f"No groups matched --models {args.models!r}.")

    if args.top:
        entries = entries[: args.top]

    render_chart(entries, args.output)
    print(f"Wrote {args.output} ({len(entries)} groups).")


if __name__ == "__main__":
    main()
