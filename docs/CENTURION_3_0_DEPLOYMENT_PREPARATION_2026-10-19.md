# CENTURION 3.0 — явный выбор Claude и подготовка N8

Ветка `feat/centurioncli/v3-implementation`, исходный HEAD `018bdd4`.
Продолжение по поручению владельца: выбирать модель Claude явно и продолжить
подготовку к локальному развёртыванию. Рабочие homes и настройки провайдера
в этом проходе не изменяются. Кандидат остаётся **3.0.0-rc.1**.

## Выполнено

- `ANTHROPIC_BASE_URL` остаётся обязательным адресом локального прокси.
  Проверка URL по-прежнему отклоняет внешний endpoint, userinfo и malformed URL.
- Основной запуск требует один точный `--model`, совпадающий с утверждённым
  `routing.model`. Восстановление отчёта берёт модель из проверенного
  `capability.route.model`. Допустимые модели, reviewer pairs и effort floors
  не расширены; запрет fallback и проверка reported runtime model сохранены.
- `ANTHROPIC_DEFAULT_OPUS_MODEL` больше не требуется и не наследуется Gateway
  children. Глобальная переменная владельца остаётся без изменений. Обновлены
  Claude README, пример окружения и действующий единый план.
- Подготовлена оговорка для явно активированных миссий policyVersion 3.0:
  исторические model/review/direct-dispatch/loader правила относятся к non-3.0;
  Gateway является единственным launcher и владельцем canonical result;
  его process/events заменяют прежнюю обязанность heartbeat-helper.
  Сохранены независимые ограничения полномочий, scope, identity, безопасности
  и приёмки. Оговорка сама не активирует миссии и не отменяет V3 gate.
- На копиях текущих homes выполнена миграция трёх клиентов с сохранением
  пользовательских префиксов. Readback всех hash/mode: Codex 124 файла,
  Claude 158, Hermes 56; три installed-surface audit прошли. Live dry-run
  также прошёл для всех трёх клиентов. Capability в этих fixture manifests
  честно остаётся `excluded`, `liveLoadedChainProven=false`.
- Проверены 332 текущих live preimages: совпадают с историческим manifest.
  Новых installed-chain manifests в live homes нет. P1–P6 повторно проверены
  по сохранённым result/state/artifact references, без новых product launches.

## Проверка изменения и Claude

`regression_order_preflight.py`: 13 PASS-групп; `regression_review_ladder.py`:
19 PASS-групп; `regression_result_gateway_v3.py`: 24 PASS-группы. Тесты покрывают
отсутствующую, совпадающую и устаревшую alias-переменную, точный report argv,
неизменный локальный proxy gate и sandbox запрет записи. Изолированный Hermes
smoke прошёл установку и 13 packaged runtime regressions. Python compile и
`git diff --check` прошли.

Дополнительно был ошибочно запущен исторический main
`regression_result_gateway.py`. Он остановился на старом ожидании слова
`namespace`, получив более ранний отказ `candidateJsonPath is not covered by
allowedPaths`. Этот main уже исключён из активной матрицы как retired direct
dispatch; его helper-функции используются актуальной v3 regression. Отказ
сохранён как unpassed check, старый тест не изменён ради зелёного результата.

Независимое ревью изменения: Opus 5.5/high, **ACCEPT**, findings `[]`, 15,01 с.
Сам запрос выполнен через изменённый production `report_launch`, локальный
прокси и read-only native profile. В parent специально задан устаревший alias,
в child он отсутствует; requested/reported model — `claude-opus-5-5`, native
structured output получен, server search/fetch telemetry равна нулю.
Это наблюдение клиента, а не независимая аттестация upstream-модели.

На основе того же native запроса и отдельной реальной OS deny-пробы точного
sandbox wrapper подготовлен свежий no-tools report capability. Product marker
не изменён, receipt принят текущим `report_capability`; CLI/settings/profile/
bwrap/adapter hashes связаны с доказательствами. Дополнительного inference
или повторного P6 product effect не было. Перед использованием pins должны
снова совпасть; этот receipt не доказывает полный installed round-trip.

Объединённое текстовое ревью AGENTS/SOUL завершилось через 1099,23 с с
`is_error=true`, `terminal_reason=api_error` и сообщением
`Connection closed mid-response`. Локального timeout не было; native
`subtype=success` при `is_error=true` не принят как успешное ревью.
После этого вопрос разделён на два ограниченных source-review: Codex AGENTS
и Hermes SOUL. Их исходные результаты сохраняются отдельно; исходный отказ
не переписан и не выдан за ACCEPT.

Разделённые ревью завершились независимо: Codex AGENTS — `ACCEPT`, findings
`[]`, 18,01 с; Hermes SOUL — `ACCEPT`, findings `[]`, 895,32 с. Оба вывода
ограничены текстовой совместимостью и не закрывают live loaded-chain gate.

Свежие read-only probes на staged homes прошли для всех исполнителей:
Codex `gpt-6.1-sol/high` за 63,73 с и Hermes `gpt-6.1-sol/high` за 54,22 с.
Они реальным terminal tool прочитали marker, SOUL/AGENTS и orchestrator contract;
native ответы подтвердили Gateway-only canonical writer, Luna `high/xhigh` и
отсутствие остановки по часам тишины. Эти receipts не являются установленным
Gateway canary и не заменяют live capability bindings.

## Остаток до переключения

1. Применить проверенную оговорку в момент переключения после backup. Root
   принял её как исполнение ранее утверждённых правил 3.0; оба независимых
   текстовых review приняты. Пока она установлена только в fixtures,
   runtime loaded-chain рабочей системы не доказана.
2. Подготовить актуальные installer capability bindings для Codex/Claude/Hermes:
   binary/version, фактический config, route, adapter и evidence. Новый report
   receipt закрывает только no-tools ветку; не заменяет остальные bindings.
3. В точке переключения включить штатный external drain Hermes, дождаться
   `gateway_state=draining` и отсутствия active work. Во время длительного drain
   обновлять marker до его штатного срока устаревания; не завершать работающих
   исполнителей по времени. Затем остановить idle service перед заменой файлов.
   Снимок `active_agents=0` сам по себе не закрывает ingress.
4. Снять свежий targeted backup, проверить rollback и отсутствие preimage drift;
   применить только согласованную оговорку и точный allowlist миграции.
   После оговорки пересчитать preimage hashes двух native policies.
5. Установить последовательно Codex → Claude → Hermes; проверить hash/mode,
   preserved prefixes, effective instructions и capability pins. На сбое
   восстановить только проверенные manifest-owned preimages и новые файлы.
6. Через свежую установленную цепочку выполнить одну harmless реальную задачу
   Gateway, проверить canonical result/controller acceptance и модель. Только
   после этой проверки возобновлять новые назначения. Старые P-миссии не повторять.

В этой сессии штатный user service подтверждён как active/running, PID 209355,
`NRestarts=0`; active agents, sessions и registered processes были пусты.
Это снимок состояния. Drain, остановка, live установка и installed canary
ещё не выполнялись. Ранее выданное условное разрешение на установку сохраняется;
результаты этого прохода сами по себе не закрывают N8.

Основные артефакты: `.centurion/explicit-claude-20261019/`:
`explicit-model-route/`, `policy-review/`, `policy-split/`, `report-capability/`,
`n8-preparation/`, `codex-capability/`, `hermes-capability/`.
[Машиночитаемая сводка](reviews/centurion-3.0-implementation/deployment-preparation-2026-10-19.json)
связывает результаты и точную оговорку; исторические receipts и бюджеты
остаются неизменными. Дополнительные проверки поставки: installer 10/10,
Codex smoke, result builder 26 PASS-групп и response envelope 7 PASS-групп.
