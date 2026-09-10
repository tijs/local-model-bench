#!/usr/bin/env python3
"""Diff the STORE and RESTORE cache fingerprints from VMLX_FIDELITY_TRACE=1.

vmlx prints one line per persisted tensor at two points: when a stable
boundary snapshot is taken, and again once a disk payload has been restored
into a live cache. Both are produced by serializing the cache the same way, so
the two sets are directly comparable.

The question this answers: restoring the cross-conversation anchor changes
greedy output on a 20,406-token prompt while a self-restore 27 tokens later is
byte-identical. If the tensors match here, the round-trip is faithful and the
divergence must come from what happens after it. If they differ, the tensor
names say which layer kind is at fault -- mamba_* for the 30 recurrent layers,
kv_*/rotating for the 10 attention ones.

Usage: diff_cache_fingerprints.py <server.log> [--store-label L] [--restore-label L]
"""
from __future__ import annotations

import argparse
import re
import sys

LINE = re.compile(
    r"\[vmlx\]\[fidelity\] (?P<name>\S+) (?P<shape>\S+) (?P<dtype>\S+) "
    r"sum=(?P<sum>\S+) absmax=(?P<absmax>\S+)")
HEADER = re.compile(r"\[vmlx\]\[fidelity\] === (?P<label>.+?) \((?P<n>\d+) tensors\) ===")


def parse(path):
    """Return [(label, {name: (shape, dtype, sum, absmax)})] in file order."""
    blocks, cur, label = [], None, None
    with open(path, errors="replace") as fh:
        for line in fh:
            h = HEADER.search(line)
            if h:
                if cur is not None:
                    blocks.append((label, cur))
                label, cur = h.group("label"), {}
                continue
            m = LINE.search(line)
            if m and cur is not None:
                cur[m.group("name")] = (m.group("shape"), m.group("dtype"),
                                        m.group("sum"), m.group("absmax"))
    if cur is not None:
        blocks.append((label, cur))
    return blocks


def kind_of(name):
    if name.startswith("mamba_"):
        return "mamba (recurrent)"
    if name.startswith("kv_") or "rotating" in name:
        return "kv / rotating"
    if name.startswith("__"):
        return "metadata"
    return "other"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--store-contains", default="STORE stable")
    ap.add_argument("--restore-contains", default="RESTORE cache-after")
    args = ap.parse_args()

    blocks = parse(args.log)
    if not blocks:
        print("no fidelity blocks found — was VMLX_FIDELITY_TRACE=1 set?", file=sys.stderr)
        return 1
    print(f"{len(blocks)} fingerprint blocks:")
    for label, t in blocks:
        print(f"  {label}  ({len(t)} tensors)")

    stores = [b for b in blocks if args.store_contains in b[0]]
    restores = [b for b in blocks if args.restore_contains in b[0]]
    if not stores or not restores:
        print("\nneed at least one store and one restore block to diff", file=sys.stderr)
        return 1
    slabel, s = stores[-1]
    rlabel, r = restores[-1]
    print(f"\ncomparing:\n  STORE   {slabel}\n  RESTORE {rlabel}\n")

    only_s = sorted(set(s) - set(r))
    only_r = sorted(set(r) - set(s))
    common = sorted(set(s) & set(r))
    diffs = [n for n in common if s[n] != r[n]]

    print(f"tensors: {len(s)} stored, {len(r)} restored, {len(common)} in common")
    if only_s:
        print(f"\nMISSING after restore ({len(only_s)}):")
        for n in only_s[:20]:
            print(f"  {n:<34} {kind_of(n)}")
    if only_r:
        print(f"\nPRESENT only after restore ({len(only_r)}):")
        for n in only_r[:20]:
            print(f"  {n:<34} {kind_of(n)}")
    if not diffs and not only_s and not only_r:
        print("\nIDENTICAL — the round-trip is faithful; look downstream of it.")
        return 0
    if diffs:
        by_kind = {}
        for n in diffs:
            by_kind.setdefault(kind_of(n), []).append(n)
        print(f"\nVALUE DIFFERENCES ({len(diffs)} tensors):")
        for kind, names in sorted(by_kind.items()):
            print(f"  {kind}: {len(names)}")
        print("\nfirst 12:")
        print(f"  {'tensor':<30}{'stored':>40}{'restored':>40}")
        for n in diffs[:12]:
            print(f"  {n:<30}{s[n][2]+'/'+s[n][3]:>40}{r[n][2]+'/'+r[n][3]:>40}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
