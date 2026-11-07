"""Reproduce exact candidate evidence and compare it with the declared controls."""

import argparse
import hashlib
import json
import math
import statistics
import sys

import yaml
from run_speed_matrix import PREP, ROOT, baseline_references

sys.path.insert(0, str(ROOT / "runner"))
from build_context_speed_cohort import (
    committed_config,
    load_cohort,
    validate_resources,
)
from qualify_mei_release import observable
from run_mei_acceptance import probe_succeeded
from verify_combined_cohorts import declared_profile, model_files

PROTOCOL = PREP / "attention-selector-qualification-protocol-20261107.json"
PREVIOUS_SPEED_SPEC = (
    ROOT
    / "artifacts/mei011-comparison-preparation-20261106/qualified-context-speed-inputs.json"
)
MODELS = ("qwen", "ornith", "groot")
METRICS = {
    "decode_tps": lambda row: row["decode_tps"],
    "wall_seconds": lambda row: row["elapsed_seconds"],
    "prefill_seconds": lambda row: row["response"]["usage"]["prefill_ms"] / 1000,
    "generate_seconds": lambda row: row["response"]["usage"]["generate_ms"] / 1000,
}


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def matches_identity(record, expected):
    return all(record.get(key) == value for key, value in expected.items())


def snapshot(cell):
    config = ROOT / cell["config"]
    directory = ROOT / cell["output"]
    invocation = read(directory / "invocation.json")
    if config.read_bytes() != (directory / "config.yaml").read_bytes() or invocation[
        "config_sha256"
    ] != digest(config):
        raise ValueError("configuration evidence differs from pre-run declaration")
    committed_config(
        ROOT, cell["config"], invocation["runner_git_sha"], config.read_bytes()
    )
    return directory, yaml.safe_load(config.read_bytes()), invocation


def check_native(cell, expected, before):
    directory, cfg, invocation = snapshot(cell)
    outcome = read(directory / "outcome.json")
    record = read(directory / "record.json")
    if (
        outcome["status"] != "passed"
        or outcome["returncode"] != 0
        or outcome["full_native_admission"] is not True
        or not probe_succeeded(directory, skip_context=False, skip_cache=False)
        or not matches_identity(record["runtime_identity"], expected)
        or not matches_identity(
            read(directory / "post-run-runtime-verification.json"), expected
        )
        or model_files(read(directory / "post-run-model-hashes.json")) != before
        or not read(directory / "owned-kv-cleanup.json")["server_exited"]
    ):
        raise ValueError(
            f"{cell['model']}: incomplete native runtime or model evidence"
        )
    validate_resources(directory, cfg, invocation)
    probes = read(directory / "probe.json")["probes"]
    if len(probes) != 13:
        raise ValueError("expected exactly thirteen native probes")
    return {"output": cell["output"], "probes": len(probes), "model_files": len(before)}


def process_timings(directories, reference, prompts):
    values = {}
    for directory in directories:
        result = read(directory / "qualification.json")
        if read(directory / "prompts.json") != prompts:
            raise ValueError("prompt bytes differ from the recorded controls")
        if any(
            observable(row["response"]) != reference[row["context"]]
            for row in result["rows"]
        ):
            raise ValueError("observable differs from the recorded controls")
        for context in ("short", "loaded"):
            rows = [
                row
                for row in result["rows"]
                if row["context"] == context and row["phase"] == "measured"
            ]
            if len(rows) != 5:
                raise ValueError("requires five measured requests per context")
            for metric, measure in METRICS.items():
                samples = [measure(row) for row in rows]
                if any(not math.isfinite(value) or value <= 0 for value in samples):
                    raise ValueError("invalid phase measurement")
                values.setdefault((context, metric), []).append(
                    statistics.mean(samples)
                )
    return values


def comparison(candidate, control):
    rows = []
    for (context, metric), new in candidate.items():
        prior = control[context, metric]
        if len(new) != 2 or len(prior) != 2:
            raise ValueError("requires two process means per leg")
        change = (statistics.mean(new) / statistics.mean(prior) - 1) * 100
        rows.append(
            {
                "context": context,
                "metric": metric,
                "candidate_process_means": new,
                "control_process_means": prior,
                "change_percent": change,
                "both_above": min(new) > max(prior),
                "both_below": max(new) < min(prior),
            }
        )
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--timing-attempt", choices=("original", "retry"), default="original"
    )
    parser.add_argument("--model", choices=MODELS)
    parser.add_argument(
        "--speed-spec",
        action="store_true",
        help="print complete validated publication input",
    )
    args = parser.parse_args()
    if args.model and args.speed_spec:
        parser.error("publication speed input requires all four profiles")
    models = (args.model,) if args.model else MODELS
    protocol = read(PROTOCOL)
    candidate = read(PREP / "attention-selector-artifact.json")
    expected = {
        "mei_source_commit": candidate["source_revision"],
        "vmlx_commit": candidate["vmlx_revision"],
        "binary_sha256": candidate["binary_sha256"],
        "metallib_sha256": candidate["metallib_sha256"],
    }
    if candidate["source_revision"] != protocol["candidate_source"]:
        raise ValueError("unexpected production source")
    native = read(PREP / "attention-selector-native-campaign.json")["cells"]
    stem = "attention-selector-speed" + (
        "-retry" if args.timing_attempt == "retry" else ""
    )
    matrix = read(PREP / f"{stem}-matrix.json")
    refs = baseline_references(matrix)
    prior_matrix = read(PREP / "apple-main-speed-matrix.json")["cells"]
    progress = read(PREP / f"{stem}-progress.json")
    if args.model is None and (
        progress["status"] != "measurement_cells_complete"
        or progress["current"] is not None
        or len(progress["completed"]) != 6
    ):
        raise ValueError("complete review requires the terminal six-cell matrix")
    old_spec = read(PREVIOUS_SPEED_SPEC)
    reports, fresh_profiles = {}, []
    for model in models:
        (native_cell,) = [c for c in native if c["model"] == model]
        spec = old_spec["profiles"][MODELS.index(model)]
        before = model_files(read(ROOT / spec["model_manifest"]))
        native_proof = check_native(native_cell, expected, before)
        cells = [c for c in matrix["cells"] if c["model"] == model]
        if [c["cell"] for c in progress["completed"] if c["model"] == model] != [
            "b1",
            "b2",
        ]:
            raise ValueError(f"{model}: requires both fresh production processes")
        prior_cells = [c for c in prior_matrix if c["model"] == model]
        previous, stable = [
            [ROOT / c["output"] for c in prior_cells if c["cell"].startswith(arm)]
            for arm in ("b", "a")
        ]
        prompts = read(previous[0] / "prompts.json")
        ref = refs[model]
        outputs = []
        spec.update(
            runtime_sha256=expected["binary_sha256"],
            metallib_sha256=expected["metallib_sha256"],
        )
        spec["processes"] = []
        status_samples = []
        previous_config = yaml.safe_load((previous[0] / "config.yaml").read_text())
        for cell in cells:
            output, cfg, _ = snapshot(cell)
            if (
                declared_profile(cfg)[:6] != declared_profile(previous_config)[:6]
                or model_files(read(output / "post-run-model-hashes.json")) != before
                or not matches_identity(
                    read(output / "post-run-runtime-verification.json"), expected
                )
            ):
                raise ValueError(
                    f"{model}: production runtime/profile evidence differs"
                )
            observed = read(output / "qualification.json")
            live_api = observed["swift_acceptance"]
            active = [
                r for r in observed["status_samples"] if r["active_generations"] > 0
            ]
            if (
                not matches_identity(observed["runtime_identity"], expected)
                or not live_api["passed"]
                or live_api["returncode"] != 0
                or live_api["expected_tests"] != 9
                or live_api["journal_requests"] != 9
                or not active
                or not all(r["ok"] for r in observed["status_samples"])
            ):
                raise ValueError(f"{model}: live API or active status proof incomplete")
            status_samples.append(
                {
                    "output": cell["output"],
                    "active_samples": len(active),
                    "max_active_status_seconds": max(
                        r["elapsed_seconds"] for r in active
                    ),
                }
            )
            outputs.append(output)
            spec["processes"].append(
                {
                    "id": f"{model}-{cell['cell']}",
                    "config": cell["config"],
                    "config_sha256": digest(ROOT / cell["config"]),
                    "output": cell["output"],
                }
            )
        _, observations = load_cohort(ROOT, {"profiles": [spec]})
        if len(observations) != 20:
            raise ValueError("unexpected number of validated measurements")
        new = process_timings(outputs, ref, prompts)
        vs_previous = comparison(new, process_timings(previous, ref, prompts))
        vs_stable = comparison(new, process_timings(stable, ref, prompts))
        reports[model] = {
            "native": native_proof,
            "live_api_cases": 18,
            "active_status": status_samples,
            "vs_pre_selector_011": vs_previous,
            "vs_stable_010": vs_stable,
            "material_regression_review": [
                row
                for row in vs_previous
                if (
                    row["metric"] == "decode_tps"
                    and row["both_below"]
                    and row["change_percent"] <= -3
                    or row["metric"] == "wall_seconds"
                    and row["both_above"]
                    and row["change_percent"] >= 3
                )
            ],
        }
        if model == "qwen":
            decode = next(
                r
                for r in vs_previous
                if (r["context"], r["metric"]) == ("loaded", "decode_tps")
            )
            reports[model]["meets_loaded_recovery_criterion"] = (
                decode["both_above"] and decode["change_percent"] >= 3.7193696799372233
            )
        fresh_profiles.append(spec)
    if args.speed_spec:
        new_spec = {**old_spec, "profiles": [*fresh_profiles, old_spec["profiles"][-1]]}
        _, observations = load_cohort(ROOT, new_spec)
        if len(observations) != 80:
            raise ValueError("requires all eighty fresh measurements")
        print(json.dumps(new_spec, indent=2))
        return
    print(
        json.dumps(
            {
                "scope": "Exact production artifact, two new guarded processes per model compared with separate control windows. Not a new interleaved ABBA or a task-score claim.",
                "artifact": candidate,
                "models": reports,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
