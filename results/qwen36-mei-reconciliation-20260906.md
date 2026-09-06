# Qwen3.6-35B Mei benchmark — reconciliation of split fragments (logical run)

- Date: 2026-09-06
- Model / artifact: `mlx-community/Qwen3.6-35B-A3B-4bit`
- Engine: `mei`
- Config path: `configs/Qwen3.6-35B-A3B/mei.yaml`
- Config hash: `cea524483faf` (matches `results/configs/cea524483faf.yaml` snapshot and the committed config verbatim)
- Inference engine: `mei` · port 8024 (shared with Ornith — never concurrent)
- Source revision / build provenance:
  - `source_revision`: `38740b847e4cb78f352aba30aa41c76e08e6eb46` (mlx-community HF commit; config_sha256 `a822a9e8…`)
  - `mei_commit`: `91fed8be21319f92ce5220622c6dcde0b851bdae` (vmlx-swift Package.resolved pin)
  - `mei_source_commit`: `67e897e2160d80be65d2e2c2ff15746d4130ad72` (Mei streaming multi-tool-call SSE-index fix 2026-09-05; verified build at `mei-build-67e897e`)
  - `model_bytes`: `20402204728` (MLX 4-bit affine g64, 8-bit router gates; qwen3_5_moe conditional-generation/VLM — text/tool path only)

## Purpose

This document reconciles ONE logical Qwen3.6-35B Mei benchmark run that spans
three `runner_git_sha` values in `results/log.jsonl`. The split is due to git
HEAD moving while the background run was executing (three results-commits
landed mid-run), NOT to a config change or to incompatible grading semantics:
every row shares the same `config_hash` (`cea524483faf`) and the same harness
code path. The raw append-only rows are **not** modified; this is a reporting
view only.

The run was **interrupted by a single `harness_error: true` row**, so this
logical run is **NOT full-eligible / NOT headline-admissible** until that row
is replaced by a clean rerun. It must not be presented as a complete,
comparable Mei leg.

> Note: the interrupted first attempt (config_hash `e9d6db1b6675`, runner
> `39dae7a6ea44`, 2 sanity rows only) is a SEPARATE attempt and is documented
> in `results/qwen36-mei-interrupted-20260906.md`. It is NOT part of this
> logical run, which uses only the current-config `cea524483faf` rows.

## Fragment table (current-config `cea524483faf`, 25 rows)

| runner_git_sha | rows | suites | pass | model-level fail (harness_error=false) | harness_error=true |
|---|---|---|---|---|---|
| `de1d34279681` | 15 | 2 sanity + 8 hermes_ops + 5 kiem_mini | 14 | `hermes_ops-multi-step-chain` (exceeded max_turns 40) | 0 |
| `e5e8e82cdeb9` | 4 | 3 hearth_mini + 1 kipclip_mini | 3 | 0 | `hearth_mini-feature` |
| `6a6d9f534804` | 6 | 3 kipclip_mini + 3 hearth_full | 5 | `kipclip_mini-merge` | 0 |
| **combined** | **25** | 2 sanity + 8 hermes_ops + 15 coding | **22** | **2** | **1** |

## Derivations audit

- **Combined rows: 25**, fully matching the configured suite shape
  (2 sanity + 8 hermes_ops + `kiem_mini`5 + `hearth_mini`3 + `kipclip_mini`4 +
  `hearth_full`3 = 15 coding).
- Per-suite: sanity 2/2 pass; hermes_ops 7/8; kiem_mini 5/5; hearth_mini 2/3;
  kipclip_mini 3/4; hearth_full 3/3. Overall **22/25 pass**.
- Recovered runtime span (first→last row timestamp):
  `2026-09-06T11:58:52Z` → `13:48:48Z`; recovered `total_runtime_seconds`
  ≈ **6602.4 s** (~1 h 50 m) across all fragments.
- **Failures classified:**
  - `hermes_ops-multi-step-chain` — model-level (exceeded max_turns 40),
    `harness_error=false`.
  - `kipclip_mini-merge` — model-level, `harness_error=false`.
  - `hearth_mini-feature` — **`harness_error=true`** (the runner classified it
    as a harness/setup failure; `within_budget=false`, `wall_seconds=544.7`,
    `hermes_turns=20`). THIS is the eligibility blocker.

## Why this logical run is NOT full-eligible / headline-admissible

When combined via the existing `fragments` selection schema in
`runner/build_summary_charts.py`, the group resolves to **partial** and is
**not** admitted to the headline charts (`synthetic_eligible == false`), because
eligibility requires real full-suite coverage **AND zero `harness_error` rows**
across the combined rows, and the combined `hearth_mini-feature` row is
`harness_error=true`. No change to reporting silently promotes this run.

The entry becomes full-eligible only after the `hearth_mini-feature`
`harness_error` row is replaced by a clean rerun of that task (same config
hash / same-methodology harness) such that the combined leg has zero harness
errors. Until then this is an **exploratory partial** result and must be labeled
as such; it carries the vision-language scope caveat (text/tool path only) from
the config's `known_gaps`.

## Reproduction of the combined view

A standalone selection manifest for the chart tool (does NOT modify the
global `results/summary_selection.json`):

    uv run --locked python runner/build_summary_charts.py \
      --selection results/qwen36-mei-selection.json --output-dir /tmp/qwen36-mei

The fragments record is:

    {
      "family": "Qwen3.6-35B-A3B", "engine": "mei",
      "fragments": [
        {"model_contains": "mlx-community/Qwen3.6-35B-A3B-4bit",
         "config_hash": "cea524483faf", "runner_git_sha": "de1d34279681"},
        {"model_contains": "mlx-community/Qwen3.6-35B-A3B-4bit",
         "config_hash": "cea524483faf", "runner_git_sha": "e5e8e82cdeb9"},
        {"model_contains": "mlx-community/Qwen3.6-35B-A3B-4bit",
         "config_hash": "cea524483faf", "runner_git_sha": "6a6d9f534804"}
      ]
    }

All three fragments resolve; the combined group is labelled partial
(`synthetic_eligible=false`) because of the `hearth_mini-feature` harness error.