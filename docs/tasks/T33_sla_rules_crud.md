# T33: CRUD SLA-правил

## Цель
Управление справочником SLA: создание, редактирование, версионирование правил. UI-форма + admin-импорт из Excel.

## Контекст
- `01_DATA_MODEL.md` таблица `core.sla_rules`.
- `02_DOMAIN_LOGIC.md` раздел "SLA-комплаенс".
- `03_API.md` раздел "SLA rules".
- `04_UI.md` раздел "SLA editor".

## DoD
- [ ] CRUD-эндпоинты:
  - `GET /api/projects/{id}/sla-rules` — список правил проекта.
  - `POST /api/projects/{id}/sla-rules` — создание.
  - `PUT /api/sla-rules/{id}` — редактирование (создаёт новую запись с инкрементом версии, старая → effective_to = now).
  - `DELETE /api/sla-rules/{id}` — мягкое удаление (effective_to = now).
- [ ] Права: только владелец проекта + admin.
- [ ] React-страница `/projects/{id}/sla-rules` — таблица правил с фильтрами.
- [ ] Модал создания/редактирования с валидацией.
- [ ] Bulk-импорт правил из Excel (опциональный, через простую таблицу).

## Структура SLA-правила
Соответствует `01_DATA_MODEL.md`:
```python
class SlaRule:
    id: int
    project_id: int
    role: str                # "Юридическое управление", "*" для всех ролей
    operation_pattern: str   # "Согласование Юридическое управление" или "*"
    sla_value: int           # числовое значение
    sla_unit: str            # "workdays" | "calendar_days" | "workhours" | "hours"
    tolerance_hours: int     # 4 (норматив просрочки в рабочих часах)
    target_compliance_pct: float  # 90.0
    effective_from: date
    effective_to: date | None  # NULL = действует сейчас
    created_by: int
    created_at: datetime
```

## Поиск подходящего правила
```python
def find_matching_rule(rules: list[SlaRule], operation: str, role: str, event_date: date) -> SlaRule | None:
    """Найти SLA-правило, наиболее точно подходящее операции/роли/дате.
    Приоритет совпадений (от точного к общему):
    1. role == "Юр.управление", operation_pattern == "Согл. Юр.управление"
    2. role == "Юр.управление", operation_pattern == "*"
    3. role == "*",             operation_pattern == "Согл. Юр.управление"
    4. role == "*",             operation_pattern == "*"
    
    Среди подходящих по effective_from <= date <= effective_to.
    """
    candidates = [r for r in rules if 
                  r.effective_from <= event_date and 
                  (r.effective_to is None or event_date < r.effective_to) and
                  (r.role == role or r.role == "*") and
                  (r.operation_pattern == operation or r.operation_pattern == "*")]
    
    # Сортируем по специфичности
    def specificity(r):
        s = 0
        if r.role != "*": s += 2
        if r.operation_pattern != "*": s += 1
        return s
    candidates.sort(key=specificity, reverse=True)
    return candidates[0] if candidates else None
```

## UI: страница `/projects/{id}/sla-rules`
- Таблица: Роль | Операция | Норматив | Толеранс | Цель | Период действия | [Edit][Delete]
- Поверх — фильтры: показать только действующие сейчас / показать все, поиск по роли.
- Кнопка "+ Новое правило" — открывает форму.
- Кнопка "Импорт из Excel" — открывает диалог загрузки.

## Форма SLA-правила
```
┌────────────────────────────────────────────────────────────┐
│  Создать SLA-правило                                       │
├────────────────────────────────────────────────────────────┤
│  Роль:               [Юридическое управление ▾]            │
│                      Или [Все роли (*)] ☐                  │
│                                                             │
│  Операция:           [Согласование Юр.управление ▾]        │
│                      Или [Все операции (*)] ☐              │
│                                                             │
│  Норматив:           [3] [Рабочие дни ▾]                   │
│                                                             │
│  Толеранс просрочки: [4] часа (по умолчанию)               │
│                                                             │
│  Целевой % компл.:   [90.0] %                              │
│                                                             │
│  Действует с:        [01.01.2025]                          │
│                                                             │
│  [Отмена]                              [Создать правило]   │
└────────────────────────────────────────────────────────────┘
```

## Шаблон Excel-импорта
| role | operation_pattern | sla_value | sla_unit | tolerance_hours | target_compliance_pct | effective_from |
|---|---|---|---|---|---|---|
| Юридическое управление | * | 3 | workdays | 4 | 90.0 | 2025-01-01 |
| Закупки | * | 3 | workdays | 4 | 90.0 | 2025-01-01 |
| ... | | | | | | |

## Тесты
- `test_create_sla_rule`.
- `test_edit_creates_new_record_with_versioning` — после PUT старая запись имеет effective_to = now, новая запись имеет инкрементированную версию.
- `test_find_matching_rule_specificity` — для (operation, role) с обоими специфичными правилами выбирается оно, не "*".
- `test_excel_import_creates_rules`.

## Acceptance
Аналитик создаёт 11 правил SLA (по 1 на каждую операцию из PDF Газпрома). После создания все правила видны в таблице. Импорт из Excel создаёт 11 правил одной операцией.
