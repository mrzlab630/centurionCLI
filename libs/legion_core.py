#!/usr/bin/env python3
"""
🏛️ LEGION CORE LIBRARY v2.1 (Virtus Fix)
"""

import sys
import json
import os
import argparse
import traceback
from datetime import datetime, timezone
from functools import wraps
import ssl

# Global SSL Fix for MacOS/Python environment issues
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass

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
    def __init__(self, mission_id, work_dir=None):
        self.id = mission_id
        # Use absolute path relative to repo root or CWD
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        self.work_dir = work_dir or os.path.join(repo_root, ".missions")
        self.path = os.path.join(self.work_dir, f"{mission_id}.json")
        os.makedirs(self.work_dir, exist_ok=True)
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path, 'r') as f:
                return json.load(f)
        return {
            "id": self.id,
            "start_time": datetime.now(timezone.utc).isoformat(),
            "status": "started",
            "steps": {}
        }

    def save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f, indent=2)

    def update_step(self, step_name, status, output=None):
        self.data["steps"][step_name] = {
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "output": output
        }
        self.save()

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
