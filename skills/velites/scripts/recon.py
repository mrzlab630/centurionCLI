#!/usr/bin/env python3
"""
🛡️ VELITES RECONNAISSANCE TOOL
Part of CenturionCLI (Cohors Ferrata)

Performs active reconnaissance on a target URL/Host.
- Port Scanning (Top 20 common ports)
- HTTP Header Analysis (Tech Stack)
- Robots.txt & Sitemap discovery
- DNS lookup
"""

import argparse
import socket
import sys
import json
import ssl
import urllib.request
import urllib.parse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# SSL Context (Ignore errors for recon)
ssl._create_default_https_context = ssl._create_unverified_context

COMMON_PORTS = [
    21, 22, 23, 25, 53, 80, 110, 135, 139, 143,
    443, 445, 993, 995, 1433, 3000, 3306, 5432, 8000, 8080
]

def banner():
    print("""
    ⚔️  VELITES RECON v1.0
    Centurion Legion | Cohors Ferrata
    """)

def check_port(host, port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            if s.connect_ex((host, port)) == 0:
                return port
    except:
        pass
    return None

def scan_ports(host):
    print(f"[*] Scanning top {len(COMMON_PORTS)} ports on {host}...")
    open_ports = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(check_port, host, p) for p in COMMON_PORTS]
        for f in futures:
            if f.result():
                open_ports.append(f.result())
    return sorted(open_ports)

def http_recon(url):
    print(f"[*] Analyzing HTTP headers for {url}...")
    results = {}
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Centurion/Velites'})
        with urllib.request.urlopen(req, timeout=5) as r:
            results['status'] = r.status
            results['headers'] = dict(r.headers)
            results['url'] = r.geturl()
            
            # Detect Tech
            server = r.headers.get('Server', 'Unknown')
            powered = r.headers.get('X-Powered-By', 'Unknown')
            results['tech_stack'] = f"Server: {server} | Powered By: {powered}"
    except Exception as e:
        results['error'] = str(e)
    return results

def check_path(base_url, path):
    url = urllib.parse.urljoin(base_url, path)
    try:
        req = urllib.request.Request(url, method='HEAD', headers={'User-Agent': 'Centurion/Velites'})
        with urllib.request.urlopen(req, timeout=3) as r:
            if r.status == 200:
                return url
    except:
        pass
    return None

def main():
    parser = argparse.ArgumentParser(description="Velites Recon Tool")
    parser.add_argument("target", help="Target URL (e.g., https://example.com) or Hostname")
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    args = parser.parse_args()

    target = args.target
    if not target.startswith("http"):
        # Assume hostname, default to https
        host = target
        url = f"https://{target}"
    else:
        url = target
        host = urllib.parse.urlparse(url).netloc

    if not args.json:
        banner()
        print(f"🎯 Target: {host} ({url})")
        # Use timezone-aware UTC
        from datetime import timezone
        print(f"🕒 Time: {datetime.now(timezone.utc).isoformat()}")

    report = {
        "target": target,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ip": None,
        "ports": [],
        "http": {},
        "files": []
    }

    # 1. DNS Resolution
    try:
        ip = socket.gethostbyname(host)
        report['ip'] = ip
        if not args.json: print(f"📍 IP Address: {ip}")
    except Exception as e:
        if not args.json: print(f"❌ DNS Error: {e}")

    # 2. Port Scan
    if report['ip']:
        report['ports'] = scan_ports(report['ip'])
        if not args.json:
            if report['ports']:
                print(f"🔓 Open Ports: {', '.join(map(str, report['ports']))}")
            else:
                print("🔒 No common ports open.")

    # 3. HTTP Recon
    report['http'] = http_recon(url)
    if not args.json:
        print(f"🌐 HTTP Status: {report['http'].get('status', 'Error')}")
        print(f"🏗️  Tech Stack: {report['http'].get('tech_stack', 'Unknown')}")

    # 4. File Discovery
    if not args.json: print("[*] Checking common files...")
    for f in ['/robots.txt', '/sitemap.xml', '/security.txt', '/.well-known/security.txt']:
        found = check_path(url, f)
        if found:
            report['files'].append(found)
            if not args.json: print(f"📄 Found: {found}")

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("\n✅ Reconnaissance Complete.")

if __name__ == "__main__":
    main()
