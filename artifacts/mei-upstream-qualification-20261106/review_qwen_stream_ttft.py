"""Review the completed Qwen streaming matrix without running a model."""

import json
import math
import statistics
import sys
from pathlib import Path

from review_attention_selector import snapshot
from run_speed_matrix import PREP, ROOT, audit

sys.path.insert(0, str(ROOT / "runner"))
from build_context_speed_cohort import validate_resources
from qualify_mei_release import succeeded

ORDER = ("a1", "b1", "c1", "c2", "b2", "a2")
FIELDS = (
    "headers_seconds",
    "first_generated_seconds",
    "first_visible_seconds",
    "prefill_seconds",
    "wall_seconds",
    "decode_tps",
)


def read(path: Path) -> dict:
    return json.loads(path.read_text())


def process_means(rows: list[dict]) -> dict:
    contexts = {}
    for context in ("short", "loaded"):
        measurements = [
            r for r in rows if r["context"] == context and r["phase"] == "measured"
        ]
        if sorted(row["repeat"] for row in measurements) != [1, 2, 3, 4, 5]:
            raise ValueError("each process needs five measured repeats per context")
        metrics = {field: [] for field in FIELDS}
        for row in measurements:
            response = row["response"]
            for field in FIELDS:
                if field == "prefill_seconds":
                    value = response["usage"]["prefill_ms"] / 1000
                elif field == "decode_tps":
                    value = row["decode_tps"]
                else:
                    value = response[field]
                if value is None and field == "first_visible_seconds":
                    metrics[field].append(None)
                elif (
                    type(value) not in (int, float)
                    or not math.isfinite(value)
                    or value < 0
                ):
                    raise ValueError(f"invalid {field} measurement")
                else:
                    metrics[field].append(value)
        contexts[context] = {
            field: {
                "samples": values,
                "mean": statistics.mean(values) if None not in values else None,
            }
            for field, values in metrics.items()
        }
    return contexts


def review() -> dict:
    matrix = read(PREP / "qwen-stream-ttft-matrix.json")
    progress = read(PREP / "qwen-stream-ttft-progress.json")
    if (
        tuple(cell["cell"] for cell in matrix["cells"]) != ORDER
        or progress["status"] != "measurement_cells_complete"
        or progress["current"] is not None
        or [
            {k: v for k, v in row.items() if k != "audit"}
            for row in progress["completed"]
        ]
        != matrix["cells"]
    ):
        raise ValueError("requires all six declared streaming cells to finish")
    pin = read(PREP / "qwen-media-prefix-pre-run-model-hashes.json")
    initial = read(PREP / "qwen-stream-ttft-initial-readback.json")
    model = Path(pin["directory"]).resolve(strict=True)
    if (
        initial["config"] != matrix["cells"][0]["config"]
        or type(initial["elapsed_seconds"]) not in (int, float)
        or not 0 < initial["elapsed_seconds"] < math.inf
        or initial["files"]
        != [
            {
                "path": str(model / row["file"]),
                "bytes": row["bytes"],
                "sha256": row["sha256"],
            }
            for row in pin["files"]
        ]
    ):
        raise ValueError("initial Expansion checkpoint readback differs from its pin")
    reference = prompts = None
    result = {}
    for cell in matrix["cells"]:
        name = cell["cell"]
        output, cfg, invocation = snapshot(cell)
        run = read(output / "qualification.json")
        checked = audit(output, reference)
        identity = {
            "binary_sha256": cfg["mei_release_artifact"]["binary_sha256"],
            "metallib_sha256": cfg["mei_release_artifact"]["metallib_sha256"],
            "mei_source_commit": cfg["mei_source_commit"],
            "vmlx_commit": cfg["vmlx_commit"],
        }
        after = read(output / "post-run-model-hashes.json")
        loader = (output / "server.log").read_text()
        marker = {
            "a": " mmap=true ",
            "b": " mmap=false ",
            "c": "mei: weight storage owned;",
        }[name[0]]
        if (
            not succeeded(output)
            or run.get("measurement_mode") != "uncached_chat_stream"
            or checked != read(output / "qualification-audit.json")
            or not read(output / "owned-kv-cleanup.json")["server_exited"]
            or after["all_match"] is not True
            or after["files"] != [row | {"matches": True} for row in pin["files"]]
            or marker not in loader
            or any(
                record[k] != v
                for record in (
                    run["runtime_identity"],
                    read(output / "post-run-runtime-verification.json"),
                )
                for k, v in identity.items()
            )
        ):
            raise ValueError(
                f"incomplete streamed evidence or loader readback for {name}"
            )
        validate_resources(output, cfg, invocation)
        reference = checked["reference"]
        current_prompts = read(output / "prompts.json")
        if prompts is not None and prompts != current_prompts:
            raise ValueError("prompt bytes changed across streaming cells")
        prompts = current_prompts
        result[name] = {
            "weight_path": cell["weight_path"],
            "contexts": process_means(run["rows"]),
        }
    arms = {}
    for arm in "abc":
        arms[arm] = {}
        for context in ("short", "loaded"):
            means = [result[f"{arm}{i}"]["contexts"][context] for i in (1, 2)]
            arms[arm][context] = {
                field: statistics.mean([m[field]["mean"] for m in means])
                if all(m[field]["mean"] is not None for m in means)
                else None
                for field in FIELDS
            }
    return {
        "scope": "Uncached chat; equal weight for five requests per process and two processes per arm. Missing visible output stays unavailable.",
        "matched_prompt_tokens": {
            name: row["prompt_tokens"] for name, row in reference.items()
        },
        "initial_checkpoint_readback_seconds": initial["elapsed_seconds"],
        "processes": result,
        "arm_averages": arms,
    }


if __name__ == "__main__":
    print(json.dumps(review(), indent=2))
