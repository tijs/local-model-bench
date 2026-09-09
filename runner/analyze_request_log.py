#!/usr/bin/env python3
"""Decompose an agentic suite's wall time from Mei's --request-log JSONL.

Motivation (2026-09-09): on the coding suites Mei produced FEWER turns and
FEWER output tokens than llama.cpp yet took substantially longer wall time —
31.6 output tok/s of wall for llama.cpp against 14.5 for Mei — despite
near-identical raw decode rates (42.4 vs 42.9 tok/s). Task-level rows could
not say where the difference went, because a coding task is many turns and
only the task total was recorded.

This reads the per-run log and answers, per turn:

  prefill_ms   time re-reading the conversation so far
  generate_ms  time actually producing tokens
  gap_ms       wall_ms - prefill - generate, i.e. server-side overhead
               (detokenisation, tool-call parsing, cache store/restore,
               memory capture) that belongs to neither

and between turns:

  idle_ms      time between one run finishing and the next starting, i.e.
               the harness's own turn cost (tool execution, file IO, its
               own model-independent work). Attributed to the harness, not
               to Mei.

Usage:
  analyze_request_log.py <log.jsonl> [--kind chat_stream] [--since-uptime S]
"""
from __future__ import annotations

import argparse
import json
import sys


def load(path: str, kind: str | None) -> list[dict]:
    rows = []
    with open(path) as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                # A run killed mid-write leaves a partial final line. Skip it
                # loudly rather than dying on an otherwise usable log.
                print(f"warning: {path}:{lineno} is not valid JSON, skipped", file=sys.stderr)
                continue
            if kind and r.get("kind") != kind:
                continue
            rows.append(r)
    return rows


def pct(part: float, whole: float) -> str:
    return f"{100.0 * part / whole:5.1f}%" if whole else "    - "


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--kind", default=None, help="only this run kind (chat, chat_stream, completion)")
    ap.add_argument("--since-uptime", type=float, default=None,
                    help="ignore runs before this server uptime in seconds (skips warmup)")
    ap.add_argument("--json", action="store_true", help="emit machine-readable totals")
    args = ap.parse_args()

    rows = load(args.log, args.kind)
    if args.since_uptime is not None:
        rows = [r for r in rows if r.get("uptime_s", 0) >= args.since_uptime]
    if not rows:
        print("no runs matched", file=sys.stderr)
        return 1
    rows.sort(key=lambda r: r["t"])

    prefill = sum(r["prefill_ms"] for r in rows)
    generate = sum(r["generate_ms"] for r in rows)
    wall = sum(r["wall_ms"] for r in rows)
    gap = wall - prefill - generate

    # Harness time: the wall clock between the end of one run and the start
    # of the next. Runs are serialized by the engine actor, so end-of-run is
    # r["t"] and start-of-run is r["t"] - wall_ms.
    idle = 0.0
    for prev, cur in zip(rows, rows[1:]):
        d = (cur["t"] - cur["wall_ms"] / 1000.0) - prev["t"]
        if d > 0:
            idle += d * 1000.0
    span = (rows[-1]["t"] - (rows[0]["t"] - rows[0]["wall_ms"] / 1000.0)) * 1000.0

    out_tok = sum(r["completion_tokens"] for r in rows)
    in_tok = sum(r["prompt_tokens"] for r in rows)
    cached = sum(r["cached_tokens"] for r in rows)
    hits = sum(1 for r in rows if r.get("cache_hit"))

    if args.json:
        print(json.dumps({
            "runs": len(rows), "span_ms": span, "server_wall_ms": wall,
            "prefill_ms": prefill, "generate_ms": generate, "server_gap_ms": gap,
            "harness_idle_ms": idle, "prompt_tokens": in_tok,
            "cached_tokens": cached, "completion_tokens": out_tok,
            "cache_hits": hits}, indent=2))
        return 0

    n = len(rows)
    print(f"runs {n}   span {span/60000:.1f} min   prompt {in_tok:,} tok "
          f"(cached {cached:,}, {hits}/{n} hits)   output {out_tok:,} tok\n")
    print(f"{'component':<22}{'total':>12}{'share of span':>16}{'per turn':>12}")
    for label, val in (("prefill (re-read)", prefill), ("generate", generate),
                       ("server gap", gap), ("harness between turns", idle)):
        print(f"{label:<22}{val/60000:>9.1f} min{pct(val, span):>16}{val/n/1000:>10.2f} s")
    print(f"{'-'*62}")
    print(f"{'span':<22}{span/60000:>9.1f} min")
    if span:
        print(f"\noutput tok/s of span: {out_tok / (span/1000.0):.1f}"
              f"   decode-only tok/s: {out_tok / (generate/1000.0):.1f}" if generate else "")

    # Where prefill goes: a turn that re-reads the whole transcript costs
    # proportionally to prompt length, so show the worst offenders.
    worst = sorted(rows, key=lambda r: -r["prefill_ms"])[:5]
    print("\nslowest prefills")
    print(f"{'prompt':>9}{'cached':>9}{'prefill s':>11}{'gen s':>8}{'out tok':>9}  kind")
    for r in worst:
        print(f"{r['prompt_tokens']:>9,}{r['cached_tokens']:>9,}"
              f"{r['prefill_ms']/1000:>11.2f}{r['generate_ms']/1000:>8.2f}"
              f"{r['completion_tokens']:>9,}  {r['kind']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
