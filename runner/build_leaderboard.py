#!/usr/bin/env python3
"""Regenerates results/LEADERBOARD.md from results/log.jsonl. Never hand-edit
the leaderboard — edit the log (or just append new runs) and regenerate."""
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

REPO = Path(__file__).resolve().parent.parent


def _current_config_hash(config_path):
    """The live file's hash right now — compared against a row's stored
    config_hash to tell whether the config has been edited since that row
    was produced (adversarial-review finding C3/C4: every config gets
    edited after being run, so an un-flagged old row silently links to
    settings that no longer exist)."""
    if not config_path:
        return None
    p = REPO / config_path
    if not p.exists():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12]


def _config_label(config_hash, config_path):
    if not config_hash:
        return "—"
    snapshot = REPO / "results" / "configs" / f"{config_hash}.yaml"
    if snapshot.exists():
        link = f"[{config_hash}](configs/{config_hash}.yaml)"
    elif config_path:
        # Predates the config-snapshot fix (2026-08-21) — no verbatim copy
        # was saved, so this links to the LIVE file, which may since have
        # changed. Flagged rather than silently presented as trustworthy.
        link = f"[{config_hash}]({config_path}) (unsnapshotted, predates 2026-08-21 fix — may not match)"
    else:
        link = config_hash
    current = _current_config_hash(config_path)
    if current and current != config_hash:
        link += " — *config since changed*"
    return link


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

    # Grouped by (model, backend, quant, config_hash, runner_git_sha) — NOT
    # just (model, backend, quant, config_hash). Two runs against the same
    # model+backend+config can still differ in RESULT-MEANING if the
    # runner/grading code itself changed between them (e.g. the max_turns=6
    # bug, or the kiem_mini-feature grading strengthened 2026-08-21) — those
    # must never be silently averaged together just because the config
    # didn't change. Rows logged before this field existed carry
    # runner_git_sha=None, which naturally keeps them in their own group
    # rather than merging with anything after this fix.
    groups = defaultdict(list)
    for r in rows:
        key = (r["model"], r["backend"], r.get("quant"), r.get("config_hash"), r.get("runner_git_sha"))
        groups[key].append(r)

    lines = [
        "# Leaderboard",
        "",
        "Regenerated from `log.jsonl` by `runner/build_leaderboard.py` — do not",
        "hand-edit rows below, edit the log and regenerate instead.",
        "",
        "Grouped by (model, backend, quant, config_hash, runner_git_sha) — never",
        "averaged across different configs OR different harness/grading code",
        "versions, even for the same model+backend, since either would mix",
        "genuinely different experiments (e.g. before/after a settings fix, or",
        "before/after a grading-bug fix). `config_hash` links to a verbatim",
        "snapshot of the exact config content used (`results/configs/`), not the",
        "live (possibly since-edited) config file — see `config_hash` values",
        "flagged \"config since changed\" for rows predating that snapshot.",
        "`runner_git_sha` rows marked `+dirty` were graded by uncommitted code.",
        "",
        "| model | backend | quant | config | runner | tasks | pass rate | avg tok/s | avg TTFT (s) | hallucinated tools |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for (model, backend, quant, config_hash, runner_sha), group in sorted(
        groups.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2] or "", kv[0][3] or "", kv[0][4] or "")
    ):
        n = len(group)
        n_pass = sum(1 for r in group if r.get("pass"))
        pass_rate = f"{100 * n_pass / n:.0f}%"
        tps_values = [r["tokens_per_second"] for r in group if r.get("tokens_per_second") is not None]
        avg_tps = f"{mean(tps_values):.1f}" if tps_values else "—"
        ttft_values = [r["ttft_seconds"] for r in group if r.get("ttft_seconds") is not None]
        avg_ttft = f"{mean(ttft_values):.2f}" if ttft_values else "—"
        n_hallucinated = sum(1 for r in group if r.get("grade_output", "").startswith("FAIL: model called tool"))
        config_path = next((r.get("config_path") for r in group if r.get("config_path")), None)
        config_label = _config_label(config_hash, config_path)
        runner_label = runner_sha or "*(predates tracking)*"
        lines.append(
            f"| {model} | {backend} | {quant or '—'} | {config_label} | {runner_label} | {n} | {pass_rate} | {avg_tps} | {avg_ttft} | {n_hallucinated} |"
        )

    lines.append("")
    lines.append("## By suite")
    lines.append("")
    lines.append("| model | backend | config | runner | suite | pass rate |")
    lines.append("|---|---|---|---|---|---|")
    suite_groups = defaultdict(list)
    for r in rows:
        key = (r["model"], r["backend"], r.get("config_hash"), r.get("runner_git_sha"), r["suite"])
        suite_groups[key].append(r)
    for (model, backend, config_hash, runner_sha, suite), group in sorted(
        suite_groups.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2] or "", kv[0][3] or "", kv[0][4])
    ):
        n = len(group)
        n_pass = sum(1 for r in group if r.get("pass"))
        runner_label = runner_sha or "*(predates tracking)*"
        lines.append(f"| {model} | {backend} | {config_hash or '—'} | {runner_label} | {suite} | {n_pass}/{n} |")

    Path(REPO / "results" / "LEADERBOARD.md").write_text("\n".join(lines) + "\n")
    print(f"Wrote results/LEADERBOARD.md from {len(rows)} rows.")


if __name__ == "__main__":
    main()
