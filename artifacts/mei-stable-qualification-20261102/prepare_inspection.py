"""Make inspection-only signed copies, proving all Mach-O sections unchanged."""

import copy
import hashlib
import json
import plistlib
import shlex
import shutil
import struct
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PREP = Path(__file__).resolve().parent


def sections(data):
    if len(data) < 32 or struct.unpack_from("<I", data)[0] != 0xFEEDFACF:
        raise ValueError("requires a thin little-endian 64-bit Mach-O")
    count, command_bytes = struct.unpack_from("<II", data, 16)
    end = 32 + command_bytes
    if end > len(data):
        raise ValueError("truncated Mach-O commands")
    offset = 32
    result = {}
    for _ in range(count):
        if offset + 8 > end:
            raise ValueError("truncated command")
        command, size = struct.unpack_from("<II", data, offset)
        if size < 8 or offset + size > end:
            raise ValueError("invalid command size")
        if command == 0x19:
            if size < 72:
                raise ValueError("truncated segment")
            nsections = struct.unpack_from("<I", data, offset + 64)[0]
            if 72 + nsections * 80 > size:
                raise ValueError("truncated section table")
            for index in range(nsections):
                start = offset + 72 + index * 80
                name, segment, _, length, position, _, _, _, flags = struct.unpack_from(
                    "<16s16sQQIIIII", data, start
                )
                key = segment.rstrip(b"\0").decode() + ":" + name.rstrip(b"\0").decode()
                if key in result:
                    raise ValueError("duplicate section identity")
                # Zero-fill sections have no file payload to compare.
                if flags & 0xFF in (1, 0xC, 0x12):
                    payload = b""
                else:
                    if position + length > len(data):
                        raise ValueError("truncated section payload")
                    payload = data[position : position + length]
                result[key] = {
                    "size": length,
                    "flags": flags,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }
        offset += size
    if offset != end or "__TEXT:__text" not in result:
        raise ValueError("incomplete command table or missing executable code")
    return result


def prepare_runtime(name, original):
    identity = json.loads((PREP / original).read_text())
    source = Path(identity["files"][0]["file"])
    before = source.read_bytes()
    if hashlib.sha256(before).hexdigest() != identity["files"][0]["sha256"]:
        raise ValueError("frozen original changed")
    target = source.parent.parent / f"inspection-{name}"
    target.mkdir()
    binary = target / "mei"
    shutil.copy2(source, binary)
    metal = target / "mlx.metallib"
    shutil.copy2(identity["files"][1]["file"], metal)
    subprocess.run(
        [
            "codesign",
            "--force",
            "--sign",
            "-",
            "--entitlements",
            str(PREP / "inspection-only-entitlements.plist"),
            str(binary),
        ],
        capture_output=True,
        check=True,
    )
    subprocess.run(["codesign", "--verify", "--strict", str(binary)], check=True)
    after = binary.read_bytes()
    before_sections, after_sections = sections(before), sections(after)
    if before_sections != after_sections or source.read_bytes() != before:
        raise ValueError("signing changed executable sections or the frozen original")
    effective = subprocess.run(
        ["codesign", "-d", "--entitlements", "-", "--xml", str(binary)],
        capture_output=True,
        check=True,
    )
    entitlements = plistlib.loads(effective.stdout)
    if entitlements != {"com.apple.security.get-task-allow": True}:
        raise ValueError("unexpected inspection entitlement set")
    result = copy.deepcopy(identity)
    result.update(
        inspection_only=True,
        never_distribute=True,
        original_manifest=original,
        executable_sections_unchanged=True,
        sections=after_sections,
        entitlements=entitlements,
    )
    for row, path in zip(result["files"], (binary, metal), strict=True):
        row.update(
            file=str(path),
            bytes=path.stat().st_size,
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        )
    with (PREP / f"inspection-{name}-runtime.json").open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    return result


def main():
    identities = {
        "a": prepare_runtime("control", "control-api-runtime.json"),
        "b": prepare_runtime("candidate", "candidate-runtime.json"),
    }
    cells = []
    for cell in ("a1", "b1", "b2", "a2", "b3", "b4"):
        cfg = yaml.safe_load(
            (
                ROOT / "configs/mei-stable-qualification-20261102/qwen-c1.yaml"
            ).read_text()
        )
        cfg.pop("mei_swift_acceptance")
        identity = identities[cell[0]]
        runtime = str(
            Path.home()
            / f".local/share/local-model-bench/mei-runtime/qwen-stable-inspection-{cell}-20261102"
        )
        old = cfg["required_runner_environment"]["MEI_RUNTIME_BASE"]
        argv = shlex.split(cfg["benchmark_launch_command"])
        argv[argv.index("--mei-binary") + 1] = identity["files"][0]["file"]
        argv[argv.index("--mei-repo") + 1] = identity["source_checkout"]
        cfg["benchmark_launch_command"] = shlex.join(argv).replace(old, runtime)
        cfg["required_runner_environment"].update(
            MEI_RUNTIME_BASE=runtime, SWIFT_DETERMINISTIC_HASHING="0"
        )
        cfg["mei_source_commit"] = identity["source_revision"]
        cfg["vmlx_commit"] = identity["vmlx_revision"]
        cfg["mei_release_artifact"] = {
            "source_revision": identity["source_revision"],
            "binary_sha256": identity["files"][0]["sha256"],
            "metallib_sha256": identity["files"][1]["sha256"],
            "inspection_only": True,
        }
        cfg["mei_qualification"].update(loaded_tokens=1024, decode_tokens=512)
        cfg["benchmark_status"] = (
            "Profiled exploratory execution-context diagnostic; never release qualification or scored performance. A=API-correct control; B=lookup candidate. Both have identical inspection-only signing entitlements and unchanged executable sections, compilation enabled, random hashing."
        )
        cfg["settings"] = [
            {
                "name": "profiling",
                "value": "Two read-only Swift task/thread captures after loaded repeats2/4, targeting the subsequent short decode. Each capture preserves actual active-generation status and timestamps. Observer interference invalidates qualification timing claims. No production or frozen binary changes.",
            }
        ]
        path = (
            ROOT
            / f"configs/mei-stable-qualification-20261102/qwen-inspection-{cell}.yaml"
        )
        with path.open("x") as stream:
            yaml.safe_dump(cfg, stream, sort_keys=False, width=100)
        cells.append(
            {
                "model": "qwen",
                "cell": cell,
                "config": str(path.relative_to(ROOT)),
                "output": f"artifacts/mei-stable-qwen-inspection-{cell}-20261102",
            }
        )
    with (PREP / "inspection-screen.json").open("x") as stream:
        json.dump(
            {"cells": cells, "purpose": "profiled diagnostic only"}, stream, indent=2
        )
        stream.write("\n")


if __name__ == "__main__":
    main()
