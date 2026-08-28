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

# Benchmark v2 (2026-08-27, user request): a coding-suite row missing
# hermes_turns (the count pulled from hermes's own SQLite session store)
# means the process was killed by the wall-clock timeout before hermes
# ever got to export session stats -- NOT that it took few turns. Scoring
# that as "0 turns" (or excluding it) would perversely REWARD a hard
# wall-clock kill with a better turns score than a model that ran the
# full, real, high-turn-count session and got graded normally. Substitute
# hermes's own agent.max_turns (~/.hermes/profiles/bench/config.yaml) as
# the assumed-worst-case value instead -- the model was still going when
# killed, so "at least this many turns" is the fair, conservative read.
CODING_TURNS_CEILING_FOR_TIMEOUT = 40

# Weights for the composite coding score (see _composite_coding_score()
# below) -- a starting point per this repo's own precedent ("the exact
# weights matter far less than writing SOME weighting down and sorting by
# it"), not a tuned optimum. Adjustable later.
#
# First tried at pass=0.35/speed=0.35 (equal top weight, per the initial
# "pass + speed should get most weight" framing) -- spot-checking the real
# regenerated leaderboard surfaced a genuine problem: a 0%-coding-pass-rate
# model (fast) outranked an 82%-coding-pass-rate model (slower), since a
# 0% pass rate doesn't zero out the composite when speed alone can still
# contribute up to its full 0.35 share -- reintroducing, at smaller scale,
# exactly the "fast-but-non-functional beats slow-but-competent" problem
# round 2's gate-then-rank design existed to fix. User's explicit call
# (2026-08-27) after seeing this: give pass MORE weight than speed, not
# equal -- pass still "gets a lot of weight," but can no longer be fully
# cancelled out by raw speed alone.
CODING_SCORE_WEIGHTS = {"pass": 0.45, "speed": 0.25, "time": 0.20, "turns": 0.10}


def _fairness_fields(config_hash, config_path):
    """temperature/reasoning_mode/reasoning_effort as declared in the
    config that produced this group — surfaced as their own columns so
    two configs that differ in these (not just quant) can't be silently
    read as an apples-to-apples comparison (adversarial review finding
    H7). reasoning_effort added 2026-08-27 (user request): reasoning is a
    large part of a thinking-mode model's output, and it was previously
    invisible even though it materially affects results — e.g. the
    Qwen3.8-27B family's own chat_template.jinja silently defaults to
    'medium' effort whenever no --reasoning-effort flag is passed (which
    every GGUF config for this family does, this whole session), so
    every result from that family has actually been produced at a
    specific, non-default-looking effort level nobody could previously
    see in any table. Missing from a config entirely (non-thinking
    models, or thinking models that don't expose a tunable effort level)
    renders as "n/a", not "?" — "?" is reserved for a config that SHOULD
    have this field (thinking mode + effort-tunable family) but the
    lookup itself failed (missing snapshot, hash mismatch), same
    precedent as temp/mode below. Prefers the exact snapshot (what was
    actually run) over the live file (which may have changed) — and,
    found by a second independent adversarial review (finding M-8): when
    falling back to the live file, only trusts it if its CURRENT hash
    still matches this row's config_hash. Confirmed live: without this
    check, a synthetic row carrying an unrelated config_hash rendered
    fairness values sourced entirely from today's live config content —
    which is what every pre-snapshot row in this repo currently does."""
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
    except yaml.YAMLError:
        return "?", "?", "?"
    temp = cfg.get("temperature", "?")
    mode = cfg.get("reasoning_mode", "?")
    effort = cfg.get("reasoning_effort", "n/a")
    return str(temp), str(mode), str(effort)


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
    bench_common.MIN_HERMES_OPS_TOKENS_PER_SECOND (see that constant's own
    comment for its current value and why it has been changed twice; the
    number is deliberately not restated here — improvement plan M5) across
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


def compute_group_stats(groups):
    """One row of the main leaderboard table (and the raw scoring inputs
    the composite "Best overall" ranking below needs) per (model,
    inference_engine, quant, config_hash, runner_git_sha) group. A
    separate pass from rank_groups() below: rank_groups() needs every
    group's raw numeric avg_tps/avg_coding_wall/avg_coding_turns visible
    at once before it can normalize any one group's speed/time/turns
    against the best value seen this run — that global best isn't known
    until all groups have been computed once. group_stats carries both
    the raw numbers (for scoring) and the pre-formatted display string
    (for the main table), computed once, so the two can never drift
    apart."""
    group_stats = []
    for (model, inference_engine, quant, config_hash, runner_sha), group in sorted(
        groups.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2] or "", kv[0][3] or "", kv[0][4] or "")
    ):
        scored = [r for r in group if not r.get("harness_error")]
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
        if any(r.get("ttft_measurable") is False for r in scored):
            avg_ttft = "n/a (proxied — not real TTFT)"
        else:
            ttft_values = [r["ttft_seconds"] for r in scored if r.get("ttft_seconds") is not None]
            avg_ttft = f"{mean(ttft_values):.2f}" if ttft_values else "—"
        n_hallucinated = sum(1 for r in scored if r.get("grade_output", "").startswith("FAIL: model called tool"))
        turn_values = [r["hermes_turns"] for r in scored if r.get("hermes_turns") is not None]
        avg_turns = f"{mean(turn_values):.1f}" if turn_values else "—"
        n_tool_errors = sum(r["hermes_tool_errors"] for r in scored if r.get("hermes_tool_errors") is not None)
        n_slow_pass = sum(1 for r in scored if r.get("pass") and r.get("within_budget") is False)
        rss_values = [r["peak_rss_gb"] for r in scored if r.get("peak_rss_gb") is not None]
        peak_rss = f"{max(rss_values):.1f}" if rss_values else "—"
        config_path = next((r.get("config_path") for r in group if r.get("config_path")), None)
        config_label = _config_label(config_hash, config_path)
        temp, reasoning_mode, reasoning_effort = _fairness_fields(config_hash, config_path)
        quant_family, cache_mode, mtp_mode = _experiment_fields(config_hash, config_path)
        runner_label = runner_sha or "*(predates tracking)*"

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

        coding_wall_values = [r["wall_seconds"] for r in coding_scored if r.get("wall_seconds") is not None]
        avg_coding_wall = mean(coding_wall_values) if coding_wall_values else None
        coding_turns_values = [
            r["hermes_turns"] if r.get("hermes_turns") is not None else CODING_TURNS_CEILING_FOR_TIMEOUT
            for r in coding_scored
        ]
        avg_coding_turns = mean(coding_turns_values) if coding_turns_values else None

        group_stats.append({
            "key": (model, inference_engine, quant, config_hash, runner_sha),
            "line": (
                f"| {model} | {inference_engine} | {quant or '—'} | {temp} | {reasoning_mode} | "
                f"{reasoning_effort} | {sanity_gate} | {config_label} | {runner_label} | {n} | {pass_rate} | "
                f"{n_slow_pass} | {avg_tps} | {avg_ttft} | {n_hallucinated} | {avg_turns} | "
                f"{n_tool_errors} | {peak_rss} | {quant_family} | {cache_mode} | {mtp_mode} |"
            ),
            "avg_tps_val": avg_tps_val,
            "reasoning_mode": reasoning_mode,
            "reasoning_effort": reasoning_effort,
            "coding_pass_rate": coding_pass_rate,
            "hermes_ops_pass_rate": hermes_ops_pass_rate,
            "avg_coding_wall": avg_coding_wall,
            "avg_coding_turns": avg_coding_turns,
            "n_sanity": len(sanity_scored),
            "n_coding": len(coding_scored),
            "n_hermes_ops": len(hermes_ops_scored),
            "latest_timestamp": max((r.get("timestamp") or "" for r in group), default=""),
        })
    return group_stats


GATE_HERMES_OPS_THRESHOLD = 0.5  # majority-pass — same concept as run_bench.py's _majority_pass()


def rank_groups(group_stats):
    """"Best overall" ranking, round 2 (2026-08-26 user feedback, replacing
    the weighted-blend design from round 1 / fa0046f / methodology review
    F3). The user's own framing: this benchmark isn't measuring "coding
    ability" as one input among peers — it's measuring USEFULNESS AS AN
    AGENT, and only THEN coding ability. "If the sanity check or full
    Hermes pass does not complete it fails the basic usefulness check.
    Then coding ability is the discerning next factor + speed which
    improves usability." A weighted blend (0.5/0.3/0.2) let speed and
    hermes_ops act as PEERS of coding, so a fast, hermes_ops-competent
    model with weak coding evidence could still outscore a slower model
    that actually demonstrated coding ability — the exact bug this round
    of feedback is about. This is now a staged gate-then-rank, not a
    blend:

    1. ELIGIBILITY (stricter than round 1, which only required
       n_coding >= 1): a group must have at least one row on ALL THREE
       axes — sanity, hermes_ops, coding — to represent a genuinely
       COMPLETED benchmark run. A group that never reached hermes_ops or
       coding (e.g. stopped by the speed gate, or still mid-run) isn't
       "for which we have all numbers" and has no place here at all,
       complete or not — it doesn't get scored on whatever subset of axes
       it happens to have, the way round 1 allowed.

    2. USEFULNESS GATE — a hard pass/fail TIER, not a weighted input:
       hermes_ops_pass_rate >= 0.5 (majority-pass; same threshold concept
       as run_bench.py's own `_majority_pass()` sanity-gate helper). A
       model that can't reliably do basic tool-use/agent operations isn't
       "useful as an agent" regardless of how well it codes or how fast
       it is — every gate-PASSING group ranks above every gate-FAILING
       group, full stop, no matter their coding or speed numbers.

    3. PRIMARY SORT among gate-passers (round 3, see CODING_SCORE_WEIGHTS):
       a weighted composite of pass rate, speed, time taken, and turns
       used — see module docstring on CODING_SCORE_WEIGHTS for the exact
       numbers and why.

    4. Dedup-to-most-evidenced-fragment-per-(model, inference_engine,
       quant) from round 1 is unchanged — still needed so an early
       1-task fragment from before a model was fully tested can't outrank
       that same model's own later, complete sweep. FIXED 2026-08-28
       (benchmark v2 Phase D wrap-up): on an EXACT evidence tie between
       two fragments of the same config (e.g. two separate full 19-task
       runs of the same config on different days — a re-run superseding
       an earlier one, not a partial), the old `evidence > current`
       comparison silently kept whichever fragment iteration happened to
       reach first (dict insertion order), which is arbitrary and
       genuinely picked a STALE result once during this session's own
       Phase D (Qwen3-Coder-30B-A3B's real 89%-pass/11-11-coding rerun
       lost a tie to an older 74%-pass partial under the same config
       hash). Now breaks ties by `latest_timestamp` — the more recent
       run wins, since a same-config re-run is meant to supersede, not
       compete evenly with, an earlier one.

    Round 3 (2026-08-27, benchmark v2, user request): round 2's primary
    sort was plain coding_pass_rate, tie-broken by speed — clean, but it
    couldn't distinguish "genuinely better at coding" from "took forever
    and used every one of its turns to barely scrape a pass," and gave
    slow-but-correct models no credit at all for eventually finishing
    once the coding-suite timeouts were bumped (see tasks/kiem_mini.yaml
    etc.) to let them run to completion instead of being hard-killed.
    This replaces that primary sort with a weighted composite over four
    axes the user specifically asked to be tracked together: pass rate
    and speed matter most (equal top weight), then time taken, then
    turns used — see CODING_SCORE_WEIGHTS's own comment for the exact
    numbers and where they come from.

    Each axis is normalized 0.0-1.0 against the best value seen among
    this run's ELIGIBLE (fully-completed, gate-passing candidates for
    normalization purposes — see eligible_for_norm below) groups, not
    against an absolute target, since "fast" and "few turns" are only
    meaningful relative to what this hardware/task-set actually
    produces:
      pass  = coding_pass_rate directly (already 0.0-1.0)
      speed = avg_tps / fastest group's avg_tps
      time  = fastest (lowest) group's avg_coding_wall / this group's
              avg_coding_wall (shorter is better, so INVERTED)
      turns = fewest-turns group's avg_coding_turns / this group's
              avg_coding_turns (fewer is better, so INVERTED)
    A group missing a denominator input (e.g. every coding row somehow
    lacked wall_seconds) scores 0.0 on that one axis rather than being
    excluded outright — conservative, not a crash.

    The usefulness GATE (hermes_ops >= 50%, hard tier boundary) and the
    eligibility rule (all three axes present) from round 2 are BOTH
    unchanged — this round only changes how gate-passers are ordered
    relative to each other, not who's allowed to compete at all.

    Returns a list of (gate_pass, score, gs) tuples, unsorted — callers
    sort by (gate_pass, score) descending themselves, since some callers
    (e.g. the chart script) want the ranking without re-deriving the
    display formatting that lives alongside the sort in main().
    """
    best_fragment = {}
    for gs in group_stats:
        model, inference_engine, quant, _config_hash, _runner_sha = gs["key"]
        dedup_key = (model, inference_engine, quant)
        evidence = gs["n_coding"] + gs["n_hermes_ops"]
        current = best_fragment.get(dedup_key)
        if current is None:
            best_fragment[dedup_key] = gs
            continue
        current_evidence = current["n_coding"] + current["n_hermes_ops"]
        if evidence > current_evidence or (
            evidence == current_evidence
            and gs["latest_timestamp"] > current["latest_timestamp"]
        ):
            best_fragment[dedup_key] = gs

    eligible_for_norm = [
        gs for gs in best_fragment.values()
        if gs["n_sanity"] and gs["n_hermes_ops"] and gs["n_coding"]
        and gs["hermes_ops_pass_rate"] >= GATE_HERMES_OPS_THRESHOLD
    ]
    max_tps_for_score = max(
        (gs["avg_tps_val"] for gs in eligible_for_norm if gs["avg_tps_val"]), default=None,
    )
    min_wall_for_score = min(
        (gs["avg_coding_wall"] for gs in eligible_for_norm if gs["avg_coding_wall"]), default=None,
    )
    min_turns_for_score = min(
        (gs["avg_coding_turns"] for gs in eligible_for_norm if gs["avg_coding_turns"]), default=None,
    )

    def _composite_coding_score(gs):
        pass_component = gs["coding_pass_rate"] or 0.0
        speed_component = (
            gs["avg_tps_val"] / max_tps_for_score
            if gs["avg_tps_val"] and max_tps_for_score else 0.0
        )
        time_component = (
            min_wall_for_score / gs["avg_coding_wall"]
            if gs["avg_coding_wall"] and min_wall_for_score else 0.0
        )
        turns_component = (
            min_turns_for_score / gs["avg_coding_turns"]
            if gs["avg_coding_turns"] and min_turns_for_score else 0.0
        )
        return (
            CODING_SCORE_WEIGHTS["pass"] * pass_component
            + CODING_SCORE_WEIGHTS["speed"] * speed_component
            + CODING_SCORE_WEIGHTS["time"] * time_component
            + CODING_SCORE_WEIGHTS["turns"] * turns_component
        )

    ranked = []
    for gs in best_fragment.values():
        if not (gs["n_sanity"] and gs["n_hermes_ops"] and gs["n_coding"]):
            continue  # not a completed run — missing an entire axis
        gate_pass = gs["hermes_ops_pass_rate"] >= GATE_HERMES_OPS_THRESHOLD
        score = _composite_coding_score(gs) if gate_pass else 0.0
        # Sort key is lexicographic, most-significant field first: gate
        # status beats the composite score, always — never traded off
        # against each other the way folding hermes_ops into the same
        # blend would allow.
        ranked.append((gate_pass, score, gs))
    return ranked


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
            f"> **⚠ {len(stale_rows)}/{len(rows)} rows below predate 2026-08-21",
            "> grading fixes** (no `runner_git_sha` — that field didn't exist yet).",
            "> **Do not treat any pre-2026-08-21 PASS/FAIL as final signal** until",
            "> re-run under current grading. Known-affected checks: `kiem_mini-feature`",
            "> (used to grade only the library function, never the CLI wiring),",
            "> `hermes_ops-error-recovery` (used to reward fabricated file contents if",
            "> an unrelated word like \"error\" appeared anywhere), `hermes_ops-selection`",
            "> (used to match \"18\" as a substring of any number, including \"2018\"),",
            "> `hermes_ops-chaining` (used to accept extra content beyond the requested",
            "> single number), and `sanity-tool` (used multiset argument matching,",
            "> which could pass wrong argument names). Re-running is the only way to",
            "> get current, trustworthy rows for these tasks.",
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
        "**`avg tok/s` caveat**:",
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
        "**¹ `temp (coding only)`**: the config's declared temperature is what the",
        "coding suite (`hermes chat`, driven by `run_fixture_suite.py`) actually",
        "runs at, since it respects the server's launch flags. `sanity`/`hermes_ops`",
        "(driven by `run_prompt.py`) deliberately hardcode `temperature=0` for EVERY",
        "model, always, regardless of this config value — a longstanding, documented",
        "design choice (see `tasks/SCHEMA.md` \"Temperature is deliberately fixed",
        "at 0\"), not a bug.",
        "Note also: `configs/Qwen3.8-27B-Ridge/gguf.yaml` is the only config that",
        "sets `--presence-penalty` (1.5) — a third confound alongside temp/",
        "reasoning-mode when comparing it against `configs/Qwen3.8-27B/gguf.yaml`,",
        "not currently its own column since no other config sets this flag.",
        "",
        "**² `slow passes`**: count of PASS rows",
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
        "**³ `avg coding turns` / `coding tool errors`**: pulled from hermes's own",
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
        "**⁴ `sanity gate` / `pass rate`**: `sanity`",
        "is a fail-fast GATE — run_bench.py stops the whole config entirely if",
        "sanity-basic fails — not a quality signal to blend in alongside real",
        "tool-use/coding results. It's shown here as its own `passed/total` column",
        "instead. `pass rate` now covers only `hermes_ops` + coding-suite rows;",
        "folding sanity in used to compress real differences between models,",
        "since it sits at or near ceiling for nearly everything.",
        "",
        "**⁵ `hallucinated tools`**: this only",
        "fires in the two synthetic prompt suites (sanity/hermes_ops), whose fixed",
        "tool manifest makes \"called a tool that doesn't exist in it\" a clean,",
        "checkable signal. The coding suite has no equivalent check — a hermes",
        "chat session's real tool manifest isn't fixed/known the way hermes_ops's",
        "41-tool mock manifest is, so this reads 0 for every coding-suite row",
        "regardless of what actually happened. Read this column as \"not observed",
        "on the two synthetic suites,\" not \"never hallucinated a tool\".",
        "",
        "**⁶ `reasoning effort`**: added 2026-08-27 (reasoning is a large part of",
        "a thinking-mode model's output, so it needs to be as visible as quant or",
        "temperature). `n/a` means the config has no tunable effort level (a",
        "non-thinking model, or a thinking model whose template doesn't expose",
        "one) -- not the same as `?`, which means the lookup itself failed (see",
        "`_fairness_fields()`'s own comment). A blank-looking value here can",
        "still be a real, active setting: e.g. the Qwen3.8-27B/Qwen3.6-35B-A3B",
        "family's own chat_template.jinja silently defaults to `medium` whenever",
        "no `--reasoning-effort` flag is passed, which every GGUF config for",
        "that family does -- read `n/a`/missing here as \"not yet labeled,\" not",
        "\"no reasoning was used.\" Configs for this family have had this field",
        "added explicitly to record that default rather than leave it invisible.",
        "",
        "| model | engine | quant | temp (coding only)¹ | reasoning | reasoning effort⁶ | sanity gate⁴ | config | runner | tasks | pass rate⁴ | slow passes² | avg tok/s | avg TTFT (s) | hallucinated tools⁵ | avg coding turns³ | coding tool errors³ | peak RSS (GB) | quant family | cache | MTP |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    group_stats = compute_group_stats(groups)

    for gs in group_stats:
        lines.append(gs["line"])

    ranked = rank_groups(group_stats)

    lines.append("")
    lines.append("## Best overall (gate, then weighted composite score)")
    lines.append("")
    lines.append("**Eligibility** — a group must have completed all three stages (sanity +")
    lines.append("hermes_ops + coding, at least one row each) to appear here at all; a partial")
    lines.append("run is excluded outright rather than scored on whichever axes it happens to")
    lines.append("have. **Usefulness gate** (pass/fail tier, not a weighted input) — hermes_ops")
    lines.append("pass rate must be ≥50% (majority-pass, same concept as run_bench.py's sanity")
    lines.append("fail-fast gate); every gate-passing group ranks above every gate-failing one")
    lines.append("regardless of the score below. **Score** among gate-passers is a weighted")
    lines.append(
        f"composite over four coding-suite axes — pass rate ({CODING_SCORE_WEIGHTS['pass']:.0%}),"
    )
    lines.append(
        f"speed ({CODING_SCORE_WEIGHTS['speed']:.0%}), time taken ({CODING_SCORE_WEIGHTS['time']:.0%}),"
    )
    lines.append(
        f"and turns used ({CODING_SCORE_WEIGHTS['turns']:.0%}) — each normalized 0.0-1.0 against"
    )
    lines.append("the best value seen among this run's gate-passing groups (see")
    lines.append("`build_leaderboard.py`'s own comment for the exact formula and why). A slow")
    lines.append("but eventually-correct model is no longer disqualified outright (coding-suite")
    lines.append("timeouts were bumped alongside this change specifically so it can finish) —")
    lines.append("it simply scores lower on speed/time than a faster model with the same pass")
    lines.append("rate. Dedup rule unchanged: each model+engine+quant appears at most once,")
    lines.append("using whichever of its own config_hash/runner_sha fragments has the most")
    lines.append("total coding+hermes_ops evidence.")
    lines.append("")
    if not ranked:
        lines.append("No group has completed all three stages (sanity + hermes_ops + coding) yet.")
    else:
        lines.append("| rank | model | engine | quant | reasoning⁶ | config | usefulness gate | score | coding | speed | avg time (s) | avg turns |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for i, (gate_pass, score, gs) in enumerate(
            sorted(ranked, key=lambda t: (t[0], t[1]), reverse=True), start=1
        ):
            model, inference_engine, quant, config_hash, runner_sha = gs["key"]
            gate_disp = (
                f"{'PASS' if gate_pass else 'FAIL'} "
                f"({100 * gs['hermes_ops_pass_rate']:.0f}%, {gs['n_hermes_ops']})"
            )
            score_disp = f"{score:.3f}" if gate_pass else "—"
            coding_disp = f"{100 * gs['coding_pass_rate']:.0f}% ({gs['n_coding']})"
            speed_disp = f"{gs['avg_tps_val']:.1f} tok/s" if gs["avg_tps_val"] is not None else "—"
            time_disp = f"{gs['avg_coding_wall']:.0f}" if gs["avg_coding_wall"] is not None else "—"
            turns_disp = f"{gs['avg_coding_turns']:.1f}" if gs["avg_coding_turns"] is not None else "—"
            reasoning_disp = (
                gs["reasoning_mode"] if gs["reasoning_effort"] in ("n/a", "?", "None")
                else f"{gs['reasoning_mode']} ({gs['reasoning_effort']})"
            )
            lines.append(
                f"| {i} | {model} | {inference_engine} | {quant or '—'} | {reasoning_disp} | {config_hash or '—'} | "
                f"{gate_disp} | {score_disp} | {coding_disp} | {speed_disp} | {time_disp} | {turns_disp} |"
            )
        lines.append("")
        # Regenerated by runner/plot_leaderboard.py (called right after this
        # file by run_bench.py's _leaderboard()) from the exact same
        # rank_groups() output as the table above — can't silently show a
        # different ranking than the table it sits next to.
        lines.append("![Best overall composite score by model](score_chart.png)")

    lines.append("")
    lines.append("## Flaky tasks (mixed pass/fail under identical conditions)")
    lines.append("")
    lines.append("Any task with the SAME (model, inference_engine, quant, config_hash,")
    lines.append("runner_git_sha, suite, task_id) that comes back with SOME passes and")
    lines.append("some fails is not \"probably fine\" — it's proof this one task's result")
    lines.append("isn't safe to treat as a boolean for this model — temperature=0")
    lines.append("measurably does not make MLX/Metal generation deterministic across")
    lines.append("runs. This catches flakiness from an explicit")
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
            "than the model producing a graded result — shown separately so they "
            "don't deflate pass rates or masquerade as model flakiness."
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
