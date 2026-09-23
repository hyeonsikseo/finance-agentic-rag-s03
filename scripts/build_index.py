#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""인덱스 생성. 청크를 임베딩해 Qdrant 에 올린다.

    python scripts/build_index.py                 # 스냅샷 있으면 재사용
    python scripts/build_index.py --recompute     # 다시 임베딩
    python scripts/build_index.py --collection finrag_no_gate   # 게이트 OFF 비교용
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from finrag.index import qdrant                      # noqa: E402
from finrag.index.embed import embed_chunks, snapshot_path  # noqa: E402
from finrag.settings import get_settings             # noqa: E402


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunks", default=None)
    ap.add_argument("--collection", default=None)
    ap.add_argument("--recompute", action="store_true")
    args = ap.parse_args()

    s = get_settings()
    # 상대경로로 줄 수 있어야 한다. relative_to 는 절대경로가 아니면 터진다.
    path = (Path(args.chunks) if args.chunks else s.chunks_dir / "chunks.jsonl").resolve()
    chunks = [json.loads(l) for l in path.open(encoding="utf-8") if l.strip()]
    print(f"청크 {len(chunks):,}개 ← {_rel(path)}")

    # 스냅샷 파일 이름을 청크 파일에서 따온다. chunks.jsonl → 기본, chunks_gate_off.jsonl → gate_off
    tag = path.stem.replace("chunks", "").strip("_")
    t0 = time.perf_counter()
    vecs = embed_chunks(chunks, use_snapshot=not args.recompute, tag=tag)
    print(f"임베딩 {vecs.shape} ({time.perf_counter() - t0:.1f}초)  스냅샷: "
          f"{_rel(snapshot_path(tag))}")

    name = qdrant.recreate(vecs.shape[1], args.collection)
    t0 = time.perf_counter()
    n = qdrant.upsert(chunks, vecs, name)
    where = s.qdrant_url or f"임베디드({s.qdrant_path})"
    print(f"업서트 {n:,}건 → 컬렉션 '{name}' @ {where} ({time.perf_counter() - t0:.1f}초)")
    print(f"포인트 수: {qdrant.count(name):,}")
    qdrant.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
