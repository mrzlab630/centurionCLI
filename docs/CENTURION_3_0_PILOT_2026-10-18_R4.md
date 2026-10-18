# CENTURION 3.0 — завершение пилота r4, 18 октября 2026

Кандидат **3.0.0-rc.1**, ветка `feat/centurioncli/v3-implementation`.
Основание продолжения — поручение владельца `do it`. Этот отчёт дополняет
[r3](CENTURION_3_0_PILOT_2026-10-17_R3.md), не изменяя исторических результатов.
Рабочая установка пока не выполнена; её результат фиксируется отдельно ниже.

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

Новые дефекты P6 и окончательные skills переданы отдельным ограниченным
continuation review: один запрос, ≤300 с, Opus 5.5/high, без tools и writable
product paths. Локальный маршрут задаётся явно через
`ANTHROPIC_BASE_URL=http://127.0.0.1:8317` и
`ANTHROPIC_DEFAULT_OPUS_MODEL=claude-opus-5-5`; новые credentials, `/login`
и публичный fallback не используются. Receipt и вердикт —
`control/p6-delta-review/`. Итог ревью и локального внедрения ещё ожидается.

## Локальное внедрение

До переключения требуются актуальное source review, сохранённые evidence,
commit текущего кандидата, свежие installer dry-runs, no-new-work drain,
точные backups, последовательная установка Codex → Claude → Hermes,
manifest/prefix readback и безопасный Gateway canary. На провале — восстановление
только изменённых manifest-owned файлов из проверенной резервной копии.
Push, публикация и release tag не входят в поручение.
