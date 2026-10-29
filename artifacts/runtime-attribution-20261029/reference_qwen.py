"""Pinned Python MLX-LM oracle on exact native prompt IDs and forced histories."""

import argparse
import importlib.metadata
import json
import time
from pathlib import Path

import mlx.core as mx
import numpy as np
from mlx_lm.models.cache import make_prompt_cache
from mlx_lm.utils import load_model
from tokenizers import Tokenizer

parser = argparse.ArgumentParser()
parser.add_argument("--model", type=Path, required=True)
parser.add_argument("--swift-output", type=Path, required=True)
parser.add_argument("--out", type=Path, required=True)
parser.add_argument("--prefill", type=int, default=256)
args = parser.parse_args()
args.out.mkdir(parents=True, exist_ok=False)
mx.set_cache_limit(128 * 1024**2)
mx.set_memory_limit(24051816857)
model, config = load_model(args.model, lazy=False, strict=True)
mx.set_cache_limit(128 * 1024**2)
tokenizer = Tokenizer.from_file(str(args.model / "tokenizer.json"))
inputs = json.loads((args.swift_output / "native-inputs.json").read_text())
report = {
    "mlx": importlib.metadata.version("mlx"),
    "mlx_lm": importlib.metadata.version("mlx-lm"),
    "cases": {},
}
for case in inputs:
    name = case["name"]
    folder = args.swift_output / name
    swift = json.loads((folder / "report.json").read_text())
    tokens = case["tokens"]
    forced = case["forced_tokens"]
    tail = swift["tail_rows"]
    vocab = swift["vocab"]
    comparisons = {}

    def start(split):
        cache = make_prompt_cache(model, max_kv_size=65536)
        mode = "cache_off_matching_split" if split else "cache_off"
        lengths = swift["prefill_segments"][mode]
        assert sum(lengths) == len(tokens)
        chunks = []
        cursor = 0
        for length in lengths:
            segment = tokens[cursor : cursor + length]
            chunks.extend(
                segment[i : i + args.prefill] for i in range(0, length, args.prefill)
            )
            cursor += length
        for part in chunks:
            logits = model(mx.array(part)[None], cache=cache)[0, -1].astype(mx.float32)
            mx.eval(logits, [c.state for c in cache])
        return cache, logits

    for mode, split in [("cache_off", False), ("cache_off_matching_split", True)]:
        started = time.monotonic()
        cache, logits = start(split)
        rows = []
        for i, token in enumerate(forced):
            if i >= len(forced) - tail:
                rows.append(np.array(logits, dtype=np.float32))
            if i + 1 < len(forced):
                logits = model(mx.array([[token]]), cache=cache)[0, -1].astype(
                    mx.float32
                )
                mx.eval(logits)
        values = np.array(rows)
        actual = np.fromfile(folder / (mode + ".f32"), dtype=np.float32).reshape(
            tail, vocab
        )
        assert values.shape == actual.shape and np.isfinite(values).all()
        comparisons[mode] = {
            "seconds": time.monotonic() - started,
            "exact_rows": int(np.all(values == actual, axis=1).sum()),
            "rows": tail,
            "max_abs": float(np.abs(values - actual).max()),
            "top1_mismatches": int((values.argmax(-1) != actual.argmax(-1)).sum()),
            "per_step_max_abs": np.abs(values - actual).max(-1).tolist(),
        }
        values.tofile(args.out / (name + "-" + mode + ".f32"))
        print(name, mode, comparisons[mode]["max_abs"], flush=True)
        del values, actual, rows, cache
        mx.clear_cache()
    cache, logits = start(True)
    generated = []
    eos = config.get("eos_token_id", [248046, 248044])
    eos = {eos} if isinstance(eos, int) else set(eos)
    started = time.monotonic()
    for _ in range(1536):
        token = int(mx.argmax(logits).item())
        generated.append(token)
        if token in eos:
            break
        logits = model(mx.array([[token]]), cache=cache)[0, -1].astype(mx.float32)
        mx.eval(logits)
    report["cases"][name] = {
        "comparisons": comparisons,
        "greedy_tokens": generated,
        "greedy_raw_text": tokenizer.decode(generated, skip_special_tokens=False),
        "greedy_seconds": time.monotonic() - started,
        "greedy_stopped_on_eos": generated[-1] in eos,
        "peak_bytes": mx.get_peak_memory(),
    }
    (args.out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(name, "greedy", len(generated), flush=True)
