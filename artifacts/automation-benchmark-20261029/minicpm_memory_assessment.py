"""Read GGUF metadata without loading tensor payloads; estimate fixed cache terms.

Research utility only: not a runtime allocation ceiling or a launch admission.
"""

from __future__ import annotations

import argparse
import json
import struct
from datetime import UTC, datetime
from pathlib import Path


def metadata(path: Path) -> dict:
    formats = {
        0: "B",
        1: "b",
        2: "H",
        3: "h",
        4: "I",
        5: "i",
        6: "f",
        7: "?",
        10: "Q",
        11: "q",
        12: "d",
    }
    with path.open("rb") as stream:

        def scalar(fmt):
            size = struct.calcsize("<" + fmt)
            return struct.unpack("<" + fmt, stream.read(size))[0]

        def string(keep=True):
            size = scalar("Q")
            if size > 16 * 1024**2:
                raise ValueError("unexpected GGUF metadata string size")
            if keep:
                return stream.read(size).decode("utf-8")
            stream.seek(size, 1)
            return None

        def value(kind, keep=True):
            if kind == 8:
                return string(keep)
            if kind == 9:
                subtype, count = scalar("I"), scalar("Q")
                if count > 2_000_000:
                    raise ValueError("unexpected GGUF array size")
                if keep and subtype in formats:
                    return [scalar(formats[subtype]) for _ in range(count)]
                if subtype in formats:
                    stream.seek(count * struct.calcsize("<" + formats[subtype]), 1)
                elif subtype == 8:
                    for _ in range(count):
                        string(False)
                else:
                    raise ValueError("unsupported nested GGUF array")
                return None
            return scalar(formats[kind])

        if stream.read(4) != b"GGUF" or scalar("I") != 3:
            raise ValueError("expected GGUF v3")
        scalar("Q")  # tensor count; tensor data is not read or mapped
        count = scalar("Q")
        if count > 100_000:
            raise ValueError("unexpected metadata count")
        fields = {}
        for _ in range(count):
            key, kind = string(), scalar("I")
            keep = not key.startswith("tokenizer.")
            item = value(kind, keep)
            if keep:
                fields[key] = item
        return fields


def assess(path: Path) -> dict:
    fields = metadata(path)
    arch = fields["general.architecture"]
    if arch != "qwen35moe":
        raise ValueError("this assessment is specific to pinned MiniCPM qwen35moe")
    prefix = arch + "."
    layers = fields[prefix + "block_count"]
    recurrent = fields[prefix + "attention.recurrent_layers"]
    if len(recurrent) != layers or any(type(item) is not bool for item in recurrent):
        raise ValueError("invalid recurrent layer declaration")
    dense_layers = recurrent.count(False)
    ctx, parallel, rollback = 65536, 1, 0
    kv_bytes = (
        dense_layers
        * ctx
        * fields[prefix + "attention.head_count_kv"]
        * (
            fields[prefix + "attention.key_length"]
            + fields[prefix + "attention.value_length"]
        )
        * 2
    )  # f16 K and V
    inner = fields[prefix + "ssm.inner_size"]
    state = fields[prefix + "ssm.state_size"]
    conv = (fields[prefix + "ssm.conv_kernel"] - 1) * (
        inner + 2 * fields[prefix + "ssm.group_count"] * state
    )
    recurrent_bytes = (
        recurrent.count(True) * (conv + state * inner) * 4 * parallel * (1 + rollback)
    )
    return {
        "checked_at": datetime.now(UTC).isoformat(),
        "file": str(path),
        "resolved_file": str(path.resolve()),
        "runtime_commit": "1268edac579110aeb1407f7928f53193ed4e28d4",
        "metadata": fields,
        "configured": {
            "context": ctx,
            "parallel": parallel,
            "rollback": rollback,
            "kv_dtype": "f16",
            "recurrent_dtype": "f32",
            "batch": 512,
            "ubatch": 128,
            "mmproj": False,
        },
        "estimates": {
            "gguf_file_bytes": path.stat().st_size,
            "dense_attention_layers": dense_layers,
            "recurrent_layers": recurrent.count(True),
            "dense_kv_tensor_bytes": kv_bytes,
            "recurrent_tensor_bytes": recurrent_bytes,
            "file_plus_cache_tensor_bytes": path.stat().st_size
            + kv_bytes
            + recurrent_bytes,
        },
        "limits": [
            "Tensor-cache terms derived from pinned llama.cpp hybrid layer filters and f16/f32 allocation formulas; backend padding may add bytes.",
            "File length is not an exact resident model allocation. Graph/compute buffers, warmup/load transients, metadata, duplicate tensors and host baseline are additional unknowns.",
            "Do not convert macOS memorystatus percentage into available GiB or copy a Qwen launch cutoff from this estimate.",
            "No model loaded by this script; retain existing85% gate pending a separate bounded runtime probe and review.",
        ],
        "source_paths": [
            "src/models/qwen35moe.cpp",
            "src/llama-model.cpp",
            "src/llama-memory-hybrid.cpp",
            "src/llama-memory-recurrent.cpp",
            "src/llama-hparams.cpp",
            "common/common.cpp",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with args.output.open("x") as destination:
        json.dump(assess(args.model), destination, indent=2)
        destination.write("\n")
