"""Guard: no Mei launch command may set --kv-cache-dir more than once.

Why this exists. All four Qwen3.6 anchors A/B configs passed --kv-cache-dir
twice. start_mei_server.sh takes the LAST value; run_bench.py's
clear_kv_cache_dir used re.search and took the FIRST. So the runner deleted a
directory the server never opened, printed "clear KV cache for a cold,
comparable run" naming it, and the server ran against a cache nobody cleared.

The evidence, after the fact: the four per-arm dirs the runner kept clearing
(kv-q36v-anchors, kv-q36v-noanchors, kv-q36-anchors, kv-q36-noanchors) did not
exist on disk at all, while the two shared dirs the server actually used held
9.9 GB and 40 and 44 entries. Both arms of each A/B shared one warm cache, so
neither arm was cold and the arms were not independent.

Two defects had to line up: a config that says a thing twice, and two readers
that disagree about which one counts. run_bench.py now clears every distinct
dir it finds and warns on duplicates; this guard stops the config half from
coming back. Run it from runner/gates/unit_tests_gate.sh or by hand.
"""
import re, sys, glob, yaml
bad=[]
for f in sorted(glob.glob("configs/*/mei*.yaml")):
    try: lc=(yaml.safe_load(open(f)) or {}).get("benchmark_launch_command") or ""
    except Exception as e: bad.append((f,f"unparseable: {e}")); continue
    d=re.findall(r"--kv-cache-dir\s+(\S+)", lc)
    if len(d)>1: bad.append((f,f"{len(d)} kv-cache-dirs: {d}"))
print(f"checked {len(glob.glob('configs/*/mei*.yaml'))} Mei configs")
for f,w in bad: print("  FAIL", f, w)
sys.exit(1 if bad else 0)
