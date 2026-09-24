#!/usr/bin/env python3
"""Offline regressions for model roles and controller-owned review handoffs."""

import copy
import hashlib
import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import agent_contract_runner as runner
from agent_result_builder import _load_schema, resolve_schema_path, validate_candidate
from review_ladder import ROUTING_PREFIX, RoutingError, select_review_route, validate_order_routing


def route(**changes):
    result = {
        "objectiveId": "handoff-objective", "attempt": 1, "taskClass": "ui_implementation",
        "complexity": "medium", "risk": "low", "ambiguity": "low", "reversibility": "high",
        "evidenceNeed": "high", "executor": "claude", "model": "claude-opus-5",
        "reasoningEffort": "high", "executionProfile": "terminal_review",
        "verificationProfile": "V2", "reviewer": "none", "confidence": "high",
        "reasons": ["escalation: independent review of UI work"], "terminalGate": True,
    }
    result.update(changes)
    return result


def set_route(order, metadata):
    order["executor"] = metadata["executor"]
    order["riskLevel"] = metadata["risk"]
    order["notesForExecutor"] = [ROUTING_PREFIX + json.dumps(metadata, separators=(",", ":"))]


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="legion-handoff-")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.candidate = self.repo / "candidate.json"
        self.candidate.write_text('{"status":"done"}\n')
        self.state_path = self.repo / "state.json"
        self.policy = runner.PathPolicy(self.repo, [str(self.repo)], [], "review-order-001")
        self.contract = {
            "version": "AQUILA_LOOP_V1", "controller": "Aquila", "loopId": "handoff-loop",
            "phase": "verify", "statePath": str(self.state_path),
            "workItem": {"workItemId": "item-001", "project": "test", "objective": "review UI"},
            "iteration": {"current": 1, "max": 3}, "budgets": {"maxWallSeconds": 3600},
            "executorStateWrites": False, "scheduleNextIteration": False, "selfApprove": False,
            "candidate": {"orderId": "candidate-order-001", "executor": "agy", "resultPath": str(self.candidate)},
            "verification": {"blind": True, "candidateOrderId": "candidate-order-001", "candidateExecutor": "agy"},
        }
        self.state = {
            "stateVersion": "AQUILA_LOOP_STATE_V1", "controller": "Aquila", "loopId": "handoff-loop",
            "project": "test", "statePath": str(self.state_path),
            "workItem": {"workItemId": "item-001", "objective": "review UI", "status": "awaiting_verification"},
            "iteration": self.contract["iteration"], "budgets": self.contract["budgets"],
            "candidate": {**self.contract["candidate"],
                "resultSha256": hashlib.sha256(self.candidate.read_bytes()).hexdigest(),
                "reviewContract": {"objectiveId": "handoff-objective", "taskClass": "ui_implementation",
                    "verificationProfile": "V2", "reviewer": "claude-opus-5"}},
            "verification": {"status": "pending"}, "failures": [], "transitions": [],
        }
        self.order = {"orderId": "review-order-001", "createdAt": "2026-09-24T00:00:00Z",
            "roleForTask": "REVIEWER", "loopContract": self.contract}
        set_route(self.order, route())
        self.write_state()

    def write_state(self):
        self.state_path.write_text(json.dumps(self.state))

    def test_assigned_opus_review_and_no_recursive_review(self):
        runner.prepare_loop_dispatch(self.order, self.policy)
        decision = select_review_route(validate_order_routing(self.order))
        self.assertEqual(decision["reviewer"], "none")
        self.assertEqual(decision["route"], "terminal_closure")
        self.assertEqual(decision["verificationProfile"], "V2")

    def test_child_cannot_lower_parent_review_floor(self):
        set_route(self.order, route(executor="codex", model="gpt-6-sol", verificationProfile="V1"))
        with self.assertRaisesRegex(runner.RunnerError, "cannot lower"):
            runner.prepare_loop_dispatch(self.order, self.policy)

    def test_child_cannot_change_objective_or_task_class(self):
        for key in ("objectiveId", "taskClass"):
            with self.subTest(key=key):
                set_route(self.order, route(**{key: "unrelated"}))
                with self.assertRaisesRegex(runner.RunnerError, key):
                    runner.prepare_loop_dispatch(self.order, self.policy)

    def test_missing_or_mutated_candidate_rejected(self):
        self.candidate.write_text('{"status":"done","changed":true}')
        with self.assertRaisesRegex(runner.RunnerError, "changed since"):
            runner.prepare_loop_dispatch(self.order, self.policy)
        self.candidate.unlink()
        with self.assertRaisesRegex(runner.RunnerError, "cannot hash"):
            runner.prepare_loop_dispatch(self.order, self.policy)

    def test_candidate_symlink_rejected_even_with_same_bytes(self):
        target = self.repo / "same-bytes.json"
        self.candidate.rename(target)
        self.candidate.symlink_to(target)
        with self.assertRaisesRegex(runner.RunnerError, "path is unsafe"):
            runner.prepare_loop_dispatch(self.order, self.policy)

    def test_route_or_digest_omission_cannot_bypass_binding(self):
        for field in ("reviewContract", "resultSha256"):
            with self.subTest(field=field):
                broken = copy.deepcopy(self.state)
                del broken["candidate"][field]
                self.state_path.write_text(json.dumps(broken))
                with self.assertRaises(runner.RunnerError):
                    runner.prepare_loop_dispatch(self.order, self.policy)
        self.write_state()
        self.order["createdAt"] = "2026-07-01T00:00:00Z"
        with self.assertRaisesRegex(runner.RunnerError, "requires routing"):
            runner.prepare_loop_dispatch(self.order, self.policy)

    def test_result_changed_during_review_cannot_complete_loop(self):
        runner.prepare_loop_dispatch(self.order, self.policy)
        self.candidate.write_text("changed during review")
        result = {"status": "done", "executorExtensions": {"aquilaLoop": {
            "loopId": "handoff-loop", "phase": "verify", "workItemId": "item-001", "iteration": 1, "verdict": "pass"}}}
        with self.assertRaisesRegex(runner.RunnerError, "changed since"):
            runner.update_loop_state_after_result(self.order, self.policy, result, self.repo / "review.json", None)
        self.assertEqual(json.loads(self.state_path.read_text())["workItem"]["status"], "awaiting_verification")

    def test_execution_saves_binding_and_review_completes(self):
        self.contract["phase"] = "execute"
        implementation = route(executor="agy", model="gemini-3.8-flash", executionProfile="implementation", reviewer="claude-opus-5")
        implementation.pop("terminalGate")
        set_route(self.order, implementation)
        self.order["roleForTask"] = "PICTOR"
        self.order["orderId"] = "candidate-order-001"
        result = {"status": "done", "executorExtensions": {"aquilaLoop": {
            "loopId": "handoff-loop", "phase": "execute", "workItemId": "item-001", "iteration": 1}}}
        runner.update_loop_state_after_result(self.order, self.policy, result, self.candidate, None)
        self.state = json.loads(self.state_path.read_text())
        self.assertEqual(self.state["candidate"]["reviewContract"]["reviewer"], "claude-opus-5")
        self.contract["phase"] = "verify"
        self.order["orderId"] = "review-order-001"
        self.order["roleForTask"] = "REVIEWER"
        set_route(self.order, route())
        result["executorExtensions"]["aquilaLoop"].update(phase="verify", verdict="pass")
        runner.prepare_loop_dispatch(self.order, self.policy)
        runner.update_loop_state_after_result(self.order, self.policy, result, self.repo / "review.json", None)
        self.assertEqual(json.loads(self.state_path.read_text())["workItem"]["status"], "completed")

    def test_gemini_launch_binds_flags_not_prompt_text(self):
        valid = "agy --model=gemini-3.8-flash --effort high --print 'Write UI text'"
        runner.validate_gemini_launch(valid, "gemini-3.8-flash", "high")
        for command in (
            "agy --print '--model gemini-3.8-flash --effort high'",
            valid + " --model another-model", valid + " --effort low",
            valid + " --continue", "agy -- --model gemini-3.8-flash --effort high",
            "agy --model gemini-3.8-flash --effort low --print text",
        ):
            with self.subTest(command=command), self.assertRaises(runner.RunnerError):
                runner.validate_gemini_launch(command, "gemini-3.8-flash", "high")

    def test_terminal_reviewer_cannot_report_product_fixes(self):
        _, validator = _load_schema(resolve_schema_path())
        payload = {"resultVersion": "AGENT_RESULT_JSON_V1", "orderId": self.order["orderId"],
            "executor": "claude", "status": "done", "summary": "reviewed", "filesChanged": [],
            "artifacts": [], "proof": [{"command": "inspect", "cwd": str(self.repo), "status": "pass", "exitCode": 0, "summary": "inspected"}],
            "selfReview": {"performed": True, "findings": [], "fixesApplied": []},
            "scopeDeviations": [], "forbiddenPatternHits": [], "remainingRisks": [], "questions": [], "errors": [],
            "stdoutSummary": "", "stderrSummary": ""}
        self.assertEqual(validate_candidate(payload, self.order, validator), [])
        for changes in ({"filesChanged": [{"path": "product.py", "action": "modified"}]},
                        {"selfReview": {"performed": True, "findings": [], "fixesApplied": ["fixed product"]}}):
            errors = validate_candidate({**payload, **changes}, self.order, validator)
            self.assertTrue(any("terminal_review" in error for error in errors), errors)

    def test_explicit_escalation_not_lost_and_executor_alias_rejected(self):
        implementation = route(executor="agy", model="gemini-3.8-flash", executionProfile="implementation", reviewer="claude-opus-5")
        implementation.pop("terminalGate")
        self.assertEqual(select_review_route(implementation)["verificationProfile"], "V2")
        set_route(self.order, route(executor="other"))
        with self.assertRaisesRegex(RoutingError, "requires executor=claude"):
            validate_order_routing(self.order)

    def test_terminal_product_edit_closes_direct_custody_as_rejected(self):
        import regression_agent_contract_runner as fixtures
        from direct_custody import verify_direct_terminal

        fixtures.install_fake_executor()
        order_path, result, _, _, _, events = fixtures.make_order(
            self.repo, "review-edits-rejected", "pass", True, "python3 -c 'print(1)'",
        )
        order = json.loads(order_path.read_text())
        order.update(createdAt="2026-09-24T00:00:00Z", roleForTask="REVIEWER")
        set_route(order, route())
        command = shlex.split(order["launch"]["command"])
        command[0] = "claude"
        order["launch"]["command"] = shlex.join(command)
        fixtures.write_json(order_path, order)
        env = {**os.environ, "PATH": f"{fixtures.BIN_DIR}:{os.environ.get('PATH', '')}",
               "HOME": str(self.repo / "empty-home"), "HERMES_HOME": str(self.repo / "empty-hermes")}
        for key in ("FAKE_REVIEW_ONLY", "FAKE_RESULT_MODE", "AQUILA_ATTEMPT_LEDGER"):
            env.pop(key, None)
        completed = subprocess.run(
            [sys.executable, str(fixtures.RUNNER), "--order", str(order_path),
             "--mode", "run", "--events", str(events), "--result", str(result)],
            env=env, cwd=self.repo, capture_output=True, text=True, timeout=20,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("terminal_review", completed.stderr)
        self.assertNotIn("Traceback", completed.stderr)
        namespace = result.parent
        paths = [list(namespace.glob(f"direct-{kind}-*.json"))
                 for kind in ("start", "closure", "acceptance")]
        self.assertEqual([len(items) for items in paths], [1, 1, 1])
        terminal = verify_direct_terminal(*(items[0] for items in paths), order_path, result)
        self.assertEqual(terminal["status"], "rejected")


if __name__ == "__main__":
    unittest.main(verbosity=2)
