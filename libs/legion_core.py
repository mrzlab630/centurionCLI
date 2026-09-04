#!/usr/bin/env python3
"""
🏛️ LEGION CORE LIBRARY v2.1 (Virtus Fix)
"""

import sys
import copy
import json
import os
import argparse
import traceback
import fcntl
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import wraps
import math
import tempfile

# Markers for reliable parsing
JSON_START = "<<<LEGION_JSON_START>>>"
JSON_END = "<<<LEGION_JSON_END>>>"

class LegionIO:
    """Handles Input/Output standardization."""
    
    @staticmethod
    def log(message, level="INFO"):
        """Write logs to stderr."""
        timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        sys.stderr.write(f"[{timestamp}] [{level}] {message}\n")
        sys.stderr.flush()

    @staticmethod
    def output(data):
        """Write result wrapped in markers to stdout."""
        # Ensure nothing else is on the line
        print(f"\n{JSON_START}")
        print(json.dumps(data, indent=2, default=str))
        print(f"{JSON_END}\n")
        sys.stdout.flush()

    @staticmethod
    def fail(error_message, details=None):
        """Exit with error JSON."""
        error_data = {
            "status": "error",
            "error": error_message,
            "details": details or {}
        }
        LegionIO.output(error_data)
        sys.exit(1)

class MissionState:
    """Manages mission persistence."""
    MAX_HISTORY = 100
    STEP_STATUSES = {"pending", "running", "done", "failed", "skipped"}
    MISSION_STATUSES = {"started", "running", "failed", "complete"}

    def __init__(self, mission_id, work_dir=None, target=None):
        self._validate_mission_id(mission_id)
        self.id = mission_id
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        self.work_dir = os.path.abspath(work_dir or os.path.join(repo_root, ".missions"))
        self.path = os.path.join(self.work_dir, f"{mission_id}.json")
        self.target = target
        os.makedirs(self.work_dir, exist_ok=True)
        self.data = self._load()
        self._baseline = copy.deepcopy(self.data)
        self._baseline_exists = os.path.exists(self.path)
        if target is not None:
            stored_target = self.data.get("target")
            if stored_target is not None and stored_target != target:
                raise ValueError(
                    f"Mission target mismatch for {self.id}: persisted target differs from resume target"
                )
            if stored_target is None:
                self.data["target"] = target

    @staticmethod
    def _validate_mission_id(mission_id):
        if not isinstance(mission_id, str) or not mission_id or "\x00" in mission_id:
            raise ValueError("Mission ID must be a non-empty string")
        if mission_id in {".", ".."} or "/" in mission_id or "\\" in mission_id:
            raise ValueError("Mission ID must not contain path separators or traversal")

    @staticmethod
    def _reject_constant(value):
        raise ValueError(f"Non-finite JSON number is not allowed: {value}")

    @staticmethod
    def _pairs_without_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    @classmethod
    def _assert_finite(cls, value):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("Non-finite JSON number is not allowed")
        if isinstance(value, dict):
            for nested in value.values():
                cls._assert_finite(nested)
        elif isinstance(value, list):
            for nested in value:
                cls._assert_finite(nested)

    @classmethod
    def _read_json(cls, path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                raw = handle.read()
            value = json.loads(
                raw,
                object_pairs_hook=cls._pairs_without_duplicates,
                parse_constant=cls._reject_constant,
            )
            cls._assert_finite(value)
            return value
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"Invalid mission state at {path}: {exc}") from exc

    def _load(self):
        if os.path.exists(self.path):
            data = self._read_json(self.path)
            if not isinstance(data, dict):
                raise ValueError(f"Invalid mission state at {self.path}: top-level JSON must be an object")
            if data.get("id") != self.id:
                raise ValueError(f"Mission state ID mismatch: expected {self.id!r}, got {data.get('id')!r}")
        else:
            data = {
            "id": self.id,
            "start_time": datetime.now(timezone.utc).isoformat(),
            "status": "started",
            "steps": {}
            }

        status = data.get("status", "started")
        if status not in self.MISSION_STATUSES:
            raise ValueError(f"Invalid mission status: {status!r}")
        steps = data.setdefault("steps", {})
        if not isinstance(steps, dict):
            raise ValueError("Mission state steps must be an object")
        for step_name, step in steps.items():
            if not isinstance(step_name, str) or not isinstance(step, dict):
                raise ValueError("Mission state steps must map names to objects")
            if step.get("status") not in self.STEP_STATUSES:
                raise ValueError(f"Invalid persisted status for step {step_name!r}")
        history = data.setdefault("history", [])
        attempts = data.setdefault("attempts", [])
        if not isinstance(history, list) or not isinstance(attempts, list):
            raise ValueError("Mission state history and attempts must be arrays")
        return data

    @contextmanager
    def _mission_lock(self):
        directory_fd = os.open(self.work_dir, os.O_RDONLY)
        try:
            fcntl.flock(directory_fd, fcntl.LOCK_EX)
            yield
        finally:
            try:
                fcntl.flock(directory_fd, fcntl.LOCK_UN)
            finally:
                os.close(directory_fd)

    def _reload_locked(self):
        self.data = self._load()
        self._baseline = copy.deepcopy(self.data)
        self._baseline_exists = os.path.exists(self.path)
        if self.target is not None:
            stored_target = self.data.get("target")
            if stored_target is not None and stored_target != self.target:
                raise ValueError(
                    f"Mission target mismatch for {self.id}: persisted target differs from resume target"
                )
            if stored_target is None:
                self.data["target"] = self.target

    def save(self, _lock_held=False):
        if not _lock_held:
            with self._mission_lock():
                return self.save(_lock_held=True)
        persisted_exists = os.path.exists(self.path)
        if persisted_exists != self._baseline_exists:
            raise ValueError(f"Stale mission state for {self.id}: persisted baseline changed")
        if persisted_exists and self._load() != self._baseline:
            raise ValueError(f"Stale mission state for {self.id}: persisted baseline changed")
        self._assert_finite(self.data)
        fd, temporary_path = tempfile.mkstemp(
            prefix=f".{self.id}.", suffix=".tmp", dir=self.work_dir
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(self.data, handle, indent=2, allow_nan=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self.path)
            try:
                directory_fd = os.open(self.work_dir, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            except OSError:
                pass
            self._baseline = copy.deepcopy(self.data)
            self._baseline_exists = True
        except Exception:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass
            raise

    def _record_history(self, event, **details):
        entry = {
            "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **details,
        }
        self.data["history"].append(entry)
        del self.data["history"][:-self.MAX_HISTORY]

    def _record_attempt(self, step_name, status, output):
        self.data["attempts"].append({
            "step": step_name,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "output": output,
        })
        del self.data["attempts"][:-self.MAX_HISTORY]

    def update_step(self, step_name, status, output=None):
        if not isinstance(step_name, str) or not step_name:
            raise ValueError("Step name must be a non-empty string")
        if status not in self.STEP_STATUSES:
            raise ValueError(f"Invalid step status: {status!r}")
        with self._mission_lock():
            self._reload_locked()
            current_step = self.data["steps"].get(step_name)
            current_status = current_step.get("status") if current_step else "pending"
            if current_status not in self.STEP_STATUSES:
                raise ValueError(f"Invalid persisted status for step {step_name!r}: {current_status!r}")
            allowed = {
                "pending": self.STEP_STATUSES,
                "running": {"running", "done", "failed"},
                "failed": {"failed", "running", "done"},
                "skipped": {"skipped", "running"},
                "done": {"done"},
            }
            if status not in allowed[current_status]:
                raise ValueError(
                    f"Illegal transition for step {step_name!r}: {current_status} -> {status}"
                )
            self.data["steps"][step_name] = {
                "status": status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "output": output
            }
            self._record_attempt(step_name, status, output)
            self._record_history("step", step=step_name, status=status)
            self.save(_lock_held=True)

    def update_status(self, status, output=None):
        if status not in self.MISSION_STATUSES:
            raise ValueError(f"Invalid mission status: {status!r}")
        with self._mission_lock():
            self._reload_locked()
            current_status = self.data.get("status", "started")
            allowed = {
                "started": {"started", "running", "failed", "complete"},
                "running": {"running", "failed", "complete"},
                "failed": {"failed", "running"},
                "complete": {"complete"},
            }
            if status not in allowed[current_status]:
                raise ValueError(f"Illegal mission status transition: {current_status} -> {status}")
            if status == current_status == "complete":
                return
            if status == "complete":
                incomplete = [
                    name for name, step in self.data["steps"].items()
                    if step.get("status") not in {"done", "skipped"}
                ]
                if incomplete:
                    raise ValueError(f"Cannot complete mission with unfinished steps: {', '.join(incomplete)}")
            self.data["status"] = status
            if status == "complete":
                self.data["completed_at"] = datetime.now(timezone.utc).isoformat()
            elif status == "failed":
                self.data["failed_at"] = datetime.now(timezone.utc).isoformat()
                if output is not None:
                    self.data["failure"] = output
            self._record_history("mission", status=status)
            self.save(_lock_held=True)

    def mark_complete(self):
        self.update_status("complete")

    def mark_failed(self, output=None):
        self.update_status("failed", output)

    def get_step(self, step_name):
        return self.data["steps"].get(step_name)

def legion_tool(description, args_configurator=None):
    """
    Decorator to standardize CLI tools.
    args_configurator: function(parser) -> None
    """
    def decorator(func):
        @wraps(func)
        def wrapper():
            parser = argparse.ArgumentParser(description=description)
            
            # Default standard args
            parser.add_argument("--json", action="store_true", help="Force JSON output")
            
            # Custom args
            if args_configurator:
                args_configurator(parser)
            else:
                # If no config provided, add generic target
                parser.add_argument("--target", help="Target input", required=False)

            # Parse known args to avoid erroring on extra flags if needed, 
            # but strict parsing is better for tools.
            args = parser.parse_args()

            try:
                # Execute tool
                result = func(args)
                
                # Success wrapper
                response = {
                    "status": "success",
                    "data": result,
                    "meta": {"ts": datetime.now(timezone.utc).isoformat()}
                }
                LegionIO.output(response)
                
            except Exception as e:
                LegionIO.log(f"CRITICAL: {e}", "ERROR")
                trace = traceback.format_exc()
                LegionIO.fail(str(e), {"trace": trace})

        return wrapper
    return decorator
