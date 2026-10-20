# CENTURION 3.0 — пилот r3, 17 октября 2026

Кандидат **3.0.0-rc.1**, ветка `feat/centurioncli/v3-implementation`.
Исторический результат r3 сохранён ниже. Продолжение P3–P6 и исправления
восстановления отчёта описаны в [пилоте r4](CENTURION_3_0_PILOT_2026-10-18_R4.md).
Рабочая установка не выполнена: N7 остановлен на P3. Основание прохода — поручение
владельца `do it` после остановки r2 на области артефактов ревьюера.

## Исправление и проверка

Review-заказ разрешает только точные product files из сохранённого snapshot
кандидата и собственный custody namespace. Недостающий файл, лишний файл,
каталог, рекурсивный product path и запрещённый файл отклоняются до расхода
запуска. Advisory остаётся без product scope. Сам список путей не является
OS sandbox: неизменность продукта проверяется при сборе результата и приёмке.

Принятое ревью можно повторно получить после приёмки продукта без нового
запуска. Новый review intent для уже принятого продукта не допускается.
Регрессии воспроизводят ссылку ревьюера на неизменённый product artifact,
отказ при изменении продукта и повторный сбор без изменения счётчиков.

Сфокусированные проверки: mission lifecycle — 13 групп, V3 Gateway — 11,
result builder — 22, accepted-input chain — 3. Полный Hermes smoke прошёл
в изолированной установке с packaged regressions. Это offline proof;
локальная рабочая установка из него не следует.

После P3 исправлен общий `skills/orchestrator/SKILL.md`: для Gateway-managed
policy 3.0 worker возвращает авторский payload через native adapter, а только
Gateway создаёт канонический `outputContract.resultPath` и controller receipts.
Явные file-output contracts вне Gateway сохраняют собственное назначение.
Согласованы packaged runner skill и reviewer: его `filesChanged=[]`, файлы
предшественника относятся к `artifacts`. Native-схема ещё допускает непустой
`filesChanged` ревьюера; семантический validator его отклоняет.

Добавленная V3 regression воспроизводит прямую запись worker в canonical path:
Gateway сохраняет файл, фиксирует collision, не принимает результат и не
повторяет продукт при restart. Это проверка отказа в приёмке, а не OS-запрет
на запись control namespace. Полный installed Hermes smoke после правки прошёл
(`/tmp/centurion-r3-final-hermes-smoke.log`); три изменённых skills прошли
`quick_validate.py`.

## Ограниченное исполнение

Управляющие артефакты: `/tmp/centurion-v3-oct17-r3/control`.
Фиксированные P1–P6: `/tmp/centurion-v3-oct17-r3/mission-workspaces`.
Ключевые receipts, source-review input/raw, P1/P2 results и P3 collision evidence
сохранены побайтово вне `/tmp` в
`.centurion/v3-local-rollout-20261017-r3/evidence/` с `archive-manifest.json`.
Это выборочный архив, не полная копия client homes или всех tool traces.
Исходный fixture SHA-256:
`729cf091b26c6e970831bd5e83ee686830abd41e1f40b6c701a8a3e6a98180e4`.

Унаследованные Q receipts и stage сохранены в `pre-refresh`; они не являются
приёмкой r3. Перед Q1 три изолированных пакета заново установлены из исходника
`684c67a`, installed manifests сверены, все 29 runtime scripts совпали побайтово
(`control/preflight-current.json`). Исправление инструкций после P3 проверено
отдельным installed smoke; существующие live receipts не переиздаются.

Лимиты: Q1–Q6 ≤8 запусков / 30 минут; каждая P-миссия ≤8 запусков / 45 минут,
≤3 product attempts; общий предел 56 запусков / 5 часов. Счётчик дополнительно
сохраняет 14 запусков r2, ранние 8 запусков отмечены отдельно. Новое окно
стартовало после подготовки; прежние миссии не возобновлялись и не менялись.
Source review отдельно ограничен двумя запросами по 600 секунд.

В r3 израсходовано 11 модельных запусков: 6 capability, P1 один, P2 три,
P3 один. Общий `modelLaunchesUsed=25` включает 14 r2; ранние 8 сохранены
отдельно. Некоторые записи ledger имеют `observed_unverified`: приёмка P1/P2
подтверждается mission results и controller receipts, не этим счётчиком.

## Результаты пилота

| Проба | Результат и доказательство |
| --- | --- |
| Q1 | Hermes / Sol high: terminal, search → найденный primary URL → extract |
| Q2 | Luna high: реальное чтение инструментом и native structured output |
| Q3 | Astra high: read-only анализ несовместимых диапазонов |
| Q4 | Opus high: native Read и Context7 resolve/query через local proxy |
| Q5 | Sol high: Playwright, 390×844, screenshot и native image-tool receipt |
| Q6 | Production report launcher: реальный OS deny записи, неизменный продукт, отключённые local tools/MCP/hooks, наблюдаемые server search/fetch = 0 |

Все шесть свежих Q прошли с первой попытки. Receipts — `control/Q1…Q6/receipt.json`.
Заявление модели о доступности `web_search` не является доказательством tool use.

- **P1 принята:** один Luna/high/V0 запуск, точная опечатка README и финальный
  controller proof. Evidence: `mission-workspaces/P1/mission-result.json`.
- **P2 принята с ручным восстановлением:** Sol создал продукт один раз. Первый
  Opus-review скопировал изменения автора в собственный `filesChanged`; validator
  отверг отчёт. После проверки остановки процесса, неизменности workspace и
  bindings сохранена отдельная owner-реконсиляция; raw не нормализовался.
  Один новый review того же продукта дал `pass`, пустые findings и совпадающие
  bindings. Сохранены 3 запуска, 1 product attempt и исходный deadline.
  Evidence: `mission-workspaces/P2/mission-result.json` и
  `workspace/.centurion/agents_results/oct17-r3-p2-review-1/owner-review-reconciliation.json`
  внутри P2. Это не доказательство автоматического reviewer report recovery.
- **P3 не принята:** Opus создал HTML, шесть screenshots и DOM evidence;
  Gateway зафиксировал `result path collision`. Уже существующий `result.json`
  не имел `responseEnvelope`; `closure.canonicalFinalized=false`. Процесс
  остановлен, intent сохранён как `reportable`, mission — `verifying`.
  Обнаружена конфликтующая инструкция installed orchestrator: писать прямо в
  `outputContract.resultPath`. Исправление выше устраняет этот текстовый конфликт;
  его соблюдение реальной моделью после правки ещё не доказано.
  Colliding result, raw, candidate и protocol receipt сохранены без замены.
  P3 не имеет разрешённого report capability в mission authority; новый product
  launch и ручная приёмка не выполнялись. Независимый Sol review UI не запускался.
- **P4–P6 не запускались:** последовательный пилот остановлен на P3.

## Независимая проверка и оставшаяся работа

Source review 1 остановлен после 600 секунд без stdout/verdict. Source review 2
получил компактный пакет и вернул **ACCEPT**, `findings=[]`, exit 0 за 12.85 с.
Оба запускались native Claude/Opus high через локальный
`ANTHROPIC_BASE_URL=http://127.0.0.1:8317` и
`ANTHROPIC_DEFAULT_OPUS_MODEL=claude-opus-5-5`, с read-only native profile.
Новые credentials, `/login` и публичный fallback не применялись.

Проверены schema projection, точный review scope/accepted collection,
report launcher/profile pins, proxy validator, installer boundaries и предложение
version-scoped migration. Review не выполнял тесты самостоятельно и не доказывает
live rollout или полноту пользовательских сценариев миграции. Source hashes
после ответа сверены. Evidence: `control/review-2/{order.json,input.txt,stdout.json,receipt.json,review.json}`.

Бюджет двух source reviews исчерпан. Правки skills и новая collision regression
сделаны после ACCEPT и им не покрыты. Для завершения нужны актуальное независимое
ревью этих правок, проверка нового контракта на чистом P3 и оставшиеся P4–P6 в
явно ограниченном продолжении. Неудачный P3 не открывается заново и не удаляется;
новое окно и дополнительные model launches в r3 автоматически не создавались.

Финальная сверка baseline: девять исходных пользовательских файлов в другой
worktree и четыре live config/SOUL файла совпадают с исходными SHA-256.

Установка разрешена только после прохождения всех обязательных гейтов,
актуальных backups/preimages, readback и canary. Публикация, push и release tag
в этот проход не входят.
