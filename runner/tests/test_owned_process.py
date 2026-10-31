"""Owned descendant cleanup keeps the leader PID reserved against reuse."""

import os
import signal
import subprocess
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from owned_process import OwnedSession


class OwnedProcessTests(unittest.TestCase):
    def launch(self, exit_leader, ignore_child_term):
        child_code = (
            "import signal,time;"
            + (
                "signal.signal(signal.SIGTERM,signal.SIG_IGN);"
                if ignore_child_term
                else ""
            )
            + 'print("READY",flush=True);time.sleep(30)'
        )
        source = (
            'import subprocess,sys,time\np=subprocess.Popen([sys.executable,"-I","-S","-c",'
            + repr(child_code)
            + '],stdout=subprocess.PIPE,text=True)\nassert p.stdout.readline().strip()=="READY"\nprint(p.pid,flush=True)\n'
            + ("" if exit_leader else "time.sleep(30)\n")
        )
        process = subprocess.Popen(
            [sys.executable, "-I", "-S", "-c", source],
            stdout=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        session = OwnedSession(process)
        self.addCleanup(self.emergency_stop, session)
        child_pid = int(process.stdout.readline())
        return session, child_pid

    def emergency_stop(self, session):
        if session.process.returncode is None:
            try:
                os.killpg(session.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            session.process.wait(timeout=3)
        session.process.stdout.close()

    def test_exited_leader_does_not_release_owned_descendant_group(self):
        session, _ = self.launch(True, False)
        deadline = time.monotonic() + 3
        while not session.leader_exited() and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertTrue(session.leader_exited())
        self.assertIsNone(session.process.returncode)  # no premature wait/poll
        session.stop()
        self.assertFalse(session.running_members())
        self.assertIsNotNone(session.process.returncode)

    def test_descendant_ignoring_term_is_killed_after_leader_exits(self):
        session, _ = self.launch(False, True)
        session.stop()
        self.assertFalse(session.running_members())
        self.assertIsNotNone(session.process.returncode)

    def test_already_reaped_leader_is_not_signaled_as_a_reused_pid(self):
        process = subprocess.Popen(
            [sys.executable, "-I", "-S", "-c", "pass"], start_new_session=True
        )
        session = OwnedSession(process)
        process.wait(timeout=3)
        with self.assertRaisesRegex(RuntimeError, "already reaped"):
            session.stop()

    def test_exited_leader_without_descendants_is_reaped(self):
        process = subprocess.Popen(
            [sys.executable, "-I", "-S", "-c", "pass"], start_new_session=True
        )
        session = OwnedSession(process)
        deadline = time.monotonic() + 3
        while not session.leader_exited() and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertTrue(session.leader_exited())
        session.stop()
        self.assertEqual(process.returncode, 0)

    def test_permission_denied_is_not_hidden_for_live_members(self):
        session, _ = self.launch(False, False)
        with (
            patch("owned_process.os.killpg", side_effect=PermissionError),
            patch.object(session.process, "wait"),
            self.assertRaises(PermissionError),
        ):
            session.stop()


if __name__ == "__main__":
    unittest.main()
