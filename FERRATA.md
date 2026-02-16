# ⚔️ COHORS FERRATA (The Iron Cohort)

> **Autonomous Security & Verification Suite**
> *Inspired by Shannon, built for Centurion.*

This module transforms CenturionCLI into an autonomous security auditor and verification engine.

## 🏛️ The Doctrine: "Acta, Non Verba"
We do not just "guess" vulnerabilities. We **prove** them.
Every finding goes through the **Probatio** cycle:
1.  **Recon** (Scan)
2.  **Analyze** (Hypothesize)
3.  **Exploit** (Verify)

---

## 🦅 The Legionaries

### 1. 🛡️ VELITES (The Scout)
**Role:** Active Reconnaissance
**Tool:** `skills/velites/scripts/recon.py`
**Usage:**
```bash
python3 skills/velites/scripts/recon.py https://target.com
```
**Output:** JSON map of ports, tech stack, and hidden files.

### 2. 🔮 HARUSPEX (The Analyst)
**Role:** Static Analysis (SAST)
**Tool:** `skills/haruspex/scripts/scan_code.py`
**Usage:**
```bash
python3 skills/haruspex/scripts/scan_code.py ./target-repo
```
**Output:** List of candidate vulnerabilities (SQLi, XSS, RCE) found in source code.

### 3. 🗡️ SICARIUS (The Assassin)
**Role:** Dynamic Verification (DAST)
**Tool:** `skills/sicarius/scripts/exploit_verify.py`
**Usage:**
```bash
python3 skills/sicarius/scripts/exploit_verify.py https://target.com/login \
  --input "#email=' OR 1=1" --submit "#login" --condition "url:dashboard"
```
**Output:** Screenshot proof of successful exploit.

---

## 🔄 The Shannon Cycle (Workflow)

To perform a full security audit:

1.  **Velites** scans the URL → finds `login.php`.
2.  **Haruspex** scans `login.php` source → finds `SELECT * FROM users WHERE user = $user`.
3.  **Haruspex** generates a hypothesis: "SQL Injection possible via `$user`".
4.  **Sicarius** launches Playwright with payload `' OR 1=1 --`.
5.  **Sicarius** confirms login bypass and saves `proof.png`.
6.  **Optio** reports: "Critical SQL Injection confirmed in `login.php`. Proof attached."

---

## 🚀 Installation & Requirements

*   **Python 3.10+**
*   **Playwright:** `pip install playwright && playwright install chromium`
*   **Permissions:** Only run against systems you own or have permission to test.
