"""Validate a declared, complete context-speed cohort and export paired figures.

The JSON specification names each serving profile and exactly two predeclared
processes. Each process supplies an id, committed config path/hash and an
artifact output directory. This adapter never discovers or promotes runs.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import re
import shlex
import subprocess
import sys
import textwrap
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml
from bench_common import REPO
from build_agent_leaderboard import within_resource_policy
from capacity_admission import capacity_fits, capacity_plan
from context_speed_summary import (
    SpeedObservation,
    SpeedProfile,
    aggregate_context_speeds,
    context_speed_figure,
)
from mei_clean_speed import verify_receipt
from qualify_llama_context import succeeded as llama_succeeded
from qualify_mei_release import observable, qualification_settings
from qualify_mei_release import succeeded as mei_succeeded
from run_mei_acceptance import split_launch_command
from supervise_bench import baseline_ready


def contained(root: Path, name: str, directory: str) -> Path:
    """Resolve declared evidence only inside its expected repository subtree."""
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise ValueError("evidence paths must be repository-relative")
    base = (root / directory).resolve()
    target = (root / name).resolve()
    if not target.is_relative_to(base) or target == base:
        raise ValueError(f"evidence must be contained in {directory}")
    return target


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def validate_resources(output: Path, cfg: dict, invocation: dict) -> None:
    baseline = [
        json.loads(line)
        for line in (output / "baseline.jsonl").read_text().splitlines()
        if line.strip()
    ]
    resources = [
        json.loads(line)
        for line in (output / "resources.jsonl").read_text().splitlines()
        if line.strip()
    ]
    plan = capacity_plan(cfg)
    count = cfg.get("resource_monitor_policy", {}).get("launch_baseline_samples")
    if (
        type(count) is not int
        or count < 7
        or len(baseline) != count
        or plan is None
        or invocation.get("capacity_plan") != plan
        or not baseline_ready(baseline, None, 0)
        or not capacity_fits(plan, baseline)
        or not within_resource_policy(resources, baseline[-1], capacity=True)
    ):
        raise ValueError("run does not reproduce its capacity and resource guards")


def committed_config(root: Path, name: str, revision: str, snapshot: bytes) -> None:
    """A matching working-tree file alone does not establish pre-run declaration."""
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{12,40}", revision):
        raise ValueError("supervisor must record a pinned runner revision")
    result = subprocess.run(
        ["git", "-C", str(root), "show", f"{revision}:{name}"],
        check=False,
        capture_output=True,
    )
    if result.returncode or result.stdout != snapshot:
        raise ValueError("config was not committed at the recorded runner revision")


def validate_mei(
    output: Path, cfg: dict, config_bytes: bytes, digest: str, model_manifest: dict
) -> dict:
    """Reproduce the original arm audit, identity and raw response checks."""
    if not mei_succeeded(output):
        raise ValueError("Mei process did not complete qualification")
    # These are the same strict auditors used to preserve the qualification
    # campaign. Import locally so the standalone plotting module stays generic.
    audit_dir = REPO / "artifacts/mei-stable-qualification-20261102"
    if str(audit_dir) not in sys.path:
        sys.path.insert(0, str(audit_dir))
    audit = importlib.import_module("run_matrix").audit
    validate_identity = importlib.import_module(
        "summarize_bounded_allocator"
    ).validate_identity

    result = read_json(output / "qualification.json")
    post = read_json(output / "post-run-runtime-verification.json")
    validate_identity(
        (output / "config.yaml").read_bytes(),
        config_bytes,
        digest,
        result,
        post,
        (output / "server.log").read_text(),
    )
    if audit(output, None) != read_json(output / "qualification-audit.json"):
        raise ValueError("saved Mei audit does not reproduce")
    if result["settings"] != qualification_settings(cfg):
        raise ValueError("Mei qualification settings changed")
    prompts = read_json(output / "prompts.json")
    if prompts.keys() != {"short", "loaded"} or result["prompt_sha256"] != {
        name: hashlib.sha256(prompt.encode()).hexdigest()
        for name, prompt in prompts.items()
    }:
        raise ValueError("Mei prompt evidence changed")
    for row in result["rows"]:
        if observable(row["response"]) != row["observable"] or (
            row["decode_tps"] != row["response"]["usage"]["tokens_per_second"]
        ):
            raise ValueError("Mei raw response does not reproduce recorded metrics")
    hashes = read_json(output / "post-run-model-hashes.json")
    command = split_launch_command(cfg["benchmark_launch_command"])
    if (
        not hashes.get("all_match")
        or not hashes.get("files")
        or not all(row.get("matches") is True for row in hashes["files"])
        or Path(hashes["directory"]).resolve()
        != Path(command[command.index("--model-dir") + 1]).resolve()
    ):
        raise ValueError("Mei post-run model hash evidence is incomplete")

    def file_identity(record: dict) -> tuple:
        return record["file"], record["bytes"], record["sha256"]

    if Path(model_manifest["directory"]).resolve() != Path(
        hashes["directory"]
    ).resolve() or sorted(map(file_identity, model_manifest["files"])) != sorted(
        map(file_identity, hashes["files"])
    ):
        raise ValueError("post-run model files differ from the pinned pre-run manifest")
    return result


def load_cohort(
    root: Path, specification: dict
) -> tuple[list[SpeedProfile], list[SpeedObservation]]:
    """Validate process evidence before passing measured rows to the aggregator.

    Each profile declares model, model_id, engine, model_revision, runtime_sha256,
    short_tokens, long_tokens, color and two process records (id, config,
    config_sha256, output). Mei profiles also declare metallib_sha256 and a
    model_manifest/model_manifest_sha256 pair. Paths are relative to
    root; output/config snapshots and invocation hashes must
    match exactly. Native engine TPS conventions are deliberately retained.
    """
    root = root.resolve()
    profiles, observations = [], []
    declared_profiles = specification.get("profiles")
    if not isinstance(declared_profiles, list) or not declared_profiles:
        raise ValueError("declare at least one complete context-speed profile")
    seen_outputs: set[Path] = set()
    for spec in declared_profiles:
        engine = spec["engine"]
        processes = spec["processes"]
        if (
            engine not in {"mei", "llama.cpp"}
            or not isinstance(processes, list)
            or len(processes) != 2
        ):
            raise ValueError("each profile needs an engine and two declared processes")
        if not re.fullmatch(r"[0-9a-f]{64}", spec["runtime_sha256"]):
            raise ValueError("require an exact runtime SHA256")
        if engine == "mei" and not re.fullmatch(
            r"[0-9a-f]{64}", spec["metallib_sha256"]
        ):
            raise ValueError("Mei profiles require an exact Metal SHA256")
        profile = SpeedProfile(
            spec["model"],
            engine,
            spec["runtime_sha256"],
            spec["model_revision"],
            (processes[0]["id"], processes[1]["id"]),
            spec["short_tokens"],
            spec["long_tokens"],
        )
        profiles.append(profile)
        model_manifest = None
        if engine == "mei":
            manifest_path = contained(root, spec["model_manifest"], "artifacts")
            if (
                hashlib.sha256(manifest_path.read_bytes()).hexdigest()
                != spec["model_manifest_sha256"]
            ):
                raise ValueError("Mei pre-run model manifest differs from its pin")
            model_manifest = read_json(manifest_path)
            if model_manifest.get("all_match") is not True or not model_manifest.get(
                "files"
            ):
                raise ValueError("Mei pre-run model manifest is incomplete")
        elif not re.fullmatch(r"[0-9a-f]{64}", spec["model_sha256"]):
            raise ValueError("llama.cpp profiles require an exact model SHA256")
        process_profile = None
        prompt_hashes = None
        for process in processes:
            config = contained(root, process["config"], "configs")
            output = contained(root, process["output"], "artifacts")
            if output in seen_outputs:
                raise ValueError("a process output cannot be reused")
            seen_outputs.add(output)
            config_bytes = config.read_bytes()
            digest = hashlib.sha256(config_bytes).hexdigest()
            if (
                digest != process["config_sha256"]
                or (output / "config.yaml").read_bytes() != config_bytes
            ):
                raise ValueError(
                    "declared config and saved snapshot must match their pin"
                )
            invocation = read_json(output / "invocation.json")
            if invocation.get("config_sha256") != digest:
                raise ValueError("supervisor config identity does not match")
            committed_config(
                root, process["config"], invocation.get("runner_git_sha"), config_bytes
            )
            outcome = read_json(output / "outcome.json")
            if (
                outcome.get("status") != "passed"
                or outcome.get("returncode") != 0
                or outcome.get("stop_reason") is not None
            ):
                raise ValueError("partial or failed processes cannot be plotted")
            cfg = yaml.safe_load(config_bytes)
            validate_resources(output, cfg, invocation)
            if (
                cfg.get("inference_engine") != engine
                or cfg.get("model") != spec["model_id"]
                or cfg.get("source_revision") != spec["model_revision"]
            ):
                raise ValueError("model, engine or revision differs from declaration")
            command = (
                split_launch_command(cfg["benchmark_launch_command"])
                if engine == "mei"
                else shlex.split(cfg["benchmark_launch_command"])
            )
            if engine == "mei":
                receipt = read_json(output / "clean-speed-launch.json")
                verify_receipt(
                    root,
                    cfg,
                    command,
                    invocation,
                    receipt,
                    output / "launcher-executed.sh",
                    output / "stopper-executed.sh",
                )
            for flag in ("--request-log", "--runtime-base", "--kv-cache-dir"):
                if flag in command:
                    if command.count(flag) != 1:
                        raise ValueError("ambiguous process-owned path")
                    command[command.index(flag) + 1] = "<owned-path>"
            environment = dict(cfg.get("required_runner_environment", {}))
            environment.pop("MEI_RUNTIME_BASE", None)
            clean_environment = None
            if engine == "mei":
                if "[vmlx][cache/" in (output / "server.log").read_text():
                    raise ValueError("Mei timing log contains active cache tracing")
                clean_environment = dict(cfg["mei_clean_speed_launch"]["environment"])
                clean_environment.pop("MEI_RUNTIME_BASE", None)
            identity = (command, environment, clean_environment)
            if process_profile is None:
                process_profile = identity
            elif process_profile != identity:
                raise ValueError("context repeats changed the serving profile")
            if engine == "mei":
                assert model_manifest is not None
                art = cfg["mei_release_artifact"]
                if (
                    art["binary_sha256"] != spec["runtime_sha256"]
                    or art["metallib_sha256"] != spec["metallib_sha256"]
                ):
                    raise ValueError("Mei binary or Metal identity differs")
                result = validate_mei(output, cfg, config_bytes, digest, model_manifest)
                if (
                    result.get("clean_speed_launch_required") is not True
                    or result.get("clean_speed_launch") != receipt
                ):
                    raise ValueError(
                        "qualification result does not confirm the clean launcher receipt"
                    )
                if result.get("model") != cfg["orchestration"]["served_model_id"]:
                    raise ValueError("Mei served-model identity differs")
                if (
                    result["settings"]["loaded_tokens"] != spec["long_tokens"]
                    or result["settings"]["decode_tokens"] != 128
                    or result["settings"]["repeats"] != 5
                ):
                    raise ValueError("Mei measurement plan differs")
            else:
                if (
                    cfg["runtime"]["binary_sha256"] != spec["runtime_sha256"]
                    or cfg["model_sha256"] != spec["model_sha256"]
                    or not llama_succeeded(output)
                ):
                    raise ValueError("llama.cpp identity or complete raw audit failed")
                result = read_json(output / "qualification.json")
                if result["command"] != shlex.split(cfg["benchmark_launch_command"]):
                    raise ValueError("llama.cpp observed launch differs")
                prompts = read_json(output / "prompts.json")
                if (
                    len(prompts["short"]) != spec["short_tokens"]
                    or len(prompts["loaded"]) != spec["long_tokens"]
                ):
                    raise ValueError("llama.cpp prompt lengths differ")
            if prompt_hashes is None:
                prompt_hashes = result["prompt_sha256"]
            elif prompt_hashes != result["prompt_sha256"]:
                raise ValueError("context repeats changed the actual prompt tokens")
            for row in result["rows"]:
                if row["phase"] != "measured":
                    continue
                fields = row["observable"]
                observations.append(
                    SpeedObservation(
                        spec["model"],
                        process["id"],
                        spec["runtime_sha256"],
                        spec["model_revision"],
                        "long" if row["context"] == "loaded" else row["context"],
                        row["repeat"],
                        fields["prompt_tokens"],
                        fields["completion_tokens"],
                        row["decode_tps"],
                    )
                )
    return profiles, observations


def export(root: Path, specification: dict, destination: Path) -> None:
    """Refuse collisions and incomplete evidence before writing any graph."""
    if any(destination.with_suffix(ext).exists() for ext in (".png", ".svg", ".json")):
        raise FileExistsError("refuse to overwrite existing context-speed evidence")
    profiles, observations = load_cohort(root, specification)
    averages = aggregate_context_speeds(profiles, observations)
    colors = {item["model"]: item["color"] for item in specification["profiles"]}
    provenance = (
        "Two processes × five measured decodes per context; 128 generated tokens. "
        "Native engine decode rates use their own timing conventions.\n"
        + textwrap.fill(
            "Runtime/model revision pins: "
            + "; ".join(
                f"{p.model} {p.runtime_sha256[:12]}/{p.model_revision[:12]}"
                for p in profiles
            ),
            width=100,
        )
        + "\n"
        + specification["provenance"]
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    context_speed_figure(
        averages,
        destination,
        title=specification["title"],
        provenance=provenance,
        colors=colors,
    )
    with destination.with_suffix(".json").open("x") as stream:
        json.dump(
            {
                "specification": specification,
                "averages": [asdict(p) for p in averages],
                "observations": [asdict(r) for r in observations],
            },
            stream,
            indent=2,
        )
        stream.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path, required=True, help="fresh PNG/SVG/JSON destination stem"
    )
    args = parser.parse_args()
    export(REPO, read_json(args.spec), args.output)


if __name__ == "__main__":
    main()
