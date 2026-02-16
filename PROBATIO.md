# 🦅 PROBATIO PROTOCOL (Standard of Proof)

> **"ACTA, NON VERBA"** — Deeds, not words.

This protocol defines the mandatory verification steps for the Centurion Legion. No task is complete until it passes **Probatio**.

---

## 🏗️ The Cycle (Workflow)

1.  **EXPLORATIO (Recon):** Understand the environment. Check paths, versions, dependencies.
2.  **EXECUTIO (Action):** Write the code, config, or script.
3.  **PROBATIO (Verification):** **Mandatory.** Execute the proof.
4.  **RELATIO (Report):** Report success *only* if Probatio passed.

---

## 🛡️ Standards of Proof

### 💻 For CODER (Code Generation)
*   **Requirement:** Code must run locally.
*   **Proof:**
    *   Example usage output (stdout).
    *   Unit test execution (`PASS`).
    *   No placeholders like `// ...rest of code`.
*   **Method:**
    ```bash
    python3 script.py --test
    node script.js
    go run main.go
    ```

### 🌐 For VELITES/EXPLORATOR (Web Tasks)
*   **Requirement:** Confirm the page looks/acts as expected.
*   **Proof:**
    *   Playwright screenshot or HTML dump of key elements.
    *   Successful HTTP status (200 OK).
*   **Method:**
    *   Use `browser` tool or `web_fetch`.
    *   Create a temporary Playwright script to verify dynamic content.

### 🔧 For PONTIFEX (DevOps/Server)
*   **Requirement:** Service is up and reachable.
*   **Proof:**
    *   `curl -v localhost:PORT`
    *   `systemctl status` (or equivalent)
    *   Log check (no errors).
*   **Method:**
    *   Exec command on target host.

---

## 🚨 Failure Protocol

If **Probatio** fails:
1.  **DO NOT** ask the user what to do.
2.  **ANALYZE** the stderr/error log.
3.  **FIX** the code immediately.
4.  **RETRY** Probatio.
5.  *Limit:* 3 autonomous retries before reporting failure.

---

## 🧬 Integration

*   **Optio:** Must reject any completion report that lacks Probatio data.
*   **Virtus Mode:** Automatically enables strict Probatio.
