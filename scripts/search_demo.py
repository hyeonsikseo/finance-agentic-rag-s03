#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""벡터 검색을 손으로 한 번 해 본다. 필터를 붙이면 결과가 어떻게 바뀌는지 본다.

    python scripts/search_demo.py "중도해지이율"
    python scripts/search_demo.py "중도해지이율" --issuer 카카오뱅크
    python scripts/search_demo.py "중도해지이율" --doc-type 상품설명서 --k 5

지금은 필터를 사람이 넣는다. 5회차에 LLM 이 질문에서 필터를 뽑아낸다(Self-Query).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--issuer", help="발행사로 거른다 (예: 카카오뱅크)")
    ap.add_argument("--doc-type", help="문서 종류로 거른다 (예: 상품설명서, 약관, 특약)")
    args = ap.parse_args()

    from qdrant_client import models
    from finrag.index import qdrant
    from finrag.retrieval import dense

    must = []
    if args.issuer:
        must.append(models.FieldCondition(key="issuer", match=models.MatchValue(value=args.issuer)))
    if args.doc_type:
        must.append(models.FieldCondition(key="doc_type", match=models.MatchValue(value=args.doc_type)))
    flt = models.Filter(must=must) if must else None

    hits = dense.search(args.query, k=args.k, flt=flt)
    label = " · ".join(f"{k}={v}" for k, v in (("issuer", args.issuer), ("doc_type", args.doc_type)) if v) or "필터 없음"
    print(f"\n[{label}] {args.query}")
    print(f"  {'점수':>5}  {'문서':28} {'종류':8} {'시행일':10}  조항")
    for h in hits:
        print(f"  {h['score']:.3f}  {h['doc_id']:28} {h['doc_type']:8} {h['effective_from'] or '-':10}  {h['article'] or '-'}")
    if not hits:
        print("  (결과 없음. 필터 값이 payload 와 정확히 같아야 합니다. data/documents.csv 의 issuer, doc_type 열을 보세요)")
    qdrant.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
