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
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../libs')))
from legion_core import legion_tool, LegionIO

COMMON_PORTS = [21, 22, 80, 443, 3000, 8000, 8080]

def parse_target(target):
    """Return the URL to request and hostname to resolve for a valid target."""
    if not isinstance(target, str) or not target.strip():
        raise ValueError("Target is required")

    target = target.strip()
    lowered_target = target.lower()
    if lowered_target.startswith("http") and not lowered_target.startswith(("http://", "https://")):
        raise ValueError("Target URL must use http:// or https://")

    url = target if "://" in target else f"https://{target}"
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("Target URL must use http:// or https://")

    try:
        host = parsed.hostname
        parsed.port
    except ValueError as exc:
        raise ValueError(f"Invalid target URL: {exc}") from exc

    if not host or any(char.isspace() for char in host):
        raise ValueError("Target URL must include a valid hostname")

    return url, host

def check_port(host, port):
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return port
    except OSError:
        pass
    return None

def setup_args(parser):
    parser.add_argument("target", help="Target URL/Host")

@legion_tool("Velites Active Reconnaissance", setup_args)
def main(args):
    url, host = parse_target(args.target)
    LegionIO.log(f"Starting Recon on {url}")

    report = {
        "target": host,
        "url": url,
        "ip": None,
        "open_ports": [],
        "headers": {}
    }

    # 1. DNS
    try:
        addresses = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        report['ip'] = addresses[0][4][0]
        LegionIO.log(f"Resolved IP: {report['ip']}")
    except Exception as e:
        LegionIO.log(f"DNS Error: {e}", "WARN")
        raise ValueError(f"Unable to resolve target hostname {host!r}: {e}") from e

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
