#!/usr/bin/env python3
"""Standalone summary chart generator for the local-model-bench.

Generates a set of PNG charts from results/log.jsonl summarizing the final
model/engine groups, reusing build_leaderboard.py's own
compute_group_stats()/rank_groups() so charts and the markdown leaderboard can
never drift apart on what a group's numbers mean. This script is intentionally
SEPARATE from build_leaderboard.py and from run_bench.py: it is a curation/reporting
tool you run by hand once the final selection is decided. It never writes
LEADERBOARD.md, SUMMARY.md, or any results rows (it only writes the PNGs).

Headline charts use only the FULL ELIGIBLE groups returned by
build_leaderboard.rank_groups() (full-suite completion + benchmark-v2-or-later +
usefulness gate), matching the "Best overall" table — extended with two curation
admissions that clear the SAME real full-suite + zero-harness-error bar: curated
multi-fragment combinations (see below) and explicitly pinned single-fragment
selections whose key rank_groups deduplicates to a different (older/richer)
fragment. A chart that shows partial data explicitly documents that ("(partial)").

Run (callable with `uv`, headless — Matplotlib is forced to the Agg backend):

    uv run --locked python runner/build_summary_charts.py
    uv run --locked python runner/build_summary_charts.py --log path/log.jsonl
    uv run --locked python runner/build_summary_charts.py --output-dir results
    uv run --locked python runner/build_summary_charts.py --models "gemma,ornith"
    uv run --locked python runner/build_summary_charts.py --engines "mei,llama.cpp"
    uv run --locked python runner/build_summary_charts.py --selection selection.json

Selection file schema
---------------------
The provenance "model" strings are not always text-identical between a Mei
artifact and its llama.cpp GGUF sibling (e.g. model ``mlx-community/gemma-4-26b-a4b-it-4bit``
vs ``mudler/gemma-4-26B-A4B-it-APEX-GGUF:APEX-I-Compact``), so selection must be
by family + engine, not by exact model-string equality alone. `--selection`
points at a JSON document that is a list of records with this schema:

    [
      {
        "family": "gemma-4-26B",                 # REQUIRED grouping key
        "engine": "mei",                          # REQUIRED (e.g. "mei", "llama.cpp", "llama.cpp-dflash2")
        "model_contains": "gemma-4-26b-a4b-it-4bit",  # case-insensitive substring of the log model name
        # -- OR use an exact model name instead of model_contains --
        # "model": "mlx-community/gemma-4-26b-a4b-it-4bit",
        "config_hash": "a1b2c3d4e5f6",            # OPTIONAL 12-hex; when set the record must match this exact group
        "runner_git_sha": "b053b9647e1a"          # OPTIONAL 12-hex; when set the record must match this exact group
      },
      # -- OR combine MULTIPLE leaderboard fragments into ONE curated leg --
      # A record with `fragments` instead of a single `model_contains`/`model`
      # concatenates the rows of each listed fragment into one synthetic group.
      # This is how a run that spanned multiple runner_git_sha commits (e.g. a
      # sanity+hermes_ops leg under one sha and the coding suites under a later
      # sha, same config) is represented as a single full 25-row benchmark leg
      # rather than silently picking one fragment. Each fragment is resolved with
      # the SAME matching rules as a single record (model_contains/model +
      # optional config_hash/runner_git_sha); a missing fragment is surfaced as
      # partial/no-match, never silently dropped. The combined group is marked
      # full/eligible only when it meets the real full-suite counts with zero
      # harness errors; total_runtime_seconds is recovered across the combined
      # rows. `fragments` and a single-fragment matcher are mutually exclusive.
      {
        "family": "Gemma-4-26B", "engine": "mei",
        "fragments": [
          {"model_contains": "mlx-community/gemma-4-26b-a4b-it-4bit",
           "config_hash": "bc93f3cc55a1", "runner_git_sha": "06f997b70746"},
          {"model_contains": "mlx-community/gemma-4-26b-a4b-it-4bit",
           "config_hash": "bc93f3cc55a1", "runner_git_sha": "a171c0999673"}
        ]
      },
      { "family": "gemma-4-26B", "engine": "llama.cpp",
        "model_contains": "gemma-4-26B-A4B-it-APEX-GGUF:APEX-I-Compact" },
      { "family": "ornith-1.5-35B", "engine": "mei", "model_contains": "Ornith-1.5-35B-A3B-MLX-4bit" },
      { "family": "ornith-1.5-35B", "engine": "llama.cpp",
        "model_contains": "Ornith-1.5-35B-A3B-APEX-GGUF:APEX-Compact" }
    ]

A record resolves to exactly one leaderboard group (model, engine, quant,
config_hash, runner_git_sha). When several candidate groups match (e.g. the same
family/engine appears under multiple quant or runner configs), resolution
prefers, in order: (1) an exact config_hash / runner_git_sha pin if given, (2) a
full-eligible group (rank_groups' "Best overall" set), (3) otherwise the most
recently-run matching group — and the resolution result is surfaced so a partial
selection is explicitly acknowledged.

Engine-delta pairing (engine_delta.png) is by family + engine after selection:
for each family, the selected `mei` group is compared against its selected
`llama.cpp` group. A family with only one of the two engines is skipped with a
logged reason instead of emitting a misleading one-sided chart.

Charts generated (only when there is sufficient data; harmless skips are logged):
  1. quality_vs_runtime.png  — combined hermes_ops+coding pass rate vs recovered
     total runtime (hours); colored by engine; Pareto-efficient points highlighted.
  2. engine_delta.png         — paired Mei vs llama.cpp pass-rate + runtime deltas per family.
  3. suite_heatmap.png        — selected complete groups x suite, cells = pass rate.
  4. runtime_breakdown.png    — stacked bars of per-suite task wall-time totals (labeled
     as task wall-time, distinct from the recovered headline total runtime).
  5. failure_taxonomy.png     — only when failures are meaningful and varied; otherwise skipped.
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless — no display available in this harness
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_leaderboard import (  # noqa: E402
    compute_group_stats,
    rank_groups,
    _row_inference_engine,
)
import build_leaderboard as _bl  # noqa: E402  (module ref so the FULL_*_TASKS patch in tests is honored)

REPO = Path(__file__).resolve().parent.parent

# Suites in a canonical display order; any other suite actually present in the
# selected data is appended after these, so a novel suite is still shown.
SUITES_ORDER = ["sanity", "hermes_ops", "kiem_mini", "hearth_mini", "kipclip_mini", "hearth_full"]

# Colorblind-safe categorical palette for coloring by engine.
ENGINE_COLORS = [
    "#1f6fb2", "#c8792a", "#2a9d8f", "#a855f7", "#7a7a52",
    "#d64550", "#3b7a3b", "#8a6bbd", "#a05a2c", "#5d7a99",
]

COLOR_TEXT = "#1a1a1a"
COLOR_GRID = "#d9d9d9"
COLOR_MISSING = "#e8e8e8"  # missing/masked heatmap cell


# --------------------------------------------------------------------------- #
# Data loading + group building (delegates to build_leaderboard)
# --------------------------------------------------------------------------- #
def load_rows(log_path):
    """Read results/log.jsonl into a list of row dicts (blank lines skipped)."""
    rows = []
    for line in Path(log_path).read_text().splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def group_rows(rows):
    """Group rows by the leaderboard 5-tuple key, exactly like build_leaderboard.main()."""
    groups = defaultdict(list)
    for r in rows:
        key = (r["model"], _row_inference_engine(r), r.get("quant"), r.get("config_hash"), r.get("runner_git_sha"))
        groups[key].append(r)
    return groups


def eligible_ranked(groups):
    """Return (group_stats, ranked, eligible_keys).

    group_stats/ranked are exactly what build_leaderboard.compute_group_stats() /
    rank_groups() return. eligible_keys is the set of group keys that appear in
    rank_groups' output (the full-suite, v2-or-later, gate-passing "Best overall"
    groups). rank_groups returns (gate_pass, score, gs) tuples; we also return the
    score map so engine-delta can show score deltas when present.
    """
    group_stats = compute_group_stats(groups)
    ranked = rank_groups(group_stats)
    eligible_keys = {gs["key"] for (_g, _s, gs) in ranked}
    score_by_key = {gs["key"]: score for (_g, score, gs) in ranked}
    return group_stats, ranked, eligible_keys, score_by_key


def combined_pass_rate(gs):
    """Combined hermes_ops + coding pass rate (the score's "pass" axis).

    Returns None when there are no hermes_ops or coding rows at all to divide by.
    """
    denom = gs["n_hermes_ops"] + gs["n_coding"]
    if not denom:
        return None
    return (gs["n_hermes_ops_pass"] + gs["n_coding_pass"]) / denom


def total_runtime_hours(gs):
    secs = gs.get("total_runtime_seconds")
    if secs is None:
        return None
    return secs / 3600.0


# --------------------------------------------------------------------------- #
# Selection + filtering
# --------------------------------------------------------------------------- #
def load_selection(path):
    """Load and validate a --selection JSON file.

    Returns a list of record dicts. Raises ValueError with a human-readable
    message on a schema violation so a bad curation file fails loudly rather than
    silently influencing the charts.

    A record is EITHER a single-fragment selection (sets `model_contains`/`model`,
    with optional `config_hash`/`runner_git_sha`) OR a multi-fragment `fragments`
    list (see module docstring). Both are mutually exclusive; a record that sets
    neither (or both) is a schema error. Multi-fragment combinations lift the
    `family`/`engine` from the outer record and apply the same per-fragment
    matching rules (model_contains/model + optional config_hash/runner_git_sha).
    """
    raw = json.loads(Path(path).read_text())
    if not isinstance(raw, list):
        raise ValueError(f"selection file {path} must be a JSON list of records, got {type(raw).__name__}")
    records = []
    for i, rec in enumerate(raw):
        if not isinstance(rec, dict):
            raise ValueError(f"selection record #{i} must be an object, got {type(rec).__name__}")
        if not rec.get("family"):
            raise ValueError(f"selection record #{i} missing required 'family' (got {rec!r})")
        if not rec.get("engine"):
            raise ValueError(f"selection record #{i} missing required 'engine' (got {rec!r})")
        frags = rec.get("fragments")
        if frags is not None:
            if not isinstance(frags, list) or not frags:
                raise ValueError(
                    f"selection record #{i} ({rec.get('family')}/{rec.get('engine')}) "
                    "'fragments' must be a non-empty list of fragment selectors"
                )
            if rec.get("model_contains") or rec.get("model"):
                raise ValueError(
                    f"selection record #{i} ({rec.get('family')}/{rec.get('engine')}) "
                    "cannot set both 'fragments' and a single-fragment 'model_contains'/'model'"
                )
            parsed_frags = []
            for j, frag in enumerate(frags):
                if not isinstance(frag, dict):
                    raise ValueError(
                        f"selection record #{i} fragment #{j} must be an object, got {type(frag).__name__}"
                    )
                if not frag.get("model_contains") and not frag.get("model"):
                    raise ValueError(
                        f"selection record #{i} fragment #{j} must set 'model_contains' "
                        "(case-insensitive substring) or exact 'model'"
                    )
                parsed_frags.append({
                    "model_contains": frag.get("model_contains"),
                    "model": frag.get("model"),
                    "config_hash": frag.get("config_hash"),
                    "runner_git_sha": frag.get("runner_git_sha"),
                })
            records.append({
                "family": str(rec["family"]),
                "engine": str(rec["engine"]),
                "fragments": parsed_frags,
                "model_contains": None,
                "model": None,
                "config_hash": None,
                "runner_git_sha": None,
            })
            continue
        if not rec.get("model_contains") and not rec.get("model"):
            raise ValueError(
                f"selection record #{i} ({rec.get('family')}/{rec.get('engine')}) "
                "must set 'model_contains' (case-insensitive substring) or exact 'model'"
            )
        records.append({
            "family": str(rec["family"]),
            "engine": str(rec["engine"]),
            "model_contains": rec.get("model_contains"),
            "model": rec.get("model"),
            "config_hash": rec.get("config_hash"),
            "runner_git_sha": rec.get("runner_git_sha"),
        })
    return records


def _group_label(gs):
    model, engine, quant, _ch, _sha = gs["key"]
    label = f"{model}"
    if quant:
        label += f" ({quant})"
    return label


def _record_matches_gs(rec, gs):
    """True if one selection record's identifying fields match a group's stats row."""
    key_model, engine, _quant, config_hash, runner_sha = gs["key"]
    if engine.lower() != rec["engine"].lower():
        return False
    if rec.get("config_hash") and config_hash != rec.get("config_hash"):
        return False
    if rec.get("runner_git_sha") and (runner_sha or "").split("+", 1)[0] != rec.get("runner_git_sha"):
        return False
    if rec.get("model"):
        if key_model != rec["model"]:
            return False
    else:
        if not rec.get("model_contains") or rec["model_contains"].lower() not in key_model.lower():
            return False
    return True


def _pick_gs(matches, eligible_keys):
    """Pick exactly one group from the candidate matches: prefer a full-eligible
    (rank_groups' "Best overall") group, else the most recently-run one."""
    eligible_matches = [gs for gs in matches if gs["key"] in eligible_keys]
    if eligible_matches:
        return eligible_matches[0]
    return sorted(matches, key=lambda g: g.get("latest_timestamp") or "")[-1]


def _resolve_one(selector, group_stats, eligible_keys):
    """Resolve a single selector dict (a selection record OR one fragment) to
    exactly one group's stats row, or None when nothing matches. A selector here
    has `engine` plus `model_contains`/`model` and optional config_hash /
    runner_git_sha pins — the same matching rules as a single-fragment record."""
    matches = [gs for gs in group_stats if _record_matches_gs(selector, gs)]
    if not matches:
        return None
    return _pick_gs(matches, eligible_keys)


def _row_group_eligible(gs, rows):
    """Eligibility of ONE leaderboard group by its own real full-suite counts.

    A group is full/eligible exactly when it meets the real full-suite counts
    (the same completeness rule rank_groups applies to a single run: sanity
    present + FULL hermes_ops + FULL coding tasks) AND has zero harness errors
    across its rows. This is the single source of truth for "is this a complete,
    trustworthy benchmark leg?"; both curated multi-fragment combinations
    (_combined_eligible) and explicitly pinned single-fragment selections share
    this same bar.
    """
    complete = bool(
        gs["n_sanity"]
        and gs["n_hermes_ops"] >= _bl.FULL_HERMES_OPS_TASKS
        and gs["n_coding"] >= _bl.FULL_CODING_TASKS
    )
    zero_harness_errors = not any(r.get("harness_error") for r in rows)
    return complete and zero_harness_errors


def _combined_eligible(gs, combined_rows):
    """Eligibility for a CURATED multi-fragment combination.

    A combined group is full/eligible exactly when it clears the SAME bar as a
    real group (_row_group_eligible) on the concatenated rows: real full-suite
    counts (sanity present + FULL hermes_ops + FULL coding tasks) AND zero
    harness errors across all combined rows. This deliberately mirrors the
    leaderboard's completeness gate on the concatenated rows rather than trusting
    each fragment's individual completeness — a fragment may be part of a
    coherent combined run (e.g. one runner leg covering sanity+hermes_ops,
    another covering the coding suites).
    """
    return _row_group_eligible(gs, combined_rows)


def _combine_selection_fragments(rec, group_stats, eligible_keys, groups):
    """Resolve a multi-fragment selection record into ONE curated combined group.

    Resolves each fragment to exactly one group (same matching rules as a single
    record), concatenates their rows into a synthetic group, and computes a
    synthetic group_stats row via build_leaderboard.compute_group_stats on the
    combined rows so its recovered total_runtime_seconds spans all fragments and
    its per-suite/quality numbers reflect the whole 25-row leg.

    A missing fragment is SURFACED (partial/no-match), never silently dropped:
    the record resolves to a partial entry with gs=None and a label naming which
    fragment(s) were not found, and no synthetic group is added.

    Returns a selected-entry dict, sending its synthetic group's rows into
    `groups` (mutated in place) so downstream per-suite / runtime / failure
    charts can read rows for the combined key exactly like a real group.
    """
    resolved = []          # list of (fragment_selector, gs) for matched fragments
    missing = []           # fragment selectors that matched nothing
    for frag in rec["fragments"]:
        selector = {
            "engine": rec["engine"],
            "model": frag.get("model"),
            "model_contains": frag.get("model_contains"),
            "config_hash": frag.get("config_hash"),
            "runner_git_sha": frag.get("runner_git_sha"),
        }
        gs = _resolve_one(selector, group_stats, eligible_keys)
        if gs is None:
            missing.append(selector)
        else:
            resolved.append((selector, gs))

    if missing:
        missing_desc = "; ".join(
            f"runner={_short_sha(f.get('runner_git_sha'))}"
            f"{'/config=' + f.get('config_hash') if f.get('config_hash') else ''}"
            for f in missing
        )
        matched_desc = f"{len(resolved)} of {len(rec['fragments'])}"
        return {
            "family": rec["family"], "engine": rec["engine"], "gs": None,
            "eligible": False, "partial": True, "combined": True,
            "label": (f"{rec['family']}/{rec['engine']} combined — "
                      f"NO MATCH ({matched_desc} fragments resolved; missing: {missing_desc})"),
        }

    # Concatenate the fragment groups' rows into one synthetic group.
    combined_rows = []
    for _selector, gs in resolved:
        combined_rows.extend(groups.get(gs["key"], []))
    shas = [gs["key"][4] for (_s, gs) in resolved]
    # Synthetic key: same model/engine/quant/config as the fragments, but a
    # reserved `curated:` runner sha that cannot collide with a real 12-hex sha,
    # so the combined legs stay distinct from any single-fragment group while the
    # downstream charts can still look up its rows by this key.
    first_key = resolved[0][1]["key"]
    synth_key = (first_key[0], first_key[1], first_key[2], first_key[3],
                 "curated:" + "+".join(shas))
    synthetic_gs = compute_group_stats({synth_key: combined_rows})[0]
    eligible = _combined_eligible(synthetic_gs, combined_rows)
    # Surface the combined rows under the synthetic key so suite heatmap /
    # runtime breakdown / failure taxonomy can read them like any other group.
    groups[synth_key] = combined_rows
    return {
        "family": rec["family"], "engine": rec["engine"],
        "gs": synthetic_gs,
        "eligible": eligible, "partial": not eligible,
        "combined": True, "synthetic": True, "synthetic_eligible": eligible,
        "label": (f"{_group_label(synthetic_gs)} · curated "
                  f"{len(resolved)}-fragment combo"),
        "runner_fragments": [
            {"config_hash": gs["key"][3], "runner_git_sha": gs["key"][4]}
            for (_s, gs) in resolved
        ],
    }


def _short_sha(sha):
    """First 12 chars of a runner sha given (or a placeholder) for provenance text."""
    if not sha:
        return "(none)"
    return sha[:12]


def resolve_selection(records, group_stats, eligible_keys, groups=None):
    """Resolve a curated --selection into a list of selected-group dicts.

    Each output dict has: family, engine, gs (the group_stats row), eligible
    (bool), label. For a single-fragment record we pick one group: exact
    model_match first, else prefer an eligible (full "Best overall") group, else
    the most recent group. For a multi-fragment record (rec["fragments"]) we
    combine the matched fragment groups into one curated synthetic group — see
    _combine_selection_fragments(). Every record yields an entry even if it is
    partial, because a selection explicitly chooses those records; a `partial`
    flag makes that explicit to downstream charts. `groups` (key -> rows) is
    required when any record uses fragments; it is mutated to carry the synthetic
    combined rows.
    """
    selected = []
    for rec in records:
        if rec.get("fragments"):
            if groups is None:
                raise ValueError(
                    "resolve_selection: combining fragments requires the rows map "
                    "(pass `groups`)" + f" for {rec['family']}/{rec['engine']}"
                )
            selected.append(_combine_selection_fragments(rec, group_stats, eligible_keys, groups))
            continue
        gs = _resolve_one(rec, group_stats, eligible_keys)
        if gs is None:
            selected.append({
                "family": rec["family"], "engine": rec["engine"], "gs": None,
                "eligible": False, "partial": True,
                "label": f"{rec['family']}/{rec['engine']} (NO MATCHING GROUP)",
            })
            continue
        in_eligible = gs["key"] in eligible_keys
        pinned_eligible = False
        # An explicitly PINNED single-fragment selection (config_hash and/or
        # runner_git_sha given) is admitted to the headline set on its own merit
        # when its stats clear the same real full-suite + zero-harness-error bar
        # as a combined selection (_row_group_eligible) — even when rank_groups
        # deduplicates this model/engine to a different (older/richer) fragment
        # so its key is not among the vanilla eligible_keys. This never admits a
        # genuinely partial pinned record: full-suite completeness + zero harness
        # errors are still mandatory.
        if not in_eligible and (rec.get("config_hash") or rec.get("runner_git_sha")) \
                and groups is not None:
            pinned_eligible = _row_group_eligible(gs, groups.get(gs["key"], []))
        eligible = in_eligible or pinned_eligible
        selected.append({
            "family": rec["family"], "engine": rec["engine"], "gs": gs,
            "eligible": eligible,
            "partial": not eligible,
            "pinned_eligible": pinned_eligible,
            "label": _group_label(gs),
        })
    return selected


def filter_group_stats(group_stats, models, engines):
    """Apply --models/--engines substring filters (case-insensitive) to group_stats."""
    result = []
    for gs in group_stats:
        model, engine, *_ = gs["key"]
        if models and not any(n in model.lower() for n in models):
            continue
        if engines and not any(n in engine.lower() for n in engines):
            continue
        result.append(gs)
    return result


# --------------------------------------------------------------------------- #
# Pareto efficiency
# --------------------------------------------------------------------------- #
def pareto_efficient(xs, ys):
    """Indices of points that are not dominated on (minimize x, maximize y)."""
    pts = list(zip(xs, ys))
    eff = []
    for i, (x, y) in enumerate(pts):
        dominated = any(
            xj <= x and yj >= y and (xj < x or yj > y)
            for j, (xj, yj) in enumerate(pts) if j != i
        )
        if not dominated:
            eff.append(i)
    return eff


# --------------------------------------------------------------------------- #
# Engine-delta pairing
# --------------------------------------------------------------------------- #
def compute_engine_deltas(selected, score_by_key=None):
    """Pair each family's selected `mei` and `llama.cpp` groups.

    Returns (pairs, skipped). Each pair: {family, mei_gs, llama_gs, mei_engine,
    llama_engine, pass_delta, runtime_hours, runtime_ratio, score_delta}. Skipped
    entries carry a human reason when a family lacks one of the two engine legs.
    score_delta is included when a rank_groups score is available for both legs.
    """
    score_by_key = score_by_key or {}
    by_family = defaultdict(dict)  # family -> engine -> selected dict
    for s in selected:
        if s["gs"] is None:
            continue
        by_family[s["family"]][s["engine"].lower()] = s

    def _find(engines_map, *needles):
        for need in needles:
            for k in engines_map:
                if k == need or k.startswith(need):
                    return engines_map[k]
        return None

    pairs = []
    skipped = []
    for fam in sorted(by_family):
        engines_map = by_family[fam]
        mei = _find(engines_map, "mei")
        llama = _find(engines_map, "llama.cpp")
        if mei is None and llama is None:
            skipped.append({"family": fam, "reason": "neither a mei nor llama.cpp group selected"})
            continue
        if mei is None:
            skipped.append({"family": fam, "reason": "no mei group selected (only llama.cpp)"})
            continue
        if llama is None:
            skipped.append({"family": fam, "reason": "no llama.cpp group selected (only mei)"})
            continue
        mia = combined_pass_rate(mei["gs"])
        lla = combined_pass_rate(llama["gs"])
        mi_hours = total_runtime_hours(mei["gs"])
        ll_hours = total_runtime_hours(llama["gs"])
        mei_score = score_by_key.get(mei["gs"]["key"])
        llama_score = score_by_key.get(llama["gs"]["key"])
        score_delta = None
        if mei_score is not None and llama_score is not None:
            score_delta = mei_score - llama_score
        pair = {
            "family": fam,
            "mei_gs": mei["gs"], "llama_gs": llama["gs"],
            "mei_engine": mei["engine"], "llama_engine": llama["engine"],
            "mei_label": mei["label"], "llama_label": llama["label"],
            "pass_delta": (mia - lla) if (mia is not None and lla is not None) else None,
            "runtime_hours": (mi_hours - ll_hours) if (mi_hours is not None and ll_hours is not None) else None,
            "runtime_ratio": (ll_hours / mi_hours) if (mi_hours and ll_hours) else None,
            "score_delta": score_delta,
            "mei_partial": mei["partial"], "llama_partial": llama["partial"],
        }
        pairs.append(pair)
    return pairs, skipped


# --------------------------------------------------------------------------- #
# Failure taxonomy
# --------------------------------------------------------------------------- #
_FAILURE_CATEGORY_ORDER = ["task_failure", "timeout_stall", "malformed_tool", "harness_error"]
_FAILURE_CATEGORY_LABELS = {
    "task_failure": "model/task failure",
    "timeout_stall": "timeout / stall",
    "malformed_tool": "malformed tool call",
    "harness_error": "harness error",
}


def classify_failure(row):
    """Classify a FAIL row into a taxonomy category, or None if it is a pass.

    Categories (see module docs):
      harness_error  — row flagged harness_error (harness/env crash).
      timeout_stall  — timeout_phase set, stream stall, truncated response, device
                       connection refused, or the coding-suite 3000s deactivation.
      malformed_tool — model called a tool never declared / malformed tool args.
      task_failure   — any other FAIL that is not harness/timeout/malformed-tool.
    """
    if row.get("harness_error"):
        return "harness_error"
    if row.get("pass"):
        return None
    err = " ".join(str(row.get(k) or "") for k in ("run_error", "grade_output"))
    if row.get("timeout_phase") or re.search(
        r"timeout|truncated|stream stalled|no qualifying progress|connection refused|finish_reason=length|3000",
        err, re.IGNORECASE,
    ):
        return "timeout_stall"
    if re.search(r"model called tool|never declared|manifest|malformed|unparseable tool", err, re.IGNORECASE):
        return "malformed_tool"
    return "task_failure"


def failure_taxonomy_counts(rows):
    """Aggregate failure categories over a list of rows.

    Returns (counts_dict, total_failures). counts includes every category with 0
    explicitly present so callers can detect "no variation/meaningful data".
    """
    counts = {c: 0 for c in _FAILURE_CATEGORY_ORDER}
    for r in rows:
        cat = classify_failure(r)
        if cat is not None:
            counts[cat] += 1
    return counts, sum(counts.values())


# --------------------------------------------------------------------------- #
# Rendering helpers
# --------------------------------------------------------------------------- #
def _style_ax(ax, title, xlabel, ylabel=None):
    ax.set_facecolor("white")
    ax.set_title(title, fontsize=12, color=COLOR_TEXT, pad=12, loc="left", fontweight="bold")
    ax.set_xlabel(xlabel, fontsize=9, color=COLOR_TEXT)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=9, color=COLOR_TEXT)
    ax.tick_params(colors=COLOR_TEXT)
    ax.grid(axis="x", color=COLOR_GRID, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(COLOR_GRID)
    ax.spines["left"].set_color(COLOR_GRID)


def _save(fig, output_dir, filename):
    fig.patch.set_facecolor("white")
    out = Path(output_dir) / filename
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    return out


def _engine_colors(engines):
    mapping = {}
    order = sorted({e for e in engines if e})
    for i, e in enumerate(order):
        mapping[e] = ENGINE_COLORS[i % len(ENGINE_COLORS)]
    return mapping


# --------------------------------------------------------------------------- #
# Chart 1: quality vs runtime
# --------------------------------------------------------------------------- #
def render_quality_vs_runtime(gs_list, output_dir, title="Quality vs recovered runtime"):
    """Combined hermes_ops+coding pass rate (y) vs recovered total runtime hours (x).

    Uses eligible groups; skips points with no recoverable runtime or no pass rate.
    """
    pts = []
    for gs in gs_list:
        pr = combined_pass_rate(gs)
        hrs = total_runtime_hours(gs)
        if pr is None or hrs is None:
            continue
        pts.append((gs, pr, hrs))
    if not pts:
        print("SKIP quality_vs_runtime: no group had both a pass rate and recoverable runtime.")
        return None
    if len(pts) < 2:
        print("SKIP quality_vs_runtime: only one usable point (need >=2 to compare).")
        return None

    engines = [gs["key"][1] for gs, *_ in pts]
    colors = _engine_colors(engines)
    xs = [hrs for _gs, _pr, hrs in pts]
    ys = [pr * 100 for _gs, pr, _hrs in pts]
    eff = pareto_efficient(xs, ys)

    fig, ax = plt.subplots(figsize=(11, 6.5), dpi=150)
    for i, ((gs, pr, hrs), c) in enumerate(zip(pts, [colors[e] for e in engines])):
        ax.scatter(hrs, pr * 100, s=90 if i in eff else 55,
                   color=c, alpha=0.95, zorder=3,
                   edgecolor="black" if i in eff else "none", linewidths=1.4)
        # annotate with family/model label (short).
        label = gs["key"][0]
        if len(label) > 34:
            label = label.split("/")[-1] if "/" in label else label[:34]
        ax.annotate(label, (hrs, pr * 100), textcoords="offset points",
                    xytext=(6, 5), fontsize=7.5, color=COLOR_TEXT)

    eff_pts = [pts[i] for i in eff]
    for gs, pr, hrs in eff_pts:
        ax.axvline(hrs, color="#bbbbbb", linewidth=0.6, linestyle=":", zorder=1)
        ax.axhline(pr * 100, color="#bbbbbb", linewidth=0.6, linestyle=":", zorder=1)

    handles = [plt.Line2D([], [], marker="o", ls="", color=colors[e], label=e) for e in sorted(colors)]
    handles.append(plt.Line2D([], [], marker="o", ls="", color="none", markerfacecolor="none",
                              markeredgecolor="black", label="Pareto-efficient (≤ runtime, ≥ quality)"))
    ax.legend(handles=handles, fontsize=8, frameon=False, loc="lower right")

    _style_ax(ax, title, "recovered total runtime (hours, approx)", "combined hermes_ops + coding pass rate (%)")
    ax.grid(axis="y", color=COLOR_GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.set_ylim(-2, 105)
    path = _save(fig, output_dir, "quality_vs_runtime.png")
    print(f"Wrote {path} ({len(pts)} points, {len(eff)} pareto-efficient).")
    return path


# --------------------------------------------------------------------------- #
# Chart 2: engine delta (Mei vs llama.cpp)
# --------------------------------------------------------------------------- #
def render_engine_delta(pairs, output_dir, title="Mei vs llama.cpp engine deltas (per family)"):
    """Dumbbell/slope chart: per family, mark Mei and llama.cpp values for
    pass rate (left) and total runtime hours (right); annotate the delta."""
    usable = [p for p in pairs if p["pass_delta"] is not None and
              (p["runtime_hours"] is not None or p["runtime_ratio"] is not None)]
    if not usable:
        reasons = [p for p in pairs]
        print("SKIP engine_delta: no family had both a pass-rate and runtime delta", reasons)
        return None

    families = [p["family"] for p in usable]
    y = range(len(usable))
    colors = {"mei": "#2a9d8f", "llama.cpp": "#1f6fb2"}

    fig, (axl, axr) = plt.subplots(1, 2, figsize=(13, max(3.2, 0.7 * len(usable) + 1.2)), dpi=150)
    for yi, p in zip(y, usable):
        mi, ll = p["mei_gs"], p["llama_gs"]
        mi_pr = (combined_pass_rate(mi) or 0) * 100
        ll_pr = (combined_pass_rate(ll) or 0) * 100
        mi_h, ll_h = total_runtime_hours(mi), total_runtime_hours(ll)
        suffix = ""
        if p.get("score_delta") is not None:
            suffix = f"  (score {p['score_delta']:+.3f})"
        # left: pass rate dumbbell
        axl.plot([ll_pr, mi_pr], [yi, yi], color="#999999", linewidth=1.6, zorder=1)
        axl.scatter([ll_pr], [yi], s=70, color=colors.get(p["llama_engine"].split("-")[0], "#555555"), zorder=3, label=p["llama_engine"] if yi == 0 else None)
        axl.scatter([mi_pr], [yi], s=70, color=colors.get("mei"), zorder=3, label="mei" if yi == 0 else None)
        axl.annotate(f"{p['pass_delta']:+.0f}pp{suffix}", (mi_pr, yi), textcoords="offset points",
                     xytext=(6, 0), fontsize=7.5, va="center", color=COLOR_TEXT)
        # right: runtime hours dumbbell (or ratio text if hours missing)
        if mi_h is not None and ll_h is not None:
            axr.plot([ll_h, mi_h], [yi, yi], color="#999999", linewidth=1.6, zorder=1)
            axr.scatter([ll_h], [yi], s=70, color=colors.get(p["llama_engine"].split("-")[0], "#555555"), zorder=3)
            axr.scatter([mi_h], [yi], s=70, color=colors.get("mei"), zorder=3)
            axr.annotate(f"{p['runtime_hours']:+.1f}h", (mi_h, yi), textcoords="offset points",
                         xytext=(6, 0), fontsize=8, va="center", color=COLOR_TEXT)
        else:
            axr.scatter([0], [yi], s=70, color="#bbbbbb", zorder=3)
            axr.annotate("n/a", (0, yi), textcoords="offset points", xytext=(6, 0),
                         fontsize=8, va="center", color="#666666")

    axl.set_yticks(list(y))
    axl.set_yticklabels(families, fontsize=8, color=COLOR_TEXT)
    axl.set_xlabel("combined pass rate (%)", fontsize=9, color=COLOR_TEXT)
    axr.set_yticks(list(y))
    axr.set_yticklabels(["" for _ in y])
    axr.set_xlabel("total runtime (hours, approx)", fontsize=9, color=COLOR_TEXT)
    axr.set_xlim(-1, max([0.5] + [p["runtime_hours"] and abs(p["runtime_hours"]) + 1 or 0.5 for p in usable]))
    axl.grid(axis="x", color=COLOR_GRID, linewidth=0.6)
    axr.grid(axis="x", color=COLOR_GRID, linewidth=0.6)
    fig.suptitle(title, fontsize=12, fontweight="bold", x=0.0, ha="left", color=COLOR_TEXT)
    axl.legend(loc="upper right", fontsize=8, frameon=False)
    path = _save(fig, output_dir, "engine_delta.png")
    print(f"Wrote {path} ({len(usable)} families).")
    return path


# --------------------------------------------------------------------------- #
# Chart 3: suite heatmap
# --------------------------------------------------------------------------- #
def _render_suite_heatmap_matrix(matrix, output_dir, suites, title="Pass rate by suite"):
    """matrix: list of dicts {label, row: {suite: pass_rate_or_None}}. Non-None
    cells are pass[%]; None cells are masked and labeled '—'."""
    if not matrix or not suites:
        print("SKIP suite_heatmap: no group/suite data.")
        return None
    rows = len(matrix)
    cols = len(suites)
    data = [[None] * cols for _ in range(rows)]
    for i, entry in enumerate(matrix):
        for j, s in enumerate(suites):
            data[i][j] = entry["row"].get(s)

    fig, ax = plt.subplots(figsize=(max(7, 1.4 * cols), max(3, 0.55 * rows)), dpi=150)
    import numpy as np
    arr = np.zeros((rows, cols), dtype=float)
    mask = np.zeros((rows, cols), dtype=bool)
    for i in range(rows):
        for j in range(cols):
            v = data[i][j]
            if v is not None:
                arr[i, j] = v
            else:
                mask[i, j] = True
    cmap = plt.get_cmap("Blues")
    im = ax.imshow(np.ma.masked_array(arr, mask=mask), cmap=cmap, vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(range(cols))
    ax.set_xticklabels(suites, fontsize=8, rotation=30, ha="right", color=COLOR_TEXT)
    ax.set_yticks(range(rows))
    ax.set_yticklabels([m["label"] for m in matrix], fontsize=7.5, color=COLOR_TEXT)
    ax.grid(False)
    for i in range(rows):
        for j in range(cols):
            v = data[i][j]
            if v is None:
                ax.text(j, i, "—", ha="center", va="center", fontsize=8, color="#999999")
            else:
                ax.text(j, i, f"{v:.0f}%", ha="center", va="center", fontsize=8,
                        color="white" if v > 55 else COLOR_TEXT)
    ax.set_title(title, fontsize=12, color=COLOR_TEXT, loc="left", pad=12, fontweight="bold")
    fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02, label="pass rate (%)")
    path = _save(fig, output_dir, "suite_heatmap.png")
    print(f"Wrote {path} ({rows} groups x {cols} suites).")
    return path


def _group_suite_matrix(rows_by_key, selected, suites_order=None):
    """Build the heatmap matrix (list of {label, row}) from selected groups and a
    key->rows map, computing pass rate per suite excluding harness_error rows."""
    suites_order = suites_order or SUITES_ORDER
    present = set()
    for key, rows in rows_by_key.items():
        for r in rows:
            present.add(r["suite"])
    ordered = list(suites_order) + sorted(present - set(suites_order))

    matrix = []
    for s in selected:
        if s["gs"] is None:
            continue
        key = s["gs"]["key"]
        rows = rows_by_key.get(key, [])
        row_map = {}
        for suite in ordered:
            suite_rows = [r for r in rows if r["suite"] == suite and not r.get("harness_error")]
            if not suite_rows:
                row_map[suite] = None
            else:
                n_pass = sum(1 for r in suite_rows if r.get("pass"))
                row_map[suite] = 100.0 * n_pass / len(suite_rows)
        label = s["label"] + (" (partial)" if s.get("partial") else "")
        matrix.append({"label": label, "row": row_map})
    return matrix, ordered


# --------------------------------------------------------------------------- #
# Chart 4: runtime breakdown
# --------------------------------------------------------------------------- #
def render_runtime_breakdown(rows_by_key, selected, output_dir, suites_order=None,
                             title="Task wall-time by suite (not recovered elapsed runtime)"):
    """Stacked horizontal bars: per selected group, the sum of per-task wall_seconds
    across each suite. Explicitly labeled as task wall-time, distinct from the
    recovered headline total runtime (which remains the quality_vs_runtime x-axis)."""
    suites_order = suites_order or SUITES_ORDER
    present = {r["suite"] for rows in rows_by_key.values() for r in rows}
    ordered = list(suites_order) + sorted(present - set(suites_order))
    entries = []
    for s in selected:
        if s["gs"] is None:
            continue
        key = s["gs"]["key"]
        rows = [r for r in rows_by_key.get(key, []) if not r.get("harness_error")]
        if not rows:
            continue
        totals = {suite: sum(float(r.get("wall_seconds") or 0) for r in rows if r["suite"] == suite)
                  for suite in ordered}
        if all(v == 0 for v in totals.values()):
            continue
        entries.append({"label": s["label"] + (" (partial)" if s.get("partial") else ""), "totals": totals})
    if not entries:
        print("SKIP runtime_breakdown: no selected group with task wall-time data.")
        return None

    entries = list(reversed(entries))
    labels = [e["label"] for e in entries]
    used_colors = [plt.get_cmap("tab10")(i % 10) for i in range(len(ordered))]

    fig, ax = plt.subplots(figsize=(11, max(3, 0.62 * len(entries) + 0.8)), dpi=150)
    bottom = [0.0] * len(entries)
    for k, suite in enumerate(ordered):
        vals = [e["totals"][suite] if suite in e["totals"] else 0 for e in entries]
        ax.barh(labels, vals, left=bottom, height=0.62, color=used_colors[k],
                label=suite, edgecolor="none")
        bottom = [b + v for b, v in zip(bottom, vals)]
    for i, (e, b) in enumerate(zip(entries, bottom)):
        if b:
            ax.text(b, i, f" {b/3600:.1f}h", va="center", ha="left", fontsize=7.5, color=COLOR_TEXT)
    ax.set_title(title, fontsize=11, color=COLOR_TEXT, loc="left", pad=12, fontweight="bold")
    ax.set_xlabel("sum of task wall_seconds (hours) — task wall-time, NOT recovered elapsed runtime", fontsize=9, color=COLOR_TEXT)
    ax.legend(fontsize=8, frameon=False, loc="lower right")
    ax.tick_params(axis="y", labelsize=8, colors=COLOR_TEXT)
    ax.tick_params(axis="x", labelsize=8, colors=COLOR_TEXT)
    ax.grid(axis="x", color=COLOR_GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(COLOR_GRID)
    ax.spines["left"].set_color(COLOR_GRID)
    path = _save(fig, output_dir, "runtime_breakdown.png")
    print(f"Wrote {path} ({len(entries)} groups).")
    return path


# --------------------------------------------------------------------------- #
# Chart 5: failure taxonomy
# --------------------------------------------------------------------------- #
def render_failure_taxonomy(counts, total, output_dir, title="Failure taxonomy"):
    """Bar chart of failure categories. Only called when the caller has decided
    the data is meaningful AND varied (see _should_render_taxonomy)."""
    cats = [c for c in _FAILURE_CATEGORY_ORDER if counts[c] > 0]
    xs = range(len(cats))
    vals = [counts[c] for c in cats]
    labels = [_FAILURE_CATEGORY_LABELS[c] for c in cats]
    colors = ["#d64550", "#c8792a", "#a855f7", "#7a7a52"]

    fig, ax = plt.subplots(figsize=(8.5, 4.6), dpi=150)
    bars = ax.bar(list(xs), vals, color=[colors[_FAILURE_CATEGORY_ORDER.index(c)] for c in cats], edgecolor="none")
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.3, str(v),
                ha="center", va="bottom", fontsize=10, color=COLOR_TEXT)
    ax.set_xticks(list(xs))
    ax.set_xticklabels(labels, fontsize=9, color=COLOR_TEXT)
    ax.set_title(title, fontsize=12, color=COLOR_TEXT, loc="left", pad=12, fontweight="bold")
    ax.set_ylabel("rows", fontsize=9, color=COLOR_TEXT)
    ax.tick_params(axis="y", colors=COLOR_TEXT)
    ax.grid(axis="y", color=COLOR_GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(COLOR_GRID)
    ax.spines["left"].set_color(COLOR_GRID)
    path = _save(fig, output_dir, "failure_taxonomy.png")
    print(f"Wrote {path} (total {total} failure rows across {len(cats)} categories).")
    return path


def should_render_taxonomy(counts, total):
    """True only when failures are meaningful AND varied.

    Meaningful: at least one failure row. Varied: more than one distinct category
    present — a chart of a single homogeneous category (e.g. only harness errors,
    or a group that is all-pass) would be a misleading flat 1-bar / blank image.
    """
    if total <= 0:
        return False
    nonzero = [c for c in _FAILURE_CATEGORY_ORDER if counts[c] > 0]
    return len(nonzero) >= 2


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #
def build(log_path=None, output_dir=None, models=None, engines=None, selection_path=None,
          only_eligible=True):
    """Run the whole pipeline from a log path to a set of PNGs.

    Returns a dict summarizing what was written/skipped and the selected groups,
    so the caller (and tests) can assert on the outcome without parsing stdout.
    """
    log_path = Path(log_path) if log_path else (REPO / "results" / "log.jsonl")
    output_dir = Path(output_dir) if output_dir else (REPO / "results")

    rows = load_rows(log_path)
    groups = group_rows(rows)
    group_stats = compute_group_stats(groups)
    ranked = rank_groups(group_stats)
    eligible_keys = {gs["key"] for (_g, _s, gs) in ranked}
    score_by_key = {gs["key"]: score for (_g, score, gs) in ranked}

    # Determine the working set of groups.
    if selection_path:
        records = load_selection(selection_path)
        selected = resolve_selection(records, group_stats, eligible_keys, groups)
    else:
        working = filter_group_stats(group_stats, models, engines)
        if only_eligible:
            working = [gs for gs in working if gs["key"] in eligible_keys]
        selected = [
            {"family": gs["key"][0], "engine": gs["key"][1], "gs": gs,
             "eligible": gs["key"] in eligible_keys, "partial": gs["key"] not in eligible_keys,
             "label": _group_label(gs)}
            for gs in working
        ]

    # Headline charts use full-eligible groups: the leaderboard's "Best overall"
    # set (keys present in eligible_keys) PLUS curated synthetic multi-fragment
    # combinations that met the full-suite + zero-harness-error bar (their curated
    # synthetic key is by definition not in the original eligible_keys, so they
    # are marked in via `synthetic_eligible`) PLUS explicitly pinned single-fragment
    # selections that met that same real bar on their own rows (marked in via
    # `pinned_eligible`). Genuinely partial pinned records stay out.
    headline = [s for s in selected if s["gs"] is not None and (
        s["gs"]["key"] in eligible_keys
        or s.get("synthetic_eligible") or s.get("pinned_eligible"))]

    output = {"written": {}, "skipped": [], "selected": selected, "ranked": ranked}

    # Ch1: quality vs runtime — headline eligible groups.
    output["written"]["quality_vs_runtime"] = render_quality_vs_runtime(
        [s["gs"] for s in headline], output_dir)

    # Ch2: engine delta.
    pairs, skipped = compute_engine_deltas(selected, score_by_key)
    output["engine_delta_skipped"] = skipped
    output["written"]["engine_delta"] = render_engine_delta(pairs, output_dir)

    # Ch3: suite heatmap + Ch4: runtime breakdown use selected complete groups.
    matrix, suites = _group_suite_matrix(groups, selected, SUITES_ORDER)
    output["written"]["suite_heatmap"] = _render_suite_heatmap_matrix(matrix, output_dir, suites)
    output["written"]["runtime_breakdown"] = render_runtime_breakdown(groups, selected, output_dir)

    # Ch5: failure taxonomy over selected groups' rows.
    fail_rows = []
    for s in selected:
        if s["gs"] is None:
            continue
        fail_rows.extend(groups.get(s["gs"]["key"], []))
    counts, total = failure_taxonomy_counts(fail_rows)
    if should_render_taxonomy(counts, total):
        output["written"]["failure_taxonomy"] = render_failure_taxonomy(counts, total, output_dir)
    else:
        reason = "no failure rows" if total == 0 else f"not varied (only categories present: " \
                 f"{[c for c in _FAILURE_CATEGORY_ORDER if counts[c] > 0]})"
        print(f"SKIP failure_taxonomy: {reason} ({total} failure rows total over selected groups).")
        output["skipped"].append("failure_taxonomy: " + reason)

    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--log", type=str, default=str(REPO / "results" / "log.jsonl"),
                        help="Path to results/log.jsonl (default: results/log.jsonl)")
    parser.add_argument("--output-dir", type=str, default=str(REPO / "results"),
                        help="Directory to write PNGs (default: results/)")
    parser.add_argument("--models", type=str, default=None,
                        help="Comma-separated case-insensitive model substring filters.")
    parser.add_argument("--engines", type=str, default=None,
                        help="Comma-separated engine substring filters (e.g. 'mei,llama.cpp').")
    parser.add_argument("--selection", type=str, default=None,
                        help="Path to a --selection JSON file (documented in module docstring).")
    parser.add_argument("--all", action="store_true",
                        help="Include non-eligible (partial) groups in headline charts too.")
    args = parser.parse_args()

    models = [m.strip().lower() for m in args.models.split(",")] if args.models else None
    engines = [e.strip().lower() for e in args.engines.split(",")] if args.engines else None
    if args.models and not models:
        models = None
    if args.engines and not engines:
        engines = None

    out = build(
        log_path=args.log,
        output_dir=args.output_dir,
        models=models,
        engines=engines,
        selection_path=args.selection,
        only_eligible=not args.all,
    )
    written = {k: str(v) for k, v in out["written"].items() if v}
    print("Charts written:", written or "(none)")
    print("Skipped:", out["skipped"] or "(none)")


if __name__ == "__main__":
    main()