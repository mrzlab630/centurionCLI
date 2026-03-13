# ⚔️ CENTURION — Commander of the AI Legion

<div align="center">

<img src="logo/logo_vexillum.jpg" alt="CENTURION Vexillum" width="300">

![Name](https://img.shields.io/badge/⚔️-CENTURION-gold)
![Version](https://img.shields.io/badge/version-COHORS%20SECUNDA-blue)
![Legionaries](https://img.shields.io/badge/legionaries-27-red)
![MCP](https://img.shields.io/badge/MCP%20servers-7-green)
![Status](https://img.shields.io/badge/status-BATTLE%20TESTED-green)

**The Autonomous AI Orchestration Framework for Claude Code**

*DISCIPLINA ET FIDES*

</div>

---

## What is CENTURION?

CENTURION transforms Claude Code into a disciplined **Roman Legion** of 27 specialized AI agents.
Each legionary has a defined role, tools, references, and institutional memory.
The framework includes protocols for quality assurance, adversarial verification, and multi-agent coordination.

### Key Features

- **27 Legionaries** across 7 categories (Core, Build, Quality, Intel, Growth, Ops, Ferrata)
- **MEMORIA v1.2.0** — Semantic memory MCP server with local embeddings (nomic-embed-text-v1.5)
- **7 MCP Servers** — memoria, context7, brave-search, playwright, sequential-thinking, solanaMcp, github
- **Battle Protocols** — VIRTUS (deep analysis), WAR ROOM (3-position debate), CENSOR (adversarial verification), AGMEN (multi-agent coordination)
- **PROBATIO Doctrine** — Every task requires proof: Recon → Action → Verify → Report

---

## The Legion (27 Legionaries)

### Core 8 (Elite)
| Legionary | Skill | Role |
|:---|:---|:---|
| **OPTIO** | `/orchestrator` | Commander. Plan, interpret, route tasks. |
| **CODER** | `/coder` | Builder. Code, refactor, docs, API design. |
| **DEBUGGER** | `/error-handler` | Medic. Fix bugs, analyze logs, incident response. |
| **EXPLORATOR** | `/researcher` | Scout. Perplexity Deep Search + GitHub MCP + Playwright. |
| **PONTIFEX** | `/pontifex` | Engineer. Docker, CI/CD, PostgreSQL, infrastructure. |
| **TESTER** | `/tester` | QA. Unit, integration, E2E tests, coverage. |
| **GUARDIAN** | `/security` | Shield. OWASP, deps audit, secrets scan. |
| **LIBRARIUS** | `/planner` | Scribe. Plan, decompose tasks, manage knowledge. |

### Build 3
| Legionary | Skill | Role |
|:---|:---|:---|
| **ARTIFEX** | `/artifex` | Forge. Create skills, MCP servers, CLI tools. |
| **PICTOR** | `/pictor` | Frontend. React/Vue/Svelte/Next.js/Tailwind/CSS. |
| **PRAECO** | `/praeco` | Telegram. grammY, Bot API, Mini Apps. |

### Quality 3
| Legionary | Skill | Role |
|:---|:---|:---|
| **CENSOR** | `/censor` | Tribunal. Adversarial verification, Red/Blue debate. |
| **REVIEWER** | `/reviewer` | Auditor. Code review, zero-trust, phased analysis. |
| **AEDILIS** | `/aedilis` | Architect. UI/UX design, accessibility, design systems. |

### Intel 4
| Legionary | Skill | Role |
|:---|:---|:---|
| **AUGUR** | `/augur` | Oracle. Combat intelligence, data analysis, WAR ROOM. |
| **QUAESTOR** | `/quaestor` | Analyst. Crypto markets, TA, on-chain, scam detection. |
| **TABULARIUS** | `/tabularius` | Publisher. Format reports, publish to TinyNotepad. |
| **CURATOR** | `/context-optimizer` | Optimizer. Context window management, token reduction. |

### Growth 4
| Legionary | Skill | Role |
|:---|:---|:---|
| **MERCATOR** | `/mercator` | Strategist. Marketing, campaigns, positioning. |
| **ORATOR** | `/orator` | Speaker. Social media content, platform optimization. |
| **INDAGATOR** | `/indagator` | Tracker. SEO, GEO/AEO, schema markup, keywords. |
| **ALEATOR** | `/aleator` | Gambler. Gamification, behavioral psychology, rewards. |

### Ops 2
| Legionary | Skill | Role |
|:---|:---|:---|
| **EVOCATUS** | `/evocate` | Veteran. Delegate to external AI models via tmux. |
| **SIGNIFER** | `/git-master` | Standard Bearer. Git commits, branches, PRs, conflicts. |

### Cohors Ferrata 3 (Offensive Security)
| Legionary | Skill | Role |
|:---|:---|:---|
| **VELITES** | `/velites` | Eyes. Port scanning, HTTP headers, attack surface. |
| **HARUSPEX** | `/haruspex` | Brain. Static analysis (SAST), vulnerability patterns. |
| **SICARIUS** | `/sicarius` | Hands. Exploit verification via Playwright (DAST). |

---

## Battle Protocols

| Protocol | Trigger | Purpose |
|:---|:---|:---|
| **VIRTUS** | `Virtus!` | Deep analysis mode. Zero laziness, full reasoning, fact-checking. |
| **WAR ROOM** | `/war-room "Topic"` | 3-position debate (Prosecutor/Advocate/Judge) → Verdict. |
| **CENSOR** | `/censor` | 5-phase adversarial verification tribunal. |
| **AGMEN** | `Agmen!` | Multi-legionary coordination with structured handoffs. |
| **PROBATIO** | Always active | Every task must be verified with proof. |
| **TABULARIUS** | Auto / manual | Large outputs formatted as HTML reports, published to TinyNotepad. |
| **INCIDENT** | System failure | P0-P3 severity assessment, DEBUGGER runbooks. |

---

## MEMORIA — Semantic Memory

Built-in MCP server for persistent, semantic memory across conversations.

- **Model:** nomic-embed-text-v1.5 (local ONNX, 384 dimensions)
- **Storage:** INT8 quantized embeddings, JSON persistence
- **Features:** Recency boost, stale penalty, context expansion, batch inference, auto-reindex
- **Tools:** `memory_search`, `memory_store`, `memory_forget`, `memory_list`, `memory_reindex`, `memory_status`

---

## Installation

### Quick Install

```bash
git clone https://github.com/mrzlab630/centurionCLI.git
cd centurionCLI
git checkout cohors-secunda
chmod +x install.sh
./install.sh
```

### Prerequisites

- **Node.js** >= 20
- **Claude Code CLI** ([install](https://github.com/anthropics/claude-code))
- **Python 3** (optional, for Cohors Ferrata security scripts)

### API Keys

Set these in your shell profile (`~/.bashrc` or `~/.zshrc`):

```bash
export BRAVE_API_KEY="your_key"              # Brave Search (EXPLORATOR)
export GITHUB_PERSONAL_ACCESS_TOKEN="ghp_x"  # GitHub MCP
export PERPLEXITY_API_KEY="pplx-x"           # Perplexity (EXPLORATOR)
```

Re-run `./install.sh` after setting keys to register MCP servers that require them.

See `.env.example` for the complete list.

### What install.sh does

1. Checks prerequisites (node >= 20, claude CLI)
2. Backs up existing `~/.claude/` configuration
3. Copies `CLAUDE.md` (global instructions) and doctrine files
4. Deploys all 27 legionary skills with references and tools
5. Builds MEMORIA MCP server (`npm install && npm run build`)
6. Registers 7 MCP servers via `claude mcp add`
7. Verifies installation

---

## Directory Structure

```
centurionCLI/
├── CLAUDE.md              # Global instructions (27 legionaries, protocols)
├── FERRATA.md             # Offensive security doctrine
├── PROBATIO.md            # Proof protocol standards
├── README.md              # This file
├── install.sh             # One-command installer
├── .env.example           # API key template
├── settings.json.example  # Claude Code settings template
├── claude.json.example    # MCP server config template
├── libs/                  # Shared libraries
│   └── legion_core.py     # Python foundation for Ferrata tools
├── scripts/               # Utility scripts
│   └── evocate.sh         # Multi-model delegation
├── pipeline/              # Agmen protocol templates
│   ├── TEMPLATE-active.md
│   └── TEMPLATE-handoff.md
├── mcp-servers/
│   └── memoria/           # Semantic memory MCP server (v1.2.0)
│       ├── package.json
│       ├── tsconfig.json
│       └── src/           # TypeScript source
├── skills/                # 27 legionary modules
│   ├── orchestrator/      # OPTIO
│   ├── coder/             # CODER
│   ├── ...                # (25 more)
│   └── sicarius/          # SICARIUS
└── logo/                  # Branding assets
```

---

## Version History

| Version | Codename | Legionaries | Highlights |
|:---|:---|:---|:---|
| 1.0 | Cohors Prima | 8 | Core legion, PROBATIO doctrine |
| 1.5 | Cohors Ferrata | 11 | Security elite (Velites, Haruspex, Sicarius) |
| **2.0** | **Cohors Secunda** | **27** | **Full roster, MEMORIA, 7 MCP servers, WAR ROOM, AGMEN** |

---

<div align="center">

*Built with the precision of a Roman Legion.*

**⚔️ DISCIPLINA ET FIDES**

</div>
