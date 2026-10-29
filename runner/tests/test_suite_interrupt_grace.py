"""Parent cancellation must let the suite persist its interrupted evidence."""

import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_bench


class SuiteInterruptGraceTests(unittest.TestCase):
    def test_interrupt_waits_for_child_finalization_instead_of_immediate_kill(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "saved.json"
            code = (
                "import signal,time,sys\ndef stop(*a):\n time.sleep(.05)\n open("
                + repr(str(marker))
                + ',"w").write("interrupted evidence saved")\n sys.exit(130)\nsignal.signal(signal.SIGTERM,stop)\nprint("READY",flush=True)\ntime.sleep(30)\n'
            )
            actual = subprocess.Popen(
                [sys.executable, "-I", "-S", "-c", code],
                stdout=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(actual.stdout.readline().strip(), "READY")
            killed = []

            class Child:
                first = True

                def wait(self, timeout=None):
                    if self.first:
                        self.first = False
                        actual.send_signal(signal.SIGTERM)
                        raise KeyboardInterrupt
                    return actual.wait(timeout=timeout)

                def terminate(self):
                    actual.terminate()

                def kill(self):
                    killed.append(True)
                    actual.kill()

            try:
                with (
                    patch.object(run_bench.subprocess, "Popen", return_value=Child()),
                    self.assertRaises(KeyboardInterrupt),
                ):
                    run_bench.run(["owned-suite"], graceful_interrupt=True)
                self.assertEqual(marker.read_text(), "interrupted evidence saved")
                self.assertEqual(actual.returncode, 130)
                self.assertFalse(killed)
            finally:
                if actual.poll() is None:
                    actual.kill()
                    actual.wait(timeout=3)
                actual.stdout.close()

    def test_nonfinalizing_suite_is_escalated_and_reaped(self):
        calls = []

        class Child:
            def wait(self, timeout=None):
                calls.append(("wait", timeout))
                if timeout is None:
                    raise KeyboardInterrupt
                if len([c for c in calls if c[0] == "wait"]) < 4:
                    raise subprocess.TimeoutExpired("owned-suite", timeout)
                return -9

            def terminate(self):
                calls.append(("terminate", None))

            def kill(self):
                calls.append(("kill", None))

        with (
            patch.object(run_bench.subprocess, "Popen", return_value=Child()),
            self.assertRaises(KeyboardInterrupt),
        ):
            run_bench.run(["owned-suite"], graceful_interrupt=True)
        self.assertIn(("terminate", None), calls)
        self.assertIn(("kill", None), calls)
        self.assertEqual(calls[-1], ("wait", 3))


if __name__ == "__main__":
    unittest.main()
