"""Released comparison cannot silently rank mixed, partial or unsupported evidence."""

import hashlib
import json
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_agent_leaderboard import TRACKS, render_campaign, source_path


class AgentLeaderboardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cfg_path = "configs/fixture.yaml"
        self.commit = "d" * 40
        self.runner = "c" * 12
        self.supervision = "e" * 32
        self.start = datetime(2026, 10, 29, 21, tzinfo=UTC).timestamp()
        self.cfg = yaml.safe_dump(
            {
                "model": "fixture-model",
                "inference_engine": "mei",
                "standin_partition": "heldout",
                "python_automation": True,
            }
        ).encode()
        self.selection = {
            "model": "fixture-model",
            "engine": "mei",
            "config": self.cfg_path,
            "household_run": "20261029T210000Z-11111111",
            "python_run": "20261029T210100Z-22222222",
            "supervision": "artifacts/supervision",
        }
        self.campaign = {
            "benchmark_release": "benchmark-v7",
            "release_commit": self.commit,
            "partition": "heldout",
            "trials": 1,
            "models": [self.selection],
        }
        self.paths = {}
        self.logs = {}
        self.rows = {}
        self.manifests = {}
        for track, (folder, scope, ids, names) in TRACKS.items():
            rid = self.selection[track + "_run"]
            directory = self.root / "results" / folder / "runs" / rid
            directory.mkdir(parents=True)
            manifest = {
                "run_id": rid,
                "benchmark_scope": scope,
                "model": "fixture-model",
                "inference_engine": "mei",
                "partition": "heldout",
                "test_only": False,
                "config_hash": hashlib.sha256(self.cfg).hexdigest()[:12],
                "runner_git_sha": self.runner,
                "versions": {
                    name: hashlib.sha256(
                        self.reader(self.commit, source_path(name))
                    ).hexdigest()
                    for name in names
                },
                "generation_profile": "native",
                "runtime_identity": {"source": "verified fixture"},
                "cache_policy": "fresh",
                "planned": [{"task_id": tid, "trial": 1} for tid in ids],
                "rows_completed": len(ids),
                "status": "completed",
                "supervision_id": self.supervision,
                "started_at": self.start + (5 if track == "household" else 65),
                "finished_at": self.start + (25 if track == "household" else 85),
            }
            if track == "python":
                manifest["isolation"] = {"policy": "verified fixture"}
            rows = []
            for tid in ids:
                artifact = directory / (tid + "-trial1.json")
                relative = str(artifact.relative_to(self.root))
                row = {
                    k: manifest[k]
                    for k in (
                        "run_id",
                        "benchmark_scope",
                        "model",
                        "inference_engine",
                        "partition",
                        "config_hash",
                        "runner_git_sha",
                        "versions",
                        "generation_profile",
                        "runtime_identity",
                        "cache_policy",
                        "supervision_id",
                    )
                }
                if track == "python":
                    row["isolation"] = manifest["isolation"]
                row.update(
                    task_id=tid,
                    trial=1,
                    wall_seconds=1.0,
                    error=None,
                    failure_class=None,
                    invalid_tool_calls=0,
                    failed_checks=[],
                    result_path=relative,
                    **{"pass": True},
                )
                if track == "household":
                    row.update(
                        critical_safety_failure=False,
                        unsafe_attempts=0,
                        unauthorized_mutations=0,
                    )
                grade = {"pass": True, "failed_checks": [], "invalid_tool_calls": 0}
                if track == "household":
                    grade.update(
                        critical_safety_failure=False,
                        unsafe_attempts=0,
                        unauthorized_mutations=0,
                    )
                artifact.write_text(
                    json.dumps(
                        {
                            "grade": grade,
                            "error": None,
                            "failure_class": None,
                            "wall_seconds": 1.0,
                        }
                    )
                )
                rows.append(row)
            (directory / "config.yaml").write_bytes(self.cfg)
            self.paths[track] = directory
            self.rows[track] = rows
            self.manifests[track] = manifest
            self.logs[track] = self.root / "results" / folder / "log.jsonl"
            self.save(track)
        monitor = self.root / "artifacts/supervision"
        monitor.mkdir(parents=True)
        (monitor / "config.yaml").write_bytes(self.cfg)
        (monitor / "invocation.json").write_text(
            json.dumps(
                {
                    "argv": ["runner/run_bench.py", "--config", self.cfg_path],
                    "supervision_id": self.supervision,
                    "config_sha256": hashlib.sha256(self.cfg).hexdigest(),
                    "supervisor_git_sha": self.runner,
                    "supervisor_versions": {
                        name: hashlib.sha256(
                            self.reader(self.commit, "runner/" + name)
                        ).hexdigest()
                        for name in (
                            "supervise_bench.py",
                            "owned_process.py",
                            "bench_common.py",
                            "run_standin_suite.py",
                        )
                    },
                    "initial": {
                        "time": "2026-10-29T21:00:00+00:00",
                        "swap_used_mib": 0.0,
                    },
                }
            )
        )
        (monitor / "outcome.json").write_text(
            json.dumps(
                {
                    "time": "2026-10-29T21:02:00+00:00",
                    "returncode": 0,
                    "stop_reason": None,
                    "supervision_id": self.supervision,
                    "run_ids": {
                        scope: [self.selection[track + "_run"]]
                        for track, (_, scope, _, _) in TRACKS.items()
                    },
                }
            )
        )
        (monitor / "resources.jsonl").write_text(
            json.dumps(
                {"free_percent": 20, "kernel_pressure_level": 1, "swap_used_mib": 0.0}
            )
            + "\n"
        )

    def reader(self, commit, path):
        return self.cfg if path == self.cfg_path else ("method:" + path).encode()

    def save(self, track):
        (self.paths[track] / "manifest.json").write_text(
            json.dumps(self.manifests[track])
        )
        self.logs[track].write_text(
            "".join(json.dumps(r) + "\n" for r in self.rows[track])
        )

    def report(self, reader=None):
        return render_campaign(self.root, self.campaign, reader or self.reader)

    def test_complete_matching_runs_are_compared(self):
        text = self.report()
        self.assertIn("12/12", text)
        self.assertIn("3/3", text)
        self.assertIn("| 1 | fixture-model", text)

    def test_partial_household_cannot_receive_order(self):
        self.rows["household"].pop()
        self.manifests["household"]["rows_completed"] -= 1
        self.manifests["household"]["status"] = "interrupted"
        self.save("household")
        text = self.report()
        self.assertIn("partial/unusable", text)
        self.assertNotIn("| 1 |", text)

    def test_method_change_is_rejected_even_when_row_and_manifest_agree(self):
        name = next(iter(self.manifests["python"]["versions"]))
        self.manifests["python"]["versions"][name] = "0" * 64
        for row in self.rows["python"]:
            row["versions"] = self.manifests["python"]["versions"]
        self.save("python")
        with self.assertRaisesRegex(ValueError, "method differs"):
            self.report()

    def test_missing_helper_fingerprint_is_rejected(self):
        self.manifests["python"]["versions"].pop("owned_process.py")
        self.save("python")
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            self.report()

    def test_config_and_model_identity_must_match_release(self):
        (self.paths["python"] / "config.yaml").write_bytes(self.cfg + b"\n")
        with self.assertRaisesRegex(ValueError, "released config"):
            self.report()

    def test_parent_lifecycle_change_is_rejected(self):
        def changed(commit, path):
            return (
                b"changed parent"
                if commit == self.runner and path == "runner/run_bench.py"
                else self.reader(commit, path)
            )

        with self.assertRaisesRegex(ValueError, "parent lifecycle"):
            self.report(changed)

    def test_uncommitted_runner_source_cannot_rank(self):
        self.manifests["python"]["runner_git_sha"] = self.runner + "+dirty"
        for row in self.rows["python"]:
            row["runner_git_sha"] = self.manifests["python"]["runner_git_sha"]
        self.save("python")
        with self.assertRaisesRegex(ValueError, "clean committed"):
            self.report()

    def test_raw_pass_requires_matching_task_artifact(self):
        path = self.root / self.rows["python"][0]["result_path"]
        data = json.loads(path.read_text())
        data["grade"]["pass"] = False
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "artifact outcome"):
            self.report()

    def test_resource_log_cannot_be_borrowed_from_other_config(self):
        path = self.root / "artifacts/supervision/invocation.json"
        data = json.loads(path.read_text())
        data["argv"][-1] = "configs/other.yaml"
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "different config"):
            self.report()

    def test_python_runtime_identity_mismatch_is_rejected(self):
        self.rows["python"][0]["isolation"] = {"policy": "different"}
        self.save("python")
        with self.assertRaisesRegex(ValueError, "isolation provenance"):
            self.report()

    def test_pending_entries_cannot_rank(self):
        self.selection.update(household_run=None, python_run=None, supervision=None)
        text = self.report()
        self.assertIn("pending", text)
        self.assertNotIn("| 1 |", text)

    def test_monitor_from_another_attempt_of_same_config_is_rejected(self):
        for filename in ("invocation.json", "outcome.json"):
            path = self.root / "artifacts/supervision" / filename
            data = json.loads(path.read_text())
            data["supervision_id"] = "f" * 32
            path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "supervision identity"):
            self.report()

    def test_registered_run_ids_must_match_exact_selections(self):
        path = self.root / "artifacts/supervision/outcome.json"
        data = json.loads(path.read_text())
        data["run_ids"]["python-automation-v1"] = ["20261029T210100Z-33333333"]
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "registered different runs"):
            self.report()

    def test_supervisor_config_hash_and_method_are_pinned(self):
        path = self.root / "artifacts/supervision/invocation.json"
        original = json.loads(path.read_text())
        data = json.loads(json.dumps(original))
        data["config_sha256"] = "0" * 64
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "config bytes/hash"):
            self.report()
        data = json.loads(json.dumps(original))
        data["supervisor_versions"]["supervise_bench.py"] = "0" * 64
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "supervisor differs"):
            self.report()

    def test_old_timestamp_monitor_cannot_cover_new_runs(self):
        for filename in ("invocation.json", "outcome.json"):
            path = self.root / "artifacts/supervision" / filename
            data = json.loads(path.read_text())
            if filename == "invocation.json":
                data["initial"]["time"] = data["initial"]["time"].replace(
                    "2026", "2000"
                )
            else:
                data["time"] = data["time"].replace("2026", "2000")
            path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "timing is outside"):
            self.report()

    def test_tracks_cannot_be_joined_across_different_serving_runtimes(self):
        self.manifests["python"]["runtime_identity"] = {"source": "different runtime"}
        for row in self.rows["python"]:
            row["runtime_identity"] = self.manifests["python"]["runtime_identity"]
        self.save("python")
        with self.assertRaisesRegex(ValueError, "different serving runtime"):
            self.report()

    def test_grade_safety_and_invalid_counters_must_match_artifacts(self):
        for track, key, value in [
            ("household", "critical_safety_failure", True),
            ("python", "invalid_tool_calls", 1),
        ]:
            with self.subTest(track=track, key=key):
                path = self.root / self.rows[track][0]["result_path"]
                data = json.loads(path.read_text())
                old = data["grade"][key]
                data["grade"][key] = value
                path.write_text(json.dumps(data))
                with self.assertRaisesRegex(ValueError, "grade counter mismatch"):
                    self.report()
                data["grade"][key] = old
                path.write_text(json.dumps(data))

    def test_critical_boundary_failure_and_pressure_warning_cannot_rank(self):
        self.rows["household"][0]["critical_safety_failure"] = True
        path = self.root / self.rows["household"][0]["result_path"]
        data = json.loads(path.read_text())
        data["grade"]["critical_safety_failure"] = True
        path.write_text(json.dumps(data))
        self.save("household")
        self.assertIn("critical boundary failure; unranked", self.report())
        self.rows["household"][0]["critical_safety_failure"] = False
        data["grade"]["critical_safety_failure"] = False
        path.write_text(json.dumps(data))
        self.save("household")
        (self.root / "artifacts/supervision/resources.jsonl").write_text(
            json.dumps(
                {"free_percent": 20, "kernel_pressure_level": 2, "swap_used_mib": 0.0}
            )
            + "\n"
        )
        self.assertNotIn("| 1 |", self.report())


if __name__ == "__main__":
    unittest.main()
