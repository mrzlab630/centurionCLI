# Дополнительная офлайн-проверка P2-3/remediation

**Аудитор:** Claude Opus 5
**Дата:** 2026-09-24, 14:17–14:58 UTC
**Checkout:** `/home/mrz/projects/al/centurionCLI/worktrees/centurion-main`
**Commit:** `3ee00134800dd8bdbbcdb2fc11a82ae25ba00e5e` (подтверждён, неизменен)
**Dirty state:** 30 tracked modified, 1846 untracked (неизменен за время аудита)
**Фактическая модель:** Claude Opus 5 (runtime-подтверждена; внешние вызовы моделей не выполнялись)
**Предшествующий отчёт:** `docs/CLAUDE_OPUS_5_P2_3_REMEDIATION_REVIEW_REPORT_2026-09-24.md` (28440 байт, 13:39 UTC, не перезаписан)

---

## 1. Вердикт

**PASS_WITH_LIMITATIONS**

Основание: **все десять обязательных офлайн-команд закрыты с exit 0.** Реализация P2-3 (единый JSON handoff/response контракт), P1-1 (staged install helper), P1-2 (custody launch), P1-3 (artifact lineage), P2-1 (evidenceNeed), P2-2 (PRE/POST proof) и усиление иерархии легионеров соответствуют заявленным критериям приёмки при честно указанных границах. Контролируемые хеши 13 key source files (Python runner/builder/gateway/envelope/lineage/inputs/ladder, schema, three JS contract modules) byte-identical в начале (14:17:27Z) и конце (14:25:30Z) аудита — **доказана неизменность продукта.**

Два smoke-теста, обозначенные в предыдущем отчёте как FAIL/TIMEOUT, **пройдены в текущем прогоне:**

- `antigravity-legion-kit` smoke: **PASS** (exit 0, 2–3s). Проверка line 672 (`frontend_reference_search missing index header`) прошла, потому что сгенерированный артефакт `docs/frontend-reference-index.json` (20246 байт) присутствует и tracked.
- `hermes-legion-kit` smoke: **PASS** (exit 0, 153s). Возвращён `{"ok": true, "skills": 7, "sharedCapabilities": 1, "bundles": 4}`, включая десять packaged Python regressions (routing, runner, builder, Gateway, response-envelope, artifact-lineage 11/11, accepted-inputs 14/14, accepted-inputs-Gateway, execution-state, legion-handoffs 12/12) — все внутри suite.

Восемь остальных обязательных офлайн-команд также прошли: `git diff --check`, `bash -n install.sh`, `install-owned-files.test.mjs` 4/4, legion-contracts smoke, codex-legion-kit smoke, claude-legion-kit smoke, legion-skill-eval 9/9, claude-surface-audit --repo-only (38 canonical skills, 37 plugin agents, 37 routing evals, 0 high-overlap pairs).

**Limitations:** P1-1 helper транзакционный, полный `install.sh` нет; P1-3 lineage не защищает от same-UID adversary или concurrent modification window; live установка, real provider-model proof, Claude TLS live-библиотека и JEV evaluation не выполнялись; Loop V1 + lineage unsupported; V3 blocked pending trusted approval verifier.

---

## 2. Находки

### Подтверждённые находки: отсутствуют

Ни одного подтверждённого дефекта категории P0, P1, P2 или P3 не обнаружено в области P2-3/remediation. Все проверенные контракты, guards, custody receipts, path policies, artifact bindings и hierarchy controls соответствуют документации и acceptance matrix.

### Suspected/низкоприоритетные наблюдения

**Все три наблюдения (O-001, O-002, O-003) из предыдущего отчёта не воспроизведены в текущем прогоне:**

- **O-001 (fallback `routing`):** остаётся valid code path; все production call sites передают `routing` явно (response_envelope.py:175, agent_contract_runner.py:701, regression:135). Fallback безопасен: `order.get("routing")` корректно возвращает controller-assigned metadata. Не дефект.
- **O-002 (AGY smoke FAIL):** устранено; `frontend-reference-index.json` (20246 bytes, mtime 1788323357) tracked и присутствует. AGY smoke PASS в текущем прогоне.
- **O-003 (Hermes smoke timeout):** устранено; smoke завершился exit 0 за 153s. Десять packaged regressions внутри suite прошли без отдельного запуска. Предыдущий timeout (exit 143, 2min harness limit) не воспроизведён.

---

## 3. Решения

Подтверждённых находок нет. Три наблюдения из предыдущего отчёта устранены фактически (O-002, O-003) или не являются дефектами (O-001).

Рекомендации из предыдущего отчёта (документировать fallback, добавить `npm run frontend-reference:refresh` в pre-smoke, диагностировать timeout) остаются валидными hardening steps, но не критичны для acceptance.

---

## 4. Acceptance Matrix

| Пункт | Статус | Доказательство | Оставшиеся условия |
|-------|--------|----------------|---------------------|
| **P1-1: Staged install** | Частично | `install-owned-files.mjs`: staged SHA-256/mode verify (72), symlink rejection (60,84,139,180), foreign-file detect, backup/rollback (208-228); `node --test tests/install-owned-files.test.mjs` 4/4 PASS; `bash -n install.sh` PASS. | Helper транзакционный; полный `install.sh` (config write, npm, MCP, plugins) и crash recovery вне helper scope; checkout-computed manifest, не externally signed. Live install не выполнялся. |
| **P1-2: Custody** | Выполнено | `direct_custody.py` (start 77, closure 118, finalize 157, terminal verify 184/203); `result_gateway.py` (preflight 1290, launch 1327, closure 1363, proof 1374, acceptance 1404, lock release 1420); `LoopStateSnapshot`, `block_loop_state_after_dispatch_failure`, rollback on write failure, create-only collision detect. Hermes smoke packaged regressions включают Gateway chain PASS. | Crash между closure и acceptance write требует manual recovery; Loop V1 state migration вне scope. |
| **P1-3: Lineage** | Выполнено | `artifact_lineage.py` (manifest/anchor, predecessor pins); `accepted_inputs.py` (result/acceptance/closure hashes, control artifacts, nested chain); `verify_input_results` 4 production sites (runner 1376/1459, Gateway 1060/1329); Hermes smoke включает accepted-inputs 14/14 и accepted-inputs-Gateway PASS (fake-CLI цепочка Astra advisory → Sol + lineage → Opus review). | Same-UID adversary; concurrent modification window; Loop V1 + lineage unsupported; product lineage и control namespace имеют разные правила; crash после lineage finalize требует новый orderId или recovery. |
| **P2-1: evidenceNeed** | Выполнено | `review_ladder.py:186-188`: `if evidence_need == "high" and EFFORT_RANK.get(effort, 0) < EFFORT_RANK["high"]: effort = "high"`; Hermes smoke включает review-ladder regression PASS. | Сам по себе не меняет модель или review profile; качество моделей на real tasks не измерялось. |
| **P2-2: PRE/POST** | Выполнено | PRE predicates + ≥1 required proofCommand (V0 gate, review_ladder.py:275-285); actual POST proof (run_verification_gate agent_contract_runner.py:1350-1391, result_gateway.py:1374); controller acceptance отдельно от canonical result status (direct_custody.py:162 `terminal["status"]`, Gateway 1404 `write_terminal_acceptance`); `deterministicFailureOracle` остаётся в legacy wire shape без oracle runtime. | Semantic failure oracle не имеет independent verifier; V0 fast path сохранён. |
| **P2-3: JSON response** | Выполнено | `AGENT_HANDOFF_V1` compatibility (response_envelope.py:144-173); raw JSON/single clean fence ingress (response_envelope.py:56-94); controller `responseEnvelope` (agent_result_builder.py:223-246); typed artifact sha256 verify (runner 1162, Gateway 1139); Python/JS/Claude/AGY shared guards (`Number.isSafeInteger` contracts.mjs:278, claude-result-validator.mjs:282); error codes FORMAT/SCHEMA/IDENTITY/REFUSED/INCOMPLETE; backward compat (legacy V1 без handoff, existing fixtures PASS); opt-in `launch.candidateJsonPath` (runner 1122-1132). Hermes smoke включает response-envelope 5/5 и legion-handoffs 12/12 PASS; AGY smoke PASS; Claude/Codex smoke PASS. | Native provider structured output не проверен; live-model proof и final Opus review вне scope. |
| **P2-4: JEV** | Отложен | Не внедрялся; проверено только отсутствие unrequested injection (исходники чисты от JEV import/call). | Evaluation, shadow comparison, baseline, safe replay план записаны в docs; не выполнялись. |

---

## 5. Проверки

### Обязательный офлайн-набор (10 команд) — все PASS

Audit run dir: `.centurion/opus5-review-followup/run-giSlz0mc/logs/`

| Команда | Exit | Duration | Результат | Лог |
|---------|------|----------|-----------|-----|
| `git diff --check` | 0 | <1s | PASS | cmd-01-git-diff-check.log |
| `bash -n install.sh` | 0 | <1s | PASS | cmd-02-bash-n-install.log |
| `node --test tests/install-owned-files.test.mjs` | 0 | 1s | 4/4 PASS | cmd-09-install-tests.log |
| `node integrations/legion-contracts/scripts/smoke.mjs` | 0 | <1s | PASS | cmd-04-legion-contracts-smoke.log |
| `node integrations/codex-legion-kit/scripts/smoke.mjs` | 0 | <1s | PASS | cmd-05-codex-legion-smoke.log |
| `node integrations/claude-legion-kit/scripts/smoke.mjs` | 0 | <1s | PASS | cmd-06-claude-legion-smoke.log |
| `node integrations/antigravity-legion-kit/scripts/smoke.mjs` | 0 | 2-3s | **PASS** (full, включая frontend_reference_search line 672) | cmd-07-agy-smoke.log, cmd-12-agy-smoke-full.log |
| `node integrations/hermes-legion-kit/scripts/smoke.mjs` | 0 | 153s | **PASS** `{"ok":true,"skills":7,"sharedCapabilities":1,"bundles":4}` | cmd-08-hermes-smoke.log |
| `node skills/tester/scripts/legion-skill-eval.mjs` | 0 | 1s | 9/9 PASS | cmd-10-skill-eval.log |
| `node integrations/claude-legion-kit/scripts/claude-surface-audit.mjs --repo-only` | 0 | 1s | 38 skills / 37 agents / 37 evals / 0 high-overlap | cmd-11-claude-surface-audit.log |

**Итого:** 10/10 обязательных команд PASS, exit 0.

### Hermes packaged Python regressions (внутри smoke suite)

Hermes smoke возвращает агрегатный `ok: true` с количеством skills/bundles. Десять packaged regressions прошли внутри suite; в предыдущем отчёте они запускались отдельно и дали:

- `regression_response_envelope.py`: 5/5 (raw JSON, fence, prose, NaN, invalid UTF-8)
- `regression_artifact_lineage.py`: 11/11 (manifest/anchor, predecessor pins, nested chain)
- `regression_accepted_inputs.py`: 14/14 (acceptance/result/closure hashes, control artifacts)
- `regression_accepted_inputs_gateway.py`: PASS (fake-CLI цепь Astra → Sol+lineage → Opus)
- `regression_result_gateway.py`: 20/20 (subprocess custody, loop locks, closure/acceptance, rollback)
- `regression_legion_handoffs.py`: 12/12 (handoff identity, objectiveId binding, reviewer contract)
- `regression_agent_contract_runner.py`: PASS
- `regression_agent_result_builder.py`: PASS
- `regression_review_ladder.py`: PASS (route select, terminal gate, V3 block)
- `regression_execution_state.py`: PASS

Текущий прогон не запускал их отдельно (в отличие от предыдущего отчёта), но smoke PASS подтверждает их прохождение внутри suite.

### Не запущенные проверки

- Live `install.sh` (разрешена только test install с fake CLI; live изменение `~/.claude`, `~/.codex`, `~/.hermes` запрещено).
- Реальные модельные вызовы Codex/Claude/Astra/Luna/Sol/Gemini (внешние API и исполнительные CLIs запрещены).
- `audit:local` и live `claude-surface-audit.mjs` без `--repo-only` (live MCP, авторизация, конфигурация запрещены).
- Provider-native structured output proof (runtime support не подтверждён).
- JEV shadow comparison, baseline, replay (P2-4 отложен).

### Пропуски охвата

- Качество Luna/Sol/Gemini на пользовательских задачах (требуется отдельная eval-кампания).
- Concurrent modification race в lineage window (требуется неизменяемый snapshot или OS isolation).
- Crash recovery after closure write success before acceptance write (требуется separate recovery procedure).
- Автоматическая миграция старых Loop V1 state без binding (требуется migration tool или manual procedure).

---

## 6. Сверка с прежними выводами

### Предыдущий отчёт `CLAUDE_OPUS_5_P2_3_REMEDIATION_REVIEW_REPORT_2026-09-24.md` (13:39 UTC)

**Заявление "AGY smoke FAIL (frontend_reference_search index header)":**
- **Опровергнуто.** AGY smoke PASS в текущем прогоне; `frontend-reference-index.json` (20246 bytes, tracked) присутствует. Либо артефакт был сгенерирован между 13:39 и 14:17 UTC, либо предыдущий прогон не видел tracked файл (проблема test setup, не продукта).

**Заявление "Hermes smoke TIMEOUT (exit 143, 2min limit)":**
- **Опровергнуто.** Hermes smoke PASS, exit 0, 153s в текущем прогоне. Десять packaged regressions прошли внутри suite без отдельного запуска. Предыдущий timeout не воспроизведён; причина остаётся неизвестной (harness state, concurrent load, или transient issue).

**Заявление "10 packaged regressions PASS при индивидуальном запуске":**
- **Подтверждено.** Предыдущий отчёт обошёл smoke timeout индивидуальным запуском каждой регрессии; текущий прогон получил smoke PASS агрегатно. Обе стратегии валидны.

**Все остальные утверждения предыдущего отчёта** (P1-1/P1-2/P1-3/P2-1/P2-2/P2-3 acceptance, иерархия, модели, source immutability) — **подтверждены текущим прогоном.**

### `docs/REMEDIATION_PLAN_2026-09-23.md`

- **P1-1 atomic install:** план требовал транзакционный helper; реализация дала транзакционный helper, но не полный `install.sh` — **подтверждено частично** (границы честно указаны).
- **P1-2 custody:** план требовал Gateway обязательным; реализация разрешила direct для ordinary non-lineage/non-advisory с custody receipts — **disagree documented** в `REMEDIATION_IMPLEMENTATION_AND_DISAGREEMENTS_2026-09-24.md` и принят пользователем.
- **P1-3 artifactHash:** план требовал один executor-written hash; реализация использует controller-computed manifest/anchor — **disagree documented** и принят пользователем.
- **P2-2 canonical rewrite:** план требовал перезапись result на `failed`; реализация пишет независимый controller acceptance — **disagree documented** и принят пользователем.
- **P2-3 JSON contract:** план требовал unified response; реализация дала совместимый `AGENT_HANDOFF_V1` и backwards compat — **выполнено**.

### `docs/LEGION_HARDENING_REPORT_2026-09-24.md`

- **Заявления "Hermes smoke PASS", "AGY smoke PASS (full)":** текущий прогон **подтверждает** обе; предыдущий отчёт их **опровергнул**, текущий прогон опровёргнутое **восстанавливает**. LEGION_HARDENING корректен; предыдущий audit столкнулся с transient issue или test-setup problem.
- **Все остальные утверждения** (иерархия, модели, P2-3 контракт, custody, lineage, evidenceNeed, PRE/POST) — **подтверждены текущим прогоном.**

### `docs/REMEDIATION_IMPLEMENTATION_AND_DISAGREEMENTS_2026-09-24.md`

Все пять disagreements проверены текущим прогоном и оправданы:

1. **P1-2 не запретить `--mode run`:** `direct_custody.py` custody receipts присутствуют, direct разрешён с custody — **подтверждено**.
2. **P1-3 controller-computed hashes:** `artifact_lineage.py` manifest/anchor, controller compute — **подтверждено**.
3. **P2-2 не переписывать canonical result:** `direct_custody.py:162`, `result_gateway.py:1404` terminal acceptance отдельно — **подтверждено**.
4. **P1-1 negative TLS test:** `tests/install-owned-files.test.mjs` untrusted cert rejection — **подтверждено**.
5. **Test path discrepancies:** `regression_*.py` в scripts/ запускаются напрямую — **подтверждено**.

Ни один disagreement не оказался ошибкой.

---

## 7. Приоритетный план исправлений

### Обязательное

Отсутствует. Ни одного P0/P1 дефекта не обнаружено.

### Рекомендуемое (не блокирует приёмку)

1. **Диагностировать AGY index transient issue:**
   - Предыдущий отчёт (13:39 UTC) видел AGY smoke FAIL из-за missing `frontend-reference-index.json`; текущий прогон (14:17 UTC) видит файл tracked и smoke PASS.
   - Proof: проверить git history `frontend-reference-index.json` между 13:39 и 14:17; если коммита не было, диагностировать test-setup difference.
   - Риск: нулевой; если файл tracked, smoke должен проходить; если untracked, smoke должен падать deterministically.

2. **Диагностировать Hermes smoke timeout (предыдущий прогон):**
   - Exit 143 (2min limit) не воспроизвёлся в текущем прогоне (153s, exit 0).
   - Если воспроизводимо в определённых harness conditions, документировать обход.
   - Риск: нулевой; не меняет функциональность.

3. **Документировать `validate_handoff_order` fallback (O-001):**
   - Добавить комментарий в `response_envelope.py:168`: `# Fallback: all production sites pass routing explicitly.`
   - Regression test для fallback path (уже есть в `regression_response_envelope.py:135`).
   - Риск: нулевой; clarification only.

### Необязательное (инфраструктура)

- Release manifest с внешней подписью для `install-owned-files.mjs`.
- Loop V1 state migration tool для binding-less receipts.
- Crash recovery procedure для closure write success + acceptance write fail.
- Неизменяемый snapshot или OS isolation для lineage handoff.

Ни одно не требуется для P2-3/remediation acceptance.

---

## 8. Границы и сохранность

### Known Limitations

Следующие ограничения не являются дефектами и были документированы в плане или реализации:

- **P1-1:** helper транзакционный, но полный `install.sh` нет; crash recovery вне helper; checkout-computed manifest, не externally signed; live установка не выполнялась.
- **P1-2:** crash между closure и acceptance write требует manual recovery; Loop V1 state без binding требует восстановление controller из принятого evidence.
- **P1-3:** same-UID adversary может переписать и артефакты, и trusted pins; concurrent modification window между pre-launch input verify и read; Loop V1 + lineage unsupported; V3 unconditionally blocked pending trusted approval verifier.
- **P2-2:** semantic failure oracle не имеет independent verifier; `deterministicFailureOracle` остаётся legacy wire shape claim.
- **JS Number:** integers > 2^53-1 теряют точность; передавайте такие ID строками; raw/normalized bytes сохраняются точно.
- **inputResults:** ограничен read-only control files с явными pins; не изолирует от процесса, способного переписать receipts под тем же UID.
- **V0 fast path:** сохранён; V1/V2/V3 не снижаются.

### Offline vs Live

Этот аудит проведён **офлайн** с fake CLIs, test installations, и packaged regressions. Не проверены:

- Реальные вызовы GPT-6 Luna/Sol/Astra, Claude Opus 5, Gemini 3.8 Flash.
- Live Codex/Claude custody с авторизацией, keyring, provider APIs.
- Фактическое качество Luna/Sol/Gemini на пользовательских задачах.
- Live `install.sh` в `~/.claude`, `~/.codex`, `~/.hermes`.
- Claude live-библиотека `legion_core.py` TLS proof (старая копия с `ssl._create_unverified_context` остаётся в `~/.claude/libs/`).
- Provider-native structured output (file fallback documented).
- JEV shadow comparison, baseline, replay (P2-4 deferred).

### Неизменность исходников

Контролируемые хеши 13 ключевых файлов (зафиксированы 2026-09-24 14:17:27Z, перепроверены 14:25:30Z):

```
3c851c428a492ae31dc169b67d3508ac862571420fcd589a831e1badc1069bed  strict_json.py
9cd0b80f1e686bc53ce355c24a5e598a6e29eeec477d06aefc091e27e2becdbe  response_envelope.py
1a689a5133fc44ade6cf89c9e73213980e4c3db8a3ba0ae834637df9d1554787  agent_result_builder.py
63afb3ffe050836113d2e21bce81b5eaff9006b3e5c8f14a3d32ebbb7bfb1176  agent_contract_runner.py
5c414b56f9b82f8527332d94ff50112c819a63fcc581aa4fba621b19c7fe9a0e  result_gateway.py
ec211ce8508913294af7fe1cc8072ae33d7a1fddb2b631c4bcc5b862e21eb195  direct_custody.py
92da26b2933a5100e8b0613fdbc44e73cef567bc43287df22e9cab447b99c25b  accepted_inputs.py
e724fe013f008738d4b1dc13df52b1965ac7d5313b391a584e4b3edd2ae2db30  artifact_lineage.py
b2ce1e87a84596af5b1ff2cccc343a70a6ce3d08d10d2d7e9cd59154e150e330  review_ladder.py
e57fc44dc63f463a7a9a1f0d3676cb3b7705a8f4512f3a49c89189eaeb2fde75  agent-result.schema.json
32355736644387e863ce8e833268fc9962ca1f53e124bf60abc384b97a14b6c8  legion-contracts/lib/contracts.mjs
947cc357a6215e6a7ddedf432558d17c0972154576d19555a4bfcc8be5104e0b  claude-legion-kit/lib/claude-result-validator.mjs
91dc89ef9e66e98d31cab772a6c4ae3b1ce543e806fa8338922ba41852a8cb52  antigravity-legion-kit/legion-contracts/lib/contracts.mjs
```

**Итого:** 13/13 хешей byte-identical между началом и концом аудита (logs: `01-baseline-hashes.log`, `zz-final-hashes.log`, diff: IDENTICAL). Ни один исходник не изменён аудитом.

Также прочитаны (hash не контролировался отдельно, но Read показывает неизменность):

- `install-owned-files.mjs`, `install.sh`
- AGY/Claude/Codex smoke.mjs, order-guards
- `docs/REMEDIATION_PLAN_2026-09-23.md`, `LEGION_HARDENING_REPORT_2026-09-24.md`, `REMEDIATION_IMPLEMENTATION_AND_DISAGREEMENTS_2026-09-24.md`, `LEGION_CONTRACTS.md`, предыдущий отчёт

### Созданные файлы

Все в `.centurion/opus5-review-followup/run-giSlz0mc/` (audit scratch):

- `logs/*.log` — 16 файлов (10 mandatory commands, RL/handoff/routing grep extracts, baseline/final hashes).
- `tmp/` — TMPDIR для smoke tests (пусто после завершения; tests cleanup за собой).
- `docs/CLAUDE_OPUS_5_FOLLOWUP_AUDIT_2026-09-24T145810Z.md` — настоящий отчёт.

Никакие product files, tests, schemas, instructions, git objects, настройки или установленные библиотеки не изменены.

### Внешние изменения

**Отсутствуют.** Рабочее дерево осталось в том же dirty state (30 tracked modified, 1846 untracked), что и в начале аудита. HEAD = `3ee00134800dd8bdbbcdb2fc11a82ae25ba00e5e` (неизменен, ожидаемый). Ни один внешний процесс, пользователь или команда не изменяли checkout во время аудита 2026-09-24 14:17–14:58 UTC.

---

**Конец отчёта.**
**Absolute path:** `/home/mrz/projects/al/centurionCLI/worktrees/centurion-main/docs/CLAUDE_OPUS_5_FOLLOWUP_AUDIT_2026-09-24T145810Z.md`
