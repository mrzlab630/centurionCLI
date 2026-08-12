# CENTURION — Commander of the AI Legion

<div align="center">

<img src="logo/logo_vexillum.jpg" alt="CENTURION Vexillum" width="300">

![Name](https://img.shields.io/badge/⚔️-CENTURION-gold)
![Version](https://img.shields.io/badge/version-COHORS%20SECUNDA%20v2.4-blue)
![Legionaries](https://img.shields.io/badge/legionaries-37-red)
![MCP](https://img.shields.io/badge/MCP%20servers-7-green)
![Status](https://img.shields.io/badge/status-BATTLE%20TESTED-green)

**A Roman-legion orchestration framework for AI coding agents**

*DISCIPLINA ET FIDES*

</div>

---

## What Is CENTURION?

CENTURION turns a coding agent into a disciplined Roman Legion of specialized
skills. Each Legionary has a role, activation rules, tools, and proof standards.
Cohors Secunda v2.4 keeps one canonical active Legion skill surface in
`~/.agents/skills` and leaves Codex system skills in `~/.codex/skills/.system` to
avoid duplicate skill names and context bloat. It also records the current
sanitized local tooling baseline for Hermes, Codex, Claude Code, and
Antigravity/`agy` without copying secret-bearing home configs into the repo.

### Key Features

- **37 Legionaries** across command, build, product/UX, quality, intel, growth, ops, and Ferrata security cohorts.
- **Canonical skill surface** — Legion skills live in `~/.agents/skills`; duplicate copies are not installed into `~/.codex/skills`.
- **Mission preparation tooling** — OPTIO routes primary and adjacent Legionaries with `mission-prep.mjs`.
- **Context governance** — CURATOR audits active skills for duplicate names, drift, long descriptions, and heavy skill bodies.
- **Eval gate** — TESTER runs a deterministic Legion smoke eval that checks routing, GUARDIAN risk gating, and duplicate-free skill names.
- **MEMORIA v1.2.0** — semantic memory MCP server with local embeddings.
- **PROBATIO doctrine** — every material task requires proof: facts, tests, logs, diffs, scans, or live checks.
- **Antigravity Legion Kit** — portable Google Antigravity IDE and `agy` CLI integration under `integrations/antigravity-legion-kit`.
- **Claude Legion Kit** — native Claude Code plugin, 37 subagents, and `CLAUDE_ORDER v1` guard under `integrations/claude-legion-kit`.
- **Codex Legion Kit** — Codex CLI surface audit and canonical skill sync under `integrations/codex-legion-kit`.
- **Hermes Legion Kit** — Aquila Team Lead skills, the shared Open Design capability, and lean Hermes bundles under `integrations/hermes-legion-kit`.
- **Sanitized local tooling baseline** — current Hermes, Codex, Claude, Antigravity/`agy`, and toolchain settings under `docs/LOCAL_TOOLING_BASELINE.md` and `docs/settings-snapshots/`.
- **Shared Legion JSON contracts** — bounded order/result/review validation under `integrations/legion-contracts`.
- **Open Design production fabric** — curated reference search, proof-first create/revise, async MCP jobs, verified HTML, Chrome screenshots, and cross-client continuation under `integrations/open-design-bridge`.

---

## The Legion

### Core 8

| Legionary | Skill | Role |
| :--- | :--- | :--- |
| **OPTIO** | `/orchestrator` | Commander. Plan, interpret, route tasks. |
| **CODER** | `/coder` | Builder. Production code implementation and focused fixes. |
| **DEBUGGER** | `/error-handler` | Medic. Errors, logs, incidents, data. |
| **EXPLORATOR** | `/researcher` | Scout. Codebase, documentation, web research. |
| **PONTIFEX** | `/pontifex` | Engineer. Docker, CI/CD, PostgreSQL, infra. |
| **TESTER** | `/tester` | QA. Tests, coverage, evals, regression gates. |
| **GUARDIAN** | `/security` | Shield. OWASP, secrets, dependencies, supply chain. |
| **LIBRARIUS** | `/planner` | Scribe. Plans, TODOs, project knowledge. |

### Specialist Cohorts

| Cohort | Legionaries |
| :--- | :--- |
| Command | CAPABILITIES, CURATOR, PRAEMONITOR, SKILL-QUARTERMASTER |
| Build | ARCHITECTUS, ARTIFEX, DOCUMENTER, PICTOR, PRAECO, REFACTORER |
| Product/UX | LUDIFEX, AEDILIS, NOMENCLATOR, GLOSSATOR |
| Quality | CENSOR, REVIEWER |
| Intel | AUGUR, QUAESTOR, TABULARIUS |
| Growth | ALEATOR, INDAGATOR, MERCATOR, ORATOR |
| Ops | EVOCATUS, SIGNIFER |
| Ferrata | VELITES, HARUSPEX, SICARIUS |
| Prompt | INTERPRES (`prompt-engineer`) |

---

## Field Doctrine

### Legion Field Cycle

1. **Praeparatio** — identify needed capability and local skills.
2. **Dispositio** — route by hierarchy: OPTIO, EXPLORATOR, CODER, TESTER, REVIEWER, GUARDIAN, CURATOR.
3. **Actio** — execute in small handoffs with objective, files, proof, and adjacent calls.
4. **Probatio** — verify with tests, logs, scans, source citations, or live checks.
5. **Disciplina** — retain compact lessons without bloating global memory.

### Battle Protocols

| Protocol | Trigger | Purpose |
| :--- | :--- | :--- |
| **VIRTUS** | `Virtus!` or high-risk work | Deep verification mode. |
| **WAR ROOM** | `/war-room "Topic"` | Prosecutor/Advocate/Judge debate. |
| **CENSOR** | `/censor` or review work | Adversarial verification. |
| **PROBATIO** | Always active | Evidence before completion. |
| **CODE MODE** | Repetitive/bulk work | Use deterministic local scripts. |

---

## Skill Surface Tools

Run from a checkout or an installed skill root:

```bash
CENTURION_SKILLS_ROOT="${CENTURION_SKILLS_ROOT:-$PWD/skills}"
node "$CENTURION_SKILLS_ROOT/context-optimizer/scripts/skill-surface-audit.mjs"
node "$CENTURION_SKILLS_ROOT/context-optimizer/scripts/skill-drift-report.mjs"
node "$CENTURION_SKILLS_ROOT/tester/scripts/legion-skill-eval.mjs"
```

Expected active-surface invariants:

```text
duplicateNameCount: 0
driftedDuplicateCount: 0
longDescriptions: [] for non-system skills
```

---

## MEMORIA

Built-in MCP server for persistent semantic memory across conversations.

- **Model:** nomic-embed-text-v1.5 compatible local embeddings.
- **Storage:** JSON persistence with indexed chunks.
- **Tools:** `memory_search`, `memory_store`, `memory_forget`, `memory_list`, `memory_reindex`, `memory_status`.

---

## Antigravity Integration

`integrations/antigravity-legion-kit` preserves the Antigravity-facing CENTURION pack in this repository. It contains IDE rules, workflows, compact skill briefs, an `agy` CLI plugin, a local MCP bridge, catalog refresh scripts, frontend/reference/content catalogs, and the guarded `AUXILIUM AGY` delegation protocol.

Start here:

```bash
cd integrations/antigravity-legion-kit
node ./scripts/smoke.mjs
node ./installer/install.mjs --dry-run
```

See [docs/ANTIGRAVITY_LEGION_KIT.md](docs/ANTIGRAVITY_LEGION_KIT.md) for install, validation, and maintenance rules.

---

## Claude Code Integration

`integrations/claude-legion-kit` preserves the Claude Code-facing CENTURION pack. It contains a native Claude plugin, one entry skill, 37 Legionary subagents, the shared Open Design production capability, a proof-first output style, installer, smoke test, and the guarded `CLAUDE_ORDER v1` protocol for bounded Claude execution.

Start here:

```bash
cd integrations/claude-legion-kit
node ./scripts/smoke.mjs
node ./installer/install.mjs --dry-run
```

See [docs/CLAUDE_LEGION_KIT.md](docs/CLAUDE_LEGION_KIT.md) for local audit findings, install, validation, and maintenance rules.

---

## Hermes Integration

`integrations/hermes-legion-kit` preserves the Hermes/Aquila Team Lead additions. It contains five Aquila skills, the shared Open Design capability, its local stdio MCP, four lean skill bundles, an installer, and an offline smoke check. The kit does not edit `SOUL.md`, enable plugins, alter unrelated MCP servers, or import ECC runtime code.

Start here:

```bash
cd integrations/hermes-legion-kit
npm run smoke
npm run install:dry-run
```

See [docs/HERMES_LEGION_KIT.md](docs/HERMES_LEGION_KIT.md) and [integrations/hermes-legion-kit/README.md](integrations/hermes-legion-kit/README.md) for install, validation, and maintenance rules.

---

## Open Design Production

`skills/open-design-producer` exposes the proof-first Open Design bridge as a
shared capability without creating a 38th Legionary owner. AEDILIS owns UX
briefs and visual acceptance; PICTOR owns create/revise HTML and UI production.
Domain specialists provide platform, copy, localization, marketing, and SEO
constraints, while TESTER, REVIEWER, and GUARDIAN own acceptance gates.

The reference phase uses `CENTURION_REFERENCE_REQUEST_V1` and returns a bounded
manifest from shadcn/ui, Magic UI, HyperUI, Tabler, and Landbook. Production uses
`CENTURION_OD_REQUEST_V1` and returns `CENTURION_OD_RESULT_V1` with absolute HTML,
Chrome screenshot, immutable reference evidence, and continuation paths:

```bash
node skills/open-design-producer/scripts/open-design.mjs \
  --request request.json \
  --result result.json \
  --pretty
```

Hermes, Claude, and Codex installers activate the same skill and stdio MCP using
staged, rollback-safe replacement of their owned targets. A
job can start in Hermes, be revised in Claude, and continue in Codex through the
same durable `project.previousResultPath` under the design results root. Failed staging is deleted, preserved, or held
for user choice according to the request policy. Accepted bundles remain
immutable, and deleting an Open Design project always requires explicit consent.

See [integrations/open-design-bridge/README.md](integrations/open-design-bridge/README.md), [docs/CLAUDE_LEGION_KIT.md](docs/CLAUDE_LEGION_KIT.md), and [docs/HERMES_LEGION_KIT.md](docs/HERMES_LEGION_KIT.md).

---

## Local Tooling Baseline

The repository tracks a sanitized local tooling baseline for operator-facing
settings that affect Hermes/Aquila, Codex CLI, Claude Code, Antigravity/`agy`,
and the basic host toolchain. The baseline is intentionally summary-only: it
documents model/provider shape, local proxy endpoints, installed integration
surfaces, current CLI versions, Camofox/native web settings, and known installed
configuration drift without storing raw home config files, secrets, OAuth data,
permissions allowlists, trusted project lists, or memory contents.

Start with [docs/LOCAL_TOOLING_BASELINE.md](docs/LOCAL_TOOLING_BASELINE.md). The
machine-readable sanitized snapshot is
[docs/settings-snapshots/local-tooling-baseline-2026-07-09.json](docs/settings-snapshots/local-tooling-baseline-2026-07-09.json).

---

## Legion JSON Contracts

`integrations/legion-contracts` provides shared `LEGION_ORDER_V1`, `LEGION_RESULT_V1`, and `LEGION_REVIEW_V1` validators for bounded delegation between Codex, `agy`, Claude, and future executors.

Use JSON only for orders, results, and review artifacts that a controller can validate mechanically. Keep WAR ROOM reasoning, research notes, normal agent discussion, and user-facing summaries in Markdown.

Surface-specific protocols remain in place: Antigravity keeps `AGY_ORDER_V1`, Claude keeps `CLAUDE_ORDER_V1`, and their guards explicitly opt in to legacy result validation while still owning workspace scope checks.

See [docs/LEGION_CONTRACTS.md](docs/LEGION_CONTRACTS.md) for the exact boundary and validation commands.

See [docs/ECC_INTAKE_PLAN.md](docs/ECC_INTAKE_PLAN.md) for the constrained ECC pattern intake plan. It preserves existing Legionary ownership and keeps ECC as a vetted idea source, not an installed runtime pack.

---

## Installation

```bash
git clone https://github.com/mrzlab630/centurionCLI.git
cd centurionCLI
git checkout cohors-secunda
chmod +x install.sh
./install.sh
```

### Prerequisites

- Node.js >= 20
- Claude Code CLI for legacy MCP registration through `claude mcp add`
- Python 3 for Ferrata helper scripts

### API Keys

Set optional keys in your shell profile before running `install.sh`:

```bash
export BRAVE_API_KEY="your_key"
export GITHUB_PERSONAL_ACCESS_TOKEN="ghp_x"
export PERPLEXITY_API_KEY="pplx-x"
```

### What `install.sh` Does

1. Checks prerequisites.
2. Backs up existing Claude configuration.
3. Installs `CLAUDE.md`, doctrine docs, scripts, pipeline templates, and shared libs.
4. Deploys all 37 Legion skills to `~/.agents/skills`.
5. Keeps Codex system skills in `~/.codex/skills/.system` and avoids Legion duplicates in `~/.codex/skills`.
6. Builds MEMORIA and registers MCP servers when possible.
7. Runs the Legion skill eval when installed.

---

## Directory Structure

```text
centurionCLI/
├── CLAUDE.md              # Global Centurion instructions
├── FERRATA.md             # Offensive security doctrine
├── PROBATIO.md            # Proof protocol standards
├── README.md              # This file
├── install.sh             # Installer
├── docs/                  # Operator docs, including Antigravity kit guidance
├── integrations/          # External product integrations: Antigravity, Claude, Codex, Hermes, contracts
├── libs/                  # Shared libraries
├── scripts/               # Utility scripts
├── pipeline/              # Handoff templates
├── mcp-servers/memoria/   # Semantic memory MCP server
├── skills/                # 37 Legionaries plus shared canonical capabilities
└── logo/                  # Branding assets
```

---

## Version History

| Version | Codename | Legionaries | Highlights |
| :--- | :--- | :--- | :--- |
| 1.0 | Cohors Prima | 8 | Core legion, PROBATIO doctrine |
| 1.5 | Cohors Ferrata | 11 | Velites, Haruspex, Sicarius |
| 2.0 | Cohors Secunda | 27 | Full roster, MEMORIA, WAR ROOM, AGMEN |
| **2.1** | **Cohors Secunda** | **37** | **Canonical `.agents` skill surface, specialized Product/UX Legionaries, mission-prep, skill audit/eval, duplicate-name guard** |
| **2.2** | **Cohors Secunda** | **37** | **Sanitized Hermes/Codex/Claude/Antigravity local tooling baselines, HTTP local proxy correction, native web_extract, Camofox autostart, current CLI versions** |
| **2.3** | **Cohors Secunda** | **37** | **Shared Open Design production, JSON bridge, verified HTML/screenshots, Claude and Hermes activation, artifact lifecycle guards** |
| **2.4** | **Cohors Secunda** | **37** | **Curated reference search, async Open Design MCP, immutable reference evidence, and Hermes/Claude/Codex continuation** |

---

<div align="center">

**⚔️ DISCIPLINA ET FIDES**

</div>
