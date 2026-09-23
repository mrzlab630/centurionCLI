# Adaptive Model Routing Policy

This concise note records the approved GPT-6 adaptive routing policy for
manual review and operational reference. It is not automatically installed by
the Hermes Legion Kit installer and does not authorize edits to `SOUL.md`,
config, plugins, hooks, or MCP.

## Invariants

- Choose model and reasoning effort independently for every DAG node.
- Model tiers: `gpt-6-luna` with `none`/`low` for exact mechanical work,
  and `medium` for bounded changes with clear requirements, high confidence,
  and deterministic proof. Choose `gpt-6-sol` with `medium` for coding that
  requires judgment or an uncertain brief; use `high` for difficult reasoning.
  High complexity, material ambiguity, cross-service/architecture/security,
  hard debugging, or long-horizon work requires Sol rather than Luna.
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
- Start bounded Luna work at `medium` effort; compare quality, latency, and
  cost on representative tasks. If the scope or proof is unclear, select Sol
  rather than raising Luna's effort to compensate for model choice.
- Eligible low-risk micro work may omit independent review. Meaningful
  non-trivial or medium-risk work requires independent review. High-risk work
  retains specialist gates and Boss approval.
- No executor self-approves; Aquila retains final judgment.
- A Codex implementation (Luna or Sol) with a meaningful deterministic-proof
  gap requires the V2 Claude review floor; fully proved low-risk Codex work may
  use V0. V1 Sol remains the terminal reviewer only for non-Codex executors.
- Claude Opus 5 is a live-proven exact local route and principal
  reviewer/reasoning-heavy executor. Codex remains the implementation default;
  Luna at `medium` is for clear bounded work; Sol at `medium` is the default
  when implementation needs judgment.
- Runtime/launcher evidence overrides stale static summaries. Codex
  personality remains a valid CLI enum; prose does not activate effort. Pass
  the selected model and effort explicitly in the Codex launch command and
  verify the observed runtime model before accepting the result. Routing
  metadata alone is not proof of which model executed.
