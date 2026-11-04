import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, "/Users/tijs/projects/local-model-bench/runner")
from owned_process import OwnedSession
from supervise_bench import baseline_ready, gate_reason, sample

root = Path(tempfile.mkdtemp(prefix="mei-affine-real-slices-20261104-"))
fixture = root / "fixture"
fixture.mkdir()
baseline = []
for _ in range(7):
    baseline.append(sample(os.getpid(), root))
    time.sleep(1)
(root / "baseline.json").write_text(json.dumps(baseline, indent=2))
if not baseline_ready(baseline, None, 0):
    print(f"PREFLIGHT DECLINED {root}", flush=True)
    raise SystemExit(2)
environment = os.environ.copy()
environment.update({
    "DEVELOPER_DIR": "/Applications/Xcode.app/Contents/Developer",
    "MTL_DEBUG_LAYER": "1",
    "METAL_DEVICE_WRAPPER_TYPE": "1",
    "VMLX_QWEN35_REAL_SLICE_MODEL": "/Users/tijs/.local/share/local-model-bench/mei-models/Qwen3.6-35B-A3B-4bit-textonly",
})
command = ["swift", "test", "-j", "2", "--skip-build", "--scratch-path",
           "/tmp/mei-residency-diagnostic-build", "--filter", "sampleRealExpertSlices"]
reason = None
process = None
session = None
start = time.monotonic()
try:
    with (root / "test.log").open("w") as output, (root / "telemetry.jsonl").open("w") as telemetry:
        process = subprocess.Popen(command, cwd="/Users/tijs/projects/mei-affine-streaming-fixture-20261104",
                                   env=environment, stdout=output, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        session = OwnedSession(process)
        print(f"START {process.pid} {root}", flush=True)
        warnings = 0
        while not session.leader_exited():
            current = sample(process.pid, root)
            telemetry.write(json.dumps(current) + "\n")
            telemetry.flush()
            warnings = warnings + 1 if current["kernel_pressure_level"] >= 2 else 0
            reason = gate_reason(current, baseline[-1], 0, warnings, percent_stop=False)
            if reason is None and time.monotonic() - start > 300:
                reason = "deadline"
            if reason:
                break
            time.sleep(2)
except BaseException as exc:
    reason = f"monitor error: {type(exc).__name__}: {exc}"
finally:
    if session is not None:
        session.stop(grace_seconds=10)
    result = {"returncode": process.returncode if process else None,
              "reason": reason, "elapsed_seconds": time.monotonic() - start}
    (root / "outcome.json").write_text(json.dumps(result, indent=2))
    print(f"DONE {root} {result}", flush=True)
if reason or not process or process.returncode != 0:
    raise SystemExit(1)
