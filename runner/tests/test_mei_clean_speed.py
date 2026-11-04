"""A final-speed launch uses committed bytes and an explicit clean environment."""

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mei_clean_speed import (
    AUDITED_LAUNCHER_SHA256,
    AUDITED_MEI_REVISION,
    AUDITED_REVISION_PAIRS,
    AUDITED_VMLX_REVISION,
    FIXED_PATH,
    MODE,
    PROFILE_KEYS,
    SOURCE_FILES,
    STOPPER,
    clean_environment,
    launch_receipt,
    verify_receipt,
)
from owned_process import OwnedSession


class CleanSpeedLaunchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        repo = Path(__file__).resolve().parents[2]
        launcher = self.root / "runner/start_mei_server.sh"
        launcher.parent.mkdir()
        shutil.copyfile(repo / "runner/start_mei_server.sh", launcher)
        shutil.copyfile(repo / STOPPER, self.root / STOPPER)
        self.assertEqual(
            hashlib.sha256(launcher.read_bytes()).hexdigest(), AUDITED_LAUNCHER_SHA256
        )
        for name in SOURCE_FILES:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((repo / name).read_bytes())
        subprocess.run(["git", "-C", str(self.root), "init", "-q"], check=True)
        subprocess.run(
            ["git", "-C", str(self.root), "add", "runner", "pyproject.toml", "uv.lock"],
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(self.root),
                "-c",
                "user.name=Fixture",
                "-c",
                "user.email=fixture@example.invalid",
                "commit",
                "-qm",
                "fixture",
            ],
            check=True,
        )
        revision = subprocess.check_output(
            ["git", "-C", str(self.root), "rev-parse", "HEAD"], text=True
        ).strip()
        self.invocation = {"runner_git_sha": revision}
        settings = {
            key: "/tmp/fixture-runtime" if key == "MEI_RUNTIME_BASE" else "0"
            for key in PROFILE_KEYS
        }
        self.cfg: dict[str, Any] = {
            "mei_source_commit": AUDITED_MEI_REVISION,
            "vmlx_commit": AUDITED_VMLX_REVISION,
            "required_runner_environment": settings,
            "mei_clean_speed_launch": {
                "mode": MODE,
                "launcher_sha256": AUDITED_LAUNCHER_SHA256,
                "environment": {
                    "HOME": "/tmp/fixture-home",
                    "PATH": FIXED_PATH,
                    **settings,
                },
            },
        }
        self.command = ["bash", "runner/start_mei_server.sh", "--model-dir", "/fixture"]

    def prepare(self, verify_worktree=True):
        return launch_receipt(
            self.root,
            self.cfg,
            self.command,
            self.invocation,
            verify_worktree=verify_worktree,
        )

    def test_dirty_launcher_cannot_change_the_executed_git_bytes(self):
        expected, receipt = self.prepare()
        (self.root / "runner/start_mei_server.sh").write_text("echo dirty\n")
        payload, after = self.prepare()
        self.assertEqual(payload, expected)
        self.assertEqual(receipt, after)
        self.assertEqual(
            receipt["actual_command"],
            ["/bin/bash", "-s", "--", "--model-dir", "/fixture"],
        )

    def test_dirty_runner_source_and_wrong_launcher_pin_fail_before_launch(self):
        (self.root / SOURCE_FILES[0]).write_text("dirty\n")
        with self.assertRaisesRegex(ValueError, "runner source differs"):
            self.prepare()
        self.cfg["mei_clean_speed_launch"]["launcher_sha256"] = "a" * 64
        with self.assertRaisesRegex(ValueError, "launcher SHA256"):
            self.prepare()

    def test_receipt_and_executed_bytes_are_both_verified(self):
        payload, receipt = self.prepare()
        copied = self.root / "executed.sh"
        copied.write_bytes(payload)
        stopper = self.root / "stopper-executed.sh"
        stopper.write_bytes((self.root / STOPPER).read_bytes())
        verify_receipt(
            self.root, self.cfg, self.command, self.invocation, receipt, copied, stopper
        )
        changed = copy.deepcopy(receipt)
        changed["environment"]["PATH"] = "/tmp/injected"
        with self.assertRaisesRegex(ValueError, "receipt"):
            verify_receipt(
                self.root,
                self.cfg,
                self.command,
                self.invocation,
                changed,
                copied,
                stopper,
            )
        copied.write_bytes(payload + b"\n")
        with self.assertRaisesRegex(ValueError, "receipt"):
            verify_receipt(
                self.root,
                self.cfg,
                self.command,
                self.invocation,
                receipt,
                copied,
                stopper,
            )
        copied.write_bytes(payload)
        stopper.write_bytes(b"modified stop script")
        with self.assertRaisesRegex(ValueError, "receipt"):
            verify_receipt(
                self.root,
                self.cfg,
                self.command,
                self.invocation,
                receipt,
                copied,
                stopper,
            )
        stopper.unlink()
        with self.assertRaises(OSError):
            verify_receipt(
                self.root,
                self.cfg,
                self.command,
                self.invocation,
                receipt,
                copied,
                stopper,
            )

    def test_inherited_functions_and_presence_sensitive_flags_never_reach_child(self):
        marker = self.root / "startup-ran"
        startup = self.root / "startup.sh"
        startup.write_text(f"/usr/bin/touch '{marker}'\n")
        for value in ("1", "0", ""):
            with (
                self.subTest(value=value),
                patch.dict(
                    os.environ,
                    {
                        "BASH_ENV": str(startup),
                        "BASH_FUNC_echo%%": f"() {{ /usr/bin/touch '{marker}'; }}",
                        "VMLX_CACHE_FETCH_TRACE": value,
                        "VMLX_SSM_STORE_TRACE": value,
                        "OPENAI_API_KEY": "fixture-secret",
                    },
                ),
            ):
                env = clean_environment(self.cfg)
                completed = subprocess.run(
                    ["/bin/bash", "-s", "--"],
                    input=b"/usr/bin/env\n",
                    env=env,
                    capture_output=True,
                    check=True,
                )
                for name in (
                    b"BASH_ENV=",
                    b"BASH_FUNC_",
                    b"VMLX_CACHE_FETCH_TRACE=",
                    b"VMLX_SSM_STORE_TRACE=",
                    b"OPENAI_API_KEY=",
                    b"fixture-secret",
                ):
                    self.assertNotIn(name, completed.stdout)
                self.assertFalse(marker.exists())

    def test_conflicting_or_secret_environment_declarations_fail_closed(self):
        for name, value in (
            ("VMLX_CACHE_FETCH_TRACE", "0"),
            ("VMLX_SSM_STORE_TRACE", ""),
            ("BASH_ENV", "/tmp/x"),
            ("BASH_FUNC_echo%%", "malicious"),
            ("OPENAI_API_KEY", "fixture-secret"),
        ):
            with self.subTest(name=name):
                cfg = copy.deepcopy(self.cfg)
                cfg["mei_clean_speed_launch"]["environment"][name] = value
                with self.assertRaises(ValueError) as error:
                    clean_environment(cfg)
                self.assertNotIn(
                    value if name == "OPENAI_API_KEY" else "fixture-secret",
                    str(error.exception),
                )
        cfg = copy.deepcopy(self.cfg)
        cfg["required_runner_environment"]["VMLX_CACHE_FETCH_TRACE"] = "0"
        with self.assertRaisesRegex(ValueError, "match declared"):
            clean_environment(cfg)

    def test_only_audited_revision_pairs_are_accepted(self):
        old, new = AUDITED_REVISION_PAIRS
        for mei, vmlx in (old, new):
            cfg = copy.deepcopy(self.cfg)
            cfg["mei_source_commit"], cfg["vmlx_commit"] = mei, vmlx
            self.assertEqual(clean_environment(cfg)["PATH"], FIXED_PATH)
        for mei, vmlx in ((old[0], new[1]), (new[0], old[1]), ([], new[1])):
            cfg = copy.deepcopy(self.cfg)
            cfg["mei_source_commit"], cfg["vmlx_commit"] = mei, vmlx
            with self.assertRaisesRegex(ValueError, "requires an audit"):
                clean_environment(cfg)

    def test_historical_groot_clean_receipts_still_validate(self):
        from build_context_speed_cohort import load_cohort

        repo = Path(__file__).resolve().parents[2]
        evidence = (
            repo
            / "artifacts/mei-stable-qualification-20261102/groot-clean-speed-summary.json"
        )
        specification = json.loads(evidence.read_text())["specification"]
        for process in specification["profiles"][0]["processes"]:
            invocation = json.loads(
                (repo / process["output"] / "invocation.json").read_text()
            )
            try:
                found = subprocess.run(
                    [
                        "git",
                        "-C",
                        str(repo),
                        "cat-file",
                        "-e",
                        invocation["runner_git_sha"] + "^{commit}",
                    ],
                    capture_output=True,
                    check=False,
                )
            except OSError:
                self.skipTest("Git is required for historical receipt verification")
            if found.returncode:
                self.skipTest("Historical runner commit unavailable in this checkout")
        profiles, observations = load_cohort(repo, specification)
        self.assertEqual(len(profiles), 1)
        self.assertEqual(len(observations), 20)

    def test_committed_scripts_run_fake_mei_and_cleanly_stop_it(self):
        model = self.root / "model"
        model.mkdir()
        (model / "config.json").write_text("{}")
        mei_repo = self.root / "mei-repo"
        mei_repo.mkdir()
        (mei_repo / "Package.swift").touch()
        binary_dir = self.root / "bin"
        binary_dir.mkdir()
        binary = binary_dir / "mei"
        binary.write_text(
            "#!/bin/bash\ntrap '' TERM\n/usr/bin/env\nprintf 'ARGS %s\\n' \"$*\"\nwhile :; do /bin/sleep 1; done\n"
        )
        binary.chmod(0o755)
        (binary_dir / "mlx.metallib").touch()
        runtime = str(self.root / "runtime")
        self.cfg["required_runner_environment"]["MEI_RUNTIME_BASE"] = runtime
        self.cfg["mei_clean_speed_launch"]["environment"]["MEI_RUNTIME_BASE"] = runtime
        self.command += [
            "--served-model-id",
            "fixture",
            "--port",
            "0",
            "--context-cap",
            "1024",
            "--mei-repo",
            str(mei_repo),
            "--mei-binary",
            str(binary),
            "--runtime-base",
            runtime,
        ]
        self.command[3] = str(model)
        launcher, receipt = self.prepare()
        stopper = (self.root / STOPPER).read_bytes()
        (self.root / "runner/start_mei_server.sh").write_text("exit 99\n")
        (self.root / STOPPER).write_text("exit 99\n")
        marker = self.root / "injected"
        startup = self.root / "startup"
        startup.write_text(f"/usr/bin/touch '{marker}'\n")
        with patch.dict(
            os.environ,
            {
                "BASH_ENV": str(startup),
                "VMLX_CACHE_FETCH_TRACE": "0",
                "BASH_FUNC_echo%%": f"() {{ /usr/bin/touch '{marker}'; }}",
            },
        ):
            process = subprocess.Popen(
                receipt["actual_command"],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=receipt["environment"],
                start_new_session=True,
            )
            session = OwnedSession(process)
            try:
                assert process.stdin is not None
                process.stdin.write(launcher)
                process.stdin.close()
                pid_file = Path(runtime) / "server.pid"
                for _ in range(100):
                    if pid_file.exists():
                        break
                    time.sleep(0.05)
                self.assertTrue(pid_file.exists())
                log = Path(runtime) / "logs/server.log"
                for _ in range(100):
                    if log.exists() and "ARGS " in log.read_text():
                        break
                    time.sleep(0.05)
                self.assertIn("ARGS ", log.read_text())
                stopped = subprocess.run(
                    receipt["stop_command"],
                    input=stopper,
                    env=receipt["environment"],
                    capture_output=True,
                    timeout=10,
                    check=False,
                )
                self.assertEqual(stopped.returncode, 0, stopped.stderr)
                self.assertIn(b"Force-stopped", stopped.stdout)
                for _ in range(100):
                    if session.leader_exited():
                        break
                    time.sleep(0.05)
                self.assertTrue(session.leader_exited())
                self.assertFalse(pid_file.exists())
                self.assertFalse(marker.exists())
                logs = list(Path(runtime).rglob("server.log"))
                self.assertEqual(len(logs), 1)
                text = logs[0].read_text()
                self.assertIn("ARGS ", text)
                self.assertNotIn("VMLX_CACHE_FETCH_TRACE=", text)
                self.assertNotIn("BASH_FUNC_", text)
            finally:
                session.stop(grace_seconds=0)

    def test_process_group_is_cleaned_after_fixture_failure(self):
        process = subprocess.Popen(
            ["/bin/bash", "-c", "/bin/sleep 60 & echo $!; wait"],
            start_new_session=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        session = OwnedSession(process)
        with self.assertRaisesRegex(RuntimeError, "fixture failure"):
            try:
                assert process.stdout is not None
                child_pid = int(process.stdout.readline().strip())
                raise RuntimeError("fixture failure")
            finally:
                session.stop(grace_seconds=0)
                if process.stdout is not None:
                    process.stdout.close()
        self.assertIsNotNone(process.poll())
        child = subprocess.run(
            ["ps", "-p", str(child_pid), "-o", "stat="],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertTrue(
            not child.stdout.strip() or child.stdout.strip().startswith("Z")
        )


if __name__ == "__main__":
    unittest.main()
