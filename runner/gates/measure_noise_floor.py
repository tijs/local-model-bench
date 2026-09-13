#!/usr/bin/env python3
"""Measure a model's noise floor from repeats of the SAME config.

A floor is "tasks that flip between two runs of one config, nothing changed".
Anything else is not a floor. The set this replaces was derived from runs whose
two arms shared a never-cleared KV cache, and it was wrong in both directions at
once: it excluded four genuinely stable tasks (hiding real regressions) while
omitting one that really does flip (manufacturing a fake one).

Usage:
    measure_noise_floor.py configs/<model>/<config>.yaml [more configs...]

Prints the per-config floor, the union across configs of the same model (which
is how UNSTABLE_BY_MODEL is defined), and a paste-ready dict entry. Refuses to
report a floor for a config with fewer than two complete runs rather than
guessing from one.
"""
import json, sys, collections
from pathlib import Path

def _find_repo():
    """Walk up from cwd, then from this file, looking for results/log.jsonl.

    Deriving the repo from __file__'s depth breaks the moment the script is run
    from anywhere but its installed location — which is exactly how it was
    first tested.
    """
    for start in (Path.cwd(), Path(__file__).resolve().parent):
        for d in (start, *start.parents):
            if (d / "results" / "log.jsonl").exists():
                return d
    raise SystemExit("could not locate the benchmark repo (no results/log.jsonl above cwd)")

REPO = _find_repo()

def complete_runs(config_path):
    rows = [json.loads(l) for l in (REPO / "results" / "log.jsonl").open() if l.strip()]
    rs = sorted((r for r in rows if (r.get("config_path") or "") == str(config_path)),
                key=lambda r: r["timestamp"])
    out, cur = [], None
    for r in rs:
        if r["task_id"] == "sanity-basic":
            cur = {}; out.append(cur)
        if cur is not None:
            cur[r["task_id"]] = r
    return [x for x in out if len(x) == 25]

def floor_for(config_path):
    runs = complete_runs(config_path)
    if len(runs) < 2:
        return None, len(runs)
    flips = set()
    for i in range(len(runs) - 1):
        a, b = runs[i], runs[i + 1]
        flips |= {t for t in set(a) & set(b) if a[t]["pass"] != b[t]["pass"]}
    return flips, len(runs)

def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    by_model = collections.defaultdict(set)
    ok = True
    for cfg in sys.argv[1:]:
        flips, n = floor_for(cfg)
        name = f"{Path(cfg).parent.name}/{Path(cfg).name}"
        if flips is None:
            print(f"{name:52s} SKIPPED — {n} complete run(s), need 2")
            ok = False
            continue
        print(f"{name:52s} {n} runs   floor {len(flips)}: {sorted(flips) or '(deterministic)'}")
        by_model[Path(cfg).parent.name] |= flips
    print()
    for model, flips in sorted(by_model.items()):
        print(f'    "{model}": {{')
        for t in sorted(flips):
            print(f'        "{t}",')
        print(f'    }},   # {len(flips)} tasks, measured from same-config repeats')
    if not ok:
        print("\nSome configs lacked repeats; the union above is incomplete.")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
