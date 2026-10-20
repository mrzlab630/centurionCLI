# Claude Legion Kit 1.0.0 — CENTURION 3.0.0-rc.2

This native instruction adapter uses the [single functional contract](../../skills/orchestrator/SKILL.md)
and [load map](../codex-legion-kit/scripts/lib/surface-config.mjs).
The kit version changes for the breaking explicit-selection installer API; it is
separate from product acceptance and does not introduce a new order schema.

Claude CLI always uses the owner's local proxy in this project.
`ANTHROPIC_BASE_URL` selects that proxy. Pass it explicitly into the native child
environment, including isolated homes and report-only probes. Select the exact
model with `--model` from the approved controller `routing.model`; report-only
launches use the model pinned in their approved capability receipt. The Gateway
validates the launch model and reported runtime model against the approved route.
`ANTHROPIC_DEFAULT_OPUS_MODEL` configures the `opus` alias for native CLI usage; it is
not required or inherited by Gateway children. The owner's global variable may
remain unchanged. Never silently fall back to the public Anthropic endpoint or
another model. The local proxy requires no password or Anthropic account login.

An interactive shell's `.bashrc` exports are not guaranteed in a service or
noninteractive subprocess. Check the actual child environment without printing
credentials; [proxy-env.sh.example](scripts/proxy-env.sh.example) documents the
required transport variable. The Gateway rejects a missing/nonlocal proxy or a
launch model that differs from the approved route. It does not source
shell startup files or change authentication.

Treat `Not logged in` before any API activity as a launch/configuration failure
to investigate first, not evidence that the local proxy is unavailable or that
the user needs `/login`. Check the inherited route, model, isolated settings and
CLI mode. In the inspected CLI, `--bare` requires `ANTHROPIC_API_KEY` or an explicit
`apiKeyHelper`; proxy-side password-free access does not remove that client-side
check. Do not invent credentials, change global authentication, or remove no-write
restrictions to make a probe pass. A successful native round-trip through the
configured proxy is required before accepting that isolated mode.

The 2026-10-17 native probe succeeded with normal print mode and read-only access
to the existing native `.claude.json` profile. An empty isolated profile failed
before API activity even with both route variables. No new password, key or login
was supplied. For report recovery, `native-profile-readonly` requires a pinned
CLI, bwrap binary, profile, settings and local endpoint in the controller's Q6
receipt. Only scratch is writable; tools/MCP/hooks remain disabled. The native
profile mounts at the isolated `CLAUDE_CONFIG_DIR/.claude.json`; keep HOME and that
directory aligned for this tested mode. Existing native state can supply client
authentication internally; do not describe this as proof that no auth header was
sent. No receipt or source review alone proves the unrun P6 recovery mission.

In native-schema mode Claude may return both `structured_output` and a textual
`result`. The Gateway consumes the preselected structured object. Missing or
invalid structured output remains a protocol failure and never falls back to text.

Install only to an explicitly authorized isolated home:

```bash
node integrations/claude-legion-kit/installer/install.mjs --profile domain --skill coder --claude-home /tmp/centurion-fixture/claude
```

Choose `core`, `domain` or `maintenance`; domain and maintenance require explicit
`--skill` values from the map. There is no automatic full-library installation.
Use `--dry-run` to inspect selection and target paths. Unknown settings/instructions
or a modified owned file are reported as conflicts without changing them. Prior
owned manifests enable transactional upgrade, retirement and rollback. Existing
legacy homes without ownership evidence need a separate reviewed migration.

Read `<native-home>/centurion/installed-chain.json` for every source/installed
hash, selected instruction and adapter evidence. Missing or changed binary/config/
route/adapter capability binding excludes that adapter. Installation runs no live
client CLI, update, dependency sync, external model or automatic MCP registration.
New dispatch remains Gateway-only; native agents are bounded projections. No
copied upstream delegation skills or alternate queues are part of the bundle.

Optional Open Design is explicitly selected as a domain capability and configured
for the requested isolated target. Camofox and document conversion require their
own requested task and proven adapter; they are not automatic MCP installs.
See the [root README](../../README.md) for proof commands and N5/N6 limitations.
