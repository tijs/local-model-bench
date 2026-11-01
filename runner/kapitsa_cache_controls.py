"""Cold-determinism and cached-continuation controls for native Clover diffusion."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shlex
import subprocess
import time
from pathlib import Path

from mei_provenance import listener_binary
from run_mei_acceptance import wait_ready
from run_standin_suite import write_json
from supervise_bench import baseline_ready, sample


def vm_bytes(point, label):
    text = point["host_vm_stat"]
    page = re.search(r"page size of (\d+)", text)
    count = re.search(re.escape(label) + r":\s+(\d+)", text)
    if page is None or count is None:
        raise ValueError("missing macOS VM byte counters")
    return int(page[1]) * int(count[1])


def recovered(points, initial):
    return (len(points) >= 7 and baseline_ready(points[-7:], None, 2)
            and all(vm_bytes(p, label) <= vm_bytes(initial, label) + 512 * 1024**2
                    for p in points[-7:] for label in ("Pages wired down", "Pages occupied by compressor")))


def wait_for_recovery(output, initial, session):
    points = []
    deadline = time.monotonic() + 90
    with (output / f"recovery-{session}.jsonl").open("x", buffering=1) as stream:
        while time.monotonic() < deadline:
            point = sample(os.getpid(), output)
            stream.write(json.dumps(point) + "\n")
            points.append(point)
            if recovered(points, initial):
                return
            time.sleep(5)
    raise RuntimeError("post-exit resource recovery not observed within90seconds; no next model started")


def signature(response):
    choice = response["choices"][0]
    message = choice["message"]
    return {
        "content": message.get("content"),
        "reasoning_content": message.get("reasoning_content"),
        "tool_calls": [{"name": c["function"]["name"],
                        "arguments": json.loads(c["function"]["arguments"])}
                       for c in message.get("tool_calls", [])],
        "finish_reason": choice["finish_reason"],
    }


def cached(response):
    return response["usage"].get("prompt_tokens_details", {}).get("cached_tokens", 0)


def compare(warm, cold_a, cold_b):
    baseline = signature(cold_a) == signature(cold_b)
    return {
        "cold_determinism": baseline,
        "cached_matches_cold": baseline and signature(warm) == signature(cold_a),
        "warm_cached_tokens": cached(warm),
        "cold_cached_tokens": [cached(cold_a), cached(cold_b)],
        "passed": baseline and signature(warm) == signature(cold_a)
        and cached(warm) > 0 and cached(cold_a) == cached(cold_b) == 0,
    }


def succeeded(output: Path) -> bool:
    report = json.loads((output / "cache-comparison.json").read_text())
    cases = report.get("cases", {})
    return (report.get("status") == "passed" and report.get("decoder_verified") == "block diffusion"
            and set(cases) == {"repeat", "growing_tool_history", "after_partial_block"}
            and all(row.get("passed") is True and row.get("cold_determinism") is True
                    and row.get("tool_contract_passed") is True
                    and row.get("cached_matches_cold") is True and row.get("warm_cached_tokens", 0) > 0
                    and row.get("cold_cached_tokens") == [0, 0] for row in cases.values()))


def child(cfg, content, output):
    import hashlib

    if os.environ.get("BENCH_ADMITTED_CONFIG_SHA256") != hashlib.sha256(content).hexdigest():
        raise ValueError("missing matching parent admission")
    runtime = Path(cfg["runtime_base"])
    runtime.mkdir(parents=True, exist_ok=False)
    spec = importlib.util.spec_from_file_location("release_probe", cfg["probe_program"])
    if spec is None or spec.loader is None:
        raise ValueError("cannot load pinned probe helpers")
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    url = cfg["benchmark_endpoint"]
    command = shlex.split(cfg["benchmark_launch_command"])
    server = None
    log = None
    session = 0
    initial = json.loads((output / "baseline.jsonl").read_text().splitlines()[-1])
    report = {"status": "running", "decoder_verified": None, "cases": {}}

    def stop():
        nonlocal server, log
        if server is not None:
            server.terminate()
            try:
                server.wait(timeout=15)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=3)
            server = None
        if log is not None:
            log.close()
            log = None

    def restart():
        nonlocal server, log, session
        stop()
        if session:
            wait_for_recovery(output, initial, session)
        session += 1
        path = output / f"server-{session}.log"
        log = path.open("x")
        server = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        wait_ready(server, url, timeout=180)
        if listener_binary(url).resolve() != Path(cfg["runtime_binary"]).resolve():
            raise ValueError("wrong listener")
        if "Clover: block diffusion, 32-row blocks, threshold 0.95" not in path.read_text():
            raise ValueError("diffusion mode not confirmed")
        report["decoder_verified"] = "block diffusion"

    def request(label, payload):
        write_json(output / f"{label}-request.json", payload)
        response, seconds = probe.request_json(url + "/chat/completions", payload, timeout=180)
        write_json(output / f"{label}-response.json", {"response": response, "seconds": seconds, "session": session})
        return response

    try:
        restart()
        prefix = "Synthetic cache fixture. No private data. " * 160
        tools = [{"type": "function", "function": {"name": "add_numbers", "description": "Add integers.",
                  "parameters": {"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
                                 "required": ["a", "b"], "additionalProperties": False}}}]
        base = {"model": cfg["served_model_id"], "temperature": 0, "seed": 17,
                "max_tokens": cfg["native_probe"]["max_tokens"], "stream": False, "tools": tools, "tool_choice": "auto"}
        messages = [{"role": "system", "content": prefix},
                    {"role": "user", "content": "What is 15 + 27? You must use add_numbers to compute it."}]
        repeat = base | {"messages": messages}
        first = request("repeat-seed", repeat)
        probe.validate_add_call(first)
        warm = {"repeat": request("repeat-warm", repeat)}
        assistant = first["choices"][0]["message"]
        growing = base | {"messages": [*messages, assistant,
                   {"role": "tool", "tool_call_id": assistant["tool_calls"][0]["id"], "content": '{"result":42}'},
                   {"role": "user", "content": "Use add_numbers again, with a=42 and b=8."}]}
        warm["growing_tool_history"] = request("growing-warm", growing)
        partial_messages = [{"role": "system", "content": prefix},
                            {"role": "user", "content": "Count from 1 to 50."}]
        partial = request("partial-block", base | {"messages": partial_messages, "max_tokens": 7})
        if partial["choices"][0]["finish_reason"] != "length" or partial["usage"]["completion_tokens"] != 7:
            raise ValueError("partial-block control did not stop at seven tokens")
        followup = base | {"messages": [*partial_messages, partial["choices"][0]["message"],
                    {"role": "user", "content": "Now use add_numbers with a=15 and b=27."}]}
        warm["after_partial_block"] = request("after-partial-warm", followup)
        payloads = {"repeat": repeat, "growing_tool_history": growing, "after_partial_block": followup}
        for name, payload in payloads.items():
            cold = []
            for leg in ("a", "b"):
                restart()
                cold.append(request(f"{name}-cold-{leg}", payload))
            row = compare(warm[name], cold[0], cold[1])
            expected = {"a": 42, "b": 8} if name == "growing_tool_history" else {"a": 15, "b": 27}
            actual = signature(warm[name])
            row["tool_contract_passed"] = (actual["finish_reason"] == "tool_calls"
                and actual["tool_calls"] == [{"name": "add_numbers", "arguments": expected}])
            row["passed"] &= row["tool_contract_passed"]
            report["cases"][name] = row
            write_json(output / "cache-comparison.json", report)
        report["status"] = "passed" if all(row["passed"] for row in report["cases"].values()) else "failed"
    except KeyboardInterrupt:
        report.update(status="interrupted", error="supervisor interrupted cache controls")
        raise
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        report.update(status="failed", error=f"{type(exc).__name__}: {exc}")
    finally:
        stop()
        write_json(output / "cache-comparison.json", report)
    return 0 if succeeded(output) else 1
