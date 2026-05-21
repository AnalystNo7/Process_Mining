# T32: Drill-down по операции/роли/кейсу

## Цель
Возможность "провалиться" вглубь данных при клике на узел графа, операцию таблицы или кейс.

## Контекст
- `04_UI.md` раздел "11. Drill-down кейса", "9. Виртуальный датасет: Explore"
- `03_API.md` эндпоинты `analytics/case/{case_id}`, `virtual-datasets/{id}/role-breakdown`, `activity-breakdown`

## DoD
- [ ] Backend: эндпоинты для drill-down реализованы (см. T15).
- [ ] Кейс drill-down: модальное окно/drawer с подробной трассой кейса:
  - Метаданные (атрибуты)
  - Хронологическая таблица операций (с длительностями и пометками "повтор"/"SLA нарушен")
  - Кнопка "Открыть похожие кейсы" → возврат к таблице с фильтром
- [ ] Роль drill-down: модалка "Какие подразделения входят в роль X" со списком и кол-вом событий.
- [ ] Операция drill-down: модалка "Из каких сырых operation составлена X" + список кейсов, где встретилась.
- [ ] Из process_graph (T29) клик на узел → один из drill-down путей в зависимости от уровня.

## Реализация

```tsx
// Drill-down состояние в Zustand
const useDrillDownStore = create((set) => ({
  active: null,  // {type: 'case'|'role'|'activity', id: string}
  open: (type, id) => set({active: {type, id}}),
  close: () => set({active: null}),
}));

// Компонент Drill-down rendererа
function DrillDownDrawer() {
  const {active, close} = useDrillDownStore();
  if (!active) return null;
  
  if (active.type === 'case') return <CaseDrillDown caseId={active.id} onClose={close} />;
  if (active.type === 'role') return <RoleDrillDown role={active.id} onClose={close} />;
  if (active.type === 'activity') return <ActivityDrillDown activity={active.id} onClose={close} />;
}

// В виджете process_graph cytoscape handler:
cy.on('tap', 'node', (e) => {
  const nodeId = e.target.data('id');
  useDrillDownStore.getState().open('activity', nodeId);
});
```

## Тесты
- Backend integration: `test_case_drill_down_returns_full_trace`.
- `test_role_breakdown_shows_departments`.

## Acceptance
Клик на узел графа открывает drawer с подробностями. Клик на кейс — drawer с трассой.
