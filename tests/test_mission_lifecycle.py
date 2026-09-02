import json
import importlib
import importlib.util
import multiprocessing
import os
import ssl
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "libs"))
import legion_core
from legion_core import MissionState


MISSION_CONTROL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "skills", "orchestrator", "scripts", "mission_control.py"
)
MISSION_CONTROL_SPEC = importlib.util.spec_from_file_location("mission_control_test", MISSION_CONTROL_PATH)
mission_control = importlib.util.module_from_spec(MISSION_CONTROL_SPEC)
MISSION_CONTROL_SPEC.loader.exec_module(mission_control)


def _run_concurrent_step(work_dir, step_name, barrier, result_queue):
    try:
        state = MissionState("concurrent", work_dir)
        barrier.wait()
        state.update_step(step_name, "done", step_name)
        result_queue.put((step_name, None))
    except BaseException as exc:
        result_queue.put((step_name, repr(exc)))


class MissionStateLifecycleTests(unittest.TestCase):
    def test_import_does_not_disable_default_tls_verification(self):
        default_context = ssl._create_default_https_context
        importlib.reload(legion_core)
        self.assertIs(ssl._create_default_https_context, default_context)

    def test_rejects_unsafe_ids_before_creating_path(self):
        with tempfile.TemporaryDirectory() as work_dir:
            for mission_id in ("../escape", "nested/mission", "nested\\mission"):
                with self.subTest(mission_id=mission_id):
                    with self.assertRaises(ValueError):
                        MissionState(mission_id, work_dir)
            self.assertEqual(os.listdir(work_dir), [])

    def test_save_replaces_atomically_and_preserves_legacy_fields(self):
        with tempfile.TemporaryDirectory() as work_dir:
            path = os.path.join(work_dir, "legacy.json")
            legacy = {
                "id": "legacy",
                "start_time": "2026-01-01T00:00:00+00:00",
                "status": "started",
                "steps": {},
                "legacy_field": {"keep": True},
            }
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(legacy, handle)
            state = MissionState("legacy", work_dir)
            state.update_step("recon", "done", {"ports": []})
            with open(path, encoding="utf-8") as handle:
                saved = json.load(handle)
            self.assertEqual(saved["legacy_field"], {"keep": True})
            self.assertEqual(saved["steps"]["recon"]["status"], "done")
            self.assertFalse(any(name.endswith(".tmp") for name in os.listdir(work_dir)))

    def test_public_save_rejects_stale_same_baseline_instance(self):
        with tempfile.TemporaryDirectory() as work_dir:
            MissionState("shared", work_dir).save()
            first = MissionState("shared", work_dir)
            second = MissionState("shared", work_dir)

            first.data["first_update"] = "committed"
            first.save()
            second.data["second_update"] = "stale"

            with self.assertRaisesRegex(ValueError, "Stale mission state"):
                second.save()

            persisted = MissionState("shared", work_dir).data
            self.assertEqual(persisted["first_update"], "committed")
            self.assertNotIn("second_update", persisted)

    def test_strict_load_rejects_duplicates_nonfinite_malformed_and_id_mismatch(self):
        cases = [
            '{"id":"m","status":"started","steps":{},"id":"other"}',
            '{"id":"m","status":"started","steps":{},"value":NaN}',
            '{"id":"m","status":"started","steps":{},"value":Infinity}',
            '{"id":"m","status":"started","steps":{},"value":1e999}',
            '{"id":"m","status":"started",',
            '{"id":"other","status":"started","steps":{}}',
        ]
        for payload in cases:
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as work_dir:
                with open(os.path.join(work_dir, "m.json"), "w", encoding="utf-8") as handle:
                    handle.write(payload)
                with self.assertRaises(ValueError):
                    MissionState("m", work_dir)

    def test_history_and_attempts_are_bounded_and_step_regressions_fail(self):
        with tempfile.TemporaryDirectory() as work_dir:
            state = MissionState("bounded", work_dir)
            for index in range(state.MAX_HISTORY + 5):
                state.update_step("recon", "running", index)
            self.assertEqual(len(state.data["history"]), state.MAX_HISTORY)
            self.assertEqual(len(state.data["attempts"]), state.MAX_HISTORY)
            state.update_step("recon", "done", "ok")
            with self.assertRaises(ValueError):
                state.update_step("recon", "failed", "late failure")

    def test_status_completion_and_resume_target_are_guarded(self):
        with tempfile.TemporaryDirectory() as work_dir:
            state = MissionState("mission", work_dir, target="alpha")
            state.update_status("running")
            state.update_step("recon", "done", "ok")
            state.mark_complete()
            with self.assertRaises(ValueError):
                state.update_status("failed", "conflict")
            with self.assertRaises(ValueError):
                MissionState("mission", work_dir, target="beta")
            resumed = MissionState("mission", work_dir, target="alpha")
            self.assertEqual(resumed.data["status"], "complete")
            self.assertEqual(resumed.data["steps"]["recon"]["status"], "done")

    def test_concurrent_process_updates_preserve_each_commit(self):
        with tempfile.TemporaryDirectory() as work_dir:
            MissionState("concurrent", work_dir).update_status("running")
            context = multiprocessing.get_context("fork")
            barrier = context.Barrier(2)
            result_queue = context.Queue()
            processes = [
                context.Process(
                    target=_run_concurrent_step,
                    args=(work_dir, step_name, barrier, result_queue),
                )
                for step_name in ("recon", "analyze")
            ]
            for process in processes:
                process.start()
            for process in processes:
                process.join(10)
                self.assertFalse(process.is_alive())
                self.assertEqual(process.exitcode, 0)
            results = [result_queue.get(timeout=1) for _ in processes]
            self.assertTrue(all(error is None for _, error in results), results)

            persisted = MissionState("concurrent", work_dir)
            self.assertEqual(
                {name: step["status"] for name, step in persisted.data["steps"].items()},
                {"recon": "done", "analyze": "done"},
            )
            self.assertEqual(
                {attempt["step"] for attempt in persisted.data["attempts"]},
                {"recon", "analyze"},
            )
            self.assertEqual(
                {entry["step"] for entry in persisted.data["history"] if entry["event"] == "step"},
                {"recon", "analyze"},
            )

    def test_ferrata_persists_truthful_success_and_failure(self):
        for succeeds in (True, False):
            with self.subTest(succeeds=succeeds), tempfile.TemporaryDirectory() as work_dir:
                def state_factory(mission_id, target=None):
                    return MissionState(mission_id, work_dir, target)

                run_result = {"status": "success", "data": {"ports": []}}
                run_side_effect = None if succeeds else RuntimeError("recon failed")
                with mock.patch.object(mission_control, "MissionState", side_effect=state_factory), \
                     mock.patch.object(
                         mission_control,
                         "run_agent",
                         return_value=run_result,
                         side_effect=run_side_effect,
                     ):
                    args = SimpleNamespace(target="https://example.test", resume=None)
                    if succeeds:
                        result = mission_control.main.__wrapped__(args)
                        self.assertEqual(result["status"], "complete")
                    else:
                        with self.assertRaisesRegex(RuntimeError, "recon failed"):
                            mission_control.main.__wrapped__(args)

                files = os.listdir(work_dir)
                self.assertEqual(len(files), 1)
                persisted = MissionState(files[0][:-5], work_dir, "https://example.test")
                self.assertEqual(persisted.data["status"], "complete" if succeeds else "failed")
                expected_step = "done" if succeeds else "failed"
                self.assertEqual(persisted.data["steps"]["recon"]["status"], expected_step)
                if succeeds:
                    self.assertEqual(persisted.data["steps"]["analyze"]["status"], "skipped")


if __name__ == "__main__":
    unittest.main()
