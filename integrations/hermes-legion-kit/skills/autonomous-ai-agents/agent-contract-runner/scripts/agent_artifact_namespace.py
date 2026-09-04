#!/usr/bin/env python3
"""Canonical namespace rules for controller-owned executor artifacts."""

from __future__ import annotations

import re
from pathlib import Path


CONTROL_NAMESPACE_RELATIVE = Path(".centurion") / "agents_results"
_SAFE_ORDER_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{7,127}$")


class ArtifactNamespaceError(ValueError):
    """Raised when an order identity or control artifact path is unsafe."""


def validate_order_id(order_id: str) -> str:
    """Return a safe single path component for an order identity."""
    if not isinstance(order_id, str) or not order_id.strip():
        raise ArtifactNamespaceError("orderId must be a non-empty string")
    if order_id != order_id.strip() or not _SAFE_ORDER_ID.fullmatch(order_id):
        raise ArtifactNamespaceError(
            "orderId must be one safe path component containing 8-128 ASCII letters, digits, '_' or '-'"
        )
    if order_id in {".", ".."}:
        raise ArtifactNamespaceError("orderId must not be '.' or '..'")
    return order_id


def artifact_namespace(repo_path: str | Path, order_id: str) -> Path:
    """Derive the controller-artifact directory without touching the filesystem."""
    safe_order_id = validate_order_id(order_id)
    repo = Path(repo_path).expanduser().resolve(strict=False)
    return repo / CONTROL_NAMESPACE_RELATIVE / safe_order_id


def require_no_symlink_components(namespace: str | Path) -> Path:
    """Reject pre-existing symlinks in the derived control namespace components."""
    namespace_path = Path(namespace).expanduser()
    for component in (
        namespace_path.parent.parent,
        namespace_path.parent,
        namespace_path,
    ):
        try:
            is_symlink = component.is_symlink()
        except OSError as exc:
            raise ArtifactNamespaceError(
                f"could not inspect control artifact namespace component {component}: {exc}"
            ) from exc
        if is_symlink:
            raise ArtifactNamespaceError(
                "control artifact namespace component must not be a symlink: "
                f"{component}"
            )
    return namespace_path


def require_control_path(path: str | Path, namespace: Path, label: str) -> Path:
    """Require a control path to be a strict descendant of ``namespace``."""
    require_no_symlink_components(namespace)
    resolved = Path(path).expanduser().resolve(strict=False)
    namespace = namespace.resolve(strict=False)
    if namespace not in resolved.parents:
        raise ArtifactNamespaceError(
            f"{label} must be under expected control artifact namespace {namespace}: {resolved}"
        )
    return resolved
