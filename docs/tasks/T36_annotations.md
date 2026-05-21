# T36: Аннотации

## Цель
Произвольный текст-комментарий на узлах графа, рёбрах графа, конкретных кейсах и временных диапазонах. Видны всем аналитикам проекта. Сохраняются на уровне виртуального датасета.

## Контекст
- `01_DATA_MODEL.md` таблица `core.annotations`.
- `03_API.md` раздел "Annotations".
- `04_UI.md` раздел "Annotations".

## DoD
- [ ] CRUD-эндпоинты:
  - `GET /api/virtual-datasets/{id}/annotations` — список с фильтрами `target_type`.
  - `POST /api/virtual-datasets/{id}/annotations` — создание.
  - `PUT /api/annotations/{id}` — редактирование текста.
  - `DELETE /api/annotations/{id}` — удаление (только автор + admin).
- [ ] Поддерживаемые `target_type`: `node`, `edge`, `case`, `time_range`.
- [ ] UI:
  - Граф процесса (Cytoscape): иконка-маркер 📍 на узле/ребре с аннотацией. Hover показывает текст.
  - Таблица кейсов: иконка-маркер в колонке.
  - Графики динамики: подсветка диапазона + иконка над ним.
- [ ] Любой аналитик может создать, редактировать может только автор (+ admin).
- [ ] Видны всем аналитикам проекта.

## Структура `target` для разных типов
**target_type=node:**
```json
{"activity": "Согласование Юр.управление"}
```

**target_type=edge:**
```json
{"from": "Согласование Юр.управление", "to": "Доп.согл. Юр.управление"}
```

**target_type=case:**
```json
{"case_id": "DOC-12345-abc"}
```

**target_type=time_range:**
```json
{"start_date": "2025-04-01", "end_date": "2025-04-30", "context": "operation:Задача УКЗ"}
```
(`context` — опциональный селектор, для какого виджета/операции применяется)

## API контракт
`POST /api/virtual-datasets/{id}/annotations`:
```json
{
  "target_type": "node",
  "target": {"activity": "Согласование Юр.управление"},
  "text": "Узкое место — основная причина задержек по договорам типа X"
}
```

Ответ:
```json
{
  "id": 42,
  "virtual_dataset_id": 1,
  "target_type": "node",
  "target": {"activity": "Согласование Юр.управление"},
  "text": "Узкое место...",
  "author_id": 5,
  "author_name": "Иванов И.И.",
  "created_at": "2025-11-15T10:00:00Z",
  "updated_at": "2025-11-15T10:00:00Z"
}
```

## UI Cytoscape — иконка на узле
```javascript
// При рендере узла: проверяем есть ли аннотация
const nodeStyle = (activity) => {
  const hasAnnotation = annotations.some(a => 
    a.target_type === 'node' && a.target.activity === activity
  );
  return {
    'background-image': hasAnnotation ? 'url(/pin.svg)' : undefined,
    'background-position': 'top right',
    'background-width': 16,
    'background-height': 16,
  };
};

// Tooltip при наведении на узел с аннотацией
cy.on('mouseover', 'node', (e) => {
  const node = e.target;
  const ann = annotations.find(a => 
    a.target_type === 'node' && a.target.activity === node.id()
  );
  if (ann) showTooltip(node.position(), ann.text + `\n— ${ann.author_name}`);
});
```

## UI диалог создания аннотации
```
┌────────────────────────────────────────────────────────────┐
│  Добавить пометку для: Согласование Юр.управление          │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  Текст пометки:                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Узкое место — основная причина задержек по         │   │
│  │ договорам типа X. Обсуждалось с владельцем          │   │
│  │ процесса 12 ноября.                                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  [Отмена]                                  [Сохранить]      │
└────────────────────────────────────────────────────────────┘
```

## Тесты
- `test_create_annotation_node`.
- `test_create_annotation_edge`.
- `test_create_annotation_case`.
- `test_create_annotation_time_range`.
- `test_other_user_cannot_edit_annotation`.
- `test_admin_can_edit_annotation`.
- `test_list_annotations_filter_by_type`.

## Acceptance
Аналитик А создаёт 3 аннотации: на узле графа, на ребре и на кейсе. Аналитик B заходит в этот виртуальный датасет → видит все 3 аннотации с автором "А". Аналитик B не может редактировать. Admin может.
