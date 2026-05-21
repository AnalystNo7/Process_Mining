# T29: Виджеты process_graph и top_paths_graph (Cytoscape)

## Цель
Интерактивные графы процессов с использованием Cytoscape.js.

## Контекст
- `04_UI.md` виджеты "process_graph", "top_paths_graph"
- `T21_dfg_graph.md`

## DoD
- [ ] Backend: использует функции из T21 (`build_dfg`, `filter_dfg`).
- [ ] Frontend компонент `ProcessGraphWidget` с Cytoscape + dagre layout.
- [ ] Self-loops визуально подсвечиваются (другой цвет/толщина).
- [ ] Узлы кликабельны → emit для drill-down.
- [ ] Тултипы при наведении: количество событий, ср.длительность.
- [ ] Кнопки zoom in/out, fit, reset.
- [ ] top_paths_graph дополнительно показывает рядом таблицу с топ-N трасс (n_cases, avg_duration).

## Реализация
```tsx
import CytoscapeComponent from "react-cytoscapejs";
import dagre from "cytoscape-dagre";
import cytoscape from "cytoscape";
cytoscape.use(dagre);

export function ProcessGraphWidget({ widgetId }) {
  const { data } = useQuery({...});
  const elements = useMemo(() => [
    ...data.nodes.map(n => ({data: {id: n.id, label: n.label, count: n.count}})),
    ...data.edges.map(e => ({data: {id: `${e.source}->${e.target}`, source: e.source, target: e.target, label: String(e.count)}})),
  ], [data]);
  
  const stylesheet = [
    { selector: "node", style: {
      "label": "data(label)",
      "background-color": "#5470c6",
      "color": "white",
      "text-valign": "center",
      "width": "label", "height": "label",
      "padding": "8px",
      "shape": "round-rectangle"}},
    { selector: "edge", style: {
      "curve-style": "bezier",
      "target-arrow-shape": "triangle",
      "label": "data(label)",
      "width": 2}},
    { selector: "edge[source = target]", style: {  // self-loop
      "line-color": "#ee6666", "target-arrow-color": "#ee6666",
      "width": 3}},
  ];
  
  return (
    <CytoscapeComponent
      elements={elements}
      stylesheet={stylesheet}
      layout={{name: "dagre", rankDir: "TB"}}
      style={{ width: "100%", height: 500 }}
      cy={(cy) => {
        cy.on("tap", "node", (e) => {
          const node = e.target.data();
          // emit drill-down event
        });
      }}
    />
  );
}
```

## Acceptance
process_graph на synthetic_log отображается читаемо, видны рёбра между основными операциями, self-loops для повторов выделены красным.
