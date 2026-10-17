# CENTURION 3.0 — результат реализации и проверки

Дата: 2026-10-16. Ветка: `feat/centurioncli/v3-implementation`.
Кандидат: **3.0.0-rc.1**. **Готовность к выпуску не принята**: N7 неполон.

Единый источник требований — [план 1.5](CENTURION_3_0_IMPLEMENTATION_PLAN.md).
План прошёл документальное ревью локального Claude Opus 5.5 (`ACCEPT`);
текущая реализация получила отдельное ограниченное ревью исходников Claude Opus 5.5
(`ACCEPT`, [order](reviews/centurion-3.0-implementation/code-review-current-order.json),
[receipt](reviews/centurion-3.0-implementation/code-review-current-receipt.json),
[review](reviews/centurion-3.0-implementation/code-review-current.json)).
Оба вердикта ограничены своим входом и не являются одобрением выпуска или внедрения.

## Реализовано

| Блок | Результат |
| --- | --- |
| W1 / N1–N2 | Единая политика моделей и уровней проверки. Sol — основной исполнитель; Luna только high/xhigh; Astra — консультация; Opus — независимое ревью и дизайн. Sonnet/Fable/Gemini/старые маршруты не получают полномочий 3.0. |
| W2 / N3 | Gateway — активный launcher; строгие order/result/handoff; native projections; ограниченный capture; protocol failure сохраняет исходный ответ и не создаёт вымышленный executor result. |
| W3 / N4 | Один persistent mission state и writer lock; общие бюджеты; intent до запуска; отмена/deadline/process identity; восстановление без повторного продукта; независимое ревью привязано к candidate/result/snapshot. |
| W4 / N5–N6 | Короткий функциональный core, условная загрузка специализированных skills, исключение legacy/maintenance authority; изолированные installers, hashes/readback, conflict/rollback checks. Римские имена могут оставаться совместимыми обозначениями, но не создают второй уровень полномочий. |
| Интеграция | Реальный workspace diff с dirty baseline, включая tracked `build/dist/vendor` и явно заданные untracked product paths; различение proof cwd и разрешённых путей продукта; report-only recovery с одной попыткой и отдельным namespace. |

W1–W4 выполнялись отдельными заданиями GPT‑6.1 Sol с xhigh. Результаты и
контроллерские проверки находятся в [каталоге приёмки](reviews/centurion-3.0-implementation/).
Два дополнительных CLI-задания интеграции/подготовки пилота остановлены контроллером
до итогового result; их завершение не заявляется. Их изменения сохранены,
проверены по фактическим файлам и доработаны контроллером. Встроенный канал
дополнительного субагента дважды вернул пустое поручение; успешной делегацией
это не считается.

Реализация пакетов и приёмка системы имеют разные статусы:

| Область | Приёмка |
| --- | --- |
| W1: политика и routing | Принято в репозиторную интеграцию; 19 routing groups и 16 исторических route cases проверены. Это не доказательство модели у провайдера. |
| W2/W3: Gateway и mission state | Интегрированы; актуальные packaged regressions, A23 и compound A25/A27 пройдены offline. Старые receipts отдельных пакетов описывают состояние до интеграции. |
| W4: skills и поставка | Изолированные install/upgrade/rollback и source/installed readback пройдены. Фактическая загрузка инструкций клиентом остаётся непроверенной до N7. |
| N5: authority chain и active skills | Независимое компактное ревью Claude Opus 5.5: `ACCEPT`; проверены installer map, core contract, Gateway-only dispatch и выбранные entrypoints. Live loaded-chain по-прежнему не заявляется. |
| N7: модельный пилот | Не принят: Q6 отказал до API, остальные обязательные пробы и P1–P6 не выполнены. |
| N8: выпуск и рабочая установка | Не выполнялся; требует принятого N7 и разрешения на конкретную область установки. |

## Что исправлено при контроллерской проверке

1. Отчёт Claude, собранный после Codex-продукта, разбирается как фактический
   native Claude output, сохраняя исходную идентичность заказа.
2. Неизменяемые settings отделены от scratch Claude. После перезапуска
   сохранённый отчёт собирается без второй inference; новые hooks/MCP/plugins
   в scratch отклоняются.
3. Отклонённый, но корректный и завершившийся результат фиксируется как
   наблюдённый результат. `review verdict=fail` больше не оставляет
   `unknown_effect` при уже остановленном процессе. Продукт не принимается;
   дальнейшая коррекция по-прежнему требует решения контроллера и бюджета.
4. Report-only модель получает реальные изменения, before/after digests,
   метаданные артефактов и команды/статусы сохранённых proof. Список файлов,
   факты proof и метаданные артефактов ответа сверяются до finalization.
   Выдуманные команды, действия и хеши отвергаются.
5. Smoke установленного Hermes запускает актуальный mission entrypoint и V3
   Gateway. Общий fixture больше не требует отсутствующий legacy monitor при
   импорте. Старый монитор в новый core не добавлен.
6. A23: прерывание после durable `observe_result`, но до сохранения verification,
   восстанавливается из того же captured report. Проверяются canonical equality,
   custody и reviewer binding; новая реализация и второй отчёт не запускаются.
   Owner probe: `accepted`, product launches = 1, report launches = 1.

## Независимое ревью кода

Исходный [Opus `REVISE`](reviews/centurion-3.0-implementation/code-review-runtime.json)
сохранён без изменения. Последующее ограниченное
[Opus `ACCEPT`](reviews/centurion-3.0-implementation/code-review-current.json)
относится к текущим recovery/reservation/dispatch fragments и их V3 regression.

| Замечание | Решение контроллера |
| --- | --- |
| F1: недостаточные факты для no-tools report | Подтверждено в части неполного input. Исправлены `report_projection` и `validate_report_facts`; добавлены отрицательные проверки выдуманных фактов. Утверждение о свободном принятии несуществующего артефакта было шире фактического поведения: artifact gate уже проверял существование и hash. |
| F2: rejected intent якобы разрешает повтор продукта после crash | В предложенном причинном пути не подтверждено. `fail()` синхронно сохраняет mission state; тот же intent возвращает closed/no replay. Новый product intent требует retry reason/evidence, остаётся в общем бюджете и отвергается при открытом captured product. Ссылки на best-effort Loop V1 event не описывают активный путь 3.0. Отдельный фактический дефект negative review → unknown_effect воспроизведён и исправлен, см. выше. |
| F3: неуспешный save якобы не проверяется до spawn | В предложенном причинном пути не подтверждено. Atomic write выполняет flush/fsync/replace/directory fsync; исключение не позволяет вернуть launch reservation. `save()` помечает неопределённую запись и выбрасывает исключение. Offline fault injection до/после replace проверяет сохранение spent budget и запрет replay. Произвольная аппаратная порча диска не объявляется покрытой. Новый WAL/БД не добавлялся. |

Первый большой запрос ревью закончился `max_tokens` без вердикта. Второй
`ACCEPT` отклонён контроллером: ответ ошибочно пересказывал старый статус W4.
Третий запрос содержал актуальные source ranges без отчётов исполнителей.
После изменений report-capture выполнено отдельное bounded ревью текущих байтов;
оно подтвердило recovery и отсутствие новых существенных дефектов в проверенной
области. Хеши входа и ответа сохранены в каталоге ревью. Это не закрывает N7/N8.
Запрос до этого завершился timeout и имел уже устаревший hash Gateway; он не
использован для приёмки. У финального ответа `end_turn`, requested/reported model
`claude-opus-5-5`, effort high; все три input hashes сверены с текущими файлами.

Контроллер исправляет неточность в `limitations` последнего ответа: строка 1729
runner запрещает профиль **V3** без доверенного verifier, а не «N7 review-based
verification». Само независимое ревью V1/V2 работает и проверено regressions.
Строка 1727 запрещает прямой report dispatch; recovery Gateway отдельно требует
receipt Q6. Эти два пояснения модели не используются как доказательство поведения.

## Фактические проверки

| Проверка | Результат |
| --- | --- |
| Полный smoke установленного Hermes с 13 актуальными Python entrypoints | PASS; повторён владельцем на текущих байтах, включая mission-only и V3 Gateway |
| Codex и Claude isolated install smoke | PASS |
| V3 Gateway | 8 групп PASS: strict ingress, native schema, review binding, recovery/restart, actual diff, ENOSPC, bounded capture; внутри recovery также отвергаются выдуманные report facts |
| Mission lifecycle (`--mission-only`) | 12 групп PASS, включая общие лимиты, независимое ревью, рестарт, отмену и process identity |
| Astra → Sol → Opus → downstream с nested inputs и lineage | PASS |
| Python compilation / `git diff --check` | PASS |
| Последний полный glob `regression_*.py` | 12 PASS из 14; два исторических main остаются несовместимыми с новым запретом direct/Loop V1 dispatch |
| Изолированная установка и source/installed hash readback | PASS; не доказывает live загрузку инструкций клиентом |
| Исходные 9 dirty-файлов и 4 рабочих конфигурации | SHA-256 без изменений |
| A25/A27 compound proof | PASS: несовместимая интеграция не завершается; cutoff/cancel останавливает owned process, foreign process не затронут, restart не повторяет запуск |
| Fault-injection F2/F3 | PASS: 42/42 targeted cases на записанном snapshot; отказ записи не обнуляет уже потраченный бюджет и не допускает replay. Последующие A23-изменения проверены отдельно. |
| Финальное bounded ревью текущего Gateway Claude Opus 5.5 | ACCEPT; input hashes совпадают с текущими `result_gateway.py`, `agent_contract_runner.py` и V3 regression |

Два исторических main: `regression_agent_contract_runner.py` без
`--mission-only` ожидает старый direct runner launch;
`regression_result_gateway.py` содержит прежние Loop V1/synthetic-result
сценарии и устаревшую диагностику. Они не объявлены прошедшими и не используются
как доказательство 3.0. Parser/builder/envelope/lineage checks остаются в активном
наборе; real Gateway проверяется отдельными V3 и accepted-input chain fixtures.
Полный glob не заменяет определённую в smoke актуальную матрицу.

Артефакты [A23](reviews/centurion-3.0-implementation/SOL_REPORT_CAPTURE_RESULT.json),
[F2/F3](reviews/centurion-3.0-implementation/SOL_RUNTIME_GATE_RESULT.json) и
[A25/A27](reviews/centurion-3.0-implementation/SOL_COMPOUND_PROOF_RESULT.json)
проверены контроллером. Все 16 исходных hashes compound proof совпали с текущими
файлами; наблюдения показывают: несовместимые принятые срезы оставляют mission
`verifying`, совместимый control достигает `completed`; cutoff блокирует миссию,
отмена во время proof даёт `stopped`, owned PID остановлен, foreign canary не
получает сигнал, product launch count после restart остаётся 1.

В raw compound result есть ошибка отчётности: первый harness run помечен `pass`
при `exitCode=1`. Этот запуск **не принят как успешная команда**: он сохранил два
успешных A25-наблюдения и упал на коллизии временного fixture до A27. A27 отдельно
прошёл исправленным disposable harness с exit 0. Сами наблюдения и hashes проверены;
raw result не переписан. Старый coverage audit предшествует этим proof и A23 fix,
поэтому его список открытых offline gates не является текущим итогом.

Итоговая owner-side запись [owner-final-acceptance.json](reviews/centurion-3.0-implementation/owner-final-acceptance.json)
сводит текущие hashes, результаты двух bounded ревью Claude, smoke, regression,
compound proof, сохранность baseline и шесть принятых worker artifacts. Её статус:
`accepted_for_offline_integration`; статус выпуска: `blocked`.

## Что не принято

**Q6 не прошёл.** В изолированном окружении Claude CLI 2.1.224 с `--bare`,
пустыми tools/MCP и отключёнными hooks вернул `Not logged in · Please run /login`.
`duration_api_ms=0`, входных/выходных токенов 0, exit code 1. Продукт не изменён,
но это отказ клиента до API, а не успешная no-write capability.
API-доступ к тому же локальному провайдеру для ревью работал без credentials;
это не заменяет проверку конкретного native CLI запуска.

**Уточнение 2026-10-17:** по подтверждённой владельцем конфигурации Claude CLI
всегда работает через локальный прокси: `ANTHROPIC_BASE_URL` и
`ANTHROPIC_DEFAULT_OPUS_MODEL`. Прокси не требует пароля или входа в аккаунт
Anthropic. Старый Q6 вручную передавал URL, задавал модель литералом, не передавал
`ANTHROPIC_DEFAULT_OPUS_MODEL` и использовал `--bare` с урезанным окружением.
Текущий `claude --help` прямо описывает требование API-key/apiKeyHelper для
`--bare`; обе маршрутные переменные объявлены в `.bashrc`, но отсутствовали в
окружении проверяющего неинтерактивного процесса. Поэтому `Not logged in` здесь
фиксирует неуспешную конфигурацию запуска Q6, **не неработоспособность Claude CLI
через прокси и не необходимость `/login`**. Точную достаточную коррекцию запуска
нужно подтвердить native round-trip, сохранив no-write режим. Правило записано в
[Claude kit README](../integrations/claude-legion-kit/README.md). Исторические raw
результаты Q6 и неподтверждённый статус capability остаются без изменений.

Зарезервирован один запуск из N7 capability budget, возврата счётчика нет.
No-write receipt не выдан; live report recovery не включён. Q1–Q5, резервы
Q7–Q8 и P1–P6 не выполнены. В частности, P6 зависит от успешного Q6.
Следовательно, live A23, клиентские tool round-trips, loaded-chain precedence,
vision/Context7/search и полная матрица моделей не доказаны.

Остаются обязательными: корректная передача конфигурации локального прокси в
изолированный Claude CLI и проверка выбранного режима; успешный Q6;
остальные probes и шесть фиксированных миссий в пределах
бюджета; итоговая приёмка исправленного кандидата. При возобновлении бюджет и
deadline читаются из сохранённого состояния, не обнуляются автоматически. Финальное
bounded ревью исходников не подменяет эти live gates.
Сохранённый capability deadline — `2026-10-16T17:55:59.793357Z`; он истёк.
Продолжение требует явного решения о новом окне пилота с сохранением истории
неуспешной Q6; автоматический сброс счётчика или deadline не выполнялся.

**N8 не выполнялся.** Нет установки в рабочие homes, production deploy,
push/tag/publication или утверждения готового релиза. Доставлен проверяемый
репозиторный RC с открытыми gates, а не законченная и внедрённая CENTURION 3.0.
