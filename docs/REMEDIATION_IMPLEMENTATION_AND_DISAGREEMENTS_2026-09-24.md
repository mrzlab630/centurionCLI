# CENTURION: реализация и разногласия по плану Opus

Дата: 2026-09-24. Исходный план: `docs/REMEDIATION_PLAN_2026-09-23.md`.
Рабочий checkout: `/home/mrz/projects/al/centurionCLI/worktrees/centurion-main`.

Дополнение после P2-3: repository-реализация и общие smoke завершены;
актуальный итог в `LEGION_HARDENING_REPORT_2026-09-24.md`. Финальный Opus review
проводит пользователь. Упоминания live-файлов ниже относятся к исходному аудиту:
в текущем этапе локальная установка не читалась для перепроверки и не менялась.

Работа выполнена в исходниках и офлайн-регрессиях. Исходное рабочее дерево уже
содержало множество незакоммиченных изменений; они сохранены. Коммит, реальная
установка, деплой и внешние вызовы Codex/Claude не выполнялись.

## Принято и воплощено

| Пункт | Результат | Степень готовности |
| --- | --- | --- |
| P1-1: staged install | `install.sh` вызывает `scripts/install-owned-files.mjs` с `--agents-home`, `--claude-home` и `--codex-home`. Helper готовит соседние staged-копии, сравнивает SHA-256 и режимы с рассчитанным по checkout manifest, отвергает симлинки и чужие файлы в управляемых каталогах, сохраняет прежние версии рядом с целями и откатывает уже переключённые цели при обычной ошибке. Офлайн-тест проверяет также отказ TLS для локального недоверенного сертификата у временно установленной библиотеки. | Частично: транзакция ограничена helper и не охватывает всю установку или аварийное завершение процесса. Текущий `~/.codex/libs/legion_core.py` совпадает с checkout, но полный `install.sh` не запускался; `~/.claude/libs/legion_core.py` всё ещё старая небезопасная копия. |
| P1-2: custody внешнего запуска | Для Codex/Claude прямой runner теперь записывает start до запуска, closure после проверки и terminal acceptance с привязкой к хешам order/result/receipts (`direct_custody.py`). Gateway держит loop-lock до proof и terminal acceptance; при отказе финальной записи возвращает снимок loop-state и блокирует повторный запуск. Прямой Astra advisory по-прежнему требует Gateway. | Реализовано и проверено офлайн, включая инъекции отказов. Реальные внешние запуски вне проверки. |
| P1-3: цепочка артефактов | `order.lineage` связывает product manifest/anchor с order/result/receipts/acceptance. Добавленный `inputResults` связывает принятые control-артефакты, включая Astra advice, по explicit result/acceptance/closure pins; проверяет их до запуска и после proof. | Локальный Gateway-срез готов и проверен, включая полную fake-CLI цепочку. Loop V1 + product lineage и строгая OS-изоляция остаются вне реализации; ограничения ниже. |
| P2-1: `evidenceNeed` | `evidenceNeed=high` повышает минимальный Codex reasoning effort до `high`, не снижая уже требуемый `xhigh`; `low` не добавляет повышение. | Реализовано, проверено парными регрессиями. Сам по себе этот признак не меняет модель или профиль review, чего план и не требовал. |
| P2-2: V0 proof | V0 допускается только при наличии хотя бы одной обязательной proof-команды и истинных предварительных предикатах. Поля `deterministicFailureOracle`, `requiredArtifactsPass` и `requiredProofsPass` сохранены в legacy wire shape, но больше не используются как доказательство до запуска. После executor контроллер фиксирует фактически выполненные проверки и отдельно принимает либо отклоняет результат: Gateway пишет `controller-proof.json` и финальный `controller-acceptance.json`, direct runner пишет свои closure/terminal receipts. Провал обязательного proof не может стать принятым V0. | Fail-closed controller gate и разделение admission PRE/POST достигнуты. Canonical result остаётся create-only; итоговое принятие определяется controller acceptance. Независимый семантический oracle для `deterministicFailureOracle` контрактом не задан. |
| P2-3: JSON response | Совместимый `AGENT_HANDOFF_V1`, raw/single-clean-fence ingress, preserved raw/normalized bytes, controller envelope, typed artifact hashes, response error codes, Python/JS guards и direct candidate adapter. | Shared и все четыре surface smoke проходят. Final Opus review и live provider proof отдельно. |

Ключевые файлы: `scripts/install-owned-files.mjs`, `install.sh`,
`integrations/hermes-legion-kit/skills/autonomous-ai-agents/agent-contract-runner/scripts/agent_contract_runner.py`,
`result_gateway.py`, `direct_custody.py`, `artifact_lineage.py`,
`review_ladder.py` в том же каталоге, `docs/LEGION_CONTRACTS.md` и
`integrations/hermes-legion-kit/skills/autonomous-ai-agents/agent-contract-runner/SKILL.md`.

## С чем не согласен

1. **P1-2, безусловно запретить `agent_contract_runner.py --mode run`.** Это
   ломает существующий прямой Loop V1 и его вызывающих клиентов. Проверяемые
   start/closure/terminal receipts до и после прямого запуска обеспечивают
   требуемый custody-контур без смены интерфейса. Флаг
   `--allow-direct-dispatch` не решает риск: он сохраняет обход как обычную
   настройку. Один proof-gate только после запуска тоже недостаточен, потому
   что не фиксирует заказ и запуск до побочных эффектов.
2. **P1-3, единый `artifactHash`, записанный исполнителем в результат.** Один
   хеш не выражает набор файлов и удалений, а self-report не доказывает живые
   байты. Поэтому хеширует контроллер, а связность задают manifest/anchor и
   доверенный digest предыдущего anchor. Поля `previousOrderId` и
   `expectedArtifactHash` не добавлены в общий результат буквально.
3. **P2-2, переписать canonical result на `failed` после провала controller
   proof.** Canonical result является заявлением исполнителя и уже связан
   хешем closure. Его перезапись стирает исходное свидетельство и нарушает
   create-only контракт. Контроллер пишет независимый статус `rejected` в
   terminal acceptance; потребитель обязан проверять именно его.
4. **P1-1, считать успешный HTTPS-запрос или обычный `openssl s_client` proof
   проверки сертификата.** Успешный запрос возможен и при отключённой
   проверке сертификатов; один `s_client -connect` также не доказывает
   корректную проверку имени хоста. Отрицательный тест с локальным недоверенным
   сертификатом проверяет нужное свойство у временной установки. Проверку
   реального окружения нельзя заявлять без разрешённой установки.
5. **Пути и способ запуска тестов из плана.** `tests/test_agent_contract_runner.py`
   в checkout отсутствует; `regression_agent_contract_runner.py` является
   сценарным скриптом, поэтому его запускают напрямую, не через
   `python3 -m unittest` с путём, содержащим дефисы.

## Нерешённое и границы доказательства

- **P1-1 остаётся открытым для полной живой установки.** Полный `install.sh`
  пишет конфигурацию Claude до helper, а поздние npm/MCP/plugin-шаги находятся
  вне его отката. Переключение нескольких целей не является одной атомарной
  операцией и не восстанавливается автоматически после аварийного завершения.
  Helper сверяет рассчитанный по текущему checkout manifest, а не внешне
  подписанный release manifest. Текущий `/home/mrz/.codex/libs/legion_core.py`
  совпадает с checkout и не меняет HTTPS default; `/home/mrz/.claude/libs/legion_core.py`
  остаётся старой 4179-байтовой копией с `ssl._create_unverified_context`, потому
  что полный install не запускался.
- **P1-3 проверяет целостность заявленных файлов, но не авторство.** Наличие
  файла в `lineage.artifactPaths` само по себе не доказывает, что его создал
  именно этот executor. Между предзапусковой проверкой предыдущего файла и
  чтением его преемником остаётся окно конкурентной правки. Для строгого
  handoff нужен неизменяемый snapshot или изоляция путей. Поддерживаются
  только явно названные обычные файлы и маркеры удаления; каталоги, прямой
  runner и сочетание lineage + Loop V1 не поддерживаются. Сбой финальной
  квитанции может оставить непринимаемые create-only manifest/anchor: нужен
  новый orderId либо отдельная процедура восстановления. Существующий
  read-only Astra advisory требует артефакты внутри control namespace, тогда
  как `lineage.artifactPaths` описывает файлы вне него. Этот прежний пробел
  закрыт отдельным `inputResults` контрактом: predecessor acceptance/result/
  closure hashes и selected control artifacts проверяются до запуска и после
  proof. `regression_accepted_inputs_gateway.py` теперь доказывает цепочку
  Astra advisory -> Sol implementation с product lineage -> Opus terminal review
  через реальные Gateway subprocess и fake CLIs. Это не live-модельный proof.
- **P1-2 покрывает управляемые ошибки, но не аварийное завершение процесса.**
  Если процесс принудительно завершится между записью нового loop-state и
  terminal receipt, сохранённый снимок сам по себе не выполнит восстановление
  при следующем запуске. Для этого требуется отдельная recovery-процедура.
- `monitor-delegation.sh` подтверждает start/closure/result и маршрут, но не
  семантическое принятие. Для Gateway нужен `controller-acceptance.json` со
  статусом `passed`, для прямого runner его terminal receipt. Хеши и файлы
  под одним UID не защищают от злонамеренного процесса, способного переписать
  и данные, и контрольные квитанции.

## Проверка

Из корня checkout прошли:

```bash
python3 integrations/hermes-legion-kit/skills/autonomous-ai-agents/agent-contract-runner/scripts/regression_agent_contract_runner.py
python3 integrations/hermes-legion-kit/skills/autonomous-ai-agents/agent-contract-runner/scripts/regression_result_gateway.py
python3 integrations/hermes-legion-kit/skills/autonomous-ai-agents/agent-contract-runner/scripts/regression_artifact_lineage.py
python3 integrations/hermes-legion-kit/skills/autonomous-ai-agents/agent-contract-runner/scripts/regression_review_ladder.py
node --test tests/install-owned-files.test.mjs
bash -n install.sh
node --check scripts/install-owned-files.mjs
git diff --check
```

Lineage: 11/11, installer: 4/4. Gateway и direct runner проверены инъекциями
отказа финальной квитанции и записи события после loop-state; Gateway также
проверен при `OSError` финализации lineage. Реальную полную установку,
обновление `~/.claude`, deploy и внешнюю модель эти тесты не подтверждают.

Для перепроверки Opus: оценить достаточность controller acceptance вместо
перезаписи canonical result; определить, нужен ли release manifest и
транзакционность всего `install.sh`; решить, требует ли межзаказный handoff
неизменяемых snapshots и доказательства происхождения каждого продукта.
