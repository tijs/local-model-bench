"""Independent Python incremental-cache oracle for the exact packed Flint artifact.
Architecture: mlx-vlm 8c061ef5 flint/language.py; packed primitive: jangq
6dd1268e kernel. No Swift implementation or generated output is imported.
"""

import pathlib, json, time, sys, math
import mlx.core as mx
import mlx.nn as nn
import numpy as np
from tokenizers import Tokenizer

sys.path.insert(0, "/Users/tijs/.local/share/local-model-bench/jangh2-reference")
from jangh_ref import kernels as K
from jangh_ref.format import cubic_params, codebook

root = pathlib.Path(sys.argv[1])
out = pathlib.Path(sys.argv[2])
c = json.loads((root / "config.json").read_text())
mx.set_cache_limit(512 * 1024**2)
w = {}
for p in sorted(root.glob("model-*.safetensors")):
    w.update(mx.load(str(p)))


def lin(x, n):
    return mx.quantized_matmul(
        x,
        w[n + ".weight"],
        w[n + ".scales"],
        w[n + ".biases"],
        transpose=True,
        group_size=64,
        bits=8,
    )


def norm(x, n):
    return mx.fast.rms_norm(x, w[n + ".weight"], c["rms_norm_eps"])


def dense(x, n):
    return lin(
        nn.silu(lin(x, n + ".gate_proj")) * lin(x, n + ".up_proj"), n + ".down_proj"
    )


def rotate(x):
    return mx.hadamard_transform(
        x.reshape(*x.shape[:-1], x.shape[-1] // 32, 32), scale=1 / math.sqrt(32)
    ).reshape(x.shape)


def packed(x, n, ids, per_dispatch=False):
    b = c["quantization"][n]["bits"]
    a, beta = cubic_params(b)
    book = c["jangtq"]["codebooks"][str(b)]
    assert a == book["alpha"] and beta == book["beta"]
    return K.gather_qmv(
        rotate(x.astype(mx.float32)),
        w[n + ".tq2_packed"],
        w[n + ".tq2_scales"],
        mx.array(codebook(b)),
        ids,
        b,
        x_per_dispatch=per_dispatch,
    )


def forward(token_ids, caches):
    length = len(token_ids)
    x = mx.dequantize(
        w["model.embed_tokens.weight"][mx.array(token_ids)],
        w["model.embed_tokens.scales"][mx.array(token_ids)],
        w["model.embed_tokens.biases"][mx.array(token_ids)],
        group_size=64,
        bits=8,
    )[None]
    for layer in range(c["num_hidden_layers"]):
        p = f"model.layers.{layer}"
        a = norm(x, p + ".input_layernorm")
        heads = c["num_attention_heads"]
        kv = c["num_key_value_heads"]
        dim = c["head_dim"]
        q = norm(
            lin(a, p + ".self_attn.q_proj").reshape(1, length, heads, dim),
            p + ".self_attn.q_norm",
        ).transpose(0, 2, 1, 3)
        k = norm(
            lin(a, p + ".self_attn.k_proj").reshape(1, length, kv, dim),
            p + ".self_attn.k_norm",
        ).transpose(0, 2, 1, 3)
        v = (
            lin(a, p + ".self_attn.v_proj")
            .reshape(1, length, kv, dim)
            .transpose(0, 2, 1, 3)
        )
        if layer not in c["no_rope_layer_indices"]:
            q = mx.fast.rope(
                q,
                dims=dim,
                traditional=False,
                base=c["rope_theta"],
                scale=1.0,
                offset=caches[layer].offset,
            )
            k = mx.fast.rope(
                k,
                dims=dim,
                traditional=False,
                base=c["rope_theta"],
                scale=1.0,
                offset=caches[layer].offset,
            )
        window = (
            c["sliding_window"]
            if c["layer_types"][layer] == "sliding_attention"
            else None
        )
        mask = caches[layer].make_mask(length, window_size=window, return_array=False)
        k, v = caches[layer].update_and_fetch(k, v)
        att = mx.fast.scaled_dot_product_attention(
            q,
            k,
            v,
            scale=dim**-0.5,
            mask=mask,
            sinks=w[p + ".self_attn.softmax_offset"].astype(q.dtype),
        )
        x = x + lin(
            att.transpose(0, 2, 1, 3).reshape(1, length, -1), p + ".self_attn.o_proj"
        )
        h = norm(x, p + ".post_attention_layernorm")
        residual = x
        if layer in c["mlp_only_layers"]:
            x = x + dense(h, p + ".mlp")
        else:
            scores = mx.sigmoid((h @ w[p + ".mlp.gate.weight"].T).astype(mx.float32))
            ids = mx.argpartition(scores, kth=-c["num_experts_per_tok"], axis=-1)[
                ..., -c["num_experts_per_tok"] :
            ]
            probs = mx.take_along_axis(scores, ids, axis=-1)
            probs = probs / (probs.sum(axis=-1, keepdims=True) + 1e-20)
            ids = ids.reshape(-1).astype(mx.uint32)
            parent = p + ".mlp.switch_mlp"
            flat = h.reshape(-1, c["hidden_size"])
            gate = packed(flat, parent + ".gate_proj", ids)
            up = packed(flat, parent + ".up_proj", ids)
            hidden = nn.silu(gate) * up
            down = packed(hidden, parent + ".down_proj", ids, True).reshape(
                1, length, c["num_experts_per_tok"], c["hidden_size"]
            )
            routed = (down * probs[..., None]).sum(axis=-2).astype(h.dtype)
            shared = dense(h, p + ".mlp.shared_expert")
            x = x + (routed + shared)
        mx.eval(x)
    result = lin(norm(x, "model.norm").astype(mx.float32), "lm_head")[0, -1]
    mx.eval(result)
    return np.array(result, dtype=np.float32)


import importlib.util

spec = importlib.util.spec_from_file_location("upstream_flint_cache", sys.argv[5])
cachemod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = cachemod
spec.loader.exec_module(cachemod)
case = json.loads(pathlib.Path(sys.argv[3]).read_text())
raw_dir = pathlib.Path(sys.argv[4])
report = {}
for mode in ("cache_off", "cache_off_matching_split"):
    caches = [
        cachemod.RotatingKVCache(max_size=c["sliding_window"], keep=0)
        if t == "sliding_attention"
        else cachemod.KVCache()
        for t in c["layer_types"]
    ]
    tokens = case["tokens"]
    end = len(tokens) if mode == "cache_off" else len(tokens) - 1
    chunks = [tokens[i : min(i + 64, end)] for i in range(0, end, 64)]
    if mode != "cache_off":
        chunks.append([tokens[-1]])
    for i, chunk in enumerate(chunks):
        first = forward(chunk, caches)
        print(mode, "prefill", i + 1, "/", len(chunks), flush=True)
    rows = [first]
    for i, token in enumerate(case["forced_tokens"][:-1]):
        rows.append(forward([token], caches))
    values = np.array(rows)
    actual = np.fromfile(raw_dir / (mode + ".f32"), dtype=np.float32).reshape(
        values.shape
    )
    report[mode] = {
        "max_abs": float(np.abs(values - actual).max()),
        "exact_rows": [bool(np.array_equal(a, b)) for a, b in zip(values, actual)],
        "top1_mismatches": int(
            np.sum(values.argmax(axis=-1) != actual.argmax(axis=-1))
        ),
        "per_step_max_abs": [
            float(np.abs(a - b).max()) for a, b in zip(values, actual)
        ],
    }
    values.tofile(raw_dir / ("python_" + mode + ".f32"))
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(mode, report[mode]["max_abs"], flush=True)
