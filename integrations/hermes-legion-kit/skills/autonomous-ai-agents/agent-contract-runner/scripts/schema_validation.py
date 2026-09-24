"""Fail-closed access to the JSON Schema Draft 2020-12 validator."""

from __future__ import annotations

try:
    from jsonschema import Draft202012Validator
except ImportError as exc:  # Do not silently downgrade schema semantics.
    raise RuntimeError(
        "jsonschema Draft 2020-12 support is required; refusing a weaker validator"
    ) from exc

__all__ = ["Draft202012Validator"]
