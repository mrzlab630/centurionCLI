# CENTURION Open Design Bridge

Proof-first JSON orchestration from CENTURION to Open Design.

The canonical surface is a CLI, not MCP. A design production run is long-lived,
stateful, and artifact-oriented: create or reuse an OD project, run a selected
agent/plugin, inspect the run, materialize files, validate the HTML, render it in
Chrome, and return absolute paths. MCP adapters for Hermes, Claude, Codex, or
Antigravity should call this CLI/core instead of reimplementing that workflow.

## Contract

Input uses `CENTURION_OD_REQUEST_V1`. Output uses
`CENTURION_OD_RESULT_V1`. JSON schemas live in `schemas/`.

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

- `delete` is the default. It removes the failed staging directory. For a
  failed `create`, it also deletes the newly created Open Design project unless
  `cleanup.deleteFailedProject=false`; a failed `revise` never deletes the
  existing project.
- `keep` preserves the staging directory and returns its absolute path in
  `cleanup.preservedPath`.
- `ask` also preserves staging, sets `cleanup.pending=true`, and lets the host
  ask the user whether to keep, trash, or delete it.

At the start of every request, the bridge removes child directories older than
`cleanup.stagingMaxAgeHours` from `.staging` and `.trash`. The default is 24
hours. The result reports the removal counts as `staleStagingRemoved` and
`staleTrashRemoved`. This sweep never examines accepted output directories.

## Setup

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
  --result ./.centurion/design/clear-day-create/result.json \
  --pretty
```

The result includes:

- `projectId`, `conversationId`, and `runId` for continuation;
- `artifact.absolutePath` for the implemented HTML;
- `screenshot.absolutePath` for the Chrome render;
- SHA-256 and byte sizes for both;
- deterministic proof entries, executor status, warnings, and errors.

## Revise

`revise` can provide `project.projectId` directly or load identity and defaults
from `project.previousResultPath`:

```bash
node ./bin/centurion-design.mjs \
  --request ./examples/revise.json \
  --result ./.centurion/design/clear-day-revise-1/result.json \
  --pretty
```

Every revision materializes a new immutable result directory while continuing
the same Open Design project. This keeps before/after screenshots and HTML
available for owner review.

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
