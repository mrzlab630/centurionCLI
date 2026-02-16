#!/usr/bin/env python3
"""
🔮 HARUSPEX ANALYZER v2.0 (Powered by Legion Core)
"""

import sys
import os
import re

# Import Legion Core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from libs.legion_core import legion_tool, LegionIO

PATTERNS = {
    'SQL Injection': [r'SELECT.*FROM.*\$', r'execute\s*\(.*\%'],
    'XSS': [r'innerHTML', r'document\.write', r'dangerouslySetInnerHTML'],
    'RCE': [r'eval\(', r'exec\(', r'system\(']
}

def scan_file(filepath):
    findings = []
    try:
        with open(filepath, 'r', errors='ignore') as f:
            for i, line in enumerate(f):
                for vtype, regexes in PATTERNS.items():
                    for r in regexes:
                        if re.search(r, line, re.IGNORECASE):
                            findings.append({
                                "type": vtype,
                                "file": filepath,
                                "line": i+1,
                                "code": line.strip()[:100]
                            })
    except:
        pass
    return findings

def setup_args(parser):
    parser.add_argument("target", help="Path to code")

@legion_tool("Haruspex Static Code Analysis", setup_args)
def main(args):
    path = args.target
    if not os.path.exists(path):
        raise ValueError(f"Path not found: {path}")

    LegionIO.log(f"Scanning codebase: {path}")
    
    all_findings = []
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(('.py', '.js', '.php', '.go')):
                full_path = os.path.join(root, file)
                all_findings.extend(scan_file(full_path))

    LegionIO.log(f"Scan complete. Found {len(all_findings)} issues.")
    return {
        "scan_path": path,
        "total_findings": len(all_findings),
        "details": all_findings
    }

if __name__ == "__main__":
    main()
