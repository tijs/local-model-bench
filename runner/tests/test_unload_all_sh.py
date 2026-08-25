"""Tests for runner/unload_all.sh's port-derived process termination
(M4 of the 2026-08-24 improvement plan).

The script used to end with `pkill -9 -f "llama-server"` and a
`pgrep -f "...|vllm-mlx|..."` sweep — command-line substring matches
across the whole machine, which can terminate an unrelated checkout's
server (or any process whose argv happens to contain the string). It now
resolves the PIDs actually listening on this benchmark's configured ports
and stops exactly those, after checking the command line looks like a
known backend.

These drive the real script, and never kill anything: the destructive
paths are exercised only against a listener this test started itself.

Run: uv run --locked python -m unittest discover -s runner/tests -v
"""
import os
import re
import socket
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml

import run_fixture_suite as rfs

REPO = rfs.REPO
UNLOAD_ALL_SH = REPO / "runner" / "unload_all.sh"


def _list_ports():
    out = subprocess.run(
        ["bash", str(UNLOAD_ALL_SH), "--list-ports"],
        capture_output=True, text=True, check=True, cwd=str(REPO),
    ).stdout
    return {int(line) for line in out.split()}


class PortDiscoveryTests(unittest.TestCase):
    def test_lists_the_well_known_defaults(self):
        ports = _list_ports()
        for expected in (8012, 8015, 8020):  # vllm-mlx, bench proxy, oMLX
            self.assertIn(expected, ports)

    def test_lists_every_port_declared_by_a_real_config(self):
        declared = set()
        for config in sorted(REPO.glob("configs/*/*.yaml")):
            try:
                cfg = yaml.safe_load(config.read_text())
            except yaml.YAMLError:
                continue
            orch = (cfg or {}).get("orchestration") or {}
            for key in ("raw_port", "proxy_port"):
                if isinstance(orch.get(key), int):
                    declared.add(orch[key])
        self.assertTrue(declared, "no config declares a port — test is not proving anything")
        self.assertLessEqual(declared, _list_ports())

    def test_listing_ports_is_non_destructive(self):
        # --list-ports must return before any kill/launchctl/cocore call.
        text = UNLOAD_ALL_SH.read_text()
        listing_block = text.split('--list-ports', 1)[1].split("exit 0", 1)[0]
        for destructive in ("kill", "pkill", "launchctl", "cocore"):
            self.assertNotIn(destructive, listing_block)


def _code_lines(text):
    """Executable lines only — the file's prose explains WHY pkill was
    dropped, so a naive substring check would match its own commentary."""
    return "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )


class NoBroadPatternKillByDefaultTests(unittest.TestCase):
    def test_unconditional_pkill_is_gone(self):
        code = _code_lines(UNLOAD_ALL_SH.read_text())
        # Only the opt-in BENCH_UNLOAD_FORCE branch may sweep by pattern.
        outside_force, force_branch = code.split('BENCH_UNLOAD_FORCE:-0', 1)
        self.assertNotIn("pkill", outside_force)
        self.assertNotIn("pgrep", outside_force)
        self.assertIn("pgrep", force_branch)
        self.assertNotIn("pkill", force_branch)

    def test_kills_are_gated_on_a_backend_command_pattern(self):
        text = UNLOAD_ALL_SH.read_text()
        self.assertIn("BACKEND_CMD_PATTERN", text)
        self.assertIn("is not a known benchmark backend, leaving it alone", text)


class StopPortBehaviourTests(unittest.TestCase):
    """Drives the script's own stop_port() against a listener this test
    starts, so the decision logic is exercised for real."""

    def setUp(self):
        # A listener on an ephemeral port whose command line does NOT
        # look like a benchmark backend.
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(1)
        self.port = self.sock.getsockname()[1]
        self.proc = subprocess.Popen(
            [sys.executable, "-c",
             "import socket,sys,time\n"
             "s=socket.socket(); s.bind(('127.0.0.1', 0)); s.listen(1)\n"
             "print(s.getsockname()[1], flush=True)\n"
             "time.sleep(120)\n"],
            stdout=subprocess.PIPE, text=True,
        )
        self.listener_port = int(self.proc.stdout.readline().strip())

    def tearDown(self):
        self.sock.close()
        self.proc.kill()
        self.proc.wait()
        self.proc.stdout.close()

    def _run_stop_port(self, port):
        return subprocess.run(
            ["bash", "-c", f'source "{UNLOAD_ALL_SH}"; stop_port {port}'],
            capture_output=True, text=True, cwd=str(REPO),
            env={**os.environ, "BENCH_UNLOAD_DEFINE_ONLY": "1"},
        )

    def test_an_unrelated_listener_is_left_alone(self):
        # The exact hazard M4 names: something else is on the port, and
        # the script must refuse to kill it rather than pattern-matching
        # its way into someone else's process.
        result = self._run_stop_port(self.listener_port)
        self.assertIn("not a known benchmark backend", result.stdout, result.stderr)
        self.assertIsNone(self.proc.poll(), "an unrelated listener must survive")

    def test_a_free_port_is_a_no_op(self):
        self.sock.close()
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            free_port = probe.getsockname()[1]
        result = self._run_stop_port(free_port)
        self.assertEqual(result.stdout.strip(), "")
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
