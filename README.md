# CENTURION 3.0.0-rc.5

Release candidate for one team lead, bounded workers and independent findings.
Implementation is not release or pilot acceptance. The lead completes approved
work autonomously within mission state, scope, budget and authority.

Read the [functional contract](skills/orchestrator/SKILL.md),
[implementation plan](docs/CENTURION_3_0_IMPLEMENTATION_PLAN.md) and
[skills/tools decisions](docs/CENTURION_3_0_SKILLS_TOOLS_AUDIT_2026-10-16.md).
Controller routing owns model selection; the user's approved mission selects
verification. The current [user-authority policy](docs/USER_AUTHORITY.md) supersedes
historical review floors in the implementation plan.

Task complexity and reasoning effort are separate fields. In policyVersion 3.0,
Luna handles routine, mechanical, bounded low-complexity work with low risk and
low ambiguity. Its `reasoningEffort` is `high` by default; only `high` and `xhigh`
are permitted, even for trivial tasks. Those effort values describe reasoning
depth, never a requirement for high task complexity. Engineering work that the
controller assigns to Sol cannot use Luna by increasing effort. See the
[explicit routing instructions and examples](CLAUDE.md).

The existing [surface map](integrations/codex-legion-kit/scripts/lib/surface-config.mjs)
is the single source for core, domain/on-demand, maintenance and excluded skills.
Planning and context discipline are incorporated into the one core entrypoint.
Domain recipes do not create agents or new authority. New child dispatch uses
Gateway with AGENT_ORDER_JSON_V1, AGENT_RESULT_JSON_V1 and AGENT_HANDOFF_V1.

Installation requires a client, profile, explicit target homes and, outside core,
explicit skill selection. No home is inferred and no client startup, dependency
sync, update, MCP registration or external model call runs during installation.
For example, in a disposable isolated fixture:

```bash
./install.sh --client codex --profile domain --skill coder --skill researcher \
  --agents-home /tmp/centurion-fixture/agents --codex-home /tmp/centurion-fixture/codex
node integrations/hermes-legion-kit/installer/install.mjs --profile core \
  --hermes-home /tmp/centurion-fixture/hermes
node integrations/claude-legion-kit/installer/install.mjs --profile domain --skill reviewer \
  --claude-home /tmp/centurion-fixture/claude
```

Use `--dry-run` for read-only planning. `--profile maintenance --skill artifex`
selects maintenance instructions only; it does not authorize global skill creation.
Open Design is archived and is not an active installable or routable capability.
The active package retains `aedilis`, `pictor`, `nomenclator`, `tabularius` and
related design and web-development skills. Media generation uses the consumer's
available tools under the approved task; it does not depend on Open Design.
See the [historical archive](archive/open-design/README.md). Camofox, MarkItDown and other
optional adapters stay excluded without requested task and capability evidence.
Broken research CLI adapters, upstream delegation skills and legacy control paths are
not installed. Native/Brave/Context7/Playwright research follows the bounded
[research recipe](skills/researcher/SKILL.md).

Each installation writes `<native-home>/centurion/installed-chain.json` with the
product version, selected surfaces, source/installed file hashes, instruction
candidates and capability status. Generated projections include their rendered
bytes. This is a package readback, not proof of a live runtime loaded chain.
Unknown files/settings, hooks or changed owned instructions cause an explicit
conflict before mutation. They are never silently overwritten. A previous owned
manifest permits transactional upgrade and selection changes, with backups;
legacy homes without ownership evidence require a separately reviewed migration.
Live homes are not a test fixture.

`--capability-record <json>` accepts maintenance evidence bound to client,
binary SHA/version, config SHA, route SHA, adapter version/SHA and their paths.
Changing any binding invalidates that adapter's receipt. Missing evidence excludes
the adapter from dispatch readiness; it does not freeze the core package.
No probe is run on every dispatch and nothing updates automatically.

Malformed reporting can be recovered without rerunning product work. Gateway
supports budgeted report corrections and controller-authorized manual review;
see [report recovery and mission continuation](docs/REPORT_RECOVERY.md).

The user decides which actions and verification are authorized. The system
explains risk and recommends checks; risk labels and defect history cannot veto
the approved verification choice. The automatic V3 verifier/specialist gate is
retired. Historical V3 records remain readable with V2 review semantics. See
[user authority and risk warnings](docs/USER_AUTHORITY.md).
Repeated Claude reads, historical tool denials and no-progress heuristics also
warn without cancelling authorized work or rejecting proven output. Strategy
changes have no fixed one-switch ceiling; recorded owner continuation can extend
launch and per-task product budgets while preserving spent counters and evidence.

Focused offline verification:

```bash
node skills/tester/scripts/legion-skill-eval.mjs
node skills/context-optimizer/scripts/skill-surface-audit.mjs
node skills/context-optimizer/scripts/skill-drift-report.mjs --consumer-root /tmp/centurion-fixture/hermes
node integrations/codex-legion-kit/scripts/smoke.mjs
node integrations/claude-legion-kit/scripts/smoke.mjs
node integrations/hermes-legion-kit/scripts/smoke.mjs --skills-only
```

The default Hermes smoke also runs the packaged Python regressions and remains
an integration gate after W2/W3 are merged. `--skills-only` reports that gate as
unrun. Native binary/schema/permission mode, live no-write correction, visual
capabilities, pilot and independent review remain separate N5/N6/N7/N8 evidence.
The source package is `3.0.0-rc.5`. It includes user-selected verification,
advisory progress warnings, budgeted report recovery, authorized manual report
collection, mission continuation and the Open Design archive. The live rollout
and Gateway canary
acceptance in [the readiness receipt](docs/CENTURION_3_0_READINESS_2026-10-20.md)
apply to `3.0.0-rc.2`, not this release. The rc.5 regression suite exercises local
fixture executors and isolated package installation. Publishing this source
package does not update existing client homes or prove a new live provider run.
Preserve and reconcile locally modified instructions during any later rollout.
Native kit `1.0.0` versions mark the breaking change to explicit selection and conflict-first install;
the canonical JSON contract version remains V1.
