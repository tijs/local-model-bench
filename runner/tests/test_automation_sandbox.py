"""Exercise the actual OS boundary before any model-authored script is run."""

from __future__ import annotations

import json
import os
import platform
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from automation_sandbox import (
    MAX_OUTPUT_BYTES,
    POLICY_VERSION,
    SandboxUnavailable,
    run_python,
)


@unittest.skipUnless(platform.system() == "Darwin", "actual macOS Seatbelt tests")
class SandboxBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="python-automation-test-")
        self.root = Path(self.temp.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self.canary = self.root / "private-canary.txt"
        self.canary.write_text("OUTSIDE_SYNTHETIC_CANARY")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_code(self, code: str, **kwargs):
        (self.workspace / "solution.py").write_text(code)
        return run_python(self.workspace, **kwargs)

    def test_stdlib_transform_unicode_decimal_and_timezone(self) -> None:
        (self.workspace / "input.csv").write_text(
            'name,amount\n"Café, food",0.10\nMilk,0.20\n'
        )
        result = self.run_code(
            "import csv,json,sys\n"
            "from decimal import Decimal\n"
            "from datetime import datetime\n"
            "from zoneinfo import ZoneInfo\n"
            "with open(sys.argv[1],newline='') as f: rows=list(csv.DictReader(f))\n"
            "print(json.dumps({'total':str(sum((Decimal(r['amount']) for r in rows),Decimal(0))),"
            "'first':rows[0]['name'],'hour':datetime(2026,1,1,tzinfo=ZoneInfo('Europe/Amsterdam')).hour}))\n",
            args=["input.csv"],
        )
        self.assertEqual(result["returncode"], 0, result)
        self.assertEqual(
            json.loads(result["stdout"]),
            {"total": "0.30", "first": "Café, food", "hour": 0},
        )
        self.assertEqual(result["isolation"]["policy_version"], POLICY_VERSION)
        self.assertEqual(result["isolation"]["workspace_mode"], "read-only")

    def test_outside_read_and_write_are_denied(self) -> None:
        result = self.run_code(
            "import json\n"
            f"path={str(self.canary)!r}\n"
            "denied=[]\n"
            "for mode in ('r','w'):\n"
            " try:\n"
            "  with open(path,mode) as f: f.read() if mode=='r' else f.write('changed')\n"
            " except PermissionError: denied.append(mode)\n"
            "print(json.dumps(denied))\n"
        )
        self.assertEqual(result["returncode"], 0, result)
        self.assertEqual(json.loads(result["stdout"]), ["r", "w"])
        self.assertEqual(self.canary.read_text(), "OUTSIDE_SYNTHETIC_CANARY")

    def test_symlink_directory_and_file_cannot_escape(self) -> None:
        (self.workspace / "outside.txt").symlink_to(self.canary)
        (self.workspace / "outside-dir").symlink_to(self.root, target_is_directory=True)
        result = self.run_code(
            "import json\n"
            "denied=[]\n"
            "for path in ('outside.txt','outside-dir/private-canary.txt'):\n"
            " try: open(path).read()\n"
            " except PermissionError: denied.append(path)\n"
            "print(json.dumps(denied))\n"
        )
        self.assertEqual(result["returncode"], 0, result)
        self.assertEqual(len(json.loads(result["stdout"])), 2)
        self.assertNotIn("OUTSIDE_SYNTHETIC_CANARY", result["stdout"])

    def test_no_workspace_writes_or_fixture_mutation(self) -> None:
        fixture = self.workspace / "input.json"
        fixture.write_text('{"unchanged": true}')
        result = self.run_code(
            "import json,os\n"
            "denied=[]\n"
            "for name,operation in ["
            "('overwrite',lambda:open('input.json','w')),"
            "('new',lambda:open('new.txt','w')),"
            "('unlink',lambda:os.unlink('input.json')),"
            "('mkdir',lambda:os.mkdir('scratch')),"
            "('symlink',lambda:os.symlink('input.json','link'))]:\n"
            " try: operation()\n"
            " except PermissionError: denied.append(name)\n"
            "print(json.dumps(denied))\n"
        )
        self.assertEqual(result["returncode"], 0, result)
        self.assertEqual(len(json.loads(result["stdout"])), 5)
        self.assertEqual(fixture.read_text(), '{"unchanged": true}')
        self.assertEqual(
            sorted(p.name for p in self.workspace.iterdir()),
            ["input.json", "solution.py"],
        )

    def test_network_and_unix_sockets_are_denied(self) -> None:
        with (
            tempfile.TemporaryDirectory(prefix="pyauto-", dir="/tmp") as temp,
            socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp,
            socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as unix,
        ):
            tcp.bind(("127.0.0.1", 0))
            tcp.listen(1)
            unix_path = str(Path(temp) / "socket")
            unix.bind(unix_path)
            unix.listen(1)
            result = self.run_code(
                "import json,socket\n"
                "denied=[]\n"
                f"for kind,address in [(socket.AF_INET,{tcp.getsockname()!r}),"
                f"(socket.AF_UNIX,{unix_path!r})]:\n"
                " try:\n"
                "  with socket.socket(kind,socket.SOCK_STREAM) as s: s.connect(address)\n"
                " except PermissionError: denied.append(kind)\n"
                "print(json.dumps(denied))\n"
            )
            for listener in (tcp, unix):
                listener.setblocking(False)
                with self.assertRaises(BlockingIOError):
                    listener.accept()
        self.assertEqual(result["returncode"], 0, result)
        self.assertEqual(len(json.loads(result["stdout"])), 2)

    def test_fork_and_subprocess_including_same_python_are_denied(self) -> None:
        result = self.run_code(
            "import json,os,subprocess,sys\n"
            "denied=[]\n"
            "for name,operation in ["
            "('fork',lambda:os.fork()),"
            "('system',lambda:subprocess.run(['/usr/bin/true'],check=True)),"
            "('python',lambda:subprocess.run([sys.executable,'-I','-S','-c','print(1)'],check=True))]:\n"
            " try: operation()\n"
            " except PermissionError: denied.append(name)\n"
            "print(json.dumps(denied))\n"
        )
        self.assertEqual(result["returncode"], 0, result)
        self.assertEqual(json.loads(result["stdout"]), ["fork", "system", "python"])

    def test_same_interpreter_exec_replacement_is_denied(self) -> None:
        result = self.run_code(
            "import os,sys\n"
            "try: os.execve(sys.executable,[sys.executable,'-c','print(\"escaped\")'],{})\n"
            "except PermissionError: print('exec denied')\n"
        )
        self.assertEqual(result["returncode"], 0, result)
        self.assertEqual(result["stdout"], "exec denied\n")

    def test_sysctl_cannot_read_owned_process_canary(self) -> None:
        # The target contains only synthetic environment data. A positive control
        # proves this actual numeric-MIB/full-buffer probe works outside Seatbelt;
        # never target the test runner's potentially private environment.
        owned = subprocess.Popen(
            [sys.executable, "-I", "-S", "-c", "import time;time.sleep(20)"],
            env={"AUTOMATION_OWNED_CANARY": "ONLY_SYNTHETIC_ENVIRONMENT"},
        )
        code = (
            "import ctypes,json\n"
            "lib=ctypes.CDLL(None,use_errno=True)\n"
            f"mib=(ctypes.c_int*3)(1,49,{owned.pid})\n"
            "lib.sysctl.argtypes=[ctypes.POINTER(ctypes.c_int),ctypes.c_uint,ctypes.c_void_p,"
            "ctypes.POINTER(ctypes.c_size_t),ctypes.c_void_p,ctypes.c_size_t]\n"
            "size=ctypes.c_size_t(0)\n"
            "query=lib.sysctl(mib,3,None,ctypes.byref(size),None,0)\n"
            "buffer=ctypes.create_string_buffer(max(size.value,1))\n"
            "read=lib.sysctl(mib,3,buffer,ctypes.byref(size),None,0)\n"
            "print(json.dumps({'query':query,'read':read,'errno':ctypes.get_errno(),"
            "'leaked':b'ONLY_SYNTHETIC_ENVIRONMENT' in buffer.raw}))\n"
        )
        try:
            control = subprocess.run(
                [sys.executable, "-I", "-S", "-c", code],
                env={},
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            )
            self.assertTrue(json.loads(control.stdout)["leaked"])
            result = self.run_code(code)
            self.assertEqual(result["returncode"], 0, result)
            self.assertEqual(
                json.loads(result["stdout"]),
                {"query": -1, "read": -1, "errno": 1, "leaked": False},
            )
        finally:
            owned.terminate()
            owned.wait(timeout=5)

    def test_sysctlbyname_and_proc_info_syscalls_are_denied(self) -> None:
        result = self.run_code(
            "import ctypes,json,os\n"
            "lib=ctypes.CDLL(None,use_errno=True)\n"
            "buffer=ctypes.create_string_buffer(1024)\n"
            "size=ctypes.c_size_t(1024)\n"
            "lib.sysctlbyname.argtypes=[ctypes.c_char_p,ctypes.c_void_p,"
            "ctypes.POINTER(ctypes.c_size_t),ctypes.c_void_p,ctypes.c_size_t]\n"
            "a=lib.sysctlbyname(b'hw.memsize',buffer,ctypes.byref(size),None,0)\n"
            "first=[a,ctypes.get_errno()]\n"
            "proc=ctypes.CDLL('/usr/lib/libproc.dylib',use_errno=True)\n"
            "proc.proc_pidinfo.argtypes=[ctypes.c_int,ctypes.c_int,ctypes.c_uint64,"
            "ctypes.c_void_p,ctypes.c_int]\n"
            "ctypes.set_errno(0)\n"
            "b=proc.proc_pidinfo(os.getpid(),3,0,buffer,1024)\n"
            "print(json.dumps([first,[b,ctypes.get_errno()]]))\n"
        )
        self.assertEqual(result["returncode"], 0, result)
        self.assertEqual(json.loads(result["stdout"]), [[-1, 1], [0, 1]])

    def test_environment_and_python_site_are_isolated(self) -> None:
        with patch.dict(os.environ, {"AUTOMATION_PARENT_CANARY": "must-not-leak"}):
            result = self.run_code(
                "import os,sys,json\n"
                "print(json.dumps([os.environ.get('AUTOMATION_PARENT_CANARY'),"
                "sys.flags.isolated,sys.flags.no_site,sys.flags.dont_write_bytecode]))"
            )
        self.assertEqual(result["returncode"], 0, result)
        self.assertEqual(json.loads(result["stdout"]), [None, 1, 1, 1])

    def test_wall_limit_stops_sleeping_script(self) -> None:
        result = self.run_code("import time;time.sleep(20)", timeout=0.2)
        self.assertTrue(result["timed_out"])
        self.assertEqual(result["limit_reason"], "wall_time")
        self.assertLess(result["wall_seconds"], 2)
        self.assertNotEqual(result["returncode"], 0)

    def test_closing_output_pipes_does_not_bypass_wall_limit(self) -> None:
        result = self.run_code(
            "import os,time;os.close(1);os.close(2);time.sleep(20)", timeout=0.2
        )
        self.assertTrue(result["timed_out"])
        self.assertEqual(result["limit_reason"], "wall_time")
        self.assertLess(result["wall_seconds"], 2)

    def test_interruption_kills_and_reaps_candidate_process(self) -> None:
        import automation_sandbox

        original = automation_sandbox._footprint
        seen: list[int] = []

        def interrupted(function, pid):
            if not seen:
                seen.append(pid)
            elif pid != seen[0]:
                seen.append(pid)
                raise KeyboardInterrupt
            return original(function, pid)

        with (
            patch("automation_sandbox._footprint", side_effect=interrupted),
            self.assertRaises(KeyboardInterrupt),
        ):
            self.run_code("import time;time.sleep(20)")
        self.assertEqual(len(seen), 2)
        with self.assertRaises(ProcessLookupError):
            os.kill(seen[-1], 0)

    def test_cpu_loop_stops(self) -> None:
        result = self.run_code("while True: pass", timeout=0.2)
        self.assertTrue(result["timed_out"])
        self.assertLess(result["wall_seconds"], 2)

    def test_bounded_stdout_and_stderr(self) -> None:
        result = self.run_code(
            "import os\nwhile True:\n os.write(1,b'x'*32768)\n os.write(2,b'y'*32768)\n"
        )
        self.assertEqual(result["limit_reason"], "output")
        self.assertLessEqual(
            len(result["stdout"].encode()) + len(result["stderr"].encode()),
            MAX_OUTPUT_BYTES,
        )
        self.assertLess(result["wall_seconds"], 2)

    def test_memory_growth_is_stopped(self) -> None:
        result = self.run_code(
            "import time\nchunks=[]\nwhile True:\n chunks.append(bytearray(8*1024*1024))\n time.sleep(0.01)\n"
        )
        self.assertEqual(result["limit_reason"], "memory")
        self.assertFalse(result["timed_out"])
        self.assertLess(result["wall_seconds"], 3)

    def test_invalid_utf8_cannot_expand_tool_output_past_limit(self) -> None:
        result = self.run_code("import os\nwhile True: os.write(1,b'\\xff'*32768)")
        self.assertEqual(result["limit_reason"], "output")
        self.assertLessEqual(
            len(result["stdout"].encode()) + len(result["stderr"].encode()),
            MAX_OUTPUT_BYTES,
        )

    def test_script_symlink_and_oversize_are_rejected(self) -> None:
        link = self.workspace / "solution.py"
        link.symlink_to(self.canary)
        with self.assertRaises(ValueError):
            run_python(self.workspace)
        link.unlink()
        link.write_text("#" * 65_537)
        with self.assertRaises(ValueError):
            run_python(self.workspace)

    def test_path_args_and_timeout_validation(self) -> None:
        (self.workspace / "solution.py").write_text("print(1)")
        for kwargs in [
            {"script": "../solution.py"},
            {"script": "/tmp/solution.py"},
            {"timeout": float("nan")},
            {"timeout": float("inf")},
            {"timeout": True},
            {"timeout": 0},
            {"timeout": 31},
            {"args": ["bad\0arg"]},
        ]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                run_python(self.workspace, **kwargs)


@unittest.skipUnless(platform.system() == "Darwin", "actual macOS boundary probes")
class AdditionalOwnedProcessTests(unittest.TestCase):
    def test_mach_inspection_ports_and_memory_ports_are_not_acquired(self):
        from automation_security_probes import mach_probe

        result = mach_probe()
        self.assertTrue(result["control"]["task_name_for_pid"]["got_port"])
        sandboxed = json.loads(result["sandboxed"]["stdout"])
        self.assertFalse(sandboxed["task_name_for_pid"]["got_port"])
        self.assertFalse(sandboxed["task_for_pid"]["got_port"])
        self.assertFalse(sandboxed.get("memory_read", {}).get("leaked", False))
        # Memory-port denial is also the host OS baseline; don't claim an
        # independent Seatbelt-specific positive control for that narrower path.

    def test_allow_all_sandbox_cannot_replace_existing_policy(self):
        from automation_security_probes import reinstall_probe

        result = json.loads(reinstall_probe()["stdout"])
        self.assertEqual(result["reinstall_rc"], -1)
        self.assertFalse(result["leaked"])

    def test_owned_external_process_cannot_be_signaled(self):
        from automation_security_probes import signal_probe

        result = signal_probe()
        self.assertTrue(result["control_signal_received"])
        self.assertTrue(json.loads(result["sandboxed"]["stdout"])["signal_denied"])


class SandboxAvailabilityTests(unittest.TestCase):
    def test_unsupported_platform_fails_closed_before_any_subprocess(self) -> None:
        with (
            patch("automation_sandbox.platform.system", return_value="Linux"),
            patch("automation_sandbox.subprocess.Popen") as launch,
        ):
            with self.assertRaises(SandboxUnavailable):
                run_python(Path("/nonexistent"))
            launch.assert_not_called()

    @unittest.skipUnless(platform.system() == "Darwin", "actual macOS executor")
    def test_broken_preflight_never_runs_candidate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="python-automation-test-") as temp:
            root = Path(temp)
            (root / "solution.py").write_text("raise AssertionError('must not run')")
            with patch(
                "automation_sandbox._execute",
                return_value={"returncode": 1, "stdout": ""},
            ) as execute:
                with self.assertRaises(SandboxUnavailable):
                    run_python(root)
                self.assertEqual(execute.call_count, 1)


if __name__ == "__main__":
    unittest.main()
