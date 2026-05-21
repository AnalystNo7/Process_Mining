# T38: PNG-экспорт виджетов и дашбордов

## Цель
Сохранение отдельных виджетов или целого дашборда в PNG для вставки в презентации. Без серверного рендера, всё через `html-to-image` на клиенте.

## Контекст
- `04_UI.md` раздел "Export".

## DoD
- [ ] Кнопка "💾 PNG" на каждом виджете (видна при hover).
- [ ] Кнопка "💾 Экспорт дашборда в PNG" в верхней панели страницы дашборда.
- [ ] Используется библиотека `html-to-image` (npm: `html-to-image`).
- [ ] PNG сохраняется на клиенте через FileSaver.js (или `URL.createObjectURL`).
- [ ] Имя файла: `{dashboard_name}_{YYYY-MM-DD}.png` для дашборда, `{widget_title}_{YYYY-MM-DD}.png` для виджета.
- [ ] Качество: pixelRatio 2 (для retina), белый фон.

## Реализация
```typescript
// src/lib/png-export.ts
import * as htmlToImage from 'html-to-image';

export async function exportElementToPng(element: HTMLElement, filename: string) {
  const dataUrl = await htmlToImage.toPng(element, {
    pixelRatio: 2,
    backgroundColor: '#ffffff',
    cacheBust: true,
  });
  const link = document.createElement('a');
  link.download = filename;
  link.href = dataUrl;
  link.click();
}

export function exportWidgetToPng(widgetId: number, title: string) {
  const el = document.querySelector(`[data-widget-id="${widgetId}"]`);
  if (!el) return;
  const safe = title.replace(/[^a-z0-9а-яё-_]/gi, '_');
  const date = new Date().toISOString().slice(0, 10);
  return exportElementToPng(el as HTMLElement, `${safe}_${date}.png`);
}

export function exportDashboardToPng(dashboardId: number, dashboardTitle: string) {
  const el = document.querySelector(`[data-dashboard-id="${dashboardId}"]`);
  if (!el) return;
  const safe = dashboardTitle.replace(/[^a-z0-9а-яё-_]/gi, '_');
  const date = new Date().toISOString().slice(0, 10);
  return exportElementToPng(el as HTMLElement, `${safe}_${date}.png`);
}
```

## UI: кнопка на виджете
```tsx
const WidgetCard = ({ widget, children }) => {
  return (
    <div data-widget-id={widget.id} className="widget-card">
      <div className="widget-toolbar">
        <Tooltip title="Экспорт в PNG">
          <Button icon={<DownloadOutlined />} size="small" type="text"
                  onClick={() => exportWidgetToPng(widget.id, widget.config.title)} />
        </Tooltip>
      </div>
      {children}
    </div>
  );
};
```

## UI: кнопка экспорта дашборда
```tsx
<Space>
  <Button icon={<DownloadOutlined />} onClick={() => exportDashboardToPng(dashboard.id, dashboard.title)}>
    Экспорт PNG
  </Button>
</Space>
```

## Ограничения
- Графики Plotly должны быть полностью отрендерены до экспорта. Если виджет загружается лениво — кнопка disabled.
- Cytoscape-граф рендерится через Canvas, у которого работает html-to-image (нужно проверить, что включена `useCORS: false`).
- Аннотации (tooltip над узлами при hover) на PNG не попадают. Подсветка "узкое место" — попадает.

## Тесты
- Manual smoke: щёлкнуть PNG-кнопку на KPI-карточке → файл скачался → открывается → совпадает с виджетом на экране.
- Тоже для bar_chart, для rework_table, для process_graph, для dashboard.
- Никаких unit-тестов (это чисто браузерная функциональность).

## Acceptance
Аналитик нажимает "Экспорт PNG" на дашборде "Обзор" → файл `Обзор_2025-11-15.png` сохраняется → файл открывается → видна вся страница дашборда с виджетами.
