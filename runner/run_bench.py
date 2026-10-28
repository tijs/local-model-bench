#!/usr/bin/env python3
"""Current model-only benchmark: sanity plus neutral mocked tool behavior.

Hermes runtime/profile/coding work is retired. Historical orchestration remains
in legacy_run_bench.py for source/evidence regression tests, not execution.
No Peixinho application behavior is claimed by these native model tests.
"""
import argparse
import hashlib
import json
import math
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml
from bench_common import (
    BACKEND_HEALTH_TIMEOUT_SECONDS,
    MIN_FREE_DISK_GB_BEFORE_LAUNCH,
    config_rank_eligible,
    git_sha,
    snapshot_config,
)
from mei_provenance import verify_mei_runtime

REPO = Path(__file__).resolve().parent.parent
MODEL_ONLY_SUITES = ("sanity", "model_tools")
MODEL_ONLY_SCOPE = "model-only-v1"


def validate_model_only_scope(stage, coding_suites=None, reasoning=None):
    if stage not in ("all", "model") or coding_suites is not None or reasoning is not None:
        raise ValueError("Hermes coding/stages are retired; current runs evaluate model-only suites")


def complete_model_summary(rows, expected, trials):
    from collections import Counter
    return (isinstance(rows, list) and all(isinstance(row, dict)
            and isinstance(row.get("pass"), bool) and not row.get("harness_error") for row in rows)
            and Counter((row.get("task_id"), row.get("trial")) for row in rows)
            == Counter({(key, trial): 1 for key in expected for trial in range(1, trials + 1)}))


def admitted_config_snapshot(content, config_hash):
    path = REPO / "results" / "configs" / f"{config_hash}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != content:
        raise ValueError("config snapshot conflicts with admitted bytes")
    path.write_bytes(content)
    return path


def mei_stop_command(cfg):
    command = ["bash", str(REPO / "runner" / "stop_mei_server.sh")]
    runtime = (cfg.get("required_runner_environment") or {}).get("MEI_RUNTIME_BASE")
    if runtime:
        command += ["--runtime-base", runtime]
    return command


def _model_report():
    return run([sys.executable, str(REPO / "runner" / "build_model_report.py")]).returncode == 0


def run(cmd, **kw):
    printable = cmd if isinstance(cmd, str) else " ".join(str(c) for c in cmd)
    print(f"$ {printable}")
    return subprocess.run(cmd, shell=isinstance(cmd, str), cwd=str(REPO), **kw)


def wait_for_health(url, timeout=BACKEND_HEALTH_TIMEOUT_SECONDS, proc=None):
    """proc, if given, is the just-launched server's Popen handle — if it
    has already exited, fail immediately instead of waiting out the full
    timeout only to report a generic "never became healthy" (adversarial
    review finding H2, partial: this alone doesn't catch a STALE process
    silently answering instead of the new one — see model/parser identity
    checks in run_one())."""
    print(f"Waiting for {url} to respond (timeout {timeout}s)...")
    start = time.time()
    while time.time() - start < timeout:
        if proc is not None and proc.poll() is not None:
            print(f"  server process exited early (returncode={proc.returncode}) — not waiting further")
            return False
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                if resp.status == 200:
                    print(f"  healthy after {time.time() - start:.1f}s")
                    return True
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError):
            pass
        time.sleep(3)
    return False


def _majority_pass(rows):
    """More than half of *rows* passed. Used for the sanity fail-fast gate
    instead of requiring ALL rows to pass (adversarial review finding
    M-12): with --trials N, the flag added specifically to MEASURE
    flakiness made a single flaky failure among N trials abort hermes_ops
    AND the coding suite too — the more trials you run to detect
    flakiness, the more likely one of them randomly fails and the more
    destructive that single failure becomes. A flaky sanity result is
    still recorded (see the "Flaky tasks" leaderboard section) even when
    the majority passes and the run continues."""
    return sum(1 for r in rows if r["pass"]) * 2 > len(rows)


def _base_repo_name(model_id):
    """Strip a ':quant' suffix, e.g. 'foo/Bar-GGUF:Q4_K_M' -> 'foo/Bar-GGUF'."""
    return model_id.split(":")[0]




def assert_serving_expected_model(raw_port, expected_model, alias=None, served_model_id=None):
    """Confirm the server actually answering raw_port is serving the model
    THIS config expects, not a stale process left over from a previous
    config (adversarial review finding H2: wait_for_health only checks
    that *something* answers 200 — a leftover server on the same port
    would pass that check while silently serving the wrong model).

    When *alias* is given (gguf configs — see server_command()), this
    checks for an EXACT match against it instead of a repo-name substring
    match. Confirmed live: llama-server's --alias fully replaces /v1/models'
    "id" field with the given string. Needed because a repo-name substring
    match can't distinguish a config from its own speculative-decoding
    sibling (adversarial review finding H-5) — three pairs in this repo
    share both a base repo id and raw_port (e.g. Qwen3.8-27B/gguf.yaml vs.
    gguf-dflash2.yaml), so a stale sibling server answers with the
    identical id and would silently pass a substring check."""
    url = f"http://127.0.0.1:{raw_port}/v1/models"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"FAILED: could not verify served model via {url}: {e}")
        return False
    served_ids = [m.get("id", "") for m in data.get("data", [])]
    # oMLX serves the local model-directory (or configured model-alias) ID,
    # not necessarily the source HF repository recorded as `model:` in the
    # benchmark config. A fuzzy source-ID match would accept an old oMLX
    # directory that happens to share part of the source name, so oMLX config
    # must supply a stable `orchestration.served_model_id` and match it exactly.
    if served_model_id:
        if served_model_id in served_ids:
            return True
        print(f"FAILED: {url} is serving {served_ids!r}, expected exact served_model_id "
              f"{served_model_id!r} — a stale oMLX process or model directory may be bound "
              "to this port.")
        return False
    if alias:
        if alias in served_ids:
            return True
        print(f"FAILED: {url} is serving {served_ids!r}, expected exact alias {alias!r} "
              f"— a stale sibling-config server (e.g. the plain vs. speculative-decoding "
              f"variant) may still be bound to this port.")
        return False
    expected = _base_repo_name(expected_model)
    if any(expected in sid or sid in expected for sid in served_ids if sid):
        return True
    print(f"FAILED: {url} is serving {served_ids!r}, expected something matching {expected!r} "
          f"— a stale server from a previous config may still be bound to this port.")
    return False


def assert_plain_completion(base_url, request_model, timeout=60):
    """Prove the selected endpoint can generate ordinary assistant text.

    A 200 /v1/models response only proves a process is listening. Before any
    benchmark rows are recorded, make one minimal non-streaming completion on
    the same served model ID that the suites will request.
    """
    url = f"{base_url.rstrip('/')}/chat/completions"
    body = json.dumps({
        "model": request_model,
        "messages": [{"role": "user", "content": "Reply with exactly: ready"}],
        "temperature": 0,
        # 32, not 8 (confirmed live 2026-08-23): poolside/Laguna-XS-2.1
        # forces thinking mode on via --chat-template-kwargs
        # enable_thinking:true, and even with the reasoning_content
        # fallback below, 8 tokens isn't always enough budget for a
        # thinking-forced model to produce ANY extractable text (opening
        # the <think> block alone can consume the whole budget) — this
        # config genuinely IS alive and serves real completions once given
        # room, so a bigger probe budget is more honest than declaring it
        # dead. Still small enough to be cheap for every other model.
        "max_tokens": 32,
        "stream": False,
    }).encode()
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"FAILED: plain completion probe at {url} failed: {e}")
        return False
    choices = data.get("choices") or []
    message = (choices[0].get("message") or {}) if choices else {}
    content = message.get("content")
    # Some llama-server chat templates misclassify an entire short response
    # (this probe's whole 8-token budget) as reasoning_content, leaving
    # content empty — bench_local_proxy.py's normalize_response() already
    # has a documented 2026-08-20 fix for exactly this (confirmed live for
    # poolside/Laguna-XS-2.1), but that fix only runs for proxied configs;
    # this probe deliberately hits the RAW backend, before any proxy is
    # even started, so it never benefited from it. Confirmed live again
    # 2026-08-23: this false-failed poolside/Laguna-XS-2.1/gguf.yaml AND
    # LiquidAI/LFM2.5-2.6B-GGUF:Q8_0/gguf.yaml (a config with real,
    # previously-confirmed 45+ tok/s hermes_ops results) in the same
    # sweep — both servers' own logs showed a real completed generation at
    # probe time, so this is a probe-side false negative, not a dead
    # backend. tool_calls presence is also accepted as life, matching
    # normalize_response()'s own "tool_calls means don't touch it" logic.
    if isinstance(content, str) and content.strip():
        print("Plain completion probe passed.")
        return True
    if message.get("tool_calls"):
        print("Plain completion probe passed (tool_calls).")
        return True
    reasoning_content = message.get("reasoning_content")
    if isinstance(reasoning_content, str) and reasoning_content.strip():
        print("Plain completion probe passed (reasoning_content).")
        return True
    print(f"FAILED: plain completion probe returned no assistant content for {request_model!r}.")
    return False


def assert_proxy_matches(proxy_port, expected_parser, expected_upstream):
    """Same identity check as assert_serving_expected_model, for the proxy
    layer: a stale bench_local_proxy.py left bound to the port would also
    answer /healthz successfully while pointed at the wrong parser/upstream
    (the exact failure mode observed live 2026-08-20 — see AGENTS.md's
    killed-task retry hazard note)."""
    url = f"http://127.0.0.1:{proxy_port}/healthz"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"FAILED: could not verify proxy identity via {url}: {e}")
        return False
    actual_parser = data.get("tool_call_parser")
    actual_upstream = data.get("upstream")
    if actual_parser == expected_parser and actual_upstream == expected_upstream:
        return True
    print(f"FAILED: proxy on {proxy_port} reports parser={actual_parser!r} upstream={actual_upstream!r}, "
          f"expected parser={expected_parser!r} upstream={expected_upstream!r} — "
          f"a stale proxy process is likely still bound to this port.")
    return False


def clear_kv_cache_dir(cfg):
    """Delete this config's persistent Mei KV/prefix cache before a run.

    Mei's disk KV tier is a real and wanted speedup for normal use — a warm
    prefix makes a growing agent transcript cheap. But `--kv-cache-dir` points
    at a FIXED path in every Mei config, so it survives between benchmark runs,
    and a second run of the same config is then served from the first run's
    cache. That silently changes what the benchmark measures.

    Measured 2026-09-07 on the Nemotron config: two runs, identical prompts and
    byte-identical outputs, avg hermes_ops 1.02 tok/s (cold) vs 32.74 tok/s
    (warm), TTFT 84.6s vs 1.8s. Because
    `tokens_per_second = completion_tokens / wall_seconds` and that workload is
    ~99% prefill, the metric moved 32x on cache state alone -- flipping the 4.0
    viability speed gate from fail to pass.

    So: keep the cache in Mei, clear it here. Every benchmark run starts cold,
    which is the only state that is comparable across configs and across time.
    """
    text = (cfg.get("benchmark_launch_command") or "")
    # EVERY occurrence, not the first. A launch command that passes
    # --kv-cache-dir twice gives the server the LAST one (start_mei_server.sh
    # parses argv in order and the last assignment wins), while re.search
    # returns the FIRST. The four Qwen3.6 anchors A/B configs did exactly that,
    # so this function cleared a directory the server never opened and printed
    # a confident "cleared for a cold, comparable run" naming it. The dirs it
    # named were never created at all; the ones actually in use reached 9.9 GB
    # and 40+ entries, shared by BOTH arms of each A/B. Clearing all of them is
    # correct whichever end of the list the server takes.
    raws = re.findall(r"--kv-cache-dir\s+(\S+)", text)
    if not raws:
        return
    cleaned = []
    for raw in raws:
        raw = raw.strip().strip("\\").strip('"').strip("'")
        if raw not in cleaned:
            cleaned.append(raw)
    if len(cleaned) > 1:
        print(f"--- WARNING: launch command sets --kv-cache-dir {len(cleaned)} "
              f"times: {cleaned}. The server uses the LAST ({cleaned[-1]}); "
              f"clearing all of them. Fix the config — two arms of an A/B that "
              f"share a cache dir are not independent measurements. ---")
    for raw in cleaned:
        _clear_one_kv_dir(raw)


def _clear_one_kv_dir(raw):
    path = pathlib.Path(os.path.expanduser(raw))
    # Only ever delete inside the project's own runtime root -- never follow a
    # config into an arbitrary path.
    runtime_root = pathlib.Path(
        os.path.expanduser("~/.local/share/local-model-bench")).resolve()
    try:
        resolved = path.resolve()
        resolved.relative_to(runtime_root)
    except (ValueError, OSError):
        print(f"--- KV cache: refusing to clear {path} (outside "
              f"{runtime_root}) ---")
        return
    if not resolved.exists():
        print(f"--- KV cache: {resolved} absent, already cold ---")
        return
    print(f"--- clear KV cache for a cold, comparable run: {resolved} ---")
    shutil.rmtree(resolved, ignore_errors=True)


def with_seed(text, seed):
    """Append `--seed N` to a Mei launch command, or refuse.

    A previous adversarial review (finding CR3-2) caught a flag being blindly
    string-appended to the END of a launch block whose last line was a trailing
    shell COMMENT, so the flag landed inside the comment and was silently never
    passed. Guard against exactly that rather than trusting the shape.
    """
    if seed is None:
        return text
    body = text.strip()
    last = [ln for ln in body.splitlines() if ln.strip()][-1]
    if last.lstrip().startswith("#"):
        raise SystemExit(
            "--seed refused: launch command ends with a shell comment, so an "
            "appended flag would land inside it. Fix the config or add the "
            "flag there explicitly.")
    if last.rstrip().endswith("\\"):
        raise SystemExit(
            "--seed refused: launch command ends with a line continuation.")
    if "--seed" in body:
        raise SystemExit("--seed refused: launch command already sets --seed.")
    return body + f" \\\n    --seed {seed}"


def server_command(cfg, alias=None):
    """benchmark_launch_command sometimes documents a follow-up proxy step
    inline (as literal shell text, not a shell comment) — that's for a
    human reading the file, not something to execute as one blob. Only
    take the lines up to the first mention of bench_local_proxy.py.

    *alias*, when given, is appended as `--alias <alias>` on llama-server's
    own command line (adversarial review finding H-5): three config pairs
    in this repo share both a base HF repo id and raw_port (a plain config
    and its speculative-decoding sibling, e.g. Qwen3.8-27B/gguf.yaml vs.
    gguf-dflash2.yaml) — /v1/models reports the same `id` for both, so the
    repo-name identity check couldn't tell a stale sibling server from the
    one actually requested. llama-server (and both forked binaries used
    for DFlash2/DSpark) support --alias; vllm-mlx (the MLX backend) does
    not, so this only applies to gguf configs."""
    text = cfg["benchmark_launch_command"].strip()
    marker = "bench_local_proxy.py"
    if marker in text:
        idx = text.index(marker)
        # walk back to the start of the line that introduces this step
        # (the "# then, separately" comment line, if present) and cut there
        prior_newline = text.rfind("\n", 0, idx)
        comment_start = text.rfind("\n#", 0, idx)
        cut = comment_start if comment_start != -1 else prior_newline
        text = text[:cut].strip()
    if alias and cfg.get("inference_engine", "").startswith("llama.cpp"):
        # A third independent adversarial review (finding CR3-2) found this
        # used to blindly string-append to the END of `text` — but
        # Qwen3.5-9B/gguf.yaml's launch block ends with a trailing shell
        # COMMENT (explaining a --ctx-size choice), so the alias landed
        # inside it and was never actually passed to llama-server at all.
        # /v1/models then reported the real repo id, assert_serving_
        # expected_model's exact-alias check failed, and that config was
        # silently skipped on every --all sweep. Walk backward past any
        # trailing blank/comment-only lines to find the actual last
        # command line, and append there instead.
        lines = text.split("\n")
        i = len(lines) - 1
        while i >= 0 and (not lines[i].strip() or lines[i].lstrip().startswith("#")):
            i -= 1
        if i < 0:
            text += f" --alias {alias}"  # entire block was comments/blank — fall back
        else:
            lines[i] = lines[i] + f" --alias {alias}"
            text = "\n".join(lines)
    return text






def _record_disk_preflight(config_path, config_hash, free_bytes):
    """Persist explicit operator opt-in before launch, even if a later gate fails.

    Never rewrite task rows or authored configs. The verbatim config snapshot
    carries the diagnostic/ranking declaration; this separate append-only audit
    records the actual disk observation and CLI authorization for this attempt.
    A failed snapshot/audit write aborts the launch rather than losing evidence.
    """
    snap_hash, relative_path = snapshot_config(config_path)
    snapshot = REPO / "results" / "configs" / f"{snap_hash}.yaml"
    if (snap_hash != config_hash
            or hashlib.sha256(snapshot.read_bytes()).hexdigest()[:12] != config_hash):
        raise SystemExit("disk preflight refused: config changed or snapshot does not match")
    floor_bytes = int(MIN_FREE_DISK_GB_BEFORE_LAUNCH * (1024 ** 3))
    entry = {
        "config_path": relative_path,
        "config_hash": config_hash,
        "runner_git_sha": git_sha(),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "observed_free_bytes": free_bytes,
        "floor_gib": MIN_FREE_DISK_GB_BEFORE_LAUNCH,
        "floor_bytes": floor_bytes,
        "shortfall_bytes": max(0, floor_bytes - free_bytes),
        "force_disk_gate": True,
        "disk_gate_overridden": free_bytes < floor_bytes,
        "forced_gate": True,
        "exploratory": True,
        "rank_eligible": False,
    }
    with open(REPO / "results" / "disk_preflight.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")
        f.flush()
        os.fsync(f.fileno())
    return snapshot


def _record_authorized_disk_floor_override(config_path, config_content, config_hash, free_bytes):
    """Persist a rank-eligible, per-invocation waiver before any server launch.

    This is separate from the forced diagnostic path: a resource-floor waiver
    does not change scoring eligibility. Write the admitted bytes exclusively,
    fsync both files and their directories, and read back both artifacts. Any
    failure propagates before Popen; an existing snapshot is never rewritten.
    """
    full_hash = hashlib.sha256(config_content).hexdigest()
    if full_hash[:12] != config_hash or config_path.read_bytes() != config_content:
        raise SystemExit("disk-floor override refused: config changed before preflight")
    relative_path = str(config_path.resolve().relative_to(REPO))
    snapshot = REPO / "results" / "configs" / f"{config_hash}.yaml"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    if snapshot.is_symlink():
        raise SystemExit("disk-floor override refused: snapshot must not be a symlink")
    try:
        with open(snapshot, "xb") as f:
            if f.write(config_content) != len(config_content):
                raise OSError("incomplete disk-floor override config snapshot write")
            f.flush()
            os.fsync(f.fileno())
    except FileExistsError:
        pass  # verify, but never overwrite, a content-addressed snapshot
    with open(snapshot, "rb") as f:
        if f.read() != config_content:
            raise SystemExit("disk-floor override refused: snapshot does not match admitted config")
        os.fsync(f.fileno())

    floor_bytes = int(MIN_FREE_DISK_GB_BEFORE_LAUNCH * (1024 ** 3))
    entry = {
        "config_path": relative_path,
        "config_hash": config_hash,
        "config_sha256": full_hash,
        "config_snapshot": str(snapshot.relative_to(REPO)),
        "runner_git_sha": git_sha(),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "observed_free_bytes": free_bytes,
        "floor_gib": MIN_FREE_DISK_GB_BEFORE_LAUNCH,
        "floor_bytes": floor_bytes,
        "shortfall_bytes": max(0, floor_bytes - free_bytes),
        "allow_disk_floor_override": True,
        "disk_floor_override_authorized": True,
        "disk_gate_overridden": free_bytes < floor_bytes,
        "rank_eligible": True,
    }
    audit = REPO / "results" / "disk_preflight.jsonl"
    payload = (json.dumps(entry) + "\n").encode("utf-8")
    with open(audit, "ab") as f:
        offset = f.tell()
        if f.write(payload) != len(payload):
            raise OSError("incomplete disk-floor override audit write")
        f.flush()
        os.fsync(f.fileno())
    with open(audit, "rb") as f:
        f.seek(offset)
        if f.read(len(payload)) != payload:
            raise SystemExit("disk-floor override refused: audit readback does not match")
    for directory in (snapshot.parent, audit.parent):
        fd = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    return snapshot


def _run_one_impl(config_path: Path, cfg, config_hash, trials: int = 1, coding_suites=None, stage="all",
                  seed=None, generation_profile=None, reasoning=None, force_disk_gate=False,
                  allow_disk_floor_override=False, *, config_content=None):
    validate_model_only_scope(stage, coding_suites, reasoning)
    if not isinstance(cfg, dict):
        sys.exit(f"{config_path} must contain a YAML config mapping")
    orch = cfg.get("orchestration")
    if not isinstance(orch, dict) or not orch:
        sys.exit(f"{config_path} has no valid orchestration: mapping — see configs/README.md")

    if force_disk_gate and allow_disk_floor_override:
        sys.exit("--force-disk-gate and --allow-disk-floor-override are mutually exclusive")

    if force_disk_gate and not (
        force_disk_gate is True
        and orch.get("forced_gate") is True
        and orch.get("exploratory") is True
        and orch.get("rank_eligible") is False
        and orch.get("raw_port") is not None
        and not orch.get("api_base_url")
        and orch.get("viable", "full") == "full"
        and stage == "all"
    ):
        sys.exit("--force-disk-gate requires orchestration.forced_gate: true, "
                 "orchestration.exploratory: true, orchestration.rank_eligible: false "
                 "(literal YAML booleans), a local raw_port without api_base_url, "
                 "viable: full and --stage all")

    if allow_disk_floor_override and not (
        allow_disk_floor_override is True
        and orch.get("disk_floor_override_authorized") is True
        and config_rank_eligible(cfg)
        and orch.get("raw_port") is not None
        and not orch.get("api_base_url")
        and orch.get("viable", "full") == "full"
        and stage == "all"
    ):
        sys.exit("--allow-disk-floor-override requires "
                 "orchestration.disk_floor_override_authorized: true (a literal YAML boolean), "
                 "a rank-eligible config (no forced_gate/exploratory/rank veto), "
                 "a local raw_port without api_base_url, viable: full and --stage all")

    model = cfg["model"]
    inference_engine = cfg["inference_engine"]
    served_model_id = orch.get("served_model_id")
    # Mei deliberately serves a stable local directory/alias ID while log
    # rows retain the source artifact ID in `model`. Other frameworks request
    # the model ID directly as before. (oMLX retired as an active lane
    # 2026-09-04; its served_model_id guard was removed with the lane.)
    if cfg.get("inference_engine") == "mei" and not served_model_id:
        sys.exit(f"{config_path} is inference_engine: mei but has no orchestration.served_model_id")
    request_model = served_model_id or model
    viable = orch.get("viable", "full")

    print(f"\n{'=' * 70}\n{model} ({inference_engine}) — {config_path}\nviable={viable}\n{'=' * 70}")

    if viable == "coding_only":
        print("SKIPPED: coding_only depends on the retired application runtime")
        return
    if viable in ("blocked", "retired"):
        reason = "config is blocked (see known_gaps)" if viable == "blocked" \
            else "lane is retired (historical evidence only — active local engines are llama.cpp variants + Mei)"
        print(f"SKIPPED ({viable}) — {reason}.")
        return

    raw_port = orch.get("raw_port")
    suite_config_path = admitted_config_snapshot(config_content or config_path.read_bytes(), config_hash)
    needs_proxy = orch.get("needs_proxy", False)
    proxy_port = orch.get("proxy_port", 8015)
    api_base_url = orch.get("api_base_url")

    if api_base_url and not orch.get("api_key_env"):
        sys.exit(f"{config_path} sets api_base_url but no api_key_env")
    if api_base_url and not os.environ.get(orch["api_key_env"]):
        print(f"FAILED: {orch['api_key_env']} is not set in the environment — "
              f"export it before running this config.")
        return

    if raw_port is not None:
        if cfg.get("inference_engine") == "mei":
            print("\n--- stop any prior isolated Mei server ---")
            run(mei_stop_command(cfg))
        print("\n--- unload any existing candidate backend ---")
        run(["bash", str(REPO / "runner" / "unload_all.sh")])

        clear_kv_cache_dir(cfg)

        free_bytes = shutil.disk_usage(REPO).free
        free_gb = free_bytes / (1024 ** 3)
        if (free_gb < MIN_FREE_DISK_GB_BEFORE_LAUNCH
                and not force_disk_gate and not allow_disk_floor_override):
            print(f"FAILED: only {free_gb:.1f}GB free (need at least "
                  f"{MIN_FREE_DISK_GB_BEFORE_LAUNCH:.0f}GB) — refusing to launch "
                  f"onto a nearly-full filesystem. Free up space and rerun this "
                  f"config.")
            return

        if force_disk_gate:
            # Suites must keep the admitted diagnostic identity even if the
            # authored config is edited while the server loads or tasks run.
            suite_config_path = _record_disk_preflight(config_path, config_hash, free_bytes)
            print(f"--- explicit exploratory disk opt-in: {free_gb:.3f} GiB free; "
                  f"normal floor {MIN_FREE_DISK_GB_BEFORE_LAUNCH:.0f} GiB; "
                  f"disk gate overridden={free_gb < MIN_FREE_DISK_GB_BEFORE_LAUNCH}; "
                  "rank-ineligible (results/disk_preflight.jsonl) ---")

        if allow_disk_floor_override:
            suite_config_path = _record_authorized_disk_floor_override(
                config_path, config_content, config_hash, free_bytes)
            print(f"--- explicitly authorized one-run disk-floor waiver: {free_gb:.3f} GiB free; "
                  f"normal floor {MIN_FREE_DISK_GB_BEFORE_LAUNCH:.0f} GiB; "
                  f"disk gate overridden={free_gb < MIN_FREE_DISK_GB_BEFORE_LAUNCH}; "
                  "ranking eligibility unchanged (results/disk_preflight.jsonl) ---")

        print("\n--- launch candidate server ---")
        alias = f"bench-{config_hash}" if inference_engine.startswith("llama.cpp") else None
        cmd = server_command(cfg, alias=alias)
        cmd = with_seed(cmd, seed)
        log_file = f"/tmp/bench_{config_path.parent.name}_{config_path.stem}_server.log"
        print(f"(backgrounded, log: {log_file})")
        # The file object is closed right after Popen() returns (adversarial
        # review finding L2: these were never closed at all) — safe to do
        # immediately since Popen dup()s the fd into the child before
        # returning; the child keeps its own copy independent of this
        # process's handle.
        with open(log_file, "w") as f:
            server_proc = subprocess.Popen(
                cmd, shell=True, cwd=str(REPO),
                stdout=f, stderr=subprocess.STDOUT,
            )

        if not wait_for_health(f"http://127.0.0.1:{raw_port}/v1/models", proc=server_proc):
            print(f"FAILED: backend never became healthy — check {log_file}")
            return
        if not assert_serving_expected_model(raw_port, model, alias=alias, served_model_id=served_model_id):
            print(f"FAILED: refusing to continue against the wrong model — check {log_file} "
                  f"and confirm no stale process survived unload_all.sh (e.g. `lsof -i :{raw_port}`).")
            return
        if not assert_plain_completion(f"http://127.0.0.1:{raw_port}/v1", request_model, timeout=900):
            print(f"FAILED: refusing to benchmark an endpoint that cannot complete a plain request — check {log_file}")
            return

        if needs_proxy:
            print("\n--- launch bench_local_proxy.py ---")
            parser = orch["proxy_parser"]
            upstream = f"http://127.0.0.1:{raw_port}"
            proxy_log = f"/tmp/bench_proxy_{proxy_port}.log"
            proxy_env = os.environ.copy()
            proxy_env.update({
                "BENCH_TOOL_PARSER": parser,
                "BENCH_PROXY_UPSTREAM": upstream,
                "BENCH_PROXY_PORT": str(proxy_port),
            })
            with open(proxy_log, "w") as f:
                proxy_proc = subprocess.Popen(
                    [sys.executable, str(REPO / "runner" / "bench_local_proxy.py")],
                    cwd=str(REPO), env=proxy_env,
                    stdout=f, stderr=subprocess.STDOUT,
                )
            if not wait_for_health(f"http://127.0.0.1:{proxy_port}/healthz", timeout=30, proc=proxy_proc):
                print(f"FAILED: proxy never became healthy — check {proxy_log}")
                return
            if not assert_proxy_matches(proxy_port, parser, upstream):
                print(f"FAILED: refusing to continue against a proxy pointed at the wrong "
                      f"parser/upstream — check {proxy_log} and confirm no stale proxy process "
                      f"survived unload_all.sh (e.g. `lsof -i :{proxy_port}`).")
                return

    base_url = api_base_url or f"http://127.0.0.1:{proxy_port if needs_proxy else raw_port}/v1"

    if cfg.get("inference_engine") == "mei" and cfg.get("mei_source_commit"):
        identity = verify_mei_runtime(cfg, base_url=base_url)
        print("Mei runtime provenance: " + json.dumps(identity, sort_keys=True))

    if cfg.get("benchmark_scope") == "peixinho-standin-v1":
        from run_standin_suite import selected_task_ids
        expected = set(selected_task_ids(cfg, cfg.get("standin_smoke", False)))
        with tempfile.TemporaryDirectory() as td:
            summary_path = Path(td) / "summary.json"
            command = [sys.executable, str(REPO / "runner" / "run_standin_suite.py"),
                       "--config", str(suite_config_path), "--source-config", str(config_path),
                       "--base-url", base_url, "--request-model", request_model,
                       "--trials", str(trials), "--partition", cfg.get("standin_partition", "development"),
                       "--summary-out", str(summary_path)]
            if cfg.get("standin_smoke", False):
                command.append("--smoke")
            proc = run(command)
            try:
                rows = json.loads(summary_path.read_text())
            except (OSError, ValueError):
                rows = None
            if proc.returncode != 0 or not complete_model_summary(rows, expected, trials):
                print("FAILED: stand-in suite did not complete with usable task/trial coverage")
                return
        return True

    for suite in MODEL_ONLY_SUITES:
        if suite != "sanity" and viable == "sanity_only":
            break
        print(f"\n--- {suite} ({MODEL_ONLY_SCOPE}) ---")
        expected = {task["id"] for task in yaml.safe_load(
            (REPO / "tasks" / f"{suite}.yaml").read_text())["tasks"]}
        with tempfile.TemporaryDirectory() as td:
            summary_path = Path(td) / "summary.json"
            command = [sys.executable, str(REPO / "runner" / "run_prompt_suite.py"),
                       "--suite", suite, "--base-url", base_url, "--model", model,
                       "--request-model", request_model, "--inference-engine", inference_engine,
                       "--config", str(suite_config_path), "--trials", str(trials),
                       "--benchmark-scope", MODEL_ONLY_SCOPE, "--summary-out", str(summary_path)]
            if suite == "model_tools" and generation_profile:
                command += ["--generation-profile", generation_profile]
            proc = run(command)
            try:
                rows = json.loads(summary_path.read_text())
            except (OSError, ValueError):
                rows = None
            if proc.returncode != 0 or not complete_model_summary(rows, expected, trials):
                print(f"FAILED: {suite} did not produce complete, usable model-only rows")
                _model_report()
                return
        if suite == "sanity":
            for task_id in expected:
                if not _majority_pass([row for row in rows if row["task_id"] == task_id]):
                    print(f"FAILED: {task_id}; stopping at the sanity gate")
                    _model_report()
                    return
    return _model_report()


def run_one(config_path: Path, trials: int = 1, coding_suites=None, stage="all",
            seed=None, generation_profile=None, reasoning=None, force_disk_gate=False,
            allow_disk_floor_override=False):
    """Run one config and always tear down the isolated Mei process.

    The implementation has many deliberate fail-fast returns.  Keeping cleanup
    in this outer wrapper ensures an identity, load, completion, sanity, or
    tool failure cannot strand a Metal model or stale port 8024-8027 process.
    (The oMLX lane was retired 2026-09-04; its isolated-server teardown was
    removed with it.)
    """
    # Parse/hash once and retain that identity for cleanup. Re-reading the
    # authored path in finally could skip teardown if it was edited or removed
    # while loading, even though the suites correctly use the forced snapshot.
    validate_model_only_scope(stage, coding_suites, reasoning)
    config_content = config_path.read_bytes()
    cfg = yaml.safe_load(config_content)
    config_hash = hashlib.sha256(config_content).hexdigest()[:12]
    if cfg.get("benchmark_scope") == "peixinho-standin-v1":
        from run_standin_suite import committed_config, validate_config
        validate_config(cfg)
        _, committed_bytes = committed_config(config_path)
        if committed_bytes != config_content:
            raise ValueError("stand-in config changed during admission")
    # Fail before teardown/unload/build: an immutable YAML pin must not silently
    # build the newer code now occupying its mutable checkout path.
    verify_mei_runtime(cfg)
    try:
        return _run_one_impl(
            config_path, cfg, config_hash, trials=trials, coding_suites=coding_suites, stage=stage,
            seed=seed, generation_profile=generation_profile, reasoning=reasoning,
            force_disk_gate=force_disk_gate,
            allow_disk_floor_override=allow_disk_floor_override,
            config_content=config_content,
        )
    finally:
        if isinstance(cfg, dict) and cfg.get("inference_engine") == "mei":
            run(mei_stop_command(cfg))


def _leaderboard():
    run([sys.executable, str(REPO / "runner" / "build_leaderboard.py")])
    # Best-effort: regenerate the composite-score chart alongside the
    # table every time (2026-08-27, user request) so LEADERBOARD.md's
    # embedded image never lags behind a real leaderboard rebuild. Not
    # fatal if it fails (e.g. too early in a run for any group to have
    # cleared the "all three axes present" eligibility check yet) --
    # losing the chart for one cycle is not worth aborting the leaderboard
    # rebuild that just succeeded.
    # plot_leaderboard.py needs matplotlib, which the interpreter running THIS
    # script does not necessarily have -- run_bench is routinely launched with a
    # bare python3. That made the chart step fail silently-but-non-fatally on
    # every single run: results/score_chart.png sat unchanged from 2026-09-06
    # through 2026-09-08 while the ranking underneath it changed twice, and
    # nobody noticed because the failure is by design not fatal. The repo's
    # canonical environment is `uv sync --locked` (see runner/requirements.txt),
    # so ask uv for the interpreter first and only fall back to our own.
    # Pin the project and the lockfile explicitly: `uv run` otherwise discovers
    # the project from the caller's working directory, which -- when the chart
    # step runs from elsewhere -- can resolve to an unrelated project (or none)
    # whose environment lacks matplotlib.
    plot_script = str(REPO / "runner" / "plot_leaderboard.py")
    plot_cmds = [
        ["uv", "run", "--quiet", "--project", str(REPO), "--locked", "python3", plot_script],
        [sys.executable, plot_script],
    ]
    for cmd in plot_cmds:
        try:
            result = run(cmd)
        except FileNotFoundError:
            continue          # uv not installed on this machine
        if result.returncode == 0:
            break
        print(f"plot_leaderboard.py via {cmd[0]} exited {result.returncode}")
    else:
        print("plot_leaderboard.py failed on every interpreter (non-fatal); "
              "results/score_chart.png is now STALE")


def sweep_stale_run_dirs(min_age_seconds=3600):
    """Remove leftover runner/runs/tmp*/ directories from a killed run
    (adversarial review finding L1) — found one live: a full git-initialized
    fixture copy from a task that never got to clean up its own
    TemporaryDirectory context manager. Harmless (gitignored) but
    accumulates indefinitely otherwise. Only sweeps directories older than
    min_age_seconds (default 1h, comfortably longer than any real task
    takes) so this can never race a genuinely concurrent run's own
    in-progress temp dir."""
    runs_root = REPO / "runner" / "runs"
    if not runs_root.is_dir():
        return
    now = time.time()
    for child in runs_root.iterdir():
        if child.is_dir() and (now - child.stat().st_mtime) > min_age_seconds:
            shutil.rmtree(child, ignore_errors=True)


def build_arg_parser():
    ap = argparse.ArgumentParser()
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--config", help="path to one configs/<model>/<backend>.yaml")
    group.add_argument("--all", action="store_true", help="run every configs/*/*.yaml in sequence")
    disk_options = ap.add_mutually_exclusive_group()
    disk_options.add_argument("--force-disk-gate", action="store_true", default=False,
                    help="explicit disk-floor-only opt-in for one exploratory --config "
                         "run (--stage all). Requires orchestration.forced_gate: true, "
                         "exploratory: true and rank_eligible: false; records the disk "
                         "observation, never skips identity/health/sanity/speed checks")
    disk_options.add_argument("--allow-disk-floor-override", action="store_true", default=False,
                    help="explicitly authorized one-run disk-floor waiver for one local "
                         "--config (--stage all). Requires orchestration."
                         "disk_floor_override_authorized: true and a rank-eligible config; "
                         "persists prelaunch evidence, preserves ranking eligibility and all other gates")
    ap.add_argument("--seed", type=int, default=None,
                    help="sampling seed passed to the Mei server. NOTE: this "
                         "benchmark runs GREEDY (temperature 0), so the seed is "
                         "inert here — measured, seed 101 differed from the "
                         "unseeded run on 0 of 10 token-recorded tasks. Use "
                         "--trials for repeats (finding C5); this flag is only "
                         "useful if the harness is ever run non-greedy")
    ap.add_argument("--trials", type=int, default=1,
                     help="run each task N times per config (default 1) — see "
                          "run_fixture_suite.py's --trials help (adversarial review "
                          "finding C5: single-trial temperature=0 results aren't reliably "
                          "reproducible on MLX/Metal)")
    ap.add_argument("--coding-suites", default=None,
                    help="retired; Hermes coding suites cannot run")
    ap.add_argument("--inference-engine", default=None,
                    help="with --all, run only configs whose top-level inference_engine "
                         "matches this value (for example: mei); keeps an engine sweep from "
                         "re-running every historical/retired llama.cpp/vllm-mlx/omlx "
                         "config. Note oMLX and vllm-mlx are retired active lanes "
                         "(2026-09-04) and are always skipped regardless of this flag.")
    ap.add_argument("--stage", choices=("all", "model", "coding"), default="all",
                    help="all/model run current model-only suites; coding is retired")
    ap.add_argument("--generation-profile", default=None,
                    help="named request sampling profile for model_tools; sanity remains deterministic")
    ap.add_argument("--reasoning", default=None, help="retired coding option; current runs refuse it")

    return ap


def _discover_ordered_configs(repo, inference_engine=None):
    """Return the --all / engine-sweep config list, in run order.

    Enumerates `configs/*/*.yaml`, keeps only files whose top-level dict has an
    `orchestration:` block (a stray non-config .yaml must never become a run —
    adversarial review finding L3), optionally filters by a top-level
    `inference_engine`, then sorts deterministically.

    Ordering (added 2026-09-05): a config may carry an optional
    `orchestration.run_order` int (higher = later in the sweep); configs that
    omit it default to 0. Sorting by `(run_order, path)` keeps every existing
    config in its historical lexical order while letting a late-added model
    (e.g. configs/Ling-3.0-tiny/mei.yaml, whose directory would otherwise
    lexically sort before Ornith) run LAST in the four-model Mei sweep without
    renaming its directory. One-config `--config` runs ignore this entirely.
    """
    candidates = sorted(repo.glob("configs/*/*.yaml"))
    entries = []
    for c in candidates:
        try:
            loaded = yaml.safe_load(c.read_text())
        except yaml.YAMLError:
            continue
        if not (isinstance(loaded, dict) and "orchestration" in loaded):
            continue
        if inference_engine is not None and loaded.get("inference_engine") != inference_engine:
            continue
        run_order = 0
        orch = loaded.get("orchestration")
        if isinstance(orch, dict):
            raw = orch.get("run_order")
            if isinstance(raw, int) and not isinstance(raw, bool):
                run_order = raw
        entries.append((run_order, c))
    entries.sort()  # deterministic: (run_order, path)
    return [p for _, p in entries]


def main():
    ap = build_arg_parser()
    args = ap.parse_args()
    if args.force_disk_gate and (args.all or args.stage != "all"):
        ap.error("--force-disk-gate requires a single --config with --stage all")
    if args.allow_disk_floor_override and (args.all or args.stage != "all"):
        ap.error("--allow-disk-floor-override requires a single --config with --stage all")
    try:
        validate_model_only_scope(args.stage, args.coding_suites, args.reasoning)
    except ValueError as exc:
        ap.error(str(exc))
    coding_suites = None

    # After parse_args(), not before (adversarial review finding L-7) — this
    # used to run before argument parsing at all, so it fired on --help and
    # on invalid arguments too, not just a real invocation.
    sweep_stale_run_dirs()

    if args.all:
        # _discover_ordered_configs enumerates only files with an
        # orchestration: block (a stray non-config .yaml in a model directory
        # must never become a run — adversarial review finding L3) and sorts
        # by optional orchestration.run_order (existing configs unchanged).
        configs = _discover_ordered_configs(REPO, inference_engine=args.inference_engine)
        print(f"Running {len(configs)} configs...")
        failed = []
        for i, config_path in enumerate(configs, 1):
            print(f"\n\n########## [{i}/{len(configs)}] {config_path} ##########")
            if not run_one(
                config_path, trials=args.trials, coding_suites=coding_suites,
                stage=args.stage, seed=args.seed, generation_profile=args.generation_profile,
                reasoning=args.reasoning,
            ):
                failed.append(str(config_path))
        if failed:
            print(f"\n{len(failed)} of {len(configs)} configs did not run: "
                  + ", ".join(failed))
            sys.exit(1)
    else:
        if not run_one(
            Path(args.config), trials=args.trials, coding_suites=coding_suites,
            stage=args.stage, seed=args.seed, generation_profile=args.generation_profile,
            reasoning=args.reasoning,
            force_disk_gate=args.force_disk_gate,
            allow_disk_floor_override=args.allow_disk_floor_override,
        ):
            sys.exit(1)


if __name__ == "__main__":
    main()
