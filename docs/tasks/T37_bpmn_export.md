# T37: BPMN-экспорт DFG

## Цель
Экспорт текущего DFG-графа (с учётом фильтров) в BPMN 2.0 XML-файл. Аналитик скачивает .bpmn, открывает в Camunda Modeler / bpmn.io / Visio для визуального сравнения с эталонной моделью.

## Контекст
- T21 — DFG-граф.
- `02_DOMAIN_LOGIC.md` раздел "BPMN export".
- BPMN 2.0 schema: https://www.omg.org/spec/BPMN/2.0/

## DoD
- [ ] Модуль `app/domain/mining/bpmn_export.py`.
- [ ] Функция `dfg_to_bpmn(dfg: DFG, process_name: str) -> str` — возвращает XML.
- [ ] Endpoint `GET /api/virtual-datasets/{id}/analytics/bpmn?filters=...` — отдаёт `.bpmn` файл.
- [ ] UI кнопка "Экспорт BPMN" на странице DFG-графа.
- [ ] Тест: сгенерированный файл валиден по XSD и открывается в bpmn.io.

## Стратегия преобразования
DFG → BPMN это упрощённое преобразование (не реальный process mining BPMN discovery типа Inductive Miner). Маппинг:

- Каждый узел DFG → `<bpmn:task>` с уникальным `id` и `name`.
- Стартовый узел (если есть в DFG как special) → `<bpmn:startEvent>`.
- Конечный узел → `<bpmn:endEvent>`.
- Каждое ребро DFG → `<bpmn:sequenceFlow>`.
- Для self-loop (узел сам на себя) — не отдельный sequenceFlow, а помечаем тип задачи как loop через `<bpmn:standardLoopCharacteristics>`.
- Layout (координаты x, y) — простой каскад сверху вниз слева направо, через `<bpmndi:BPMNDiagram>`.

## Шаблон XML
```xml
<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
                  xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
                  xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
                  id="Definitions_1"
                  targetNamespace="http://process-mining/bpmn">
  <bpmn:process id="Process_1" name="{process_name}" isExecutable="false">
    <bpmn:startEvent id="StartEvent_1" />
    <bpmn:task id="Task_a1b2c3" name="Согласование Юр.управление" />
    <bpmn:task id="Task_d4e5f6" name="Согласование Закупки" 
               isForCompensation="false">
      <bpmn:standardLoopCharacteristics />
    </bpmn:task>
    <bpmn:endEvent id="EndEvent_1" />
    <bpmn:sequenceFlow id="Flow_1" sourceRef="StartEvent_1" targetRef="Task_a1b2c3" />
    <bpmn:sequenceFlow id="Flow_2" sourceRef="Task_a1b2c3" targetRef="Task_d4e5f6" />
    <bpmn:sequenceFlow id="Flow_3" sourceRef="Task_d4e5f6" targetRef="EndEvent_1" />
  </bpmn:process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_1">
    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_1">
      <bpmndi:BPMNShape id="Shape_StartEvent" bpmnElement="StartEvent_1">
        <dc:Bounds x="100" y="100" width="36" height="36" />
      </bpmndi:BPMNShape>
      ... (координаты всех узлов и edges)
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn:definitions>
```

## Алгоритм размещения (layout)
Используем простой топологический sort с слоями:
1. Слой 0: startEvent.
2. Слой N: узлы, все предки которых в слоях 0..N-1.
3. Координаты: x = layer * 200, y = position_in_layer * 100.

Для self-loops размещаем "крючок" над узлом.

## Реализация
```python
def dfg_to_bpmn(dfg: DFG, process_name: str = "Process") -> str:
    """Конвертирует DFG в BPMN 2.0 XML.
    DFG — это объект с .nodes (list[str]) и .edges (list[tuple[str, str, int]])."""
    
    # 1. Создаём id для каждого узла
    nodes_id = {node: f"Task_{uuid4().hex[:6]}" for node in dfg.nodes}
    
    # 2. Определяем стартовые и конечные узлы (нет входящих / нет исходящих)
    incoming = {n: 0 for n in dfg.nodes}
    outgoing = {n: 0 for n in dfg.nodes}
    for src, tgt, _ in dfg.edges:
        if src != tgt:  # не учитываем self-loops
            incoming[tgt] += 1
            outgoing[src] += 1
    start_nodes = [n for n in dfg.nodes if incoming[n] == 0]
    end_nodes = [n for n in dfg.nodes if outgoing[n] == 0]
    
    # 3. Определяем узлы с self-loop
    loop_nodes = set(src for src, tgt, _ in dfg.edges if src == tgt)
    
    # 4. Layout — топологический sort
    layers = topological_layout(dfg.nodes, [(s,t) for s,t,_ in dfg.edges if s != t])
    
    # 5. Генерация XML (через xml.etree.ElementTree)
    root = ET.Element("bpmn:definitions", {
        "xmlns:bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
        "xmlns:bpmndi": "http://www.omg.org/spec/BPMN/20100524/DI",
        "xmlns:dc": "http://www.omg.org/spec/DD/20100524/DC",
        "id": "Definitions_1",
        "targetNamespace": "http://process-mining/bpmn",
    })
    process = ET.SubElement(root, "bpmn:process", 
        id="Process_1", name=process_name, isExecutable="false")
    
    # StartEvent
    ET.SubElement(process, "bpmn:startEvent", id="StartEvent_1")
    # EndEvent
    ET.SubElement(process, "bpmn:endEvent", id="EndEvent_1")
    
    # Tasks
    for node, task_id in nodes_id.items():
        attrs = {"id": task_id, "name": node}
        task_el = ET.SubElement(process, "bpmn:task", attrs)
        if node in loop_nodes:
            ET.SubElement(task_el, "bpmn:standardLoopCharacteristics")
    
    # SequenceFlows
    flow_idx = 1
    # От start к каждому стартовому узлу
    for n in start_nodes:
        ET.SubElement(process, "bpmn:sequenceFlow", 
            id=f"Flow_{flow_idx}", sourceRef="StartEvent_1", targetRef=nodes_id[n])
        flow_idx += 1
    # Все рёбра DFG (кроме self-loops, они уже как loop characteristics)
    for src, tgt, freq in dfg.edges:
        if src == tgt: continue
        ET.SubElement(process, "bpmn:sequenceFlow",
            id=f"Flow_{flow_idx}", sourceRef=nodes_id[src], targetRef=nodes_id[tgt])
        flow_idx += 1
    # От каждого конечного узла к end
    for n in end_nodes:
        ET.SubElement(process, "bpmn:sequenceFlow",
            id=f"Flow_{flow_idx}", sourceRef=nodes_id[n], targetRef="EndEvent_1")
        flow_idx += 1
    
    # Diagram (упрощённо)
    diag = ET.SubElement(root, "bpmndi:BPMNDiagram", id="BPMNDiagram_1")
    plane = ET.SubElement(diag, "bpmndi:BPMNPlane", id="BPMNPlane_1", bpmnElement="Process_1")
    _add_shape(plane, "StartEvent_1", 100, 100, 36, 36)
    for layer_idx, layer_nodes in enumerate(layers):
        for pos_idx, n in enumerate(layer_nodes):
            x = 200 + layer_idx * 180
            y = 80 + pos_idx * 120
            _add_shape(plane, nodes_id[n], x, y, 100, 80)
    
    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")
```

## Endpoint
```python
@router.get("/virtual-datasets/{id}/analytics/bpmn")
async def export_bpmn(id: int, filters: str | None = None):
    vd = await get_vd(id)
    df = await load_vd(vd, parse_filters(filters))
    dfg = build_dfg(df, max_nodes=20)
    xml = dfg_to_bpmn(dfg, process_name=vd.project.name)
    return Response(
        content=xml,
        media_type="application/bpmn+xml",
        headers={"Content-Disposition": f'attachment; filename="{vd.name}.bpmn"'},
    )
```

## Тесты
- `test_dfg_to_bpmn_produces_valid_xml`.
- `test_bpmn_validates_against_xsd` — есть локальная копия `BPMN20.xsd`, валидация через `lxml.etree.XMLSchema`.
- `test_self_loop_creates_loop_characteristics`.
- `test_start_and_end_events_present`.
- Manual smoke: открыть сгенерированный файл в https://demo.bpmn.io/ — отображается корректно.

## Acceptance
Кнопка "Экспорт BPMN" в графе DFG → файл скачивается → файл открывается в bpmn.io без ошибок → отображает все узлы с правильными именами.
