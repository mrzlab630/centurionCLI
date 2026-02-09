# ⚔️ CENTURION — Commander of the AI Legion

<div align="center">

<img src="logo/logo_vexillum.jpg" alt="CENTURION Vexillum" width="300">

![Name](https://img.shields.io/badge/⚔️-CENTURION-gold)
![Version](https://img.shields.io/badge/version-COHORS%20SECUNDA-gold)
![Status](https://img.shields.io/badge/status-BATTLE%20READY-green)

**The Ultimate AI Orchestration Framework for OpenClaw / Claude Code**

*DISCIPLINA ET FIDES* (Discipline and Loyalty)

</div>

## 🏛️ What is CENTURION?

CENTURION transforms your AI coding assistant into a disciplined **Roman Legion**.
Instead of a generic chatbot, you command an elite squad of specialized agents ("Legionaries").

### ⚡ Core Capabilities
*   **Orchestration (OPTIO):** Translates chaos into plans.
*   **Implementation (CODER):** Writes modern, stub-free code (includes Refactoring & Docs).
*   **Research (EXPLORATOR):** Maps codebases, **Deep Search** (Perplexity AI), and **Web Surfing** (Stealth).
*   **Defense (GUARDIAN):** Security audits & Dependency checks.
*   **Ops (PONTIFEX):** Docker, CI/CD, PostgreSQL maintenance.
*   **Hard Mode (VIRTUS):** Anti-lazy protocol for critical tasks.

---

## 🦅 The Legion (Elite 8)

| Legionary | Role | Command |
| :--- | :--- | :--- |
| **OPTIO** | **Commander.** Orchestrates, plans, clarifies requests. | `/orchestrator` |
| **CODER** | **Builder.** Writes code, refactors, documents. | `/coder` |
| **DEBUGGER** | **Medic.** Fixes bugs, analyzes logs/data. | `/error-handler` |
| **EXPLORATOR** | **Scout.** Codebase research + **Deep Search (Perplexity)** + Web Surfing. | `/researcher` |
| **PONTIFEX** | **Engineer.** DevOps, Docker, PostgreSQL. | `/devops` |
| **TESTER** | **Tester.** Unit & E2E testing. | `/tester` |
| **GUARDIAN** | **Shield.** Security & Dependency Guard. | `/security` |
| **LIBRARIUS** | **Scribe.** Planning & Project Memory. | `/planner` |

*Specialists:* `ARTIFEX` (Forge), `EVOCATUS` (Delegate), `SIGNIFER` (Git).

---

## 🧠 BATTLE PROTOCOLS

### 🚀 CODE MODE
**Trigger:** Repetitive tasks, large data processing.
**Action:** The Legionary writes a temporary script (Node.js/Python) to execute the task locally instead of consuming tokens in chat loops.

### 🦅 VIRTUS (Super Mode)
**Trigger:** `Virtus!` or Complex Tasks.
**Action:**
1.  **Nulla Remissio:** Zero laziness. No stubs.
2.  **Ratio Maxima:** Deep reasoning (Chain of Thought).
3.  **Veritas Absoluta:** Fact-checking via Context7.

### 📚 MEMORIA (Knowledge)
LIBRARIUS automatically maintains `KNOWLEDGE.md` to store architectural decisions.

---

## 🚀 Installation

### 1. Clone & Install
```bash
git clone https://github.com/mrzlab630/centurionCLI.git ~/.claude
```

### 2. Configure Deep Search (Perplexity)
```bash
export PERPLEXITY_API_KEY="pplx-your-key-here"

# Test
node ~/.claude/skills/researcher/scripts/deep-search.js "test query"
```
Get an API key at [perplexity.ai](https://docs.perplexity.ai).

### 3. Configure Web Surfing (Optional)
For Stealth Browser:
```bash
cd ~/.claude/skills/researcher
npm install
```

---

## 🔍 EXPLORATOR Deep Search

EXPLORATOR now has **Perplexity AI** integration for real-time research with citations.

```bash
# Quick search
node scripts/deep-search.js "What is Solana Geyser?"

# Deep research
node scripts/deep-search.js "Solana MEV protection strategies 2026" sonar-pro

# Latest news only
node scripts/deep-search.js "crypto market today" sonar day
```

| Model | Speed | Best For |
|-------|-------|----------|
| `sonar` | ~1s | Quick facts |
| `sonar-pro` | ~3s | Deep research |
| `sonar-reasoning` | ~10s | Complex analysis |
| `sonar-deep-research` | ~30s | Full investigation |

---

*Built with the precision of a Roman Legion.*
