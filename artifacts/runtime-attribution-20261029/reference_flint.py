"""Extend the prior independent Flint implementation through a failed tool turn."""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

# Arguments deliberately preserve the existing audited implementation's CLI:
# model, report, native-single-input, raw-dir, upstream-cache-source.
source = (
    Path(__file__).resolve().parents[1]
    / "flint-runtime-forensics-20261028/reference_incremental.py"
)
namespace = {}
exec(
    compile(
        source.read_text().split("\nimport importlib.util")[0], str(source), "exec"
    ),
    namespace,
)
mx = namespace["mx"]
c = namespace["c"]
forward = namespace["forward"]
out = Path(sys.argv[2])
case = json.loads(Path(sys.argv[3]).read_text())
raw = Path(sys.argv[4])
spec = importlib.util.spec_from_file_location("upstream_flint_cache", sys.argv[5])
cachemod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = cachemod
spec.loader.exec_module(cachemod)
report = {}
forced = case["forced_tokens"]
tokens = case["tokens"]
tail = min(64, len(forced))
prefill = 64
for mode in ("cache_off", "cache_off_matching_split"):
    caches = [
        cachemod.RotatingKVCache(max_size=c["sliding_window"], keep=0)
        if t == "sliding_attention"
        else cachemod.KVCache()
        for t in c["layer_types"]
    ]
    native = json.loads((raw / "report.json").read_text())
    lengths = native["prefill_segments"][mode]
    assert sum(lengths) == len(tokens)
    chunks = []
    cursor = 0
    for length in lengths:
        segment = tokens[cursor : cursor + length]
        chunks.extend(segment[i : i + prefill] for i in range(0, length, prefill))
        cursor += length
    for chunk in chunks:
        logits = forward(chunk, caches)
    rows = []
    for i, token in enumerate(forced):
        if i >= len(forced) - tail:
            rows.append(logits)
        if i + 1 < len(forced):
            logits = forward([token], caches)
    values = np.array(rows)
    actual = np.fromfile(raw / (mode + ".f32"), dtype=np.float32).reshape(values.shape)
    assert np.isfinite(values).all()
    report[mode] = {
        "max_abs": float(np.abs(values - actual).max()),
        "exact_rows": int(np.all(values == actual, axis=1).sum()),
        "rows": tail,
        "top1_mismatches": int((values.argmax(-1) != actual.argmax(-1)).sum()),
        "per_step_max_abs": np.abs(values - actual).max(-1).tolist(),
    }
    values.tofile(raw / ("python_failure_" + mode + ".f32"))
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(mode, report[mode]["max_abs"], flush=True)
