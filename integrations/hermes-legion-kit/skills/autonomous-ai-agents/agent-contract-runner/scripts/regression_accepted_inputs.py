#!/usr/bin/env python3
"""Offline regression proof for accepted advisory predecessor handoffs."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import accepted_inputs
from accepted_inputs import AcceptedInputError, verify_input_results
from agent_artifact_namespace import artifact_namespace


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class AcceptedInputsRegression(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="accepted-inputs-")
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name)

    def _stage(self, order_id: str, *, input_results: list[dict] | None = None, artifact_text: str = "advice\n") -> dict:
        namespace = artifact_namespace(self.repo, order_id)
        namespace.mkdir(parents=True)
        artifact = namespace / "advice.md"
        artifact.write_text(artifact_text, encoding="utf-8")
        order_path = namespace / "order.json"
        result_path = namespace / "result.json"
        start_path = namespace / "start.json"
        closure_path = namespace / "closure.json"
        proof_path = namespace / "controller-proof.json"
        acceptance_path = namespace / "controller-acceptance.json"
        order = {
            "orderVersion": "AGENT_ORDER_JSON_V1",
            "orderId": order_id,
            "executor": "codex",
            "inputResults": input_results or [],
        }
        result = {
            "resultVersion": "AGENT_RESULT_JSON_V1",
            "orderId": order_id,
            "executor": "codex",
            "status": "done",
            "filesChanged": [],
            "artifacts": [{"path": str(artifact), "exists": True, "type": "advice", "note": "fixture"}],
        }
        write_json(order_path, order)
        write_json(result_path, result)
        order_sha = digest(order_path)
        result_sha = digest(result_path)
        run_id = f"run-{order_id}"
        write_json(start_path, {
            "startReceiptVersion": "RESULT_GATEWAY_START_V1",
            "state": "started",
            "orderId": order_id,
            "executor": "codex",
            "runId": run_id,
            "orderPath": str(order_path),
            "orderSha256": order_sha,
            "resultPath": str(result_path),
            "startReceiptPath": str(start_path),
            "closurePath": str(closure_path),
        })
        start_sha = digest(start_path)
        write_json(closure_path, {
            "closureVersion": "RESULT_GATEWAY_CLOSURE_V2",
            "state": "closed",
            "launcherClosed": True,
            "canonicalFinalized": True,
            "childStarted": True,
            "timedOut": False,
            "exitCode": 0,
            "controllerErrors": [],
            "canonicalStatus": "done",
            "orderId": order_id,
            "executor": "codex",
            "runId": run_id,
            "orderPath": str(order_path),
            "startReceiptPath": str(start_path),
            "startReceiptSha256": start_sha,
            "canonicalResultPath": str(result_path),
            "canonicalResultSha256": result_sha,
            "orderSha256": order_sha,
        })
        closure_sha = digest(closure_path)
        write_json(proof_path, {
            "version": "AQUILA_CONTROLLER_VERIFICATION_V1",
            "scope": "post_execution_proof",
            "status": "passed",
            "reason": None,
            "orderId": order_id,
            "runId": run_id,
            "orderSha256": order_sha,
            "startReceiptSha256": start_sha,
            "closureSha256": closure_sha,
            "canonicalResultSha256": result_sha,
            "observedChecks": {"proof": [{"status": "pass"}]},
        })
        proof_sha = digest(proof_path)
        write_json(acceptance_path, {
            "version": "AQUILA_CONTROLLER_ACCEPTANCE_V1",
            "status": "passed",
            "reason": None,
            "orderId": order_id,
            "runId": run_id,
            "orderSha256": order_sha,
            "startReceiptSha256": start_sha,
            "closureSha256": closure_sha,
            "canonicalResultSha256": result_sha,
            "proofReceiptSha256": proof_sha,
            "completedAt": "2026-09-24T00:00:00Z",
        })
        return {
            "order": order,
            "orderPath": order_path,
            "resultPath": result_path,
            "resultSha256": result_sha,
            "acceptancePath": acceptance_path,
            "acceptanceSha256": digest(acceptance_path),
            "closurePath": closure_path,
            "artifactPath": artifact,
            "artifactSha256": digest(artifact),
        }

    @staticmethod
    def _input(stage: dict) -> dict:
        return {
            "orderId": stage["order"]["orderId"],
            "resultPath": str(stage["resultPath"]),
            "resultSha256": stage["resultSha256"],
            "acceptancePath": str(stage["acceptancePath"]),
            "acceptanceSha256": stage["acceptanceSha256"],
            "closurePath": str(stage["closurePath"]),
            "artifacts": [{"path": str(stage["artifactPath"]), "sha256": stage["artifactSha256"], "mediaType": "text/markdown"}],
        }

    @staticmethod
    def _reseal(stage: dict) -> None:
        """Pin intentionally invalid receipt content to test semantics, not hashes."""
        namespace = stage["resultPath"].parent
        start_path = namespace / "start.json"
        proof_path = namespace / "controller-proof.json"
        order_sha = digest(stage["orderPath"])
        stage["resultSha256"] = digest(stage["resultPath"])
        start = json.loads(start_path.read_text(encoding="utf-8"))
        start["orderSha256"] = order_sha
        write_json(start_path, start)
        closure = json.loads(stage["closurePath"].read_text(encoding="utf-8"))
        closure.update(orderSha256=order_sha, canonicalResultSha256=stage["resultSha256"], startReceiptSha256=digest(start_path))
        write_json(stage["closurePath"], closure)
        proof = json.loads(proof_path.read_text(encoding="utf-8"))
        proof.update(orderSha256=order_sha, canonicalResultSha256=stage["resultSha256"], startReceiptSha256=digest(start_path), closureSha256=digest(stage["closurePath"]))
        write_json(proof_path, proof)
        acceptance = json.loads(stage["acceptancePath"].read_text(encoding="utf-8"))
        acceptance.update(orderSha256=order_sha, canonicalResultSha256=stage["resultSha256"], startReceiptSha256=digest(start_path), closureSha256=digest(stage["closurePath"]), proofReceiptSha256=digest(proof_path))
        write_json(stage["acceptancePath"], acceptance)
        stage["acceptanceSha256"] = digest(stage["acceptancePath"])

    def test_full_advisory_implementation_review_chain(self) -> None:
        advisory = self._stage("advisory-001")
        implementation = self._stage("implementation-001", input_results=[self._input(advisory)], artifact_text="implementation\n")
        review = self._stage("review-001", input_results=[self._input(implementation)], artifact_text="review\n")
        verified = verify_input_results(review["order"], self.repo)
        self.assertEqual(verified[0]["orderId"], "implementation-001")
        self.assertEqual(verified[0]["nested"][0]["orderId"], "advisory-001")
        self.assertEqual(verify_input_results(advisory["order"], self.repo), [])

    def test_result_tampering_and_wrong_identity_are_rejected(self) -> None:
        advisory = self._stage("advisory-002")
        implementation = self._stage("implementation-002", input_results=[self._input(advisory)])
        advisory["resultPath"].write_text(advisory["resultPath"].read_text(encoding="utf-8").replace('"done"', '"failed"'), encoding="utf-8")
        with self.assertRaisesRegex(AcceptedInputError, "canonical result digest mismatch"):
            verify_input_results(implementation["order"], self.repo)
        advisory["resultPath"].write_text(json.dumps({"resultVersion": "AGENT_RESULT_JSON_V1", "orderId": "other-002", "executor": "codex", "status": "done", "artifacts": []}) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(AcceptedInputError, "canonical result digest mismatch"):
            verify_input_results(implementation["order"], self.repo)

    def test_symlink_artifact_nonpassed_acceptance_and_current_order_are_rejected(self) -> None:
        advisory = self._stage("advisory-003")
        implementation = self._stage("implementation-003", input_results=[self._input(advisory)])
        outside = self.repo / "outside.md"
        outside.write_text("outside\n", encoding="utf-8")
        advisory["artifactPath"].unlink()
        advisory["artifactPath"].symlink_to(outside)
        with self.assertRaisesRegex(AcceptedInputError, "must not contain symlinks"):
            verify_input_results(implementation["order"], self.repo)

        advisory = self._stage("advisory-004")
        implementation = self._stage("implementation-004", input_results=[self._input(advisory)])
        acceptance = json.loads(advisory["acceptancePath"].read_text(encoding="utf-8"))
        acceptance["status"] = "rejected"
        acceptance["reason"] = "fixture rejection"
        advisory["acceptancePath"].write_text(json.dumps(acceptance, sort_keys=True) + "\n", encoding="utf-8")
        implementation["order"]["inputResults"][0]["acceptanceSha256"] = digest(advisory["acceptancePath"])
        with self.assertRaisesRegex(AcceptedInputError, "acceptance is not passed"):
            verify_input_results(implementation["order"], self.repo)

        current = self._stage("current-005")
        current["order"]["inputResults"] = [{
            "orderId": "current-005", "resultPath": str(current["resultPath"]), "resultSha256": current["resultSha256"],
            "acceptancePath": str(current["acceptancePath"]), "acceptanceSha256": current["acceptanceSha256"], "artifacts": [],
            "closurePath": str(current["closurePath"]),
        }]
        with self.assertRaisesRegex(AcceptedInputError, "current order"):
            verify_input_results(current["order"], self.repo)

    def test_duplicate_inputs_and_malformed_entries_fail_closed(self) -> None:
        advisory = self._stage("advisory-006")
        duplicate = self._stage("implementation-006", input_results=[self._input(advisory), self._input(advisory)])
        with self.assertRaisesRegex(AcceptedInputError, "duplicate orderId"):
            verify_input_results(duplicate["order"], self.repo)
        malformed = self._stage("implementation-007")
        malformed["order"]["inputResults"] = [{"orderId": "advisory-006"}]
        with self.assertRaisesRegex(AcceptedInputError, "unexpected or missing fields"):
            verify_input_results(malformed["order"], self.repo)

    def test_artifact_drift_rejected_when_rechecking_before_acceptance(self) -> None:
        predecessor = self._stage("advisory-drift")
        current = {"orderId": "current-drift", "inputResults": [self._input(predecessor)]}
        self.assertEqual(len(verify_input_results(current, self.repo)), 1)
        predecessor["artifactPath"].write_text("changed after preflight\n", encoding="utf-8")
        with self.assertRaisesRegex(AcceptedInputError, "artifact digest mismatch"):
            verify_input_results(current, self.repo)

    def test_each_frozen_custody_document_is_bound(self) -> None:
        for index, filename in enumerate(("order.json", "result.json", "start.json", "closure.json", "controller-proof.json", "controller-acceptance.json")):
            with self.subTest(filename=filename):
                predecessor = self._stage(f"advisory-custody-{index}")
                current = {"orderId": "current-custody", "inputResults": [self._input(predecessor)]}
                path = predecessor["resultPath"].parent / filename
                path.write_bytes(path.read_bytes() + b" ")
                with self.assertRaises(AcceptedInputError):
                    verify_input_results(current, self.repo)

    def test_invalid_identity_executor_run_and_exit_cannot_be_pinned_as_success(self) -> None:
        cases = (
            ("result.json", "orderId", "wrong-order", "accepted done result"),
            ("result.json", "executor", "claude", "accepted done result"),
            ("order.json", "executor", [], "not a Gateway executor"),
            ("start.json", "executor", "claude", "receipt identities"),
            ("closure.json", "runId", "wrong-run", "receipt identities"),
            ("closure.json", "exitCode", False, "successful Gateway closure"),
            ("controller-proof.json", "scope", "preflight", "observed post-execution checks"),
        )
        for index, (filename, key, value, error) in enumerate(cases):
            with self.subTest(filename=filename, key=key):
                predecessor = self._stage(f"advisory-semantic-{index}")
                path = predecessor["resultPath"].parent / filename
                document = json.loads(path.read_text(encoding="utf-8"))
                document[key] = value
                write_json(path, document)
                self._reseal(predecessor)
                with self.assertRaisesRegex(AcceptedInputError, error):
                    verify_input_results({"orderId": "current-semantic", "inputResults": [self._input(predecessor)]}, self.repo)

    def test_symlink_control_parent_and_external_paths_fail_closed(self) -> None:
        predecessor = self._stage("advisory-paths")
        current = {"orderId": "current-paths", "inputResults": [self._input(predecessor)]}
        namespace = predecessor["resultPath"].parent
        actual_namespace = namespace.with_name("relocated-namespace")
        namespace.rename(actual_namespace)
        namespace.symlink_to(actual_namespace, target_is_directory=True)
        with self.assertRaisesRegex(AcceptedInputError, "must not contain symlinks"):
            verify_input_results(current, self.repo)
        namespace.unlink()
        actual_namespace.rename(namespace)
        current["inputResults"][0]["resultPath"] = str(self.repo / "product.json")
        with self.assertRaisesRegex(AcceptedInputError, "predecessor control namespace"):
            verify_input_results(current, self.repo)

    def test_relative_artifact_paths_work_and_alias_duplicates_do_not(self) -> None:
        predecessor = self._stage("advisory-relative")
        item = self._input(predecessor)
        item["artifacts"][0]["path"] = str(predecessor["artifactPath"].relative_to(self.repo))
        current = {"orderId": "current-relative", "inputResults": [item]}
        self.assertEqual(len(verify_input_results(current, self.repo)), 1)
        item["artifacts"].append(self._input(predecessor)["artifacts"][0])
        with self.assertRaisesRegex(AcceptedInputError, "duplicate artifact paths"):
            verify_input_results(current, self.repo)

    def test_nested_cycle_back_to_current_and_shared_duplicate_fail(self) -> None:
        predecessor = self._stage("advisory-cycle")
        invalid_ancestor = self._input(predecessor)
        invalid_ancestor["orderId"] = "current-cycle"
        predecessor["order"]["inputResults"] = [invalid_ancestor]
        write_json(predecessor["orderPath"], predecessor["order"])
        self._reseal(predecessor)
        with self.assertRaisesRegex(AcceptedInputError, "duplicate or cycle"):
            verify_input_results({"orderId": "current-cycle", "inputResults": [self._input(predecessor)]}, self.repo)
        leaf = self._stage("advisory-shared")
        middle = self._stage("implementation-shared", input_results=[self._input(leaf)])
        with self.assertRaisesRegex(AcceptedInputError, "duplicate or cycle"):
            verify_input_results({"orderId": "current-shared", "inputResults": [self._input(middle), self._input(leaf)]}, self.repo)

    def test_depth_limit_and_strict_json_fail_closed(self) -> None:
        leaf = self._stage("advisory-depth")
        middle = self._stage("implementation-depth", input_results=[self._input(leaf)])
        current = {"orderId": "current-depth", "inputResults": [self._input(middle)]}
        with patch.object(accepted_inputs, "MAX_INPUT_DEPTH", 1):
            with self.assertRaisesRegex(AcceptedInputError, "maximum depth"):
                verify_input_results(current, self.repo)
        leaf["resultPath"].write_text('{"orderId":"advisory-depth","orderId":"other-id"}\n', encoding="utf-8")
        with self.assertRaisesRegex(AcceptedInputError, "not strict JSON"):
            verify_input_results({"orderId": "current-json", "inputResults": [self._input(leaf)]}, self.repo)

    def test_artifact_must_be_reported_once_as_existing(self) -> None:
        for index, value in enumerate(([], [{"exists": False}], [{"exists": True}, {"exists": True}])):
            predecessor = self._stage(f"advisory-reported-{index}")
            result = json.loads(predecessor["resultPath"].read_text(encoding="utf-8"))
            result["artifacts"] = [dict(entry, path=str(predecessor["artifactPath"])) for entry in value]
            write_json(predecessor["resultPath"], result)
            self._reseal(predecessor)
            with self.assertRaisesRegex(AcceptedInputError, "not reported as existing"):
                verify_input_results({"orderId": "current-reported", "inputResults": [self._input(predecessor)]}, self.repo)

    def test_control_fifo_fails_without_waiting_for_writer(self) -> None:
        predecessor = self._stage("advisory-fifo")
        current = {"orderId": "current-fifo", "inputResults": [self._input(predecessor)]}
        predecessor["resultPath"].unlink()
        os.mkfifo(predecessor["resultPath"])
        with self.assertRaisesRegex(AcceptedInputError, "must be a regular file"):
            verify_input_results(current, self.repo)

    def test_absent_inputs_legacy_and_invalid_wire_shapes(self) -> None:
        self.assertEqual(verify_input_results({}, self.repo), [])
        with self.assertRaisesRegex(AcceptedInputError, "must be an array"):
            verify_input_results({"orderId": "current-shape", "inputResults": None}, self.repo)
        predecessor = self._stage("advisory-shape")
        for key, value, message in (
            ("orderId", "../unsafe", "unsafe"),
            ("resultSha256", "+" + "0" * 63, "lowercase SHA-256"),
            ("resultPath", "nul\x00path", "NUL byte"),
            ("extra", True, "unexpected or missing fields"),
        ):
            with self.subTest(key=key):
                item = self._input(predecessor)
                item[key] = value
                with self.assertRaisesRegex(AcceptedInputError, message):
                    verify_input_results({"orderId": "current-shape", "inputResults": [item]}, self.repo)


if __name__ == "__main__":
    unittest.main()
