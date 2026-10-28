# CENTURION 3.0.0-rc.6

Read [the functional contract](skills/orchestrator/SKILL.md) once for this mission.
It governs team lead, worker and reviewer behavior. The selected surface and
installed-chain receipt determine available instructions; aliases add no authority.
Project/global instructions and configuration conflicts must be reported before
using the affected adapter. Never resolve a conflict by silently editing settings.

Use [proportional proof](PROBATIO.md) for acceptance evidence.

Open Design is archived, not an active route, installable skill or runtime
dependency. Keep general UI/UX and web work with the selected domain skills;
media generation uses available native tools within the approved task. Do not
invoke or reinstall the archived Open Design adapter. Historical evidence is
retained under archive/open-design in the source repository.

## CENTURION policyVersion 3.0 scope

For an explicitly activated CENTURION policyVersion 3.0 mission only, the
installed selected functional contract and controller routing govern launch,
model, effort, verification pairing and result transport. The historical
route/review/direct-dispatch and delegation/custody/launch chapter requirements
above apply to historical or separately requested non-3.0 work. For 3.0, load
the installed orchestrator core and agent-contract-runner adapter where available;
load only selected domain recipes for the assigned task. Legacy chapters cannot
restore a retired route, alternate dispatcher or another controller.

Select the model and its reasoning effort as two separate decisions:

- Task suitability: use `gpt-6-luna` only for routine, mechanical, clearly bounded
  work with `complexity=low`, `risk=low`, `ambiguity=low`, `reversibility=high`
  and `confidence=high`. This includes simple read-only tasks and simple bounded
  implementation. Reading alone does not make a complex analysis a Luna task.
  If any of these controller fields falls outside those values, do not route the
  implementation to Luna; use `gpt-6.1-sol`. This includes `complexity=medium`
  as well as `complexity=high`, material uncertainty, consequential work,
  architecture, security or hard debugging. Approved read-only analysis may use
  Astra only through its separate advisory route.
- Luna's reasoning effort: set `reasoningEffort=high` by default, even for trivial
  tasks; `xhigh` is the only other permitted value. These values describe the
  model's depth of reasoning, not the task's complexity. Raising Luna's effort
  never makes it eligible for a task that requires Sol.
- Example: `complexity=low` plus Luna plus `reasoningEffort=high` is valid for a
  simple mechanical task. `complexity=high` plus Luna plus
  `reasoningEffort=xhigh` is invalid; route engineering work to Sol. The word
  `high` in the effort field does not change the complexity field.

When explaining this policy, say "Luna handles routine, mechanical, low-risk
tasks with reasoning effort high or xhigh." Never describe Luna as reserved
for high- or very-high-complexity tasks. Historical Luna `medium` effort guidance
above does not apply to policyVersion 3.0.

Use `gpt-6-astra` only for read-only advice and `claude-opus-5-5`
for its approved specialist/reviewer role. No unapproved alternate model,
external delegation path or legacy model fallback in new 3.0 dispatch.
The user is the sole source of action authority and chooses the verification
required for the mission. Risk labels and review recommendations do not add a
permission gate. V3's unavailable verifier and automatic specialist gate are
retired; the historical V3 spelling remains readable with V2 review semantics.
An independent review, when selected, must actually be independent. Explain
concrete risks and recommended checks once before an unresolved user decision;
continue within an existing approval without asking again for the same action.
This replaces historical CENTURION V3, specialist and risk-based review floors.
Progress heuristics also warn: repeated reads or lack of new proof cannot kill
an authorized worker or reject otherwise proven work. There is no one-switch
strategy ceiling. Astra advice imposes no verification floor. A historical tool
denial does not establish final product failure; report it and check the outcome.
Only the user extends approved launch/product budgets through recorded continuation;
spent counters, explicit cancellation and actual host permissions remain effective.

Gateway alone launches new 3.0 children and creates outputContract.resultPath
and controller receipts. Workers return the native payload through the selected
adapter and never write the canonical result or call a finalizer. Legacy exact
file-output contracts retain their separate non-3.0 path and grant no 3.0 launch
authority. Gateway process/events observation replaces legacy heartbeat-helper
launch obligations for these children. Missing result formatting never permits
replaying completed product work.

Malformed reporting alone is not a failed product. Follow the functional
contract's report-recovery section: use successive report-only attempts within
the approved budget or collect an explicitly authorized manual-review report.
Every attempt preserves the original evidence and product snapshot. Reporting
does not consume a product correction attempt; user-selected review still applies.

New model work has launch.timeoutSeconds=null and mission budget.deadlineAt=null
unless the owner explicitly requests a finite limit. Observe the owning process
about every 30 seconds; silence or elapsed time does not authorize termination,
retry or a claim of remote model health. Existing finite historical orders and
launch/attempt limits remain unchanged; explicit cancellation and bounded cleanup
remain required. Claude uses the local ANTHROPIC_BASE_URL and exact --model from
the approved route; ANTHROPIC_DEFAULT_OPUS_MODEL is not the order's authority.

All independent user authority, scope, safety, identity, proof, approval and
no-secret/no-hidden-change requirements remain effective. This clause grants no
new permissions or authority outside the user's order and does not activate a
3.0 mission by itself. Host/runtime permissions remain actual technical limits;
current explicit user and higher-priority instructions win.
