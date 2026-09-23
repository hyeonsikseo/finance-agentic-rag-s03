# -*- coding: utf-8 -*-
"""검색·답변 지표.

작은 셋(40문항)에서는 전체 평균이 서사를 만들지 못한다. 유형별로 쪼개야
"조항번호형이 Hybrid 로 얼마나 올랐는가" 같은 말을 할 수 있다.
"""
from __future__ import annotations

from collections import defaultdict


def recall_at_k(retrieved: list[str], gold: list[str], k: int) -> float:
    """gold 청크가 상위 k 안에 하나라도 있으면 1. 근거는 여러 개일 수 있다."""
    return 1.0 if set(retrieved[:k]) & set(gold) else 0.0


def mrr(retrieved: list[str], gold: list[str]) -> float:
    for rank, cid in enumerate(retrieved, start=1):
        if cid in set(gold):
            return 1.0 / rank
    return 0.0


def precision_at_k(retrieved: list[str], gold: list[str], k: int) -> float:
    if not k:
        return 0.0
    return len(set(retrieved[:k]) & set(gold)) / k


def aggregate(rows: list[dict], ks: tuple[int, ...] = (1, 3, 5, 10)) -> dict:
    """행 하나 = 문항 하나. type 별 분해표까지 만든다."""
    def block(subset: list[dict]) -> dict:
        n = len(subset) or 1
        out = {f"recall@{k}": round(sum(r[f"recall@{k}"] for r in subset) / n, 4) for k in ks}
        out["mrr"] = round(sum(r["mrr"] for r in subset) / n, 4)
        out["n"] = len(subset)
        answered = [r for r in subset if r.get("answered") is not None]
        if answered:
            out["answer_rate"] = round(sum(1 for r in answered if r["answered"]) / len(answered), 4)
            # 오거절률: 답할 근거가 있는데 거절한 비율
            can = [r for r in answered if r.get("answerable", True)]
            if can:
                out["false_refusal_rate"] = round(sum(1 for r in can if not r["answered"]) / len(can), 4)
            # 미답변 정확도: 거절해야 할 문항을 실제로 거절했는가
            cannot = [r for r in answered if not r.get("answerable", True)]
            if cannot:
                out["abstain_accuracy"] = round(sum(1 for r in cannot if not r["answered"]) / len(cannot), 4)
        lat = [r["latency_ms"] for r in subset if r.get("latency_ms")]
        if lat:
            out["latency_ms_avg"] = round(sum(lat) / len(lat), 1)
            out["latency_ms_p95"] = round(sorted(lat)[max(int(len(lat) * 0.95) - 1, 0)], 1)
        return out

    by_type: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_type[r.get("type", "?")].append(r)
    return {"overall": block(rows),
            "by_type": {t: block(rs) for t, rs in sorted(by_type.items())}}


def compare(tables: dict[str, dict], metric: str = "recall@5") -> list[dict]:
    """3단계 비교표. 파이프라인별 유형 분해를 한 표로 세운다."""
    types = sorted({t for tb in tables.values() for t in tb["by_type"]})
    rows = []
    for t in types:
        row = {"type": t}
        for name, tb in tables.items():
            row[name] = tb["by_type"].get(t, {}).get(metric)
        rows.append(row)
    row = {"type": "전체"}
    for name, tb in tables.items():
        row[name] = tb["overall"].get(metric)
    rows.append(row)
    return rows
