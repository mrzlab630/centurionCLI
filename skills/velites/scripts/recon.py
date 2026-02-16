#!/usr/bin/env python3
"""
🛡️ VELITES RECON v2.0 (Powered by Legion Core)
"""

import sys
import os
import socket
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

# Import Legion Core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from libs.legion_core import legion_tool, LegionIO

COMMON_PORTS = [21, 22, 80, 443, 3000, 8000, 8080]

def check_port(host, port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            if s.connect_ex((host, port)) == 0:
                return port
    except:
        pass
    return None

def setup_args(parser):
    parser.add_argument("target", help="Target URL/Host")

@legion_tool("Velites Active Reconnaissance", setup_args)
def main(args):
    target = args.target
    if not target:
        raise ValueError("Target is required")

    LegionIO.log(f"Starting Recon on {target}")
    
    if not target.startswith("http"):
        host = target
        url = f"https://{target}"
    else:
        url = target
        host = urllib.parse.urlparse(url).netloc

    report = {
        "target": host,
        "url": url,
        "ip": None,
        "open_ports": [],
        "headers": {}
    }

    # 1. DNS
    try:
        report['ip'] = socket.gethostbyname(host)
        LegionIO.log(f"Resolved IP: {report['ip']}")
    except Exception as e:
        LegionIO.log(f"DNS Error: {e}", "WARN")

    # 2. Ports
    if report['ip']:
        LegionIO.log(f"Scanning ports on {report['ip']}...")
        with ThreadPoolExecutor(max_workers=10) as ex:
            futures = [ex.submit(check_port, report['ip'], p) for p in COMMON_PORTS]
            for f in futures:
                if f.result():
                    report['open_ports'].append(f.result())
        LegionIO.log(f"Open ports: {report['open_ports']}")

    # 3. HTTP Headers
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Centurion/Velites'})
        with urllib.request.urlopen(req, timeout=5) as r:
            report['headers'] = dict(r.headers)
            report['status'] = r.status
    except Exception as e:
        report['http_error'] = str(e)

    return report

if __name__ == "__main__":
    main()
