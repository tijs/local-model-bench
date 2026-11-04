"""Estimate page-rounded per-expert mapping lengths from a saved header inventory.

These are Metal buffer lengths, not resident memory or a process-wide limit.
The input inventory reads only safetensors headers; this does not rehash weights.
"""

import argparse
import json
from pathlib import Path

from inspect_affine_headers import PATTERN

UINT64_MAX = (1 << 64) - 1


def estimate(inventory: dict, page_size: int) -> dict:
    experts = inventory["experts"]
    layers = inventory["layers"]
    if (
        not isinstance(experts, int)
        or experts <= 0
        or not isinstance(layers, int)
        or layers <= 0
    ):
        raise ValueError("invalid model geometry")
    if not isinstance(page_size, int) or page_size <= 0:
        raise ValueError("invalid page size")
    by_layer: dict[int, list[dict]] = {layer: [] for layer in range(layers)}
    for name, row in inventory["routed"].items():
        match = PATTERN.fullmatch(name)
        if not match or int(match[1]) not in by_layer:
            raise ValueError(f"unexpected routed key: {name}")
        if row["shape"][0] != experts or row["bytes"] <= 0 or row["bytes"] % experts:
            raise ValueError(f"invalid expert layout: {name}")
        if not 0 <= row["absolute_offset"] <= UINT64_MAX:
            raise ValueError(f"invalid offset: {name}")
        by_layer[int(match[1])].append(row)
    if any(len(rows) != 9 for rows in by_layer.values()):
        raise ValueError("each layer must contain all nine routed tensors")

    values = []
    for layer, rows in by_layer.items():
        for expert in range(experts):
            total = 0
            for row in rows:
                length = row["bytes"] // experts
                offset = row["absolute_offset"] + expert * length
                if offset > UINT64_MAX:
                    raise ValueError("expert offset overflow")
                span = offset % page_size + length
                rounded = ((span + page_size - 1) // page_size) * page_size
                total += rounded
                if rounded > UINT64_MAX or total > UINT64_MAX:
                    raise ValueError("mapping length overflow")
            values.append((total, layer, expert))
    minimum = min(values)
    maximum = max(values)
    return {
        "source_directory": inventory["directory"],
        "scope": "Saved headers only; summed page-rounded buffer lengths, not RSS or physical memory",
        "page_size": page_size,
        "layers": layers,
        "experts_per_layer": experts,
        "expert_count": len(values),
        "minimum_bytes": minimum[0],
        "maximum_bytes": maximum[0],
        "maximum_example": {"layer": maximum[1], "expert": maximum[2]},
        "distinct_sizes_bytes": sorted({value[0] for value in values}),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path)
    parser.add_argument("--page-size", type=int, required=True)
    args = parser.parse_args()
    data = json.loads(args.inventory.read_text())
    print(json.dumps(estimate(data, args.page_size), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
