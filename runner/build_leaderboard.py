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

# `sanity` is explicitly a fail-fast GATE (run_bench.py stops entirely if
# sanity-basic fails), not a quality signal to average alongside real
# tool-use/coding results — folding it into one blended "pass rate" can
# only compress the differences between models that already cleared it,
# since it sits at or near ceiling for nearly everything (26/26 and 25/26
# in the committed data as of the methodology review, finding F3).
# CODING_SUITES names every `runner: fixture` suite explicitly rather than
# inferring "not sanity, not hermes_ops" — a future prompt-runner suite
# added alongside hermes_ops should default to being treated like it, not
# silently miscounted as coding.
CODING_SUITES = {"kiem_mini", "hearth_mini", "kipclip_mini"}


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


def _experiment_fields(config_hash, config_path):
    """Inference-engine factors that must remain visible for oMLX comparisons.

    The config hash already prevents accidental averaging, but a reader should
    not need to open every snapshot to discover that two rows differ by cache,
    MTP, or mixed-precision quant family. `inference_engine` itself (the inference
    engine identity — llama.cpp/vllm-mlx/omlx, or a fork variant like
    llama.cpp-dflash2) is NOT returned here — it's the row's own primary
    identity column, sourced directly from the log row (see _row_inference_engine()),
    not re-derived from the config snapshot.
    """
    if not config_hash:
        return "—", "—", "—"
    snapshot = REPO / "results" / "configs" / f"{config_hash}.yaml"
    if snapshot.exists():
        src = snapshot
    elif config_path and _current_config_hash(config_path) == config_hash:
        src = REPO / config_path
    else:
        return "?", "?", "?"
    try:
        cfg = yaml.safe_load(src.read_text()) or {}
    except (OSError, yaml.YAMLError):
        return "?", "?", "?"
    return tuple(str(cfg.get(name, "—")) for name in (
        "quant_family", "cache_mode", "mtp_mode"
    ))


def _row_inference_engine(r):
    """The inference-engine identity for one log row: `inference_engine`
    going forward (llama.cpp, vllm-mlx, omlx, or a fork variant like
    llama.cpp-dflash2/llama.cpp-dspark). Two renames happened in quick
    succession 2026-08-23 (backend -> framework -> inference_engine, since
    "framework" was itself judged not quite the right final name either),
    and results/log.jsonl is an append-only historical record that is
    NEVER rewritten in place — so a real row can carry any of the three
    field names depending on when it was logged. All three coexist here,
    preferring the newest."""
    return r.get("inference_engine") or r.get("framework") or r.get("backend") or "?"


def _blocked_configs():
    """Configs marked `orchestration.viable: blocked` (a model+inference-engine
    combination ruled out as non-viable on this hardware, e.g. after a live
    pilot showed it too slow to ever finish a task). Scanned directly from
    `configs/**/*.yaml` rather than derived from log.jsonl rows, because a
    config can be blocked BEFORE it was ever run (e.g. mid-pilot, once one
    sibling engine's result was bad enough to stop testing the model's other
    engines/quants too) — such a config has no log row at all, and would
    silently vanish from every other section in this file with no trace of
    why."""
    found = []
    for path in sorted((REPO / "configs").glob("**/*.yaml")):
        try:
            cfg = yaml.safe_load(path.read_text()) or {}
        except yaml.YAMLError:
            continue
        orch = cfg.get("orchestration") or {}
        if orch.get("viable") != "blocked":
            continue
        found.append({
            "model": cfg.get("model", "—"),
            "inference_engine": cfg.get("inference_engine", "—"),
            "config_path": str(path.relative_to(REPO)),
            "blocked_reason": orch.get("blocked_reason", "(no blocked_reason set)"),
        })
    return found


def _speed_gated_configs():
    """Configs that run_bench.py itself stopped early because that
    config's own hermes_ops run averaged under
    bench_common.MIN_HERMES_OPS_TOKENS_PER_SECOND (4 tok/s as of
    2026-08-23 — see that constant's own comment for why this was lowered
    from an initial 10 tok/s) across
    every hermes_ops task — see run_bench.py's speed-gate block, right
    after the hermes_ops suite call. Read from results/speed_gate.jsonl, a
    dedicated append-only log kept separate from log.jsonl (whose task/
    suite-keyed schema every grouping/flakiness check above assumes) and
    separate from the config YAML files (which stay hand-authored, not
    rewritten by this automated check — unlike `orchestration.viable:
    blocked`, which is a human judgment call recorded in the config
    itself)."""
    path = REPO / "results" / "speed_gate.jsonl"
    if not path.exists():
        return []
    found = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            found.append(json.loads(line))
    return found


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

    # Grouped by (model, inference_engine, quant, config_hash, runner_git_sha) — NOT
    # just (model, inference_engine, quant, config_hash). Two runs against the same
    # model+inference_engine+config can still differ in RESULT-MEANING if the
    # runner/grading code itself changed between them (e.g. the max_turns=6
    # bug, or the kiem_mini-feature grading strengthened 2026-08-21) — those
    # must never be silently averaged together just because the config
    # didn't change. Rows logged before this field existed carry
    # runner_git_sha=None, which naturally keeps them in their own group
    # rather than merging with anything after this fix. `inference_engine` (the
    # inference engine: llama.cpp/vllm-mlx/omlx, or a fork variant like
    # llama.cpp-dflash2) replaced the older, coarser `backend` field
    # (mlx/gguf/omlx/api) 2026-08-23 — see _row_inference_engine()'s own comment;
    # rows logged before that rename still carry `backend` only.
    groups = defaultdict(list)
    for r in rows:
        key = (r["model"], _row_inference_engine(r), r.get("quant"), r.get("config_hash"), r.get("runner_git_sha"))
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
        "Grouped by (model, inference_engine, quant, config_hash, runner_git_sha) — never",
        "averaged across different configs OR different harness/grading code",
        "versions, even for the same model+inference_engine, since either would mix",
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
        "**² `slow passes`** (methodology review, finding F5): count of PASS rows",
        "that took longer than `bench_common.py`'s `INTERACTIVE_BUDGET_SECONDS`",
        "(300s) to complete — still correct, and still counted in `pass rate`",
        "above, but not a practically usable result in a real interactive agentic",
        "session. Deliberately separate from `timeout_seconds`/`--timeout`, which",
        "exist to give a slow-but-alive model a fair chance to finish generating",
        "without being cut off mid-response — a task can legitimately take up to",
        "that much generous budget and still show up here if it's well past what",
        "an interactive session would tolerate. 300s is a judgment call (see that",
        "constant's own comment), not a hard spec.",
        "",
        "**³ `avg coding turns` / `coding tool errors`** (methodology review, finding",
        "F6): the coding suite previously logged zero performance data from the",
        "actual target workload — no tokens, no turn count, no tool-call data,",
        "ever, unlike the two synthetic prompt suites. Pulled from hermes's own",
        "SQLite session store (`hermes sessions export`) after each coding-suite",
        "task; blank/0 for sanity/hermes_ops-only groups, which call the raw API",
        "directly and have no hermes session to pull from. `coding tool errors` is",
        "a best-effort heuristic (documented in",
        "`run_fixture_suite.py`'s `extract_hermes_session_stats()`), not a fully",
        "generic classifier — confirmed live that a tool's own `exit_code` can",
        "read 0 even when its output clearly shows a build failure, so this also",
        "scans for the same compiler-error markers `grade_mutation.sh` already",
        "looks for as a fallback.",
        "",
        "**⁴ `sanity gate` / `pass rate`** (methodology review, finding F3): `sanity`",
        "is a fail-fast GATE — run_bench.py stops the whole config entirely if",
        "sanity-basic fails — not a quality signal to blend in alongside real",
        "tool-use/coding results. It's shown here as its own `passed/total` column",
        "instead. `pass rate` now covers only `hermes_ops` + coding-suite rows;",
        "folding sanity in used to compress real differences between models,",
        "since it sits at or near ceiling for nearly everything.",
        "",
        "**⁵ `hallucinated tools`** (methodology review, finding F14): this only",
        "fires in the two synthetic prompt suites (sanity/hermes_ops), whose fixed",
        "tool manifest makes \"called a tool that doesn't exist in it\" a clean,",
        "checkable signal. The coding suite has no equivalent check — a hermes",
        "chat session's real tool manifest isn't fixed/known the way hermes_ops's",
        "41-tool mock manifest is, so this reads 0 for every coding-suite row",
        "regardless of what actually happened. Read this column as \"not observed",
        "on the two synthetic suites,\" not \"never hallucinated a tool\" — the",
        "coding-suite session data added for finding F6 (avg coding turns/tool",
        "errors) doesn't cover this specific question either.",
        "",
        "| model | engine | quant | temp (coding only)¹ | reasoning | sanity gate⁴ | config | runner | tasks | pass rate⁴ | slow passes² | avg tok/s | avg TTFT (s) | hallucinated tools⁵ | avg coding turns³ | coding tool errors³ | peak RSS (GB) | quant family | cache | MTP |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    # Two passes, not one (methodology review, finding F3): the composite
    # "Best overall" ranking below needs the raw numeric avg_tps for every
    # group BEFORE it can normalize any one group's speed against the
    # fastest group seen this run — that global max isn't known until all
    # groups have been visited once. group_stats carries both the raw
    # numbers (for scoring) and the pre-formatted display strings (for the
    # main table), computed once, so the two never drift apart.
    group_stats = []
    for (model, inference_engine, quant, config_hash, runner_sha), group in sorted(
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
        # sanity is a fail-fast GATE (see CODING_SUITES comment above), not
        # a quality signal — excluded from pass_rate and shown as its own
        # column instead (methodology review, finding F3). Confirmed live
        # against the committed data: sanity-basic and sanity-tool sit at
        # 26/26 and 25/26, so blending them in only compresses the real
        # differences between models on hermes_ops/coding.
        sanity_scored = [r for r in scored if r["suite"] == "sanity"]
        non_sanity_scored = [r for r in scored if r["suite"] != "sanity"]
        sanity_gate = (
            f"{sum(1 for r in sanity_scored if r.get('pass'))}/{len(sanity_scored)}"
            if sanity_scored else "—"
        )
        n = len(non_sanity_scored)
        n_pass = sum(1 for r in non_sanity_scored if r.get("pass"))
        pass_rate = f"{100 * n_pass / n:.0f}%" if n else "n/a (all harness errors)"
        tps_values = [r["tokens_per_second"] for r in scored if r.get("tokens_per_second") is not None]
        avg_tps_val = mean(tps_values) if tps_values else None
        avg_tps = f"{avg_tps_val:.1f}" if avg_tps_val is not None else "—"
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
        # Pulled from hermes's own session store, coding-suite rows only —
        # sanity/hermes_ops rows never populate these (they call the raw
        # API directly, no hermes session involved), so this is silently
        # 0 for prompt-suite-only groups rather than misleadingly blank
        # (methodology review, finding F6: the coding suite previously
        # had zero performance data of any kind).
        turn_values = [r["hermes_turns"] for r in scored if r.get("hermes_turns") is not None]
        avg_turns = f"{mean(turn_values):.1f}" if turn_values else "—"
        n_tool_errors = sum(r["hermes_tool_errors"] for r in scored if r.get("hermes_tool_errors") is not None)
        # A PASS that took longer than INTERACTIVE_BUDGET_SECONDS isn't a
        # failure (it's still counted in pass_rate above), but it's not a
        # practically usable result in a real interactive session either
        # — surfaced as its own count rather than silently blending into
        # the same pass_rate number as a 5-second pass (methodology
        # review, finding F5). None (row has no wall_seconds at all, e.g.
        # a harness crash) is not counted as slow.
        n_slow_pass = sum(1 for r in scored if r.get("pass") and r.get("within_budget") is False)
        # Peak, not average, across the group (methodology review, finding
        # F7) — the 32GB unified-memory ceiling is a hard capacity limit,
        # so the worst observed footprint is the number that actually
        # matters for "does this fit," not a smoothed-out mean that could
        # hide a run that came close to swapping.
        rss_values = [r["peak_rss_gb"] for r in scored if r.get("peak_rss_gb") is not None]
        peak_rss = f"{max(rss_values):.1f}" if rss_values else "—"
        config_path = next((r.get("config_path") for r in group if r.get("config_path")), None)
        config_label = _config_label(config_hash, config_path)
        temp, reasoning_mode = _fairness_fields(config_hash, config_path)
        quant_family, cache_mode, mtp_mode = _experiment_fields(config_hash, config_path)
        runner_label = runner_sha or "*(predates tracking)*"

        # Per-axis pass rates for the composite score below — kept as raw
        # fractions (0.0-1.0) here, not the display-formatted `pass_rate`
        # string above, and computed separately per suite category rather
        # than reused from the blended one, since "coding" and
        # "hermes_ops" need to combine at DIFFERENT weights, not get
        # averaged together first and lose that distinction.
        coding_scored = [r for r in non_sanity_scored if r["suite"] in CODING_SUITES]
        hermes_ops_scored = [r for r in non_sanity_scored if r["suite"] not in CODING_SUITES]
        coding_pass_rate = (
            sum(1 for r in coding_scored if r.get("pass")) / len(coding_scored)
            if coding_scored else None
        )
        hermes_ops_pass_rate = (
            sum(1 for r in hermes_ops_scored if r.get("pass")) / len(hermes_ops_scored)
            if hermes_ops_scored else None
        )

        group_stats.append({
            "key": (model, inference_engine, quant, config_hash, runner_sha),
            "line": (
                f"| {model} | {inference_engine} | {quant or '—'} | {temp} | {reasoning_mode} | "
                f"{sanity_gate} | {config_label} | {runner_label} | {n} | {pass_rate} | "
                f"{n_slow_pass} | {avg_tps} | {avg_ttft} | {n_hallucinated} | {avg_turns} | "
                f"{n_tool_errors} | {peak_rss} | {quant_family} | {cache_mode} | {mtp_mode} |"
            ),
            "avg_tps_val": avg_tps_val,
            "coding_pass_rate": coding_pass_rate,
            "hermes_ops_pass_rate": hermes_ops_pass_rate,
            "n_coding": len(coding_scored),
            "n_hermes_ops": len(hermes_ops_scored),
        })

    for gs in group_stats:
        lines.append(gs["line"])

    # Composite "Best overall" ranking (methodology review, finding F3):
    # the table above is 20 independent columns the reader has to weigh
    # by hand — there was no ordering by quality, no tie-break, no single
    # answer to "which one is best." score = 0.5*coding_pass_rate +
    # 0.3*hermes_ops_pass_rate + 0.2*speed_score, per the review's own
    # suggested starting point: "the exact weights matter far less than
    # writing SOME weighting down and sorting by it." speed_score is each
    # group's avg_tps normalized against the FASTEST group seen in this
    # run (0.0-1.0), not an absolute tok/s target, since "fast enough" is
    # relative to what this hardware can actually produce for any model.
    #
    # A group missing an axis entirely (most groups have zero coding rows
    # today, per finding F1) does NOT get scored as if that axis were 0 —
    # the weights renormalize over whichever axes actually have data, so a
    # hermes_ops-only group is judged on hermes_ops+speed alone, not
    # unfairly zeroed out on coding it was never run against. This means
    # scores computed from different axis-subsets aren't perfectly
    # apples-to-apples — flagged in the section text, not hidden.
    max_tps = max(
        (gs["avg_tps_val"] for gs in group_stats if gs["avg_tps_val"] is not None),
        default=None,
    )
    ranked = []
    for gs in group_stats:
        axes = []
        if gs["coding_pass_rate"] is not None:
            axes.append((gs["coding_pass_rate"], 0.5))
        if gs["hermes_ops_pass_rate"] is not None:
            axes.append((gs["hermes_ops_pass_rate"], 0.3))
        if gs["avg_tps_val"] is not None and max_tps:
            axes.append((gs["avg_tps_val"] / max_tps, 0.2))
        if not axes:
            continue
        total_weight = sum(w for _, w in axes)
        score = sum(v * w for v, w in axes) / total_weight
        ranked.append((score, len(axes), gs))

    lines.append("")
    lines.append("## Best overall (composite ranking)")
    lines.append("")
    lines.append("`score = 0.5×coding_pass_rate + 0.3×hermes_ops_pass_rate + 0.2×speed_score`")
    lines.append("(speed_score = this group's avg tok/s ÷ the fastest group's avg tok/s seen")
    lines.append("in this run). Weights renormalize over whichever axes a group actually has")
    lines.append("data for — a group with no coding rows yet is scored on hermes_ops+speed")
    lines.append("alone, not penalized as if its missing coding score were 0. That also means")
    lines.append("a 1-axis score and a 3-axis score aren't strictly apples-to-apples; `axes`")
    lines.append("below shows how many contributed. Groups with zero scoreable axes (harness-")
    lines.append("error-only, or sanity-only with `--coding-suites`/`hermes_ops` never run)")
    lines.append("are omitted entirely rather than shown with a misleading score.")
    lines.append("")
    if not ranked:
        lines.append("No group has enough data yet to score.")
    else:
        lines.append("| rank | model | engine | quant | config | score | axes | coding | hermes_ops | speed |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|")
        for i, (score, n_axes, gs) in enumerate(
            sorted(ranked, key=lambda t: t[0], reverse=True), start=1
        ):
            model, inference_engine, quant, config_hash, runner_sha = gs["key"]
            coding_disp = f"{100 * gs['coding_pass_rate']:.0f}% ({gs['n_coding']})" if gs["coding_pass_rate"] is not None else "—"
            hermes_disp = f"{100 * gs['hermes_ops_pass_rate']:.0f}% ({gs['n_hermes_ops']})" if gs["hermes_ops_pass_rate"] is not None else "—"
            speed_disp = f"{gs['avg_tps_val']:.1f} tok/s" if gs["avg_tps_val"] is not None else "—"
            lines.append(
                f"| {i} | {model} | {inference_engine} | {quant or '—'} | {config_hash or '—'} | "
                f"{score:.2f} | {n_axes} | {coding_disp} | {hermes_disp} | {speed_disp} |"
            )

    lines.append("")
    lines.append("## Flaky tasks (mixed pass/fail under identical conditions)")
    lines.append("")
    lines.append("Any task with the SAME (model, inference_engine, quant, config_hash,")
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
        key = (r["model"], _row_inference_engine(r), r.get("quant"), r.get("config_hash"), r.get("runner_git_sha"), r["suite"], r["task_id"])
        task_groups[key].append(r)
    flaky = {k: v for k, v in task_groups.items() if 0 < sum(1 for r in v if r.get("pass")) < len(v)}
    if not flaky:
        lines.append("None observed (or no task has been run with `--trials` > 1 yet).")
    else:
        lines.append("| model | engine | quant | config | suite | task | pass/trials |")
        lines.append("|---|---|---|---|---|---|---|")
        for (model, inference_engine, quant, config_hash, runner_sha, suite, task_id), group in sorted(flaky.items(), key=lambda kv: tuple(str(x) for x in kv[0])):
            n = len(group)
            n_pass = sum(1 for r in group if r.get("pass"))
            lines.append(f"| {model} | {inference_engine} | {quant or '—'} | {config_hash or '—'} | {suite} | {task_id} | {n_pass}/{n} |")

    lines.append("")
    lines.append("## By suite")
    lines.append("")
    lines.append("| model | engine | config | runner | suite | pass rate |")
    lines.append("|---|---|---|---|---|---|")
    suite_groups = defaultdict(list)
    for r in rows:
        if r.get("harness_error"):  # CR3-6: same exclusion as the main table
            continue
        key = (r["model"], _row_inference_engine(r), r.get("config_hash"), r.get("runner_git_sha"), r["suite"])
        suite_groups[key].append(r)
    for (model, inference_engine, config_hash, runner_sha, suite), group in sorted(
        suite_groups.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2] or "", kv[0][3] or "", kv[0][4])
    ):
        n = len(group)
        n_pass = sum(1 for r in group if r.get("pass"))
        runner_label = runner_sha or "*(predates tracking)*"
        lines.append(f"| {model} | {inference_engine} | {config_hash or '—'} | {runner_label} | {suite} | {n_pass}/{n} |")

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
        lines.append("| model | engine | suite | task | grade_output (truncated) |")
        lines.append("|---|---|---|---|---|")
        for r in sorted(harness_error_rows, key=lambda r: (r["model"], _row_inference_engine(r), r["suite"], r["task_id"])):
            snippet = r.get("grade_output", "")[:120].replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {r['model']} | {_row_inference_engine(r)} | {r['suite']} | {r['task_id']} | {snippet} |")

    blocked = _blocked_configs()
    lines.append("")
    lines.append("## Blocked configs (marked non-viable, excluded from every table above)")
    lines.append("")
    lines.append("Scanned directly from `configs/**/*.yaml` (`orchestration.viable: blocked`),")
    lines.append("not from log rows — a config can be blocked before it was ever run (e.g.")
    lines.append("a whole quant ladder ruled out once one sibling engine's live pilot showed")
    lines.append("the model too slow to be worth testing further), so it would otherwise")
    lines.append("vanish from this file with no trace of why.")
    lines.append("")
    if not blocked:
        lines.append("None currently blocked.")
    else:
        lines.append("| model | engine | config | blocked_reason |")
        lines.append("|---|---|---|---|")
        for b in blocked:
            reason = b["blocked_reason"].replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {b['model']} | {b['inference_engine']} | {b['config_path']} | {reason} |")

    speed_gated = _speed_gated_configs()
    lines.append("")
    lines.append("## Speed-gated configs (stopped early — too slow to be practical)")
    lines.append("")
    lines.append("`run_bench.py` runs a config's full hermes_ops suite as normal, then checks")
    lines.append("the average tokens_per_second across every task it just ran — the same")
    lines.append("number the main table's `avg tok/s` column reports. Below threshold, it")
    lines.append("skips the coding suite (typically far more expensive: real builds +")
    lines.append("multi-turn agentic loops) rather than spend that time confirming an outcome")
    lines.append("hermes_ops already answered. The hermes_ops rows themselves ARE still real")
    lines.append("log.jsonl rows (visible in every table above) — this section just makes the")
    lines.append("*reason the coding suite didn't run* explicit rather than something a reader")
    lines.append("has to infer from a config missing coding rows.")
    lines.append("")
    if not speed_gated:
        lines.append("None gated on speed so far.")
    else:
        lines.append("| model | engine | config | avg tok/s | per-task tok/s | threshold | timestamp |")
        lines.append("|---|---|---|---|---|---|---|")
        for g in speed_gated:
            measured = g.get("measured_tokens_per_second") or []
            measured_disp = ", ".join(f"{v:.2f}" for v in measured) if measured else "—"
            avg_disp = f"{g['avg_tokens_per_second']:.2f}" if g.get("avg_tokens_per_second") is not None else "—"
            lines.append(
                f"| {g.get('model', '—')} | {g.get('inference_engine') or g.get('framework') or g.get('backend', '—')} | {g.get('config_path', '—')} | "
                f"{avg_disp} | {measured_disp} | {g.get('threshold_tokens_per_second', '—')} | {g.get('timestamp', '—')} |"
            )

    Path(REPO / "results" / "LEADERBOARD.md").write_text("\n".join(lines) + "\n")
    print(f"Wrote results/LEADERBOARD.md from {len(rows)} rows.")


if __name__ == "__main__":
    main()
