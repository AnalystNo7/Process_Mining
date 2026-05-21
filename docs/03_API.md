# 03. REST API контракт

## Общие принципы

- **Base URL:** `/api/v1`
- **Формат:** JSON везде, кроме загрузки файлов (`multipart/form-data`)
- **Аутентификация:** JWT Bearer Token в заголовке `Authorization: Bearer <token>`
- **Все timestamps:** ISO 8601 в UTC (`2025-11-07T16:19:56Z`)
- **Пагинация:** `?page=1&page_size=50`, ответ содержит `total`, `items`
- **Ошибки:** стандартный формат с кодом и сообщением

## Структура ответа об ошибке

```json
{
  "error": {
    "code": "ENTITY_NOT_FOUND",
    "message": "Project with id=123 not found",
    "details": {"project_id": 123}
  }
}
```

Стандартные HTTP-коды: 200, 201, 204, 400, 401, 403, 404, 409, 422, 500.

## 1. Аутентификация (`/auth`)

### `POST /auth/login`

Вход по логину/паролю (локальные пользователи) или через LDAP.

**Request:**
```json
{
  "username": "ivanov",
  "password": "secret"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "expires_in": 3600,
  "user": {
    "id": 1,
    "username": "ivanov",
    "full_name": "Иван Иванов",
    "role": "analyst",
    "email": "ivanov@example.com"
  }
}
```

**Errors:** 401 (`INVALID_CREDENTIALS`), 403 (`USER_INACTIVE`).

### `POST /auth/refresh`

Обновление access-токена.

### `POST /auth/logout`

Отзыв refresh-токена.

### `GET /auth/me`

Текущий пользователь.

## 2. Пользователи (`/users`) — только админ

### `GET /users`

Список пользователей с пагинацией.

**Query:** `?page=1&page_size=50&search=ivan&role=analyst&is_active=true`

### `POST /users`

Создать пользователя.

**Request:**
```json
{
  "username": "petrov",
  "full_name": "Пётр Петров",
  "email": "petrov@example.com",
  "password": "initial_password",  // null для LDAP
  "is_ldap": false,
  "role": "analyst"
}
```

### `PATCH /users/{user_id}`

Изменить пользователя (роль, активность, ФИО, пароль).

### `DELETE /users/{user_id}`

Удалить пользователя (мягкое — set is_active=false; жёсткое — только если нет связанных сущностей).

## 3. Проекты (`/projects`)

### `GET /projects`

Список всех проектов (виден всем).

**Query:** `?page=1&page_size=50&search=договор&created_by=1`

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "name": "Согласование договоров",
      "description": "TESSA, выгрузка 2025",
      "created_by": {"id": 1, "username": "ivanov", "full_name": "Иван Иванов"},
      "created_at": "2025-11-01T10:00:00Z",
      "physical_datasets_count": 3,
      "virtual_datasets_count": 5,
      "dashboards_count": 12
    }
  ],
  "total": 7,
  "page": 1,
  "page_size": 50
}
```

### `POST /projects`

Создать проект. Любой аналитик может создавать.

**Request:**
```json
{
  "name": "Согласование договоров",
  "description": "TESSA, выгрузка 2025"
}
```

При создании автоматически:
- Создаётся пустой `role_mapping` (версия 1) на основе глобального шаблона.
- Создаётся пустой набор SLA-правил.
- Создаётся `upload_template` со стандартным маппингом колонок TESSA по умолчанию.

### `GET /projects/{id}`

Детали проекта.

### `PATCH /projects/{id}`

Изменить (только создатель и админ).

### `DELETE /projects/{id}`

Удалить (только создатель и админ). Soft delete с возможностью восстановления админом.

## 4. Физические датасеты (`/projects/{id}/physical-datasets`)

### `POST /projects/{project_id}/physical-datasets/preview`

Загружает файл, парсит первый лист, возвращает превью + список колонок. **Не сохраняет** в БД.

Используется как первый шаг мастера загрузки — аналитик видит, что в файле, и настраивает маппинг.

**Request:** `multipart/form-data`, поле `file`.

**Response:**
```json
{
  "columns": [
    {"name": "doc_id", "sample_values": ["DOC-00001-...", "DOC-00002-..."], "dtype": "string"},
    {"name": "Операция", "sample_values": ["Согласование Юр.управление", ...], "dtype": "string"},
    {"name": "in_progress_datetime", "sample_values": [45677.77, 45678.42], "dtype": "datetime_excel"},
    ...
  ],
  "preview_rows": [
    {"doc_id": "DOC-...", "Операция": "...", ...},
    ...  // первые 10 строк
  ],
  "total_rows": 25606,
  "suggested_mapping": {
    "case_id": "doc_id",
    "activity": "Операция",
    "timestamp_start": "in_progress_datetime",
    "timestamp_end": "completed_datetime",
    "resource": "task_user",
    "department": "task_user_department"
  },
  "preview_token": "tmp_abc123"
}
```

`preview_token` — временный идентификатор файла во временном хранилище (TTL ~1 час). Используется в следующем шаге.

### `POST /projects/{project_id}/physical-datasets`

Создаёт физический датасет на основе preview_token и финального маппинга.

**Request:**
```json
{
  "name": "Договоры Q1-Q3 2025",
  "preview_token": "tmp_abc123",
  "column_mapping": {
    "case_id": "doc_id",
    "activity": "Операция",
    "timestamp_start": "in_progress_datetime",
    "timestamp_end": "completed_datetime",
    "resource": "task_user",
    "department": "task_user_department",
    "additional": {
      "doc_type": "doc_type",
      "doc_number": "doc_number",
      "kr_state": "kr_state",
      "head_user_name": "head_user_name"
    }
  },
  "save_as_template": true
}
```

**Response (202 Accepted):**
```json
{
  "id": 42,
  "status": "validating",
  "task_id": "celery_task_abc"
}
```

Загрузка идёт в фоновой задаче Celery. Прогресс отслеживается через WebSocket или polling.

### `GET /projects/{project_id}/physical-datasets/{id}`

Детали датасета: статистика, health report, статус.

**Response:**
```json
{
  "id": 42,
  "name": "Договоры Q1-Q3 2025",
  "status": "ready",
  "file_name": "tessa_contracts_q1q3.xlsx",
  "file_size_bytes": 5242880,
  "total_events": 25606,
  "total_cases": 1328,
  "unique_activities": 507,
  "period_start": "2025-01-09T11:53:47Z",
  "period_end": "2025-11-07T16:19:56Z",
  "uploaded_by": {"id": 1, "username": "ivanov"},
  "uploaded_at": "2025-11-15T10:00:00Z",
  "health_status": "warning",
  "health_report": {
    "checks": [
      {"name": "cases_count", "severity": "info", "message": "1328 кейсов...", "value": 1328},
      {"name": "rework_pct", "severity": "info", "message": "20.06%", "value": 20.06},
      {"name": "department_field", "severity": "info", "message": "Поле подразделения замаплено", "value": null}
    ]
  },
  "column_mapping": {...}
}
```

### `GET /projects/{project_id}/physical-datasets`

Список физических датасетов проекта.

### `DELETE /projects/{project_id}/physical-datasets/{id}`

Удалить. Если есть связанные виртуальные датасеты — 409 с просьбой удалить их сначала.

### `GET /projects/{project_id}/physical-datasets/{id}/health`

Текущий health report (для повторного отображения).

## 5. Шаблоны загрузки (`/projects/{id}/upload-templates`)

### `GET /projects/{id}/upload-templates`

Список шаблонов проекта.

### `POST /projects/{id}/upload-templates`

Создать новый шаблон.

### `PATCH /projects/{id}/upload-templates/{template_id}`

Изменить шаблон.

### `DELETE /projects/{id}/upload-templates/{template_id}`

## 6. Маппинг ролей (`/projects/{id}/role-mappings`)

### `GET /projects/{id}/role-mappings/current`

Текущая (последняя версия) маппинга ролей проекта.

**Response:**
```json
{
  "id": 5,
  "project_id": 1,
  "version": 3,
  "name": "Основной маппинг",
  "mapping": {
    "Юридическое управление": "Юридическое управление",
    "Договорной отдел": "Договорной отдел",
    "Проект 001": "Инициатор",
    "Проект 002": "Инициатор"
  },
  "roles": [
    "Инициатор",
    "Юридическое управление",
    "Договорной отдел",
    "Финансовый блок"
  ],
  "created_at": "2025-11-01T10:00:00Z",
  "updated_at": "2025-11-15T12:00:00Z"
}
```

### `POST /projects/{id}/role-mappings/suggest`

Авто-предложение маппинга на основе списка подразделений (полученных из физ. датасета).

**Request:**
```json
{
  "departments": ["Юридическое управление", "Проект 001", "Проект 002", ...],
  "physical_dataset_id": 42
}
```

**Response:**
```json
{
  "suggestions": {
    "Юридическое управление": {"role": "Юридическое управление", "matched_pattern": "Юридическое управление"},
    "Проект 001": {"role": "Не размечено", "matched_pattern": null},
    "Проект 002": {"role": "Не размечено", "matched_pattern": null}
  },
  "available_roles": ["Инициатор", "Юридическое управление", "Финансовый блок", ...]
}
```

### `PUT /projects/{id}/role-mappings/current`

Обновить маппинг (создаёт новую версию). Только создатель проекта и админ.

**Request:**
```json
{
  "mapping": {
    "Юридическое управление": "Юридическое управление",
    "Проект 001": "Инициатор",
    "Проект 002": "Инициатор",
    "Проект 003": "Инициатор"
  },
  "roles": ["Инициатор", "Юридическое управление", ...]
}
```

### `GET /projects/{id}/role-mappings/history`

Список всех версий маппинга.

## 7. SLA-справочник (`/projects/{id}/sla-rules`)

### `GET /projects/{id}/sla-rules`

Список SLA-правил проекта.

**Query:** `?active_only=true&role=Юр.управление`

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "project_id": 1,
      "role": "Юридическое управление",
      "operation_pattern": "*",
      "sla_value": 3,
      "sla_unit": "workdays",
      "tolerance_hours": 4,
      "target_compliance_pct": 80.0,
      "effective_from": "2025-01-01",
      "effective_until": null,
      "description": "ЮУ: все согласования — 3 рабочих дня"
    }
  ],
  "total": 25
}
```

### `POST /projects/{id}/sla-rules`

Создать SLA-правило. Только создатель проекта и админ.

### `PATCH /projects/{id}/sla-rules/{rule_id}`

### `DELETE /projects/{id}/sla-rules/{rule_id}`

### `POST /projects/{id}/sla-rules/import`

Массовый импорт SLA-правил из xlsx.

## 8. Виртуальные датасеты (`/projects/{id}/virtual-datasets`)

### `POST /projects/{project_id}/virtual-datasets`

Создать виртуальный датасет.

**Request:**
```json
{
  "name": "Договоры Q1-Q3 2025 (с ролями)",
  "description": "Маппинг от 15.11, без отозванных кейсов",
  "physical_dataset_id": 42,
  "config": {
    "filters": {
      "date_range": {"from": "2025-01-01", "to": "2025-09-30"},
      "attributes_filter": {
        "doc_type": ["Договорный документ"]
      }
    }
  }
}
```

При создании система:
1. Берёт **текущую версию** маппинга ролей проекта и сохраняет snapshot в `role_mapping_snapshot`.
2. Берёт **текущие** SLA-правила проекта и сохраняет snapshot в `sla_rules_snapshot`.
3. Запускает фоновую задачу расчёта `cached_stats`.

**Response (202):**
```json
{
  "id": 100,
  "status": "computing_stats",
  "task_id": "celery_task_xyz"
}
```

### `GET /projects/{project_id}/virtual-datasets/{id}`

Детали виртуального датасета + cached_stats.

**Response:**
```json
{
  "id": 100,
  "name": "Договоры Q1-Q3 2025 (с ролями)",
  "physical_dataset_id": 42,
  "role_mapping_snapshot": {
    "version": 3,
    "mapping": {...},
    "roles": [...]
  },
  "sla_rules_snapshot": [...],
  "config": {...},
  "cached_stats": {
    "total_cases": 1328,
    "total_events": 25606,
    "unique_activities": 507,
    "global_rework_pct": 20.06,
    ...
  },
  "created_by": {"id": 1, "username": "ivanov"},
  "created_at": "2025-11-15T12:00:00Z",
  "is_personal": true
}
```

### `GET /projects/{project_id}/virtual-datasets`

Список виртуальных датасетов проекта (показывает свои + видимые).

### `DELETE /projects/{project_id}/virtual-datasets/{id}`

Удалить. Только создатель и админ.

### `GET /projects/{project_id}/virtual-datasets/{id}/role-breakdown`

Drill-down для роли: какие сырые подразделения в неё входят, сколько событий по каждому.

**Query:** `?role=Инициатор`

**Response:**
```json
{
  "role": "Инициатор",
  "departments": [
    {"name": "Проект 001", "events": 1240, "cases": 95},
    {"name": "Проект 002", "events": 980, "cases": 78}
  ],
  "total_events": 2220,
  "total_cases": 173
}
```

### `GET /projects/{project_id}/virtual-datasets/{id}/activity-breakdown`

Drill-down для роль-операции: из каких сырых operation она составлена.

**Query:** `?activity_with_role=Согласование+Инициатор`

## 9. Именованные срезы (`/virtual-datasets/{id}/slices`)

### `GET /virtual-datasets/{vd_id}/slices`

Список срезов виртуального датасета.

### `POST /virtual-datasets/{vd_id}/slices`

Создать срез.

**Request:**
```json
{
  "name": "Договоры с длительностью >30 дней",
  "description": "Затяжные кейсы для разбора",
  "filters": {
    "case_duration": {"min_days": 30}
  }
}
```

### `PATCH /virtual-datasets/{vd_id}/slices/{slice_id}`

### `DELETE /virtual-datasets/{vd_id}/slices/{slice_id}`

## 10. Аналитика (`/virtual-datasets/{id}/analytics`)

Все эндпоинты принимают `?slice_id=` или `?filters=` (JSON) для фильтрации.

### `GET /virtual-datasets/{vd_id}/analytics/kpi`

Базовый KPI-набор.

**Response:**
```json
{
  "total_cases": 1328,
  "total_events": 25606,
  "unique_activities": 507,
  "unique_resources": 257,
  "unique_departments": 118,
  "period_start": "2025-01-09T11:53:47Z",
  "period_end": "2025-11-07T16:19:56Z",
  "avg_case_duration_seconds": 1850000,
  "avg_case_duration_with_rework_seconds": 1905000,
  "avg_case_duration_without_rework_seconds": 1019000,
  "cases_with_rework": 1145,
  "cases_without_rework": 183,
  "global_rework_pct": 20.06,
  "variability_pct": 89.83,
  "mean_occurrence_pct": 3.04,
  "sla_compliance_pct": 87.5  // null если SLA не настроены
}
```

### `GET /virtual-datasets/{vd_id}/analytics/rework-table`

Воспроизводит ping-pong таблицу.

**Query:** `?activity_level=raw|role` (по сырым именам или с ролями), `?limit=50`

**Response:**
```json
{
  "items": [
    {
      "activity": "Проверка Договорной отдел",
      "total": 1717,
      "repeats": 444,
      "rework_pct": 25.9
    },
    ...
  ],
  "total_operations": 25606,
  "total_repeats": 5136,
  "global_rework_pct": 20.06
}
```

### `GET /virtual-datasets/{vd_id}/analytics/sla-compliance`

Таблица SLA-комплаенса.

**Query:** опционально `?role=`, `?activity=`, `?unit=workdays|calendar_days`

**Response:**
```json
{
  "items": [
    {
      "activity": "Согласование Юридическое управление",
      "role": "Юридическое управление",
      "total_events": 1337,
      "evaluated": 1300,  // для скольких нашлось правило
      "passed": 1124,
      "failed": 176,
      "pass_pct": 86.5,
      "target_pct": 80.0,
      "is_compliant": true,
      "sla_rule": {
        "value": 3,
        "unit": "workdays",
        "tolerance_hours": 4
      }
    },
    ...
  ]
}
```

### `GET /virtual-datasets/{vd_id}/analytics/top-paths`

ТОП-N путей процесса.

**Query:** `?n=5&activity_level=raw|role`

**Response:**
```json
{
  "total_cases": 1328,
  "total_variants": 1194,
  "top_n": 5,
  "covered_cases": 84,
  "coverage_pct": 6.3,
  "variants": [
    {
      "trace": ["Регистрация документа", "Проверка Договорной отдел", ...],
      "n_cases": 29,
      "avg_duration_seconds": 354900,
      "example_case_ids": ["DOC-00001-...", "DOC-00045-...", ...]
    },
    ...
  ]
}
```

### `GET /virtual-datasets/{vd_id}/analytics/dfg`

Directly-Follows Graph.

**Query:** `?activity_level=raw|role&min_edge_frequency_pct=2&top_n_paths=10`

**Response:**
```json
{
  "nodes": [
    {"id": "Проверка Договорной отдел", "count": 1717, "avg_own_duration_sec": 5400}
  ],
  "edges": [
    {
      "from": "Регистрация документа",
      "to": "Проверка Договорной отдел",
      "count": 1200,
      "avg_duration_seconds": 7200
    }
  ],
  "start_activities": {"Регистрация документа": 1100, "Создание": 228},
  "end_activities": {"Подписание": 1300, "Отозвать": 28}
}
```

### `GET /virtual-datasets/{vd_id}/analytics/dfg/bpmn`

Скачать DFG в формате BPMN 2.0 XML.

**Response:** `Content-Type: application/xml`, файл `process.bpmn`.

### `GET /virtual-datasets/{vd_id}/analytics/monthly-dynamics`

Динамика по месяцам.

**Query:** `?activity=` (опционально, для drill-down одной операции)

**Response:**
```json
{
  "items": [
    {
      "month": "2025-01",
      "n_events": 1124,
      "n_cases": 119,
      "avg_sojourn_seconds": 13800
    },
    ...
  ]
}
```

### `GET /virtual-datasets/{vd_id}/analytics/resources`

Анализ исполнителей.

**Query:** `?limit=50&sort_by=n_events&order=desc`

**Response:**
```json
{
  "items": [
    {
      "resource": "Иванов И.И.",
      "n_cases": 145,
      "n_events": 312,
      "avg_own_duration_seconds": 3600,
      "n_unique_activities": 4
    },
    ...
  ]
}
```

### `GET /virtual-datasets/{vd_id}/analytics/cases`

Список кейсов (для таблицы drill-down).

**Query:** обширные фильтры + пагинация

### `GET /virtual-datasets/{vd_id}/analytics/case/{case_id}`

Полные события одного кейса (трасса) для drill-down.

**Response:**
```json
{
  "case_id": "DOC-00001-...",
  "attributes": {
    "doc_type": "Договорный документ",
    "doc_number": "DOC-NUM-00001",
    "head_user_name": "Иванов И.И."
  },
  "events": [
    {
      "activity": "Регистрация документа",
      "timestamp_start": "2025-01-15T08:00:00Z",
      "timestamp_end": "2025-01-15T08:05:00Z",
      "resource": "Петров П.П.",
      "department": "Договорной отдел",
      "role": "Договорной отдел",
      "sojourn_seconds": 300,
      "is_repeat": false
    },
    ...
  ],
  "total_duration_seconds": 1850000,
  "has_rework": true,
  "n_events": 18
}
```

## 11. Дашборды (`/virtual-datasets/{id}/dashboards`)

### `GET /virtual-datasets/{vd_id}/dashboards`

Список дашбордов виртуального датасета (мои + общие).

### `POST /virtual-datasets/{vd_id}/dashboards`

Создать дашборд.

**Request:**
```json
{
  "name": "SLA-комплаенс по подразделениям",
  "description": "Контроль исполнения SLA",
  "global_filters": {
    "date_range": {"from": "2025-07-01", "to": "2025-09-30"}
  },
  "applied_slice_id": null,
  "layout": [
    {"widget_id": 1, "x": 0, "y": 0, "w": 4, "h": 2},
    {"widget_id": 2, "x": 4, "y": 0, "w": 8, "h": 4}
  ]
}
```

### `GET /dashboards/{id}`

Детали дашборда + список виджетов.

### `PATCH /dashboards/{id}`

### `DELETE /dashboards/{id}`

### `POST /dashboards/{id}/duplicate`

Создать копию дашборда (для шаринга шаблона).

### `GET /dashboards/{id}/export/png`

Экспорт всего дашборда в PNG.

**Response:** `Content-Type: image/png`.

Серверный рендеринг через headless Chromium (Playwright) или фронтовый через `html-to-image` + endpoint для приёма.

## 12. Виджеты (`/dashboards/{id}/widgets`)

### `POST /dashboards/{id}/widgets`

Добавить виджет на дашборд.

**Request:**
```json
{
  "widget_type": "kpi_card",
  "title": "Всего кейсов",
  "config": {
    "metric": "total_cases",
    "format": "number",
    "icon": "FileTextOutlined"
  },
  "local_filters": null,
  "use_global_filters": true,
  "grid_x": 0,
  "grid_y": 0,
  "grid_width": 3,
  "grid_height": 2
}
```

### `GET /widgets/{id}/data`

Получить **рассчитанные данные** для отрисовки виджета.

Этот эндпоинт инкапсулирует всю логику: применяет фильтры (global + local), вызывает соответствующий алгоритм из `domain/mining/`, форматирует результат под нужды виджета.

**Response (формат зависит от widget_type):**

```json
// kpi_card
{
  "value": 1328,
  "formatted": "1 328",
  "delta": null
}

// bar_chart
{
  "data": [
    {"x": "Январь", "y": 1124},
    {"x": "Февраль", "y": 2020},
    ...
  ],
  "x_label": "Месяц",
  "y_label": "Количество операций"
}

// rework_table
{
  "rows": [...]
}
```

### `PATCH /widgets/{id}`

### `DELETE /widgets/{id}`

### `POST /widgets/{id}/export/png`

Экспорт отдельного виджета в PNG.

## 13. Аннотации (`/virtual-datasets/{id}/annotations`)

### `GET /virtual-datasets/{vd_id}/annotations`

Список аннотаций виртуального датасета.

### `POST /virtual-datasets/{vd_id}/annotations`

**Request:**
```json
{
  "target_type": "node",
  "target_id": "Согласование Юридическое управление",
  "text": "Узкое место: рост длительности с июня",
  "color": "#ff4444"
}
```

### `PATCH /annotations/{id}`

### `DELETE /annotations/{id}`

## 14. Глобальные справочники (`/admin/global-role-templates`) — только админ

### `GET /admin/global-role-templates`

### `POST /admin/global-role-templates`

### `PATCH /admin/global-role-templates/{id}`

### `DELETE /admin/global-role-templates/{id}`

## 15. Audit log (`/admin/audit-log`) — только админ

### `GET /admin/audit-log`

**Query:** `?user_id=&action=&entity_type=&from=&to=&page=&page_size=`

**Response:**
```json
{
  "items": [
    {
      "id": 1001,
      "user": {"id": 1, "username": "ivanov"},
      "action": "project.create",
      "entity_type": "project",
      "entity_id": 42,
      "metadata": {"name": "..."},
      "ip_address": "192.168.1.10",
      "created_at": "..."
    }
  ],
  "total": 5421
}
```

## 16. Системные эндпоинты

### `GET /health`

Health check. Возвращает 200 если БД доступна, 503 если нет.

### `GET /version`

Версия API.

### `GET /tasks/{task_id}`

Статус фоновой задачи Celery (для UI-индикатора прогресса).

**Response:**
```json
{
  "task_id": "abc123",
  "status": "PENDING|STARTED|SUCCESS|FAILURE",
  "progress": 65,  // 0-100, опционально
  "result": null,  // при SUCCESS — данные результата
  "error": null    // при FAILURE — текст ошибки
}
```

## Принципы реализации в FastAPI

1. **Роутеры по доменам.** Каждый раздел API — отдельный файл в `app/api/v1/`: `auth.py`, `projects.py`, `physical_datasets.py`, `virtual_datasets.py`, `analytics.py`, `dashboards.py`, etc.
2. **Pydantic-схемы — отдельно от моделей БД.** Все request/response — Pydantic-схемы в `app/schemas/`.
3. **Dependency injection для авторизации.** `Depends(get_current_user)`, `Depends(require_admin)`, `Depends(require_project_owner_or_admin)`.
4. **Pagination — единая схема.** `class PaginatedResponse[T]` с `items: list[T]`, `total: int`, `page: int`, `page_size: int`.
5. **OpenAPI — автоматически.** FastAPI генерирует swagger из Pydantic-схем. Это уже документация для разработчика frontend.
6. **Ошибки — через исключения.** `EntityNotFoundError`, `ValidationError`, `PermissionDeniedError` → обработчики возвращают стандартный JSON.
7. **Фоновые задачи — через Celery.** Долгие операции (парсинг xlsx, расчёт cached_stats, экспорт PNG) — в фоне с возвратом task_id.

## Что читать дальше

- UI, использующий эти эндпоинты → `04_UI.md`
- Тестирование эндпоинтов → `06_TESTING.md`
