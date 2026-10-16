# CENTURION 3.0 — проверка полноты покрытия текущей версии

Дата: 2026-10-16. Это traceability-аудит единого плана
[CENTURION_3_0_IMPLEMENTATION_PLAN.md](CENTURION_3_0_IMPLEMENTATION_PLAN.md).
Документ не добавляет этапы реализации и не является вторым планом. Итоговая
редакция плана после обработки D1–D5 имеет версию 1.4; SHA-256 текущих документов
зафиксированы в [решении владельца](reviews/centurion-3.0-plan/coverage-owner-acceptance.json).

## 1. Метод и граница

Сверены четыре источника проблем и решений:

- R01–R25 из аудита концепции Легиона;
- ST01–ST17 из аудита skills/tools;
- CT01–CT12 из аудита туннеля Hermes/Codex/Claude;
- T1–T12 и S1–S14 из исторического плана автономности.

Дополнительно проверено состояние рабочей ветки, включая девять незакоммиченных
файлов runner/preflight/detector. Для каждого пункта проверялось наличие в плане:

1. конкретного решения или явного решения «не включать»;
2. этапа N1–N8 и владельца;
3. сценария приёмки;
4. deterministic proof или честно обозначенной live-proof boundary.

«Покрыто планом» не означает «уже реализовано». Все N1–N8 ещё не начаты.

Проверка только реестров дала бы неполный вывод: 54 пункта имеют решения, но
чтение действующих launcher, bundles и `PROBATIO.md` выявило ещё шесть групп
пробелов G01–G06 (§6). В план 1.3 добавлены их решения и A25–A30 в существующих
этапах. Это уточнение полноты; исходные аудиты и Claude receipts не переписываются.

## 2. Реестр R01–R25

| ID | Решение в 3.0 | Этап / владелец | Приёмка | Proof / граница |
| --- | --- | --- | --- | --- |
| R01 | Тимлид сам выбирает технические шаги внутри цели; новые полномочия требуют владельца | N1/N4/N5 · тимлид/инженер | A02/A13 | contract fixtures; V3 остаётся заблокирован |
| R02 | Обычный локальный блокер возвращается тимлиду, а не заказчику | N1/N4/N5 · тимлид | A02/A13 | authority table и blocker fixtures |
| R03 | Общий mission budget не сбрасывается новым order/reviewer/restart | N1/N4 · инженер Sol | A07/A08 | state/ledger/interleaving regressions |
| R04 | Подмножество разрешённых путей допустимо; новая цель внутри пути — нет | N3/N4 · инженер Sol | A03/A10 | drift/scope fixtures |
| R05 | Один controller loop, recovery и terminal acceptance; text-only stop не завершает миссию | N4 · инженер Sol | A08/A09/A16 | runner restart/interleaving regressions |
| R06 | Обычная автономность отделена от V3 и trusted verifier | N1/N2/N4 · тимлид/инженер | A13/A14 | review-ladder и policy fixtures; verifier live boundary |
| R07 | Риск определяется фактическими эффектами, не словами `no ...` | N2 · инженер Sol | A06 | `regression_review_ladder.py` |
| R08 | `mission-prep` только советует skills и не выдаёт authority | N2/N5 · инженер/редактор | A06/A17 | восемь routing cases и skill eval |
| R09 | Preflight проверяет transport, paths, argv/env и outputs до child launch | N3 · инженер Sol | A19/A21 | order-preflight и no-child fixtures |
| R10 | Product result отделён от envelope; metadata не запускает новую реализацию | N3 · инженер Sol | A05/A21–A23 | builder/envelope/Gateway regressions |
| R11 | Scratch/cache отделены от product scope | N3/N5 · инженер/редактор | A04/A05 | cache/path fixtures |
| R12 | Фактический diff/snapshot проверяет tracked, untracked, delete, rename, symlink, mode и binary | N3/N4/N6 · инженер/поставка | A04/A10/A11 | lineage/Gateway; real write boundary остаётся N7 |
| R13 | Reviewer сообщает findings и не чинит продукт/не назначает reviewer | N5 · редактор/Opus | A12 | handoff/reviewer regressions |
| R14 | Один исполнитель может использовать несколько skills; handoff только ради отдельного результата | N5/N7 · тимлид | A01/A17 | skill trigger eval и пилот |
| R15 | Консультация/premortem по конкретному риску; обязательные WAR ROOM/tribunal и review-of-review исключены | N5 · редактор | A12/A17 | focused instruction search |
| R16 | Tests/helpers/coverage запускаются по критериям и риску | N5/N7 · тимлид/TESTER | A01/A11/A17 | acceptance fixtures и pilot evidence |
| R17 | UI-бриф и критерии важнее шаблонных догм и новых состояний | N5/N7 · AEDILIS/PICTOR/Opus | A03/A11 | P3 screenshot/DOM/a11y proof |
| R18 | Diagnostic scripts и публикация не обязательны; внешняя запись gated | N5/N6 · редактор/поставка | A17/A20 | active allowlist/install manifest |
| R19 | Progressive disclosure и фактически прочитанный context вместо тотальной загрузки | N5/N7 · редактор/тимлид | A17/A18 | surface/eval and pilot context record |
| R20 | Один применимый независимый reviewer; no review-of-review и no quota findings | N5/N7 · Opus/тимлид | A11/A12/A24 | review ladder/handoff bindings |
| R21 | Единый routing source: Sol/Luna/Astra/Opus; Luna только high/xhigh; Sonnet/Fable/старые IDs исключены | N2/N7 · инженер Sol/Opus | A01/A15/A24 | route/model/effort round-trip; provider identity остаётся ограниченно наблюдаемой |
| R22 | Source/installed drift проверяется manifest/readback/rollback до live canary | N6/N8 · поставка/PONTIFEX | A14/A20 | install fixture и разрешённый canary |
| R23 | Названия ролей не являются механизмом полномочий; описание совпадает с исполнением | N5/N6 · редактор/тимлид | A20/A21 | instruction and contract audit |
| R24 | Hash/receipt — целостность наблюдения, не абсолютное авторство; trust framework вне 3.0 | N3/N5/N8 · инженер/поставка | A04/A13/A19/A24 | write-boundary probe; crypto trust не заявляется |
| R25 | Небольшой одинаковый pilot измеряет пригодность, а не рейтинг моделей | N7/N8 · тимлид/TESTER | P1–P6, A01–A24 offline | eval report; непроведённые live routes остаются непрошедшими |

## 3. Реестр ST01–ST17

| ID | Решение в 3.0 | Этап / владелец | Приёмка | Proof / граница |
| --- | --- | --- | --- | --- |
| ST01 | Surface audit охватывает integrations и installed consumers | N5/N6 · редактор/поставка | A17/A20 | updated surface/drift audit |
| ST02 | Legacy deep-search выключен; перед отдельным включением проверять HTTP status/schema/content, не принимать 503 | N5/N6; optional ремонт отдельно · researcher | A18/A19/A20 | Сейчас exclusion fixture; 503/empty-output fixture только для выбранного adapter |
| ST03 | Legacy deep-search выключен; перед включением deadline, size bound и URL-to-metadata binding | N5/N6; optional ремонт отдельно · researcher | A18/A19/A20 | Exclusion proof, не обязательный ремонт исключённого tool |
| ST04 | Native Playwright первичен; browse CLI только после dependency/size/status checks и без shared overwrite | N5/N6/N7 · researcher | A18/A19 | dependency/cwd/fallback probes |
| ST05 | Perplexity/Monid optional; цены и provider hop не обязательны | N2/N5/N7 · тимлид/researcher | A18/A20 | capability manifest/pilot; optional route may remain unproved |
| ST06 | Memoria не создаёт второй core store; cache/index writes видимы | N4/N5/N6 · инженер/поставка | A17/A20 | allowlist/cache fixture |
| ST07 | `mission_control.py`, `legion_core.py`, raw `evocate.sh` не входят в active lifecycle | N1/N5/N6 · тимлид/поставка | A20/A24 | legacy dispatch rejection |
| ST08 | Mandatory coverage/tribunal/publish/style/fix rules убраны из core | N5 · редактор | A01/A12/A17 | trigger-noise/ceremony eval |
| ST09 | Tool names/version проверяются capability inventory; старые API не копируются | N5/N7 · researcher/domain owner | A17/A19/A20 | Context7/tool round-trip |
| ST10 | Registry discovery исключён из core; перед отдельным включением исправить `--help`/strict argv/deadline | N5/N6 · maintenance owner | A17/A20 | Exclusion fixture; ремонт вне core release |
| ST11 | Regex/ports/text oracle имеют узкие evidence labels; exploit не в core | N5/N7/N8 · security gate | A13/A19/A24 | security boundary and failure fixtures |
| ST12 | Historical smoke/37-role routes отделены от active 3.0 manifest | N6/N7/N8 · поставка | A14/A15/A20 | active manifest/readback/canary |
| ST13 | Open Design fixture cwd-independent; real install не смешан с unit run | N6/N8 · поставка | A19/A20 | isolated fixture; live install only N8 |
| ST14 | Installer использует explicit allowlist, pinned versions и hash/readback; home config не копируется автоматически | N6/N8 · поставка | A14/A20 | cold/upgrade/rollback fixture |
| ST15 | Health/config не считаются retrieval/model proof; один backend на функцию | N6/N7 · тимлид/TESTER | A15/A19/A20 | real capability round-trip |
| ST16 | Broken cross-skill/optional references чинятся или явно объявляются dependency до включения | N5/N6 · редактор | A17/A20 | link/reference audit |
| ST17 | Project-specific paths/constants не являются portable facts; scope/date обязательны | N5/N6 · редактор/domain owner | A17/A20 | portable-skill scope audit |

## 4. Реестр CT01–CT12

| ID | Решение в 3.0 | Этап / владелец | Приёмка | Proof / граница |
| --- | --- | --- | --- | --- |
| CT01 | Один `AGENT_ORDER_JSON_V1` → `AGENT_RESULT_JSON_V1` и exact handoff; legacy только read-only | N1/N5/N6 · controller/редактор | A14/A21/A22 | contract/identity fixtures |
| CT02 | Claude native `structured_output` и text mode имеют явные adapters; conflicting sources reject | N3/N6/N7 · инженер Sol | A21–A23 | adapter fixtures + selected round-trip |
| CT03 | Codex `--output-schema` разрешается только по проверенному capability; unsupported route блокируется | N2/N3/N6/N7 · инженер Sol | A15/A21 | preflight and native-schema probe |
| CT04 | Hermes permissive parser не является acceptance; общий strict parser после transport | N3/N5 · инженер/редактор | A19/A21/A22 | duplicate/prose/missing-validator fixtures |
| CT05 | Hermes child correction с tools не входит в product dispatch; no-write capability обязательна | N3/N4/N7 · инженер Sol | A23 | disabled correction and harmless deny probe |
| CT06 | Malformed transport — protocol-failure receipt, не synthetic executor result и не replay | N3/N4/N7 · controller | A05/A23 | create-only/recovery fixtures |
| CT07 | Raw JSONL/wrapper сохраняется; requested model отделён от observed evidence | N3/N6/N7 · adapter owner | A15/A21 | extraction/hash/model evidence |
| CT08 | Controller fields не переписывают author payload; identity/ambiguity reject | N3 · controller | A22/A23 | strict envelope fixtures |
| CT09 | CLI capabilities/permission mode versioned; stale docs не запускаются | N5/N6/N7 · поставка | A15/A19/A20 | `--version`/focused help/readback |
| CT10 | Выбран один совместимый Loop/snapshot/lineage binding; две несовместимые цепочки не обещаются | N3/N4/N6/N7 · инженер | A07/A24 | lineage/restart fixtures |
| CT11 | Один canonical schema и минимальные native projections; review binding обязателен только review order | N1/N3/N6 · controller | A21/A22/A24 | projection/schema parity |
| CT12 | Считаются controller launches и report corrections; API calls/tokens — отдельная telemetry | N1/N4/N7 · controller/TESTER | A07/A08/A23 | state counter/interleaving/pilot report |

## 5. Исторический план и текущий dirty baseline

Старые этапы не потеряны при переходе к N1–N8:

| Исторический этап | Эквивалент в 3.0 | Сценарии |
| --- | --- | --- |
| T1 | N1 | A02/A13/A14 |
| T2 | N2 | A06/A15 |
| T3–T4 | N3 | A05/A19/A21–A23 |
| T5 | N3 | A03–A05/A11 |
| T6–T7 | N4 | A07–A10/A16 |
| T8–T9 | N5 | A01/A03/A11/A12/A17/A20 |
| T10 | N6 | A14/A19/A20/A21 |
| T11 | N7 | P1–P6 |
| T12 | N8 | canary/rollback |

Старые S-сценарии сохраняют смысл: `S1→A01`, `S2→A02`, `S3→A03`,
`S4→A04`, `S5/S6→A05`, `S7→A06`, `S8→A07/A08`, `S9→A08`,
`S10→A09`, `S11→A10`, `S12→A11`, `S13→A13`, `S14→A14`.

Девять исходных dirty-файлов не считаются реализованными автоматически:

| Файл | Наблюдаемая функция | Решение в плане | Этап / proof |
| --- | --- | --- | --- |
| `agent_contract_runner.py` | Подключает deterministic order preflight к admission/run boundary | Переиспользовать только после review; не принимать dirty diff как 3.0 | N1/N3; runner boundary regressions |
| `order_preflight.py` | Планирует prompt/path/output/candidate custody до child launch | Сохранить как часть единого preflight при прохождении scope/transport proof | N3; `regression_order_preflight.py` |
| `progress_drift_detector.py` | Read-only advisory progress/no-progress/drift | Подключить к одному controller loop; не выдаёт authority | N4; progress regressions |
| `blocker_packet_projection.py` | Evidence-only blocker classification/projection | Подключить как projection, не как второй controller | N4; blocker regressions |
| `regression_order_preflight.py` | Regression proof для preflight | Оставить release/maintenance proof, не запускать как product stage | N3/N6 |
| `regression_progress_drift_detector.py` | Regression proof для progress detector | Оставить release/maintenance proof | N4/N6 |
| `regression_blocker_packet_projection.py` | Regression proof для blocker projection | Оставить release/maintenance proof | N4/N6 |
| `autonomy-authority.schema.json` | Inert design-only trust shape | Не включать в core authority; schema pass не выдаёт permit | N1/N6; excluded install check |
| `autonomy-trust-contract-design.md` | Документ будущего P1/V3 trust boundary | Сохранить как blocked reference; не делать prerequisite обычной автономности | N1/N8; V3 boundary |

`agent_contract_runner.py` — единственный tracked dirty файл; остальные восемь
пока untracked. Они сохраняются вне документационного коммита и требуют
отдельного решения в N1. Это не скрытый принятый runtime.

## 6. Дополнительные пробелы на стыках

Здесь отделены наблюдаемый код и недоопределённое поведение плана. Не каждый
плановый пробел означает воспроизведённую runtime-аварию.

| ID | Основание и недостающее решение версии 1.2 | Решение в 1.4 / владелец / приёмка |
| --- | --- | --- |
| G01 | План требовал закрыть критерии миссии, но не задавал конкретного случая: два принятых поручения несовместимы после интеграции. Не было формы пользовательского delivery-отчёта | §4/N4/N7: один writer интеграции, accepted dependency revision, focused proof итоговых bytes и привязка применимого review; отчёт из acceptance с проектом, запуском и ограничениями. Тимлид/инженер; A25/P2. Новый merge-agent не нужен |
| G02 | В плане были restart/session ID и progressive disclosure, но не восстановление authority и открытых intent после compaction. `context-optimizer/SKILL.md:325` предлагает fresh session, что само по себе не восстанавливает миссию | §4/N4/N7: reload единственного state до продолжения, summary/memory не authority; provider probe проходит tool-result → следующий ответ. Тимлид/инженер; A26/P6. Native history engine не переписывается |
| G03 | `agent_contract_runner.py:1006` проверяет wall budget только для execute; `regression_agent_contract_runner.py:1665` прямо разрешает verify после expiry. `run_command:1246` и `run_proof_commands:1307` используют timeout заказа; Gateway:1170 передаёт тот же timeout. Direct path не использует process-group termination Gateway. План обещал общий предел и stopped без явной связи с этими путями | §3.2/N1/N4: Gateway — единственный active child launcher 3.0; direct dispatch отвергается до child. Cutoff и общий 30-секундный резерв на termination/finalization внутри deadline, TERM до 10 секунд; после cutoff новые inference/proof запрещены. Инженер; A27. Это решение плана; тест утечки процесса в этом аудите не запускался |
| G04 | `PROBATIO.md:53–60`: FIX immediately и три retry; `install.sh:96–99` копирует эту доктрину. Delivery bundle:3–10 подключает upstream delegation skills/повтор proof, eval bundle:7–9 включает agy/delegate_task. 38 SKILL.md и 12 integration entrypoints не исчерпывают загружаемые инструкции | N5/N6: audit фактической цепочки bundle → native skills → project/global instructions → hooks/MCP/CLI settings; устаревшие инструкции обновить/исключить из поставки. Редактор/поставка; A28. Loaded-chain readback N7 на изолированной сборке 3.0, глобальные настройки не меняются в аудите |
| G05 | Raw сохраняется целиком, selected inputs проверяют hashes, но в плане не было явного правила видимости raw/env и применения instruction boundary ко всем handoff artifacts. Gateway:563 наследует env процесса; это не доказанная утечка credentials | N3/N5: minimum input projection, restricted raw, безопасный пользовательский отчёт; secrets не передавать в prompts/receipts, чужой текст не authority. Инженер/security lens только по необходимости; A29 с искусственным marker. Не новый DLP/trust framework |
| G06 | Gateway:448/516/519/543 копит stream chunks и line buffer, затем объединяет bytes; buffered path:628 использует communicate. `strict_json.py:60` читает файл целиком. План ограничивал search output, но не executor streams/candidate; общая atomic-state формулировка не задавала случай ENOSPC/повреждения state | N3/N4/N6: конечные byte caps до накопления/parse, bounded capture, partial evidence не complete; persistence failure запрещает acceptance/reset/replay. Инженер; A30. Unit failure injection вместо заполнения реального диска, без нового storage service |

Все G-пункты дополняют текущие механизмы. Этапы N1–N8, состав моделей и бюджет
пилота не расширены. A25–A30 — проверяемые случаи для существующих regressions,
не шесть новых обязательных модельных миссий.

Кандидат 1.3 получил отдельный Claude review: пять уточнений D1–D5 обработаны
владельцем в итоговой редакции 1.4. Уточнены резерв времени, единственный Gateway launch, положительный
report-only случай P6, изолированная среда пилота и mapping Q1–Q8. Полный разбор
и граница между проверенным кандидатом и финальной редакцией — в §7
[отчёта ревью](CENTURION_3_0_PLAN_REVIEW.md). Новый полный Claude ACCEPT финальных
bytes не заявляется.

## 7. Проверки и оставшиеся границы

Текущий offline baseline: 12 regression scripts завершились с exit 0 и
содержательными PASS. Они включают legacy поведение, в частности G03, поэтому
зелёный baseline **не означает устранение проблем или pass A01–A30 в 3.0**.
Новые проверки G01–G06 ещё не реализованы.

Команды запускаются из runner scripts с `env PYTHONDONTWRITEBYTECODE=1 python3 -B`:

| Существующие scripts | Будущий proof в этой области |
| --- | --- |
| `regression_review_ladder.py` | N2, A01/A06/A13–A15, review floors |
| `regression_order_preflight.py` | N3, A04/A05/A19/A21; no-child на invalid inputs |
| `regression_response_envelope.py`, `regression_agent_result_builder.py` | N3, A05/A21–A23/A29/A30 |
| `regression_result_gateway.py` | N3/N4, capture/recovery, A09/A21–A24/A27/A30 |
| `regression_agent_contract_runner.py`, `regression_progress_drift_detector.py`, `regression_blocker_packet_projection.py` | N4, state/counters/stop/reload, A07–A10/A16/A25–A27/A30 |
| `regression_accepted_inputs.py`, `regression_accepted_inputs_gateway.py`, `regression_artifact_lineage.py`, `regression_legion_handoffs.py` | N3/N4/N5, source/candidate/review binding, A11/A12/A24/A25/A29 |

N5/N6 дополняют соответствующие проверки `node skills/tester/scripts/legion-skill-eval.mjs`,
surface/drift audits и kit `scripts/smoke.mjs` для A17/A20/A28. Эти дополнительные
прогоны здесь не повторялись: их предыдущие результаты и непрошедший полный
Hermes smoke перечислены в skills/tools-аудите. Ссылки/IDs и `git diff --check`
проверяются для текущих документов отдельно. Полный список не становится
обязательной проверкой каждого продуктового поручения.

| Граница | Где и как закрывать |
| --- | --- |
| Live provider/tool round-trips, no-write и recovery | N7; capability receipt, P1–P6. Пока не доказаны |
| Cold install/upgrade/rollback и real loaded surface | N6 offline, N8 отдельно разрешённый install/readback/canary. Пока не приняты |
| Runtime smoke новой policy | N6 после реализации; прежний pass не переносится |
| Каждая строка domain references/внешних зависимостей | Полностью не аудировались; включённые capabilities проверяются по N5–N7, исключённые требуют отдельной работы. Не обещается blanket certification |
| Независимый review финального текста | Точные candidate hashes, ответ и owner disposition отражаются в §7 отчёта ревью; проверка текста не подтверждает runtime |

**Вердикт:** версия 1.2 покрывала все 54 зарегистрированных пункта, но не все
существенные стыки. В 1.3 внесены решения G01–G06 и проверяемая связь с этапами;
в 1.4 зафиксированы решения D1–D5 и owner acceptance текущих bytes.
Можно переходить к N1; реализация, live-внедрение и автоматическое принятие
девяти dirty-файлов этим аудитом не выполняются. Утверждение «каждый аспект
нынешнего кода полностью проверен» было бы недостоверным.
