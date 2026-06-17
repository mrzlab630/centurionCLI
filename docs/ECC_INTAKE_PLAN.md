# ECC Intake Plan

This plan adapts selected patterns from `https://github.com/affaan-m/ECC` into CENTURION without importing ECC as a runtime, installer, hook pack, MCP pack, or new Legionary set.

## Non-Negotiable Boundary

- Keep one primary Legionary owner per task.
- Strengthen existing Legionaries; do not add ECC agents as new owners.
- Keep durable behavior in `skills/` and integration-specific behavior in the kit edge.
- Store long guidance in `references/` and load it on demand.
- Treat ECC as an idea source until GUARDIAN passes a candidate. Direct bulk install is blocked.

## Current Safety Decision

The local external-skill scanner blocked direct ECC import:

```text
node integrations/claude-legion-kit/scripts/external-skill-scan.mjs /home/mrz/tmp/ecc-review
external-skill-scan: fail
blockers: 29
warnings: 500
```

This does not block manual adaptation of small protocols. It blocks copying or installing the full repo, hooks, MCP configs, installers, auto-update scripts, wallet/payment/trading skills, or broad-permission tooling into active surfaces.

## Surface Strategy

| Surface | Role | Best ECC Pattern Fit | Guard |
| --- | --- | --- | --- |
| Codex | Primary commander, repo maintainer, final integrator | context budget, config GC, AI regression checks, self-debug, session status design | `legion-skill-eval`, `codex-surface-audit`, direct diff/test proof |
| Claude | Controlled deep executor/reviewer through native agents and tool gates | self-debug, eval harness, context budget, workspace audit | `CLAUDE_ORDER_V1`, `claude-order-guard`, `claude-surface-audit` |
| agy | Fast auxiliary executor for bounded UI/content/reference slices | iterative retrieval, validation loop, prompt budget hints, failure capture | `AGY_ORDER_V1`, `agy-order-guard`, Antigravity smoke |

## Pattern Placement

| ECC Pattern | CENTURION Owner | Implementation Shape | Do Not Do |
| --- | --- | --- | --- |
| Context budget | CURATOR | `skills/context-optimizer/references/context-budget.md` plus short pointer | Do not paste long budget tables into `SKILL.md` |
| Config GC | CURATOR + GUARDIAN | same reference, read-only scan and human-confirmed cleanup doctrine | Do not delete or rewrite global configs automatically |
| AI regression testing | TESTER + REVIEWER | `skills/tester/references/ai-regression.md` plus eval smoke pointer | Do not create a separate AI-regression Legionary |
| Agent self-debug | DEBUGGER | `skills/error-handler/references/agent-self-debug.md` plus bounded recovery pointer | Do not use self-debug as proof of feature correctness |
| Iterative retrieval | EXPLORATOR + OPTIO | already present in EXPLORATOR; reuse in delegation briefs | Do not add another search owner |
| Workspace surface audit | CAPABILITIES + CURATOR + GUARDIAN | future read-only report shape in Codex/Claude/Antigravity audits | Do not expose secret values |
| Session adapter | EVOCATUS + OPTIO | future `LEGION_SESSION_V1` after a separate contract smoke | Do not change `LEGION_RESULT_V1` semantics |

## Phased Rollout

### Phase 1: Codex Core Skills

Add compact references and eval checks for CURATOR, TESTER, and DEBUGGER. This phase must not modify Claude/Antigravity runtime behavior.

Required proof:

```bash
node skills/tester/scripts/legion-skill-eval.mjs
node skills/context-optimizer/scripts/skill-surface-audit.mjs
git diff --check
```

### Phase 2: Claude Edge

Add short plugin references or pointers only after Phase 1 is green. Keep `CLAUDE_ORDER_V1` unchanged and continue rejecting missing/malformed `CLAUDE_RESULT.json`.

Required proof:

```bash
cd integrations/claude-legion-kit
npm run smoke
npm run audit:surface
```

### Phase 3: agy / Antigravity Edge

Add prompt-budget and failure-capture language to Antigravity workflows and MCP brief text only after Claude edge remains green. Keep `AGY_ORDER_V1` unchanged.

Required proof:

```bash
cd integrations/antigravity-legion-kit
npm run smoke
npm run legion:eval
agy plugin validate ./agy-plugin
```

### Phase 4: Session Contract

Design `LEGION_SESSION_V1` only after external worker status needs are concrete. Keep it separate from `LEGION_RESULT_V1` and add contract smoke before any surface adopts it.

## Acceptance Criteria

- No new Legionary owner names.
- No duplicate active skill names.
- No drift in canonical `skills/` vs installed active surface after sync.
- All new guidance is progressive-disclosure friendly.
- Existing `AGY_ORDER_V1`, `CLAUDE_ORDER_V1`, and `LEGION_*` contracts keep backward-compatible behavior.
- Every phase has deterministic smoke before commit.
