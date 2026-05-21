# T21: DFG-граф

## Цель
Directly-Follows Graph: построение, фильтрация по частоте, экспорт для Cytoscape.

## Контекст
- `02_DOMAIN_LOGIC.md` раздел "Модуль domain/mining/graph.py"
- `03_API.md` эндпоинт `GET /analytics/dfg`

## DoD
- [ ] Функции `build_dfg(df, activity_col)`, `filter_dfg(dfg, min_edge_freq_pct, top_n_paths)`.
- [ ] Dataclasses `DFGNode`, `DFGEdge`, `DFG`.
- [ ] Эндпоинт возвращает JSON совместимый с Cytoscape elements format.
- [ ] Поддержка self-loops (повтор операции в одном кейсе).
- [ ] Unit-тесты + интеграционный на synthetic_log.

## Реализация — псевдокод в `02_DOMAIN_LOGIC.md`.

Особенность: в эндпоинте format для Cytoscape:
```json
{
  "nodes": [{"data": {"id": "A", "label": "A", "count": 100, "avg_duration_sec": 1200}}],
  "edges": [{"data": {"id": "A->B", "source": "A", "target": "B", "count": 50, "avg_duration_sec": 600}}]
}
```

## Тесты
- `test_dfg_simple_chain` — A→B→C даёт 2 ребра.
- `test_dfg_self_loop` — A→A в одном кейсе.
- `test_filter_dfg_min_frequency`.

## Acceptance
Endpoint /analytics/dfg на synthetic_log возвращает граф, в Cytoscape отрисовывается читаемо.
