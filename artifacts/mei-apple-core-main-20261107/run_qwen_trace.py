"""Run one prebuilt Qwen dispatch capture under the native resource guard."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from audit_qwen_trace import identity
from run_campaign import (
    HERE,
    ROOT,
    committed_native_config,
    digest,
    save,
    verify_files,
)
from run_mei_acceptance import monitor_child

EXPANSION = Path("/Volumes/Expansion/local-model-bench")
CONFIG = ROOT / "configs/mei-apple-core-main-20261107/qwen-native.yaml"
DEVELOPER = "/Applications/Xcode.app/Contents/Developer"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path, help="staged and built package")
    parser.add_argument("context", choices=("short", "loaded"))
    parser.add_argument("output", type=Path, help="new capture directory on Expansion")
    parser.add_argument("--test-binary", type=Path, required=True)
    parser.add_argument("--metallib", type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads((HERE / "qwen-decode-trace-plan.json").read_bytes())
    package = args.package.resolve(strict=True)
    output = args.output.resolve()
    for path in (package, output):
        path.relative_to(EXPANSION)
    if output.exists() or package.name not in ("control", "candidate"):
        raise ValueError(
            "use a staged control or candidate and a fresh capture directory"
        )
    if any(shutil.disk_usage(path).free < 23 * 1024**3 for path in (ROOT, EXPANSION)):
        raise ValueError("need 23 GiB of disk headroom on both volumes")

    source = json.loads((package / "trace-source.json").read_bytes())
    if (
        source["core"]
        != plan[f"{'reference' if package.name == 'control' else 'candidate'}_core"]
    ):
        raise ValueError("staged package differs from the declared core revision")
    subprocess.run(
        ["/usr/bin/shasum", "-a", "256", "-c", "trace-inputs.sha256"],
        cwd=package,
        check=True,
    )
    ports = subprocess.run(
        ["/usr/sbin/lsof", "-nP", "-iTCP:8017", "-iTCP:8024", "-sTCP:LISTEN"],
        capture_output=True,
        check=False,
    )
    if ports.returncode != 1 or ports.stdout or ports.stderr:
        raise ValueError("benchmark ports are not both free")

    binary = args.test_binary.resolve(strict=True)
    bundle = binary.parents[2]
    if bundle.suffix != ".xctest" or binary.parent != bundle / "Contents/MacOS":
        raise ValueError("test binary must be inside a macOS XCTest bundle")

    def assets():
        paths = (
            binary,
            args.metallib.resolve(strict=True),
        )
        if paths[0] == paths[1] or paths[1].suffix != ".metallib":
            raise ValueError("provide the test executable and its Metal library")
        return {str(path.relative_to(package)): digest(path) for path in paths}

    before = assets()
    cfg, content = committed_native_config(CONFIG)
    manifest = (HERE / plan["checkpoint_manifest"]).resolve(strict=True)
    model = verify_files(cfg, manifest)
    prompts = (HERE / plan["prompts_file"]).resolve(strict=True)
    prompt = json.loads(prompts.read_bytes())[args.context]
    if (
        hashlib.sha256(prompt.encode()).hexdigest()
        != plan["prompt_sha256"][args.context]
    ):
        raise ValueError("prompt differs from the declared input")
    trace = output / f"{args.context}.gputrace"
    receipt = trace.with_suffix(".gputrace.json")
    env = {
        **cfg["required_runner_environment"],
        "HOME": str(Path.home()),
        "PATH": os.defpath + ":/usr/sbin:/sbin",
        "DEVELOPER_DIR": DEVELOPER,
        "MTL_CAPTURE_ENABLED": "1",
        "VMLX_QWEN_DECODE_CAPTURE": "1",
        "VMLX_QWEN_TRACE_CONTEXT": args.context,
        "VMLX_QWEN_TRACE_PROMPTS": str(prompts),
        "VMLX_QWEN_TRACE_MODEL": model["directory"],
        "VMLX_QWEN_TRACE_OUTPUT": str(trace),
    }
    command = [
        "/usr/bin/env",
        "-i",
        *(f"{key}={value}" for key, value in env.items()),
        "/usr/bin/xcrun",
        "xctest",
        "-XCTest",
        "MLXLMTests.QwenDecodeCaptureTests/testOptInQwenDecodeCapture",
        str(bundle),
    ]
    options = argparse.Namespace(
        output=output,
        deadline=900,
        skip_context=True,
        skip_cache=True,
    )

    def check(_):
        return bool(identity(receipt, plan["expected_templated_tokens"][args.context]))

    code = monitor_child(cfg, content, options, command, diagnostic_check=check)
    post = verify_files(cfg, manifest)
    after = assets()
    save(
        output / "capture-provenance.json",
        {
            "source": source,
            "package": str(package),
            "context": args.context,
            "checkpoint_before": model,
            "checkpoint_after": post,
            "build_assets_before": before,
            "build_assets_after": after,
        },
    )
    return code or int(before != after)


if __name__ == "__main__":
    raise SystemExit(main())
