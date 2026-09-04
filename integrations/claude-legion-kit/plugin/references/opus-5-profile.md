# Claude Opus 5 Profile

Use this reference when routing Claude Code work to Opus 5.

## Strengths To Exploit

- Long-horizon agentic coding and high-autonomy work.
- Large-context synthesis when the controller provides a compact dossier.
- Better instruction following, scope retention, and professional-grade outputs.
- Tool-use workflows, subagent control, and multi-step codebase edits.
- Vision/computer-use style reasoning for frontend and browser verification.
- Security and knowledge-work synthesis when evidence is provided.

## Prompting Defaults

- Keep one owner per task: `--agent <slug>`.
- Use explicit allowed files, non-goals, forbidden patterns, proof commands, and timeout.
- Prefer stdin prompts for long orders so variadic CLI options do not consume the prompt.
- For coding/high-autonomy work, prefer high or xhigh effort when available in the active surface.
- Do not set manual extended thinking budgets for Opus 5; use adaptive thinking/effort controls instead.
- Do not rely on stdout. Accept only guard output, proof commands, and direct artifact inspection.

## Context Discipline

- Do not fill the 1M window by default.
- Build a dossier: objective, constraints, files, specs, changed diff, proof commands, risk ledger.
- Load references on demand. The controller should pass only the reference needed by the current owner.

## Rejection Conditions

- Timeout with partial edits.
- Missing or malformed `<workspace>/.centurion/agents_results/<orderId>/CLAUDE_RESULT.json`.
- Canonical `status=done` without non-empty `proof[].status=pass`, `selfReview.performed=true`, and empty scope/forbidden arrays.
- Any scope drift, extra files, or missing owner handoff.

The default result is canonical `AGENT_RESULT_JSON_V1` with `executor="claude"` and the exact order ID. The former `CLAUDE_ORDER_V1` shape is compatibility-only and requires an explicit `verify --allow-legacy` mode.
