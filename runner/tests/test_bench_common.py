"""Regression tests for runner/bench_common.py.

Run: uv run --locked python -m unittest discover -s runner/tests -v
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bench_common


class GitShaDirtyCheckPathsTests(unittest.TestCase):
    """CR3-11: git_sha()'s dirty-check porcelain path list never included
    configs/, so an uncommitted edit to a config's SIBLING file (e.g.
    configs/Qwen3.8-27B/chat_template.jinja, which is copied straight
    into the live HF cache on every MLX launch) was completely invisible
    in runner_git_sha."""

    def test_configs_dir_is_in_the_dirty_check_path_list(self):
        captured = {}

        def fake_run(cmd, **kwargs):
            if cmd[:2] == ["git", "status"]:
                captured["paths"] = cmd[cmd.index("--") + 1:]
            result = unittest.mock.Mock()
            result.stdout = ""
            result.returncode = 0
            return result

        with patch("bench_common.subprocess.run", side_effect=fake_run):
            bench_common.git_sha()

        self.assertIn("configs/", captured["paths"])
        # Regression guard: this addition must not have dropped any of
        # the paths M-10 already established (fixtures/) or the original
        # set (runner/, tasks/, checks/).
        for expected in ("runner/", "tasks/", "checks/", "fixtures/", "configs/"):
            self.assertIn(expected, captured["paths"])


class SnapshotConfigTests(unittest.TestCase):
    def test_writes_snapshot_and_returns_stable_hash(self):
        tmp = tempfile.mkdtemp()
        try:
            # .resolve() matters here: macOS's /var is a symlink to
            # /private/var, and snapshot_config() resolves its input path
            # before computing relative_to(REPO) — without also resolving
            # REPO the same way, the two would disagree on a symlinked tmpdir.
            repo = Path(tmp).resolve()
            config_path = repo / "configs" / "Fake" / "gguf.yaml"
            config_path.parent.mkdir(parents=True)
            config_path.write_text("model: fake\n")
            with patch.object(bench_common, "REPO", repo):
                h1, rel1 = bench_common.snapshot_config(config_path)
                h2, rel2 = bench_common.snapshot_config(config_path)
            self.assertEqual(h1, h2)
            self.assertTrue((repo / "results" / "configs" / f"{h1}.yaml").exists())
            self.assertEqual(rel1, rel2)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
