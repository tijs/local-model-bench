"""Guarded llama.cpp native admission, separate from held-out task scoring."""

import argparse
import json
import signal
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runner"))
from llama_provenance import verify_llama_runtime
from mei_provenance import sha256
from probe_mei import request_json, request_stream, validate_add_call
from qualify_llama_context import prepare_prompts
from run_mei_acceptance import committed_native_config, monitor_child, wait_ready
from run_standin_suite import write_json

CHECKS = {
    "identity",
    "plain",
    "tool",
    "stream_tool",
    "continuation",
    "cache",
    "context",
    "over_context",
}
TOOL = {
    "type": "function",
    "function": {
        "name": "add_numbers",
        "description": "Add two integers",
        "parameters": {
            "type": "object",
            "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
            "required": ["a", "b"],
            "additionalProperties": False,
        },
    },
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def succeeded(output):
    result = json.loads((output / "admission.json").read_text())
    return (
        result["status"] == "passed"
        and result["server_exited"] is True
        and set(result["passed"]) == CHECKS
        and result["pre_sha256"] == result["post_sha256"] == result["expected_sha256"]
    )


def exercise(cfg, output, result):
    endpoint = cfg["benchmark_endpoint"]
    base = endpoint.removesuffix("/v1")
    model = cfg["orchestration"]["served_model_id"]
    cap = cfg["context_cap"]

    def save(label, response):
        write_json(output / f"{label}.json", response)
        return response

    def passed(label):
        result["passed"].append(label)
        write_json(output / "admission.json", result)
        print(f"PASS {label}", flush=True)

    identity = save("models", request_json(endpoint + "/models")[0])
    require(
        [row["id"] for row in identity["data"]] == [model], "unexpected served identity"
    )
    passed("identity")

    def chat(label, **payload):
        body = {
            "model": model,
            "temperature": 0,
            "seed": 17,
            "max_tokens": 512,
            **payload,
        }
        return save(label, request_json(endpoint + "/chat/completions", body)[0])

    def visible(response):
        choice = response["choices"][0]
        require(
            choice["finish_reason"] == "stop"
            and not choice["message"].get("tool_calls"),
            "expected a completed plain answer",
        )
        return (choice["message"]["content"] or "").strip().rstrip(".")

    plain = [
        {
            "role": "user",
            "content": "Reply with exactly the word ready and nothing else.",
        }
    ]
    require(
        visible(chat("plain", messages=plain)).lower() == "ready",
        "plain answer differs",
    )
    passed("plain")
    user = {
        "role": "user",
        "content": "Call add_numbers with a=15 and b=27. Do not answer until the tool returns. After the tool returns, reply with exactly the result number and nothing else.",
    }
    body = {
        "model": model,
        "messages": [user],
        "tools": [TOOL],
        "tool_choice": "auto",
        "temperature": 0,
        "seed": 17,
        "max_tokens": 768,
    }
    reply = chat("tool", **body)
    validate_add_call(reply)
    passed("tool")
    streamed = save(
        "stream_tool", request_stream(endpoint + "/chat/completions", body)[0]
    )
    validate_add_call(streamed)
    passed("stream_tool")
    for name, response in (("buffered", reply), ("streamed", streamed)):
        assistant = response["choices"][0]["message"]
        call_id = assistant["tool_calls"][0]["id"]
        require(isinstance(call_id, str) and call_id, "tool call has no replayable ID")
        messages = [
            user,
            assistant,
            {"role": "tool", "tool_call_id": call_id, "content": "42"},
        ]
        continued = chat(
            f"continuation-{name}", messages=messages, tools=[TOOL], tool_choice="auto"
        )
        require(
            visible(continued) == "42",
            "dependent tool result did not reach the final answer",
        )
    passed("continuation")

    tokens = prepare_prompts(base, 2048)["loaded"]
    payload = {
        "prompt": tokens,
        "n_predict": 8,
        "temperature": 0,
        "seed": 17,
        "cache_prompt": True,
    }
    first = save("cache-first", request_json(base + "/completion", payload)[0])
    second = save("cache-second", request_json(base + "/completion", payload)[0])
    require(
        first["content"]
        and first["content"] == second["content"]
        and second["timings"]["cache_n"] > 0,
        "repeated prompt did not reuse cache with greedy parity",
    )
    passed("cache")

    tokens = prepare_prompts(base, cap - 1)["loaded"]
    payload = {
        "prompt": tokens,
        "n_predict": 1,
        "temperature": 0,
        "ignore_eos": True,
        "cache_prompt": False,
    }
    exact = save("context", request_json(base + "/completion", payload)[0])
    require(
        exact["tokens_evaluated"] == cap - 1
        and exact["tokens_predicted"] == 1
        and not exact["truncated"],
        "full configured window was not evaluated",
    )
    passed("context")
    try:
        request_json(base + "/completion", payload | {"prompt": tokens + tokens[-2:]})
    except RuntimeError as error:
        save("over_context", {"error": str(error)})
        require(
            str(error).startswith("HTTP 400:") and "context size" in str(error),
            "wrong error for overlong input",
        )
    else:
        raise ValueError("overlong input was accepted")
    passed("over_context")


def child(cfg, output):
    import shlex

    argv = shlex.split(cfg["benchmark_launch_command"])
    model = Path(argv[argv.index("--model") + 1])
    result = {
        "status": "failed",
        "passed": [],
        "server_exited": False,
        "expected_sha256": cfg["model_sha256"],
    }
    server = None
    try:
        result["pre_sha256"] = sha256(model)
        require(
            result["pre_sha256"] == result["expected_sha256"],
            "GGUF differs from its pin",
        )
        with (output / "server.log").open("x") as log:
            server = subprocess.Popen(
                argv, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT
            )
        wait_ready(server, cfg["benchmark_endpoint"])
        result["runtime_identity"] = verify_llama_runtime(
            cfg, base_url=cfg["benchmark_endpoint"]
        )
        exercise(cfg, output, result)
        result["status"] = "passed"
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
        AssertionError,
        subprocess.SubprocessError,
        KeyboardInterrupt,
    ) as error:
        result["error"] = f"{type(error).__name__}: {error}"
    finally:
        if server is not None:
            server.terminate()
            try:
                server.wait(timeout=8)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=3)
            result["server_exited"] = True
        write_json(output / "admission.json", result)
    if result["status"] == "passed":
        result["post_sha256"] = sha256(model)
        write_json(output / "admission.json", result)
    return 0 if succeeded(output) else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--deadline", type=int, default=1800)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    cfg, content = committed_native_config(args.config.resolve())
    require(
        cfg["benchmark_scope"] == "queued-llama-native-v1"
        and cfg["inference_engine"] == "llama.cpp",
        "expected non-ranking native config",
    )
    verify_llama_runtime(cfg)
    if args.child:

        def interrupt(_signal, _frame):
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            raise KeyboardInterrupt

        signal.signal(signal.SIGTERM, interrupt)
        return child(cfg, args.output)
    for port in (8017, 8024):
        with socket.socket() as connection:
            connection.settimeout(0.5)
            require(
                connection.connect_ex(("127.0.0.1", port)) != 0,
                f"port {port} already in use",
            )
    args.skip_context = False
    args.skip_cache = False
    return monitor_child(
        cfg,
        content,
        args,
        [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:], "--child"],
        diagnostic_check=succeeded,
    )


if __name__ == "__main__":
    raise SystemExit(main())
