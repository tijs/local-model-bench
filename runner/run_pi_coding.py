"""Run a frozen Pi coding suite against one local model configuration."""

import argparse
import hashlib
import json
import os
import platform
import secrets
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml
from bench_common import REPO
from pi_coding.server import digest, endpoint
from pi_coding.workspace import TaskWorkspace, check, write_json

SUITE = REPO / "tasks/pi-coding-v1"
EXT = REPO / "runner/pi_coding/bridge.ts"
SYSTEM = "You maintain small Python projects. Use the supplied tools to inspect and edit files. Run visible tests and repair failures. Once correct, finish with a brief summary."
TOOLS = "read_file,edit_file,write_file,run_tests"


def run_task(task, cfg, out, agent, cwd):
    out.mkdir()
    token = secrets.token_urlsafe(32)
    start = time.monotonic()
    workspace = TaskWorkspace(task, out, start, cfg["output_tokens"])

    class Bridge(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            if self.headers.get("Authorization") != "Bearer " + token:
                self.send_error(403)
                return
            try:
                length = int(self.headers["Content-Length"])
                if length > 2**20:
                    raise ValueError("Oversized tool request")
                message = json.loads(self.rfile.read(length))
                result = workspace.apply(message["action"], message["args"])
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
            except Exception as exc:  # noqa: BLE001 -- propagate bridge failures to the scoring process
                workspace.infrastructure_error = str(exc)
                self.send_error(500)

    prompt = (
        task["prompt"]
        + "\nFiles: "
        + ", ".join(task["files"])
        + ". Run the visible tests before finishing."
    )
    write_json(out / "input.json", {"prompt": prompt, "files": task["files"]})
    cmd = [
        "pi",
        "--provider",
        "bench",
        "--model",
        cfg["model"],
        "--mode",
        "json",
        "--no-extensions",
        "--extension",
        str(EXT),
        "--no-skills",
        "--no-mcp",
        "--no-context-files",
        "--no-session",
        "--no-builtin-tools",
        "--tools",
        TOOLS,
        "--system-prompt",
        SYSTEM,
        "-p",
        prompt,
    ]
    timed_out = False
    with ThreadingHTTPServer(("127.0.0.1", 0), Bridge) as bridge:
        thread = threading.Thread(target=bridge.serve_forever, daemon=True)
        thread.start()
        env = dict(
            os.environ,
            PI_CODING_AGENT_DIR=str(agent),
            CODING_BRIDGE=f"http://127.0.0.1:{bridge.server_port}",
            CODING_TOKEN=token,
        )
        try:
            with (
                (out / "pi.jsonl").open("w") as log,
                (out / "stderr.log").open("w") as err,
            ):
                proc = subprocess.Popen(
                    cmd,
                    cwd=cwd,
                    env=env,
                    stdout=log,
                    stderr=err,
                    start_new_session=True,
                )
                try:
                    proc.wait(cfg["task_seconds"])
                except subprocess.TimeoutExpired:
                    timed_out = True
                finally:
                    if proc.poll() is None:
                        os.killpg(proc.pid, signal.SIGKILL)
                        proc.wait()
            elapsed = time.monotonic() - start
        finally:
            bridge.shutdown()
            thread.join()
    if workspace.infrastructure_error:
        raise RuntimeError(workspace.infrastructure_error)
    events = [
        json.loads(l)
        for l in (out / "pi.jsonl").read_text().splitlines()
        if l.startswith("{")
    ]
    messages = [
        e["message"]
        for e in events
        if e.get("type") == "message_end" and e["message"].get("role") == "assistant"
    ]
    reasons = [m.get("stopReason") for m in messages]
    if not workspace.requests or (
        not timed_out and (proc.returncode or not messages or "error" in reasons)
    ):
        raise RuntimeError(
            f"Pi/endpoint failure for {task['name']}: {reasons}; see {out}"
        )
    first = None
    grades = []
    for elapsed_write, files in workspace.snapshots:
        grade = check(task, files, hidden=True)
        grades.append({"seconds": elapsed_write, "files": files, "grade": grade})
        if grade["passed"] and first is None:
            first = elapsed_write
    write_json(out / "patches.json", grades)
    final = grades[-1]["grade"] if grades else check(task, workspace.files, hidden=True)
    return {
        "task": task["name"],
        "passed": final["passed"],
        "first_pass_s": first,
        "wall_s": elapsed,
        "timed_out": timed_out,
        "finish": reasons[-1] if reasons else None,
        "capped_turns": reasons.count("length"),
        "turns": workspace.requests,
        "visible_test_runs": workspace.visible_tests,
        "output_tokens": sum(m.get("usage", {}).get("output", 0) for m in messages),
        "writes": len(grades),
        "final_grade": final,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    config = args.config.resolve()
    out = args.output.resolve()
    cfg = yaml.safe_load(config.read_text())
    cfg_rel = config.relative_to(REPO)
    suite = cfg.get("suite", "pi-coding-v1")
    if suite not in {"pi-coding-v1", "pi-coding-v2"}:
        raise ValueError(f"Unknown coding suite: {suite}")
    dataset = sorted((REPO / "tasks" / suite).glob("*.yaml"))
    if not dataset:
        raise ValueError(f"Empty coding suite: {suite}")
    sources = [
        *dataset,
        EXT,
        Path(__file__),
        REPO / "runner/pi_coding/workspace.py",
        REPO / "runner/pi_coding/server.py",
        REPO / "runner/automation_sandbox.py",
        REPO / "runner/supervise_bench.py",
        REPO / "uv.lock",
    ]
    pinned = [config, *sources]
    if "mei" in cfg:
        pinned.append(config.parent / cfg["mei"]["file_manifest"])
    for file in pinned:
        relative = file.resolve().relative_to(REPO)
        if (
            subprocess.check_output(["git", "show", "HEAD:" + str(relative)], cwd=REPO)
            != file.read_bytes()
        ):
            raise ValueError(f"Uncommitted benchmark input: {relative}")
    pi_version = subprocess.check_output(
        ["pi", "--no-extensions", "--version"], text=True
    ).strip()
    if pi_version != cfg["pi_version"]:
        raise ValueError(f"Unexpected Pi version: {pi_version}")
    identity = {str(f.resolve().relative_to(REPO)): digest(f) for f in sources}
    protocol = {
        "suite": suite,
        "sources": identity,
        "pi": pi_version,
        "context": cfg["context"],
        "output_tokens": cfg["output_tokens"],
        "task_seconds": cfg["task_seconds"],
        "python": sys.version,
    }
    fingerprint = hashlib.sha256(
        json.dumps(protocol, sort_keys=True).encode()
    ).hexdigest()
    out.mkdir(parents=True, exist_ok=False)
    manifest = {
        "config": str(cfg_rel),
        "profile": cfg["label"],
        "model": cfg["model"],
        "host": {
            "chip": subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"], text=True
            ).strip(),
            "os": platform.mac_ver()[0],
            "memory_bytes": int(
                subprocess.check_output(["sysctl", "-n", "hw.memsize"])
            ),
        },
        "protocol": protocol,
        "fingerprint": fingerprint,
        "revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO, text=True
        ).strip(),
        "complete": False,
    }
    write_json(out / "manifest.json", manifest)
    shutil.copy(config, out / "config.yaml")
    results = []
    try:
        with endpoint(cfg, config, out), tempfile.TemporaryDirectory() as tmp:
            agent = Path(tmp) / "agent"
            agent.mkdir()
            # Stable neutral CWD keeps Pi's injected path identical across runs.
            cwd = Path(tempfile.gettempdir()) / "pi-coding-v1-empty"
            cwd.mkdir(exist_ok=True)
            if cwd.is_symlink() or any(cwd.iterdir()):
                raise ValueError("Pi neutral cwd must be empty")
            provider = {
                "baseUrl": cfg["endpoint"],
                "api": "openai-completions",
                "apiKey": "local",
                "compat": {"maxTokensField": "max_tokens"},
                "models": [
                    {
                        "id": cfg["model"],
                        "contextWindow": cfg["context"],
                        "maxTokens": cfg["output_tokens"],
                    }
                ],
            }
            write_json(agent / "models.json", {"providers": {"bench": provider}})
            write_json(agent / "settings.json", {"compaction": {"enabled": False}})
            for file in dataset:
                task = yaml.safe_load(file.read_text())
                row = run_task(task, cfg, out / task["name"], agent, cwd)
                write_json(out / task["name"] / "result.json", row)
                results.append(row)
                print(task["name"], row["passed"], round(row["wall_s"], 1), flush=True)
        write_json(out / "results.json", results)
        manifest["complete"] = True
    except BaseException as exc:
        manifest["error"] = str(exc)
        raise
    finally:
        write_json(out / "manifest.json", manifest)


if __name__ == "__main__":

    def terminate(_signum, _frame):
        raise KeyboardInterrupt("terminated")

    signal.signal(signal.SIGTERM, terminate)
    main()
