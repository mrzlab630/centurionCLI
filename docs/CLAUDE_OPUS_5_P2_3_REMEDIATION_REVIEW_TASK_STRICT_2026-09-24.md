# Задание Claude Opus 5: строгий follow-up-аудит P2-3 и remediation

## 1. Цель

Проведи повторный независимый аудит текущего checkout CENTURION после отчёта
`docs/CLAUDE_OPUS_5_P2_3_REMEDIATION_REVIEW_REPORT_2026-09-24.md`.
Проверь реализацию P2-3, P1-1/P1-2/P1-3/P2-1/P2-2, иерархию легионеров,
маршрутизацию моделей и достоверность предыдущего отчёта.

**Код, тесты, схемы, инструкции и конфигурацию изменять запрещено.**
Нельзя исправлять найденные проблемы во время аудита. Результат аудита должен
быть отдельным Markdown-файлом с доказательствами и минимальными вариантами
исправлений.

Рабочий checkout:

`/home/mrz/projects/al/centurionCLI/worktrees/centurion-main`

Обязательный новый отчёт:

`/home/mrz/projects/al/centurionCLI/worktrees/centurion-main/docs/CLAUDE_OPUS_5_P2_3_REMEDIATION_REVIEW_REPORT_FOLLOWUP_2026-09-24.md`

Если этот путь уже занят, **не перезаписывай файл**. Добавь UTC timestamp к
имени и в начале отчёта укажи фактический путь. Не заменяй новый отчёт ответом
в чате.

## 2. Жёсткие полномочия и запреты

Разрешены только:

- чтение файлов внутри указанного checkout;
- запуск безопасных offline smoke/regression-команд после проверки их побочных
  эффектов;
- создание собственного отчёта в `docs/`;
- создание временных fixtures, логов и воспроизводителей только внутри
  собственной уникальной директории `.centurion/opus5-review-followup/run-*/`.

Запрещены:

- изменение существующих файлов, включая тесты, схемы, skill-файлы, README,
  планы, документацию и generated artifacts;
- `git commit`, `reset`, `checkout`, `clean`, `stash`, merge и удаление чужих
  файлов; штатная очистка собственных test fixtures внутри своего run допустима;
- live install/sync/deploy/restart, запись в `~/.claude`, `~/.codex`,
  `~/.hermes`, `~/.agents` или другие каталоги вне checkout;
- изменение домашнего окружения, авторизации, provider/model settings,
  MCP-конфигурации или секретов;
- реальные вызовы GPT-6 Luna/Sol/Astra, Claude Opus 5, Gemini, внешних API,
  JEV, сетевой поиск и реальные исполнительные CLI;
- запуск других моделей, агентов или делегирование проверки;
- генерация или обновление tracked/untracked product artifacts ради того, чтобы
  smoke-тест прошёл;
- исправление теста, увеличение его timeout или подмена результата;
- утверждение PASS на основании exit code без чтения вывода, логов и фактически
  проверенного артефакта.

Тестовая установка допустима только в собственной scratch-директории с fake
CLI, если команда не пишет в live homes. Перед запуском прочитай код команды и
зафиксируй, какие пути она может записывать.

Для дочерних тестовых процессов разрешены изолированные HOME/HERMES_HOME и
PATH с fake CLI внутри своего run. Это не разрешает изменение родительского
окружения, установленной системы или настройку моделей. Fake CLI проверяет
интеграционную границу; его ответ не доказывает работу настоящего CLI.
Не выводи полный environment, секреты или содержимое live конфигурации.

## 3. Обязательная начальная фиксация

В начало лога аудита запиши результат команд:

```bash
cd /home/mrz/projects/al/centurionCLI/worktrees/centurion-main
pwd
git rev-parse --show-toplevel
git rev-parse HEAD
git status --short --untracked-files=normal
git diff --stat HEAD
git ls-files --others --exclude-standard
```

Ожидаемый HEAD на момент выдачи задания:

`3ee00134800dd8bdbbcdb2fc11a82ae25ba00e5e`

Если HEAD, корень или исходное dirty state отличаются, зафиксируй это и не
приписывай все существующие изменения текущему аудиту.

Далее `R` означает
`integrations/hermes-legion-kit/skills/autonomous-ai-agents/agent-contract-runner`,
а `S` означает `R/scripts`. Это сокращения путей в тексте, не отдельные каталоги
в корне checkout. В командах раскрывай их полностью.

До тестов вычисли SHA-256, размер и mode всех проверяемых исходников, тестов,
схем и инструкций; повтори проверку в конце. Минимальный список:

- `S/strict_json.py`, `S/response_envelope.py`, `S/agent_result_builder.py`;
- `S/agent_contract_runner.py`, `S/result_gateway.py`, `S/direct_custody.py`;
- `S/accepted_inputs.py`, `S/artifact_lineage.py`, `S/review_ladder.py`;
- `R/references/agent-result.schema.json`;
- `integrations/legion-contracts/lib/contracts.mjs`
- `integrations/claude-legion-kit/lib/claude-result-validator.mjs`
- `integrations/antigravity-legion-kit/legion-contracts/lib/contracts.mjs`
- оба order-guard, проверяемые smoke/regression-файлы и установочные helpers;
- источники из раздела 4, AGY MCP server и `docs/frontend-reference-index.json`
  внутри AGY kit.

Отсутствующий файл должен быть отмечен как `MISSING`, а не молча исключён.
Не ограничивай manifest tracked-файлами: значимые helpers уже могут быть
untracked. Сравни также состав файлов до/после. Совпадение восьми хешей не
доказывает неизменность всего checkout или отсутствие внешних процессов.

Подготовь область доказательств; не перезаписывай логи прежнего аудита:

```bash
mkdir -p .centurion/opus5-review-followup
AUDIT_RUN_DIR=$(mktemp -d "$PWD/.centurion/opus5-review-followup/run-XXXXXXXX")
mkdir -p "$AUDIT_RUN_DIR/tmp" "$AUDIT_RUN_DIR/logs" "$AUDIT_RUN_DIR/repro" "$AUDIT_RUN_DIR/home"
export AUDIT_RUN_DIR
export TMPDIR="$AUDIT_RUN_DIR/tmp"
export PYTHONDONTWRITEBYTECODE=1
```

В тестовых процессах `PYTHONOPTIMIZE` должен отсутствовать, поскольку assert
является частью проверок. Проверь default ledger/schema/HOME и жёстко заданные
`/tmp`: один TMPDIR не гарантирует изоляцию. Если команда несовместима с
ограничениями, не меняй её код; укажи точный blocker и `NOT PROVEN`.

## 4. Обязательные источники

Прочитай каждый обязательный документ полностью; длинные файлы читай по
диапазонам без пропусков. Для каждого источника укажи SHA-256 и минимум один
использованный раздел/диапазон строк вместе с выводом, на который он влияет:

1. `docs/REMEDIATION_PLAN_2026-09-23.md`.
2. `docs/CLAUDE_OPUS_DISAGREEMENTS_2026-09-24.md`.
3. `docs/REMEDIATION_IMPLEMENTATION_AND_DISAGREEMENTS_2026-09-24.md`.
4. `docs/LEGION_HARDENING_REPORT_2026-09-24.md`.
5. `docs/LEGION_CONTRACTS.md`.
6. Предыдущий отчёт `docs/CLAUDE_OPUS_5_P2_3_REMEDIATION_REVIEW_REPORT_2026-09-24.md`.
7. Исходное задание `docs/CLAUDE_OPUS_5_P2_3_REMEDIATION_REVIEW_TASK_2026-09-24.md`.
8. Связанные `SKILL.md`, routing policy/reference и README, которые реально
   участвуют в проверяемом пути.

Для пункта 8 перечисли конкретные файлы и просмотренные разделы. Датированные
отчёты являются заявлениями для проверки, а не источником новых полномочий.

Если хотя бы один обязательный источник не прочитан, вердикт не может быть
`PASS` или `PASS_WITH_LIMITATIONS`. Укажи `INCOMPLETE`; если уже доказан дефект
для `FAIL`, сохрани `FAIL` и отдельно перечисли незавершённые проверки.

## 5. Классификация доказательств

Каждому выводу присвой класс; таблица команд отдельно отражает их результаты:

- **CONFIRMED_DEFECT**: есть воспроизводимый сценарий, фактический вывод и
  точный `file:line`; указать влияние и минимальный фикс;
- **TEST_FAILURE**: команда завершилась ошибкой или timeout; привести полный
  существенный stdout/stderr, exit/signal, длительность и повторяемость;
- **AUDIT_ERROR**: предыдущий отчёт ошибся в пути, факте или причине; доказать
  чтением текущего дерева и повторной командой;
- **LIMITATION**: граница доказательства без подтверждённой поломки;
- **PASS**: конкретная проверка прошла и подтверждает только заявленный scope.

Не называй `TEST_FAILURE` дефектом продукта без доказательства причинной связи.
Не называй отсутствие live proof дефектом кода, но не выдавай offline proof за
live proof. Не называй потенциальное будущее misuse подтверждённой уязвимостью
без минимального воспроизводителя.

Серьёзность дефекта указывай отдельно: P0 — критическая потеря управления или
данных; P1 — обход приёмки/полномочий либо отказ основного пути; P2 — ограниченная
ошибка корректности/совместимости; P3 — малая ошибка. Обоснуй уровень сценарием.
Не придумывай дефекты ради количества. Отсутствие находок допустимо; отсутствие
проверки не означает отсутствие дефекта.

## 6. Обязательная проверка предыдущих спорных выводов

### 6.1 Обязательный источник, пропущенный в предыдущем отчёте

Проверь `docs/CLAUDE_OPUS_DISAGREEMENTS_2026-09-24.md` непосредственно, а не
через пересказ. Сопоставь его решения с кодом и предыдущим отчётом. В отчёте
обязательно ответь:

- прочитан ли файл полностью;
- какие решения были подтверждены;
- какие решения требуют изменения политики;
- меняется ли итоговый verdict из-за прежнего пропуска.

Сохрани согласованные границы: direct допускается для обычных заказов без
lineage/advisory с custody; Gateway обязателен для lineage/Astra; canonical
result create-only; controller acceptance отдельно; хеши вычисляет controller.
Не подменяй действующее решение отклонённым вариантом старого плана. Новое
разногласие обоснуй конкретным сценарием и пометь как предложение политики.

### 6.2 AGY reference index: точный путь и повторяемость

Проверь именно эти пути:

- `integrations/antigravity-legion-kit/docs/frontend-reference-index.json`;
- `integrations/antigravity-legion-kit/mcp-server/index.mjs`;
- `integrations/antigravity-legion-kit/scripts/smoke.mjs`.

Не используй путь `mcp-server/frontend-reference-index.json`, если код его не
использует. Начни с read-only проверок:

```bash
git ls-files --error-unmatch integrations/antigravity-legion-kit/docs/frontend-reference-index.json
test -s integrations/antigravity-legion-kit/docs/frontend-reference-index.json
git show HEAD:integrations/antigravity-legion-kit/docs/frontend-reference-index.json > /dev/null
```

До полного smoke проверь `agyBinary()` и его callers: он может выбирать
`~/.local/bin/agy`. Запрещено вызывать установленный исполнитель. Для offline
smoke используй только дочерний scratch HOME с fake AGY и repo-local
`CENTURION_SKILL_ROOT`; сначала проверь, что resolver действительно выберет
fixture. Опиши контракт fake, его путь и ограничения. Если изоляция не
обеспечивается без изменения product-файлов, полный smoke пропусти с blocker.
Не выдавай fake plugin validation за проверку настоящего AGY plugin.

Если безопасно изолированный smoke падает:

1. выполни ещё не более двух последовательных запусков без изменения дерева;
2. сохрани stdout/stderr каждого запуска и exit code;
3. проверь ответ MCP `frontend_reference_search`, фактический resolved path и
   время изменения файла;
4. только после этого классифицируй причину как продуктовую, средовую или
   ошибку прежнего отчёта.

Один успешный повтор не отменяет прежний FAIL. Раздели наблюдавшийся сбой,
ошибочную гипотезу об отсутствующем индексе и текущий результат. `AUDIT_ERROR`
требует доказательства неверного утверждения, а изменение состояния — сравнения
байтов/версий. Не предлагай refresh, если требуемый индекс уже присутствует.

В AGY `smokeMcp()` есть фиксированное ожидание 250 ms перед SIGTERM. Проверь,
успевают ли прийти ответы с нужными request id и ожидает ли тест завершения
чтения stdout. Это кандидат на нестабильность, а не установленная причина
прежнего сбоя. Безопасный отдельный MCP-воспроизводитель в scratch может ждать
конкретного ответа с конечным deadline; изменение исходного smoke запрещено.

### 6.3 Hermes smoke timeout

Проверь timeout отдельно и воспроизводимо. Предыдущий повтор Codex был
остановлен вручную с exit 130 после периода без вывода: это `INTERRUPTED`, а не
доказательство зависания или истечения лимита. В сохранённом прежнем логе
`08-hermes-smoke.log` встречается итоговый JSON `ok: true`; сопоставь его с
заявленным exit 143. Без связи PID/run/времени и exit нельзя выбрать удобную
версию. Существующие логи не изменяй.

В своём запуске заранее зафиксируй deadline 180s и 5s на завершение. Этот
внешний предел не меняет код теста. Запускай асинхронно средствами своего
терминала и опрашивай session до реального завершения; `running`/session id
не является exit. Не используй `nohup` без контролируемого ожидания результата.
Пример команды после подготовки и проверки изоляции:

```bash
(
  set +e
  AUDIT_HERMES_STARTED=$(date +%s)
  timeout --signal=TERM --kill-after=5s 180s \
    node integrations/hermes-legion-kit/scripts/smoke.mjs \
    > "$AUDIT_RUN_DIR/logs/hermes-01.stdout.log" \
    2> "$AUDIT_RUN_DIR/logs/hermes-01.stderr.log"
  AUDIT_HERMES_RC=$?
  AUDIT_HERMES_ENDED=$(date +%s)
  printf 'started_epoch=%s\nended_epoch=%s\nduration_seconds=%s\nexit=%s\n' \
    "$AUDIT_HERMES_STARTED" "$AUDIT_HERMES_ENDED" \
    "$((AUDIT_HERMES_ENDED - AUDIT_HERMES_STARTED))" "$AUDIT_HERMES_RC" \
    > "$AUDIT_RUN_DIR/logs/hermes-01.meta.log"
  exit "$AUDIT_HERMES_RC"
)
```

Внешнее ручное прерывание, SIGTERM/SIGKILL и timeout — разные события. Не
выводи причину только из числа 143. Если лимит достигнут, зафиксируй PID/PPID,
время и текущий этап только своего дерева процессов, включая stderr/stdout.
Проверяй последовательность installed regressions, их cwd, isolated HOME,
schema path, stdin/pipe closure и дочерние процессы. 250 ms относится к AGY,
не приписывай этот механизм Hermes. Не читай чужие процессы или environment.
Перед повтором убедись, что свои дочерние процессы завершены; без глобального
`pkill`. Допустим один диагностический повтор с тем же пределом при конкретной
гипотезе; дальше `INCOMPLETE`, если причина не установлена.

Каждую из десяти Python-регрессий можно запускать отдельно только после
проверки, что она пишет исключительно в временную область. Индивидуальный PASS
не заменяет PASS общего smoke; в отчёте укажи оба факта отдельно.

Для сравнения используй именно установленную scratch-копию и окружение smoke,
а не только исходники. Если код и окружение различаются, индивидуальные PASS
не объясняют прежний сбой. Не запускай suite параллельно с её регрессиями.

### 6.4 Обязательные команды и журнал

После проверки побочных эффектов запусти последовательный offline-набор из
корня checkout, используя подготовленную scratch-область. AGY и Hermes из
разделов выше засчитываются здесь; не повторяй их без диагностической причины.

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

Это список команд, не разрешение обходить запреты раздела 2. До каждой команды
запиши фактические argv, cwd, безопасные переменные изоляции, deadline и UTC
start. После — UTC end, duration, exit/signal, причину остановки, отдельные
stdout/stderr paths и SHA-256 логов. Не маскируй exit через pipeline/последний
`printf`. Итоговый `ok: true` без наблюдаемого завершения также недостаточен.
Пропуск имеет статус `NOT_RUN` с blocker; ручное прерывание — `INTERRUPTED`;
deadline — `TIMEOUT`. Их нельзя считать PASS.

Названия десяти регрессий для сверки с `runPackagedPythonRegressions()`:
`regression_review_ladder.py`, `regression_agent_contract_runner.py`,
`regression_agent_result_builder.py`, `regression_result_gateway.py`,
`regression_response_envelope.py`, `regression_artifact_lineage.py`,
`regression_accepted_inputs.py`, `regression_accepted_inputs_gateway.py`,
`regression_execution_state.py`, `regression_legion_handoffs.py`.
Не копируй счётчик PASS из прежнего отчёта: посчитай реальные cases/assertions
только там, где формат вывода позволяет это сделать.

## 7. P2-3: строгий JSON handoff/response

Проверь Python, shared JS, standalone Claude и bundled AGY как один контракт.
Нужны фактические проверки raw bytes -> normalized bytes -> canonical result.

Минимальный набор входов:

- raw JSON с пробелами, CRLF и UTF-8;
- ровно один lowercase `json` fence;
- prose до/после, два объекта, два fence, неверный fence tag;
- duplicate keys, trailing comma, `NaN`, `Infinity`, `-Infinity`, `1e999`;
- truncation, invalid UTF-8, lone surrogate, excessive nesting;
- refusal, incomplete, wrong status/type и пустые обязательные поля;
- `orderId`, `executor`, `version`, `schemaId`, `inReplyTo`, sender/recipient
  roles и `objectiveId`;
- числа около `2^53`, bool вместо int и int вместо bool;
- legacy V1 без handoff и custom schema override.

Проверь, что:

- лишний текст не принимается как JSON;
- duplicate keys и non-finite числа отвергаются до schema acceptance;
- raw evidence сохраняется, normalized bytes не выдаются за raw;
- отказ/incomplete не превращаются в `done`;
- executor не может сам назначить себе роль, reviewer, objective или terminal
  acceptance;
- canonical routing берётся из `AQUILA_ROUTING_JSON_V1:` в
  `notesForExecutor`, а не из удобного неподтверждённого поля;
- ошибка упаковки не скрывает первичную refusal/incomplete/format причину;
- одинаковые правила действуют в Python, shared JS, Claude и AGY.

Отдельно проверь `validate_handoff_order(..., routing=None)` на трёх fixtures:
явный routing с неверным objective; routing не передан, metadata существует
только в `notesForExecutor`; top-level `order.routing` противоречит canonical
metadata. Зафиксируй фактический результат каждого случая, не подгоняй его под
ожидание PASS. Проследи прямые и транзитивные callers, включая
`validate_response_handoff()`: где routing извлекают, что происходит при None.
Helper-level пропуск проверки не доказывает достижимый production bypass.
Для такого вывода необходима цепочка через реальный entrypoint до acceptance.
Если нужна только защита от будущего misuse, укажи `LIMITATION` и отдельно
необязательную рекомендацию. В новом отчёте укажи правильные ссылки вместо
неверных ссылок старого отчёта; сам старый файл не редактируй.

Для каждого класса входов из раздела 7 сделай матрицу Python/shared JS/Claude/AGY:
expected, observed, error code, raw/canonical/acceptance effects, test/log path.
Отмечай применимость поля к конкретной схеме. Различия числовых представлений
проверь на реальном решении о принятии, а не только на парсинге.

## 8. Custody, evidence и lineage

Проверь реальные call sites, а не только helper:

- preflight -> launch -> closure -> proof -> acceptance;
- direct custody для ordinary non-lineage/non-advisory;
- Gateway для lineage и Astra advisory;
- create-only result/evidence/receipts и collision/retry;
- live-byte SHA-256, mediaType, size и path scope;
- symlink leaf/ancestor, traversal, alias, directory/FIFO, missing evidence;
- partial write, timeout, nonzero exit, early candidate, unknown response;
- сохранение первичной причины synthetic failure;
- inputResults до launch, после proof и перед acceptance;
- predecessor result/start/closure/proof/acceptance identity и hashes;
- cycles, duplicates, current-order reference, common ancestor, depth/size;
- drift после preflight, во время executor, после proof и перед acceptance;
- запрет replay того же orderId после side effect;
- same-UID authorship и concurrent modification window как явные пределы.

Проверь отдельную цепочку fake CLI:

`Astra advisory -> Sol/Luna implementation -> independent Opus review -> controller closure`.

Подтверди чтениями и hashes, что входы реально проверяются в каждой точке.
Названия стадий и строки `PASS` без bindings доказательством не являются.

## 9. Иерархия, роли и модели

Сопоставь документацию с фактическими launch arguments, routing metadata,
overrides и receipts:

| Уровень | Проверяемая граница |
| --- | --- |
| Boss -> controller -> OPTIO/task owner | scope, objective, budget и acceptance задаются сверху |
| GPT-6 Luna/Sol | исполнение по complexity/risk/ambiguity/evidenceNeed; effort отдельно от model |
| GPT-6 Astra | только bounded read-only ARCHITECTUS advisory; не final reviewer |
| Claude Opus 5 | независимая проверка; не исправляет и не принимает свою реализацию |
| Gemini 3.8 Flash | UI/design/text/creative через AGY; не назначается на backend/security без явного правила |

Проверь запреты на self-approval, review-of-review, terminal-gate bypass,
objective substitution, reviewer substitution, silent downgrade и budget-based
downgrade. Проверь V0/V1/V2/V3, evidenceNeed=high, PRE/POST и
`deterministicFailureOracle`. V3 должен оставаться заблокированным без trusted
approval verifier. Датированные исторические модели не считай активным drift без
доказательства фактического использования.

## 10. P1-1 и границы remediation

Статически и в изолированной scratch-установке проверь helper:

- staging, SHA-256, modes, backup/rollback;
- foreign files, symlink rejection, partial failure;
- negative TLS с недоверенным сертификатом;
- различие atomic helper и транзакционности полного `install.sh`.

Live install запрещён. В отчёте отдельно отметь, что live install, provider
calls и TLS в установленной Claude-библиотеке не проверялись. Не утверждай её
текущее состояние по старому отчёту. Same-UID/authorship и concurrent-writer
гарантии оцени в пределах fixtures; не переноси их на live среду.

## 11. Обязательные критерии verdict

Выбери ровно один verdict в следующем порядке:

1. `FAIL`: доказан P0/P1 либо нарушение обязательного contract/acceptance
   независимо от серьёзности. Незавершённые проверки перечисли дополнительно.
2. `INCOMPLETE`: нет основания для FAIL, но источник/зона пропущены или любая
   обязательная offline-команда не завершена успешно. Гипотеза о harness или
   инфраструктуре не закрывает этот пробел.
3. `PASS_WITH_LIMITATIONS`: все обязательные offline-проверки завершены успешно,
   источники прочитаны, нарушения acceptance не найдены; остаются только явно
   согласованные границы — отсутствие live proof, fake CLI, same-UID/race,
   частичность P1-1. Для каждой границы укажи ссылку на согласованное решение.
4. `PASS`: то же покрытие без существенных оговорок внутри заявленного scope;
   это не утверждение о live готовности. Нельзя скрывать ограничения сменой scope.

Нельзя использовать `PASS` при любом непрочитанном обязательном источнике.
Нельзя называть smoke PASS, если exit code ненулевой, процесс убит timeout или
проверена только часть suite. Нельзя считать индивидуальные регрессии заменой
общего smoke.

## 12. Формат итогового отчёта

Отчёт должен содержать следующие разделы в этом порядке:

1. `Verdict` с одним из четырёх значений и строгим основанием.
2. `Scope and integrity`: HEAD, dirty state, исходные/финальные hashes,
   изменённые во время аудита файлы.
3. `Source attestation`: каждый обязательный источник и использованные строки.
4. `Findings`: ID, класс доказательства, severity, file:line, воспроизведение,
   влияние, минимальный фикс и regression proof. Для решения укажи затрагиваемые
   функции, совместимость, зависимости и ожидаемый тест до/после; не применяй фикс.
5. `Mandatory command matrix`: команда, exit/signal, duration, log path,
   доказано, не доказано.
6. `Previous-report corrections`: отдельно AGY path/result, Hermes timeout,
   пропущенный disagreement document и O-001 fallback.
7. `Role/model/hierarchy matrix`.
8. `Acceptance matrix`: P1-1/P1-2/P1-3/P2-1/P2-2/P2-3 — выполнено/частично/
   не выполнено/не проверено, актуальный критерий, доказательство, открытое условие;
   P2-4 — отложен.
9. `Remediation proposals`: минимальные исправления по приоритету с точным proof;
   необязательные улучшения отдельно. Не предлагай технологии без доказанной пользы.
10. `Open limitations`: только реально непроверенные вещи.
11. `Integrity close-out`: сравнение manifest, scope проверки неизменности,
    полный список собственных файлов. Не приписывай неизвестные изменения другим
    процессам без доказательств и не откатывай чужие правки. Отдельно напиши
    `No-change attestation`: подтверждена ли неизменность исходников, тестов,
    схем, инструкций и конфигурации в пределах проверенного manifest. Любое
    расхождение перечисли, не заверяй неизменность без доказательств; собственные
    scratch-файлы перечисли абсолютными путями.

Для каждого отсутствующего или непроверенного доказательства напиши `NOT
PROVEN`, а не `PASS`. В финальном сообщении укажи абсолютный путь отчёта,
verdict, количество `CONFIRMED_DEFECT`, `TEST_FAILURE`, `AUDIT_ERROR`,
`LIMITATION`, а также команды, которые не завершились.

Достоверно укажи активную модель только по уже доступным runtime-сведениям.
Если её нельзя подтвердить без внешнего обращения, напиши `NOT PROVEN`;
самоописание «я Opus 5» не является доказательством. Для каждого исправления
старого отчёта приведи старое утверждение, новые данные и степень вывода:
подтверждено/опровергнуто/не воспроизведено/не доказано. Успешный повтор не
доказывает, что прежнего сбоя не было. Закончив файл отчёта, остановись.

Итоговая рекомендация остаётся рекомендацией. Этот аудит не даёт полномочий
внедрять исправления, менять routing или начинать P2-4/JEV.
