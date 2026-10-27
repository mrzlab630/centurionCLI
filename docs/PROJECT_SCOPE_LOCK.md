# Project scope lock — review scenarios

## Canonical rule and delivery boundary

The normative rule is **Project scope lock and external dependencies** in
[`skills/orchestrator/SKILL.md`](../skills/orchestrator/SKILL.md). Hermes core
adapters point to that rule rather than maintaining separate policy copies.
The core is selected for all client profiles by `LOAD_MAP.core`; the adapters
are selected through `INTEGRATION_MAP.core` for Hermes.

This is an instruction-level scope boundary, not a new runtime scope validator,
result enum, approval mechanism, deployment or capability. No runner, schema,
risk floor or dispatch behavior changes. `BLOCKED_EXTERNAL_DEPENDENCY` describes
the blocker in existing reporting fields; use the current contract's blocked
result/state rather than inventing a new canonical status. Repository delivery
does not prove that installed copies or an existing session loaded the rule.

## Acceptance scenarios

Use this matrix for content review of the canonical rule and both adapter
references. It is a semantic review specification, not an automated agent
benchmark or proof of runtime prevention.

| ID | Situation | Required disposition |
|---|---|---|
| S1 | A product gate requires unavailable Gateway/V3/verifier capability. | Identify the affected product gate with permitted bounded read-only inspection, report the external blocker once, retain existing admission/custody predicates; do not repair the platform. |
| S2 | A reviewed scratch candidate or prepared install/rollback packet already exists. | Preserve it as evidence; do not integrate, re-review for installation, activate, install, rerun, delete or revert it under the product mission. |
| S3 | User says `go`, `do it` or `continue` on the product task. | Continue only the already authorized product objective; no implied maintenance assignment, bootstrap exception or install authority. |
| S4 | The agent proposed platform repair; user gives an ambiguous acknowledgement. | Do not treat it as a separate platform mission. Clarify once only if there is a genuine user-requested scope change; do not repeatedly solicit maintenance authority. |
| S5 | User explicitly assigns a separate bounded platform-maintenance mission. | Name its objective, targets, allowed actions, non-goals, proof and stop conditions; route it separately with its own admission, approvals and independent review. Explicit assignment alone does not waive gates. |
| S6 | The same external blocker appears on another status request. | Give a brief unchanged blocked status; no duplicate investigation, review, maintenance roadmap, authorization-gap packet or approval solicitation. |
| S7 | Another product ledger row exists but has unmet prerequisites, frozen ordering or no remaining attempt. | Do not dispatch it merely to appear productive; keep its constraints. If no independent action is admitted, stop blocked, not complete. |
| S8 | An independent product action is already admitted with satisfied prerequisites and budget. | Continue within its approved scope without making platform repair its prerequisite or asking to expand authority. |
| S9 | New external-resolution or capability evidence is supplied to the mission. | Validate its exact scope/bytes through the existing approved mechanism. Resume only after affected product prerequisites and fresh bounded-order admission pass; insufficient evidence leaves the blocker. |
| S10 | A direct review says `ACCEPT` but formal Gateway closure is missing. | Retain the substantive verdict as evidence; do not fabricate custody, self-approve, lower risk or bypass dispatch. |
| S11 | The proposed platform repair is delegated to a worker, another cwd, scratch copy or parallel task. | Reject the indirect scope expansion; a different executor/path does not change mission ownership. |
| S12 | An explicitly in-scope shared library lies outside the current cwd. | Follow the approved objective and allowed paths, not a blanket directory prohibition. Permitted read-only dependency inspection is not permission to repair external infrastructure. |

## Proportional verification

For this documentation-only change:

- Inspect the complete changed files and matrix against the approved objective;
  require an independent content-bearing review bound to the final commit.
- Run the existing `node --test tests/install-owned-files.test.mjs` and
  `node integrations/hermes-legion-kit/scripts/smoke.mjs --skills-only` to check
  selected instruction packaging in disposable client homes.
- Run `git diff --check <base> <tip>` and audit the exact changed-path allowlist.
  No runner, schema, routing, configuration, installed-client or product writes
  belong to this change.

Installer/smoke success proves packaging assertions only. Matrix review proves
reviewed instruction semantics, not behavioral compliance of all future agents.
Full runtime, live-provider enforcement and local rollout are not claimed.
