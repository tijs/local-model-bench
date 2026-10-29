"""Keep an owned session's PID reserved until all running members are stopped."""

from __future__ import annotations

import os
import signal
import subprocess
import time


class OwnedSession:
    def __init__(self, process: subprocess.Popen):
        if (
            process.returncode is not None
            or os.getpgid(process.pid) != process.pid
            or os.getsid(process.pid) != process.pid
        ):
            raise ValueError("owned process must be an unreaped new session leader")
        self.process = process
        self.pid = process.pid

    def leader_exited(self) -> bool:
        # Popen.poll()/wait() would reap a dead leader and release its PID for
        # reuse. Keep it reserved until group cleanup has sent its last signal.
        if self.process.returncode is not None:
            raise RuntimeError("owned session leader was reaped before cleanup")
        result = subprocess.run(
            ["ps", "-p", str(self.pid), "-o", "stat="],
            capture_output=True,
            text=True,
            check=False,
        )
        status = result.stdout.strip()
        if not status:
            raise RuntimeError("owned session leader vanished before cleanup")
        return status.startswith("Z")

    def running_members(self) -> bool:
        result = subprocess.run(
            ["ps", "-axo", "pgid=,stat="], capture_output=True, text=True, check=True
        )
        return any(
            len(fields := line.split()) == 2
            and fields[0] == str(self.pid)
            and not fields[1].startswith("Z")
            for line in result.stdout.splitlines()
        )

    def stop(self) -> None:
        if self.process.returncode is not None:
            raise RuntimeError("cannot signal an already reaped owned session")
        try:
            try:
                os.killpg(self.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            deadline = time.monotonic() + 3
            while self.running_members() and time.monotonic() < deadline:
                time.sleep(0.05)
            if self.running_members():
                try:
                    os.killpg(self.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                deadline = time.monotonic() + 3
                while self.running_members() and time.monotonic() < deadline:
                    time.sleep(0.05)
                if self.running_members():
                    raise RuntimeError(
                        "owned session still has running members after SIGKILL"
                    )
        finally:
            self.process.wait(timeout=3)
