#!/usr/bin/env python3
"""Precise, reproducible quant-ledger audit for the kiem_mini-testwrite task.

The quantisation conclusions in results/SUMMARY.md rest on exact pass/total
counts drawn from the append-only results/log.jsonl (the ledger). This script
derives those counts mechanically and verifies them against pinned
expectations, so an aggregate like "4/69" can only stay in the summary while
it still reproduces from the raw log.

Scope of every number below: suite == "kiem_mini", task_id ==
"kiem_mini-testwrite", counted over ALL config hashes / runner SHAs / reruns
("all time"). `pass` is the row's boolean grade field (NOT `passed`).

Usage:
    uv run --locked python runner/quant_ledger_audit.py            # print ledger
    uv run --locked python runner/quant_ledger_audit.py --check     # exit 1 on drift
    uv run --locked python runner/quant_ledger_audit.py --json      # machine-readable

`--check` compares the live derivation against PINNED_EXPECTATIONS below.
If a future run adds rows, the check fails loudly and the pins (and any
SUMMARY.md aggregate they back) must be updated deliberately — the audit is
the reproducible gate that keeps the summary's numbers honest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LOG_PATH = REPO / "results" / "log.jsonl"

TASK_ID = "kiem_mini-testwrite"
SUITE = "kiem_mini"


def load_rows(log_path: Path) -> list[dict]:
    rows = []
    with open(log_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def testwrite_rows(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r.get("suite") == SUITE and r.get("task_id") == TASK_ID]


def group_by_model(rows: list[dict]) -> dict[tuple[str, str], list[dict]]:
    groups: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        key = (str(r.get("model")), str(r.get("inference_engine")))
        groups.setdefault(key, []).append(r)
    return groups


def tally(grp: list[dict]) -> dict:
    return {
        "passes": sum(1 for r in grp if r.get("pass") is True),
        "total": len(grp),
        "harness_errors": sum(1 for r in grp if r.get("harness_error")),
    }


def scope_rows(rows: list[dict], members: set[str], engine: str = "mei") -> list[dict]:
    """Rows inside an explicitly-enumerated membership set (quant scope)."""
    return [r for r in rows if r.get("inference_engine") == engine and str(r.get("model")) in members]


# ---------------------------------------------------------------------------
# Frozen scope definitions, 2026-09-13 (commit 7fb38d3 log.jsonl).
#
# MLX_UNIFORM_4BIT is the exact membership behind SUMMARY.md's "every MLX
# model, all time = 4/69": every config-declared *uniform 4-bit affine g64*
# Mei model. Mixed-precision legs are deliberately excluded even though they
# are also MLX/Mei: DWQ (mixed 4/8, 0/3), EigenLabs mixed46 (mixed 4/6, 1/13)
# and Qwen3.5-9B-8bit (uniform 8-bit, 0/3). The label "every MLX model"
# without that qualifier overstates the scope, which is what this audit pins.
# ---------------------------------------------------------------------------
MLX_UNIFORM_4BIT = {
    "ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit",                       # 0/40
    "orcarouter/Qwen3.8-27B-Uncensored-MLX (subdir 4-bit)",        # 1/2
    "mlx-community/gemma-4-26b-a4b-it-4bit",                       # 0/1
    "mlx-community/Qwen3.8-27B-4bit",                              # 1/1
    "mlx-community/Qwen3.6-35B-A3B-4bit",                          # 1/14
    "Tostibrown/Qwen3.6-35B-A3B-4bit-textonly",                    # 1/10
    "mlx-community/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-4bit",    # 0/1
}

# Per-(model, engine) pins cited directly by SUMMARY.md's quantisation table.
PINNED_GROUPS = {
    ("mlx-community/Qwen3.6-35B-A3B-4bit", "mei"): (1, 14),                    # stock MLX
    ("Tostibrown/Qwen3.6-35B-A3B-4bit-textonly", "mei"): (1, 10),              # text-only MLX
    ("EigenLabs/Qwen3.6-35B-A3B-MLX-mixed-4bit", "mei"): (1, 13),              # mixed46 MLX
    ("mlx-community/Qwen3.6-35B-A3B-4bit-DWQ", "mei"): (0, 3),                 # DWQ MLX
    ("mlx-community/Qwen3.5-9B-8bit", "mei"): (0, 3),                          # 9B 8-bit MLX
    ("ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit", "mei"): (0, 40),                 # Ornith MLX
    ("ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M", "llama.cpp"): (2, 6),         # Ornith GGUF arm
    ("bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0", "llama.cpp"): (3, 3),              # 9B GGUF arm
}

# Aggregate pins: (passes, total).
PINNED_AGGREGATES = {
    "mlx_uniform_4bit": (4, 69),   # qualifies the SUMMARY.md "4/69" aggregate
    "all_mei": (5, 88),            # every Mei row, any quant, all time
}


def derive(rows: list[dict]) -> dict:
    tw = testwrite_rows(rows)
    groups = group_by_model(tw)
    group_rows = {k: g for k, g in sorted(groups.items())}
    per_group: dict[str, dict] = {f"{m} | {e}": tally(g) for (m, e), g in group_rows.items()}
    four_bit = scope_rows(tw, MLX_UNIFORM_4BIT)
    returns = {
        "log_rows": len(rows),
        "testwrite_rows": len(tw),
        "per_group": per_group,
        "aggregates": {
            "mlx_uniform_4bit": tally(four_bit),
            "all_mei": tally([r for r in tw if r.get("inference_engine") == "mei"]),
        },
    }
    return returns


def check_pins(derived: dict) -> list[str]:
    problems = []
    per_group = {tuple(k.split(" | ")): v for k, v in derived["per_group"].items()}
    for key, (p, n) in PINNED_GROUPS.items():
        got = per_group.get(key, {"passes": None, "total": None})
        if got["passes"] != p or got["total"] != n:
            problems.append(
                f"GROUP {key[0]} | {key[1]}: pinned {p}/{n}, derived {got['passes']}/{got['total']}"
            )
    for name, (p, n) in PINNED_AGGREGATES.items():
        got = derived["aggregates"][name]
        if got["passes"] != p or got["total"] != n:
            problems.append(
                f"AGGREGATE {name}: pinned {p}/{n}, derived {got['passes']}/{got['total']}"
            )
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="fail (exit 1) if the ledger drifts from the pins")
    ap.add_argument("--json", action="store_true", help="emit the derived ledger as JSON")
    args = ap.parse_args()

    rows = load_rows(LOG_PATH)
    derived = derive(rows)
    blob = LOG_PATH.read_bytes()
    derived["log_sha256"] = hashlib.sha256(blob).hexdigest()

    if args.json:
        print(json.dumps(derived, indent=1, sort_keys=True))
        return 0

    print(f"quant-ledger audit — {TASK_ID} (all time, append-only {LOG_PATH.name})")
    print(f"log rows: {derived['log_rows']}; testwrite rows: {derived['testwrite_rows']}")
    print(f"log.jsonl sha256: {derived['log_sha256']}")
    print()
    print("per (model | engine):")
    for key, t in derived["per_group"].items():
        mark = ""
        if t["harness_errors"]:
            mark = f"  (harness_error rows: {t['harness_errors']})"
        print(f"  {t['passes']}/{t['total']}  {key}{mark}")
    print()
    print("aggregates:")
    for name, t in derived["aggregates"].items():
        print(f"  {name}: {t['passes']}/{t['total']}")

    problems = check_pins(derived)
    if problems:
        print()
        print("DRIFT vs pinned expectations (update pins deliberately):")
        for p in problems:
            print(f"  - {p}")
        return 1
    print()
    print("OK: ledger reproduces every pinned count (including SUMMARY.md's 4/69 scope).")
    return 0


if __name__ == "__main__":
    sys.exit(main())