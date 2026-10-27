# Восстановление отчёта и продолжение миссии

Ошибка JSON/формата не доказывает ошибку продукта. Gateway сохраняет исходные
raw, order, start/closure, snapshot продукта и выполненные controller checks.
Продуктовая работа не повторяется ради исправления отчёта. Валидный авторский
`failed` не превращается этим механизмом в `done`.

## Модельное восстановление

Повторите исходную команду `result_gateway.py` с теми же параметрами custody,
добавив `--recover-report`. Команда собирает существующий запуск после restart
или выполняет следующие report-only ordinals до валидного ответа. Каждая попытка
сохраняется в `report-N/` с отдельными start/raw/child/failure либо closure.
Потраченные model launches учитываются, product attempts не увеличиваются.
Канонический result создаётся один раз после проверки.

Нужен controller-pinned `authority.reportCapabilityRef`: рабочий Q6 receipt,
привязанный к точным CLI/config/profile и доказанной изоляции. Его отсутствие
не является дефектом продукта. Автоматические вызовы останавливаются при повторе
одинакового невалидного ответа, неизвестном эффекте, нарушении изоляции или
целостности, отмене и недоступном бюджете. Диагностика следующей попытки содержит
класс предыдущей ошибки, без исходного невалидного текста или credentials.

Для новых миссий с включённой capability `budget.reportLaunchReserve` по умолчанию
равен 1. Это минимальный резерв общего бюджета, не потолок report attempts.
Первоначальный бюджет должен покрывать исходные задачи, обязательные независимые
review и резерв. Обычный dispatch не расходует оставшийся резерв; report recovery
сохраняет минимум запусков для обязательного review. Старые бюджеты при загрузке
не меняются. Миссии без включённой модельной capability могут использовать ручную
проверку без дополнительного model launch.

## Записанное продолжение

Runner остаётся владельцем mission state. Подготовьте в control namespace
исходного order JSON решения владельца и выполните без dispatch:

```bash
python3 integrations/hermes-legion-kit/skills/autonomous-ai-agents/agent-contract-runner/scripts/agent_contract_runner.py \
  --order /absolute/control/order.json \
  --continue-mission /absolute/control/continuation.json
```

Формат решения:

```json
{
  "version": "CENTURION_MISSION_CONTINUATION_V1",
  "missionId": "original-mission-id",
  "approvalRef": "original-owner-approval-reference",
  "stateSha256": "sha256-of-current-state-bytes",
  "reason": "Recorded owner decision to extend the reporting budget",
  "maxModelLaunches": 6
}
```

`maxModelLaunches` необязателен, может только сохранить или увеличить утверждённый
предел. Решение привязано к точным текущим bytes state; повторное применение
устаревшего решения отклоняется. В state добавляется история continuation с hash
решения и прежним бюджетом. Счётчики, raw, canonical results и deadline не сбрасываются.
Живые/неизвестные эффекты сначала нужно reconcile. Завершённые, отменённые миссии
и реальные terminal product failures не открываются. Узкая совместимость допускает
старый `failed` с точной причиной `mission model-launch budget exhausted` при
сохранённой целостности и остановленных эффектах.

Решение также может передать точный `reportCapabilityRef`, когда владелец уже
предоставил проверенную capability. Это не создаёт новую report authority и не
подменяет Q6 проверку при последующем запуске. Обычное продолжение внутри текущего
бюджета не требует новых запросов владельцу.

## Ручная проверка готовой работы

Проверяющий изучает реальные изменения и сохранённые checks, при необходимости
выполняет отдельную проверку. Если продукт верен, он подготавливает полный JSON
по исходному result contract и отдельную запись:

```json
{
  "version": "CENTURION_MANUAL_PRODUCT_REVIEW_V1",
  "missionId": "original-mission-id",
  "orderId": "original-order-id",
  "orderSha256": "sha256-of-original-order",
  "productSnapshotSha256": "saved-product-snapshot-sha256",
  "rawSha256": "sha256-of-original-malformed-candidate",
  "candidateRef": {"path": "/absolute/control/manual-candidate.json", "sha256": "exact-candidate-sha256", "bytes": 1234},
  "criteria": ["original acceptance criterion"],
  "reviewer": "identified human reviewer",
  "verdict": "pass"
}
```

Оба файла лежат в control namespace order. Их содержимое должно соответствовать
реальным доказательствам. В решение continuation добавляется
`manualReportReviewRef` с точными path/sha256/bytes записи review. После его
применения повторите исходную Gateway-команду с
`--recover-report-from /absolute/control/manual-candidate.json`.

Gateway проверяет привязку решения, reviewer, критериев, snapshot, исходных raw
и новых candidate bytes; сверяет filesChanged/artifacts/proof с собственными
сохранёнными наблюдениями. Эта операция не запускает модель и не требует Q6,
поскольку не выполняет executor/tool commands. Обязательные controller checks
должны уже пройти. Неполные сведения нельзя заполнить вымышленными фактами.

Ручная запись восстанавливает отчёт, но не заменяет обязательного независимого
terminal review и не обходит V3 admission. После восстановления V2-кандидат
остаётся `awaiting_review`, пока установленное review условие не выполнено.
Downstream проверяет обе цепочки: исходный запуск и восстановление отчёта.

## Граница поставки

Source merge не обновляет установленные Hermes/Codex/Claude homes и не исправляет
конкретную живую миссию автоматически. Для установки нужен отдельный согласованный
шаг с проверкой drift, backup/rollback и фактическим capability readback.
Offline fixtures доказывают проверенные переходы, а не доступность live provider.
