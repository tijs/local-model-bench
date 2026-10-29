"""Owned synthetic-canary probes; never inspect unrelated/private processes."""

import json
import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from automation_sandbox import run_python


def candidate(code):
    with tempfile.TemporaryDirectory(prefix="automation-security-owned-") as d:
        p = Path(d)
        (p / "solution.py").write_text(code)
        result = run_python(p, timeout=5)
        return {
            k: result[k] for k in ("returncode", "stdout", "stderr", "limit_reason")
        }


def mach_probe():
    child_code = (
        "import ctypes,json,os,time\n"
        'b=ctypes.create_string_buffer(b"OWNED_MACH_SYNTHETIC_CANARY")\n'
        'print(json.dumps({"pid":os.getpid(),"address":ctypes.addressof(b),"size":len(b)}),flush=True)\n'
        "time.sleep(30)\n"
    )
    owned = subprocess.Popen(
        [sys.executable, "-I", "-S", "-c", child_code],
        env={},
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        info = json.loads(owned.stdout.readline())
        code = (
            """import ctypes,json
lib=ctypes.CDLL(None,use_errno=True)
self_port=ctypes.c_uint.in_dll(lib,'mach_task_self_').value
result={}
for name in ['task_name_for_pid','task_for_pid']:
 fn=getattr(lib,name);fn.argtypes=[ctypes.c_uint,ctypes.c_int,ctypes.POINTER(ctypes.c_uint)];fn.restype=ctypes.c_int
 port=ctypes.c_uint();rc=fn(self_port,TARGET_PID,ctypes.byref(port));result[name]={'rc':rc,'got_port':bool(port.value)}
 if name=='task_for_pid' and rc==0:
  fn2=lib.mach_vm_read_overwrite;fn2.argtypes=[ctypes.c_uint,ctypes.c_uint64,ctypes.c_uint64,ctypes.c_uint64,ctypes.POINTER(ctypes.c_uint64)];fn2.restype=ctypes.c_int
  b=ctypes.create_string_buffer(TARGET_SIZE);n=ctypes.c_uint64()
  r=fn2(port.value,TARGET_ADDRESS,TARGET_SIZE,ctypes.addressof(b),ctypes.byref(n));result['memory_read']={'rc':r,'leaked':b'OWNED_MACH_SYNTHETIC_CANARY' in b.raw}
print(json.dumps(result))
""".replace("TARGET_PID", str(info["pid"]))
            .replace("TARGET_SIZE", str(info["size"]))
            .replace("TARGET_ADDRESS", str(info["address"]))
        )
        control = subprocess.run(
            [sys.executable, "-I", "-S", "-c", code],
            env={},
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        return {"control": json.loads(control.stdout), "sandboxed": candidate(code)}
    finally:
        owned.terminate()
        owned.wait(timeout=5)
        owned.stdout.close()


def reinstall_probe():
    with tempfile.TemporaryDirectory(prefix="sandbox-reinstall-owned-") as d:
        root = Path(d)
        canary = root / "owned.txt"
        canary.write_text("SYNTHETIC_REINSTALL_CANARY")
        code = """import ctypes,json
lib=ctypes.CDLL('/usr/lib/libsandbox.dylib',use_errno=True)
fn=lib.sandbox_init;fn.argtypes=[ctypes.c_char_p,ctypes.c_uint64,ctypes.POINTER(ctypes.c_char_p)];fn.restype=ctypes.c_int
error=ctypes.c_char_p();rc=fn(b'(version 1)(allow default)',0,ctypes.byref(error));errno=ctypes.get_errno()
try:
 data=open(CANARY_PATH).read();leaked='SYNTHETIC_REINSTALL_CANARY' in data
except PermissionError:leaked=False
print(json.dumps({'reinstall_rc':rc,'errno':errno,'leaked':leaked}))
""".replace("CANARY_PATH", repr(str(canary)))
        return candidate(code)


def signal_probe():
    child_code = (
        "import signal,time\n"
        "signal.signal(signal.SIGUSR1,lambda *a: print('OWNED_SIGNAL_RECEIVED',flush=True))\n"
        "print('READY',flush=True)\ntime.sleep(20)\n"
    )
    owned = subprocess.Popen(
        [sys.executable, "-I", "-S", "-c", child_code],
        env={},
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert owned.stdout.readline().strip() == "READY"
        os.kill(owned.pid, signal.SIGUSR1)
        assert owned.stdout.readline().strip() == "OWNED_SIGNAL_RECEIVED"
        code = (
            f"import os,signal,json\ntry:\n os.kill({owned.pid},signal.SIGUSR1); denied=False\n"
            "except PermissionError: denied=True\nprint(json.dumps({'signal_denied':denied}))\n"
        )
        return {"control_signal_received": True, "sandboxed": candidate(code)}
    finally:
        owned.terminate()
        owned.wait(timeout=5)
        owned.stdout.close()


if __name__ == "__main__":
    print(
        json.dumps(
            {
                "mach": mach_probe(),
                "reinstall": reinstall_probe(),
                "signal": signal_probe(),
            },
            indent=2,
        )
    )
