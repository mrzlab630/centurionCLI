#!/usr/bin/env python3
"""Focused regression proof for controller-owned linked artifact snapshots."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from artifact_lineage import LineageError, create_manifest, finalize_lineage, preflight_lineage, verify_anchor, verify_manifest


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ArtifactLineageRegression(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="artifact-lineage-")
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name)
        self.order_id = "advisory-001"
        self.control = self.repo / ".centurion" / "agents_results" / self.order_id
        self.control.mkdir(parents=True)
        self.order = self.control / "order.json"
        self.result = self.control / "result.json"
        self.start = self.control / "start.json"
        self.closure = self.control / "closure.json"
        self.acceptance = self.control / "controller-proof.json"
        self.terminal = self.control / "controller-acceptance.json"
        self.run_id = "run-id-advisory-001"
        self.product = self.repo / "docs" / "proposal.md"
        self.product.parent.mkdir()
        self.product.write_text("original proposal\n", encoding="utf-8")
        write_json(self.order, {"orderVersion": "AGENT_ORDER_JSON_V1", "orderId": self.order_id, "executor": "codex"})
        write_json(self.result, {"resultVersion": "AGENT_RESULT_JSON_V1", "orderId": self.order_id, "executor": "codex", "status": "done"})
        write_json(self.start, {
            "startReceiptVersion": "RESULT_GATEWAY_START_V1", "state": "started",
            "orderId": self.order_id, "executor": "codex", "runId": self.run_id,
            "orderPath": str(self.order), "resultPath": str(self.result),
            "startReceiptPath": str(self.start), "closurePath": str(self.closure),
            "orderSha256": sha256(self.order),
        })
        write_json(self.closure, {
            "closureVersion": "RESULT_GATEWAY_CLOSURE_V2", "state": "closed",
            "launcherClosed": True, "canonicalFinalized": True, "canonicalStatus": "done",
            "childStarted": True, "timedOut": False, "exitCode": 0, "controllerErrors": [],
            "orderId": self.order_id, "executor": "codex", "runId": self.run_id,
            "orderPath": str(self.order), "canonicalResultPath": str(self.result),
            "startReceiptPath": str(self.start),
            "orderSha256": sha256(self.order),
            "canonicalResultSha256": sha256(self.result),
            "startReceiptSha256": sha256(self.start),
        })
        self.write_acceptance()
        self.manifest_path = self.control / "lineage-manifest.json"

    def write_acceptance(self, status: str = "passed") -> None:
        write_json(self.acceptance, {
            "version": "AQUILA_CONTROLLER_VERIFICATION_V1",
            "scope": "post_execution_proof",
            "orderId": self.order_id, "runId": self.run_id,
            "orderSha256": sha256(self.order),
            "startReceiptSha256": sha256(self.start),
            "closureSha256": sha256(self.closure),
            "canonicalResultSha256": sha256(self.result),
            "status": status,
            "reason": None if status == "passed" else "fixture rejection",
            "observedChecks": {},
        })

    def write_terminal(self, anchor_digest: str, status: str = "passed") -> None:
        write_json(self.terminal, {
            "version": "AQUILA_CONTROLLER_ACCEPTANCE_V1",
            "orderId": self.order_id, "runId": self.run_id,
            "orderSha256": sha256(self.order),
            "startReceiptSha256": sha256(self.start),
            "closureSha256": sha256(self.closure),
            "canonicalResultSha256": sha256(self.result),
            "proofReceiptSha256": sha256(self.acceptance),
            "lineageAnchorSha256": anchor_digest,
            "status": status,
            "reason": None if status == "passed" else "fixture rejection",
            "completedAt": "2026-09-24T00:00:00Z",
        })

    def refresh_custody(self, acceptance_status: str = "passed") -> None:
        start = json.loads(self.start.read_text(encoding="utf-8"))
        start["orderSha256"] = sha256(self.order)
        write_json(self.start, start)
        closure = json.loads(self.closure.read_text(encoding="utf-8"))
        closure["orderSha256"] = sha256(self.order)
        closure["canonicalResultSha256"] = sha256(self.result)
        closure["startReceiptSha256"] = sha256(self.start)
        write_json(self.closure, closure)
        self.write_acceptance(acceptance_status)

    def create_first(self, **overrides):
        args = {
            "repo_path": self.repo,
            "order_id": self.order_id,
            "order_path": self.order,
            "result_path": self.result,
            "receipt_paths": {"start": self.start, "closure": self.closure, "acceptance": self.acceptance},
            "artifact_paths": [self.product],
            "manifest_path": self.manifest_path,
        }
        args.update(overrides)
        return create_manifest(**args)

    def test_manifest_binds_product_order_result_and_both_gateway_receipts(self) -> None:
        manifest, digest = self.create_first()
        self.assertEqual(sha256(self.manifest_path), digest)
        self.assertEqual(manifest["artifacts"][0]["path"], "docs/proposal.md")
        self.assertEqual(manifest["artifacts"][0]["sha256"], sha256(self.product))
        self.assertEqual(set(manifest["bindings"]["receipts"]), {"start", "closure", "acceptance"})
        self.assertEqual(verify_manifest(self.manifest_path, self.repo, expected_sha256=digest, expected_order_id=self.order_id), manifest)
        with self.assertRaisesRegex(LineageError, "already exists"):
            self.create_first()
        with self.assertRaisesRegex(LineageError, "manifest digest mismatch"):
            verify_manifest(self.manifest_path, self.repo, expected_sha256="0" * 64)

    def test_successor_checks_previous_manifest_and_live_artifact(self) -> None:
        _, first_digest = self.create_first()
        next_id = "implement-001"
        next_control = self.repo / ".centurion" / "agents_results" / next_id
        next_control.mkdir()
        next_order = next_control / "order.json"
        next_result = next_control / "result.json"
        next_product = self.repo / "src" / "change.py"
        next_product.parent.mkdir()
        next_product.write_text("print('ok')\n", encoding="utf-8")
        write_json(next_order, {"orderVersion": "AGENT_ORDER_JSON_V1", "orderId": next_id, "executor": "codex"})
        write_json(next_result, {"resultVersion": "AGENT_RESULT_JSON_V1", "orderId": next_id, "executor": "codex", "status": "done"})
        next_manifest = next_control / "lineage-manifest.json"
        verify_manifest(self.manifest_path, self.repo, expected_sha256=first_digest, expected_order_id=self.order_id)
        _, next_digest = create_manifest(
            repo_path=self.repo,
            order_id=next_id,
            order_path=next_order,
            result_path=next_result,
            receipt_paths={},
            artifact_paths=[next_product],
            manifest_path=next_manifest,
            previous_manifest_path=self.manifest_path,
            expected_previous_manifest_sha256=first_digest,
        )
        self.assertEqual(verify_manifest(next_manifest, self.repo, expected_sha256=next_digest)["previous"]["sha256"], first_digest)
        self.product.write_text("tampered proposal\n", encoding="utf-8")
        with self.assertRaisesRegex(LineageError, "changed since manifest creation"):
            verify_manifest(self.manifest_path, self.repo, expected_sha256=first_digest)
        self.assertEqual(verify_manifest(next_manifest, self.repo, expected_sha256=next_digest)["previous"]["sha256"], first_digest)

    def test_custody_files_and_manifest_tampering_fail(self) -> None:
        _, digest = self.create_first()
        self.result.write_text('{"orderId":"advisory-001","status":"failed"}\n', encoding="utf-8")
        with self.assertRaisesRegex(LineageError, "changed since manifest creation"):
            verify_manifest(self.manifest_path, self.repo, expected_sha256=digest)
        write_json(self.result, {"resultVersion": "AGENT_RESULT_JSON_V1", "orderId": self.order_id, "executor": "codex", "status": "done"})
        self.start.write_text('{"orderId":"advisory-001"}\n', encoding="utf-8")
        with self.assertRaisesRegex(LineageError, "changed since manifest creation"):
            verify_manifest(self.manifest_path, self.repo, expected_sha256=digest)
        self.start.write_text(json.dumps({
            "startReceiptVersion": "RESULT_GATEWAY_START_V1", "state": "started",
            "orderId": self.order_id, "executor": "codex", "runId": self.run_id,
            "orderPath": str(self.order), "resultPath": str(self.result),
            "startReceiptPath": str(self.start), "closurePath": str(self.closure),
            "orderSha256": sha256(self.order),
        }, sort_keys=True) + "\n", encoding="utf-8")
        self.manifest_path.write_bytes(self.manifest_path.read_bytes() + b" ")
        with self.assertRaisesRegex(LineageError, "manifest digest mismatch"):
            verify_manifest(self.manifest_path, self.repo, expected_sha256=digest)

    def test_deletion_marker_and_mode_are_verified(self) -> None:
        deleted = self.repo / "obsolete.txt"
        manifest, digest = self.create_first(deleted_paths=[deleted])
        self.assertIn({"path": "obsolete.txt", "type": "deleted"}, manifest["artifacts"])
        deleted.write_text("resurrected\n", encoding="utf-8")
        with self.assertRaisesRegex(LineageError, "declared deletion still exists"):
            verify_manifest(self.manifest_path, self.repo, expected_sha256=digest)
        deleted.unlink()
        original_mode = self.product.stat().st_mode & 0o7777
        os.chmod(self.product, original_mode ^ 0o100)
        with self.assertRaisesRegex(LineageError, "changed since manifest creation"):
            verify_manifest(self.manifest_path, self.repo, expected_sha256=digest)

    def test_symlinks_directories_and_unsafe_paths_are_rejected(self) -> None:
        link = self.repo / "docs" / "linked.md"
        link.symlink_to(self.product)
        with self.assertRaisesRegex(LineageError, "cannot open regular file"):
            self.create_first(artifact_paths=[link])
        with self.assertRaisesRegex(LineageError, "not a regular file"):
            self.create_first(artifact_paths=[self.product.parent])
        with self.assertRaisesRegex(LineageError, "unsafe path component"):
            self.create_first(artifact_paths=["docs/../proposal.md"])
        with self.assertRaisesRegex(LineageError, "outside controller namespace"):
            self.create_first(artifact_paths=[self.order])

    def test_product_replaced_by_symlink_after_snapshot_fails(self) -> None:
        _, digest = self.create_first()
        self.product.unlink()
        self.product.symlink_to(self.order)
        with self.assertRaisesRegex(LineageError, "cannot open regular file"):
            verify_manifest(self.manifest_path, self.repo, expected_sha256=digest)

    def test_wrong_receipt_link_and_untrusted_previous_digest_fail(self) -> None:
        closure = json.loads(self.closure.read_text(encoding="utf-8"))
        closure["canonicalResultSha256"] = "0" * 64
        write_json(self.closure, closure)
        with self.assertRaisesRegex(LineageError, "receipts do not bind"):
            self.create_first()
        closure["canonicalResultSha256"] = sha256(self.result)
        write_json(self.closure, closure)
        self.write_acceptance()
        self.create_first()
        other_control = self.repo / ".centurion" / "agents_results" / "implement-001"
        other_control.mkdir()
        write_json(other_control / "order.json", {"orderVersion": "AGENT_ORDER_JSON_V1", "orderId": "implement-001", "executor": "codex"})
        write_json(other_control / "result.json", {"resultVersion": "AGENT_RESULT_JSON_V1", "orderId": "implement-001", "executor": "codex", "status": "done"})
        with self.assertRaisesRegex(LineageError, "manifest digest mismatch"):
            create_manifest(
                repo_path=self.repo,
                order_id="implement-001",
                order_path=other_control / "order.json",
                result_path=other_control / "result.json",
                receipt_paths={},
                artifact_paths=[self.product],
                manifest_path=other_control / "lineage-manifest.json",
                previous_manifest_path=self.manifest_path,
                expected_previous_manifest_sha256="0" * 64,
            )

    def test_rejected_or_unrelated_result_and_receipt_cannot_be_manifested(self) -> None:
        rejected = json.loads(self.result.read_text(encoding="utf-8"))
        rejected["status"] = "failed"
        write_json(self.result, rejected)
        self.refresh_custody()
        with self.assertRaisesRegex(LineageError, "done status"):
            self.create_first()
        rejected["status"] = "done"
        rejected["orderId"] = "unrelated-001"
        write_json(self.result, rejected)
        self.refresh_custody()
        with self.assertRaisesRegex(LineageError, "identity"):
            self.create_first()
        rejected["orderId"] = self.order_id
        write_json(self.result, rejected)
        self.refresh_custody("rejected")
        with self.assertRaisesRegex(LineageError, "accepted order"):
            self.create_first()
        self.refresh_custody()
        closure = json.loads(self.closure.read_text(encoding="utf-8"))
        closure["runId"] = "unrelated-run"
        write_json(self.closure, closure)
        self.write_acceptance()
        with self.assertRaisesRegex(LineageError, "accepted order"):
            self.create_first()

    def test_gateway_receipts_require_controller_acceptance_and_control_paths(self) -> None:
        with self.assertRaisesRegex(LineageError, "start, closure and controller proof"):
            self.create_first(receipt_paths={"start": self.start, "closure": self.closure})
        outside = self.repo / "outside-result.json"
        outside.write_bytes(self.result.read_bytes())
        with self.assertRaisesRegex(LineageError, "result path must be in order control namespace"):
            self.create_first(result_path=outside)
        other_namespace = self.repo / ".centurion" / "agents_results" / "other-order-001"
        other_namespace.mkdir()
        copied = other_namespace / "acceptance.json"
        copied.write_bytes(self.acceptance.read_bytes())
        with self.assertRaisesRegex(LineageError, "receipt path must be in order control namespace"):
            self.create_first(receipt_paths={"start": self.start, "closure": self.closure, "acceptance": copied})

    def test_anchor_preflight_rejects_tampering_then_allows_same_path_successor(self) -> None:
        order = json.loads(self.order.read_text(encoding="utf-8"))
        order["lineage"] = {
            "artifactPaths": ["docs/proposal.md"], "deletedPaths": [],
            "previousAnchorPath": None, "previousAnchorSha256": None,
        }
        write_json(self.order, order)
        self.refresh_custody()
        self.assertIsNotNone(preflight_lineage(order, self.repo))
        first = finalize_lineage(
            order, self.repo, self.order, self.result,
            {"start": self.start, "closure": self.closure, "acceptance": self.acceptance},
        )
        assert first is not None
        with self.assertRaisesRegex(LineageError, "controller-acceptance.json"):
            verify_anchor(first["anchorPath"], self.repo, expected_sha256=first["anchorSha256"])
        self.write_terminal(first["anchorSha256"])
        first_anchor = verify_anchor(first["anchorPath"], self.repo, expected_sha256=first["anchorSha256"])
        self.assertEqual(first_anchor["manifestSha256"], first["manifestSha256"])
        next_id = "implement-001"
        next_order = {
            "orderVersion": "AGENT_ORDER_JSON_V1", "orderId": next_id, "executor": "codex",
            "lineage": {
                "artifactPaths": ["docs/proposal.md"], "deletedPaths": [],
                "previousAnchorPath": first["anchorPath"],
                "previousAnchorSha256": first["anchorSha256"],
            },
        }
        self.product.write_text("tampered before handoff\n", encoding="utf-8")
        with self.assertRaisesRegex(LineageError, "changed since manifest creation"):
            preflight_lineage(next_order, self.repo)
        self.product.write_text("original proposal\n", encoding="utf-8")
        self.assertIsNotNone(preflight_lineage(next_order, self.repo))
        self.product.write_text("legitimate successor revision\n", encoding="utf-8")
        next_control = self.repo / ".centurion" / "agents_results" / next_id
        next_control.mkdir()
        next_order_path = next_control / "order.json"
        next_result_path = next_control / "result.json"
        write_json(next_order_path, next_order)
        write_json(next_result_path, {
            "resultVersion": "AGENT_RESULT_JSON_V1", "orderId": next_id,
            "executor": "codex", "status": "done",
        })
        next_start = next_control / "start.json"
        next_closure = next_control / "closure.json"
        next_acceptance = next_control / "controller-proof.json"
        next_terminal = next_control / "controller-acceptance.json"
        run_id = "run-id-implement-001"
        write_json(next_start, {
            "startReceiptVersion": "RESULT_GATEWAY_START_V1", "state": "started",
            "orderId": next_id, "executor": "codex", "runId": run_id,
            "orderPath": str(next_order_path), "resultPath": str(next_result_path),
            "startReceiptPath": str(next_start), "closurePath": str(next_closure),
            "orderSha256": sha256(next_order_path),
        })
        write_json(next_closure, {
            "closureVersion": "RESULT_GATEWAY_CLOSURE_V2", "state": "closed",
            "launcherClosed": True, "canonicalFinalized": True, "canonicalStatus": "done",
            "childStarted": True, "timedOut": False, "exitCode": 0, "controllerErrors": [],
            "orderId": next_id, "executor": "codex", "runId": run_id,
            "orderPath": str(next_order_path), "canonicalResultPath": str(next_result_path),
            "startReceiptPath": str(next_start), "orderSha256": sha256(next_order_path),
            "canonicalResultSha256": sha256(next_result_path),
            "startReceiptSha256": sha256(next_start),
        })
        write_json(next_acceptance, {
            "version": "AQUILA_CONTROLLER_VERIFICATION_V1", "orderId": next_id,
            "scope": "post_execution_proof",
            "runId": run_id, "orderSha256": sha256(next_order_path),
            "startReceiptSha256": sha256(next_start), "closureSha256": sha256(next_closure),
            "canonicalResultSha256": sha256(next_result_path), "status": "passed",
            "reason": None, "observedChecks": {},
        })
        second = finalize_lineage(
            next_order, self.repo, next_order_path, next_result_path,
            {"start": next_start, "closure": next_closure, "acceptance": next_acceptance},
        )
        assert second is not None
        write_json(next_terminal, {
            "version": "AQUILA_CONTROLLER_ACCEPTANCE_V1", "orderId": next_id,
            "runId": run_id, "orderSha256": sha256(next_order_path),
            "startReceiptSha256": sha256(next_start), "closureSha256": sha256(next_closure),
            "canonicalResultSha256": sha256(next_result_path),
            "proofReceiptSha256": sha256(next_acceptance),
            "lineageAnchorSha256": second["anchorSha256"],
            "status": "passed", "reason": None, "completedAt": "2026-09-24T00:00:00Z",
        })
        self.assertEqual(verify_anchor(second["anchorPath"], self.repo, expected_sha256=second["anchorSha256"])["previousAnchorSha256"], first["anchorSha256"])
        with self.assertRaisesRegex(LineageError, "changed since manifest creation"):
            verify_anchor(first["anchorPath"], self.repo, expected_sha256=first["anchorSha256"])

    def test_terminal_acceptance_is_required_and_must_bind_anchor(self) -> None:
        order = json.loads(self.order.read_text(encoding="utf-8"))
        order["lineage"] = {
            "artifactPaths": ["docs/proposal.md"], "deletedPaths": [],
            "previousAnchorPath": None, "previousAnchorSha256": None,
        }
        write_json(self.order, order)
        self.refresh_custody()
        first = finalize_lineage(
            order, self.repo, self.order, self.result,
            {"start": self.start, "closure": self.closure, "acceptance": self.acceptance},
        )
        assert first is not None
        next_order = {
            "orderId": "implement-001",
            "lineage": {
                "artifactPaths": ["docs/proposal.md"], "deletedPaths": [],
                "previousAnchorPath": first["anchorPath"],
                "previousAnchorSha256": first["anchorSha256"],
            },
        }
        with self.assertRaisesRegex(LineageError, "controller-acceptance.json"):
            preflight_lineage(next_order, self.repo)
        self.write_terminal(first["anchorSha256"], status="rejected")
        with self.assertRaisesRegex(LineageError, "terminal controller acceptance does not bind"):
            preflight_lineage(next_order, self.repo)
        self.write_terminal("0" * 64)
        with self.assertRaisesRegex(LineageError, "terminal controller acceptance does not bind"):
            preflight_lineage(next_order, self.repo)
        self.write_terminal(first["anchorSha256"])
        self.assertIsNotNone(preflight_lineage(next_order, self.repo))


if __name__ == "__main__":
    unittest.main()
