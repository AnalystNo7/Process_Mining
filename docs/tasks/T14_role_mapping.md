# T14: Маппинг ролей

## Цель
CRUD маппинга подразделений → ролей. Авто-предложение по глобальному шаблону. Версионирование.

## Контекст
- `02_DOMAIN_LOGIC.md` раздел "Модуль domain/mining/role_mapping.py"
- `03_API.md` раздел "6. Маппинг ролей"
- `04_UI.md` раздел "7. Редактор маппинга ролей"
- `01_DATA_MODEL.md` таблицы `core.role_mappings`, `core.global_role_templates`

## DoD
- [ ] Функция `suggest_role_mapping(departments, global_templates) -> dict`.
- [ ] Функция `apply_role_mapping(df, mapping) -> df` (добавляет колонки `role` и `activity_with_role`).
- [ ] Эндпоинты: `GET /role-mappings/current`, `POST /role-mappings/suggest`, `PUT /role-mappings/current`, `GET /role-mappings/history`.
- [ ] При создании проекта (T09) создаётся пустой role_mapping версия 1.
- [ ] При PUT — создаётся новая версия (старые не удаляются).
- [ ] При новом физическом датасете в проекте — новые незнакомые подразделения автоматически добавляются в mapping с ролью "Не размечено", создаётся новая версия.
- [ ] Seed данных: 10 базовых ролей из `02_DOMAIN_LOGIC.md` (DEFAULT_ROLE_TEMPLATES) в таблицу `core.global_role_templates` через миграцию или CLI-команду.
- [ ] UI: страница `/projects/:id/role-mapping` с таблицей подразделений, dropdown ролей, кнопкой "Применить авто-разметку".

## Реализация
См. полный псевдокод в `02_DOMAIN_LOGIC.md`.

## Тесты
- `test_suggest_role_mapping_matches_patterns` — "Юридическое управление" → "Юридическое управление".
- `test_suggest_role_mapping_unknown_returns_unmapped` — "Проект X" → "Не размечено".
- `test_apply_role_mapping_renames_activity` — "Согл. Проект X" → "Согл. Инициатор" при mapping "Проект X→Инициатор".
- `test_apply_role_mapping_keeps_when_role_equals_dept` — "Согл. Юр.управление" остаётся "Согл. Юр.управление".
- `test_put_creates_new_version`.

## Acceptance
На странице маппинга после загрузки synthetic_log.xlsx видно 118 подразделений, большинство Проектов автоматически → "Не размечено", основные подразделения (Юр., Финанс., и т.д.) → корректные роли. Аналитик массово назначает "все Не размечено → Инициатор", сохраняет версию 2.
