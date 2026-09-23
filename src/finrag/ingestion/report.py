# -*- coding: utf-8 -*-
"""인제스천 리포트. 경로별 통계와 실패 목록을 한 화면으로 낸다."""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def build_report(results: list[dict]) -> dict:
    routes = Counter(r["route"] for r in results)
    total_chunks = sum(len(r.get("chunks", [])) for r in results)
    failed = [{"doc_id": r["doc_id"], "reasons": r.get("report", {}).get("reasons", []),
               "warnings": r.get("warnings", [])} for r in results if r["route"] == "failed"]
    repaired = [r["doc_id"] for r in results if r.get("llm_repaired")]
    synthetic = [r["doc_id"] for r in results if r.get("meta", {}).get("synthetic_degraded")]
    parsers = Counter(r.get("parser", "?") for r in results)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "documents": len(results),
        "chunks": total_chunks,
        "routes": dict(routes),
        "parsers": dict(parsers),
        "verdicts": dict(Counter(r.get("report", {}).get("verdict", "?") for r in results)),
        "llm_repaired": repaired,
        "synthetic_degraded": synthetic,
        "failed": failed,
    }


def print_report(rep: dict) -> None:
    print(f"\n문서 {rep['documents']}건 → 청크 {rep['chunks']:,}개")
    print("  경로:", ", ".join(f"{k} {v}" for k, v in sorted(rep["routes"].items())))
    print("  게이트:", ", ".join(f"{k} {v}" for k, v in sorted(rep["verdicts"].items())))
    print("  파서:", ", ".join(f"{k} {v}" for k, v in sorted(rep["parsers"].items())))
    if rep["synthetic_degraded"]:
        print(f"  [주의] 열화 재현본 {len(rep['synthetic_degraded'])}건 포함 — 지표를 실데이터와 분리해 보고할 것")
    if rep["llm_repaired"]:
        print(f"  LLM 복구: {rep['llm_repaired']}")
    if rep["failed"]:
        print(f"  사람 검토 큐 {len(rep['failed'])}건:")
        for f in rep["failed"]:
            print(f"    - {f['doc_id']}: {'; '.join(f['reasons'][:2]) or '사유 없음'}")


def save_report(rep: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
