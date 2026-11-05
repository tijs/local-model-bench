import copy
import json
import shlex
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from verify_combined_cohorts import (
    compare,
    declared_profile,
    matching_speed_profile,
    model_files,
    verify_task_runtime,
)


class CombinedProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for d in ("configs", "results", "artifacts"):
            (self.root / d).mkdir()
        self.config: dict[str, Any] = {
            "model": "example/model",
            "source_revision": "abc",
            "inference_engine": "mei",
            "context_cap": 65536,
            "mei_source_commit": "mei-rev",
            "vmlx_commit": "vmlx-rev",
            "mei_release_artifact": {
                "binary_sha256": "1" * 64,
                "metallib_sha256": "2" * 64,
            },
            "benchmark_launch_command": (
                "bash runner/start_mei_server.sh --mei-binary /bin/a --mei-repo /repo "
                "--model-dir /models/example --prefill-step-size 32 --cache-limit-bytes 128 "
                "--runtime-base /a --kv-cache-dir /a/kv"
            ),
            "required_runner_environment": {
                "MEI_RUNTIME_BASE": "/a",
                "VMLX_ENABLE_UNSAFE_COMPILE": "0",
            },
        }
        self.file_hash = "a" * 64
        self.score = {"models": {"example/model": "Example"}, "cohorts": []}
        self.speed = {
            "profiles": [
                {
                    "model": "Example",
                    "model_id": "example/model",
                    "model_manifest": "artifacts/model.json",
                    "processes": [],
                }
            ]
        }
        for seed in (17, 29):
            name = f"configs/task{seed}.yaml"
            (self.root / name).write_text(yaml.safe_dump(self.config))
            out = self.root / "artifacts" / f"task{seed}"
            out.mkdir()
            (out / "config.yaml").write_bytes((self.root / name).read_bytes())
            (out / "post-run-model-hashes.json").write_text(
                json.dumps(
                    {
                        "all_match": True,
                        "files": [
                            {
                                "file": "/models/example/model.safetensors",
                                "bytes": 123,
                                "sha256": self.file_hash,
                                "matches": True,
                            }
                        ],
                    }
                )
            )
            cpath = f"results/cohort{seed}.json"
            for folder in ("standin", "automation"):
                run = self.root / f"results/{folder}/runs/run{seed}"
                run.mkdir(parents=True)
                (run / "manifest.json").write_text(
                    json.dumps(
                        {
                            "runtime_identity": {
                                "mei_source_commit": "mei-rev",
                                "vmlx_commit": "vmlx-rev",
                                "binary_sha256": "1" * 64,
                                "metallib_sha256": "2" * 64,
                            }
                        }
                    )
                )
            (self.root / cpath).write_text(
                json.dumps(
                    {
                        "models": [
                            {
                                "model": "example/model",
                                "config": name,
                                "supervision": f"artifacts/task{seed}",
                                "household_run": f"run{seed}",
                                "python_run": f"run{seed}",
                            }
                        ]
                    }
                )
            )
            self.score["cohorts"].append(cpath)
        for i in (1, 2):
            cfg = copy.deepcopy(self.config)
            cfg["benchmark_launch_command"] = (
                cfg["benchmark_launch_command"]
                .replace("/bin/a", "/bin/b")
                .replace("/repo", "/other")
                .replace("/a/kv", f"/b{i}/kv")
                .replace("/a", f"/b{i}")
            )
            cfg["required_runner_environment"]["MEI_RUNTIME_BASE"] = f"/b{i}"
            name = f"configs/speed{i}.yaml"
            (self.root / name).write_text(yaml.safe_dump(cfg))
            self.speed["profiles"][0]["processes"].append({"config": name})
        (self.root / "artifacts/model.json").write_text(
            json.dumps(
                {
                    "directory": "/models/example",
                    "all_match": True,
                    "files": [
                        {
                            "file": "model.safetensors",
                            "bytes": 123,
                            "sha256": self.file_hash,
                            "matches": True,
                        }
                    ],
                }
            )
        )
        self.score_patch = patch("verify_combined_cohorts.load_points")
        self.speed_patch = patch("verify_combined_cohorts.load_cohort")
        self.score_patch.start()
        self.speed_patch.start()
        self.addCleanup(self.score_patch.stop)
        self.addCleanup(self.speed_patch.stop)

    def test_source_equivalence_requires_identical_build_inputs_and_binary(self):
        task = copy.deepcopy(self.config)
        task["mei_source_commit"] = "a" * 40
        speed = copy.deepcopy(task)
        speed["mei_source_commit"] = "b" * 40
        left, right = declared_profile(task), declared_profile(speed)
        with patch("verify_combined_cohorts.subprocess.run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = "same-git-object\n"
            self.assertTrue(matching_speed_profile(left, right, task))
            self.assertEqual(run.call_count, 6)
            run.side_effect = [
                type("R", (), {"returncode": 0, "stdout": x})()
                for x in ("one", "different")
            ]
            self.assertFalse(matching_speed_profile(left, right, task))
        speed["mei_release_artifact"]["binary_sha256"] = "3" * 64
        self.assertFalse(matching_speed_profile(left, declared_profile(speed), task))

    def test_matching_profiles_ignore_only_owned_paths(self):
        self.assertEqual(compare(self.root, self.score, self.speed)["status"], "passed")

    def test_prefill_change_fails_even_when_both_cohorts_are_valid(self):
        p = self.root / "configs/speed2.yaml"
        cfg = yaml.safe_load(p.read_text())
        cfg["benchmark_launch_command"] = cfg["benchmark_launch_command"].replace(
            "--prefill-step-size 32", "--prefill-step-size 256"
        )
        p.write_text(yaml.safe_dump(cfg))
        with self.assertRaisesRegex(
            ValueError, "speed and task declared profiles differ"
        ):
            compare(self.root, self.score, self.speed)

    def test_changed_runtime_or_environment_fails(self):
        for key in ("binary", "environment"):
            cfg = copy.deepcopy(self.config)
            if key == "binary":
                cfg["mei_release_artifact"]["binary_sha256"] = "3" * 64
            else:
                cfg["required_runner_environment"]["VMLX_ENABLE_UNSAFE_COMPILE"] = "1"
            self.assertNotEqual(declared_profile(self.config), declared_profile(cfg))

    def test_llama_library_change_is_not_a_matching_runtime(self):
        cfg: dict[str, Any] = {
            "model": "example/gguf",
            "source_revision": "rev",
            "inference_engine": "llama.cpp",
            "context_cap": 65536,
            "benchmark_launch_command": "/one/llama-server --model /models/model.gguf --ctx-size 65536",
            "runtime": {
                "binary_sha256": "a" * 64,
                "revision": "rev",
                "shared_libraries": {"libggml.dylib": "b" * 64},
            },
        }
        changed = copy.deepcopy(cfg)
        changed["runtime"]["shared_libraries"]["libggml.dylib"] = "c" * 64
        self.assertNotEqual(declared_profile(cfg), declared_profile(changed))

    def test_model_hash_mismatch_fails(self):
        p = self.root / "artifacts/model.json"
        record = json.loads(p.read_text())
        record["files"][0]["sha256"] = "b" * 64
        p.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, "model files differ"):
            compare(self.root, self.score, self.speed)

    def test_worktree_score_config_must_match_saved_run(self):
        with (self.root / "configs/task17.yaml").open("a") as stream:
            stream.write("\n# unrecorded change\n")
        with self.assertRaisesRegex(ValueError, "differs from saved snapshot"):
            compare(self.root, self.score, self.speed)

    def test_two_tracks_agree_on_wrong_runtime_but_still_fail(self):
        for folder in ("standin", "automation"):
            path = self.root / f"results/{folder}/runs/run17/manifest.json"
            manifest = json.loads(path.read_text())
            manifest["runtime_identity"]["binary_sha256"] = "b" * 64
            path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "observed task runtime differs"):
            compare(self.root, self.score, self.speed)

    def test_duplicate_file_and_ambiguous_launch_fail_closed(self):
        row = {"file": "a", "bytes": 1, "sha256": self.file_hash, "matches": True}
        with self.assertRaisesRegex(ValueError, "duplicate"):
            model_files(
                {"directory": "/models", "all_match": True, "files": [row, row]}
            )
        cfg = copy.deepcopy(self.config)
        cfg["benchmark_launch_command"] += " --mei-binary /another"
        with self.assertRaises(ValueError):
            declared_profile(cfg)


class RecordedCohortTests(unittest.TestCase):
    def test_recorded_logics_profile_and_model_match(self):
        root = Path(__file__).resolve().parents[2]
        task = yaml.safe_load(
            (root / "configs/four-model-v9p10-20261102/logics-seed17.yaml").read_text()
        )
        speed = yaml.safe_load(
            (
                root / "configs/mei-stable-qualification-20261102/logics-context-1.yaml"
            ).read_text()
        )
        for path in (
            "results/standin/runs/20261102T083631Z-2af535d3/manifest.json",
            "results/automation/runs/20261102T084527Z-61f2e985/manifest.json",
        ):
            verify_task_runtime(task, json.loads((root / path).read_text()))
        self.assertEqual(declared_profile(task), declared_profile(speed))
        record = json.loads(
            (
                root
                / "artifacts/logics-four-v9p10-seed17-20261102/post-run-model-hashes.json"
            ).read_text()
        )
        command = shlex.split(task["benchmark_launch_command"])
        directory = str(Path(command[command.index("--model") + 1]).parent)
        self.assertEqual(
            model_files(record, directory=directory),
            ((speed["model_file"], speed["model_bytes"], speed["model_sha256"]),),
        )

    def test_recorded_groot_new_candidate_is_not_old_score_runtime(self):
        root = Path(__file__).resolve().parents[2]
        task = yaml.safe_load(
            (root / "configs/four-model-v9p10-20261102/groot-seed17.yaml").read_text()
        )
        speed = yaml.safe_load(
            (
                root
                / "configs/mei-stable-qualification-20261102/groot-clean-speed-1.yaml"
            ).read_text()
        )
        for path in (
            "results/standin/runs/20261102T082458Z-4e770190/manifest.json",
            "results/automation/runs/20261102T083056Z-ffb408f6/manifest.json",
        ):
            verify_task_runtime(task, json.loads((root / path).read_text()))
        self.assertNotEqual(declared_profile(task), declared_profile(speed))
        record = json.loads(
            (
                root
                / "artifacts/groot-four-v9p10-seed17-20261102/post-run-model-hashes.json"
            ).read_text()
        )
        baseline = json.loads(
            (
                root
                / "artifacts/mei-stable-qualification-20261102/groot-pre-run-model-hashes.json"
            ).read_text()
        )
        command = shlex.split(task["benchmark_launch_command"])
        self.assertEqual(
            model_files(record, directory=command[command.index("--model-dir") + 1]),
            model_files(baseline),
        )


if __name__ == "__main__":
    unittest.main()
