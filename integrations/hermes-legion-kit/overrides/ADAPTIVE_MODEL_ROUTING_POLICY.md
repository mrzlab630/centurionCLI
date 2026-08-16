# Adaptive Model Routing Policy

This concise note records the approved GPT-5.6 adaptive routing policy for
manual review and operational reference. It is not automatically installed by
the Hermes Legion Kit installer and does not authorize edits to `SOUL.md`,
config, plugins, hooks, or MCP.

## Invariants

- Choose model and reasoning effort independently for every DAG node.
- Model tiers: `gpt-5.6-luna` for mechanical/read-only/high-volume
  low-complexity work; `gpt-5.6-terra` as the routine bounded implementation
  default; `gpt-5.6-sol` for high complexity, material ambiguity,
  cross-service/architecture/security, hard debugging, or long-horizon
  reasoning.
- The effort enum is exactly `none|low|medium|high|xhigh|max`.
- `none` is only exact extraction, classification, or format conversion with no
  material judgment, low risk, and deterministic proof. `low` is mechanical
  micro/simple retrieval. `medium` is routine bounded implementation. `high`
  is non-trivial implementation or review. `xhigh` is hard debugging,
  security, architecture, high ambiguity, or cross-service reasoning. `max` is
  only the hardest quality-first work after runtime support is proven and cost
  justified.
- Risk, ambiguity, reversibility, and evidence need can raise but never lower
  routing or effort floors.
- Eligible low-risk micro work may omit independent review. Meaningful
  non-trivial or medium-risk work requires independent review. High-risk work
  retains specialist gates and Boss approval.
- No executor self-approves; Aquila retains final judgment.
- Claude Opus 5 is a live-proven exact local route and principal
  reviewer/reasoning-heavy executor. Codex remains the implementation default;
  Terra, not Sol, is the routine bounded implementation default.
- Runtime/launcher evidence overrides stale static summaries. Codex
  personality remains a valid CLI enum; prose does not activate effort.
