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
    (what was actually run) over the live file (which may have changed) —
    and, found by a second independent adversarial review (finding M-8):
    when falling back to the live file, only trusts it if its CURRENT hash
    still matches this row's config_hash. Confirmed live: without this
    check, a synthetic row carrying an unrelated config_hash rendered
    fairness values sourced entirely from today's live config content —
    which is what every pre-snapshot row in this repo currently does."""
    if not config_hash:
        return "—", "—"
    snapshot = REPO / "results" / "configs" / f"{config_hash}.yaml"
    if snapshot.exists():
        src = snapshot
    elif config_path and _current_config_hash(config_path) == config_hash:
        src = REPO / config_path
    else:
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
        "**¹ `temp (coding only)`** (2nd adversarial review finding CR-3, a bug in",
        "the H7 fix): the config's declared temperature is what the coding suite",
        "(`hermes chat`, driven by `run_fixture_suite.py`) actually runs at, since",
        "it respects the server's launch flags. `sanity`/`hermes_ops` (driven by",
        "`run_prompt.py`) deliberately hardcode `temperature=0` for EVERY model,",
        "always, regardless of this config value — a longstanding, documented",
        "design choice (see `tasks/SCHEMA.md` \"Temperature is deliberately fixed",
        "at 0\"), not a bug. The H7 fix originally displayed this value as if it",
        "applied everywhere, which was false for 124 of 138 rows at the time.",
        "Note also: `configs/Qwen3.8-27B-Ridge/gguf.yaml` is the only config that",
        "sets `--presence-penalty` (1.5) — a third confound alongside temp/",
        "reasoning-mode when comparing it against `configs/Qwen3.8-27B/gguf.yaml`,",
        "not currently its own column since no other config sets this flag.",
        "",
        "| model | backend | quant | temp (coding only)¹ | reasoning | config | runner | tasks | pass rate | avg tok/s | avg TTFT (s) | hallucinated tools |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for (model, backend, quant, config_hash, runner_sha), group in sorted(
        groups.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2] or "", kv[0][3] or "", kv[0][4] or "")
    ):
        # harness_error rows excluded from n/n_pass (3rd adversarial
        # review, finding CR3-6): a harness crash (npm ci network blip, a
        # missing tools_file, etc.) is not a model failure — counting it in
        # `n` deflated pass_rate for reasons unrelated to the model, and
        # counting it as a "trial" polluted the flaky-task detection below
        # too. Confirmed live: a synthetic 2-pass/1-harness-crash group
        # showed 67% before this fix (should read 100%, 2/2 real trials).
        # Surfaced separately in their own "Harness errors" section instead
        # of being silently dropped.
        scored = [r for r in group if not r.get("harness_error")]
        n = len(scored)
        n_pass = sum(1 for r in scored if r.get("pass"))
        pass_rate = f"{100 * n_pass / n:.0f}%" if n else "n/a (all harness errors)"
        tps_values = [r["tokens_per_second"] for r in scored if r.get("tokens_per_second") is not None]
        avg_tps = f"{mean(tps_values):.1f}" if tps_values else "—"
        # bench_local_proxy.py buffers the whole response into one SSE
        # chunk, so "ttft_seconds" for any proxied config structurally
        # equals total generation time, not real time-to-first-token —
        # showing it in the same column as genuine TTFT numbers silently
        # mixed two different measurements (adversarial review finding
        # H6). Any row explicitly marked unmeasurable blanks the whole
        # group's cell instead.
        if any(r.get("ttft_measurable") is False for r in scored):
            avg_ttft = "n/a (proxied — not real TTFT)"
        else:
            ttft_values = [r["ttft_seconds"] for r in scored if r.get("ttft_seconds") is not None]
            avg_ttft = f"{mean(ttft_values):.2f}" if ttft_values else "—"
        n_hallucinated = sum(1 for r in scored if r.get("grade_output", "").startswith("FAIL: model called tool"))
        config_path = next((r.get("config_path") for r in group if r.get("config_path")), None)
        config_label = _config_label(config_hash, config_path)
        temp, reasoning_mode = _fairness_fields(config_hash, config_path)
        runner_label = runner_sha or "*(predates tracking)*"
        lines.append(
            f"| {model} | {backend} | {quant or '—'} | {temp} | {reasoning_mode} | {config_label} | {runner_label} | {n} | {pass_rate} | {avg_tps} | {avg_ttft} | {n_hallucinated} |"
        )

    lines.append("")
    lines.append("## Flaky tasks (mixed pass/fail under identical conditions)")
    lines.append("")
    lines.append("Any task with the SAME (model, backend, quant, config_hash,")
    lines.append("runner_git_sha, suite, task_id) that comes back with SOME passes and")
    lines.append("some fails is not \"probably fine\" — it's proof this one task's result")
    lines.append("isn't safe to treat as a boolean for this model (adversarial review")
    lines.append("finding C5: temperature=0 measurably does not make MLX/Metal generation")
    lines.append("deterministic across runs). This catches flakiness from an explicit")
    lines.append("`--trials N` run AND from two separate invocations that happen to share")
    lines.append("every one of those fields (found live: a real historical entry below")
    lines.append("came from two independent runs, not --trials, which didn't exist yet).")
    lines.append("Tasks run only once never appear here — that is NOT the same as")
    lines.append("confirmed-stable, just untested for flakiness.")
    lines.append("")
    # quant added to the key (adversarial review finding L-5) — the main
    # table above groups on it too; omitting it here meant two genuinely
    # different quants of the same model/config could be misread as one
    # flaky result instead of two separate, single-quant ones.
    # harness_error rows excluded up front (3rd adversarial review, finding
    # CR3-6): a harness crash mixed in with real passes used to get
    # flagged as MODEL flakiness (a task showing 2/3 when it's really a
    # clean 2/2 plus one unrelated npm-ci network blip) — this section is
    # specifically about non-determinism in the model's own behavior, not
    # infrastructure hiccups, so those rows are dropped before grouping
    # rather than counted as a trial either way.
    task_groups = defaultdict(list)
    for r in rows:
        if r.get("harness_error"):
            continue
        key = (r["model"], r["backend"], r.get("quant"), r.get("config_hash"), r.get("runner_git_sha"), r["suite"], r["task_id"])
        task_groups[key].append(r)
    flaky = {k: v for k, v in task_groups.items() if 0 < sum(1 for r in v if r.get("pass")) < len(v)}
    if not flaky:
        lines.append("None observed (or no task has been run with `--trials` > 1 yet).")
    else:
        lines.append("| model | backend | quant | config | suite | task | pass/trials |")
        lines.append("|---|---|---|---|---|---|---|")
        for (model, backend, quant, config_hash, runner_sha, suite, task_id), group in sorted(flaky.items(), key=lambda kv: tuple(str(x) for x in kv[0])):
            n = len(group)
            n_pass = sum(1 for r in group if r.get("pass"))
            lines.append(f"| {model} | {backend} | {quant or '—'} | {config_hash or '—'} | {suite} | {task_id} | {n_pass}/{n} |")

    lines.append("")
    lines.append("## By suite")
    lines.append("")
    lines.append("| model | backend | config | runner | suite | pass rate |")
    lines.append("|---|---|---|---|---|---|")
    suite_groups = defaultdict(list)
    for r in rows:
        if r.get("harness_error"):  # CR3-6: same exclusion as the main table
            continue
        key = (r["model"], r["backend"], r.get("config_hash"), r.get("runner_git_sha"), r["suite"])
        suite_groups[key].append(r)
    for (model, backend, config_hash, runner_sha, suite), group in sorted(
        suite_groups.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2] or "", kv[0][3] or "", kv[0][4])
    ):
        n = len(group)
        n_pass = sum(1 for r in group if r.get("pass"))
        runner_label = runner_sha or "*(predates tracking)*"
        lines.append(f"| {model} | {backend} | {config_hash or '—'} | {runner_label} | {suite} | {n_pass}/{n} |")

    harness_error_rows = [r for r in rows if r.get("harness_error")]
    lines.append("")
    lines.append("## Harness errors (excluded from every table above)")
    lines.append("")
    if not harness_error_rows:
        lines.append("None observed.")
    else:
        lines.append(
            f"{len(harness_error_rows)} row(s) where the harness itself crashed "
            "(e.g. a network blip during `npm ci`, a malformed task spec) rather "
            "than the model producing a graded result — added 2026-08-21 (3rd "
            "adversarial review, finding CR3-6) so these are visible instead of "
            "silently deflating pass rates or masquerading as model flakiness."
        )
        lines.append("")
        lines.append("| model | backend | suite | task | grade_output (truncated) |")
        lines.append("|---|---|---|---|---|")
        for r in sorted(harness_error_rows, key=lambda r: (r["model"], r["backend"], r["suite"], r["task_id"])):
            snippet = r.get("grade_output", "")[:120].replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {r['model']} | {r['backend']} | {r['suite']} | {r['task_id']} | {snippet} |")

    Path(REPO / "results" / "LEADERBOARD.md").write_text("\n".join(lines) + "\n")
    print(f"Wrote results/LEADERBOARD.md from {len(rows)} rows.")


if __name__ == "__main__":
    main()
