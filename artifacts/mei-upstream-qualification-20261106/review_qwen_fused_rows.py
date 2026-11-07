"""Audit the complete same-binary row-sharing screen; never promote a release."""

import copy
import hashlib
import json
import math
import shlex
import statistics
import sys

import yaml
from run_speed_matrix import PREP, ROOT, audit, baseline_references

sys.path.insert(0, str(ROOT / "runner"))
from build_context_speed_cohort import validate_resources


def read(path):
    return json.loads(path.read_text())


def review():
    matrix = read(PREP / "qwen-fused-rows-screen-20261107.json")
    progress = read(PREP / "qwen-fused-rows-screen-progress-20261107.json")
    expected = [("qwen", arm) for arm in ("a", "b")]
    if (
        progress["status"] != "measurement_cells_complete"
        or progress["current"] is not None
        or [(c["model"], c["cell"]) for c in progress["completed"]] != expected
        or [(c["model"], c["cell"]) for c in matrix["cells"]] != expected
    ):
        raise ValueError("requires both terminal predeclared diagnostic arms")
    reference = baseline_references(matrix)["qwen"]
    rows = []
    signature = None
    files = None
    prompts = None
    for cell, finished in zip(matrix["cells"], progress["completed"], strict=True):
        if any(cell[k] != finished[k] for k in ("model", "cell", "config", "output")):
            raise ValueError("completed cell differs from declaration")
        output = (ROOT / cell["output"]).resolve()
        config = (ROOT / cell["config"]).resolve()
        if not output.is_relative_to(ROOT / "artifacts") or not config.is_relative_to(
            ROOT / "configs"
        ):
            raise ValueError("evidence/config must remain in declared directories")
        raw = config.read_bytes()
        cfg = yaml.safe_load(raw)
        invocation = read(output / "invocation.json")
        if (
            raw != (output / "config.yaml").read_bytes()
            or hashlib.sha256(raw).hexdigest() != invocation["config_sha256"]
        ):
            raise ValueError("launch snapshot/config hash mismatch")
        validate_resources(output, cfg, invocation)
        checked = audit(output, reference)
        if checked != read(output / "qualification-audit.json"):
            raise ValueError("saved observable/resource audit does not reproduce")
        normalized = copy.deepcopy(cfg)
        environment = normalized["required_runner_environment"]
        base = environment.pop("MEI_RUNTIME_BASE")
        flag = environment.pop("VMLX_GDN_SHARE_FUSED_ROWS")
        if flag != {"a": "1", "b": "0"}[cell["cell"]]:
            raise ValueError("unexpected row-sharing treatment")
        normalized.pop("benchmark_status")
        normalized["benchmark_launch_command"] = [
            arg.replace(base, "<owned-runtime>")
            for arg in shlex.split(normalized["benchmark_launch_command"])
        ]
        current_prompts = read(output / "prompts.json")
        hashes = read(output / "post-run-model-hashes.json")
        current_files = sorted(
            (r["file"], r["bytes"], r["sha256"]) for r in hashes["files"]
        )
        if signature is None:
            signature, prompts, files = normalized, current_prompts, current_files
        elif (
            normalized != signature
            or current_prompts != prompts
            or current_files != files
        ):
            raise ValueError("arms differ beyond row sharing/owned paths/status prose")
        cleanup = read(output / "owned-kv-cleanup.json")
        if (
            not hashes["all_match"]
            or len(current_files) != 15
            or not all(r["matches"] for r in hashes["files"])
            or not cleanup["server_exited"]
            or not cleanup["deleted"]
        ):
            raise ValueError("model integrity or terminal cleanup incomplete")
        q = read(output / "qualification.json")
        if (
            q["command"] != shlex.split(cfg["benchmark_launch_command"])
            or q["model"] != cfg["orchestration"]["served_model_id"]
        ):
            raise ValueError("recorded command/served model differs from snapshot")
        post = read(output / "post-run-runtime-verification.json")
        identity = {
            "mei_source_commit": cfg["mei_source_commit"],
            "vmlx_commit": cfg["vmlx_commit"],
            "binary_sha256": cfg["mei_release_artifact"]["binary_sha256"],
            "metallib_sha256": cfg["mei_release_artifact"]["metallib_sha256"],
        }
        if any(
            observed.get(k) != v
            for observed in (q["runtime_identity"], post)
            for k, v in identity.items()
        ):
            raise ValueError("runtime artifact/source identity mismatch")
        http = q["swift_acceptance"]
        if (
            not http["passed"]
            or http["returncode"] != 0
            or http["expected_tests"] != 9
            or http["journal_requests"] != 9
            or q["normal_output_budget"] != 8192
            or not q["status_samples"]
            or not all(r["ok"] for r in q["status_samples"])
            or not any(r["active_generations"] > 0 for r in q["status_samples"])
            or "fused_gdn_decode_input_projections=active groups=[4]"
            not in (output / "server.log").read_text()
        ):
            raise ValueError(
                "requires live API/status and active fused-projection proof"
            )
        resources = [
            json.loads(line)
            for line in (output / "resources.jsonl").read_text().splitlines()
        ]
        footprints = [
            process["phys_footprint_bytes"]
            for sample in resources
            for process in sample["owned_processes"]
            if process["comm"].endswith("/mei")
        ]
        if not footprints:
            raise ValueError("requires owned server physical-footprint observations")
        for context in ("short", "loaded"):
            measured = [
                r
                for r in q["rows"]
                if r["context"] == context and r["phase"] == "measured"
            ]
            metrics = {
                "wall_seconds": [r["elapsed_seconds"] for r in measured],
                "prefill_seconds": [
                    r["response"]["usage"]["prefill_ms"] / 1000 for r in measured
                ],
                "generation_seconds": [
                    r["response"]["usage"]["generate_ms"] / 1000 for r in measured
                ],
                "decode_tps": [r["decode_tps"] for r in measured],
            }
            if any(
                len(values) != 5 or any(not math.isfinite(v) or v <= 0 for v in values)
                for values in metrics.values()
            ):
                raise ValueError("requires five finite positive measured values")
            rows.append(
                {
                    "arm": cell["cell"],
                    "row_sharing": flag,
                    "context": context,
                    "metrics": {
                        key: {
                            "mean": statistics.mean(values),
                            "median": statistics.median(values),
                            "values": values,
                        }
                        for key, values in metrics.items()
                    },
                    "process_peak_phys_footprint_bytes": max(footprints),
                }
            )
    return {
        "status": "complete_diagnostic_observations_review_required",
        "scope": "Same binary/source/model, one declared row-sharing flag difference.28 observable rows,20 measured requests,18 live API cases,30 unchanged model-file checks. No old timings pooled. One process/arm is a mechanism screen, not statistical or stable qualification; physical peaks include process/system variation. Phase counters retain native boundaries and are not additive. No production duplicate-weight policy recommendation.",
        "rows": rows,
    }


if __name__ == "__main__":
    result = review()
    with (PREP / "qwen-fused-rows-review-20261107.json").open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print("Both same-binary diagnostic arms audited; interpretation remains manual")
