#!/usr/bin/env python3
"""Compare two benchmark runs the way this suite's noise actually allows.

Why this exists. Two same-config repeat pairs were measured on 2026-09-11 and
both showed the SAME shape:

  * 3 of 25 tasks flip pass<->fail between runs of an identical config+build
  * the flips come from only four tasks, two of them chronically
  * the 10 token-recorded tasks (hermes_ops + sanity) never varied: 0/10, twice
  * wall time swung 35.8 -> 46.9 min, 31%, on nothing but run-to-run variation

So a raw "23/25 vs 20/25" comparison mostly measures noise, and comparing wall
between builds measures almost nothing. This script reports the comparison over
the stable tasks, lists the known-unstable ones separately instead of scoring
them, and deliberately does not compare wall at all.

usage:
  compare_runs.py <config-a.yaml> <config-b.yaml> [--index-a N] [--index-b N]

Indices select which run of that config (0 = first, -1 = last, the default).
"""
import argparse
import json
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Flipped under an IDENTICAL config in at least one measured repeat pair.
# A pass/fail change on one of these is not evidence about a build.
# Tasks that flip between runs of an IDENTICAL config. Measured per model:
# applying one model's list to another assumes they fail in the same places,
# and they do not. Ornith's floor is 3 of 25; Qwen3.6 vision's is 5 of 25 and
# includes two hermes_ops tasks Ornith never varies on.
UNSTABLE_BY_MODEL = {
    "Ornith-1.5-35B-A3B": {
        "kipclip_mini-merge",      # 2 of 2 pairs
        "hearth_full-feature",     # 2 of 2
        "kiem_mini-parse-note",    # 1 of 2
        "hearth_mini-feature",     # 1 of 2
        "kiem_mini-debug",         # added after a third pair
        "kiem_mini-rename",        # added after a third pair
    },
    # Measured over three same-config coding runs: 5, 4 and 3 flips per pair.
    # Each of these flipped in 2 of the 3 pairs. Only two of them
    # (kipclip_mini-merge, kiem_mini-parse-note) are also unstable on Ornith,
    # which is why one model's list must never be applied to another.
    "Qwen3.6-35B-A3B": {
        "hermes_ops-multi-step-chain",
        "hermes_ops-persistent-failure",
        "kiem_mini-feature",
        "kiem_mini-parse-note",
        "kipclip_mini-merge",
        "kipclip_mini-testwrite",
        # added after measuring the ANCHORS arm too: a set derived from one
        # arm only under-counts, which made two pairs look like a -2 cost
        "kiem_mini-debug",
        "hearth_full-feature",
    },
}


def unstable_for(config_path):
    """The measured list for this model, or None if nobody measured one.

    Matches the config's parent DIRECTORY exactly. A substring match silently
    scored Qwen3.6-35B-A3B-textonly with the vision model's list, because one
    name contains the other — the same class of error this per-model table
    exists to prevent.
    """
    model = Path(config_path).parent.name
    return UNSTABLE_BY_MODEL.get(model)


def load_runs(suffix):
    """Every complete 25-task run of one config, oldest first."""
    rows = [json.loads(l) for l in (REPO / "results" / "log.jsonl").open() if l.strip()]
    rs = [r for r in rows if (r.get("config_path") or "").endswith(suffix)]
    rs.sort(key=lambda r: r["timestamp"])
    out, cur = [], None
    for r in rs:
        if r["task_id"] == "sanity-basic":
            cur = {}
            out.append(cur)
        if cur is not None:
            cur[r["task_id"]] = r
    return [x for x in out if len(x) == 25]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config_a")
    ap.add_argument("config_b")
    ap.add_argument("--index-a", type=int, default=-1)
    ap.add_argument("--index-b", type=int, default=-1)
    args = ap.parse_args()

    ra, rb = load_runs(Path(args.config_a).name), load_runs(Path(args.config_b).name)
    for label, runs in ((args.config_a, ra), (args.config_b, rb)):
        if not runs:
            raise SystemExit(f"no complete 25-task run found for {label}")
    a, b = ra[args.index_a], rb[args.index_b]

    common = sorted(set(a) & set(b))
    unstable = unstable_for(args.config_a)
    if unstable is None:
        print("WARNING: no same-config noise floor has been measured for this "
              "model, so every task is scored. A delta here may be noise.")
        unstable = set()
    stable = [t for t in common if t not in unstable]
    pa = sum(1 for t in stable if a[t]["pass"])
    pb = sum(1 for t in stable if b[t]["pass"])

    print(f"A: {args.config_a}  (run {args.index_a} of {len(ra)})")
    print(f"B: {args.config_b}  (run {args.index_b} of {len(rb)})")
    print(f"\nSTABLE TASKS ({len(stable)} of {len(common)}): A {pa}/{len(stable)}"
          f"   B {pb}/{len(stable)}   delta {pb - pa:+d}")

    diffs = [t for t in stable if a[t]["pass"] != b[t]["pass"]]
    for t in diffs:
        print(f"   {t:30s} A={a[t]['pass']} B={b[t]['pass']}")
    if not diffs:
        print("   (no differences on stable tasks)")

    # Token counts only exist for the prompt suite, and only there do they mean
    # anything: comparing a null to a null is not agreement.
    tok = [t for t in common if a[t].get("completion_tokens") is not None]
    td = [t for t in tok if a[t]["completion_tokens"] != b[t]["completion_tokens"]]
    print(f"\nTOKEN-RECORDED TASKS ({len(tok)}): {len(td)} differ")
    if td:
        print("   generation genuinely changed on:", ", ".join(td))
        print("   (these tasks never varied across same-config repeats,")
        print("    so a difference here is attributable to the change under test)")

    print(f"\nUNSTABLE, NOT SCORED ({len(unstable & set(common))}):")
    for t in sorted(unstable & set(common)):
        print(f"   {t:30s} A={a[t]['pass']} B={b[t]['pass']}")

    print("\nWall time is deliberately not compared: it swung 31% (35.8 -> 46.9 min)")
    print("between two runs of an identical config. Use runner/analyze_request_log.py")
    print("for per-turn prefill and server gap, which reproduce across pairs.")


if __name__ == "__main__":
    main()
