# Bounded recovery: offline pilot reference

Этот справочник помогает Aquila продолжить согласованную задачу после сбоя или
смены контекста. Он не вводит policy, schema, approval, retry или dispatch и не
даёт полномочий на действие. Действуют исходный order, текущие approvals,
существующие contract/gateway/review rules и лимит: одна начальная product
attempt плюс не более одной finding-mapped correction.

## Бюджет шага и checkpoints

Планируйте каждый исполняемый шаг консервативно на **180-240 секунд**, оставляя
остаток внешнего окна наблюдения на остановку, фиксацию checkpoint и readback
процесса и bytes. Это операционная эвристика декомпозиции, а не новый timeout и
не гарантия завершения: реальный шаг может закончиться раньше, позже или быть
прерван внешним пределом наблюдения.

До каждого шага checkpoint должен фиксировать его точный scope, ожидаемые
target paths и исходные hashes/размеры, разрешённую mutation, proof command,
product-attempt identity и первый незакрытый `REQUIRED` gate. После шага или
timeout дополните checkpoint фактическим состоянием процесса, readback
paths/hashes/размеров, выполненным proof, canonical result/custody и следующим
маленьким незавершённым шагом. Prose без этих проверяемых данных не является
checkpoint evidence.

## Timeout-safe ветвление

После timeout остановитесь и сначала прочитайте состояние прежнего процесса и
фактические target bytes. Пока процесс ещё может писать или владение
неопределённо, ничего не продолжайте.

- Если bytes не изменились и процесс доказанно завершён, продолжайте только
  следующий маленький незавершённый шаг, явно разрешённый исходным order. Не
  переисполняйте уже закрытые шаги и не расширяйте scope.
- Если bytes изменились, никогда не повторяйте product mutation. Выполняйте
  только read-only proof и восстановление result/custody по существующим
  правилам. Отсутствующий или malformed result не разрешает повтор реализации.

Компактная последовательность исполнения:

1. Зафиксировать checkpoint и первый незакрытый `REQUIRED` gate.
2. Выполнить один маленький шаг в пределах эвристического бюджета.
3. Остановить mutation и прочитать процесс, bytes и proof.
4. Зафиксировать checkpoint; при timeout применить ветку unchanged/changed.
5. Продолжить только следующий незавершённый шаг либо восстановить
   proof/result; затем отдельно пройти custody, review и delivery gates.

## Четыре независимых состояния

| Состояние | Что подтверждает | Чего не подтверждает |
| --- | --- | --- |
| Техническое | Фактические target bytes, процесс, readback, hashes и direct proof | Canonical result, review, acceptance или delivery |
| Canonical result | Валидный identity-matching result в назначенной custody | Семантический `ACCEPT`, закрытие review или delivery |
| Review | Применимый независимый review для точных bytes и scope | Canonical custody другого gate или delivery |
| Delivery | Отдельно разрешённые и доказанные merge/install/deploy действия | Корректность непройденных upstream gates |

Совпадение одного состояния не закрывает остальные. Read-only derived state
только показывает evidence: оно не выдаёт order, approval или право на действие.

## Последовательность восстановления

1. Проверьте завершение и владельца прежнего процесса. Если он ещё может писать
   или его состояние неопределённо, остановитесь: concurrent или blind retry
   запрещён.
2. Сверьте реальный target, точные paths/hashes, receipts и canonical result.
   Не восстанавливайте состояние из одной прозы handoff.
3. Разложите требуемые gates по порядку и выберите самый ранний незакрытый
   `REQUIRED` gate. Конфликтующие, неполные или stale artifacts закрывают его как
   `blocked`, пока противоречие не разрешено действующим owner/controller.
4. Если для этого gate всё ещё есть явное разрешение, выпустите отдельный
   bounded successor order только на него. Новый order не наследует более
   широкий scope или approval и не обнуляет product-attempt budget.
5. Не запускайте зависимый gate без валидного upstream proof. Зафиксируйте
   фактическое состояние и следующий gate в существующем handoff.

Здесь нет автоматического retry или перехода к следующему dispatch. Readback
может подтвердить bytes или side effects, но не создаёт отсутствующий executor
result, не меняет его status и не заменяет required independent review.

## Решения по типу сбоя

| Наблюдение | Bounded решение |
| --- | --- |
| Defect в order до исполнения | Исправить order до dispatch в пределах исходного разрешения |
| Временный transport/provider failure до side effects | Выполнить harmless preflight; bounded retry допустим только после проверки side effects и attempt rules |
| Timeout после возможной записи | Остановиться; прочитать процесс и bytes; при unchanged продолжить только следующий маленький незавершённый шаг, при changed не повторять mutation и восстанавливать только proof/result |
| Malformed или отсутствующий result при корректных bytes | Сохранить техническое evidence; применить существующее contract recovery, не повторять реализацию и не изобретать result |
| Environment-only test failure | Зафиксировать discrepancy; direct proof не закрывает обязательный executor/review gate |
| Подтверждённый product defect | Допустима только одна finding-mapped correction с минимальным proof |
| Две product attempts исчерпаны | `blocked`; третья правка запрещена |
| Out-of-scope prerequisite или конфликт evidence | `blocked`; нужен новый scope/approval |

Transport retry не является новой product attempt только когда он не повторяет
product mutation; это устанавливается по evidence, а не по названию сбоя.

## Переиспользование review

Review можно переиспользовать только при одновременном выполнении всех условий:

- manifest полон и связывает каждый применимый полный path с точным hash;
- context и scope не изменились;
- reviewer identity и проверяемая canonical custody подтверждены;
- semantic verdict равен действующему `ACCEPT`;
- unresolved blocking findings отсутствуют.

Одинаковые bytes сами по себе недостаточны. Если любой reviewed byte изменён,
для новых bytes нужен новый применимый independent review. Если hashes равны,
но manifest или custody неполны, формальный `ACCEPT` остаётся `blocked`: следует
закрыть конкретный custody gap, а не объявлять review пройденным. Stale или
конфликтующие review artifacts не выбираются по удобству и fail closed.

## Synthetic A-J exercises

Пилот выполняется отдельно. Эти prompts не являются результатами реальных
executor, review, remote operation или dispatch.

| ID | Synthetic prompt | Ожидаемое решение |
| --- | --- | --- |
| A | Target записан, stream оборван | Не повторять запись; найти первый незакрытый gate |
| B | Result отсутствует, bytes и direct proof корректны | Technical state подтверждён; formal acceptance `blocked` |
| C | Upstream artifact отсутствует | Не запускать downstream gate |
| D | Полный path/hash manifest совпадает; context, scope, identity, custody и `ACCEPT` валидны; blockers нет | Переиспользовать применимый review |
| E | Один reviewed file изменён | Старый review не принимает новые bytes; запросить новый applicable independent review |
| F | Hashes совпадают, canonical review custody неполна | Закрыть конкретный custody gap; не объявлять `ACCEPT` |
| G | Обе разрешённые product attempts исчерпаны | `blocked`; не выполнять третью правку |
| H | Предыдущий процесс ещё может писать | Запретить concurrent retry до доказанного завершения/владения |
| I | Контекст сменился, handoff prose и artifacts расходятся | Восстановить первый незакрытый `REQUIRED` gate из валидных artifacts; конфликт fail closed |
| J | Следующий шаг требует production или paid action | Запросить отдельный требуемый approval; прежний go не универсален |

## Offline pilot checklist

- Пометить fixtures и receipts как synthetic и держать их в свежем immutable
  evidence namespace.
- До упражнения зафиксировать order, scope, paths, hashes, gate order и ожидаемое
  решение; не менять historical artifacts.
- Для A-J записать только решение и evidence mapping; не выполнять описанные
  side effects и не создавать автоматический next dispatch.
- Отдельно отчитать candidate, offline proof, formal acceptance и delivery.
- Перед принятием потребовать установленный review floor и полную custody; этот
  reference сам ничего не принимает и не устанавливает в runtime.
