#!/usr/bin/env python3
"""
🔮 HARUSPEX SOURCE ANALYZER
Part of CenturionCLI (Cohors Ferrata)

Performs static analysis (SAST) to find vulnerability candidates.
Uses regex patterns to identify dangerous sinks.
"""

import argparse
import os
import re
import json
import sys
from datetime import datetime, timezone

# Dangerous patterns database
PATTERNS = {
    'SQL Injection': [
        r'SELECT.*FROM.*\$',           # PHP variables in SQL
        r'Execute\s*\(\s*["\'].*\+',   # String concat in SQL exec
        r'cursor\.execute\s*\(\s*f["\']', # Python f-string in SQL
    ],
    'XSS': [
        r'innerHTML\s*=',
        r'dangerouslySetInnerHTML',
        r'document\.write\(',
        r'echo\s+\$_GET',
        r'<%=.*%>'
    ],
    'RCE': [
        r'eval\s*\(',
        r'exec\s*\(',
        r'system\s*\(',
        r'subprocess\.call',
        r'os\.system'
    ],
    'Hardcoded Secrets': [
        r'api_key\s*=\s*["\'][A-Za-z0-9]{20,}["\']',
        r'password\s*=\s*["\'].+["\']',
        r'secret\s*=\s*["\'].+["\']'
    ]
}

def scan_file(filepath):
    findings = []
    try:
        with open(filepath, 'r', errors='ignore') as f:
            lines = f.readlines()
            
        for i, line in enumerate(lines):
            for vuln_type, regex_list in PATTERNS.items():
                for regex in regex_list:
                    if re.search(regex, line, re.IGNORECASE):
                        findings.append({
                            "type": vuln_type,
                            "file": filepath,
                            "line": i + 1,
                            "code": line.strip(),
                            "pattern": regex
                        })
    except Exception as e:
        pass # Ignore binary files etc
        
    return findings

def scan_directory(root_dir, extensions=None):
    if not extensions:
        extensions = ['.py', '.js', '.ts', '.php', '.go', '.java', '.rb', '.c', '.cpp', '.h', '.html']
        
    all_findings = []
    
    for root, dirs, files in os.walk(root_dir):
        # Skip hidden dirs
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                path = os.path.join(root, file)
                all_findings.extend(scan_file(path))
                
    return all_findings

def main():
    parser = argparse.ArgumentParser(description="Haruspex Source Analyzer")
    parser.add_argument("path", help="Path to repository/directory to scan")
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    args = parser.parse_args()

    if not args.json:
        print(f"""
    🔮 HARUSPEX ANALYZER v1.0
    Centurion Legion | Cohors Ferrata
    Scanning: {args.path}
        """)

    results = scan_directory(args.path)
    
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "target": args.path,
        "count": len(results),
        "findings": results
    }

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"🔎 Found {len(results)} potential issues:\n")
        for f in results:
            print(f"[{f['type']}] {f['file']}:{f['line']}")
            print(f"   Code: {f['code']}")
            print("")

if __name__ == "__main__":
    main()
