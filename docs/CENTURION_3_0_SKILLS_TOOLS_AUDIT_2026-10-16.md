# CENTURION 3.0 — аудит skills и tools

Исторический аудит на дату ниже. По решению владельца 2026-10-28 Open Design
перенесён в [архив](../archive/open-design/README.md); рекомендации включить его
в активную поставку больше не действуют. Остальные предметные навыки сохранены.

Дата: 2026-10-16. Этот документ является evidence-пакетом для единого плана
[CENTURION_3_0_IMPLEMENTATION_PLAN.md](CENTURION_3_0_IMPLEMENTATION_PLAN.md).
Он описывает поверхность, которую нужно включить в 3.0, но не устанавливает
runtime и не меняет live-конфигурацию провайдеров.

## 1. Граница и метод

Проверены:

- 38 корневых `skills/*/SKILL.md` и исполняемые скрипты;
- 12 integration skills в Claude, Codex, Hermes и Antigravity kits;
- MCP-конфигурации примеров репозитория и доступные host-конфигурации без
  чтения секретных значений;
- `skill-surface-audit.mjs`, `skill-drift-report.mjs`,
  `legion-skill-eval.mjs`, kit surface audits и smoke/регрессионные проверки;
- researcher toolchain (`deep-search.js`, `browse.js`, `check-deps.js`,
  `monid-adapter.js`), Open Design, Memoria и security scripts;
- реальные read-only capability probes Brave Search, Context7, Playwright и
  Camofox health.

Доказательство наличия файла не считается доказательством установленного
агента, активного MCP или рабочего provider route. Для каждого surface ниже
разделяются `prompt-only`, локальный executable, MCP/provider и фактическая
доступность.

## 2. Итог

Текущая поверхность функционально богата, но для 3.0 она чрезмерна как
всегда загружаемый набор. Основные источники лишней сложности:

1. 38 entrypoint-файлов занимают 279 043 bytes (около 273 KiB) и 8 143 строк. Аудит
   surface видит 44 skills (проект плюс system roots) и около 60k оценочных
   токенов по грубой формуле words × 1.3. Это объём библиотеки, а не измеренный
   расход одного запроса: skills загружаются по выбору. Дубликатов имён в
   охваченных roots не найдено, но отсутствие дубликатов не устраняет
   trigger noise и обязательные церемонии внутри отдельных skills.
2. Общая политика дублируется в skills, kit overrides, smoke tests и старых
   документах. Это создаёт расхождение, когда обновлена одна копия.
3. Несколько skills требуют действий всегда: WAR ROOM/tribunal, 80% coverage,
   чтение полной библиотеки references, обязательный глубокий анализ,
   публикацию HTML или дополнительные тестовые состояния. Эти правила не
   пропорциональны простому заказу.
4. Часть tools присутствует только в конфигурации или требует отсутствующей
   зависимости. `researcher/check-deps.js` подтвердил Chromium, но не нашёл
   `playwright-core` в корне researcher. Это делает локальный `browse.js`
   нерабочим в текущем checkout.
5. Legacy control paths (`mission_control.py`, raw `evocate.sh`) не являются
   единым controller 3.0 и должны остаться вне активного dispatch.

Вывод: не удалять весь Legion и не загружать всё сразу. Нужны один короткий
control surface, условные domain skills и один канонический tool path для каждой
задачи.

## 3. Решения по root skills

Статусы:

- **оставить** — активный функциональный capability, совместимый с authority 3.0;
- **обновить** — capability полезен, но содержит устаревшее правило или
  лишнюю обязательную операцию;
- **оптимизировать** — оставить только on-demand и вынести детали в references;
- **не включать** — не активировать в обычном 3.0 dispatch; файл можно сохранить
  для явно запрошенной maintenance/domain работы.

| Skill | Целевой слой | Решение | Почему | Изменение в 3.0 |
| --- | --- | --- | --- | --- |
| `orchestrator` | core: встроить | обновить | Главный routing surface; должен быть единственным владельцем dispatch | Оставить только intake, scope, model/effort, handoff и closure; убрать вторые командные иерархии |
| `planner` | core: встроить | оставить | Декомпозиция и durable plan расширяют способность тимлида | Один plan snapshot; не превращать каждый шаг в отдельный агент |
| `context-optimizer` | core: встроить | обновить | Progressive disclosure полезен, но «80% reduction», EPCC и абсолютные запреты не являются acceptance | Короткий loader policy; размер и загрузка проверяются по факту, без фиксированного процента |
| `researcher` | on-demand | обновить | Единственный специализированный research workflow, но текущий deep-search/browser имеет dependency и error gaps | Ввести L0–L5, fallback Brave/Context7/Playwright, bounded evidence и provider-neutral adapter |
| `architect` | on-demand | оставить | Read-only архитектурная консультация закрывает отдельный пробел Astra | Только по material ambiguity; не обязательная стадия и не reviewer |
| `coder` | on-demand | оставить | Производственная реализация | Scope и result contract задаются controller; не делегирует дальше сам |
| `reviewer` | on-demand | обновить | Независимое ревью необходимо, но 500 строк и всегда включаемые frontend gates раздувают работу | Короткий risk-first review; React/browser/performance gates только по применимости |
| `tester` | on-demand | обновить | Regression/eval capability нужна; правило 80% coverage расширяет scope | Риск- и oracle-based proof; coverage только если заказан критерием |
| `error-handler` | on-demand | оставить | Воспроизведение и диагностика hard failures | Не запускать после каждого несущественного warning |
| `refactorer` | on-demand | обновить | Сохраняет поведение и убирает debt | Убрать обязательное «сначала написать тесты» при отсутствии требования; focused proof достаточен |
| `security` | on-demand | оставить | Guardrail для secrets, dependencies, MCP и опасных действий | Обязателен только при risk trigger, не для каждого заказа |
| `praemonitor` | on-demand | оптимизировать | Полезен для high ambiguity, но не нужен для micro work | Вызывать один раз при material risk; не строить отдельный debate cycle |
| `censor` | on-demand | обновить | Adversarial verification полезна как lens | Убрать обязательный tribunal/three-voice debate; findings возвращаются одному тимлиду |
| `documenter` | on-demand | оставить | Итоговый README/API/report capability | Только требуемая документация; не переписывать проектные docs автоматически |
| `git-master` | on-demand | оптимизировать | Нужен для branch/commit/recovery, но Git Flow и PR workflow не нужны каждой миссии | Короткий safe subset; rebase, reset, push, PR и release только при отдельном заказе |
| `capabilities` | on-demand | оставить | Делает surface наблюдаемым | Возвращать актуальный runtime inventory, а не статический список |
| `prompt-engineer` | on-demand | оптимизировать | Полезен для неясного брифа, но модели уже умеют обычную трансформацию | Только при неоднозначных acceptance criteria; не добавлять второй план |
| `pontifex` | on-demand | оставить | Реальная infra/DB/service функция | On-demand, с явной границей production и credentials |
| `open-design-producer` | on-demand | оставить | Исполняемый UI/design bridge с artifact и screenshot proof | Только UI-заказ; deletion/publication остаются explicit-gated |
| `aedilis` | on-demand | обновить | Сильная UI/UX экспертиза; универсальные «16px», 100ms и запрет hamburger устарели | Принципы становятся контекстными; бриф и accessibility proof важнее догмы |
| `pictor` | on-demand | обновить | UI implementation расширяет продуктовые возможности | Все состояния только для реально интерактивного компонента; Context7 по версии, без обязательной анимации |
| `nomenclator` | on-demand | оптимизировать | Нужен для source copy и naming | On-demand вместе с UI/content; не отдельный handoff для каждой строки |
| `glossator` | on-demand | оптимизировать | Реальная i18n и locale QA ценность | Включать при нескольких locale/RTL/plural requirements; иначе не загружать |
| `praeco` | on-demand | обновить | Telegram API быстро меняется, Context7 полезен | Один источник актуальной документации и один project-pattern check, без чтения всех references |
| `ludifex` | on-demand | оптимизировать | Глубокая game product expertise | Только game-заказы; retention references и screens не обязательны вне игры |
| `aleator` | on-demand | оптимизировать | Этическая gamification аналитика | Только игровые/поведенческие механики; caps и exit points остаются domain safety, не общий gate |
| `mercator` | on-demand | оптимизировать | Marketing capability реальна | Не требовать каждый framework и «So What?» для технического заказа |
| `orator` | on-demand | оптимизировать | Social/content production | Платформенный reference только для соответствующей площадки; не общий research step |
| `indagator` | on-demand | оптимизировать | SEO и search visibility отдельная ценность | Search Console/PageSpeed проверять только если доступ и scope требует; не блокировать совет без них |
| `tabularius` | on-demand | обновить | Форматирование отчётов полезно | Local artifact по умолчанию; TinyNotepad, пароль и публикация только explicit-gated, не обязательны |
| `velites` | on-demand | обновить | Active recon расширяет security proof | Только разрешённый target и explicit security scope; портовый scan не запускается автоматически |
| `haruspex` | on-demand | обновить | Быстрый triage полезен | Явно маркировать regex как candidate, не SAST verdict; не обещать полноту |
| `sicarius` | legacy / вне поставки | не включать | Browser exploit/PoC — опасная side-effect capability и сейчас не имеет общего gate | Сохранить для отдельного security order после trusted authorization и изолированной среды |
| `augur` | on-demand | оптимизировать | Узкая ScamNet/pool intelligence | Только соответствующий on-chain order; убрать обязательный WAR ROOM |
| `quaestor` | on-demand | оптимизировать | On-chain/DEX analysis расширяет доменную глубину | Три timeframe/3 signals только если доказательно нужны; не общий minimum |
| `artifex` | maintenance | не включать | Создаёт skills в global `~/.claude/skills`, меняя runtime surface | Только maintenance request; не активировать через обычный mission dispatch |
| `skill-quartermaster` | maintenance | не включать | Внешний skill registry не является необходимостью и добавляет supply-chain risk | Оставить ручным discovery/audit инструментом с deny-by-default install |
| `evocate-ad-opus` | legacy / вне поставки | объединить с controller | Уже корректно описывает Gateway delegation; отдельный повтор не расширяет функцию | Полезный contract перенести в общий controller entrypoint; raw launcher не возвращать |

Колонка слоя задаёт размещение функции: `core: встроить` означает извлечение
общего правила в короткий контракт тимлида, не сохранение трёх загружаемых
entrypoints. `on-demand` — инструкции по задаче; проверка reviewer включается
по V-профилю, а не по наличию skill. Maintenance/legacy не входят в обычные
поручения. `evocate-ad-opus` уже описывает корректную bounded delegation через
Gateway; исключается отдельный повтор этой инструкции, сама функция остаётся
у controller. Raw `evocate.sh launch` и этот prompt-only skill — разные вещи.

«Оставить capability» не означает «оставить отдельного агента и полный учебник».
Целевая группировка N5: короткий entrypoint тимлида; engineering recipes
(`coder`, debugging, refactoring, testing, git, docs); independent review с
security/premortem lenses; research; UI/design. Telegram, i18n, игры, маркетинг,
on-chain и Solana — подключаемые domain packs. Maintenance skills не входят
в обычный executor context. Точное число файлов не является KPI; устраняем
дублирующую инструкцию и handoff, сохраняя проверяемую функцию.

Общие советы «пиши хороший код», Git-команды, SOLID, EARS и шаблоны отчётов сами
по себе не расширяют reasoning современных моделей. Их сохраняем в references
только при наличии проектного правила, воспроизводимой ошибки или нужного
формата. API knowledge, локальные conventions, специфические failure modes,
tool adapters и проверки результата дают отдельную пользу. Вывод о пользе
пакета не является сравнительным benchmark Sol/Opus/Astra/Luna.

## 4. Integration skills

Все 12 entrypoints (пути относительно `integrations/`):

| Entry point | Слой и решение |
| --- | --- |
| `claude-legion-kit/plugin/SKILL.md` | Core adapter: обновить под общий контракт, убрать вторую иерархию и обязательный WAR ROOM |
| `claude-legion-kit/plugin/skills/claude-order/SKILL.md` | Core adapter: сохранить bounded order/result/scope proof, синхронизировать общий контракт |
| `antigravity-legion-kit/agy-plugin/skills/centurion-legion/SKILL.md` | Legacy: исключить из активной поставки, Gemini route не входит в 3.0 |
| `codex-legion-kit/skills/camofox-browser/SKILL.md` | On-demand optional: fallback, не обязательный браузер |
| `hermes-legion-kit/skills/autonomous-ai-agents/agent-contract-runner/SKILL.md` | Core adapter: один dispatch/acceptance path, обновить routing и scope |
| `hermes-legion-kit/skills/autonomous-ai-agents/aquila-team-orchestration/SKILL.md` | Core adapter: общий контракт тимлида, не отдельный OPTIO/дополнительный commander |
| `hermes-legion-kit/skills/autonomous-ai-agents/aquila-execution-state/SKILL.md` | On-demand operational projection: оставить производной, не загружать на каждый dispatch |
| `hermes-legion-kit/skills/autonomous-ai-agents/aquila-harness-audit/SKILL.md` | Maintenance: аудит фактических tools/model/config, не каждый заказ |
| `hermes-legion-kit/skills/autonomous-ai-agents/aquila-executor-eval/SKILL.md` | Maintenance: существующий N7 eval, без нового benchmark framework |
| `hermes-legion-kit/skills/autonomous-ai-agents/aquila-self-debug/SKILL.md` | Maintenance: конкретный runtime сбой, без постоянного self-improvement loop |
| `hermes-legion-kit/skills/software-development/solana-program-engineering/SKILL.md` | On-demand domain: сохранить account invariants/version-aware references; production gates остаются |
| `hermes-legion-kit/overrides/skills/research/research-paper-writing/SKILL.md` | Optional domain, вне core поставки: неполный reference bundle; включать только полным пакетом для paper-заказа |

`agent-contract-runner`, `aquila-execution-state`, `aquila-team-orchestration`,
Claude plugin root и `claude-order` обновить под один authority contract.
Execution-state остаётся производной, не вторым writer. Claude root — adapter
к общим skills, не ещё один тимлид и не 37 обязательных процессов.

`aquila-harness-audit`, `aquila-executor-eval`, `aquila-self-debug` оставить
maintenance-only: аудит окружения, выпуск и диагностика реальной неисправности.
Не загружать их для каждого заказа. Общий `open-design-producer` — отдельный
root capability, уже учтённый в 38; не считать его 13-м integration skill.

`camofox-browser` оставить fallback для anti-bot страниц после неудачи
Playwright; health check не доказывает browser retrieval.
`solana-program-engineering` оставить только для Solana-заказов.

Не включать в обычный 3.0 dispatch:

- Antigravity/Gemini route и `gemini-3.8-flash`;
- Sonnet, Fable, старый `gpt-6-sol` и любые implicit fallback aliases;
- Hermes `research-paper-writing`, если заказ не является ML-paper;
- старые WAR ROOM/quality-gate/skill-migrator workflows, если они дублируют
  controller contract.

Сохранение kit-файлов для compatibility не означает active route. Каноническая
матрица моделей находится только в routing source плана и controller.

## 5. Tool matrix

| Tool surface | Наблюдаемый статус | Решение | Правило 3.0 |
| --- | --- | --- | --- |
| `rg`, git, Node, Python | локальные executable, доступны | оставить | Первичный локальный evidence и deterministic proof |
| Brave Search MCP | read-only tool успешно ответил | оставить | L1/L2 web discovery; bounded results, primary URLs |
| Context7 MCP | resolve и docs query успешно ответили | оставить | Только library/API docs; сначала resolve, максимум три topic queries |
| Playwright MCP | безопасный `example.com` navigation/snapshot прошёл | оставить | Канонический browser extraction/UI proof; чтение DOM допустимо, запись/form submit требует полномочий заказа |
| Chrome DevTools MCP | surface доступен, функционально пересекается с Playwright | оптимизировать | Только frontend diagnostics/performance; не второй web-research path |
| Camofox | health endpoint отвечает, browser не запущен | оптимизировать | Fallback для anti-bot; health не считается page proof |
| `researcher/browse.js` | Chromium есть, `playwright-core` не найден в researcher dependency path | отключить по умолчанию; обновить перед optional включением | Native Playwright первичен. Для CLI нужны единый manifest/lock, dependency preflight и bounded JSON/output |
| `researcher/deep-search.js` | provider script есть; API key присутствует в среде, route не запускался | отключить по умолчанию; обновить перед optional включением | Основной поиск через native/Brave; status/schema/timeout/size и разрешённый output обязательны до включения старого скрипта |
| `researcher/monid-adapter.js` | offline adversarial tests pass; disabled without `--enable` | оставить с ограничением | Только L4 optional, fresh inspect/cost authorization/SSRF validation; never default |
| Memoria MCP | local semantic index code exists; lazy reindex writes outside repo | не включать в core | Native memory/search достаточно по умолчанию; semantic index optional только при доказанной пользе, согласованных roots и cache writes |
| Serena MCP | host configuration present | оптимизировать | On-demand symbol navigation for large repos; no mandatory initialization for simple work |
| Open Design MCP/bridge | smoke passed; isolated installer cross-client has environment failure | обновить optional UI adapter | Artifact/lifecycle proof; исправить изоляцию fixture в N6, реальные provider/install checks N7/N8. P3 может работать напрямую через executor/browser |
| GitHub MCP | host configured, write capability external | оптимизировать | Read-only by default; issue/PR/write requires order scope |
| Solana MCP | host configured | оптимизировать | Only Solana specialist path |
| sequential-thinking | в текущем Hermes config disabled, в Codex зарегистрирован | не включать | Не получает новых внешних данных; обязательная сериализация размышлений инструментом не обоснована |
| markitdown | текущий Hermes config enabled; конвертация не проверена | оставить optional | PDF/Office extraction даёт новую функцию; только при таком входе и после bounded probe |
| deepwiki | текущий Hermes config enabled; tool call не проверен | оптимизировать | Optional external-repo knowledge; локальный source/official docs первичны |
| pal | текущий Hermes config enabled; вызов не проверен | не включать | Дополнительный model router/consensus дублирует тимлида и принятую review matrix |
| ru-marketplace | текущий Hermes config enabled; вызов не проверен | не включать в core | Только отдельный marketplace-заказ, без auto-install |
| Hermes web/browser/file/terminal, memory/session-search, vision | native host capabilities; список в baseline не является live proof | оставить по потребности | Не дублировать одновременно native tool и MCP с одной функцией; vision нужен для screenshot review |
| image/video/TTS, cron, channels, broad delegation | в историческом baseline, актуальная работоспособность не проверена | не включать в core | Узкая media/automation capability только при отдельной задаче; не новые исполнители команды |
| `mission_control.py` | legacy two-step recon/analyze runner | не включать | Do not use as 3.0 entrypoint; preserve for historical regression only |
| `scripts/evocate.sh` | raw launch explicitly retired | не включать | Result Gateway is the only external delegation route |
| `findskills-audit.mjs` | external registry query works but `--help` is interpreted as a search | отложить вне core | Исправить help/timeout при отдельном maintenance discovery; не является prerequisite 3.0 |
| `skill-surface-audit`/`drift-report` | project audit passes but omits integration surface and installed consumer roots | обновить | Scan canonical + integration roots, exclude generated/node_modules, compare installed copies read-only |
| `legion-skill-eval` | offline eval passes existing expectations | обновить | Add active matrix, mandatory-ceremony and trigger-noise checks; not quality ranking |

### Остальные исполняемые компоненты и зависимости

| Пути/группа | Решение и реальная функция | Этап |
| --- | --- | --- |
| `skills/orchestrator/scripts/mission-prep.mjs` | Обновить optional deterministic hint; не выдаёт authority и не назначает дополнительных агентов сам | N2/N5 |
| `libs/legion_core.py`, `tests/test_mission_lifecycle.py`, `pipeline/`, `FERRATA.md` | Не переносить второй MissionState/marker protocol в активный 3.0; используемые standalone tool helpers оставить только при реальной зависимости | N1/N6 |
| runner scripts: preflight, result builder/gateway, strict JSON/envelope, lineage/accepted inputs, ledger/review ladder, monitor/projections | Сохранить необходимые deterministic controls; один dispatch/acceptance path. Regression scripts — release/maintenance, не каждый продуктовый заказ | N1–N6 |
| shared `integrations/legion-contracts`, Claude result validator и guards | Сохранить order/result validation и scope proof; синхронизировать copies через существующую поставку, не новый validator framework | N3/N6 |
| `skills/open-design-producer/scripts/open-design.mjs`, bridge CLI/MCP и Claude wrapper | Одна shared implementation с тонкими адаптерами; model/provider Open Design подтвердить отдельно, не считать доказанным по выбранному reviewer | N5–N7 |
| Claude `external-skill-scan.mjs`, `frontend-sweep-plan.mjs`, surface audit | Maintenance / явно заказанный frontend sweep. Regex scan — список подозрений, не сертификат доверия; audit обновить под 3.0 | N5/N6 |
| Codex `surface-config.mjs`, `codex-surface-audit.mjs`, `sync-agents.mjs` | Read-only audit оставить, sync только в поставке; не создавать копии роли для каждой модели | N6 |
| Antigravity MCP `mission_prep/select_legionary/load_skill_brief/war_room/quality_gate/agy_delegation_brief` | Исключить из активного 3.0. Дополнительная схема выбора исполнителя/дебатов и Gemini dispatch не нужны | N2/N6 |
| Antigravity `external_skill_*`, `frontend_*`, `content_*`, refresh scripts и AGY guard | Не переносить весь toolkit. Если нужен reference search, использовать уже общий Open Design bridge; catalogs остаются optional historical data | N5/N6 |
| `install.sh`, `install-owned-files.mjs`, kit installers | Обновить существующий manifest/профили: core отдельно от optional, никаких автоматических Memoria/sequential-thinking/Gemini installs | N6/N8 |
| package manifests/lockfiles, smoke/tests | Включать зависимости только выбранных tools; один researcher manifest, подходящий browser binary; не требовать Sonnet/Fable/37 agents/старый model baseline как acceptance 3.0 | N5/N6 |

Отложенные скрипты — **вне реализации/приёмки N1–N8**, кроме проверки, что они
не попали в active dispatch/install. Сохранить security/authoring знания можно
без этих wrappers. Ремонт возможен только отдельным поручением:

| Скрипт | Ценность и ограничение | Условие возможного возврата |
| --- | --- | --- |
| `skills/artifex/scripts/init.js`, `validate.js` | Создание skill; жёсткий home output, regex-валидация не проверяет безопасность | Explicit maintenance order, явный target; предпочтительно native skill authoring |
| `skills/velites/scripts/recon.py` | Семь COMMON_PORTS + headers; полезен как узкая автоматизация, не полный attack-surface audit | Отдельный разрешённый recon scope; ограничить targets/порты и сравнить с доступными средствами |
| `skills/haruspex/scripts/scan_code.py` | Regex SQL/XSS/RCE без dataflow, обходит директорию | Отдельный SAST/triage order, bounded scope/excludes; сначала существующие project analyzers/rg |
| `skills/sicarius/scripts/exploit_verify.py` | Form input + text/URL oracle; не универсальное доказательство exploit | Отдельный security order, проверяемое разрешение и изолированная среда |

Регистрация tool в текущей сессии подтверждена для 103 MCP methods в девяти
группах; это число предложенных схем, не 103 выполненных проверок. Нельзя
автоматически переносить всю host-конфигурацию в агента 3.0. GitHub/Memoria
есть в Claude config, а в этой Codex-сессии не предлагаются; Hermes inventory
отличается и от обоих, и от baseline июля. При dispatch нужен фактический
набор одного consumer runtime.

### Реестр дополнительных проблем

| ID | Наблюдение / источник | Решение |
| --- | --- | --- |
| ST01 | `context-optimizer/scripts/{skill-surface-audit,skill-drift-report}.mjs`: roots ограничены project, system, migrate-to-codex | Охватить install consumers/integrations; отсутствие совпадающих имён не доказывает отсутствие противоречий |
| ST02 | `researcher/scripts/deep-search.js`: HTTP status не проверяется; offline 503 fixture даёт success/`No response` | Проверять status, schema, непустой content; ошибка не становится evidence |
| ST03 | Там же: нет request timeout/response size bound; auto-write в `skills/researcher/reports`, citations сопоставляются по индексу | Deadline/size, явный output path, связь URL с metadata, не позиционная догадка |
| ST04 | `researcher/scripts/browse.js`: unconditional HTML в `~/.claude/debug/browse-latest.html`, `--no-sandbox`, hardcoded Chrome/131 UA, status не классифицируется; два package.json | Предпочесть native browser; поддерживать CLI только как проверенный fallback с bounded output, one manifest, явным runtime path и без shared overwrite |
| ST05 | `researcher/SKILL.md`: Perplexity primary, устаревающая model/price таблица; `monid` executable не найден | Убрать обязательный provider hop/цены; Perplexity optional, Monid disabled by default, оба вне critical path |
| ST06 | `memoria/src/index.ts`, `indexer.ts`: home-wide Claude memory roots, lazy reindex; Nomic embedder загружается по потребности | Не добавлять второй store в core; нельзя выдавать поиск за операцию без cache writes, если включена индексация |
| ST07 | `mission_control.py`, `legion_core.py`, `evocate.sh`: отдельное состояние/старые session paths | Не активировать в новом lifecycle; standalone tool result адаптировать без второго controller |
| ST08 | `tester`, `censor`, `augur`, `tabularius`, `reviewer`, `aedilis`, `refactorer` | Убрать обязательные coverage/tribunal/publish/style/fix операции; оставить применимые recipes |
| ST09 | `praeco`/`pictor`: примеры `get-library-docs`, тогда как доступен `query_docs`; `praeco` смешивает v9.x и 10.1+ | Обновить tool names из capabilities и проверять API/version перед использованием; не копировать старые методы как актуальные |
| ST10 | `findskills-audit.mjs --help` выполнил внешнюю query `--help`; `fetch` без deadline | Offline help/strict argv/timeout; сеть только при explicit discovery, не авто-install |
| ST11 | Security scripts обещают более широкий анализ, чем regex/ports/text-or-URL oracle | Сохранить узкие capabilities и честные evidence labels; exploit не в core |
| ST12 | Claude/Hermes smoke и surface audits проверяют старые routes/baseline/37 role entries | Разделить исторические fixtures и acceptance активного manifest 3.0; зелёный старый smoke не валидирует новую политику |
| ST13 | `open-design-bridge/tests/references.test.mjs`: относительный `path.resolve('tests/fixtures/mock-od.mjs')`; cross-client fixture вызывает реальный Hermes CLI | В N6 устранить cwd-зависимость/изолировать offline fixtures; реальный install проверять отдельно, не смешивать с unit run |
| ST14 | `install.sh` регистрирует Memoria/sequential-thinking и устанавливает широкий набор; несколько runtime copies | Поставка по явному allowlist, version/hash readback; pinned/reproducible tool versions, без home config копирования |
| ST15 | Host MCP/toolsets и документация различаются; configuration/health не доказывают retrieval или model round-trip | Capability inventory без secrets, один backend на функцию, safe probe в реальном consumer перед использованием |
| ST16 | `pictor/SKILL.md:56` ссылается на `references/component-interface-systems.md`, которого рядом нет (есть у aedilis). ML-paper override ссылается на references/templates, отсутствующие и в пакете, и в проверенном installed path | Исправить cross-skill ссылку. Для optional paper pack нужен полный пакет/объявленная зависимость до включения; не делать его ремонт условием core release |
| ST17 | `praeco/references/our-patterns.md` содержит путь `/home/yokinaboy/sniper/telegram/base/src/`; PICTOR conventions описывают конкретный Snorter; AUGUR содержит constants/таблицы от 2026-03-10 | Проектные знания подключать только к соответствующему project scope, с датой и перепроверкой; не включать их как универсальные facts в portable skill |

Проверка ссылок различает инструкции и примеры: `references/api.md`,
`references/patterns.md`, `scripts/validate.sh` в context-optimizer и
`scripts/check-no-overflow.mjs` в executor-eval находятся в примерах, поэтому
не записаны как сломанные обязательные зависимости. Ремонтировать шаблонные
пути «для зелёного аудита» не требуется.

Ключевые исходники: [deep-search.js](../skills/researcher/scripts/deep-search.js),
[browse.js](../skills/researcher/scripts/browse.js),
[surface audit](../skills/context-optimizer/scripts/skill-surface-audit.mjs),
[installer](../install.sh),
[Open Design fixtures](../archive/open-design/integrations/open-design-bridge/tests/references.test.mjs).
Остальные пути в таблицах указаны относительно корня репозитория. Полное тело каждого
domain reference и каждой внешней зависимости не проверялось построчно;
охват — все entrypoints и группы executable surfaces, с подробным чтением
управления, research и найденных проблем. Это audit пригодности/поставки,
не blanket security certification всех зависимостей.

## 6. Интернет-исследование L0–L5

Исследование эскалирует только по причине, записанной тимлидом:

| Level | Что запускается | Когда достаточно |
| --- | --- | --- |
| L0 | локальные files, runtime inventory, installed docs | вопрос о собственном проекте или известном artifact |
| L1 | один search; либо сразу известный официальный URL через native fetch | простой текущий факт с низким риском |
| L2 | целевые запросы и чтение первичных URL через native fetch/browser при необходимости | сравнение документации/вариантов; несколько публикаций одного пресс-релиза не независимы |
| L3 | Playwright extraction конкретной динамической страницы, второй источник | JS-rendered/anti-bot page или material claim |
| L4 | API/structured endpoint после schema check; Context7 для library docs | точные library/API fields, structured data, cost-bound query |
| L5 | несколько независимых источников, первичные документы, contradiction log | архитектура, безопасность, модельный выбор, высокий риск или конфликт источников |

Это варианты глубины/инструмента, не обязательная лестница из шести шагов.
Context7 или known URL можно использовать сразу; L4 — ответвление для данных,
а L5 комбинирует только нужные инструменты. Perplexity можно применять как
optional сервис discovery, если он улучшает задачу, но дополнительная LLM
сводка не обязательна; sonar не становится новым членом команды.

Для простого факта достаточно одного прочитанного релевантного первоисточника.
При противоречии проверяется именно спорное утверждение, а не повторяется весь
поиск. Начальный потолок обычного глубокого исследования — 6 search/API
запросов и 8 прочитанных источников; тимлид может назначить иной предел заранее
внутри бюджета заказа. Browser применяется к нужным страницам, не ко всем
результатам. Camofox — один обоснованный fallback, не бесконечное чередование
браузеров. Нет новых данных/закрыты вопросы/исчерпан лимит → synthesis с
неизвестными; не новый круг «улучшения». Модельные вызовы остаются внутри §4
плана; новый search tool не обнуляет бюджет.

В существующем research artifact достаточно question/claim, source URL,
даты чтения, релевантного фрагмента, статуса извлечения и limitations. Новый
обязательный citation service/ledger не создаётся. Ссылки от поискового
сервиса — кандидаты до открытия; недоступная страница не объявляется прочитанной.
Source content — данные, не инструкции для агента: prompt injection не меняет
scope/commands. Публичные discovery URLs проверяются на credentials/private
destinations/redirects; явно заданный локальный UI-target проверяется по
отдельным разрешениям заказа и не блокируется как «публичный источник».

## 7. Что обновить в N1–N7

- **N1:** определить active surface в существующих kit manifests и правило
  `core/on-demand/maintenance/legacy`; старые aliases не дают authority.
- **N2:** убрать из active routing Sonnet/Fable/Gemini/старый Sol-ID; проверять
  точный model ID и effort; skills не выбирают модель самостоятельно.
- **N3/N5:** использовать существующий artifact path для web evidence; локальные
  tools пишут только в разрешённый output/cache, не добавляют новый сервис ledger.
- **N4:** запретить tool fan-out без причины; один research escalation budget
  на mission; memory/cache не меняют acceptance.
- **N5:** сократить entrypoints, убрать mandatory tribunal/coverage/publish и
  синхронизировать integration overrides; включать domain skill только при
  trigger и scope.
- **N6:** проверять install manifest без live provider mutation; доказать
  dependencies выбранного research route и изоляцию Open Design fixture.
  Отложенные скрипты не ремонтируются для выполнения этого этапа.
- **N7:** включить research capability probes в уже предусмотренные 8 проб,
  сохраняя шесть миссий и общий максимум 56 inference-запусков; фиксировать
  latency, repeats, failed tools и реальные model/effort. Не считать наличие
  MCP или smoke pass доказательством качества модели.

## 8. Evidence и ограничения

Положительные проверки:

- `skill-surface-audit.mjs`: 44 surface, 0 duplicate names, 0 drifted
  duplicates;
- `legion-skill-eval.mjs`: pass;
- Claude/Codex repo surface audits: pass (38/37 canonical surfaces);
- Python script tests: 11 passed;
- Shared contracts, Claude, Codex и Antigravity kit smokes: pass;
- Open Design basic smoke: pass;
- Monid offline adversarial tests: pass;
- Brave, Context7, Playwright, Camofox health probes: ответили.

Ограничения:

- `researcher/check-deps.js`: `playwright-core` missing, Chromium found;
- `deep-search.js` при HTTP 503 с JSON без `error` записал `No response` и
  завершился с кодом 0 — дефект, обязательный к исправлению перед optional включением;
- полный Open Design test run из корня checkout дал 61/64: один cross-client
  случай остановлен isolated Hermes install; два reference случая зависели от
  cwd. Только эти два повторены из `integrations/open-design-bridge`: 2/2 pass.
  Это не полный 64/64 pass;
- Hermes isolated install остановился на сборке `python-olm` под bundled
  Python 3.14; это не доказательство провала bridge logic, но остаётся N8
  dependency failure для N6; готовность live installation проверяется N8;
- Hermes umbrella smoke был прерван во время packaged regressions; итоговый
  pass не получен. Его полный запуск остаётся N6; audit не маркирует его pass;
- реальные inference routes моделей и production write isolation этим аудитом
  не подтверждены; они остаются N7/N8 acceptance.

Команды проверки: `node skills/context-optimizer/scripts/skill-surface-audit.mjs`,
`node skills/context-optimizer/scripts/skill-drift-report.mjs`,
`node skills/tester/scripts/legion-skill-eval.mjs`,
`node skills/researcher/scripts/check-deps.js`,
`node skills/researcher/scripts/test-monid-adapter.js`,
`pytest -q tests/test_script_imports.py tests/test_haruspex_scan_code.py tests/test_velites_recon.py`,
kit `scripts/smoke.mjs` и Claude/Codex `*-surface-audit.mjs --repo-only`.
Open Design: `node --test integrations/open-design-bridge/tests/*.test.mjs`
из repo root; затем только два cwd-зависимых случая через
`node --test --test-name-pattern='accepted design bundle|design production rejects a snippet' tests/references.test.mjs`
из каталога bridge. HTTP-503 fixture выполнял исходный script в Node VM с
подставленными HTTPS/FS: ноль network calls, один записанный mock report,
`content=No response`, exit code 0. Установка зависимостей researcher и вызовы
Perplexity/Monid run не выполнялись.

Эти результаты не требуют изменения live runtime в рамках аудита. Владелец
обновил план после одной проверки Claude Opus; разбор замечаний и границы
проверки версии 1.1 находятся в [отчёте ревью](CENTURION_3_0_PLAN_REVIEW.md).
