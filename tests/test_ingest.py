# -*- coding: utf-8 -*-
"""3회차 자기 확인.

    make test        (Windows: .venv\\Scripts\\python -m pytest -q)

세 묶음입니다. 앞의 둘(gate, build_ingest_graph)은 저장소에 들어 있는 법령 파일
(data/bundled/)만으로 돌고, 마지막 묶음은 내려받은 문서와 `make ingest` 결과가 있어야
돕니다(없으면 건너뜁니다). 채우기 전에는 앞의 두 묶음이 NotImplementedError 로
실패합니다. 그게 정상입니다.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

XML = ROOT / "data" / "bundled" / "law_fcpa.xml"          # 금융소비자보호법. 글자만 있는 문서
HWP = ROOT / "data" / "bundled" / "law_silson_std.hwp"    # 지원하지 않는 형식


def _through_parse(doc_id: str, path: Path) -> dict:
    """classify → parse 까지 돌린 상태. gate 에 넣을 입력이다."""
    from finrag.ingestion.nodes import classify, parse
    state = {"doc_id": doc_id, "path": str(path)}
    state.update(classify(state))
    state.update(parse(state))
    return state


# ── 실습 2 · nodes.gate ────────────────────────────────────────────────
def test_gate_fails_unsupported_format_without_running_the_validator():
    from finrag.ingestion.nodes import gate
    out = gate(_through_parse("law_silson_std_hwp", HWP))
    assert out["route"] == "fail", "HWP 는 게이트를 거치지 않고 바로 fail 이다"
    assert out["report"]["verdict"] == "fail"
    assert any("지원하지 않는" in r for r in out["report"]["reasons"]), \
        "이유에 '지원하지 않는 형식' 이 있어야 사람 검토 큐에서 왜 왔는지 안다"


def test_gate_passes_a_clean_text_document():
    from finrag.ingestion.nodes import gate
    out = gate(_through_parse("law_fcpa_xml", XML))
    assert out["route"] == "pass"
    assert out["report"]["usable_pages"] >= 1


def test_gate_route_equals_report_verdict():
    """라우터(route_after_gate)는 state["route"] 만 본다. 리포트의 판정과 어긋나면 안 된다."""
    from finrag.ingestion.nodes import gate
    out = gate(_through_parse("law_fcpa_xml", XML))
    assert out["route"] == out["report"]["verdict"]


def test_gate_report_has_the_fields_the_next_nodes_read():
    """reparse 는 bad_pages 를, ocr 은 usable_pages 를, dead_letter 는 reasons 를 읽는다."""
    from finrag.ingestion.nodes import gate
    rep = gate(_through_parse("law_fcpa_xml", XML))["report"]
    for key in ("doc_id", "verdict", "reasons", "bad_pages", "usable_pages"):
        assert key in rep, f"report 에 {key} 가 없다 (DocReport.to_dict() 를 쓰세요)"


# ── 실습 3 · graph.build_ingest_graph ──────────────────────────────────
def _graph():
    from finrag.ingestion.graph import build_ingest_graph
    return build_ingest_graph().get_graph()


def _edges() -> set[tuple[str, str]]:
    return {(e.source, e.target) for e in _graph().edges}


def test_graph_has_the_eight_nodes():
    nodes = set(_graph().nodes) - {"__start__", "__end__"}
    assert nodes == {"classify", "parse", "gate", "reparse", "ocr", "llm_repair", "chunk", "dead_letter"}


def test_graph_starts_at_classify_then_parse_then_gate():
    e = _edges()
    assert ("__start__", "classify") in e, "set_entry_point('classify')"
    assert ("classify", "parse") in e and ("parse", "gate") in e


def test_gate_branches_four_ways():
    e = _edges()
    for target in ("chunk", "reparse", "ocr", "dead_letter"):
        assert ("gate", target) in e, f"gate → {target} 가 없다"
    assert all(x.conditional for x in _graph().edges if x.source == "gate"), \
        "gate 다음은 조건부 엣지(add_conditional_edges)여야 한다"


def test_reparse_ocr_and_repair_branches():
    e = _edges()
    assert {("reparse", "chunk"), ("reparse", "ocr"), ("reparse", "llm_repair")} <= e
    assert {("ocr", "chunk"), ("ocr", "dead_letter")} <= e
    assert {("llm_repair", "chunk"), ("llm_repair", "dead_letter")} <= e


def test_graph_ends_after_chunk_and_dead_letter():
    e = _edges()
    assert ("chunk", "__end__") in e and ("dead_letter", "__end__") in e, \
        "END 로 가는 엣지가 없어도 컴파일은 되지만 그래프에 끝이 없는 노드가 남는다"


# ── 끝까지 통과시켜 본다 (bundled 파일만으로) ──────────────────────────
def test_text_document_goes_through_to_chunks():
    from finrag.ingestion.graph import build_ingest_graph
    out = build_ingest_graph().invoke({"doc_id": "law_fcpa_xml", "path": str(XML)})
    assert out["route"] == "done"
    assert len(out["chunks"]) > 10
    assert all(c["doc_id"] == "law_fcpa_xml" for c in out["chunks"])
    assert out["chunks"][0]["meta"]["validation"] == "pass"


def test_unsupported_document_lands_in_dead_letter():
    from finrag.ingestion.graph import build_ingest_graph
    out = build_ingest_graph().invoke({"doc_id": "law_silson_std_hwp", "path": str(HWP)})
    assert out["route"] == "failed"
    assert out["chunks"] == []
    assert any("지원하지 않는" in w for w in out["warnings"]), "조용히 버리지 않고 이유를 남긴다"


# ── 코퍼스가 있어야 도는 것 ──────────────────────────────────────────
def _raw(name: str) -> Path:
    p = ROOT / "data" / "raw" / name
    if not p.exists():
        pytest.skip(f"코퍼스 없음: {name} (make download)")
    return p


def test_scan_document_takes_the_ocr_branch():
    from finrag.ingestion.graph import build_ingest_graph
    p = _raw("knia_3500_scan.pdf")
    out = build_ingest_graph().invoke({"doc_id": "knia_3500_scan", "path": str(p)})
    assert out["report"]["verdict"] == "ocr", "이미지 전용 문서는 ocr 갈래로 가야 한다"
    # OCR 캐시가 있으면 청크가 나오고(done), 없으면 사람 검토 큐(failed)다. 둘 다 맞다.
    assert out["route"] in ("done", "failed")


# ── make ingest 뒤에 도는 것 ──────────────────────────────────────────
def _report() -> dict:
    p = ROOT / "data" / "ingest_report.json"
    if not p.exists():
        pytest.skip("리포트 없음 (make ingest)")
    return json.loads(p.read_text(encoding="utf-8"))


def test_report_routes_add_up_to_documents():
    rep = _report()
    assert sum(rep["routes"].values()) == rep["documents"], "샌 문서가 있다"


def test_report_shows_at_least_three_verdicts():
    rep = _report()
    assert len([k for k, v in rep["verdicts"].items() if v]) >= 3, \
        "pass 만 나왔다면 게이트가 분기하지 않은 것이다"
