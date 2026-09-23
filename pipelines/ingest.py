#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""인제스천 실행. 코퍼스 전체를 그래프에 통과시키고 청크와 리포트를 남긴다.

    python pipelines/ingest.py                 # 전체
    python pipelines/ingest.py --only nh_jangbyeong_2026   # 결과는 *_sample 파일에 따로 (전체 실행 결과를 덮어쓰지 않는다)
    python pipelines/ingest.py --no-checkpoint # 체크포인트 없이 다시
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from finrag.observability import callbacks, flush   # noqa: E402
from finrag.ingestion.graph import build_ingest_graph, thread_id_for   # noqa: E402
from finrag.ingestion.report import build_report, print_report, save_report  # noqa: E402
from finrag.parsing.metadata import load_documents                     # noqa: E402
from finrag.settings import get_settings                               # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--no-checkpoint", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    s = get_settings()
    docs = load_documents()
    targets = [d for d in docs.values() if not args.only or d.doc_id in set(args.only)]

    checkpointer = None
    if not args.no_checkpoint:
        from langgraph.checkpoint.memory import InMemorySaver
        checkpointer = InMemorySaver()
    graph = build_ingest_graph(checkpointer)

    s.chunks_dir.mkdir(parents=True, exist_ok=True)
    results, all_chunks, skipped = [], [], 0
    for i, meta in enumerate(targets, 1):
        path = s.root / meta.path
        if not path.exists():
            continue
        cfg = {"configurable": {"thread_id": thread_id_for(path)}} if checkpointer else {}
        # Langfuse 키가 있으면 노드별 실행이 그대로 트레이스가 된다. 없으면 빈 목록이라
        # 아무 일도 일어나지 않는다(5회차 전까지는 키가 없는 것이 정상이다).
        if callbacks():
            cfg["callbacks"] = callbacks()
        out = None
        if checkpointer:
            # 체크포인터는 "중단된 실행을 이어서" 하는 장치이지, 끝난 실행을 자동으로
            # 건너뛰지 않는다. 같은 파일을 다시 넣으면 그대로 다시 돈다. 그래서
            # 완료된 상태가 있으면 여기서 직접 재사용한다. thread_id 가 파일 해시라
            # 파일이 1바이트라도 바뀌면 다른 thread 가 되어 자연히 다시 처리된다.
            snap = graph.get_state(cfg)
            if snap and snap.values.get("route") in ("done", "failed"):
                out = snap.values
                skipped += 1
        if out is None:
            out = graph.invoke({"doc_id": meta.doc_id, "path": str(path)}, cfg)
        results.append(out)
        chunks = out.get("chunks", [])
        all_chunks += chunks
        if not args.quiet:
            mark = {"done": " ", "failed": "!"}.get(out["route"], "?")
            print(f"[{i:2}/{len(targets)}]{mark}{meta.doc_id:32} {out.get('report',{}).get('verdict','?'):8} "
                  f"{out.get('parser',''):11} 청크 {len(chunks):>4}")

    # --only 로 몇 건만 돌린 결과가 전체 실행 결과(chunks.jsonl, ingest_report.json)를 덮어쓰면
    # 색인이 몇 건짜리가 되고 check-s03 이 "문서 6/51건" 으로 떨어진다. 따로 저장한다.
    sample = bool(args.only)
    out_path = s.chunks_dir / ("chunks_sample.jsonl" if sample else "chunks.jsonl")
    with out_path.open("w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    rep = build_report(results)
    rep["skipped_by_checkpoint"] = skipped
    print_report(rep)
    if skipped:
        print(f"  체크포인트로 건너뜀: {skipped}건")
    report_path = s.data / ("ingest_report_sample.json" if sample else "ingest_report.json")
    save_report(rep, report_path)
    # Langfuse 는 배치로 보낸다. 짧은 스크립트는 다 보내기 전에 프로세스가 끝나서
    # 트레이스가 안 올라간 것처럼 보인다. 끝에 한 번 비운다.
    flush(note=f"ingest {len(targets)}건")
    print(f"\n청크 → {out_path.relative_to(s.root)}  리포트 → {report_path.relative_to(s.root)}")
    if sample:
        print("  (--only 결과는 전체 실행 결과를 덮어쓰지 않도록 _sample 파일에 따로 저장했습니다)")
    # 사람 검토 큐에 문서가 있어도 실행은 성공이다. 실패를 보이게 만드는 것이 목적이지
    # 실패를 오류로 만드는 것이 아니다. 종료 코드 1 을 돌려주면 make 가 "Error 1" 을 찍어서
    # 학생이 자기 코드가 틀린 줄 안다.
    return 0


if __name__ == "__main__":
    sys.exit(main())
