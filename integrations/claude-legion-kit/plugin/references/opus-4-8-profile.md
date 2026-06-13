# Claude Opus 4.8 Profile

Use this reference when routing Claude Code work to Opus 4.8.

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
- Do not set manual extended thinking budgets for Opus 4.8; use adaptive thinking/effort controls instead.
- Do not rely on stdout. Accept only guard output, proof commands, and direct artifact inspection.

## Context Discipline

- Do not fill the 1M window by default.
- Build a dossier: objective, constraints, files, specs, changed diff, proof commands, risk ledger.
- Load references on demand. The controller should pass only the reference needed by the current owner.

## Rejection Conditions

- Timeout with partial edits.
- Missing or malformed `CLAUDE_RESULT.json`.
- `status=done` without `proof[].result=passed`.
- Any scope drift, extra files, or missing owner handoff.
