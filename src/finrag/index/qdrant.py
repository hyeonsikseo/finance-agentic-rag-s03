# -*- coding: utf-8 -*-
"""Qdrant 컬렉션.

QDRANT_URL 이 있으면 서버로, 없으면 임베디드(로컬 경로)로 붙는다. 도커가 없어도
수업이 굴러가야 하고, 도커가 있으면 같은 코드가 그대로 서버를 쓴다.

payload 인덱스를 만드는 이유: Self-Query 가 doc_type·issuer·effective_from 으로
거르는데, 인덱스가 없으면 전수 스캔이라 필터가 붙을수록 느려진다.
"""
from __future__ import annotations

import atexit
from functools import lru_cache

import numpy as np
from qdrant_client import QdrantClient, models

from ..settings import get_settings

PAYLOAD_KEYWORD = ["doc_id", "doc_type", "issuer", "product", "generation", "category",
                   "article", "quality", "purpose", "parser", "validation"]
PAYLOAD_BOOL = ["synthetic_degraded", "expired", "llm_repaired"]
PAYLOAD_TEXT = ["effective_from", "effective_to", "review_expiry"]


@lru_cache
def get_client() -> QdrantClient:
    s = get_settings()
    if s.qdrant_url:
        return QdrantClient(url=s.qdrant_url, timeout=60)
    path = s.root / s.qdrant_path
    path.mkdir(parents=True, exist_ok=True)
    client = QdrantClient(path=str(path))
    # 임베디드 모드에서 닫지 않고 종료하면 __del__ 이 인터프리터 종료 도중 돌면서
    # "ImportError: sys.meta_path is None" 을 찍는다. 동작 문제는 없지만 학생이
    # 보면 실패한 줄 안다. 종료 훅에서 미리 닫는다.
    atexit.register(close)
    return client


def recreate(dim: int, collection: str | None = None) -> str:
    s = get_settings()
    name = collection or s.qdrant_collection
    c = get_client()
    if c.collection_exists(name):
        c.delete_collection(name)
    c.create_collection(
        collection_name=name,
        vectors_config={"dense": models.VectorParams(size=dim, distance=models.Distance.COSINE)},
    )
    for field in PAYLOAD_KEYWORD:
        c.create_payload_index(name, field, models.PayloadSchemaType.KEYWORD)
    for field in PAYLOAD_BOOL:
        c.create_payload_index(name, field, models.PayloadSchemaType.BOOL)
    for field in PAYLOAD_TEXT:
        c.create_payload_index(name, field, models.PayloadSchemaType.KEYWORD)
    return name


def _payload(chunk: dict) -> dict:
    m = dict(chunk.get("meta", {}))
    m.pop("traits", None)
    return {
        "chunk_id": chunk["chunk_id"], "doc_id": chunk["doc_id"], "text": chunk["text"],
        "article": chunk.get("article", ""), "article_title": chunk.get("article_title", ""),
        "page_start": chunk.get("page_start", 0), "page_end": chunk.get("page_end", 0),
        "doc_type": m.get("doc_type", ""), "issuer": m.get("issuer", ""),
        "product": m.get("product", ""), "generation": m.get("generation", ""),
        "category": m.get("category", ""), "quality": m.get("quality", ""),
        "purpose": m.get("purpose", ""), "parser": m.get("parser", ""),
        "validation": m.get("validation", ""),
        "effective_from": m.get("effective_from", ""), "effective_to": m.get("effective_to", ""),
        "review_expiry": m.get("review_expiry", ""),
        "synthetic_degraded": bool(m.get("synthetic_degraded")),
        "expired": bool(m.get("expired")), "llm_repaired": bool(m.get("llm_repaired")),
        "license": m.get("license", ""),
    }


def upsert(chunks: list[dict], vectors: np.ndarray, collection: str | None = None,
           batch: int = 256) -> int:
    s = get_settings()
    name = collection or s.qdrant_collection
    c = get_client()
    for i in range(0, len(chunks), batch):
        c.upsert(name, points=[
            models.PointStruct(id=i + j, vector={"dense": vectors[i + j].tolist()},
                               payload=_payload(ch))
            for j, ch in enumerate(chunks[i:i + batch])
        ])
    return len(chunks)


def close() -> None:
    """임베디드 모드에서 명시적으로 닫는다.

    닫지 않으면 인터프리터 종료 중에 __del__ 이 돌면서
    "ImportError: sys.meta_path is None" 이 찍힌다. 동작에는 문제가 없지만
    학생이 보면 실패한 줄 안다.
    """
    if get_client.cache_info().currsize:
        try:
            get_client().close()
        except Exception:
            pass
        get_client.cache_clear()


def count(collection: str | None = None) -> int:
    s = get_settings()
    name = collection or s.qdrant_collection
    c = get_client()
    return c.count(name).count if c.collection_exists(name) else 0


def search(vector: np.ndarray, k: int = 10, flt: models.Filter | None = None,
           collection: str | None = None) -> list[dict]:
    s = get_settings()
    name = collection or s.qdrant_collection
    res = get_client().query_points(name, query=vector.tolist(), using="dense",
                                    limit=k, query_filter=flt, with_payload=True).points
    return [{"chunk_id": p.payload["chunk_id"], "score": float(p.score), **p.payload} for p in res]
