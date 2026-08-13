# CENTURION Open Design Bridge

Proof-first JSON orchestration from CENTURION to Open Design.

The canonical implementation is the shared bridge core behind two thin transports:
JSON CLI for deterministic automation and stdio MCP for interactive agent clients.
A design production run is long-lived, stateful, and artifact-oriented: search
references, create or reuse an OD project, run a selected agent/plugin, inspect the
run, materialize files, validate the HTML, render it in Chrome, and return absolute
paths. Hermes, Claude, and Codex call the same core instead of reimplementing it.

## Contract

Input uses `CENTURION_OD_REQUEST_V1`. Output uses
`CENTURION_OD_RESULT_V1`. JSON schemas live in `schemas/`.

CLI request files/stdin and individual MCP JSONL messages are limited to 1 MiB.
Production requests also bound identifiers, briefs, selected references, active
MCP jobs, project file count, and total materialized bytes. These limits fail
before publishing an accepted bundle. Previous-result and manifest JSON files
are also limited to 1 MiB, reference snippets to 48 KiB, and job receipts to
4 MiB.

Reference discovery uses `CENTURION_REFERENCE_REQUEST_V1` and
`CENTURION_REFERENCE_RESULT_V1`. A successful search returns an absolute
`manifestPath`, SHA-256, source/license policy, attribution URLs, and bounded
snippets for sources that permit adaptation.

## Reference search

```bash
node ./bin/centurion-reference.mjs \
  --request ./examples/reference-search.json \
  --result ./.centurion/design/reference-result.json \
  --pretty
```

The MVP adapters are shadcn/ui, Magic UI, HyperUI, Tabler, and Landbook. The
first four are MIT `import-and-adapt` sources. Landbook is `inspire-only`: keep
its URL and attribution, but do not copy its code, assets, brand, or copy.

Search manifests and fetched snippets live under `.reference-cache/<searchId>`
and expire by TTL. When a design is accepted, the selected manifest and snippets
are copied into the immutable result bundle under `references/`. The accepted
copy no longer contains absolute cache paths and is excluded from TTL cleanup.

The result is `done` only when the artifact was materialized and every enabled
owner-side proof passed. An Open Design run may report `failed` after already
producing a valid artifact; that executor status remains visible under
`executor`, while acceptance is based on the real HTML and screenshot.

## Artifact lifecycle

Every create or revise run is produced under
`CENTURION_DESIGN_ROOT/.staging`. The bridge validates the HTML, renders the
enabled screenshot, and only then atomically renames the staging directory to
the requested immutable output directory. Successful output directories are
never removed by automatic cleanup.

The output target is checked again immediately before promotion. Concurrent
runs using the same output directory cannot replace an accepted non-empty
bundle; one run succeeds and the other returns a failed result.

Failed runs use `cleanup.onFailure`:

- `delete` is the default. It removes only the failed staging directory. A
  failed `create` deletes its newly created Open Design project only when the
  request explicitly sets `cleanup.deleteFailedProject=true`; a failed `revise`
  never deletes the existing project.
- `keep` preserves the staging directory and returns its absolute path in
  `cleanup.preservedPath`.
- `ask` also preserves staging, sets `cleanup.pending=true`, and lets the host
  ask the user whether to keep, trash, or delete it.

At the start of every request, the bridge removes child directories older than
`cleanup.stagingMaxAgeHours` from `.staging` and `.trash`. The default is 24
hours. The result reports the removal counts as `staleStagingRemoved` and
`staleTrashRemoved`. This sweep never examines accepted output directories.

## Setup

The security-hardened storage layer currently requires Linux with a mounted
`/proc/self/fd` and GNU coreutils `mv` supporting `--no-copy` plus
`--update=none-fail`. Publication passes opened directory descriptors to that
command, which uses Linux `renameat2(RENAME_NOREPLACE)` for atomic no-clobber
promotion. Previous-result reads, reference reads, materialization, cleanup,
job receipts, and TTL removal are anchored to opened directory descriptors with
`O_NOFOLLOW`. If that platform contract is absent, the bridge fails closed
instead of falling back to path-only containment checks.

```bash
cd integrations/open-design-bridge
npm install

export CENTURION_OD_ROOT=/path/to/open-design
export CENTURION_BROWSER_BIN=/path/to/google-chrome
export CENTURION_DESIGN_ROOT=$PWD/.centurion/design
```

`CENTURION_OD_ROOT` invokes the checkout's built `apps/daemon/bin/od.mjs`
directly through Node, avoiding package-manager version selection from the
caller's current workspace. Run the Open Design daemon build first if its
`dist/cli.js` is absent.

`CENTURION_OD_COMMAND_JSON` is the most explicit alternative:

```bash
export CENTURION_OD_COMMAND_JSON='["node","/path/to/open-design/apps/daemon/bin/od.mjs"]'
```

The bridge never resolves bare `od`, because Linux and macOS may resolve the
system octal-dump utility instead of Open Design.

## MCP

The dependency-free stdio server exposes:

- `search_design_references`;
- `start_design` (returns immediately with `jobId`);
- `get_design` (returns terminal `resultPath` for later revision);
- `cleanup_design`.

```bash
node ./mcp-server/index.mjs
```

The server keeps job receipts under `CENTURION_OD_JOB_ROOT`, defaulting to
`CENTURION_DESIGN_ROOT/.jobs`. A different client can continue the same project
by passing the terminal `resultPath` as `project.previousResultPath`. Each MCP
server process runs at most four jobs concurrently by default; set
`CENTURION_OD_MAX_CONCURRENT_JOBS` to an integer from 1 to 32 when a reviewed
host needs a different per-process bound.

Browser rendering blocks HTTP(S) requests by default so generated artifacts
cannot add telemetry or depend on remote assets during acceptance. Set
`screenshot.allowNetwork=true` only for an explicitly reviewed design that needs
remote resources.

The bridge accepts only loopback daemon URLs and the `fs:write`/
`prompt:inject` capability set. Output directories and `previousResultPath`
must stay under `CENTURION_DESIGN_ROOT`; this prevents a prose-to-JSON adapter
from turning the bridge into arbitrary filesystem read/write access.

## Create

```bash
node ./bin/centurion-design.mjs \
  --request ./examples/create.json \
  --result ./.centurion/design/.results/clear-day-create.json \
  --pretty
```

The result includes:

- `projectId`, `conversationId`, and `runId` for continuation;
- `artifact.absolutePath` for the implemented HTML;
- `screenshot.absolutePath` for the Chrome render;
- SHA-256 and byte sizes for both;
- deterministic proof entries, executor status, warnings, and errors.
- `orchestrator.client` / `orchestrator.owner` provenance;
- accepted reference evidence when a manifest was attached.

## Revise

`revise` can provide `project.projectId` directly or load identity and defaults
from `project.previousResultPath`:

```bash
node ./bin/centurion-design.mjs \
  --request ./examples/revise.json \
  --result ./.centurion/design/.results/clear-day-revise-1.json \
  --pretty
```

Every revision materializes a new immutable artifact directory while continuing
the same Open Design project. The JSON receipt lives outside that directory,
normally under `CENTURION_DESIGN_ROOT/.results`, so publishing the receipt never
mutates accepted HTML, screenshots, logs, or reference evidence.

## Cleanup

Use `action: "cleanup"` with the prior result path to remove an obsolete bundle
or a failed staging directory:

```bash
node ./bin/centurion-design.mjs \
  --request ./examples/cleanup.json \
  --result ./.centurion/design/results/clear-day-cleanup.json \
  --pretty
```

`cleanup.mode="delete"` removes the local bundle permanently.
`cleanup.mode="trash"` moves it under `CENTURION_DESIGN_ROOT/.trash` for the
configured TTL window. Open Design project deletion is separate and requires
explicit `cleanup.deleteProject=true`.

The cleanup `--result` path must be outside the bundle being removed. This is
required because the CLI writes the cleanup result after deletion. Store
cleanup result JSON in a dedicated results directory as shown above.

Cleanup accepts only canonical absolute paths from a prior bridge result. For an
accepted artifact, `artifact.absolutePath` must equal
`artifact.outputDir/artifact.entry`. For a preserved failed run,
`cleanup.preservedPath` must be a direct child of `.staging`. Adapters should
pass the returned result unchanged instead of synthesizing cleanup paths.
Cleanup rejects symbolic-link targets, and TTL sweeps skip symbolic links.
All bridge filesystem operations also resolve existing ancestors before
materialization, promotion, cleanup, trash moves, and continuation reads. An
in-root path whose parent is a symlink to another location is rejected.

Reference downloads are restricted to source-specific HTTPS origins. Redirects
are revalidated and private, loopback, or link-local DNS results are rejected.
IPv4-mapped IPv6, documentation, benchmark, multicast, transition, and other
reserved address ranges are rejected as well.
Cached snippets and their manifest are SHA-256 verified again immediately before
Open Design staging and before copying evidence into an accepted bundle.

For `cleanup.onFailure="ask"`, the host should inspect
`cleanup.preservedPath`, ask the user, and then submit a separate cleanup
request using the failed result's path. Hermes, Claude, and other adapters should
preserve this JSON exchange instead of deleting files directly.

## Proof

```bash
npm test
npm run smoke
```

The deterministic suite uses a mock OD executable and no provider calls. A live
acceptance run should additionally use a real OD daemon, a detected coding-agent
runtime, and Chrome, then inspect the returned screenshot directly.
