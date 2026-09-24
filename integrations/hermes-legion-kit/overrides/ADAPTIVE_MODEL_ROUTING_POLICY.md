# Adaptive Model Routing Policy

This concise note records the approved GPT-6 adaptive routing policy for
manual review and operational reference. It is not automatically installed by
the Hermes Legion Kit installer and does not authorize edits to `SOUL.md`,
config, plugins, hooks, or MCP.

## Invariants

- Choose model and reasoning effort independently for every DAG node.
- Model tiers: `gpt-6-luna` with `none`/`low` for exact mechanical work,
  and `medium` for routine bounded implementation. Use `high` for non-trivial
  implementation, review, or raised evidence/risk needs.
  Choose `gpt-6-sol` for coding that requires judgment or an uncertain
  brief; use at least `high` for complex, consequential, or long-horizon work
  and `xhigh` for hard debugging, security, architecture, cross-service
  reasoning, or high ambiguity.
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
- Start routine bounded Luna work at `medium` effort; compare quality, latency, and
  cost on representative tasks. If the scope or proof is unclear, select Sol
  rather than raising Luna's effort to compensate for model choice.
- Eligible low-risk micro work may omit independent review. Meaningful
  non-trivial or medium-risk work requires independent review. High-risk work
  retains specialist gates and Boss approval. The current runner blocks all V3
  dispatch until a trusted approval verifier is available.
- No executor self-approves; Aquila retains final judgment.
- GPT-6 Astra is an explicit, read-only ARCHITECTUS consultation for a named
  architecture trigger; it is never the default implementation or reviewer
  route. Its existing contract uses `executionProfile: advisory`, xhigh or
  higher effort, a read-only sandbox, and no product files. The recorded V2/V3
  floor, independent Opus 5 review, and V3 specialist/Boss gate remain.
- A Codex implementation (Luna or Sol) with a meaningful deterministic-proof
  gap requires the V2 Claude review floor; fully proved low-risk Codex work may
  use V0. V1 Sol remains the terminal reviewer only for non-Codex executors.
- Claude Opus 5 is the principal independent reviewer for the current model
  policy. Corrections return to Luna/Sol in a fresh implementation order.
  Codex remains the implementation default;
  Luna at `medium` is the routine bounded default; Sol handles work requiring
  judgment with the task-appropriate effort floor above.
- Gemini `gemini-3.8-flash` executes bounded UI, design, language, and creative
  work through `agy`. Select the existing specialty (PICTOR, AEDILIS,
  NOMENCLATOR, GLOSSATOR, LUDIFEX, ORATOR, MERCATOR, SCRIBA, TABULARIUS, or
  INTERPRES), pin `--model` and `--effort`, and retain controller acceptance.
  agy supports `low|medium|high`; Codex's larger effort enum does not imply
  Gemini support. The legacy `model: agy` route remains compatibility-only
  and does not establish which model ran. Gemini cannot be terminal reviewer.
- Runtime/launcher evidence overrides stale static summaries. Codex
  personality remains a valid CLI enum; prose does not activate effort. Pass
  the selected model and effort explicitly in the Codex launch command and
  verify the observed runtime model before accepting the result. Routing
  metadata alone is not proof of which model executed.
