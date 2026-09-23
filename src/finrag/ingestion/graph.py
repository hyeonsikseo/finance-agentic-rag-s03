# -*- coding: utf-8 -*-
"""인제스천 그래프.

LangGraph 는 스케줄러가 아니라 제어흐름 + 체크포인트다. 여기서 얻는 것은 두 가지다.
  1. "어떤 문서가 어느 경로로 갔는가"가 상태로 남는다(리포트가 공짜로 나온다).
  2. thread_id 를 파일 해시로 잡으면 같은 문서를 다시 넣어도 건너뛴다(idempotent).

    classify → parse → gate ─┬─ pass ───────────────→ chunk → END
                             ├─ reparse → (pass|ocr|repair)
                             ├─ ocr ────→ (chunk|dead_letter)
                             └─ fail ───→ dead_letter
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from langgraph.graph import END, StateGraph

from . import nodes as N


def build_ingest_graph(checkpointer=None):
    g = StateGraph(N.IngestState)
    for name in ("classify", "parse", "gate", "reparse", "ocr", "llm_repair", "chunk", "dead_letter"):
        g.add_node(name, getattr(N, name))

    # ── 실습 3: 여기를 채우세요 ──────────────────────────────
    # 노드 8개는 위에서 등록했다. 엣지만 연결하면 된다.
    #   classify → parse → gate ─┬ pass    → chunk → END
    #                            ├ reparse → reparse ─┬ pass   → chunk
    #                            │                    ├ ocr    → ocr
    #                            │                    └ repair → llm_repair
    #                            ├ ocr     → ocr ─────┬ chunk  → chunk
    #                            │                    └ fail   → dead_letter
    #                            └ fail    → dead_letter → END
    #   llm_repair 다음은 lambda s: s["route"] 로 chunk / dead_letter
    # 시작점    : g.set_entry_point("classify")
    # 보통 엣지 : g.add_edge(출발, 도착)
    # 조건부 엣지: g.add_conditional_edges(출발, 라우터, {라우터가 돌려주는 값: 도착})
    # 라우터는 nodes.py 맨 아래의 route_after_gate · route_after_reparse · route_after_ocr
    raise NotImplementedError("실습 3: build_ingest_graph 의 엣지를 연결하세요 (이 줄은 지운다)")

    return g.compile(checkpointer=checkpointer)


def thread_id_for(path: Path) -> str:
    """파일 내용 해시. 같은 파일이면 같은 thread 라 체크포인트가 재실행을 건너뛴다."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]
