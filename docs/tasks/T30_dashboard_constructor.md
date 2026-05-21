# T30: Drag&drop конструктор дашбордов

## Цель
Edit-mode дашборда: добавлять/перемещать/изменять размер/удалять виджеты, настраивать конфиг каждого через модалку.

## Контекст
- `04_UI.md` раздел "10. Дашборд" и "Конструктор виджетов"
- Виджеты из T26-T29

## DoD
- [ ] Кнопка "Редактировать" на странице дашборда переключает в edit-mode.
- [ ] В edit-mode: каждый виджет окружён рамкой с handle для drag и для resize.
- [ ] Используется `react-grid-layout` (отдельная либа) или связка `@dnd-kit` + ручной grid (предпочтительно react-grid-layout — проще).
- [ ] Кнопка "+ Виджет" открывает модалку выбора типа и настройки config.
- [ ] Каждый виджет имеет меню "⋮": Редактировать, Дублировать, Удалить.
- [ ] Кнопка "Сохранить" — PATCH /dashboards/{id} с новым layout и обновлёнными widgets.
- [ ] Кнопка "Отменить" — возврат к state до редактирования.
- [ ] Auto-save опционально (на будущее).

## Реализация

Установить дополнительную либу:
```bash
npm install react-grid-layout
```

```tsx
import { Responsive, WidthProvider } from "react-grid-layout";
const ResponsiveGridLayout = WidthProvider(Responsive);

function DashboardEditMode({ dashboard, widgets, onSave }) {
  const [localWidgets, setLocalWidgets] = useState(widgets);
  const [layout, setLayout] = useState(
    widgets.map(w => ({i: String(w.id), x: w.grid_x, y: w.grid_y, w: w.grid_width, h: w.grid_height}))
  );
  
  return (
    <>
      <ResponsiveGridLayout
        layouts={{lg: layout}}
        cols={{lg: 12, md: 10, sm: 6}}
        rowHeight={80}
        onLayoutChange={(newLayout) => setLayout(newLayout)}
        isDraggable
        isResizable
      >
        {localWidgets.map(w => (
          <div key={w.id}>
            <WidgetWrapper widget={w} editMode onConfigure={...} onDelete={...} />
          </div>
        ))}
      </ResponsiveGridLayout>
      <Button onClick={() => setShowAddModal(true)}>+ Виджет</Button>
      <Button type="primary" onClick={handleSave}>Сохранить</Button>
    </>
  );
}
```

### Модалка выбора + конфигурации виджета
Динамический рендер формы в зависимости от выбранного widget_type. Для каждого типа — свои поля.

## Тесты
Vitest на сохранение layout, изменение config виджета.

## Acceptance
Аналитик в edit-mode перетаскивает виджет, меняет его размер, добавляет новый bar_chart, сохраняет. После reload — изменения видны.
