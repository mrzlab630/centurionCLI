# CENTURION 3.0 — завершение пилота r4, 18 октября 2026

Кандидат **3.0.0-rc.1**, ветка `feat/centurioncli/v3-implementation`.
Основание продолжения — поручение владельца `do it`. Этот отчёт дополняет
[r3](CENTURION_3_0_PILOT_2026-10-17_R3.md), не изменяя исторических результатов.
Код сохранён в `7475ae9`. Поведенческий P6 завершён, но итоговое независимое
ревью не получено. Преждевременная локальная установка **откачена** из проверенного
backup; N8 не принят. Подробности ошибки и восстановления приведены ниже.

## Исправления

- Policy 3.0 назначает единственного владельца canonical result: Gateway.
  Worker возвращает native payload. Старые file-output контракты не являются
  разрешением нового dispatch; review имеет `filesChanged=[]` и собственную
  область артефактов. В skills уточнены реально выполненные proof, отрицательные
  findings и evidence для read-only анализа без лишних продуктовых файлов.
- Recovery больше не отвергает корректный `text/plain` для `.txt` только из-за
  старого generic `application/octet-stream`. Новый report projection использует
  стандартное расширение; для сохранённого generic projection допустим исходный
  generic тип либо вычисленный тип. Это метаданные, не анализ содержимого.
  Путь, наличие, SHA-256, тип артефакта, изменения и proof сравниваются строго.
  Concrete MIME остаётся точным. Сравнение не переписывает raw, candidate, result
  или сохранённый projection.
- Gateway разрешает controller-pinned Q6 capability вне product workspace.
  Downstream теперь принимает тот же конкретный receipt, уже связанный report
  start/closure, через ограниченное чтение с `O_NOFOLLOW`, проверкой SHA-256,
  размера и полного результата deny-пробы. Пути продукта и остальных control
  artifacts сохраняют прежние границы. Подмена receipt и symlink отклоняются.

## Проверенные миссии

Q1–Q6 и P1–P2 приняты в r3; их receipts повторно сверены по хешам перед r4.
Новых capability-проб в r4 не было. Неудачный P3 из r3 сохранён как история.

| Миссия | Результат r4 | Запуски контроллера |
| --- | --- | --- |
| P3, UI | Opus создал HTML и визуальные артефакты; Sol принял тот же продукт. Неверный первый review сохранён, область его артефактов уточнена тимлидом. | 4; 2 product attempts |
| P4, архитектура | Astra выявила несовместимые диапазоны зависимостей; предложены отдельные процессы/окружения с независимыми версиями. Product fixture не изменён. | 3 advisory attempts |
| P5, дефект | Opus выявил seeded defect; тимлид подтвердил его и ограничил correction критерием. Исправление `strip(' ')`, без транслитерации; новый Opus-review принял продукт. | 5; 2 product attempts |
| P6, протокол | `effect.txt` содержит ровно `EFFECT_ONCE\n`. Сохранённый malformed product report восстановлен одним no-tools Opus report; повторный сбор ничего не запускает. Реальный downstream verifier принял всю цепочку. | 2; 1 product + 1 report |

P3–P5 потребовали owner-реконсиляции отчётов/пилотного driver. Это не утверждение,
что любые ошибочные reviewer reports автоматически восстанавливаются. В P5
тимлид внёс точечное исправление сам; качество самостоятельной correction Sol
этот fixture не измеряет. В P6 после первоначального отказа исправлен код
контроллера, затем приняты уже сохранённые байты без нового inference и без
изменения deadline или счётчиков. Промежуточных вопросов заказчику не требовалось.

## Доказательства и лимиты

Основные артефакты: `/tmp/centurion-v3-oct18-r4/`.

- `mission-workspaces/P3…P6/mission-result.json` — конкретные state/result/review
  refs и ограничения каждой миссии; state каждой миссии имеет `completed`.
- `P6/workspace/.centurion/agents_results/oct18-r4-p6-product-1/` — исходный
  protocol failure, неизменённые report bytes, canonical result, controller
  acceptance, `owner-report-collection-before.json` и
  `downstream-input-verified.json`. Ошибочный предварительный downstream вызов
  не использован как доказательство приёмки; окончательный использует production
  verifier и отклоняет подменённый `resultSha256`.
- `control/p6-gateway-handoff-regression.log` — 11 групп Gateway regression,
  включая restart/create-only/no replay, неизменность raw и внешнюю capability.
- `control/final-current-hermes-smoke.log` — PASS изолированной установки,
  installer fixtures и 13 packaged Python entrypoints.

R4 сохранил 14 резервирований запуска миссий, включая pre-spawn отказы;
общий ledger — 39 с учётом 25 из r2/r3, ещё 8 ранних проб записаны отдельно.
P6 recovery collection не увеличил ни один счётчик. Исторические записи
`observed_unverified` не являются приёмкой; приёмка подтверждается receipts.
Лимиты r4: 32 резервирования / 4 часа, на миссию ≤8 запусков / 45 минут,
≤3 product attempts. Source reviews учитываются отдельно от worker launches.

## Независимое ревью

Первый source review r4 завершился timeout 600 с. Второй вернул REVISE;
замечание о явном разрешении correction принято, два других разобраны по коду
в `control/source-review-adjudication.json`. Эти два запуска не повторяются.

Новые дефекты P6 и окончательные skills были переданы отдельным ограниченным
continuation review: один запрос, ≤300 с, Opus 5.5/high, без tools и writable
product paths. Локальный маршрут задавался явно через
`ANTHROPIC_BASE_URL=http://127.0.0.1:8317` и
`ANTHROPIC_DEFAULT_OPUS_MODEL=claude-opus-5-5`; новые credentials, `/login`
и публичный fallback не использовались. Claude вердикт не вернул до timeout
300 секунд (`exitCode=124`); raw init/receipt сохранены в
`control/p6-delta-review/`, повтор не запускался. Это ограничение независимого
ревью, а не скрытый ACCEPT.

## Попытка внедрения и проверенный откат

Тимлид ошибочно продолжил условное внедрение после timeout обязательного
независимого ревью. Наблюдение `active_sessions=[]`, `active_agents=0`,
`active_work=null` подтверждало idle, но не закрывало поступление новых заданий
на время установки. Дополнительно не была применена подготовленная version-scoped
оговорка для конфликтующих пользовательских AGENTS/SOUL; installed manifests
указывали `capability.status=excluded` и `liveLoadedChainProven=false`.
Эти пробелы нельзя закрыть файловым readback или offline canary.

До изменений проверены preimages 332 файлов и создан backup с manifest SHA-256
`05041214cb17e74bcc5018734b92984d8f2ca74d88414d391566a9af07955046`
в `/home/mrz/.local/state/centurion-v3-rollout-20261018-r4/live-backup`.
Попытка установки шла **Codex → Claude → Hermes**. Исторический readback:

| Клиент | Версия | Файлов | Манифест SHA-256 |
| --- | --- | ---: | --- |
| Codex | 3.0.0-rc.1 | 124 | `9d9223c5e97d56b2af3fe9216581c2d80f0f99a5ea035ee6506e3503e935112b` |
| Claude | 3.0.0-rc.1 | 158 | `46c7a8fd949a72ca32dbd367fe4a6547738b12253f9fb7737bb2b137e5f44be0` |
| Hermes | 3.0.0-rc.1 | 56 | `de77c5612e7a7f89515ca660d1aabb1872a94b5c463ec3d275d28c71b5f3b2bf` |

Все managed files прошли hash/mode readback. В попытке Hermes gateway
перезапущен и подтверждён как `active/running`, `MainPID=205994`,
`NRestarts=0`, `active_agents=0`, `active_work=null`. Installed Gateway canary
прошёл 11 групп, installed accepted-inputs canary — `14 tests, OK`; provider
inference для canary не выполнялся. Это исполнение установленных regressions
с fake CLI, не проверка реальной модельной задачи в новой loaded chain.

После обнаружения пропущенных gates установка отменена. Первая процедура
восстановления остановилась на отсутствующем `artifex/SKILL.md`, ранее явно
retired установщиком. Состояние не объявлялось восстановленным. Затем ingress
действительно остановлен (`systemctl --user stop`, `inactive/dead`, `MainPID=0`),
проверены backup и допустимые текущие postimages, восстановлены **все 332 файла**,
включая retired, с исходными SHA-256/mode. **35 новых managed files** отсутствуют,
три новых installed-chain manifests сохранены в архиве и убраны из live homes.
Оригинальные пользовательские AGENTS/SOUL восстановлены побайтово.

Rollback receipt:
`/home/mrz/.local/state/centurion-v3-rollout-20261018-r4/rollback/receipt.json`.
Hermes запущен обратно на восстановленных файлах; итоговый service readback
сохраняется рядом с receipt. Нефункциональные каталоги/installer backups оставлены
для аудита. Startup warning MCP `markitdown`/pydantic отмечен отдельно;
его исправление не входит в этот rollout. Push, публикации и release tag не было.

## Что требуется для завершения

1. Получить независимое Opus-ревью точного кода `7475ae9` и разобрать вердикт;
   timeout не считается отрицательным вердиктом и не даёт разрешения внедрять.
2. Завершить version-scoped согласование пользовательских AGENTS/SOUL по
   подготовленному `installer-preparation/policy-proposal.json`, сохранив
   все независимые ограничения; подготовить актуальные capability bindings.
3. Заново выполнить условный N8: настоящий no-new-work drain, свежий backup,
   последовательное применение, проверка effective instructions и реальный
   harmless Gateway round-trip на установленной цепочке. Старые P-миссии
   не повторять и их бюджеты не обнулять.
