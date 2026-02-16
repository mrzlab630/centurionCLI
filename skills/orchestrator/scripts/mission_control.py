#!/usr/bin/env python3
"""
🏛️ OPTIO MISSION CONTROL v2.1 (Virtus Fix)
Robust orchestration with Marker-based Parsing.
"""

import sys
import os
import subprocess
import json
import uuid
import re

# Import Legion Core path setup
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.append(os.path.join(REPO_ROOT, 'libs'))

# Try importing to ensure it works
try:
    from legion_core import legion_tool, LegionIO, MissionState, JSON_START, JSON_END
except ImportError:
    # Fallback if libs not in path
    print(f"Error: Could not import legion_core from {REPO_ROOT}/libs", file=sys.stderr)
    sys.exit(1)

SKILLS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

def parse_legion_output(stdout):
    """Extract JSON from marker blocks."""
    # Look for content between markers
    pattern = re.compile(f"{re.escape(JSON_START)}\\s*(.*?)\\s*{re.escape(JSON_END)}", re.DOTALL)
    match = pattern.search(stdout)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON inside markers: {e}")
    # Fallback: try parsing whole stdout if it looks like JSON
    try:
        return json.loads(stdout.strip())
    except:
        raise RuntimeError("No valid Legion JSON output found in stdout")

def run_agent(role, script, args):
    path = os.path.join(SKILLS_DIR, role, 'scripts', script)
    if not os.path.exists(path):
        raise RuntimeError(f"Script not found: {path}")

    # Use sys.executable to ensure same python env
    cmd = [sys.executable, path] + args
    
    LegionIO.log(f"Calling {role} ({script})...")
    try:
        # Capture both streams
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        # Pass through stderr logs from agent
        if res.stderr:
            sys.stderr.write(res.stderr)
        
        if res.returncode != 0:
            raise RuntimeError(f"Agent process failed (code {res.returncode})")

        return parse_legion_output(res.stdout)

    except Exception as e:
        raise RuntimeError(f"Agent execution error: {e}")

def setup_args(parser):
    parser.add_argument("target", help="Mission target")
    parser.add_argument("--resume", help="Resume mission ID")

@legion_tool("Mission Control", setup_args)
def main(args):
    # Initialize Mission State
    mission_id = args.resume or f"mission_{uuid.uuid4().hex[:8]}"
    state = MissionState(mission_id)
    
    LegionIO.log(f"Mission ID: {mission_id}")
    if args.resume:
        LegionIO.log(f"Resuming mission...")

    target = args.target
    if not target:
        raise ValueError("Target required")

    # 1. Recon (Velites)
    step_recon = state.get_step("recon")
    if not step_recon or step_recon["status"] != "done":
        try:
            # We call recon.py with just the target. It handles --json implicitly via decorator if we passed it?
            # Actually, run_agent passes args directly. legion_tool adds --json flag.
            # But run_agent doesn't add --json automatically. Let's rely on standard args.
            # Wait, our scripts expect arguments.
            
            res = run_agent("velites", "recon.py", [target])
            
            if res.get("status") == "success":
                state.update_step("recon", "done", res["data"])
                LegionIO.log("✅ Recon complete")
            else:
                raise RuntimeError(res.get("error"))
        except Exception as e:
            state.update_step("recon", "failed", str(e))
            raise e
    else:
        LegionIO.log("⏭️ Skipping Recon (Already done)")

    # 2. Analyze (Haruspex)
    # Mock logic: check if target is a path
    if os.path.exists(target):
        step_analyze = state.get_step("analyze")
        if not step_analyze or step_analyze["status"] != "done":
            try:
                res = run_agent("haruspex", "scan_code.py", [target])
                if res.get("status") == "success":
                    state.update_step("analyze", "done", res["data"])
                    LegionIO.log("✅ Analysis complete")
                else:
                    raise RuntimeError(res.get("error"))
            except Exception as e:
                state.update_step("analyze", "failed", str(e))
                raise e
    else:
        if not state.get_step("analyze"):
            state.update_step("analyze", "skipped", "Target is remote URL")

    return {
        "mission_id": mission_id,
        "status": "complete",
        "results": state.data
    }

if __name__ == "__main__":
    main()
