"""Экспорт DFG в BPMN 2.0 XML (см. T37).

Упрощённое преобразование (не Inductive Miner): каждый узел DFG → bpmn:task,
каждое ребро → bpmn:sequenceFlow, self-loop → standardLoopCharacteristics.

Примечание по реализации: псевдокод T37 предполагает DFG с полями nodes как
list[str] и edges как list[tuple]. Фактическая модель DFG (app.domain.mining.graph)
использует типизированные DFGNode/DFGEdge — экспорт адаптирован под неё."""

import xml.etree.ElementTree as ET
from uuid import uuid4

from app.domain.mining.graph import DFG

_BPMN = "http://www.omg.org/spec/BPMN/20100524/MODEL"
_BPMNDI = "http://www.omg.org/spec/BPMN/20100524/DI"
_DC = "http://www.omg.org/spec/DD/20100524/DC"
_DI = "http://www.omg.org/spec/DD/20100524/DI"

_START_ID = "StartEvent_1"
_END_ID = "EndEvent_1"
_EVENT_SIZE = 36
_TASK_W, _TASK_H = 120, 80
_LAYER_X, _ROW_Y = 200, 130


def _layout_layers(nodes: list[str], edges: list[tuple[str, str]]) -> list[list[str]]:
    """Раскладывает узлы по слоям топологической сортировки. Графы process
    mining содержат циклы, поэтому при отсутствии узлов без входящих рёбер
    берётся узел с наименьшим числом непокрытых предков."""
    incoming = {n: 0 for n in nodes}
    adjacency: dict[str, list[str]] = {n: [] for n in nodes}
    for src, tgt in edges:
        incoming[tgt] += 1
        adjacency[src].append(tgt)

    remaining = dict(incoming)
    placed: set[str] = set()
    layers: list[list[str]] = []
    while len(placed) < len(nodes):
        layer = [n for n in nodes if n not in placed and remaining[n] <= 0]
        if not layer:
            stuck = min(
                (n for n in nodes if n not in placed), key=lambda n: remaining[n]
            )
            layer = [stuck]
        for node in layer:
            placed.add(node)
            for tgt in adjacency[node]:
                remaining[tgt] -= 1
        layers.append(layer)
    return layers


def _add_shape(
    plane: ET.Element, element_id: str, x: int, y: int, width: int, height: int
) -> None:
    shape = ET.SubElement(
        plane, f"{{{_BPMNDI}}}BPMNShape", {"bpmnElement": element_id}
    )
    shape.set("id", f"Shape_{element_id}")
    ET.SubElement(
        shape,
        f"{{{_DC}}}Bounds",
        {"x": str(x), "y": str(y), "width": str(width), "height": str(height)},
    )


def _add_edge(
    plane: ET.Element,
    flow_id: str,
    source: tuple[int, int],
    target: tuple[int, int],
) -> None:
    edge = ET.SubElement(
        plane, f"{{{_BPMNDI}}}BPMNEdge", {"bpmnElement": flow_id}
    )
    edge.set("id", f"Edge_{flow_id}")
    for x, y in (source, target):
        ET.SubElement(edge, f"{{{_DI}}}waypoint", {"x": str(x), "y": str(y)})


def dfg_to_bpmn(dfg: DFG, process_name: str = "Process") -> str:
    """Конвертирует DFG в строку BPMN 2.0 XML."""
    ET.register_namespace("bpmn", _BPMN)
    ET.register_namespace("bpmndi", _BPMNDI)
    ET.register_namespace("dc", _DC)
    ET.register_namespace("di", _DI)

    node_names = [node.activity for node in dfg.nodes]
    task_ids = {name: f"Task_{uuid4().hex[:8]}" for name in node_names}
    loop_nodes = {
        e.from_activity for e in dfg.edges if e.from_activity == e.to_activity
    }
    flow_edges = [
        (e.from_activity, e.to_activity)
        for e in dfg.edges
        if e.from_activity != e.to_activity
    ]

    node_set = set(node_names)
    start_nodes = [n for n in dfg.start_activities if n in node_set]
    end_nodes = [n for n in dfg.end_activities if n in node_set]
    if node_names and not start_nodes:
        start_nodes = [node_names[0]]
    if node_names and not end_nodes:
        end_nodes = [node_names[-1]]

    root = ET.Element(
        f"{{{_BPMN}}}definitions",
        {"id": "Definitions_1", "targetNamespace": "http://process-mining/bpmn"},
    )
    process = ET.SubElement(
        root,
        f"{{{_BPMN}}}process",
        {"id": "Process_1", "name": process_name, "isExecutable": "false"},
    )
    ET.SubElement(process, f"{{{_BPMN}}}startEvent", {"id": _START_ID})
    for name in node_names:
        task = ET.SubElement(
            process, f"{{{_BPMN}}}task", {"id": task_ids[name], "name": name}
        )
        if name in loop_nodes:
            ET.SubElement(task, f"{{{_BPMN}}}standardLoopCharacteristics")
    ET.SubElement(process, f"{{{_BPMN}}}endEvent", {"id": _END_ID})

    flows: list[tuple[str, str, str]] = []
    flow_idx = 1

    def _flow(source_ref: str, target_ref: str) -> None:
        nonlocal flow_idx
        flow_id = f"Flow_{flow_idx}"
        ET.SubElement(
            process,
            f"{{{_BPMN}}}sequenceFlow",
            {"id": flow_id, "sourceRef": source_ref, "targetRef": target_ref},
        )
        flows.append((flow_id, source_ref, target_ref))
        flow_idx += 1

    if node_names:
        for name in start_nodes:
            _flow(_START_ID, task_ids[name])
        for src, tgt in flow_edges:
            _flow(task_ids[src], task_ids[tgt])
        for name in end_nodes:
            _flow(task_ids[name], _END_ID)
    else:
        _flow(_START_ID, _END_ID)

    # Раскладка: StartEvent — слой 0, задачи — топологические слои, EndEvent — последний.
    layers = _layout_layers(node_names, flow_edges)
    coords: dict[str, tuple[int, int, int, int]] = {}
    start_y = 40
    coords[_START_ID] = (
        60,
        start_y + (_TASK_H - _EVENT_SIZE) // 2,
        _EVENT_SIZE,
        _EVENT_SIZE,
    )
    for layer_idx, layer in enumerate(layers):
        for row_idx, name in enumerate(layer):
            coords[task_ids[name]] = (
                160 + layer_idx * _LAYER_X,
                start_y + row_idx * _ROW_Y,
                _TASK_W,
                _TASK_H,
            )
    end_x = 160 + len(layers) * _LAYER_X
    coords[_END_ID] = (end_x, start_y + (_TASK_H - _EVENT_SIZE) // 2, _EVENT_SIZE, _EVENT_SIZE)

    diagram = ET.SubElement(
        root, f"{{{_BPMNDI}}}BPMNDiagram", {"id": "BPMNDiagram_1"}
    )
    plane = ET.SubElement(
        diagram,
        f"{{{_BPMNDI}}}BPMNPlane",
        {"id": "BPMNPlane_1", "bpmnElement": "Process_1"},
    )
    for element_id, (x, y, width, height) in coords.items():
        _add_shape(plane, element_id, x, y, width, height)

    def _center(element_id: str) -> tuple[int, int]:
        x, y, width, height = coords[element_id]
        return x + width // 2, y + height // 2

    for flow_id, source_ref, target_ref in flows:
        _add_edge(plane, flow_id, _center(source_ref), _center(target_ref))

    return ET.tostring(root, encoding="unicode", xml_declaration=True)
