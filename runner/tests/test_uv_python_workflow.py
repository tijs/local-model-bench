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
    def test_retired_mlx_serving_dependencies_are_not_project_dependencies(self):
        """The oMLX/vllm-mlx Python MLX serving stack (mlx, mlx-lm,
        vllm-mlx) was removed from the project when those lanes retired
        2026-09-04 — active engines (llama.cpp binaries, Swift Mei binary)
        don't need it. Also assert the control-plane dep that remains is
        still unconditional, not dropped into an extra."""
        project = tomllib.loads((REPO / "pyproject.toml").read_text())
        dependencies = set(project["project"]["dependencies"])

        self.assertIn("PyYAML==6.0.3", dependencies)
        self.assertTrue(
            {"mlx", "mlx-lm", "vllm-mlx"}.isdisjoint(dependencies),
            "retired MLX serving deps must not be unconditional project deps",
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

    def test_retired_engines_are_not_active_or_advertised(self):
        """After the oMLX/vllm-mlx retirement (2026-09-04), every omlx/vllm-mlx
        config must be `viable: retired` (skipped, not runnable), and NO active
        llama.cpp/Mei config's launch command may invoke the removed
        `python -m vllm_mlx.server` engine."""
        retired = []
        for path in sorted(REPO.glob("configs/*/*.yaml")):
            config = yaml.safe_load(path.read_text()) or {}
            if config.get("inference_engine") in ("vllm-mlx", "omlx"):
                viable = (config.get("orchestration") or {}).get("viable")
                retired.append((path.relative_to(REPO), viable))
        self.assertTrue(retired, "expected to find retired vllm-mlx/omlx configs")
        for _c, viable in retired:
            self.assertIn(viable, ("retired", "blocked"))

        for path in sorted(REPO.glob("configs/*/*.yaml")):
            config = yaml.safe_load(path.read_text()) or {}
            engine = config.get("inference_engine", "")
            if engine.startswith("llama.cpp") or engine == "mei":
                cmd = config.get("benchmark_launch_command", "")
                self.assertNotIn("vllm_mlx.server", cmd,
                                 f"active {engine} config must not spawn vllm-mlx")
                self.assertNotIn("vllm-mlx serve", cmd,
                                 f"active {engine} config must not spawn vllm-mlx")

    def test_proxy_script_always_uses_project_locked_uv_python(self):
        script = (REPO / "runner" / "start_bench_proxy.sh").read_text()
        self.assertIn(
            'PYTHON_CMD=(uv run --project "${REPO_DIR}" --locked python)', script
        )

    def test_leaderboard_subprocess_uses_current_interpreter(self):
        with patch.object(run_bench, "run") as run:
            run_bench._leaderboard()
        # _leaderboard() calls run() twice: build_leaderboard.py to
        # regenerate the table, then plot_leaderboard.py (2026-08-27) to
        # regenerate the chart embedded alongside it — both must use the
        # current interpreter, not a bare "python" that might not be the
        # project's uv-managed one.
        self.assertEqual(
            [c.args[0] for c in run.call_args_list],
            [
                [sys.executable, str(REPO / "runner" / "build_leaderboard.py")],
                [sys.executable, str(REPO / "runner" / "plot_leaderboard.py")],
            ],
        )


if __name__ == "__main__":
    unittest.main()
