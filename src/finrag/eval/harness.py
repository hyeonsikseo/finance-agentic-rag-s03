# -*- coding: utf-8 -*-
"""평가 하네스.

3회차부터 8회차까지 같은 하네스로 잰다. 파이프라인만 갈아 끼운다. 그래야
baseline/hybrid/agentic 세 숫자가 같은 자로 잰 값이 된다.
"""
from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from ..settings import get_settings
from .metrics import aggregate, mrr, recall_at_k

KS = (1, 3, 5, 10)


def load_golden() -> tuple[list[dict], dict[str, list[str]]]:
    s = get_settings()
    seed = [json.loads(l) for l in (s.golden_dir / "seed_golden.jsonl").open(encoding="utf-8") if l.strip()]
    gold_path = s.golden_dir / "gold_chunk_ids.json"
    gold = json.loads(gold_path.read_text(encoding="utf-8")) if gold_path.exists() else {}
    return seed, gold


def run(pipeline: Callable[[str], dict], name: str, *, limit: int | None = None,
        golden: list[dict] | None = None, verbose: bool = False) -> dict:
    """pipeline(question) → {"chunk_ids": [...], "answer": str|None, "abstained": bool, ...}"""
    seed, gold_ids = load_golden()
    if golden:
        seed = golden
    if limit:
        seed = seed[:limit]

    rows: list[dict] = []
    for item in seed:
        qid = item["id"]
        t0 = time.perf_counter()
        out = pipeline(item["question"])
        latency = (time.perf_counter() - t0) * 1000
        retrieved = out.get("chunk_ids", [])
        gold = gold_ids.get(qid, [])
        row = {
            "id": qid, "type": item.get("type", "?"), "answerable": item.get("answerable", True),
            "n_gold": len(gold), "n_retrieved": len(retrieved),
            "mrr": mrr(retrieved, gold), "latency_ms": round(latency, 1),
            "top_chunk": retrieved[0] if retrieved else None,
            "answered": (not out["abstained"]) if "abstained" in out else None,
            "answer": out.get("answer"),
        }
        for k in KS:
            row[f"recall@{k}"] = recall_at_k(retrieved, gold, k)
        rows.append(row)
        if verbose:
            print(f"  {qid} {item.get('type','')[:6]:8} R@5={row['recall@5']:.0f} "
                  f"MRR={row['mrr']:.2f} {latency:6.0f}ms")

    from ..llm import get_llm, is_fake
    fake = is_fake(get_llm("answer"))
    result = {"pipeline": name,
              "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "n": len(rows), "llm": "fake" if fake else get_settings().llm_model_main,
              **aggregate(rows, KS), "rows": rows}
    if fake:
        # 가짜 모델은 항상 "근거가 충분하다"고 판정한다. 그래서 거절이 일어나지 않고
        # 답변률 100% · 오거절률 0% · 미답변 정확도 0% 가 나온다. 이 숫자를 성능으로
        # 읽으면 안 되므로 결과 파일에 경고를 박아 둔다.
        result["warning"] = ("LLM 키가 없어 가짜 모델로 실행했습니다. 검색 지표"
                             "(Recall·MRR)는 유효하지만 답변률·오거절률·미답변 정확도는 "
                             "의미가 없습니다.")
    return result


def save(result: dict, path: Path | None = None) -> Path:
    s = get_settings()
    path = path or s.results_dir / f"{result['pipeline']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def print_summary(result: dict) -> None:
    o = result["overall"]
    if result.get("warning"):
        print(f"\n  [주의] {result['warning']}")
    print(f"\n[{result['pipeline']}] {result['n']}문항  "
          f"Recall@1 {o['recall@1']:.1%}  @5 {o['recall@5']:.1%}  @10 {o['recall@10']:.1%}  "
          f"MRR {o['mrr']:.3f}  평균 {o.get('latency_ms_avg', 0):.0f}ms")
    print(f"{'유형':16}{'n':>3} {'R@1':>6} {'R@5':>6} {'R@10':>6} {'MRR':>6}")
    for t, b in result["by_type"].items():
        print(f"{t:16}{b['n']:>3} {b['recall@1']:>6.1%} {b['recall@5']:>6.1%} "
              f"{b['recall@10']:>6.1%} {b['mrr']:>6.3f}")
