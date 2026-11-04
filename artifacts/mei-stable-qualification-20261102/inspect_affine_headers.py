"""Inventory stacked Qwen35 affine expert headers without loading tensor payloads."""

import argparse
import json
import re
import struct
from collections import Counter
from pathlib import Path
from typing import TypedDict

PATTERN = re.compile(
    r"^language_model\.model\.layers\.(\d+)\.mlp\.switch_mlp\."
    r"(gate_proj|up_proj|down_proj)\.(weight|scales|biases)$"
)


class RoutedTensor(TypedDict):
    shard: str
    shape: list[int]
    dtype: str
    bytes: int
    absolute_offset: int
    offset_mod_16384: int


def inspect(directory: Path) -> dict:
    index = json.loads((directory / "model.safetensors.index.json").read_text())
    mapping = index["weight_map"]
    routed: dict[str, RoutedTensor] = {}
    total_bytes = 0
    for shard in sorted(directory.glob("*.safetensors")):
        with shard.open("rb") as stream:
            raw = stream.read(8)
            if len(raw) != 8:
                raise ValueError(f"truncated header length: {shard.name}")
            size = struct.unpack("<Q", raw)[0]
            if not 0 < size <= 256 * 1024 * 1024:
                raise ValueError(f"invalid header size: {shard.name}")
            data = stream.read(size)
            if len(data) != size:
                raise ValueError(f"truncated header: {shard.name}")
            header = json.loads(data)
        for name, entry in header.items():
            if name == "__metadata__":
                continue
            start, end = entry["data_offsets"]
            if start < 0 or end < start or 8 + size + end > shard.stat().st_size:
                raise ValueError(f"out of bounds: {name}")
            total_bytes += end - start
            match = PATTERN.fullmatch(name)
            if match:
                if name in routed or mapping.get(name) != shard.name:
                    raise ValueError(f"duplicate or index mismatch: {name}")
                routed[name] = {
                    "shard": shard.name,
                    "shape": entry["shape"],
                    "dtype": entry["dtype"],
                    "bytes": end - start,
                    "absolute_offset": 8 + size + start,
                    "offset_mod_16384": (8 + size + start) % 16384,
                }
    indexed = {name for name in mapping if PATTERN.fullmatch(name)}
    if set(routed) != indexed:
        raise ValueError("missing or extra indexed routed tensors")
    model_config = json.loads((directory / "config.json").read_text())
    if model_config.get("model_type") != "qwen3_5_moe":
        raise ValueError("expected a Qwen35 MoE model")
    config = model_config["text_config"]
    return {
        "directory": str(directory.resolve()),
        "scope": "Safetensors headers only; no tensor payloads loaded or rehashed",
        "model_type": model_config["model_type"],
        "layers": config["num_hidden_layers"],
        "experts": config["num_experts"],
        "experts_per_token": config["num_experts_per_tok"],
        "hidden_size": config["hidden_size"],
        "moe_intermediate_size": config["moe_intermediate_size"],
        "tensor_payload_bytes": total_bytes,
        "routed_tensor_bytes": sum(row["bytes"] for row in routed.values()),
        "routed_tensor_count": len(routed),
        "dtype_counts": dict(Counter(row["dtype"] for row in routed.values())),
        "page_size_used_for_alignment": 16384,
        "routed_offsets_not_page_aligned": sum(
            row["offset_mod_16384"] != 0 for row in routed.values()
        ),
        "routed": routed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    print(json.dumps(inspect(args.directory), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
