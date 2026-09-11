#!/usr/bin/env python3
"""Compare the probe legs and say what each comparison licenses."""
import json
import os
import sys

SP = sys.argv[1]
SUF = sys.argv[2] if len(sys.argv) > 2 else ""
LEGS = ("anchorsA", "anchorsB", "noanchors", "anchorsStrict", "noanchorsStrict")


def load(kind, leg):
    f = f"{SP}/{kind}{SUF}-{leg}.json"
    if not os.path.exists(f):
        return None
    d = json.load(open(f))
    return d["requests"] if kind == "small" else d["turns"]


def first_diff(x, y, key_fields):
    for i in range(min(len(x), len(y))):
        if any(x[i][k] != y[i][k] for k in key_fields):
            return i + 1, x[i], y[i]
    return None, None, None


def compare(kind, a, b, la, lb, note):
    x, y = load(kind, a), load(kind, b)
    if x is None or y is None:
        print(f"    {la} vs {lb}: MISSING artifact, not compared")
        return None
    fields = ("content", "completion_tokens") if kind == "small" else ("content", "tool_calls")
    n, xi, yi = first_diff(x, y, fields)
    if n is None:
        print(f"    {la} vs {lb}: IDENTICAL across {min(len(x), len(y))} — {note}")
        return True
    print(f"    {la} vs {lb}: diverges at #{n} "
          f"(ctok {xi['completion_tokens']}/{yi['completion_tokens']}) — {note}")
    return False


for kind, label in (("small", "STAGE 0 — five short prompts, nothing restored"),
                    ("div", "STAGE 1 — multi-turn agentic replay")):
    print(f"\n  === {label} ===")
    # Admissibility: the anchors legs must actually have anchors in play.
    for leg in ("anchorsA", "anchorsStrict"):
        d = load(kind, leg)
        if d and kind == "div" and d[0].get("cached_tokens", 0) == 0:
            print(f"    WARNING {leg}: turn 1 cached_tokens=0, no restore happened")
    compare(kind, "anchorsA", "anchorsB", "anchorsA", "anchorsB",
            "control: must be identical, else the probe is unstable")
    ctrl = compare(kind, "anchorsA", "noanchors", "anchors", "noanchors",
                   "the defect: anchors changing greedy output")
    fix = compare(kind, "anchorsStrict", "noanchorsStrict", "anchors+STRICT", "noanchors+STRICT",
                  "THE TEST: identical here means strict removes the segmentation dependence")
    compare(kind, "noanchors", "noanchorsStrict", "noanchors", "noanchors+STRICT",
            "strict is not free: it changes output globally on its own")
    if kind == "small" and ctrl is True:
        print("    NOTE: identical here does NOT prove anchors are harmless at "
              "this size — it may mean no boundary split occurred on prompts "
              "this short, i.e. the mechanism never engaged. Stage 1 is "
              "authoritative; treat stage 0 only as a cheap reproducer when it "
              "DOES diverge.")
    if ctrl is False and fix is True:
        print(f"    => VERDICT ({kind}): segmentation dependence confirmed, and "
              f"VMLX_GDN_STRICT=1 removes it.")
    elif ctrl is False and fix is False:
        print(f"    => VERDICT ({kind}): anchors diverge and strict does NOT fix it; "
              f"the cause is not (only) kernel segmentation.")
