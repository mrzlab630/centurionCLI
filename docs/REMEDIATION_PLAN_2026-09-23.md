# CENTURION: План устранения рисков — 2026-09-23

**Назначение:** Исполняемое задание для устранения подтверждённых P1/P2 рисков после независимого аудита.
**Базовый коммит:** `3ee00134800dd8bdbbcdb2fc11a82ae25ba00e5e`
**Checkout:** `/home/mrz/projects/al/centurionCLI/worktrees/centurion-main`
**Язык:** Русский (отвечай по-русски)

---

## Приоритеты и границы

### Финальный выпуск 2.6

Пользователь разрешил финальную проверку, commit, merge, push и затем локальную
установку. Финальный статус проверок и границы доказательства зафиксированы в
`RELEASE_2_6_FINAL_CHECK.md`. Таблица ниже сохраняет состояние до независимого
Opus review; она не является новым требованием повторять цикл аудитов.
P2-4/JEV по-прежнему отложен.

### Действующая трактовка на 2026-09-24

Ниже сохранены исходные проблемы и варианты аудита. Спорные варианты заменены
решениями `CLAUDE_OPUS_DISAGREEMENTS_2026-09-24.md`:

- P1-1: repository helper и изолированная проверка; live install/TLS после
  установки выполняются только по отдельной команде пользователя.
- P1-2: direct custody допустим для обычных non-lineage/non-advisory заказов;
  Gateway обязателен для lineage/Astra advisory. Полного запрета direct нет.
- P1-3: controller-owned product manifest/anchor плюс `inputResults` для
  принятых control-артефактов. Self-reported `artifactHash` не является proof.
- P2-2: провал proof означает controller acceptance `rejected`; canonical
  executor result остаётся create-only. `deterministicFailureOracle` сохранён
  только как legacy semantic claim, исключён из наблюдаемых POST predicates.
- P2-3: совместимый V1 handoff и ingress-нормализация в исходниках проекта.
  Финальное review Claude Opus 5 проводит пользователь.
- P2-4: отложен до обсуждения после review. JEV не внедрять.

Acceptance оценивается по этой трактовке; исходные альтернативы ниже
не являются дополнительными требованиями на реализацию.

- **Не коммитить**, не устанавливать и не деплоить без явного разрешения.
- Каждое исправление — отдельный bounded change с регрессией и независимым review.
- Proof до принятия: регрессия прошла, офлайн-проверка успешна, review подтвердил.
- Реальные внешние Codex/Claude-вызовы и продакшн Gateway receipts остаются вне охвата этого задания.

---

## P1-1: Staged install с проверкой хешей и TLS

### Проблема

`~/.agents/skills/velites/scripts/recon.py` отстаёт от checkout (2295 байт vs 3116 байт, разные MD5).
`~/.codex/libs/legion_core.py` строки 13, 17 устанавливают `ssl._create_unverified_context` как HTTPS-дефолт — небезопасно.

### Ожидаемое поведение

Установщик должен:
1. Создавать staged копию в временном каталоге.
2. Копировать файлы и проверять хеши против манифеста.
3. Проверять режимы файлов (0644 для `.py`, 0755 для исполняемых скриптов).
4. Атомарно переключать установленную копию (rename/symlink).
5. Сохранять резервную копию предыдущей версии для отката.
6. После установки проверять TLS: `openssl s_client -connect <test-endpoint>:443` должен показывать валидный сертификат.

### Целевые файлы

- `install.sh` — строки 119–125 (копирование `libs/*.py`), вся логика установки навыков.
- Создать `scripts/install-staged.sh` или усилить существующий `install.sh` флагом `--staged`.

### Proof требования

1. **Регрессия:** `bash -n install.sh` exit 0.
2. **Офлайн-проверка:** Создать тестовый временный каталог, запустить staged install, проверить хеши установленных файлов против исходников.
3. **TLS-проверка:** После реальной установки (с явным разрешением пользователя) — `python3 -c "import urllib.request; urllib.request.urlopen('https://httpbin.org/get')"` не должен падать на TLS-ошибку.
4. **Review:** Независимый агент (GUARDIAN/REVIEWER) подтверждает: откат работает, хеши проверяются, небезопасный `ssl._create_unverified_context` не копируется.

### Acceptance

- [x] Repository helper создаёт staged-копии, проверяет хеши и атомарно переключает каждую управляемую цель; весь install.sh не является одной транзакцией.
- [x] Резервные копии и откат helper проверены на изолированных тестовых целях.
- [ ] TLS-проверка прошла после установки.
- [x] Регрессия helper, negative TLS в тестовой установке и `bash -n install.sh` прошли.
- [ ] Финальное review пользователя через Opus принято.

---

## P1-2: Gateway custody для всех внешних диспетчеризаций

### Проблема

`agent_contract_runner.py:1129–1132` отвергает прямой `--mode run` только для Astra advisory:

```python
if args.mode == "run" and not args.validate_only and order["executor"] == "codex":
    routing = validate_order_routing(order)
    if routing is not None and routing["executionProfile"] == "advisory":
        raise RunnerError("Astra advisory dispatch requires result_gateway.py custody receipts")
```

Для других Codex/Claude-заказов прямой путь остаётся (`SKILL.md:78`). Это минует start/closure receipts Result Gateway.

### Ожидаемое поведение

Все внешние Codex/Claude-диспетчеризации должны требовать Gateway start/closure receipts либо предоставлять эквивалентный контрольный путь с проверяемыми хешами состояния.

### Целевые файлы

- `integrations/hermes-legion-kit/skills/autonomous-ai-agents/agent-contract-runner/scripts/agent_contract_runner.py` — строки 1129–1132.
- `integrations/hermes-legion-kit/skills/autonomous-ai-agents/agent-contract-runner/SKILL.md` — строка 78.

### Варианты исправления

**Вариант А (строгий):** Расширить условие строки 1129:

```python
if args.mode == "run" and not args.validate_only and order["executor"] in {"codex", "claude"}:
    raise RunnerError("External executor dispatch requires result_gateway.py custody receipts")
```

**Вариант Б (гибкий):** Добавить флаг `--allow-direct-dispatch` для явного разрешения прямого пути; без флага требовать Gateway receipts.

**Вариант В (proof-path):** Для прямого пути без Gateway требовать альтернативный контрольный артефакт с проверяемыми хешами order/result; добавить `run_direct_proof_gate` перед `executor_ran = True`.

### Proof требования

1. **Регрессия:** Создать тестовый non-advisory Codex order JSON, запустить `python3 agent_contract_runner.py --order test.json --mode run --events e.jsonl --result r.json`. Ожидаемый результат: `RunnerError` или альтернативная proof-gate.
2. **Офлайн-проверка:** `python3 -m unittest integrations/hermes-legion-kit/skills/autonomous-ai-agents/agent-contract-runner/scripts/regression_agent_contract_runner.py` exit 0.
3. **Review:** Независимый агент (REVIEWER/GUARDIAN) подтверждает: прямой путь закрыт или защищён эквивалентным proof.

### Acceptance

- [x] Non-advisory Codex/Claude direct order имеет start/closure/terminal custody и controller proof.
- [x] Регрессия direct runner и Gateway прошла.
- [x] SKILL.md описывает оба custody-уровня; lineage/advisory требуют Gateway.
- [ ] Финальное review пользователя через Opus принято.

---

## P1-3: Межзаказная проверка артефактов и manifest

### Проблема

`agent-contract-runner/SKILL.md:47–50` указывает: «runner пока не проверяет межзаказные ID, хеши и frozen manifest для цепочки advisory → implementation → review → closure».

### Ожидаемое поведение

При цепочке связанных заказов:
1. Advisory заказ фиксирует хеш артефакта и manifest в своём результате.
2. Implementation заказ принимает `previousOrderId` и `expectedArtifactHash`; проверяет, что входной артефакт соответствует хешу.
3. Review заказ проверяет хеш артефакта implementation перед анализом.
4. Closure проверяет хеши всей цепочки перед окончательным принятием.

### Целевые файлы

- `integrations/hermes-legion-kit/skills/autonomous-ai-agents/agent-contract-runner/scripts/agent_contract_runner.py` — функция `validate_order` (добавить проверку `previousOrderId` и `expectedArtifactHash`).
- `integrations/hermes-legion-kit/skills/autonomous-ai-agents/agent-contract-runner/scripts/agent_result_builder.py` — добавить `artifactHash` в результат.
- `docs/LEGION_CONTRACTS.md` — обновить `AGENT_ORDER_JSON_V1` и `AGENT_RESULT_JSON_V1` схемы.

### Варианты исправления

**Вариант А (минимальный):** Добавить опциональные поля `previousOrderId` (string) и `expectedArtifactHash` (string) в `AGENT_ORDER_JSON_V1`. Если присутствуют, `validate_order` проверяет, что результат предыдущего заказа содержит `artifactHash`, совпадающий с `expectedArtifactHash`.

**Вариант Б (полный):** Добавить `chainManifest` (массив `{orderId, artifactHash, timestamp}`) в order и result. Каждый заказ в цепи добавляет свою запись; следующий заказ проверяет полноту цепи.

### Proof требования

1. **Регрессия:** Создать два связанных order JSON: `order1.json` с `orderId=adv-1`, `order2.json` с `previousOrderId=adv-1` и `expectedArtifactHash=<wrong-hash>`. Запустить `validate_order(order2)` → ожидается `RunnerError("Artifact hash mismatch")`.
2. **Офлайн-проверка:** Добавить новый тест `test_chain_artifact_hash_validation` в `tests/test_agent_contract_runner.py`.
3. **Review:** Независимый агент (REVIEWER) подтверждает: подмена артефакта блокируется, полнота цепи проверяется.

### Acceptance

- [x] Вместо self-reported predecessor полей используются `lineage` manifest/anchor и точные `inputResults` pins.
- [x] Controller проверяет хеш входа и predecessor acceptance до запуска и после proof.
- [x] Controller связывает order/result/receipts и живые байты; canonical результат не переписывается.
- [x] Неверный хеш отклоняется; fake-CLI Gateway цепочка Astra advisory -> Sol implementation -> Opus review проходит.
- [ ] Финальное review пользователя через Opus принято.

---

## P2-1: Влияние evidenceNeed на маршрут

### Проблема

`ADAPTIVE_MODEL_ROUTING_POLICY.md:28–29` указывает: «Risk, ambiguity, reversibility, and evidence need can raise but never lower».
`review_ladder.py:334–336` валидирует `evidenceNeed` как `low`/`medium`/`high`, но не использует его в `_requires_sol` (строки 168–176), `_minimum_codex_effort` (строки 178–197) или `minimum_profile` (строки 199–215).

Тест показал: `evidenceNeed=low` и `evidenceNeed=high` при одинаковых низкорисковых метаданных дали одинаковый результат `V2 | requires_sol=False | min_effort=medium`.

### Ожидаемое поведение

При `evidenceNeed=high` минимальный effort должен быть повышен (например, `medium` → `high`). При `evidenceNeed=low` повышения не происходит.

### Целевые файлы

- `integrations/hermes-legion-kit/skills/autonomous-ai-agents/agent-contract-runner/scripts/review_ladder.py` — функция `_minimum_codex_effort` (строки 178–197) или `minimum_profile` (строки 199–215).

### Варианты исправления

**Вариант А:** Добавить логику в `_minimum_codex_effort`:

```python
def _minimum_codex_effort(routing: dict[str, Any]) -> str:
    base_effort = "low"
    if routing["complexity"] == "high" or routing["risk"] == "high":
        base_effort = "medium"
    if routing["ambiguity"] == "high":
        base_effort = max(base_effort, "medium", key=lambda e: EFFORT_RANK[e])
    if routing.get("evidenceNeed") == "high":
        base_effort = max(base_effort, "high", key=lambda e: EFFORT_RANK[e])
    return base_effort
```

**Вариант Б:** Добавить отдельную функцию `_evidence_effort_floor(routing)` и вызвать её в `minimum_profile`.

### Proof требования

1. **Регрессия:** Создать два routing JSON:
   - `routing_low.json`: `evidenceNeed=low`, остальные метаданные низкорисковые.
   - `routing_high.json`: `evidenceNeed=high`, остальные метаданные низкорисковые.

   Запустить `minimum_profile(routing_low)` → ожидается `min_effort=medium`.
   Запустить `minimum_profile(routing_high)` → ожидается `min_effort=high`.

2. **Офлайн-проверка:** Добавить новый тест `test_evidence_need_raises_effort` в `regression_review_ladder.py`.
3. **Review:** Независимый агент (REVIEWER) подтверждает: логика корректна, не ломает существующие low-risk пути.

### Acceptance

- [x] `evidenceNeed=high` повышает `min_effort` минимум до `high`.
- [x] `evidenceNeed=low` не повышает effort.
- [x] Регрессия прошла для парных `low`/`high`.
- [ ] Финальное review пользователя через Opus принято.

---

## P2-2: Отделение proof от предварительных trust predicates

### Проблема

`review_ladder.py:159–165` проверяет `requiredProofsPass=true` в trust predicates **до** делегирования V0. Но реальные proof-команды выполняются **после** executor (`agent_contract_runner.py:1098–1105`):

```python
def run_verification_gate(
    order: dict[str, Any],
    result_path: Path,
    events_path: Path,
    policy: PathPolicy,
    passed_event: str,
) -> dict[str, Any]:
    result, result_artifact_paths = verify_result(result_path, order, policy)
    artifact_checks = check_expected_artifacts(order, policy, result_artifact_paths, result_path)
    append_event(events_path, "expected_artifacts_checked", orderId=order["orderId"], artifacts=artifact_checks)
    verify_required_artifact_checks(artifact_checks)
    proof_checks = run_proof_commands(order, policy)  # <-- ПОСЛЕ executor
    ...
```

Предварительное решение об отказе от ревью опирается на самоутверждение о будущих proof.

### Ожидаемое поведение

Отделить проверяемые **до запуска** свойства задачи (например, `localNarrowBlastRadius`, `cheapReversal`, `noSensitiveOrExternalSideEffects`) от **итоговых** proof/artifact checks. Если итоговая проверка провалилась, финальный статус результата должен быть `failed`, даже если V0 был разрешён предварительно.

### Целевые файлы

- `integrations/hermes-legion-kit/skills/autonomous-ai-agents/agent-contract-runner/scripts/review_ladder.py` — строки 43–50 (определение `TRUST_PREDICATES`), строки 159–165 (`_all_trust_predicates`).
- `integrations/hermes-legion-kit/skills/autonomous-ai-agents/agent-contract-runner/scripts/agent_contract_runner.py` — функция `run_verification_gate` (строки 1090–1105).

### Варианты исправления

**Вариант А:** Разделить `TRUST_PREDICATES` на две группы:
- `PRE_EXECUTION_PREDICATES`: проверяются до делегирования (например, `localNarrowBlastRadius`, `cheapReversal`, `noSensitiveOrExternalSideEffects`, `noUncertainty`, `noScopeOrAssumptionIssues`).
- `POST_EXECUTION_PREDICATES`: проверяются после executor (`requiredArtifactsPass`, `requiredProofsPass`, `deterministicFailureOracle`).

V0 разрешается, если `PRE_EXECUTION_PREDICATES` все `true`. После executor проверяются `POST_EXECUTION_PREDICATES`; если провал — результат помечается `failed`.

**Вариант Б:** Оставить `TRUST_PREDICATES` как есть, но добавить явную проверку в `run_verification_gate`: если `verify_required_proof_checks` бросает исключение, результат перезаписывается статусом `failed` с причиной `proof_check_failed`.

### Proof требования

1. **Регрессия:** Создать order JSON с `requiredProofsPass=true` в метаданных, но proof-команда возвращает nonzero exit. Запустить runner → ожидается финальный статус результата `failed`, событие `proof_commands_checked` с failed proof.
2. **Офлайн-проверка:** Добавить новый тест `test_v0_trust_predicates_do_not_override_proof_failure` в `regression_agent_contract_runner.py`.
3. **Review:** Независимый агент (REVIEWER) подтверждает: fail-closed реакция работает, V0 не самоутверждает успех.

### Acceptance

- [x] PRE и наблюдаемые POST predicates разделены; semantic oracle остался только в legacy wire shape.
- [x] V0 admission использует PRE и наличие обязательного controller proof.
- [x] Провал proof после executor даёт controller acceptance `rejected`; canonical executor result сохранён.
- [x] Регрессии passed/failed proof и отсутствующего proof прошли.
- [ ] Финальное review пользователя через Opus принято.

---

## P2-3: Универсальный машиночитаемый формат handoff и ответа

### Проблема

В проекте уже есть `AGENT_ORDER_JSON_V1`, `AGENT_RESULT_JSON_V1`, JSON Schema,
`outputContract` и строгий JSON parser. Однако исполнитель иногда возвращает
валидный JSON внутри Markdown code fence либо добавляет к нему поясняющий
текст. До P2-3 `agent_result_builder.py` принимал только исходный строгий JSON: такой
кандидат становится `failed`, исходные байты сохраняются как evidence, а
заказчик получает ошибку формата вместо валидируемого ответа. Разные
исполнительные поверхности также нуждаются в едином способе передавать роль,
идентификатор заказа, схему ответа, статус и ссылки на артефакты.

### Цель

Определить совместимый протокол обмена между Boss/controller, владельцем
задачи, исполнителем и reviewer. Использовать существующие версии order/result
как базу; не создавать несвязанные форматы на каждой поверхности и не менять
семантику принятия: только controller принимает результат после проверки
контракта, proof и scope.

### Требуемое поведение

1. Заказ однозначно задаёт версию контракта, `orderId`/`objectiveId`, роли
   отправителя и получателя, исполнителя и назначенную модель, задачу и её
   ограничения, формат ответа, `schemaId`/версию схемы, канонический путь
   результата, доказательства и правила при ошибке.
2. Ответ связан с исходным заказом (`orderId` и, если требуется для цепочки,
   `inReplyTo`), указывает исполнителя/роль и завершённый статус (`done`,
   `blocked`, `failed`), а машинные поля соответствуют объявленной схеме.
   Артефакты передаются как типизированные ссылки с путём, media type и
   SHA-256; содержимое больших/бинарных файлов не помещается в текстовый JSON.
3. Форматированный вывод модели предпочитает provider-native structured
   output или tool arguments с JSON Schema, если текущая модель и runtime это
   поддерживают. Для остальных runtime транспортом остаётся отдельный файл
   результата по `outputContract`; обычный Markdown-ответ не считается
   машинным артефактом.
4. На границе приёма разрешается детерминистически нормализовать либо сырой
   JSON, либо ровно один fenced-блок `json`, если до и после него только
   пробелы. После снятия оболочки payload проходит существующий strict JSON
   parser и объявленную JSON Schema. Исходные байты остаются неизменным
   evidence; нормализованный candidate записывается отдельно и связывается с
   заказом хешем.
5. Не извлекать объект регулярным выражением из произвольного текста, не
   выбирать «первый подходящий» объект из нескольких, не принимать несколько
   блоков, дублирующие ключи, обрезанный JSON, Markdown с поясняющим текстом,
   отказ модели или незавершённый ответ как успешный результат. Возвращать
   отдельный машинный код ошибки формата/отказа и сохранять raw evidence;
   никакой такой путь не запускает повторно продуктовые действия.
6. Поддержать адаптеры поверхностей Codex, Claude, AGY/Gemini и Hermes с
   явным описанием доступного режима structured output. Недоступность режима
   должна быть видна контроллеру и не должна маскироваться обещанием prompt-а.
7. Сохранить чтение действующих V1 контрактов; правила миграции и совместимости
   должны быть проверены на всех текущих валидаторах и поверхностях до
   объявления новой версии обязательной.

### Исследовательская основа и архитектурная граница

- OpenAI Structured Outputs описывает выдачу по JSON Schema и отличие от JSON
  mode: JSON mode гарантирует синтаксис, но не соответствие схеме; отказы
  модели требуется распознавать отдельно:
  <https://developers.openai.com/api/docs/guides/structured-outputs>.
- A2A задаёт нейтральную межагентную модель Task/Message/Part/Artifact,
  идентификаторы и разные виды содержимого:
  <https://github.com/a2aproject/A2A/blob/main/docs/specification.md>.
- LangChain документирует provider-native structured output с валидацией и
  отдельные ошибки, включая несколько возвращённых structured outputs:
  <https://docs.langchain.com/oss/python/langchain/structured-output>.

Использовать эти решения как сравнительные образцы. Полный A2A transport,
обнаружение агентов, streaming и сетевые API не входят в этот пункт: текущая
система локально диспетчеризует CLI и уже использует file-based custody.
Провайдерные гарантии должны подтверждаться активным runtime/model route, а не
каталогом моделей или текстом инструкции.

### Целевые файлы для отдельной реализации

- `integrations/legion-contracts/lib/contracts.mjs` и его schemas/fixtures —
  общий нейтральный envelope/compatibility contract, если он окажется нужен
  после аудита имеющихся V1 полей.
- `integrations/hermes-legion-kit/skills/autonomous-ai-agents/agent-contract-runner/scripts/agent_result_builder.py`
  — отдельная нормализация raw candidate до strict validation, не изменение
  уже созданного canonical result.
- `integrations/hermes-legion-kit/skills/autonomous-ai-agents/agent-contract-runner/scripts/result_gateway.py`
  и исполнительные адаптеры поверхностей — передача schema/correlation и
  controller-owned raw/normalized evidence.
- `docs/LEGION_CONTRACTS.md`, Hermes/Aquila orchestration и соответствующие
  Codex/Claude/Antigravity instructions — единые producer/consumer правила.

### Proof требования

1. Regression matrix: raw JSON; один чистый `json` fence; префикс/суффикс
   прозой; несколько fenced-блоков/объектов; неверная схема; duplicate keys;
   `NaN`/overflow; truncation; отказ/незавершённый ответ. Только первые два
   представления могут пройти до schema validation.
2. Доказать совпадение `orderId`, роли/исполнителя и `schemaId`, сохранение raw
   bytes и хешей, отдельный canonical candidate и неизменность create-only
   canonical result. Отрицательные случаи завершаются machine-readable
   rejection без повторного запуска исполнителя и без потери evidence.
3. Прогнать общие legion-contracts smoke и Hermes, Codex, Claude, Antigravity
   package/surface regressions в изолированных средах; проверить backward
   compatibility fixtures для действующих V1 заказов и результатов.
4. Независимое review проверяет неоднозначное извлечение, отказ/incomplete,
   hash binding, scope и совместимость схем между маршрутами.

### Acceptance

- [x] Согласован один версионированный запрос/ответ, совместимый с текущими V1
  контрактами и поддерживаемый всеми активными surfaces.
- [x] Чистая Markdown-обёртка с одним JSON-блоком нормализуется, валидируется
  схемой, при этом исходный ответ сохраняется без изменений.
- [x] Произвольный текст, неоднозначность, refusal, truncation и schema errors
  не принимаются как `done` и дают машиночитаемый диагноз.
- [x] Есть положительные/отрицательные регрессии и backward compatibility proof;
  shared, Hermes, Codex, Claude и AGY smoke прошли офлайн.
- [ ] Финальное независимое review Claude Opus 5 проводит пользователь.
  Live CLI/model proof не выполнялся и не выводится из fake-CLI тестов.

---

## P2-4: Оценка JEV без ослабления текущей маршрутизации

### Решение на 2026-09-24

**Готовый `jev-router` сейчас не внедрять.** Исследование выполнено; выигрыш на
задачах CENTURION не доказан. Этот пункт допускает итог `NO-GO`: установка
роутера не является условием приёмки системы. Возможный эксперимент ниже —
отдельная работа после подтверждения проблемы текущего выбора исполнителей
или skills, а не обязательное усложнение каждого заказа.

### Что проверено

Изучен исходный код `gargpratyush/jev-router` на коммите
`38da6b84ea01241bfc41fbddc0928d0f40a703f0` от 2026-09-19: README,
`src/router.mjs`, `src/policy.mjs`, `src/codex-proxy.mjs`, конфигурация и тесты.
Пакет предоставляет CLI-обёртки Claude/Codex с локальным proxy; решение
вычисляет внешний TypeSafe API. Jev выбирает из вариантов и оценивает признаки;
это отдельный классификатор, не исполнитель кода или независимый code reviewer.

| Наблюдение | Значение для CENTURION |
| --- | --- |
| `askJev` передаёт prompt, текущую модель, размер контекста и доступные модели. | Вход не содержит структурированного контракта наших ролей, scope, proof и verification floors. Их нельзя поручать этому выбору. |
| Proxy выбирает модель на новом пользовательском ходе; concrete model обходит auto-routing. `applyCodexTier` может заменить неподдерживаемый effort на default выбранной модели. | Прозрачное переключение после dispatch несовместимо с зафиксированными order/model/effort и custody evidence. |
| `clampToAvailable` предпочитает более высокий tier, но при его отсутствии может выбрать нижний. | README не даёт достаточной гарантии отсутствия downgrade. Наши минимальные требования остаются обязательными проверками кода. |
| Готовые обёртки обслуживают Claude/Codex; Astra — общий long tier. | Нет готового назначения ролей Hermes/AGY/Gemini и ограничения Astra на ARCHITECTUS advisory. |
| Пользовательский prompt отправляется TypeSafe; exchanges сохраняются локально. | Появляются дополнительная внешняя передача данных, API-зависимость и задержка. Установка или чтение API credentials в этот этап не входят. |

`test/live-routing.mjs` на изученном коммите передаёт `available`, хотя
`askJev` ожидает `models` и без него возвращает `null`. Этот script не
подтверждает качество live routing. Тесты policy проверяют правила выбора,
а не стоимость и успешность выполнения задач CENTURION.

Документация TypeSafe показывает более подходящую гипотезу: рекомендация skill.
В опубликованном примере на 488 синтетических запросах, 182 Hermes skills и
Haiku 4.5 ошибки выбора уменьшились с 16,8% до 7,3% при двух запросах Jev 1.12.
Это результат поставщика на другом workload; он не доказывает улучшения наших
Luna/Sol или текущего каталога. Документация Jev 1.13 отдельно описывает ошибки
на сложной косвенной логике и adversarial content. `confidence` зависит от
распределения вариантов и требует калибровки; его нельзя считать вероятностью
успешной реализации или основанием ослабить review.

### Где возможна польза

1. При неоднозначной задаче рекомендовать профильного легионера/skill или
   исполнителя **до создания order**, только среди уже разрешённых вариантов.
2. Классифицировать неоднозначный blocker для подсказки controller, куда
   направить дальнейшую диагностику. Сначала проверить, что обычные коды
   ошибок и локальные правила не решают ту же задачу дешевле.
3. Сохранить deterministic routing первым шагом. Вызывать классификатор только
   при недостаточной уверенности controller; ясный micro fast path не получает
   дополнительного API-вызова.

Не использовать Jev для приёмки результата, замены Opus/security gate,
подтверждения proof, выдачи полномочий или исправления JSON. Формат и schema
валидируются кодом по P2-3; review сохраняет независимость.

### Условия отдельного эксперимента

1. Сначала подтвердить реальные ошибки/затраты текущего выбора по существующим
   обезличенным заказам. Зафиксировать исходную политику, модели, skill catalog
   и разделить выборку на настройку и отложенную проверку. Сравнивать с текущим
   controller и более простыми локальными правилами.
2. При наличии основания провести opt-in shadow comparison: рекомендация
   записывается как advisory и не влияет на dispatch. Версия модели Jev,
   критерии, вход и схема ответа фиксируются. Перед любым внешним API-вызовом
   отдельно согласуются разрешённые данные, бюджет и доступ; секреты и сырой
   код автоматически не передаются.
3. Controller ограничивает множество кандидатов и повторно валидирует ответ.
   Jev не меняет scope, budget, capabilities, role separation, минимальные
   model/effort/verificationProfile. Заказ после создания не меняет модель.
   Ошибка, timeout, неизвестный вариант или недостаточная уверенность означают
   возврат к исходной политике; если она не может выбрать допустимый маршрут,
   применяется существующий blocked/escalation, а не более слабый исполнитель.
4. Использовать общий schema/correlation контракт P2-3 и существующее поле
   `ExecutionDecision` в context/notes, без второго командного протокола.
   Ответ классификатора не является приказом. Нужны отрицательные случаи:
   prompt injection, запрещённая роль, недоступная модель, низкая уверенность,
   timeout, неверный JSON, попытка понизить effort/gate или совместить
   исполнителя с его независимым reviewer.
5. Shadow показывает качество рекомендаций, но не доказывает экономию
   исполнения. Для такого вывода нужен отдельный разрешённый парный replay
   безопасных задач в изолированных checkout с одинаковой приёмкой. Измерять
   accepted-task rate, повторы, ошибочные понижения, полную стоимость на
   принятый результат (включая неудачные попытки, router, cache, retries и
   review), p50/p95 полного времени. Порог confidence настраивать на своих
   данных, а не копировать из примера поставщика.
6. До эксперимента зафиксировать go/no-go критерий. Предлагаемый ориентир:
   отсутствие нарушений hard floors; качество приёмки не хуже baseline в
   заранее заданной статистической границе; не менее 10% улучшения полной
   стоимости или p95 времени без ухудшения другой метрики более чем на 5%.
   Альтернативой может быть доказанное снижение ошибок выбора skill при
   заранее ограниченных затратах. Это предлагаемые пороги, не наши замеры.
   Маленькая выборка, ничья или выигрыш только на синтетике означают `NO-GO`.

### Acceptance

- [x] Изучены исходники и первичные документы; записаны ограничения и решение
  не внедрять готовую обёртку сейчас.
- [x] Определены допустимые advisory-сценарии и критерии оценки пользы.
- [ ] Только если начат отдельный эксперимент: отчёт содержит baseline,
  отложенную выборку, полные метрики и независимое review решения go/no-go.
- [ ] Только при доказанном `GO`: отдельный bounded implementation order,
  возможность отключения и проверки сохранения контрактов всех surfaces.

### Источники

- Репозиторий и зафиксированная версия:
  <https://github.com/gargpratyush/jev-router/tree/38da6b84ea01241bfc41fbddc0928d0f40a703f0>.
- Проверенные определения и live script: `src/router.mjs:32–43`,
  `src/policy.mjs:14–22`, `src/codex-proxy.mjs:126–133`,
  `test/live-routing.mjs:14–16` на указанном коммите.
- Назначение Jev: <https://docs.typesafe.ai/introduction/coding-agents>.
- Пример skill suggestion: <https://docs.typesafe.ai/cookbooks/skill_suggestion>.
- Ограничения модели: <https://docs.typesafe.ai/model-jaggedness/jev-1.13>.
- Интерпретация уверенности: <https://docs.typesafe.ai/confidence>.

---

## Итоговый чеклист приёмки

| ID | Задача | Регрессия | Офлайн-проверка | Review | Accepted |
|---|---|---|---|---|---|
| P1-1 | Helper staged install с хешами и TLS | PASS, installer 4/4 | Изолированная установка PASS | Ожидает пользовательского Opus | Repository готов; live install/TLS вне текущего scope |
| P1-2 | Gateway/direct custody | PASS | Runner + Gateway PASS | Ожидает пользовательского Opus | Repository готов |
| P1-3 | Product lineage + accepted control inputs | Lineage 11/11, inputs 14/14 | Gateway chain, drift и no-replay PASS | Ожидает пользовательского Opus | Repository готов в локальной модели доверия |
| P2-1 | Влияние evidenceNeed | Парные low/high PASS | Routing regression PASS | Ожидает пользовательского Opus | Repository готов |
| P2-2 | PRE/POST и controller acceptance | V0 failure checks PASS | Runner + Gateway PASS | Ожидает пользовательского Opus | Repository готов; semantic oracle не объявлен проверенным |
| P2-3 | JSON handoff/response | Parser/builder/identity/evidence PASS | Shared + все четыре surface smoke PASS | Ожидает пользовательского Opus | Repository готов; provider native/live отдельно |
| P2-4 | Оценка пользы JEV; внедрение условно | Только при эксперименте: floors/fallback/injection | Baseline и holdout, качество/стоимость/p95 | Независимый review перед GO | Исследовано; сейчас NO-GO |

---

## Ограничения и вне охвата

- Реальные Codex/Claude API-вызовы — вне охвата этого задания.
- Продакшн Gateway start/closure receipts с live endpoints — вне охвата.
- Коммит, установка и деплой — только с явным разрешением пользователя.
- V3 specialist gate approval источник — отдельная будущая работа.

---

*DISCIPLINA ET FIDES.*
