# Задание Claude Opus 5: независимая проверка P2-3 и remediation

## Команда и результат

Проведи независимый аудит текущего рабочего дерева CENTURION: реализации P2-3
(единый JSON handoff/response), завершённых пунктов P1-1/P1-2/P1-3/P2-1/P2-2,
иерархии легионеров и маршрутизации моделей. **Не изменяй и не исправляй код.**
Найди подтверждаемые проблемы, объясни их последствия и предложи минимальные
пути решения. Ответ и отчёт пиши по-русски.

Рабочий checkout:

`/home/mrz/projects/al/centurionCLI/worktrees/centurion-main`

Обязательный итоговый файл:

`/home/mrz/projects/al/centurionCLI/worktrees/centurion-main/docs/CLAUDE_OPUS_5_P2_3_REMEDIATION_REVIEW_REPORT_2026-09-24.md`

Создай именно файл отчёта; одного сообщения в чате недостаточно. В финальном
сообщении укажи его абсолютный путь, вердикт, число находок по приоритетам и
существенные непроверенные области. Если отчёт уже существует, не перезаписывай
его: добавь UTC timestamp к имени нового отчёта и сообщи фактический путь.
Не создавай фиктивный executor-result JSON: результат этого аудита является
Markdown-отчётом, а JSON-контракты ниже являются предметом проверки.

## Полномочия и запреты

- Только чтение исходников, существующих документов, тестов и артефактов
  **в этом checkout**. Не исследуй установленную систему, другие worktree,
  `~/.hermes`, `~/.claude`, `~/.codex`, `~/.agents`, настройки и секреты.
- Единственные разрешённые записи: новый отчёт в `docs/` и собственные
  изолированные fixtures, логи и воспроизводители под
  `<checkout>/.centurion/opus5-review/`. Не меняй существующие proof-артефакты.
- Не исправляй исходники, тесты, схемы, инструкции, план или чужие изменения.
  Не выполняй commit/reset/checkout/clean/stash, live install/sync/deploy/restart,
  форматирование, обновление зависимостей или настройку авторизации. Тестовая
  установка штатным smoke допустима только в твоей scratch-области с fake CLI.
- Не вызывай внешние модели, API, JEV, сетевые поиски и реальные исполнительные
  CLI. Для проверок запуска допустимы только fake CLIs в тестовых каталогах.
  Локальный TLS fixture допустим, если тест изолирован и сам закрывает сервер.
- Не запускай дополнительные модели или агентов: финальную проверку выполни
  самостоятельно как Claude Opus 5. Если активная модель не подтверждена
  доступным runtime, явно укажи это; не меняй конфигурацию для её включения.
- Перед тестом прочитай его команды и побочные эффекты. Если он пишет вне
  разрешённых каталогов, обращается к live-системе или требует установки,
  пропусти его и укажи причину. Не исправляй тест ради его запуска.
- Отсутствие зависимостей или невозможность части проверок не мешает сохранить
  частичный отчёт. Не маскируй непроверенное статусом PASS.
- P2-4/JEV отложен пользователем. Проверяй только отсутствие незапрошенного
  внедрения и ослабления текущих правил; оценка JEV и новые технологии вне задания.

Это рабочая система. Аудит не даёт полномочий перестраивать её, расширять scope
или применять рекомендации. Рекомендации остаются в отчёте до отдельной команды.

## Источники и исходное состояние

Начни с `pwd`, `git rev-parse HEAD`, `git status --short`, `git diff HEAD --stat`
и `git ls-files --others --exclude-standard`. Ожидаемый на момент выдачи задания
HEAD: `3ee00134800dd8bdbbcdb2fc11a82ae25ba00e5e`; проверь его заново.
Дерево уже содержит много изменений и untracked файлов. Не приписывай весь diff
последнему этапу, не ограничивай аудит tracked diff: новые helpers и регрессии
могут быть untracked. Зафиксируй исходные хеши проверяемых файлов и повторно
сверь их в конце; один `git status` не обнаруживает правки внутри dirty-файла.

Прочитай:

1. `docs/REMEDIATION_PLAN_2026-09-23.md`, особенно действующую трактовку и acceptance.
2. `docs/CLAUDE_OPUS_DISAGREEMENTS_2026-09-24.md`.
3. `docs/REMEDIATION_IMPLEMENTATION_AND_DISAGREEMENTS_2026-09-24.md`.
4. `docs/LEGION_HARDENING_REPORT_2026-09-24.md`.
5. `docs/LEGION_CONTRACTS.md`, соответствующие SKILL.md и routing rules.

Это заявления и контекст, которые надо проверить кодом и независимыми
воспроизводителями. Предыдущие PASS, комментарии и mock-тесты не доказывают
корректность сами по себе. Не подгоняй вывод под прежний аудит или реализацию.

Учитывай согласованные решения: ordinary non-lineage/non-advisory direct runner
допустим с custody; Gateway обязателен для lineage/Astra advisory; canonical
result create-only; controller acceptance отдельно; хеши вычисляет controller.
Если считаешь решение ошибочным, докажи конкретный сценарий и отдельно назови
предлагаемое изменение политики. Не выдавай отклонённый вариант старого плана
за действующее требование.

## Обязательные зоны проверки

Для Python далее `S` означает каталог
`integrations/hermes-legion-kit/skills/autonomous-ai-agents/agent-contract-runner/scripts/`.

### 1. P2-3: однозначный формат и совместимость

Проверь `S/response_envelope.py`, `S/agent_result_builder.py`,
`references/agent-result.schema.json` рядом с `scripts/`,
`integrations/legion-contracts/lib/contracts.mjs`, standalone
`integrations/claude-legion-kit/lib/claude-result-validator.mjs` и bundled
`integrations/antigravity-legion-kit/legion-contracts/lib/contracts.mjs`.

- Raw JSON и ровно один lowercase `json` fence: UTF-8, пробелы, CRLF,
  отсутствие изменения исходных или внутренних JSON-байтов.
- Prose до/после, несколько блоков/объектов, неверный tag, trailing commas,
  duplicate keys, NaN/Infinity/overflow, truncation, неверная кодировка,
  lone surrogates и чрезмерная вложенность. Не допускается выбор удобного объекта.
- Refusal/incomplete и неправильные типы полей: вместо статуса/списка/объекта
  пришёл другой тип; ошибка должна быть контролируемой, без traceback и ложного done.
- `orderId`, executor, version/schemaId, inReplyTo, senderRole/recipientRole и
  objectiveId. Routing metadata находится в `notesForExecutor` с префиксом
  `AQUILA_ROUTING_JSON_V1:`; проверь фактический источник objectiveId.
- Отсутствующий/лишний/подменённый handoff, handoff в legacy order, несовпадение
  ожиданий controller и ответа, попытка самоповышения роли или смены цели.
- Одинаковые критерии Python, shared JS, standalone Claude и bundled AGY:
  транспорт, schema, MIME, статусы, ошибка и optional/required поля.
- Числа около `2^53`, округление JS Number, bool/int и semantic comparison:
  оцени влияние на принятие, а не только наличие ограничения в документации.
- Existing V1 без handoff, explicit legacy modes и custom schema override:
  изменения не должны молча ломать действующих потребителей.

### 2. Evidence, пути и неизменяемость

Проверь `S/agent_contract_runner.py`, builder, shared JS ingress, Claude/AGY guards
и `integrations/legion-contracts/scripts/legion-contract.mjs`.

- Executor-owned candidate и controller-owned responseEnvelope: нельзя
  присвоить полномочия controller простым добавлением поля в ответ.
- Полная связь raw bytes -> normalized candidate -> canonical payload:
  хеши, размеры, transport, identity, неожиданные поля, изменение только одного
  файла, подмена обоих evidence-файлов, отсутствие evidence, подмена после proof.
- Create-only canonical и evidence, collision/retry, частичная запись,
  недоступный каталог, symlink leaf/ancestor, traversal, relative/absolute paths,
  alias, directory/FIFO вместо обычного файла. Проверка symlink должна учитывать
  исходный путь, а не только путь после resolve.
- Typed artifact path/mediaType/sha256 должны проверяться по живым байтам,
  в разрешённой области. Declared hash или exists=true не являются доказательством.
- Guard evidence рядом со snapshot (`.responses`) не должно считаться правкой
  продукта или создавать универсальный способ обойти scope/forbidden checks.
- Различай случайный drift, подмену недоверенного executor и согласованную
  перезапись всех trusted pins процессом под тем же UID. Укажи границу гарантии.

### 3. Gateway, direct adapters и отсутствие replay

Проверь `S/result_gateway.py`, `S/direct_custody.py`, runner и оба order-guard.

- Codex file candidate; Claude file/stdout и inner terminal result внутри
  event object/array/JSONL. Нормализация не должна обходить terminal success,
  runtime-model, permission-denials и tool-loop checks.
- `launch.candidateJsonPath`: свежесть candidate/canonical/evidence,
  несовпадение путей, legacy direct путь, Hermes/AGY и Codex/Claude custody.
- Timeout/nonzero exit, ранний candidate, частичный stdout, неизвестная форма,
  отказ чтения/записи. Все ошибки закрываются корректно, без повторных side effects.
- Synthetic failure сохраняет первичную причину и raw evidence; schema/identity
  ошибка вторичной упаковки не должна скрывать refusal/incomplete/format error.
- Провал proof сохраняет executor statement, но запрещает acceptance. Потребитель
  не должен считать exit 0 монитора или result.status=done достаточной приёмкой.
- Порядок preflight -> launch -> closure -> proof -> acceptance, Loop V1 locks,
  rollback при отказе записи и запрет повторного запуска того же orderId.

### 4. P1-3: передача принятых входов и product lineage

Проверь `S/accepted_inputs.py`, `S/artifact_lineage.py` и реальные точки вызова.

- Exact inputResults shape, predecessor order/result/start/closure/proof/acceptance
  identity и hash bindings, passed acceptance/proof, done result, явные artifacts.
- Недостаточно тестировать helper: проследи вызовы до child launch и после proof,
  последнюю Gateway-проверку перед acceptance и сохранение observed checks.
- Current-order reference, циклы, дубли, глубина/размер графа, общие предки,
  отсутствующие поля, symlink/FIFO, неверные версии/путь/хеш, rejected predecessor.
- Изменение входа до запуска, исполнителем, proof-командой и перед финальным
  принятием. Отказ должен сохранять исходный result и блокировать принятие/replay.
- `inputResults` даёт read-only input и не расширяет write scope. Control-artifacts
  Astra и product lineage имеют разные правила, но сквозная цепочка должна работать.
- Самостоятельно проверь цепочку Astra advisory -> Sol/Luna implementation ->
  независимый Opus review -> controller closure с fake CLIs. Проверяй реальные
  чтения входов и bindings, а не только названия стадий и слова PASS.

### 5. Иерархия, роли, модели и дрейф

Проверь `S/review_ladder.py`, Loop handoffs, canonical skills, Hermes routing
policy/reference и связанные инструкции Codex/Claude/AGY.

| Модель/уровень | Ожидаемая граница |
| --- | --- |
| Boss -> controller -> OPTIO/task owner -> исполнитель | Scope и принятие задаются сверху; blocker возвращается владельцу |
| GPT-6 Luna/Sol | Реализация по сложности/риску/ambiguity/evidence; модель и effort выбираются отдельно |
| GPT-6 Astra | В текущем контракте bounded read-only ARCHITECTUS advisory по сложной задаче; не final reviewer |
| Claude Opus 5 | Независимое review, конкретные замечания владельцу; не исправляет и не принимает собственную реализацию |
| Gemini 3.8 Flash | UI/design/text/creative через agy, подходящая роль и реальные model/effort flags |

Проверь self-approval, review-of-review, обход terminal_gate, подмену objective,
candidate digest, reviewer или verification floor. Сопоставь заявленный маршрут
с launch arguments, overrides и receipts. Проверь запрет silent downgrade при
ошибке/бюджете, V0 fast path, evidenceNeed=high, PRE/POST, фактический proof и
независимую проверку. `deterministicFailureOracle` должен оставаться legacy claim,
а V3 блокироваться до trusted approval verifier. Исторические модели в dated
snapshot/ledger не считай активным drift без доказательства использования.

### 6. P1-1 и полнота remediation

Проверь `scripts/install-owned-files.mjs`, его тесты и вызов из `install.sh`
статически: staging, SHA-256/режимы, backup/rollback, foreign files, symlink,
частичный отказ и negative TLS в изолированной установке. Не запускай live install.
Различай атомарную смену одной цели и транзакционность всего установщика.

Для P1-1/P1-2/P1-3/P2-1/P2-2/P2-3 сопоставь актуальный acceptance с реальным кодом,
регрессиями и документацией. Найди незавершённые пункты, ложные PASS/утверждения,
неупакованные helpers, расхождения bundled копий и лишние изменения вне задачи.
Известные ограничения Loop V1 + lineage, same-UID, authorship и live proof не
скрывай; отделяй их от новых дефектов и от обещаний, которые им противоречат.

## Проверки и воспроизводители

Не полагайся только на существующие регрессии: для подозреваемого обхода создай
маленький безопасный воспроизводитель в своей разрешённой scratch-области.
Не изменяй product-файлы для экспериментов. Все повреждения и гонки моделируй
на fixtures. Не запускай одну регрессию одновременно с suite, включающей её.

После проверки безопасности команд подготовь каталог:

```bash
cd /home/mrz/projects/al/centurionCLI/worktrees/centurion-main
mkdir -p .centurion/opus5-review
AUDIT_RUN_DIR=$(mktemp -d "$PWD/.centurion/opus5-review/run-XXXXXXXX")
mkdir -p "$AUDIT_RUN_DIR/tmp" "$AUDIT_RUN_DIR/logs"
export TMPDIR="$AUDIT_RUN_DIR/tmp"
export PYTHONDONTWRITEBYTECODE=1
```

`PYTHONOPTIMIZE` должен быть выключен: Python assert является частью этих тестов.
Проверь чтение default HOME/ledger/schema и использование системного `/tmp`
самими тестами. TMPDIR не изолирует произвольную команду автоматически.
Не меняй HOME, авторизацию, модели и настройки живого окружения. Проверенные
штатные тесты могут задавать своим дочерним процессам изолированный test HOME
в scratch-каталоге: это не разрешает запись в настоящее домашнее окружение.

Обязательный офлайн-набор, если после чтения нет запрещённых побочных эффектов:

```bash
git diff --check
bash -n install.sh
node --test tests/install-owned-files.test.mjs
node integrations/legion-contracts/scripts/smoke.mjs
node integrations/codex-legion-kit/scripts/smoke.mjs
node integrations/claude-legion-kit/scripts/smoke.mjs
node integrations/antigravity-legion-kit/scripts/smoke.mjs
node integrations/hermes-legion-kit/scripts/smoke.mjs
node skills/tester/scripts/legion-skill-eval.mjs
node integrations/claude-legion-kit/scripts/claude-surface-audit.mjs --repo-only
```

Hermes smoke включает десять packaged Python regressions: routing, runner,
builder, Gateway, response-envelope, artifact-lineage, accepted-inputs,
accepted-inputs-Gateway, execution-state и legion-handoffs. Отдельный повтор нужен
только для диагностики, конкретного нового воспроизводителя или если suite
не добрался до нужного теста. Логи сохраняй в своём `$AUDIT_RUN_DIR/logs`.
Не запускай `audit:local` и live surface audit. Если команда пропущена, запиши
точное ограничение и продолжи доступную статическую проверку.

## Формат файла отчёта

1. **Вердикт.** `PASS`, `PASS_WITH_LIMITATIONS`, `FAIL` или `INCOMPLETE`, краткое
   основание; commit, dirty-state, дата, фактически подтверждённая модель.
2. **Находки по убыванию серьёзности.** Для каждой: ID, P0/P1/P2/P3, статус
   `confirmed`/`suspected`, точный файл и строки/функция, наблюдаемое и ожидаемое
   поведение, сценарий и необходимые условия, команда/fixture/log evidence,
   практическое влияние. Если подтверждённых P0/P1 нет, скажи это явно.
3. **Решение каждой проблемы.** Минимальные затрагиваемые файлы/функции, алгоритм
   исправления, влияние на V1/поверхности/иерархию, нужна ли миграция, regression
   до/после и критерий приёмки. Код не менять; предложения не считать выполненными.
4. **Acceptance matrix.** P1-1/P1-2/P1-3/P2-1/P2-2/P2-3: выполнено/частично/
   не выполнено/не проверено, доказательство и оставшиеся условия. P2-4: отложен.
5. **Проверки.** Точная команда, exit code, наблюдаемый результат, путь к логу,
   что доказано и что не доказано. Отдельно новые воспроизводители, проваленные
   и не запущенные проверки, пропуски охвата.
6. **Сверка с прежними выводами.** Подтверждено/опровергнуто/изменилось/не проверено
   для существенных утверждений плана, отчёта и Opus disagreements. Не дублируй
   одну проблему несколькими находками, объясняй собственные разногласия.
7. **Приоритетный план исправлений.** Порядок минимальных независимых изменений,
   обязательный proof и риски совместимости. Отдели обязательное от необязательного;
   не предлагай инфраструктуру без конкретной доказанной пользы.
8. **Границы и сохранность.** Known limitations, offline/live разница, неизменность
   хешей исходников, полный список созданных файлов. Любое внешнее изменение
   дерева во время аудита отрази явно; чужие изменения не откатывай.

Не делай вывод «система полностью безопасна» из прохождения тестов. Одновременно
не придумывай проблемы ради количества: отсутствие подтверждённых дефектов
допустимо при честно указанном охвате. Заверши записью отчёта и краткой сводкой,
после чего остановись. Исправления, установка и обсуждение JEV требуют новой задачи.
