#!/usr/bin/env python3
"""Regenerates results/LEADERBOARD.md from results/log.jsonl. Never hand-edit
the leaderboard — edit the log (or just append new runs) and regenerate."""
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

import yaml

REPO = Path(__file__).resolve().parent.parent


def _fairness_fields(config_hash, config_path):
    """temperature/reasoning_mode as declared in the config that produced
    this group — surfaced as their own columns so two configs that differ
    in these (not just quant) can't be silently read as an apples-to-apples
    comparison (adversarial review finding H7). Prefers the exact snapshot
    (what was actually run) over the live file (which may have changed)."""
    if not config_hash:
        return "—", "—"
    snapshot = REPO / "results" / "configs" / f"{config_hash}.yaml"
    src = snapshot if snapshot.exists() else (REPO / config_path if config_path else None)
    if not src or not src.exists():
        return "?", "?"
    try:
        cfg = yaml.safe_load(src.read_text()) or {}
    except yaml.YAMLError:
        return "?", "?"
    temp = cfg.get("temperature", "?")
    mode = cfg.get("reasoning_mode", "?")
    return str(temp), str(mode)


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

    stale_rows = [r for r in rows if not r.get("runner_git_sha")]
    lines = [
        "# Leaderboard",
        "",
        "Regenerated from `log.jsonl` by `runner/build_leaderboard.py` — do not",
        "hand-edit rows below, edit the log and regenerate instead.",
        "",
    ]
    if stale_rows:
        lines += [
            f"> **⚠ {len(stale_rows)}/{len(rows)} rows below predate the 2026-08-21",
            "> adversarial-review grading fixes** (no `runner_git_sha` at all — that",
            "> field didn't exist yet when they were produced). A second independent",
            "> review found the first review's own fixes still left real bugs (see",
            "> AGENTS.md), so **do not treat any pre-2026-08-21 PASS/FAIL as final",
            "> signal** until re-run under current grading. Known-affected checks,",
            "> confirmed to have changed real outcomes:",
            "> - `kiem_mini-feature` (all rows before the C1 fix): graded only the",
            "> library function, never the CLI wiring — one logged PASS is known to",
            "> have a compiler warning proving the CLI half was never implemented.",
            "> - `hermes_ops-error-recovery` (all rows before this session's fixes,",
            "> including a since-fixed regression where the word \"error\" itself",
            "> became an auto-fail): rewarded fabricated file contents as long as",
            "> an unrelated word like \"error\" appeared anywhere in the answer.",
            "> - `hermes_ops-selection` (all rows before the L4 fix): `response_contains:",
            "> \"18\"` matched \"18\" as a substring of any number, including \"2018\".",
            "> - `hermes_ops-chaining` (all rows before the L5 fix): only checked the",
            "> written number appeared somewhere in the file, not that it was the",
            "> ONLY content, despite the prompt saying \"just that number\".",
            "> - `sanity-tool` (all rows): graded with multiset argument matching,",
            "> not exact key/value matching — could pass wrong argument names.",
            "> Re-running is the only way to get current, trustworthy rows for these",
            "> tasks; regenerating this file alone does not re-grade anything.",
            "",
        ]
    lines += [
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
        "**`avg tok/s` caveat** (adversarial review finding H6, not fully closed):",
        "this is `completion_tokens / wall_seconds` across the ENTIRE multi-turn",
        "loop, including every prefill of the suite's system prompt — it's a",
        "prefill-dominated-workload throughput number, not a pure decode rate, and",
        "it's averaged across `sanity` (tiny prompt) and `hermes_ops` (large,",
        "repeated system prompt) rows in one cell. Treat it as a rough signal,",
        "not a precise generation-speed comparison; a real prefill/decode split",
        "is a follow-up, not yet implemented. `avg TTFT` is blanked instead of",
        "silently mislabeled for proxied configs (see below), but is still a",
        "single combined average across suites where it IS real.",
        "",
        "| model | backend | quant | temp | reasoning | config | runner | tasks | pass rate | avg tok/s | avg TTFT (s) | hallucinated tools |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for (model, backend, quant, config_hash, runner_sha), group in sorted(
        groups.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2] or "", kv[0][3] or "", kv[0][4] or "")
    ):
        n = len(group)
        n_pass = sum(1 for r in group if r.get("pass"))
        pass_rate = f"{100 * n_pass / n:.0f}%"
        tps_values = [r["tokens_per_second"] for r in group if r.get("tokens_per_second") is not None]
        avg_tps = f"{mean(tps_values):.1f}" if tps_values else "—"
        # bench_local_proxy.py buffers the whole response into one SSE
        # chunk, so "ttft_seconds" for any proxied config structurally
        # equals total generation time, not real time-to-first-token —
        # showing it in the same column as genuine TTFT numbers silently
        # mixed two different measurements (adversarial review finding
        # H6). Any row explicitly marked unmeasurable blanks the whole
        # group's cell instead.
        if any(r.get("ttft_measurable") is False for r in group):
            avg_ttft = "n/a (proxied — not real TTFT)"
        else:
            ttft_values = [r["ttft_seconds"] for r in group if r.get("ttft_seconds") is not None]
            avg_ttft = f"{mean(ttft_values):.2f}" if ttft_values else "—"
        n_hallucinated = sum(1 for r in group if r.get("grade_output", "").startswith("FAIL: model called tool"))
        config_path = next((r.get("config_path") for r in group if r.get("config_path")), None)
        config_label = _config_label(config_hash, config_path)
        temp, reasoning_mode = _fairness_fields(config_hash, config_path)
        runner_label = runner_sha or "*(predates tracking)*"
        lines.append(
            f"| {model} | {backend} | {quant or '—'} | {temp} | {reasoning_mode} | {config_label} | {runner_label} | {n} | {pass_rate} | {avg_tps} | {avg_ttft} | {n_hallucinated} |"
        )

    lines.append("")
    lines.append("## Flaky tasks (mixed pass/fail across trials)")
    lines.append("")
    lines.append("A task run more than once (`--trials N`) under the identical")
    lines.append("model/config/runner that comes back with SOME passes and some fails is")
    lines.append("not \"probably fine\" — it's proof this one task's result isn't safe to")
    lines.append("treat as a boolean for this model (adversarial review finding C5:")
    lines.append("temperature=0 measurably does not make MLX/Metal generation")
    lines.append("deterministic across runs). Tasks run only once never appear here —")
    lines.append("that is NOT the same as confirmed-stable, just untested for flakiness.")
    lines.append("")
    task_groups = defaultdict(list)
    for r in rows:
        key = (r["model"], r["backend"], r.get("config_hash"), r.get("runner_git_sha"), r["suite"], r["task_id"])
        task_groups[key].append(r)
    flaky = {k: v for k, v in task_groups.items() if 0 < sum(1 for r in v if r.get("pass")) < len(v)}
    if not flaky:
        lines.append("None observed (or no task has been run with `--trials` > 1 yet).")
    else:
        lines.append("| model | backend | config | suite | task | pass/trials |")
        lines.append("|---|---|---|---|---|---|")
        for (model, backend, config_hash, runner_sha, suite, task_id), group in sorted(flaky.items()):
            n = len(group)
            n_pass = sum(1 for r in group if r.get("pass"))
            lines.append(f"| {model} | {backend} | {config_hash or '—'} | {suite} | {task_id} | {n_pass}/{n} |")

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
