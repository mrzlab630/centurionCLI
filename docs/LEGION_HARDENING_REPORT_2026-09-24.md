# Усиление взаимодействия легионеров: 2026-09-24

Checkout: `/home/mrz/projects/al/centurionCLI/worktrees/centurion-main`.
Статус: P2-3 и оставшийся repository-срез remediation реализованы и проверены
офлайн. Финальное review Claude Opus 5 пользователь проводит самостоятельно.
Установка, деплой, изменение локальной конфигурации и внедрение JEV не выполнялись.

## Суть системы и граница работы

CENTURION объединяет канонические роли/skills, интеграции Codex, Claude,
Antigravity и Hermes, контракты делегирования и контроллер приёмки. Роль,
исполнительный CLI и модель являются разными сущностями. Цепочка полномочий:
Boss задаёт цель, Aquila/CENTURION принимает работу, OPTIO организует её,
назначенный специалист исполняет ограниченное задание.

Изучен `CLAUDE_OPUS_DISAGREEMENTS_2026-09-24.md`. Сохранены его решения:
direct custody для простых non-lineage/non-advisory заказов; Gateway для
lineage/advisory; create-only canonical result; отдельное решение controller
acceptance. Предыдущие незакоммиченные remediation-изменения сохранены.
Этот отчёт описывает дополнительное усиление, а не весь diff относительно HEAD.

## Исправлено

| Проблема | Изменение | Проверка |
| --- | --- | --- |
| Loop V1 не связывал ревью с назначенной целью и уровнем проверки | Controller сохраняет `candidate.resultSha256` и `reviewContract`: objectiveId, taskClass, verificationProfile, reviewer. Проверяет их перед dispatch и перед завершением review; смена цели, понижение gate, отсутствующий/изменённый JSON и symlink отклоняются. | Регрессии handoff |
| Явное повышение проверки терялось при выборе маршрута | `select_review_route` сохраняет объявленный повышенный профиль; terminal review выбирает `terminal_closure` и `reviewer=none`. | Routing и handoff |
| Проверяющий мог сообщить исправления продукта в собственном review | Runner и builder отклоняют terminal result с непустыми `filesChanged` или `selfReview.fixesApplied`. Исправления возвращаются владельцу отдельным заданием. | Builder и direct runner |
| Отказ terminal-result проверки выходил через непойманный `RoutingError` | `verify_result` переводит ошибку в `RunnerError`; runner закрывает direct custody как `rejected`. До исправления новый тест воспроизвёл traceback; после исправления проверяет start/closure/acceptance. | Новый subprocess regression |
| Gemini не имел явного маршрута, связанного с ролью и CLI | `gemini-3.8-flash` разрешён через `agy` для творческих ролей, только implementation, effort low/medium/high. Проверяются реальные CLI flags, дубликаты и смена сессии; текст prompt не считается настройкой. | Routing и launch regressions |
| Инструкции не разделяли достаточно явно подчинённость, помощь и приёмку | Уточнены controller/task owner, передача входных артефактов, disjoint write ownership, эскалация блокеров, запрет самоповышения и самостоятельного изменения scope. | Skill eval и Claude surface audit |

Основные реализации находятся в
`integrations/hermes-legion-kit/skills/autonomous-ai-agents/agent-contract-runner/scripts/`:
`review_ladder.py`, `agent_contract_runner.py`, `agent_result_builder.py`,
`regression_legion_handoffs.py`. Инструкции согласованы в `CLAUDE.md`,
`skills/orchestrator/SKILL.md`, `skills/reviewer/SKILL.md`, Hermes orchestration,
routing policy/reference, `docs/LEGION_CONTRACTS.md` и Antigravity routing rules.

## Распределение моделей

| Модель | Назначение |
| --- | --- |
| GPT-6 Luna | Ясная ограниченная реализация на medium; none/low только для подходящей точной механической работы. High для нетривиальной реализации, review или повышенной потребности в доказательствах. |
| GPT-6 Sol | Сложная реализация, существенная неопределённость, диагностика и задачи с высокой ценой ошибки. |
| GPT-6 Astra | Ограниченная read-only консультация ARCHITECTUS по архитектуре и сложным вопросам; не финальное принятие реализации. |
| Claude Opus 5 | Независимая проверка исполнителей и возврат конкретных замечаний controller. |
| Gemini 3.8 Flash | UI, дизайн, тексты, локализация и творческие задачи через agy с назначенной профильной ролью. |

Совместимость V0/V1 сохранена: низкорисковая полностью проверяемая задача может
завершаться без модели-reviewer; V1 Sol остаётся для соответствующих non-Codex
заказов. Codex-заказ с пробелом в proof требует V2/Opus. Терминальный reviewer
не назначает ещё одного reviewer. Модели не образуют дополнительных командных
уровней. Эти проверки подтверждают правила маршрута, но не факт исполнения
запроса конкретной моделью у провайдера.

## Запрос про JSON и Markdown

**P2-3 реализован.** Сохранены `AGENT_ORDER_JSON_V1`/`AGENT_RESULT_JSON_V1`;
`outputContract.handoff` включает совместимый `AGENT_HANDOFF_V1` с привязкой к
orderId, sender/recipient role, schema и routing objective. Ответ обязан точно
повторить declared handoff. Старые V1 fixtures продолжают проходить.

- Python `response_envelope.py` и JS contract helpers принимают raw UTF-8 JSON
  или один чистый lowercase `json` fence, включая CRLF. Остальные обёртки,
  surrounding prose, несколько документов/fences, duplicate keys, NaN/overflow,
  invalid UTF-8, lone surrogate и truncation отклоняются.
- Builder сохраняет raw bytes и normalized candidate отдельно, create-only,
  добавляет controller-owned `responseEnvelope` с SHA-256/размерами/transport.
  Runner проверяет raw -> normalized -> canonical binding и повторяет проверки
  evidence после proof. Executor не может добавить собственный envelope.
- Существующие артефакты при opt-in handoff имеют `mediaType` и `sha256`;
  controller сверяет фактические bytes. Ошибки имеют коды FORMAT, SCHEMA,
  IDENTITY, REFUSED или INCOMPLETE с префиксом `RESPONSE_`.
- Codex/Claude Gateway поддерживает нормализацию candidate, Claude stdout и
  inner terminal result. Старые terminal/model/permission/tool-loop checks
  сохранены. Controller-generated failure сохраняет первичную причину.
- Claude/AGY guards используют общий ingress, optional `--handoff`, проверку
  finalized envelope и artifact hashes. AGY bundled contract синхронизирован.
  Для direct Hermes/AGY и ordinary Codex/Claude добавлен opt-in
  `launch.candidateJsonPath`; legacy canonical путь остаётся строгим JSON.
- Нет автоматического replay, эвристического извлечения JSON из прозы или
  замены blocked/failed на done. Canonical result не переписывается.

Provider-native structured output не объявлен проверенным: используется
документированный file fallback, пока активный runtime не подтвердит поддержку.
Дополнительный сетевой протокол/фреймворк и новые зависимости не добавлялись.

## Завершение repository-remediation

| Пункт | Результат текущего этапа | Граница |
| --- | --- | --- |
| P1-1 | Повторно проверены staged helper, SHA-256/режимы/rollback и negative TLS в тестовой установке, 4/4 | Полный live install.sh и live TLS остаются отдельной командой; весь installer не является одной атомарной транзакцией |
| P1-2 | Direct runner/Gateway регрессии проходят, create-only custody и отдельная acceptance сохранены | Direct разрешён для ordinary non-lineage/non-advisory; Gateway для Astra/lineage |
| P1-3 | Добавлен `accepted_inputs.py`: explicit predecessor result/acceptance/closure pins, selected control-artifact hashes, nested chain, проверки до dispatch и после proof | Gateway inputs не расширяют write scope; product lineage отдельно; same-UID/race/authorship ограничения сохраняются |
| P2-1 | Парные evidenceNeed low/high и minimum effort проходят | Качество моделей на реальных задачах не измерялось |
| P2-2 | PRE/observed POST разделены, actual proof управляет acceptance; semantic oracle удалён из POST и оставлен только в legacy wire shape | Не заявляется независимая семантическая проверка oracle |
| P2-3 | Общий response contract, Python/JS adapters, backward compatibility и package proof | Native provider/live proof и final Opus review отдельно |

Новая регрессия проводит реальную Gateway-process цепочку с fake CLIs:
`gpt-6-astra/ARCHITECTUS advisory -> gpt-6-sol implementation + lineage ->
claude-opus-5 terminal_review`. Вложенные accepted inputs и product anchors
проверены. Изменённый predecessor acceptance/artifact блокирует запуск до
побочных эффектов. Изменение входа required proof после запуска сохраняет
canonical `done`, но даёт acceptance `rejected`. Даже после восстановления
старых bytes повтор отклоняется как create-only collision, side effect не
выполняется снова. Это proof локального контроллера, а не вызов реальных моделей.

## JEV: решение и план оценки

В remediation plan добавлен **P2-4**. Изучены исходники `jev-router` на коммите
`38da6b84ea01241bfc41fbddc0928d0f40a703f0` и первичные документы TypeSafe.
**Готовую CLI/proxy-обёртку сейчас не внедрять:** она выбирает модель на ходе,
может менять effort и допускает fallback на нижний tier; её контракт не
учитывает наши полномочия, review floors и закреплённый маршрут заказа.
Улучшение стоимости/скорости/качества на CENTURION не доказано.

Возможная узкая польза — advisory-подбор skill/исполнителя при неоднозначной
задаче до создания order или классификация blocker. Сначала нужно подтвердить
проблему текущего выбора; затем сравнить с baseline и простыми локальными
правилами. В плане определены shadow comparison, отдельный безопасный replay
для измерения исполнения, полная стоимость принятого результата, p50/p95,
повторы, отрицательные проверки и go/no-go. Jev не получает право принимать
работу, ослаблять gate или исправлять JSON. Публичный пример TypeSafe с Hermes
skills рассматривается как гипотеза, не как доказательство пользы здесь.
Источники и границы приведены в P2-4. JEV не устанавливался, API не вызывался.

## Проверки

Предыдущий этап иерархии (сохранённые результаты):

```text
integrations/hermes-legion-kit: npm run smoke -> PASS
  Изолированная временная установка; 7 skills, 1 shared capability, 4 bundles;
  6 packaged Python regressions, включая новые handoff checks.
integrations/antigravity-legion-kit: npm run smoke -> PASS
node skills/tester/scripts/legion-skill-eval.mjs -> 9 checks PASS
node integrations/claude-legion-kit/scripts/claude-surface-audit.mjs --repo-only -> PASS
  38 canonical skills, 37 plugin agents, 37 routing evals, 0 high-overlap pairs.
python3 regression_legion_handoffs.py -> 12/12 PASS
python3 regression_agent_contract_runner.py -> PASS
git diff --check -> PASS
```

Python-команды выше выполнялись из каталога scripts contract runner с
`PYTHONDONTWRITEBYTECODE=1`. Последние две Python-проверки выполнены после
исправления `RoutingError`. Hermes package smoke целиком повторно прошёл после
этой поправки и согласования инструкций: Luna `medium` для routine work,
`high` при повышенных требованиях задачи и доказательств.

Дополнительный независимый Codex reviewer подтвердил исходные дефекты и после
правок не нашёл новых проблем в ограниченном diff; самостоятельно получил
12/12 PASS. Это не заменяет требуемый Opus gate.

### Итоговая проверка P2-3/remediation

Из корня checkout, `TMPDIR="$PWD/.centurion/p2-3-proof/tmp"` и
`PYTHONDONTWRITEBYTECODE=1`:

```text
node integrations/legion-contracts/scripts/smoke.mjs -> PASS
node integrations/codex-legion-kit/scripts/smoke.mjs -> PASS
node integrations/claude-legion-kit/scripts/smoke.mjs -> PASS
node integrations/antigravity-legion-kit/scripts/smoke.mjs -> PASS (full)
node integrations/hermes-legion-kit/scripts/smoke.mjs -> PASS
  isolated test installation, 7 skills, 1 shared capability, 4 bundles;
  10 packaged Python regressions, including response, inputs and Gateway chain.
node --test tests/install-owned-files.test.mjs -> PASS, 4/4
node skills/tester/scripts/legion-skill-eval.mjs -> PASS, 9 checks
node integrations/claude-legion-kit/scripts/claude-surface-audit.mjs --repo-only -> PASS
bash -n install.sh -> PASS
git diff --check -> PASS
```

Логи текущего proof находятся в `.centurion/p2-3-proof/logs/`.
Hermes smoke исполняет routing, runner, builder, Gateway, response-envelope,
artifact-lineage (11/11), accepted-inputs (14/14), accepted-inputs-Gateway,
execution-state и legion-handoffs (12/12). После переноса двух старых regression
fixtures с фиксированного `/tmp` на `TMPDIR` routing/runner проверены ещё раз.
Во время ранних прогонов эти старые тесты создавали только временные `/tmp`
fixtures; живые приложения, настройки и сервисы не менялись.

Дополнительный read-only просмотр нашёл и помог закрыть objective/role mismatch,
Unicode transport crash, потерю исходной причины synthetic failure и проверку
symlink после resolve. Последний случай закреплён отрицательной регрессией.
Финальное независимое Opus review остаётся за пользователем.

## Незавершённое и ограничения

- В предыдущем этапе Opus 5 review пытались выполнить с read-only tools и explicit model/effort.
  Минимальный CLI вернул `Not logged in`; обычная авторизация в safe mode
  вернула `401 API key is invalid`, `modelUsage={}`. Успешного вызова модели
  не было. Авторизация и конфигурация не менялись. Задание и сырые результаты:
  `.centurion/agents_results/hierarchy-review-20260924/`.
  В текущем P2-3 этапе повторов внешнего вызова не было: пользователь выполняет review сам.
- `resultSha256` защищает JSON кандидата. Байты продукта этой проверкой не
  замораживаются; запрет `filesChanged` проверяет контракт отчёта и сам по себе
  не доказывает отсутствие скрытых записей. Snapshot/guard и OS isolation
  остаются отдельной границей доказательства.
- Старый routed Loop V1 state без binding требует восстановления controller
  из принятого execution evidence. Автоматической миграции таких состояний нет.
- Сохранены известные ограничения lineage/same-UID, внешних allowedPaths и
  statePath. Semantic failure oracle не считается наблюдаемым proof. Loop V1 + lineage не поддерживается;
  V3 блокируется до trusted approval verifier.
- Live установка, реальная цепочка всех моделей, provider-selected model proof
  и качество Luna/Sol/Gemini на пользовательских задачах не проверялись.
  Ранее отмеченный Opus риск live-копии библиотеки Claude в этом этапе не
  перепроверялся и не устранялся: локальная установка вне scope.
- Коммит и изменения рабочих конфигураций Hermes/Codex/Claude не выполнялись.
- JS Number не сохраняет точные integer значения выше `2^53-1`; такие IDs/числа
  нужно передавать строками. Raw/normalized bytes сохраняются точно.
- `inputResults` ограничен read-only control files с явными pins и bounded
  nested chain. Это не изоляция от процесса, способного переписать все receipts
  и trusted pins под тем же UID.
