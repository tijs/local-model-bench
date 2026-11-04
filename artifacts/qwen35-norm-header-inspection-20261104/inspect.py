#!/usr/bin/env -S uv run --offline --no-project python
"""Read checkpoint headers and bounded norm payloads; never load a model.

Usage: uv run --offline --no-project python inspect.py [model-directory ...]
No model files are modified. Hashes identify config and index bytes only.
"""

import hashlib
import json
import math
import struct
import sys
from pathlib import Path

BASE = Path("/Users/tijs/.local/share/local-model-bench/mei-models")
DEFAULTS = [
    BASE / "Ornith-1.5-35B-A3B-MLX-4bit-aligned",
    BASE / "Qwen3.6-35B-A3B-4bit",
    BASE / "Qwen3.6-35B-A3B-4bit-textonly",
]
MAX_HEADER = 64 * 1024 * 1024
MAX_NORM = 64 * 1024


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def inspect(directory):
    directory = directory.resolve(strict=True)
    config_path = directory / "config.json"
    config = json.loads(config_path.read_bytes())
    text = config.get("text_config", {})
    quant = config.get("quantization", {})
    result = {
        "directory": str(directory),
        "config_sha256": digest(config_path),
        "index_sha256": digest(directory / "model.safetensors.index.json"),
        "root_norm_convention": config.get("norm_convention"),
        "text_norm_convention": text.get("norm_convention"),
        "quantization_defaults": {
            key: quant.get(key) for key in ("bits", "group_size", "mode")
        },
        "quantization_overrides": {
            key: value
            for key, value in quant.items()
            if key not in ("bits", "group_size", "mode")
        },
        "shards": [],
        "norms": [],
        "conv_shapes": [],
        "router_types": [],
    }
    conv_shapes, router_types = set(), set()
    for path in sorted(directory.glob("*.safetensors")):
        with path.open("rb") as file:
            prefix = file.read(8)
            if len(prefix) != 8:
                raise ValueError(f"{path}: truncated header length")
            length = struct.unpack("<Q", prefix)[0]
            if not 0 < length <= MAX_HEADER:
                raise ValueError(f"{path}: invalid header length {length}")
            raw_header = file.read(length)
            if len(raw_header) != length:
                raise ValueError(f"{path}: truncated header")
            header = json.loads(raw_header)
            result["shards"].append(
                {
                    "name": path.name,
                    "bytes": path.stat().st_size,
                    "header_sha256": hashlib.sha256(raw_header).hexdigest(),
                    "metadata": header.get("__metadata__", {}),
                }
            )
            data_start = 8 + length
            for key, descriptor in header.items():
                if key == "__metadata__":
                    continue
                shape, dtype = descriptor["shape"], descriptor["dtype"]
                if "conv1d.weight" in key:
                    conv_shapes.add(tuple(shape))
                if (
                    ".mlp.gate." in key or ".mlp.shared_expert_gate." in key
                ) and key.endswith((".weight", ".scales", ".biases")):
                    router_types.add((key.rsplit(".", 1)[-1], dtype))
                if not key.endswith(
                    (".input_layernorm.weight", ".post_attention_layernorm.weight")
                ):
                    continue
                start, end = descriptor["data_offsets"]
                element_size = {"BF16": 2, "F16": 2, "F32": 4}.get(dtype)
                if (
                    len(shape) != 1
                    or element_size is None
                    or start < 0
                    or end < start
                    or end - start > MAX_NORM
                    or end - start != shape[0] * element_size
                    or data_start + end > path.stat().st_size
                ):
                    raise ValueError(f"{path}: unsupported norm {key}")
                file.seek(data_start + start)
                raw = file.read(end - start)
                if len(raw) != end - start:
                    raise ValueError(f"{path}: truncated norm {key}")
                if dtype == "BF16":
                    values = [
                        struct.unpack("<f", struct.pack("<I", item[0] << 16))[0]
                        for item in struct.iter_unpack("<H", raw)
                    ]
                else:
                    values = [
                        item[0]
                        for item in struct.iter_unpack(
                            "<e" if dtype == "F16" else "<f", raw
                        )
                    ]
                if not values or not all(math.isfinite(value) for value in values):
                    raise ValueError(f"{path}: empty or nonfinite norm {key}")
                result["norms"].append(
                    {
                        "name": key,
                        "shard": path.name,
                        "dtype": dtype,
                        "elements": len(values),
                        "mean": sum(values) / len(values),
                        "payload_sha256": hashlib.sha256(raw).hexdigest(),
                    }
                )
    result["conv_shapes"] = [list(shape) for shape in sorted(conv_shapes)]
    result["router_types"] = [list(pair) for pair in sorted(router_types)]
    means = [norm["mean"] for norm in result["norms"]]
    result["norm_vote"] = {
        "count": len(means),
        "below_half": sum(x < 0.5 for x in means),
        "above_half": sum(x > 0.5 for x in means),
        "minimum": min(means, default=None),
        "maximum": max(means, default=None),
    }
    return result


if __name__ == "__main__":
    paths = [Path(arg) for arg in sys.argv[1:]] if sys.argv[1:] else DEFAULTS
    print(
        json.dumps(
            {
                "scope": "read-only headers and bounded norm payloads; no model or GPU load",
                "models": [inspect(path) for path in paths],
            },
            indent=2,
            sort_keys=True,
        )
    )
