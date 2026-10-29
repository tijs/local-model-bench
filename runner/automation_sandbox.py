"""Fail-closed, read-only Python execution for synthetic automation fixtures.

macOS Seatbelt is a containment boundary, not a Python language filter. Scripts
can read only their copied fixture workspace, the interpreter's standard library
and a small set of system runtime paths. They emit their result on stdout: all
filesystem writes, network access and process creation remain denied.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import math
import os
import platform
import re
import selectors
import signal
import subprocess
import sys
import tempfile
import time
import zoneinfo
from pathlib import Path
from typing import Any, BinaryIO, cast

POLICY_VERSION = "macos-seatbelt-python-readonly-v1"
SANDBOX_LIBRARY = "/usr/lib/libsandbox.dylib"
MAX_OUTPUT_BYTES = 65_536
MAX_SCRIPT_BYTES = 65_536
MAX_FILE_BYTES = 1_048_576
MAX_MEMORY_BYTES = 268_435_456
SAMPLE_SECONDS = 0.025


class SandboxUnavailable(RuntimeError):
    """Containment could not be established; never retry without it."""


def _quoted(path: Path | str) -> str:
    value = str(path)
    if any(ord(char) < 32 for char in value):
        raise ValueError("sandbox paths cannot contain control characters")
    return json.dumps(value, ensure_ascii=False)


def _runtime() -> tuple[Path, Path]:
    if platform.system() != "Darwin":
        raise SandboxUnavailable("this executor requires macOS native Seatbelt")
    executable = Path(sys.executable).resolve(strict=True)
    prefix = Path(sys.base_prefix).resolve(strict=True)
    if not executable.is_relative_to(prefix) or len(prefix.parts) < 4:
        raise SandboxUnavailable("a dedicated Python runtime prefix is required")
    return executable, prefix


def _profile(workspace: Path, prefix: Path) -> str:
    # A literal root-directory read is required by this Python/dyld startup;
    # it grants neither recursive root access nor access to private file data.
    roots = [
        prefix,
        workspace,
        Path("/System/Library"),
        Path("/usr/lib"),
        Path("/private/var/db/timezone"),
        Path("/var/db/timezone"),
    ]
    for value in zoneinfo.TZPATH:
        path = Path(value)
        if path.is_dir() and str(path.resolve()).startswith(
            "/private/var/db/timezone/"
        ):
            roots.extend([path, path.resolve()])
    readable = " ".join(f"(subpath {_quoted(path)})" for path in roots)
    return (
        "(version 1)\n(deny default)\n"
        "(deny process-info* process-fork process-exec network* file-write* mach*)\n"
        # Numeric KERN_PROCARGS2 bypasses the high-level sysctl-read rule.
        # Deny its underlying syscalls. process-info* also needs an explicit
        # denial: a default-only rule did not prevent proc_pidinfo on this OS.
        # These names/filter syntax come from Apple's installed SDK and profiles.
        "(deny syscall-unix (syscall-number SYS_sysctl) "
        "(syscall-number SYS_sysctlbyname))\n"
        f'(allow file-read* (literal "/") (literal "/var") {readable} '
        '(literal "/dev/null") (literal "/dev/urandom"))\n'
    )


_LIMIT_BOOTSTRAP = """
import ctypes, os, resource, runpy, sys
cpu = int(sys.argv[1])
file_size = int(sys.argv[2])
profile = sys.argv[3]
candidate = sys.argv[4:]
resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 1))
resource.setrlimit(resource.RLIMIT_FSIZE, (file_size, file_size))
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
library = ctypes.CDLL('/usr/lib/libsandbox.dylib')
install = library.sandbox_init
install.argtypes = [ctypes.c_char_p, ctypes.c_uint64, ctypes.POINTER(ctypes.c_char_p)]
install.restype = ctypes.c_int
error = ctypes.c_char_p()
if install(profile.encode('utf-8'), 0, ctypes.byref(error)) != 0:
    print('native Seatbelt initialization failed', file=sys.stderr)
    raise SystemExit(125)
if candidate == ['--ready']:
    # Fail closed if this OS accepts the profile but does not enforce the
    # process-introspection denials. Probe only our own clean process data.
    libc = ctypes.CDLL(None, use_errno=True)
    libc.sysctl.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_uint,
                           ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t),
                           ctypes.c_void_p, ctypes.c_size_t]
    mib = (ctypes.c_int * 3)(1, 49, os.getpid())
    size = ctypes.c_size_t(0)
    if libc.sysctl(mib, 3, None, ctypes.byref(size), None, 0) != -1 or ctypes.get_errno() != 1:
        raise SystemExit(125)
    process = ctypes.CDLL('/usr/lib/libproc.dylib', use_errno=True)
    process.proc_pidinfo.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64,
                                    ctypes.c_void_p, ctypes.c_int]
    buffer = ctypes.create_string_buffer(1024)
    ctypes.set_errno(0)
    if process.proc_pidinfo(os.getpid(), 3, 0, buffer, 1024) != 0 or ctypes.get_errno() != 1:
        raise SystemExit(125)
    print('AUTOMATION_SANDBOX_READY')
else:
    sys.argv = candidate
    runpy.run_path(candidate[0], run_name='__main__')
""".strip()


def _memory_reader() -> Any:
    try:
        library = ctypes.CDLL("/usr/lib/libproc.dylib")
        function = library.proc_pid_rusage
        function.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_void_p]
        function.restype = ctypes.c_int
        return function
    except (OSError, AttributeError) as exc:
        raise SandboxUnavailable("physical-memory monitoring is unavailable") from exc


def _footprint(function: Any, pid: int) -> int | None:
    buffer = ctypes.create_string_buffer(4096)
    if function(pid, 0, ctypes.byref(buffer)) != 0:
        return None
    # Darwin rusage_info_v0: physical footprint follows resident size at byte72.
    return int.from_bytes(buffer.raw[72:80], sys.byteorder)


def _kill(proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is None:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    proc.wait(timeout=5)


def _execute(
    command: list[str],
    workspace: Path,
    profile: str,
    timeout: float,
    memory_reader: Any,
) -> dict[str, Any]:
    cpu_seconds = max(1, math.ceil(timeout))
    started = time.monotonic()
    environment = {
        "HOME": str(workspace),
        "TMPDIR": str(workspace),
        "PATH": "/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "TZ": "UTC",
    }
    output: dict[str, bytearray] = {"stdout": bytearray(), "stderr": bytearray()}
    limit_reason = None
    peak_memory = 0
    proc: subprocess.Popen[bytes] | None = None
    try:
        # A constant trusted launcher applies limits and enters Seatbelt before
        # loading candidate code. No process-exec grant is needed, even for the
        # initial interpreter, so scripts cannot replace it to bypass its flags.
        # Avoid preexec_fn, which can deadlock when called from threaded hosts.
        proc = subprocess.Popen(
            [
                command[0],
                "-I",
                "-S",
                "-B",
                "-X",
                "utf8",
                "-c",
                _LIMIT_BOOTSTRAP,
                str(cpu_seconds),
                str(MAX_FILE_BYTES),
                profile,
                *command[1:],
            ],
            cwd=workspace,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True,
            start_new_session=True,
        )
        with selectors.DefaultSelector() as selector:
            assert proc.stdout is not None and proc.stderr is not None
            for name, stream in [("stdout", proc.stdout), ("stderr", proc.stderr)]:
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, name)
            while selector.get_map() or proc.poll() is None:
                if proc.poll() is None:
                    footprint = _footprint(memory_reader, proc.pid)
                    if footprint is None and proc.poll() is None:
                        raise SandboxUnavailable("lost live process memory monitoring")
                    peak_memory = max(peak_memory, footprint or 0)
                    if peak_memory > MAX_MEMORY_BYTES:
                        limit_reason = "memory"
                    elif time.monotonic() - started >= timeout:
                        limit_reason = "wall_time"
                    if limit_reason:
                        _kill(proc)
                for key, _ in selector.select(SAMPLE_SECONDS):
                    stream = cast(BinaryIO, key.fileobj)
                    chunk = os.read(key.fd, MAX_OUTPUT_BYTES)
                    if not chunk:
                        selector.unregister(stream)
                        stream.close()
                        continue
                    remaining = MAX_OUTPUT_BYTES - sum(map(len, output.values()))
                    output[key.data].extend(chunk[:remaining])
                    if len(chunk) > remaining:
                        limit_reason = limit_reason or "output"
                        _kill(proc)
            proc.wait(timeout=5)
        if (
            proc.returncode in (-signal.SIGXCPU, -signal.SIGKILL)
            and limit_reason is None
        ):
            limit_reason = "cpu_or_external_kill"
        decoded: dict[str, str] = {}
        remaining = MAX_OUTPUT_BYTES
        for name, content in output.items():
            # Invalid UTF-8 replacement can expand bytes. Bound the actual UTF-8
            # tool-response payload as well as the raw bytes read from pipes.
            text = content.decode("utf-8", errors="replace")
            decoded[name] = text.encode("utf-8")[:remaining].decode(
                "utf-8", errors="ignore"
            )
            remaining -= len(decoded[name].encode("utf-8"))
        return {
            "returncode": proc.returncode,
            "stdout": decoded["stdout"],
            "stderr": decoded["stderr"],
            "timed_out": limit_reason in ("wall_time", "cpu_or_external_kill"),
            "limit_reason": limit_reason,
            "wall_seconds": time.monotonic() - started,
            "peak_memory_bytes": peak_memory,
        }
    except (OSError, subprocess.SubprocessError) as exc:
        raise SandboxUnavailable(
            f"sandbox launch/monitor failed: {type(exc).__name__}"
        ) from exc
    finally:
        if proc is not None:
            _kill(proc)
            for stream in (proc.stdout, proc.stderr):
                if stream is not None:
                    stream.close()


def run_python(
    workspace: Path,
    script: str = "solution.py",
    args: list[str] | None = None,
    timeout: float = 5,
) -> dict[str, Any]:
    """Execute a copied script against read-only synthetic inputs, returning JSON data.

    The caller must provide a dedicated directory below the OS temporary root.
    Writes happen through the trusted harness before execution, never the script.
    Memory is monitored every25ms; CPU/file-size/output bounds are separate limits.
    Availability failures raise SandboxUnavailable and must be harness errors.
    """
    executable, prefix = _runtime()
    memory_reader = _memory_reader()
    root = Path(workspace)
    if root.is_symlink():
        raise ValueError("workspace root cannot be a symlink")
    root = root.resolve(strict=True)
    temporary = Path(tempfile.gettempdir()).resolve()
    if root == temporary or not root.is_relative_to(temporary) or not root.is_dir():
        raise ValueError("use a dedicated workspace under the OS temporary directory")
    if not isinstance(script, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+\.py", script):
        raise ValueError("script must be a simple Python filename")
    path = root / script
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_size > MAX_SCRIPT_BYTES
    ):
        raise ValueError("script must be a regular bounded file in the workspace")
    if (
        not isinstance(timeout, (int, float))
        or isinstance(timeout, bool)
        or not math.isfinite(timeout)
        or not 0 < timeout <= 30
    ):
        raise ValueError("timeout must be finite and between0 and30 seconds")
    arguments = args if args is not None else []
    if (
        not isinstance(arguments, list)
        or len(arguments) > 32
        or any(
            not isinstance(arg, str) or "\0" in arg or len(arg) > 1024
            for arg in arguments
        )
    ):
        raise ValueError("args must be a bounded list of strings")
    profile = _profile(root, prefix)
    ready = _execute(
        [str(executable), "--ready"],
        root,
        profile,
        2,
        memory_reader,
    )
    if ready["returncode"] != 0 or ready["stdout"] != "AUTOMATION_SANDBOX_READY\n":
        raise SandboxUnavailable("sandboxed interpreter preflight failed")
    result = _execute(
        [str(executable), str(path), *arguments], root, profile, timeout, memory_reader
    )
    result["isolation"] = {
        "policy_version": POLICY_VERSION,
        "backend": "macos-native-seatbelt-sandbox_init",
        "library": SANDBOX_LIBRARY,
        "profile_sha256": hashlib.sha256(profile.encode()).hexdigest(),
        "profile_template_sha256": hashlib.sha256(
            profile.replace(_quoted(root), _quoted("<WORKSPACE>")).encode()
        ).hexdigest(),
        "limit_bootstrap_sha256": hashlib.sha256(_LIMIT_BOOTSTRAP.encode()).hexdigest(),
        "python_executable": str(executable),
        "python_version": platform.python_version(),
        "python_full_version": sys.version,
        "python_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
        "host_os": platform.platform(),
        "host_arch": platform.machine(),
        "runtime_read_root": str(prefix),
        "workspace_mode": "read-only",
        "network": "denied",
        "process_creation": "denied",
        "process_replacement": "denied",
        "syscalls_denied": ["sysctl", "sysctlbyname"],
        "process_inspection": "explicit process-info* denial",
        "filesystem_writes": "denied",
        "max_output_bytes": MAX_OUTPUT_BYTES,
        "max_file_bytes": MAX_FILE_BYTES,
        "max_script_bytes": MAX_SCRIPT_BYTES,
        "cpu_seconds": max(1, math.ceil(timeout)),
        "cpu_hard_seconds": max(1, math.ceil(timeout)) + 1,
        "wall_seconds": timeout,
        "memory_stop_bytes": MAX_MEMORY_BYTES,
        "memory_sample_seconds": SAMPLE_SECONDS,
    }
    return result
