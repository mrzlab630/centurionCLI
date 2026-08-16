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
python3 skills/velites/scripts/recon.py example.com
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

## 🧬 Architectural Standards (Legion Core)

All tools are built on `libs/legion_core.py`, ensuring:
1.  **Strict JSON I/O:** Output is wrapped in `<<<LEGION_JSON_START>>>` markers for reliable parsing.
2.  **State Management:** `MissionState` tracks progress in `.missions/`, allowing resume after failure.
3.  **Error Handling:** Automatic traceback capture and structured error reporting.

### Workflow Orchestration (OPTIO)

Use mission preparation to route Ferrata work to the right Legionaries and proof
gates. The active implementation uses lightweight `mission-prep.mjs`; the
Ferrata tools remain independently executable.

```bash
CENTURION_SKILLS_ROOT="${CENTURION_SKILLS_ROOT:-$PWD/skills}"
node "$CENTURION_SKILLS_ROOT/orchestrator/scripts/mission-prep.mjs" \
  "security audit target https://example.com with recon, sast, dast proof"
```

Typical Ferrata chain:

```text
OPTIO -> VELITES -> HARUSPEX -> SICARIUS -> REVIEWER/GUARDIAN
```

---

## 🚀 Installation & Requirements

*   **Python 3.10+**
*   **Playwright:** `pip install playwright && playwright install chromium`
*   **Permissions:** Only run against systems you own or have permission to test.
