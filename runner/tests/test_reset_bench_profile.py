"""Profile preflight regression tests: only disposable HOME trees are used.

run_fixture_suite.py starts fresh chats, so no stored sessions need clearing.
Snapshot every entry's existence, bytes/link target, mode, and nanosecond mtime;
not even sessions may change. TMPDIR controls the disposable test root.

Run: .venv/bin/python -B -m unittest discover -s runner/tests \
    -p 'test_reset_bench_profile.py' -v
"""
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


RESET_SCRIPT = Path(__file__).resolve().parents[1] / "reset_bench_profile.sh"
STATE_DIRS = ("sessions", "memories", "logs", "cron")
PROFILE_PATHS = (
    ".", ".hermes", ".hermes/profiles", ".hermes/profiles/bench",
    ".hermes/profiles/bench/sessions",
)
STAMP_NS = 1_600_000_000_123_456_789


class ResetBenchProfileTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory(
            prefix="bench-profile-preflight-", dir=os.environ.get("TMPDIR"),
        )))
        self.home = self._seed_home("home with spaces")
        self.profile = self.home / ".hermes/profiles/bench"
        # Outside HOME, but still owned by this test, never a real profile.
        self.external = self.root / "external symlink target"
        for name in STATE_DIRS:
            self._sentinel(self.external / name / "keep.bin")

    def _sentinel(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"preserve exactly\x00\xff\n" + path.name.encode())
        path.chmod(0o640)
        path.parent.chmod(0o750)

    def _seed_home(self, name):
        home = self.root / name
        for profile in ("bench", "another-profile"):
            base = home / ".hermes/profiles" / profile
            for directory in STATE_DIRS:
                self._sentinel(base / directory / "nested" / "keep.bin")
            self._sentinel(base / "config.yaml")
            self._sentinel(base / "state.db")
        self._sentinel(home / "unrelated" / "keep.bin")
        return home

    def _snapshot(self):
        """Use lstat and never recurse through links, including dangling ones."""
        rows = {}

        def visit(path):
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode):
                payload = os.readlink(path)
            elif stat.S_ISREG(info.st_mode):
                payload = path.read_bytes()
            else:
                self.assertTrue(stat.S_ISDIR(info.st_mode), str(path))
                payload = None
            rows[str(path.relative_to(self.root))] = (
                info.st_mode, info.st_mtime_ns, payload,
            )
            if stat.S_ISDIR(info.st_mode):
                for child in sorted(path.iterdir()):
                    visit(child)

        visit(self.root)
        return rows

    def _assert_preflight(self, *, home=None, success=True, error=None):
        # Old timestamps make remove/recreate or touch detectable without sleeps.
        # rglob does not recurse into directory symlinks; utime must not follow.
        for path in [self.root, *self.root.rglob("*")]:
            os.utime(path, ns=(STAMP_NS, STAMP_NS), follow_symlinks=False)
        before = self._snapshot()
        result = subprocess.run(
            ["/bin/bash", str(RESET_SCRIPT)], cwd=self.root,
            env={
                "HOME": str(home if home is not None else self.home),
                "PATH": os.defpath,
                "TMPDIR": os.environ.get("TMPDIR", str(self.root)),
                "LC_ALL": "C",
            },
            capture_output=True, text=True, timeout=10,
        )
        # Includes directory entries and link targets: deletion, recreation, or
        # creation of any formerly absent path changes the manifest as well.
        self.assertEqual(self._snapshot(), before, result.stdout + result.stderr)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        if error:
            self.assertIn(error, result.stderr)
        return result

    def test_existing_profile_and_all_other_state_are_unchanged(self):
        sessions = self.profile / "sessions"
        (sessions / "external-link").symlink_to(self.external, target_is_directory=True)
        (sessions / "dangling-link").symlink_to(self.root / "missing target")
        self._assert_preflight()
        self._assert_preflight()  # Idempotence: no session deletion on later runs.

    def test_missing_state_directories_are_not_created(self):
        for index, missing in enumerate((*STATE_DIRS, "all")):
            with self.subTest(missing=missing):
                home = self._seed_home(f"absent state {index}")
                profile = home / ".hermes/profiles/bench"
                names = STATE_DIRS if missing == "all" else (missing,)
                for name in names:
                    (profile / name).rename(self.root / f"saved {index} {name}")
                self._assert_preflight(home=home)
                for name in names:
                    self.assertFalse(os.path.lexists(profile / name))

    def test_missing_profile_paths_fail_without_creating_directories(self):
        for index, relative in enumerate(PROFILE_PATHS[1:-1]):
            with self.subTest(path=relative):
                home = self._seed_home(f"absent profile {index}")
                path = home / relative
                path.rename(self.root / f"saved absent profile {index}")
                self._assert_preflight(home=home, success=False, error="not found")
                self.assertFalse(os.path.lexists(path))

    def test_symlinked_profile_components_and_sessions_are_refused(self):
        for index, relative in enumerate(PROFILE_PATHS):
            with self.subTest(path=relative):
                home = self._seed_home(f"linked home {index}")
                path = home / relative
                target = self.root / f"linked external target {index}"
                path.rename(target)
                path.symlink_to(target, target_is_directory=True)
                self._assert_preflight(home=home, success=False, error="symlinked")

    def test_dangling_profile_components_and_sessions_are_refused(self):
        for index, relative in enumerate(PROFILE_PATHS):
            with self.subTest(path=relative):
                home = self._seed_home(f"dangling home {index}")
                path = home / relative
                path.rename(self.root / f"saved dangling path {index}")
                target = self.root / f"missing external target {index}"
                path.symlink_to(target, target_is_directory=True)
                self._assert_preflight(home=home, success=False, error="symlinked")
                self.assertFalse(target.exists())

    def test_profile_link_to_another_profile_is_refused(self):
        self.profile.rename(self.root / "original bench")
        self.profile.symlink_to(
            self.home / ".hermes/profiles/another-profile", target_is_directory=True,
        )
        self._assert_preflight(success=False, error="symlinked")

    def test_protected_state_symlinks_and_targets_are_unchanged(self):
        for name in ("memories", "logs", "cron"):
            path = self.profile / name
            path.rename(self.root / f"original {name}")
            path.symlink_to(self.external / name, target_is_directory=True)
        self._assert_preflight()

    def test_non_directory_profile_is_refused_without_changes(self):
        self.profile.rename(self.root / "original bench")
        self._sentinel(self.profile)
        self._assert_preflight(success=False, error="not found")

    def test_non_directory_sessions_is_refused_without_changes(self):
        path = self.profile / "sessions"
        path.rename(self.root / "original sessions")
        self._sentinel(path)
        self._assert_preflight(success=False, error="not a directory")


if __name__ == "__main__":
    unittest.main()
