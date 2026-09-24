# CENTURION: Позиция Opus по реализации remediation

**Дата:** 2026-09-24
**Автор:** Claude Opus 5
**Проверенный документ:** `docs/REMEDIATION_IMPLEMENTATION_AND_DISAGREEMENTS_2026-09-24.md`
**Базовый план:** `docs/REMEDIATION_PLAN_2026-09-23.md`

## Методология проверки

Прочитал план, реализацию, ключевые модули, запустил регрессии, проверил live состояние установки. Все офлайн-тесты проходят:

```
regression_agent_contract_runner.py: PASS
regression_result_gateway.py: PASS
regression_artifact_lineage.py: 11/11
regression_review_ladder.py: PASS
tests/install-owned-files.test.mjs: 4/4
```

Live состояние: `~/.codex/libs/legion_core.py` совпадает с checkout (14K, безопасный), `~/.claude/libs/legion_core.py` старая версия (4.1K, строка 17: `ssl._create_unverified_context`).

## Пункты, где я НЕ согласен с позицией реализации

### 1. Полный запрет прямого runner для Codex/Claude (пункт разногласий #1 в реализации)

**Позиция реализации:** прямой путь НЕ должен быть запрещён полностью, потому что он создаёт start/closure/terminal receipts через `direct_custody.py`, что обеспечивает достаточный custody контур, и полный запрет сломает существующих клиентов.

**Моя позиция:** **ЧАСТИЧНО СОГЛАСЕН, но рекомендую ужесточить только для lineage**.

Текущее состояние кода правильно блокирует:
- Lineage dispatch через direct runner (строка 1235: `"lineage" in order`)
- Astra advisory через direct runner (строка 1237-1240: `executionProfile == "advisory"`)

Direct custody receipts (`direct_custody.py:77-181`) обеспечивают:
- Start receipt ДО executor launch с хешами order/command
- Closure ПОСЛЕ proof с хешами result/start
- Terminal acceptance с хешами всей цепочки

Это лучше, чем ничего, но Gateway stronger:
- Proof gate в отдельном controller процессе
- Create-only controller-proof.json и controller-acceptance.json
- Artifact lineage с manifest binding
- Loop state control с locked transactions

**Рекомендация:** оставить direct runner для простых заказов без lineage, но **документировать разницу** между direct custody и Gateway custody. Для lineage/advisory Gateway уже обязателен — достаточно.

Блокировка `codex`/`claude` не затронула бы `agy`/`hermes_delegate_task`/`other`, поскольку Gateway их и так не поддерживает (`result_gateway.py:50`). Но она и не нужна: direct custody даёт start/closure/terminal receipts с хешами order/result, чего достаточно для заказов без lineage.

`review_ladder.py:212` УЖЕ содержит проверку:
```python
or metadata["evidenceNeed"] == "high"
```

Регрессия подтверждает, что это влияет на `_minimum_codex_effort`. План требовал именно этого. Реализация корректна.

---

### 2. Отказ переписывать canonical result после провала proof (пункт разногласий #3)

**Позиция реализации:** canonical result не должен переписываться контроллером, controller acceptance отдельно.

**Моя позиция:** **СОГЛАСЕН ПОЛНОСТЬЮ**.

Canonical result — это executor statement. Его перезапись:
- Стирает исходное свидетельство
- Нарушает create-only контракт
- Мешает независимому анализу executor behavior vs controller decision

Gateway правильно создаёт отдельный `controller-acceptance.json` со статусом `passed`/`rejected`. Потребители ОБЯЗАНЫ проверять controller acceptance, а не только `result.status`. Это правильная архитектура.

---

### 3. Отказ добавить executor-owned artifactHash в общий result (пункт разногласий #2)

**Позиция реализации:** executor self-report не доказывает байты, контроллер хеширует сам через artifact_lineage.py.

**Моя позиция:** **СОГЛАСЕН ПОЛНОСТЬЮ**.

Executor может заявить любой хеш. Controller-owned manifest (`artifact_lineage.py:449-805`) доказывает:
- Per-file SHA-256 живых байтов
- Размеры и режимы
- Удалённые файлы через deletion markers
- Связь с order/result/receipts/proof через create-only anchor

Это сильнее, чем `result.artifactHash` от executor. План предлагал добавить `previousOrderId`/`expectedArtifactHash`, но механизм lineage через доверенный anchor digest предыдущей цепочки — правильное решение для controller-owned trust chain.

---

### 4. Обязательность immutable snapshots для lineage (пункт разногласий #3)

**Позиция реализации:** snapshot/изоляция нужны для shared/adversarial среды, но не обязательны для локального same-UID Gateway.

**Моя позиция:** **ЧАСТИЧНО СОГЛАСЕН**.

Для локальной single-UID разработки:
- Controller manifest + trusted predecessor anchor digest + create-only receipts + frozen predecessor verification защищают от случайной подмены
- Race window между preflight и successor read остаётся (линии 710-725)
- Authorship не доказан — manifest показывает, что файл *существует* с таким хешем, но не что его создал *этот executor*

Для production/shared среды immutable snapshot или namespace isolation ОБЯЗАТЕЛЬНЫ. Для локальной разработки — reasonable trade-off, но ограничение должно быть явно документировано.

**Рекомендация:** добавить в `LEGION_CONTRACTS.md` явное предупреждение о границах lineage trust для same-UID и shared environments.

---

### 5. Статус P2-1 (evidenceNeed) как "реализовано"

**Позиция реализации:** P2-1 полностью реализован, `evidenceNeed=high` повышает effort.

**Моя позиция:** **СОГЛАСЕН** — это уже работает.

`review_ladder.py:212` УЖЕ содержит проверку:
```python
or metadata["evidenceNeed"] == "high"
```

Регрессия подтверждает, что это влияет на `_minimum_codex_effort`. План требовал именно этого. Реализация корректна. Это НЕ разногласие.

---

### 6. Статус P1-1 как "частично реализован" vs "blocked"

**Позиция реализации:** P1-1 частично реализован (helper готов, live установка не завершена).

**Моя позиция:** **СОГЛАСЕН с формулировкой "частично"**.

Факты:
- Helper (`install-owned-files.mjs`) реализован, принимает `--agents-home`, `--claude-home`, `--codex-home`
- Офлайн-тесты проходят 4/4, проверяют SHA-256, режимы, откат, foreign file rejection, symlink rejection
- `~/.codex/libs/legion_core.py` совпадает с checkout (безопасный, 14K)
- `~/.claude/libs/legion_core.py` СТАРАЯ версия (4.1K, строка 17: `ssl._create_unverified_context`)
- Полный `install.sh` не запускался

Называть это "blocked" стирает уже проверенный helper. Называть "реализовано" переносит offline proof на live. "Частично" — точная оценка.

**Acceptance критерий:** запустить полный `install.sh`, проверить, что `~/.claude/libs/legion_core.py` обновился, и выполнить negative TLS test.

---

### 7. TLS verification proof через успешный HTTPS запрос (пункт разногласий #4)

**Позиция реализации:** успешный HTTPS не доказывает проверку сертификатов, нужен negative test с недоверенным сертификатом.

**Моя позиция:** **СОГЛАСЕН ПОЛНОСТЬЮ**.

Успешный `urllib.request.urlopen('https://httpbin.org/get')` может пройти и с `CERT_NONE`. Negative test (`install-owned-files.test.mjs` использует локальный self-signed cert и проверяет, что установка отвергает его) — правильный proof.

Однако это offline proof временной установки. Для live `~/.claude` нужен отдельный run после полного install.sh.

---

### 8. Детерминистический failure oracle как обязательный наблюдаемый артефакт (позиция реализации пункт #5)

**Позиция реализации:** `deterministicFailureOracle` остаётся в legacy trustPredicates, отдельного наблюдаемого oracle в контракте нет.

**Моя позиция:** **СОГЛАСЕН с current state, но это остаётся открытым вопросом**.

Текущая реализация:
- `deterministicFailureOracle` в POST_EXECUTION_PREDICATES
- НЕ используется для V0 admission (только PRE predicates)
- Controller proof проверяет фактические proof commands, не oracle assertion

Но контракт не определяет, КАК controller должен проверить "deterministicFailureOracle" независимо от executor claim. Это семантический предикат, а не механическая команда.

Для полной реализации нужен либо:
1. Обязательный артефакт с reproducible test case + expected failure
2. Или удалить это из POST predicates и оставить только в legacy shape

Текущее состояние fail-closed (контроллер проверяет живые proof), но semantic oracle checking не имплементирован.

---

## Пункты, где я СОГЛАСЕН с реализацией

### A. PRE/POST predicates разделены (P2-2)

**Реализация:** `PRE_EXECUTION_PREDICATES` и `POST_EXECUTION_PREDICATES` разделены, V0 использует только PRE.

**Моя позиция:** **ПРАВИЛЬНО**.

`review_ladder.py:52-67` — чёткое разделение. `_all_pre_execution_predicates` (строка 183-188) проверяет только:
- localNarrowBlastRadius
- cheapReversal
- noSensitiveOrExternalSideEffects
- noUncertainty
- noScopeOrAssumptionIssues

POST predicates проверяются контроллером после executor. Это fail-closed architecture.

---

### B. Gateway custody receipts для Codex/Claude (P1-2 частично)

**Реализация:** Gateway создаёт start/closure/controller-acceptance с хешами order/result/receipts.

**Моя позиция:** **ПРАВИЛЬНО для Gateway пути**.

`result_gateway.py:109-138` — atomic create-only receipts с fsync. Verified chain через SHA-256. Это сильный custody контур.

Разногласие только в том, что direct runner всё ещё разрешён для non-advisory заказов.

---

### C. Artifact lineage через controller-owned manifest (P1-3)

**Реализация:** `artifact_lineage.py` хеширует живые файлы, создаёт manifest/anchor, проверяет predecessor anchor digest.

**Моя позиция:** **ПРАВИЛЬНОЕ РЕШЕНИЕ**.

Это сильнее, чем executor self-report. Ограничения (race window, authorship, same-UID bounds) документированы в implementation doc.

---

### D. evidenceNeed влияет на effort (P2-1)

**Реализация:** `review_ladder.py:212` проверяет `evidenceNeed == "high"` и повышает effort до `high`.

**Моя позиция:** **УЖЕ РЕАЛИЗОВАНО, proof complete**.

---

## Дополнительные риски (не в плане, обнаружены при проверке)

Эти пункты реализация НЕ добавила как новый scope, но я их обнаружил:

1. **PathPolicy принимает внешние allowedPaths** (`agent_contract_runner.py:177-193`). Order может разрешить controller читать/писать вне `workspace.repoPath`. Нужна отдельная политика для внешних путей.

2. **loopContract.statePath может быть вне workspace** (`agent_contract_runner.py:686-695`). Проверяется только против forbidden patterns, но не ограничен control namespace. Нужна граница для controller state root.

3. **~/.claude/libs/legion_core.py не обновлён** — это LIVE RISK прямо сейчас. Строка 17: `ssl._create_unverified_context` (4179 байт против безопасных 9085 в checkout). Helper готов и проверен офлайн, но полный install не запускался. **Вне scope текущей работы** — исправление затрагивает локальную систему. Смягчение в проекте: negative TLS test в `tests/install-owned-files.test.mjs` доказывает свойство helper'а, но не состояние live-копии.

---

## Итоговая рекомендация

### Граница scope (решение пользователя, 2026-09-24)

**Работа ведётся только в проекте. Локальная система не трогается.**
Полный `install.sh` и любая правка `~/.claude`, `~/.codex`, `~/.hermes` —
вне scope текущей работы, независимо от того, что это исправляет.
Live-риск ниже остаётся открытым и требует отдельного явного решения.

### Применить в проекте:

1. **Live install НЕ выполняется** — `~/.claude/libs/legion_core.py` остаётся
   старой небезопасной копией по решению выше. Записано как известный
   незакрытый риск, а не как задача к выполнению.
2. **Добавить в `LEGION_CONTRACTS.md` и SKILL.md**:
   - Явные границы lineage trust для same-UID vs shared environments
   - Разницу между direct custody receipts и Gateway custody с controller-owned proof
3. **Задокументировать риски** внешних allowedPaths и внешнего loopContract.statePath

### Документировать как известные ограничения:

4. **Lineage race window** между preflight и successor read
5. **Authorship не доказан** — manifest показывает файл с хешом, но не executor авторство
6. **deterministicFailureOracle** остаётся semantic assertion без independent verification механизма

### Оставить как reasonable trade-offs:

7. **Canonical result не переписывается** — правильная архитектура
8. **Controller хеширует артефакты** вместо executor self-report — правильно
9. **PRE/POST predicates разделены** — правильно

---

## Что применять из реализации

**Применить полностью:**
- P1-1 helper (уже в checkout и проверен офлайн; live install — вне scope,
  отдельное решение пользователя)
- P1-2 Gateway custody (уже реализовано и правильно)
- P1-3 artifact lineage (уже реализовано и правильно)
- P2-1 evidenceNeed (уже реализовано и правильно)
- P2-2 PRE/POST split (уже реализовано и правильно)

**НЕ менять от реализации:**
- Direct runner остаётся для non-lineage non-advisory заказов — текущая блокировка lineage/advisory достаточна
- Canonical result не переписывается — правильная архитектура
- Controller хеширует артефакты вместо executor self-report — правильно

**Документировать явно:**
- Границы lineage trust (race window, authorship, same-UID vs shared)
- Разница direct custody vs Gateway custody
- Риски внешних allowedPaths и statePath
- deterministicFailureOracle остаётся semantic assertion без independent verification

---

*DISCIPLINA ET FIDES*
