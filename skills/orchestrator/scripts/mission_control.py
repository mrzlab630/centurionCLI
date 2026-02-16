#!/usr/bin/env python3
"""
🏛️ OPTIO MISSION CONTROL
Part of CenturionCLI (Cohors Ferrata)

Orchestrates multi-agent workflows.
Executes specialized scripts (Velites, Haruspex, etc.) and aggregates results.
"""

import argparse
import subprocess
import json
import os
import sys
from datetime import datetime, timezone

# Path to other skills
SKILLS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

def run_legionary(role, script, args):
    """Executes a Legionary's script."""
    script_path = os.path.join(SKILLS_DIR, role, 'scripts', script)
    
    if not os.path.exists(script_path):
        return {"error": f"Script not found: {script_path}"}

    cmd = [sys.executable, script_path] + args + ['--json']
    print(f"[*] Optio executing: {role} -> {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            return {"error": f"Execution failed: {result.stderr}"}
        
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"error": "Invalid JSON output", "raw": result.stdout}
            
    except Exception as e:
        return {"error": str(e)}

def mission_security_audit(target):
    """
    MISSION: SECURITY AUDIT
    Protocol: Shannon Cycle (Recon -> Analyze -> Report)
    """
    report = {
        "mission": "Security Audit",
        "target": target,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "steps": []
    }

    # Step 1: Velites (Recon)
    print("--- PHASE 1: VELITES (Recon) ---")
    recon_data = run_legionary('velites', 'recon.py', [target])
    report['steps'].append({"step": "recon", "data": recon_data})
    
    if 'error' in recon_data:
        print("❌ Recon failed. Aborting.")
        return report

    # Step 2: Haruspex (Analyze) - Only if we have local source
    # For remote URL, Haruspex can't do SAST. 
    # But we can simulate "Checking known paths" based on Recon.
    
    # (Future) Step 3: Sicarius - If vulnerability candidates found
    
    print("✅ Mission Complete.")
    return report

def main():
    parser = argparse.ArgumentParser(description="Optio Mission Control")
    parser.add_argument("--mission", choices=['audit'], required=True, help="Mission type")
    parser.add_argument("--target", required=True, help="Target URL or Path")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    
    args = parser.parse_args()
    
    if args.mission == 'audit':
        result = mission_security_audit(args.target)
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        # Pretty print summary
        print(f"\n🏛️  MISSION REPORT: {result['mission']}")
        print(f"🎯 Target: {result['target']}")
        for step in result['steps']:
            print(f"\n[Step: {step['step'].upper()}]")
            if 'error' in step['data']:
                print(f"❌ Error: {step['data']['error']}")
            else:
                print(f"✅ Success. Data keys: {list(step['data'].keys())}")

if __name__ == "__main__":
    main()
