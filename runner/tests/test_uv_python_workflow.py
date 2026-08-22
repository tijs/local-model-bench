"""Regression tests for the repository's uv-only benchmark Python workflow."""
import sys
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import run_bench


REPO = Path(__file__).resolve().parents[2]


class UvPythonWorkflowTests(unittest.TestCase):
    def test_mlx_serving_dependencies_are_unconditional_project_dependencies(self):
        project = tomllib.loads((REPO / "pyproject.toml").read_text())
        dependencies = set(project["project"]["dependencies"])

        self.assertTrue(
            {
                "vllm-mlx==0.4.1",
                "mlx==0.32.0",
                "mlx-lm==0.31.3",
            }.issubset(dependencies)
        )
        self.assertNotIn(
            "mlx", project["project"].get("optional-dependencies", {})
        )

    def test_canonical_setup_and_legacy_requirements_mirror_are_documented(self):
        readme = (REPO / "README.md").read_text()
        requirements = (REPO / "runner" / "requirements.txt").read_text()

        self.assertIn(
            "Run `uv sync --locked` to install all project dependencies", readme
        )
        self.assertIn("Legacy dependency mirror", requirements.splitlines()[0])

    def test_active_sources_do_not_require_an_mlx_extra(self):
        forbidden = "--extra " + "mlx"
        paths = [REPO / "README.md", REPO / "AGENTS.md", REPO / "configs" / "README.md"]
        paths.extend(REPO.glob("docs/**/*.md"))
        paths.extend(REPO.glob("configs/**/*.yaml"))
        paths.extend(REPO.glob("runner/**/*.py"))
        paths.extend(REPO.glob("runner/**/*.sh"))

        offenders = [
            str(path.relative_to(REPO))
            for path in paths
            if forbidden in path.read_text()
        ]
        self.assertEqual(offenders, [])

    def test_active_sources_do_not_expose_legacy_python_overrides(self):
        forbidden = (
            "BENCH_" + "PYTHON",
            "BENCH_" + "VLLM_COMMAND",
            "RUNNER_" + "PYTHON",
        )
        paths = [REPO / "README.md", REPO / "AGENTS.md", REPO / "configs" / "README.md"]
        paths.extend(REPO.glob("docs/**/*.md"))
        paths.extend(REPO.glob("configs/**/*.yaml"))
        paths.extend(REPO.glob("runner/**/*.py"))
        paths.extend(REPO.glob("runner/**/*.sh"))

        offenders = []
        for path in paths:
            text = path.read_text()
            for name in forbidden:
                if name in text:
                    offenders.append(f"{path.relative_to(REPO)}: {name}")
        self.assertEqual(offenders, [])

    def test_vllm_mlx_configs_launch_through_single_locked_uv_environment(self):
        configs = []
        for path in sorted(REPO.glob("configs/*/*.yaml")):
            config = yaml.safe_load(path.read_text()) or {}
            if config.get("framework") == "vllm-mlx":
                configs.append((path, config["benchmark_launch_command"]))

        self.assertTrue(configs)
        for path, command in configs:
            with self.subTest(config=path.relative_to(REPO)):
                expected = (
                    "uv run --locked vllm-mlx serve"
                    if path.parent.name == "Laguna-XS-2.1"
                    else "uv run --locked python -m vllm_mlx.server"
                )
                self.assertIn(expected, command)
                self.assertNotIn("--extra " + "mlx", command)
                for line in command.splitlines():
                    if "python runner/" in line:
                        self.assertIn("uv run --locked python runner/", line)

    def test_proxy_script_always_uses_project_locked_uv_python(self):
        script = (REPO / "runner" / "start_bench_proxy.sh").read_text()
        self.assertIn(
            'PYTHON_CMD=(uv run --project "${REPO_DIR}" --locked python)', script
        )

    def test_leaderboard_subprocess_uses_current_interpreter(self):
        with patch.object(run_bench, "run") as run:
            run_bench._leaderboard()
        self.assertEqual(
            run.call_args.args[0],
            [sys.executable, str(REPO / "runner" / "build_leaderboard.py")],
        )


if __name__ == "__main__":
    unittest.main()
