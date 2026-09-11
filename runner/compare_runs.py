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
UNSTABLE = {
    "kipclip_mini-merge",    # 2/2 pairs
    "hearth_full-feature",   # 2/2 pairs
    "kiem_mini-parse-note",  # 1/2 pairs
    "hearth_mini-feature",   # 1/2 pairs
}


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
    stable = [t for t in common if t not in UNSTABLE]
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

    print(f"\nUNSTABLE, NOT SCORED ({len(UNSTABLE & set(common))}):")
    for t in sorted(UNSTABLE & set(common)):
        print(f"   {t:30s} A={a[t]['pass']} B={b[t]['pass']}")

    print("\nWall time is deliberately not compared: it swung 31% (35.8 -> 46.9 min)")
    print("between two runs of an identical config. Use runner/analyze_request_log.py")
    print("for per-turn prefill and server gap, which reproduce across pairs.")


if __name__ == "__main__":
    main()
