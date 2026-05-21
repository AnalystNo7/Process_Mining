import lxml.etree as LET

from app.domain.mining.bpmn_export import dfg_to_bpmn
from app.domain.mining.graph import DFG, DFGEdge, DFGNode

_NS = {
    "bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
    "bpmndi": "http://www.omg.org/spec/BPMN/20100524/DI",
}


def _sample_dfg() -> DFG:
    return DFG(
        nodes=[
            DFGNode("Старт", 10, 1.0),
            DFGNode("Согласование", 8, 2.0),
            DFGNode("Конец", 5, 3.0),
        ],
        edges=[
            DFGEdge("Старт", "Согласование", 8, 60.0),
            DFGEdge("Согласование", "Согласование", 3, 30.0),  # self-loop
            DFGEdge("Согласование", "Конец", 5, 90.0),
        ],
        start_activities={"Старт": 10},
        end_activities={"Конец": 5},
    )


def _parse(xml: str) -> LET._Element:
    return LET.fromstring(xml.encode("utf-8"))


def test_dfg_to_bpmn_produces_valid_xml() -> None:
    root = _parse(dfg_to_bpmn(_sample_dfg(), "Тест"))
    assert root.tag.endswith("definitions")
    assert root.find(".//bpmn:process", _NS) is not None
    assert root.find(".//bpmndi:BPMNDiagram", _NS) is not None


def test_tasks_match_dfg_nodes() -> None:
    root = _parse(dfg_to_bpmn(_sample_dfg(), "Тест"))
    tasks = root.findall(".//bpmn:task", _NS)
    assert {t.get("name") for t in tasks} == {"Старт", "Согласование", "Конец"}


def test_start_and_end_events_present() -> None:
    root = _parse(dfg_to_bpmn(_sample_dfg(), "Тест"))
    assert root.find(".//bpmn:startEvent", _NS) is not None
    assert root.find(".//bpmn:endEvent", _NS) is not None
    # Старт→Согласование→Конец + рёбра к start/end событиям.
    assert len(root.findall(".//bpmn:sequenceFlow", _NS)) >= 3


def test_self_loop_creates_loop_characteristics() -> None:
    root = _parse(dfg_to_bpmn(_sample_dfg(), "Тест"))
    tasks = {t.get("name"): t for t in root.findall(".//bpmn:task", _NS)}
    looped = tasks["Согласование"]
    assert looped.find("bpmn:standardLoopCharacteristics", _NS) is not None
    plain = tasks["Старт"]
    assert plain.find("bpmn:standardLoopCharacteristics", _NS) is None


def test_empty_dfg_still_has_start_and_end() -> None:
    root = _parse(dfg_to_bpmn(DFG(), "Пусто"))
    assert root.find(".//bpmn:startEvent", _NS) is not None
    assert root.find(".//bpmn:endEvent", _NS) is not None
    assert root.findall(".//bpmn:task", _NS) == []
