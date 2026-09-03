import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("expert_run", ROOT / "run.py")
RUN = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = RUN
SPEC.loader.exec_module(RUN)

REPORT_SPEC = importlib.util.spec_from_file_location("expert_report", ROOT / "report.py")
REPORT = importlib.util.module_from_spec(REPORT_SPEC)
assert REPORT_SPEC.loader is not None
sys.modules[REPORT_SPEC.name] = REPORT
REPORT_SPEC.loader.exec_module(REPORT)

class HarnessTests(unittest.TestCase):
    def test_suite_version_is_v2_1(self):
        self.assertEqual(RUN.SUITE_VERSION, "v2.1")
        self.assertEqual(len(RUN.task_dirs()), 10)

    def test_v2_prompts_expose_previously_hidden_requirements(self):
        task_01 = (ROOT / "tasks" / "01_ttl_cache" / "TASK.md").read_text()
        task_02 = (ROOT / "tasks" / "02_circuit_breaker" / "TASK.md").read_text()
        task_08 = (ROOT / "tasks" / "08_inventory_cli" / "TASK.md").read_text()
        self.assertIn("booleans are not valid integers", task_01)
        self.assertIn("booleans are not valid integers", task_02)
        self.assertIn('state` must report `"half-open"` before the probe', task_02)
        self.assertIn("parent directories do not", task_08)

    def test_validation_exception_contract_accepts_type_or_value_error(self):
        for task in ("09_safe_zip", "10_retry_policy"):
            prompt = (ROOT / "tasks" / task / "TASK.md").read_text()
            grader = (ROOT / "tasks" / task / "grader.py").read_text()
            self.assertIn("`TypeError` or `ValueError`", prompt)
            self.assertIn("except (TypeError, ValueError)", grader)

    def test_opencode_command_pins_workspace(self):
        workspace = pathlib.Path("/tmp/isolated-workspace")
        command = RUN.command("corti", workspace, "prompt", "corti/corti-s1")
        self.assertEqual(command[command.index("--dir") + 1], str(workspace))
        self.assertIn("--pure", command)
        self.assertIn("--auto", command)

    def test_glm_uses_the_same_opencode_scaffold(self):
        workspace = pathlib.Path("/tmp/isolated-workspace")
        command = RUN.command("glm", workspace, "prompt", "opencode/glm-5.2")
        self.assertEqual(command[command.index("--dir") + 1], str(workspace))
        self.assertEqual(command[command.index("--model") + 1], "opencode/glm-5.2")
        self.assertIn("--pure", command)

    def test_claude_command_disables_local_customization(self):
        command = RUN.command("claude", pathlib.Path("/tmp/work"), "prompt", "claude-sonnet-5")
        self.assertIn("--safe-mode", command)
        self.assertIn("--no-session-persistence", command)

    def test_jobs_are_repeatable_and_balanced(self):
        first = RUN.build_jobs(["corti", "claude"], ["a", "b"], 2, 7)
        second = RUN.build_jobs(["corti", "claude"], ["a", "b"], 2, 7)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 8)
        self.assertEqual({job.provider for job in first}, {"corti", "claude"})

    def test_digest_changes_with_file_content(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            (root / "x.txt").write_text("one")
            before = RUN.file_digest(root)
            (root / "x.txt").write_text("two")
            self.assertNotEqual(before, RUN.file_digest(root))

    def test_digest_ignores_macos_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            (root / "x.txt").write_text("fixture")
            before = RUN.file_digest(root)
            (root / ".DS_Store").write_bytes(b"finder metadata")
            self.assertEqual(before, RUN.file_digest(root))

    def test_resume_rejects_fixture_drift(self):
        manifest = {
            "run_id": "test",
            "seed": 1,
            "repeat": 1,
            "timeout_seconds": 60,
            "infra_retries": 0,
            "providers": ["corti"],
            "models": {"corti": "corti/corti-s1"},
            "tasks": ["task"],
            "fixture_digest": "before",
        }
        with self.assertRaisesRegex(ValueError, "task fixtures changed"):
            RUN.validate_resume_manifest(manifest, "after")

    def test_resume_recovers_orphaned_attempt_checkpoint(self):
        jobs = [
            RUN.Job("corti", "task", 1),
            RUN.Job("claude", "task", 1),
        ]
        row = {
            "provider": "corti",
            "task": "task",
            "attempt": 1,
            "status": "PASS",
        }
        with tempfile.TemporaryDirectory() as temp:
            run_dir = pathlib.Path(temp)
            checkpoint = RUN.result_checkpoint_path(run_dir, jobs[0])
            RUN.write_json_atomic(checkpoint, row)
            recovered = RUN.load_completed_results(run_dir, jobs)
            self.assertEqual(recovered, [row])

    def test_atomic_results_checkpoint_round_trip(self):
        rows = [
            {"provider": "corti", "task": "a", "attempt": 1},
            {"provider": "claude", "task": "a", "attempt": 1},
        ]
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / "results.jsonl"
            RUN.write_json_atomic(path, rows, json_lines=True)
            loaded = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual(loaded, rows)
            self.assertFalse((path.parent / f".{path.name}.tmp").exists())

    def test_prepared_workspace_contains_no_private_artifacts(self):
        task = ROOT / "tasks" / "01_ttl_cache"
        with tempfile.TemporaryDirectory() as temp:
            workspace = RUN.prepare_workspace(task, pathlib.Path(temp))
            self.assertTrue((workspace / "TASK.md").exists())
            self.assertTrue((workspace / "tests" / "test_public.py").exists())
            self.assertFalse((workspace / "grader.py").exists())
            self.assertFalse((workspace / "solution").exists())
            self.assertFalse((workspace / "AGENTS.md").exists())

    def test_rate_limit_is_infrastructure_error(self):
        self.assertEqual(RUN.classify_nonzero("HTTP 429 rate limit"), "INFRA_ERROR")
        self.assertEqual(RUN.classify_nonzero("agent crashed"), "CLI_ERROR")

    def test_report_excludes_infrastructure_errors_but_counts_timeouts(self):
        with tempfile.TemporaryDirectory() as temp:
            run_dir = pathlib.Path(temp)
            (run_dir / "manifest.json").write_text(json.dumps({
                "run_id": "test", "seed": 1, "repeat": 1,
            }))
            rows = [
                {"provider": "corti", "model": "corti/corti-s1", "task": "a", "attempt": 1,
                 "status": "PASS", "wall_seconds": 2.0, "fixture_unchanged": True},
                {"provider": "corti", "model": "corti/corti-s1", "task": "b", "attempt": 1,
                 "status": "INFRA_ERROR", "wall_seconds": 1.0, "fixture_unchanged": True},
                {"provider": "corti", "model": "corti/corti-s1", "task": "c", "attempt": 1,
                 "status": "TIMEOUT", "wall_seconds": 900.0, "fixture_unchanged": True},
            ]
            (run_dir / "results.jsonl").write_text("\n".join(json.dumps(row) for row in rows))
            report = REPORT.generate(run_dir)
            self.assertIn("1/2", report)
            self.assertIn("50.0%", report)
            self.assertIn("15.1 min", report)

if __name__ == "__main__":
    unittest.main()
