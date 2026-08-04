#!/usr/bin/env python3
"""Shared fail-closed JSON decoding for packaged control-plane inputs."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


class StrictJSONError(ValueError):
    """Raised when authoritative input is not unambiguous finite JSON."""


def _reject_constant(value: str) -> None:
    raise StrictJSONError(f"non-finite constant {value}")


def _parse_finite_float(literal: str) -> float:
    parsed = float(literal)
    if not math.isfinite(parsed):
        raise StrictJSONError(f"non-finite numeric literal {literal}")
    return parsed


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise StrictJSONError(f"duplicate key {key!r}")
        value[key] = item
    return value


def strict_json_loads(text: str, context: str) -> Any:
    """Decode one JSON value while rejecting ambiguous or non-finite input."""
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
            parse_float=_parse_finite_float,
        )
    except (json.JSONDecodeError, StrictJSONError, TypeError, ValueError, OverflowError) as exc:
        raise StrictJSONError(f"{context} is not strict JSON: {exc}") from exc


def strict_json_load_bytes(content: bytes, context: str) -> Any:
    """Decode UTF-8 JSON bytes with the shared strict semantics."""
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StrictJSONError(f"{context} is not strict JSON: invalid UTF-8: {exc}") from exc
    return strict_json_loads(text, context)


def strict_json_load_path(path: Path, context: str) -> Any:
    """Read and strictly decode one JSON file without hiding I/O failures."""
    return strict_json_load_bytes(path.read_bytes(), context)
