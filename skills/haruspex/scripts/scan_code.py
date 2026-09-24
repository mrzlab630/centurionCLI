#!/usr/bin/env python3
"""
🔮 HARUSPEX ANALYZER v2.0 (Powered by Legion Core)
"""

import sys
import os
import re

# Import Legion Core
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../libs')))
from legion_core import legion_tool, LegionIO

PATTERNS = {
    'SQL Injection': [r'SELECT.*FROM.*\$', r'execute\s*\(.*\%'],
    'XSS': [r'innerHTML', r'document\.write', r'dangerouslySetInnerHTML'],
    'RCE': [r'eval\(', r'exec\(', r'system\(']
}

SCANNABLE_EXTENSIONS = ('.py', '.js', '.mjs', '.cjs', '.ts', '.tsx', '.php', '.go')


def scan_file(filepath, unreadable_files=None):
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
    except (OSError, UnicodeError) as exc:
        error = {"file": filepath, "error": str(exc)}
        if unreadable_files is not None:
            unreadable_files.append(error)
        LegionIO.log(f"Could not read {filepath}: {exc}", "WARNING")
    return findings

def setup_args(parser):
    parser.add_argument("target", help="Path to code")

@legion_tool("Haruspex Static Code Analysis", setup_args)
def main(args):
    path = args.target
    if not os.path.exists(path):
        raise ValueError(f"Path not found: {path}")
    if not os.path.isfile(path) and not os.path.isdir(path):
        raise ValueError(f"Path is not a file or directory: {path}")

    LegionIO.log(f"Scanning codebase: {path}")
    
    all_findings = []
    unreadable_files = []
    if os.path.isfile(path):
        all_findings.extend(scan_file(path, unreadable_files))
    else:
        def record_walk_error(error):
            unreadable_files.append({"file": error.filename, "error": str(error)})
            LegionIO.log(f"Could not read {error.filename}: {error}", "WARNING")

        for root, _, files in os.walk(path, onerror=record_walk_error):
            for file in files:
                if file.endswith(SCANNABLE_EXTENSIONS):
                    full_path = os.path.join(root, file)
                    all_findings.extend(scan_file(full_path, unreadable_files))

    scan_complete = not unreadable_files
    if scan_complete:
        LegionIO.log(f"Scan complete. Found {len(all_findings)} issues.")
    else:
        LegionIO.log(
            f"Scan incomplete. Found {len(all_findings)} issues; "
            f"could not read {len(unreadable_files)} files.",
            "WARNING"
        )
        unreadable_paths = ", ".join(error["file"] for error in unreadable_files)
        raise RuntimeError(
            f"Scan incomplete: could not read {len(unreadable_files)} files: {unreadable_paths}"
        )
    return {
        "scan_path": path,
        "total_findings": len(all_findings),
        "details": all_findings,
        "scan_complete": scan_complete,
        "unreadable_files": unreadable_files
    }

if __name__ == "__main__":
    main()
