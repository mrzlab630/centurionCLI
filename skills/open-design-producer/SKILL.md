---
name: open-design-producer
description: Produce verified interfaces through the CENTURION Open Design JSON bridge with absolute HTML and screenshot paths. Use for landing pages, dashboards, prototypes, revisions, and cleanup under AEDILIS or PICTOR ownership.
---

# Open Design Producer

Use Open Design as a shared production capability, not as a Legionary owner. Read
`references/role-routing.md` when selecting the owner or adjacent specialists.

## Workflow

1. Route UX architecture, flows, design systems, and visual acceptance to AEDILIS.
   Route creation or revision of HTML/UI artifacts to PICTOR.
2. Write a `CENTURION_OD_REQUEST_V1` JSON request. Use an absolute output
   directory under `CENTURION_DESIGN_ROOT` and enable the Chrome screenshot unless
   the user explicitly excludes visual proof.
3. Run the installed wrapper:

   ```bash
   node scripts/open-design.mjs --request <request.json> --result <result.json> --pretty
   ```

   When invoking from another directory, use the absolute path to this skill's
   script. Run `node scripts/open-design.mjs --print-cli` to diagnose CLI discovery.
4. Parse the returned `CENTURION_OD_RESULT_V1` JSON. Accept `status: done` only
   after inspecting `artifact.absolutePath`, `screenshot.absolutePath`, and every
   proof entry. Return those absolute paths to the user.
5. For revisions, pass the prior `result.json` as
   `project.previousResultPath`; do not recreate project identity manually.

## Artifact Lifecycle

- Remove temporary prompt/request files after the run when they are no longer
  needed. Keep accepted result bundles because they are the user-facing output.
- Use `cleanup.onFailure: delete` for disposable failed attempts, `keep` for a
  deliberate investigation, or `ask` when user judgment is required.
- If a failed result reports `cleanup.pending: true`, preserve it and ask the user
  before issuing a cleanup request.
- Use a separate cleanup request with the prior result path. Never synthesize or
  directly delete bridge-managed paths.
- Set `cleanup.deleteProject: true` only after explicit user consent. Local bundle
  cleanup and Open Design project deletion are separate decisions.

Do not bypass the bridge by invoking a bare `od` command. The system utility with
that name may be selected, and direct invocation would skip validation, screenshot
proof, atomic promotion, and cleanup guards.
