"""Run and audit the eight declared trajectories, one owned server at a time."""

import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PREP = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "runner"))
from build_context_speed_cohort import committed_config
from llama_provenance import verify_llama_runtime
from mei_provenance import verify_mei_runtime

RECEIPT = PREP / "verified-release-delivery.json"
CONFIGS = ROOT / "configs/mei-0.11.0-comparison-20261107"
RUNTIME_PREP = ROOT / "artifacts/mei-upstream-qualification-20261106"
PRESERVE_MEI = RUNTIME_PREP / "preserve_native.py"
AUDIT = ROOT / "artifacts/four-model-retest-v9p10-20261102/audit_run.py"
PROGRESS = PREP / "scored-progress.json"


def read(path):
    return json.loads(path.read_text())


def write(path, data):
    with path.open("x") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def check_ports():
    proc = subprocess.run(
        ["lsof", "-nP", "-iTCP:8017", "-iTCP:8024", "-sTCP:LISTEN"],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 1 or proc.stdout:
        raise ValueError("benchmark ports are not both free")


def bind_configs():
    if PROGRESS.exists():
        raise ValueError("review the existing campaign; never restart it")
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    committed_config(ROOT, str(RECEIPT.relative_to(ROOT)), head, RECEIPT.read_bytes())
    release = read(RECEIPT)
    if (
        release["published_asset_and_installed_artifact_verified"] is not True
        or release["version"] != "0.11.0"
    ):
        raise ValueError("the published and installed Mei release must be verified")
    declared = read(PREP / "campaign.json")
    cases = []
    for cell in declared["cells"]:
        model, seed = cell["model"], cell["seed"]
        name = CONFIGS / f"{model}-seed{seed}.yaml"
        raw = name.read_bytes()
        committed_config(ROOT, str(name.relative_to(ROOT)), head, raw)
        cfg = yaml.safe_load(raw)
        output = ROOT / f"artifacts/mei011-{model}-seed{seed}-20261107"
        if (
            output.exists()
            or cfg["source_revision"] != cell["weight_revision"]
            or cfg["inference_engine"] != cell["engine"]
            or cfg["benchmark_scope"] != "peixinho-standin-v1"
            or cfg["standin_partition"] != "heldout"
            or cfg["python_automation"] is not True
            or cfg["generation_profiles"][cfg["standin_generation_profile"]]["seed"]
            != seed
        ):
            raise ValueError(f"{model}/{seed}: unexpected or reused scoring profile")
        if cfg["inference_engine"] == "mei":
            actual = verify_mei_runtime(cfg)
            expected = {
                "binary_path": release["installed_binary"],
                "mei_source_commit": release["source_revision"],
                "vmlx_commit": release["vmlx_revision"],
                "binary_sha256": release["binary_sha256"],
                "metallib_sha256": release["metallib_sha256"],
            }
            if any(actual[k] != v for k, v in expected.items()):
                raise ValueError(f"{model}/{seed}: differs from the verified release")
        else:
            verify_llama_runtime(cfg)
        cases.append((model, seed, name, cfg, output))
    if len(cases) != 8 or len({(model, seed) for model, seed, *_ in cases}) != 8:
        raise ValueError("requires eight distinct model/seed declarations")
    return cases


def preserve(model, config, cfg, output):
    check_ports()
    if cfg["inference_engine"] == "mei":
        subprocess.run(
            [
                sys.executable,
                str(PRESERVE_MEI),
                "--output",
                str(output),
                "--model-manifest",
                str(RUNTIME_PREP / f"{model}-media-prefix-pre-run-model-hashes.json"),
            ],
            cwd=ROOT,
            check=True,
        )
    else:
        runtime = verify_llama_runtime(cfg)
        argv = shlex.split(cfg["benchmark_launch_command"])
        path = Path(argv[argv.index("--model") + 1])
        with path.open("rb") as f:
            digest = hashlib.file_digest(f, "sha256").hexdigest()
        if digest != cfg["model_sha256"] or path.stat().st_size != cfg["model_bytes"]:
            raise ValueError("GGUF content changed")
        source = Path(f"/tmp/bench_{config.parent.name}_{config.stem}_server.log")
        with source.open("rb") as f, (output / "server.log").open("xb") as out:
            shutil.copyfileobj(f, out)
        write(output / "post-run-runtime-verification.json", runtime)
        write(
            output / "post-run-model-hashes.json",
            {
                "directory": str(path.parent),
                "all_match": True,
                "files": [
                    {
                        "file": path.name,
                        "bytes": cfg["model_bytes"],
                        "sha256": digest,
                        "matches": True,
                    }
                ],
            },
        )


def run(cases):
    progress = {
        "status": "running",
        "completed": [],
        "current": None,
        "pid": os.getpid(),
    }

    def save():
        temporary = PROGRESS.with_suffix(".tmp")
        temporary.write_text(json.dumps(progress, indent=2) + "\n")
        temporary.replace(PROGRESS)

    check_ports()
    with PROGRESS.open("x") as f:
        json.dump(progress, f, indent=2)
        f.write("\n")
    for model, seed, config, cfg, output in cases:
        label = {"model": model, "seed": seed, "output": str(output.relative_to(ROOT))}
        progress["current"] = label
        save()
        try:
            check_ports()
            print(f"START {model} seed{seed}", flush=True)
            result = subprocess.run(
                [
                    sys.executable,
                    "runner/supervise_bench.py",
                    "--config",
                    str(config.relative_to(ROOT)),
                    "--output",
                    str(output),
                    "--deadline",
                    "7200",
                    "--trials",
                    "1",
                ],
                cwd=ROOT,
                check=False,
            )
            outcome = read(output / "outcome.json")
            if outcome["model_started"] and outcome["returncode"] is not None:
                preserve(model, config, cfg, output)
            if (
                result.returncode
                or outcome["returncode"] != 0
                or outcome["stop_reason"] is not None
            ):
                raise ValueError(f"guarded run stopped: {outcome['stop_reason']}")
            ids = outcome["run_ids"]
            if any(
                len(ids.get(track, [])) != 1
                for track in ("peixinho-standin-v1", "python-automation-v1")
            ):
                raise ValueError("requires both complete held-out tracks")
            subprocess.run(
                [sys.executable, str(AUDIT), str(output.relative_to(ROOT)), str(seed)],
                cwd=ROOT,
                check=True,
            )
            audit = read(output / "audit.json")
            if len(audit["household"]) != 12 or len(audit["python"]) != 3:
                raise ValueError("requires all fifteen audited task grades")
            progress["completed"].append(
                {**label, "run_ids": ids, "elapsed_seconds": outcome["elapsed_seconds"]}
            )
            save()
            print(
                f"PASS {model} seed{seed}: both tracks completed and replayed",
                flush=True,
            )
        except (
            OSError,
            ValueError,
            KeyError,
            TypeError,
            subprocess.SubprocessError,
        ) as exc:
            progress.update(
                status="stopped_for_review", error=f"{type(exc).__name__}: {exc}"
            )
            save()
            raise
    progress.update(status="complete", current=None)
    save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    cases = bind_configs()
    if args.preflight_only:
        print("All eight scored profiles verified against the delivery receipt.")
    else:
        run(cases)


if __name__ == "__main__":
    main()
