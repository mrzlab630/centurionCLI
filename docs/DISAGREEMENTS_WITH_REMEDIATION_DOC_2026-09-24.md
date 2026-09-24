# Разногласия с предложениями по remediation

Дата: 2026-09-24
Автор: CENTURION (Codex)
Проверенный документ предложений: `docs/REMEDIATION_IMPLEMENTATION_AND_DISAGREEMENTS_2026-09-24.md`
Исходный план: `docs/REMEDIATION_PLAN_2026-09-23.md`

Ниже перечислены только пункты, с которыми я не согласен полностью или в
заявленной форме. Каждое решение сопоставлено с текущим исходным кодом и
офлайн-проверкой.

## 1. Безусловный запрет прямого runner

**Позиция предложения:** все `agent_contract_runner.py --mode run` должны быть
запрещены, а внешние Codex/Claude должны запускаться только через Gateway.

**Почему не согласен:** текущий прямой путь не является бесконтрольным обходом.
Для Codex/Claude он создаёт start receipt до запуска, closure после проверки и
terminal acceptance с хешами order/result/receipts (`scripts/agent_contract_runner.py`:
1266–1284, 1334–1364; `scripts/direct_custody.py`: 77–181). В регрессии проверены
ошибки proof, terminal receipt, loop-state и запись события сразу после start
receipt. Полный запрет изменил бы существующий интерфейс без доказанного списка
совместимых вызывающих клиентов. Риск прямого пути остаётся отдельным
операционным ограничением, поэтому связанная lineage-цепочка по-прежнему
разрешена только Gateway.

## 2. Executor-owned `artifactHash` как основной контракт

**Позиция предложения:** добавить в общий результат `artifactHash`,
`previousOrderId` и `expectedArtifactHash` и проверять их runner-ом.

**Почему не согласен:** executor сообщает о результате, поэтому его хеш не
доказывает байты, режимы, удаления или связь с предыдущим заказом. Контроллер
может проверить это сам. Текущий `artifact_lineage.py` читает живые обычные
файлы, фиксирует per-file SHA-256, размер и режим, связывает order/result/
receipts/proof в create-only manifest и anchor (`artifact_lineage.py`: 449–550,
564–652, 672–805). Это более сильный источник истины, чем self-report. Общий
`AGENT_RESULT_JSON_V1` поэтому не расширен этими полями.

## 3. Требование immutable snapshot как обязательное решение lineage

**Позиция предложения:** строгий handoff требует неизменяемых snapshot-ов или
изоляции файлов.

**Почему не согласен с обязательностью:** для same-UID локальной разработки
контроллерский manifest, доверенный digest predecessor anchor, create-only
receipts и повторная проверка frozen predecessor уже защищают от обычной
подмены и случайного дрейфа. Неизменяемый snapshot не доказывает authorship и
не устраняет злонамеренный процесс с тем же UID. Поэтому snapshot/внешняя
изоляция нужны для shared или adversarial среды, но не должны быть обязательным
условием локального Gateway handoff.

Ограничение сохраняется: между preflight и чтением successor есть race-window,
а authorship executor не доказан (`artifact_lineage.py`: 710–725; основной
документ, раздел «Нерешённое»). Lineage сознательно не поддерживает direct
runner и Loop V1.

## 4. Переписывание canonical result после провала proof

**Позиция предложения:** после провала post-execution proof canonical result
должен быть переписан со статусом `failed`.

**Почему не согласен:** canonical result является исходным заявлением
исполнителя и уже связан хешем closure. Перезапись стирает свидетельство и
ломает create-only контракт. Gateway сохраняет исходный result, записывает
наблюдаемый `controller-proof.json` и создаёт terminal
`controller-acceptance.json` со статусом `rejected` (`result_gateway.py`:
1237–1279, 1325–1368). Потребители должны принимать результат только после
проверки controller acceptance; чтение одного `result.status` недостаточно.

## 5. Объявление P2-2 полностью закрытым только из-за fail-closed proof

**Позиция предложения:** разделение PRE/POST и проверка
`deterministicFailureOracle` полностью реализованы.

**Почему не согласен с полной формулировкой:** фактические artifact/proof checks
выполняются после executor и fail closed, но `deterministicFailureOracle`,
`requiredArtifactsPass` и `requiredProofsPass` остаются в legacy `trustPredicates`
для совместимости. Теперь они не используются для допуска V0 как будущий
результат: V0 проверяет только предварительные предикаты, а controller проверяет
живые artifacts и proof commands (`review_ladder.py`: 43–67, 159–181, 416–428;
`agent_contract_runner.py`: 1136–1168). Однако отдельного наблюдаемого
семантического oracle для `deterministicFailureOracle` в контракте нет. Поэтому
достигнут fail-closed controller gate, но не доказана независимая проверка
содержания этого oracle.

## 6. Статус P1-1 как «реализовано для всех live homes» или полностью blocked

**Позиция предложения:** staged install уже подтверждён для всех трёх live
каталогов.

**Почему не согласен с такой границей:** helper действительно принимает
`--agents-home`, `--claude-home` и `--codex-home` (`install.sh`: 15–18, 125–129)
и его offline-тесты проходят 4/4 (`tests/install-owned-files.test.mjs`). Но
полный `install.sh` не запускался и не является одной транзакцией: Claude
config/scripts/pipeline записываются до helper, npm/MCP/plugin шаги идут после
него (`install.sh`: 68–117, 132–260). В текущем live state `~/.codex/libs/legion_core.py`
совпадает с checkout, а `~/.claude/libs/legion_core.py` остаётся старой
4179-байтовой копией с `ssl._create_unverified_context`. Нельзя переносить
offline/helper proof на полную установку.

Для статуса использую более точное разделение: helper действительно частично
реализован и доказан offline, а live acceptance всей установки остаётся
неподтверждённой/blocked. Называть весь P1-1 только `blocked` стирает уже
проверенный helper, а называть его полностью реализованным переносит offline
доказательство на live установку.

## Дополнительные незакрытые риски проекта

Эти пункты не были добавлены в реализацию как новый scope: они не входят
буквально в проверенный документ предложений, но обнаружены при его проверке.

- `PathPolicy` принимает абсолютные `allowedPaths` вне `workspace.repoPath`
  (`agent_contract_runner.py`: 177–193). Такой order может разрешить controller
  читать или писать внешний путь. Нужна отдельная политика для внешних путей и
  её регрессия.
- `loopContract.statePath` и соответствующий `.lock` проверяются только против
  allowed/forbidden patterns и могут находиться вне `workspace.repoPath`
  (`agent_contract_runner.py`: 686–695). Нужна отдельная граница controller
  state root или запрет внешнего state path.

## Что не считаю разногласием

- Signed release manifest разумен для shared/production supply-chain контроля,
  но не является обязательным блокером для локальной single-UID разработки.
- Указание запускать regression-сценарии напрямую корректно: отдельного
  `tests/test_agent_contract_runner.py` нет, а запуск через `unittest` по пути с
  дефисами ломает импорт `attempt_ledger`.
- Дополнительные старые дефекты `legion_core.py` (mission-id validation,
  strict JSON, locking) полезно перечислять в историческом аудите, но исходный
  P1-1 план был про staged hashes/modes/TLS; это не отдельный обязательный
  acceptance пункт.

## Проверка

Прошли:

```text
regression_agent_contract_runner.py: PASS
regression_result_gateway.py: PASS
regression_artifact_lineage.py: 11/11
regression_review_ladder.py: PASS
tests/install-owned-files.test.mjs: 4/4
bash -n install.sh
node --check scripts/install-owned-files.mjs
git diff --check
```

Полная установка, deploy и внешние Codex/Claude вызовы не выполнялись.
