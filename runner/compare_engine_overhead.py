#!/usr/bin/env python3
"""Per-turn overhead split for Mei and llama.cpp on the same, server-measured basis.

Both engines report their own prefill/generate time — Mei through --request-log,
llama-server through its `print_timing` log lines. Neither number here is
derived from the leaderboard decode column, which measures harness time between
turns rather than decode.

Two things this gets right that a naive version does not, both found the hard
way:

1. A result row's `timestamp` is the run's END, not its start. Windows must be
   [timestamp - wall_seconds, timestamp]. The start-based reading covered only
   58% of llama.cpp's timing entries; the end-based reading covers 99.6%.

2. llama-server runs several slots and overlaps requests, so SUMMING per-request
   durations double-counts wall time — it reported prefill+generate greater than
   the wall clock they had to fit inside. Count the UNION of phase intervals
   instead: prefill runs [launch, launch+prompt_ms], generation ends at release.

Coverage is printed for every leg. Do not trust a split whose coverage is low.
"""
import argparse, datetime as dt, json, re, subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CODING = {"kiem_mini", "hearth_mini", "kipclip_mini", "hearth_full"}


def pts(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def union(intervals):
    if not intervals:
        return 0.0
    iv = sorted(intervals)
    total, cs, ce = 0.0, *iv[0]
    for a, b in iv[1:]:
        if a > ce:
            total += ce - cs
            cs, ce = a, b
        else:
            ce = max(ce, b)
    return total + ce - cs


def windows(rows):
    """Row timestamps are END times — see module docstring."""
    return [(pts(r["timestamp"]) - r["wall_seconds"], pts(r["timestamp"])) for r in rows]


def load_rows(config_substr, sha=None):
    out = []
    for line in (REPO / "results" / "log.jsonl").open():
        r = json.loads(line)
        if config_substr not in str(r.get("config_path", "")):
            continue
        if sha and (r.get("runner_git_sha") or "") != sha:
            continue
        out.append(r)
    return sorted(out, key=lambda r: r["timestamp"])


def mei_phases(request_log, wins):
    inside = lambda t: any(a <= t <= b for a, b in wins)
    pre, gen, seen, total = [], [], 0, 0
    for line in Path(request_log).open():
        e = json.loads(line)
        total += 1
        if not inside(e["t"]):
            continue
        seen += 1
        p = (e.get("prefill_ms") or 0) / 1000.0
        g = (e.get("generate_ms") or 0) / 1000.0
        pre.append((e["t"], e["t"] + p))
        gen.append((e["t"] + p, e["t"] + p + g))
    return pre, gen, seen, total


def llama_phases(server_log, wins):
    t0 = float(subprocess.run(["stat", "-f", "%B", server_log],
                              capture_output=True, text=True).stdout.strip())

    def elapsed(s):  # llama-server stamps MM.SS.mmm.uuu since process start
        a, b, c, d = s.split(".")
        return int(a) * 60 + int(b) + int(c) / 1e3 + int(d) / 1e6

    launch, release, timing = {}, {}, {}
    pat = re.compile(r"^([0-9.]+) I slot (launch_slot_|     release|print_timing): "
                     r"id +([0-9]+) \| task ([0-9]+)")
    for line in Path(server_log).open(errors="ignore"):
        m = pat.match(line)
        if not m:
            continue
        t = t0 + elapsed(m.group(1))
        key, kind = (m.group(3), m.group(4)), m.group(2)
        if "launch" in kind:
            launch[key] = t
        elif "release" in kind:
            release[key] = t
        else:
            ms = re.search(r"= *([0-9.]+) ms", line)
            if not ms:
                continue
            d = timing.setdefault(key, {})
            if "prompt eval time" in line:
                d["p"] = float(ms.group(1)) / 1000.0
            elif "eval time" in line and "total time" not in line:
                d["g"] = float(ms.group(1)) / 1000.0

    inside = lambda t: any(a <= t <= b for a, b in wins)
    pre, gen, seen = [], [], 0
    for key, d in timing.items():
        if key not in launch or key not in release:
            continue
        if not inside(launch[key]):
            continue
        seen += 1
        pre.append((launch[key], launch[key] + d.get("p", 0.0)))
        gen.append((release[key] - d.get("g", 0.0), release[key]))
    return pre, gen, seen, len(timing)


def report(name, rows, pre, gen, seen, total):
    wall = sum(r["wall_seconds"] for r in rows)
    turns = sum(r.get("hermes_turns") or 0 for r in rows)
    if not (wall and turns):
        print(f"{name}: no usable rows")
        return
    pu, gu = union(pre), union(gen)
    print(f"{name}")
    # `seen` counts requests inside THESE windows; `total` is the whole log,
    # which also holds other suites' requests, so seen/total is not a coverage
    # figure. The real validation is the separate all-rows check below.
    print(f"  rows {len(rows)}  turns {turns}  wall {wall/60:.2f} min  "
          f"requests in windows {seen} (log holds {total})")
    print(f"  prefill        {pu/turns:5.2f} s/turn ({pu/60:5.2f} min)")
    print(f"  generate       {gu/turns:5.2f} s/turn ({gu/60:5.2f} min)")
    print(f"  not generating {(wall-gu)/turns:5.2f} s/turn = {100*(wall-gu)/wall:.1f}% of wall")
    if pu + gu > wall:
        print("  WARNING: prefill+generate exceeds wall — concurrency is being "
              "double-counted; do not quote these numbers.")
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mei-config", default="mei-capture")
    ap.add_argument("--mei-request-log", required=True)
    ap.add_argument("--mei-last-n", type=int, default=0,
                    help="use only the last N coding rows (a coding-only rerun "
                         "needs no suite attribution)")
    ap.add_argument("--llama-config", default="gguf.yaml")
    ap.add_argument("--llama-server-log", required=True)
    ap.add_argument("--llama-sha", default=None)
    args = ap.parse_args()

    # Validation first: do end-based windows over ALL rows account for
    # essentially every request the server logged? If not, every split below is
    # built on silently dropped data — the failure mode that produced three
    # different answers for one quantity before this check existed.
    all_mei = load_rows(args.mei_config)
    _, _, seen, total = mei_phases(args.mei_request_log, windows(all_mei))
    print(f"window validation, Mei      : {seen}/{total} requests inside all-row "
          f"windows = {100*seen/max(total,1):.1f}%")
    all_gg = load_rows(args.llama_config, args.llama_sha)
    _, _, seen, total = llama_phases(args.llama_server_log, windows(all_gg))
    print(f"window validation, llama.cpp: {seen}/{total} requests inside all-row "
          f"windows = {100*seen/max(total,1):.1f}%\n")

    mei = [r for r in load_rows(args.mei_config) if r["suite"] in CODING]
    if args.mei_last_n:
        mei = mei[-args.mei_last_n:]
    w = windows(mei)
    report("MEI (coding)", mei, *mei_phases(args.mei_request_log, w))

    gg = [r for r in load_rows(args.llama_config, args.llama_sha) if r["suite"] in CODING]
    w = windows(gg)
    report("LLAMA.CPP (coding)", gg, *llama_phases(args.llama_server_log, w))


if __name__ == "__main__":
    main()
