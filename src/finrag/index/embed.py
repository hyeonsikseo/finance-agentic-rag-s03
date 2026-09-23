# -*- coding: utf-8 -*-
"""임베딩.

BGE-M3 를 sentence-transformers 로 돌린다. fastembed 는 bge-m3 를 지원하지 않는다
(PR #602 미병합).

스냅샷은 청크 하나마다 "본문 해시 → 벡터" 로 저장한다. 강사가 미리 계산한 스냅샷을
받아 두면 본문이 같은 청크는 다시 계산하지 않고, 없는 청크만 계산한다. 문서 두 건이
빠졌거나 OCR 캐시가 없어 청크 몇 개가 다른 학생도 몇 초면 끝난다. 예전 방식(청크
전체를 하나의 해시로)은 청크 하나만 달라도 3,700개를 다시 계산해야 했다(약 25분).
"""
from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

import numpy as np

from ..settings import get_settings


@lru_cache
def get_model():
    """모델을 캐시에서 올린다. 캐시에 없으면 내려받지 않고 무엇을 할지 알려 준다.

    sentence-transformers 는 캐시에 없는 모델을 조용히 내려받기 시작한다(2.2GB).
    수업 중에 그 일이 일어나면 안 된다. 받는 것은 scripts/pull_models.py 가 한다.
    """
    import os
    s = get_settings()
    os.environ.setdefault("HF_HOME", s.hf_home)
    from sentence_transformers import SentenceTransformer
    try:
        return SentenceTransformer(s.embedding_model, local_files_only=True)
    except Exception as e:  # OSError / HFValidationError 등 캐시 없음 계열
        raise RuntimeError(
            f"임베딩 모델 {s.embedding_model} 이 {s.hf_home} 에 없습니다. "
            "먼저 받으세요: make models  (Windows: .venv\\Scripts\\python scripts\\pull_models.py)"
        ) from e


def snapshot_path(tag: str = "") -> Path:
    """청크 세트마다 다른 파일에 저장한다.

    게이트 OFF 대조군을 임베딩할 때 같은 파일에 쓰면 본 스냅샷을 덮어쓴다.
    강사가 25분 걸려 만든 것을 대조군 실험 한 번에 잃는다.
    """
    s = get_settings()
    name = s.embedding_model.replace("/", "_") + (f"__{tag}" if tag else "")
    return s.data / "embeddings" / f"{name}.npz"


def text_key(text: str) -> str:
    """청크 본문 하나의 해시. 스냅샷의 열쇠다."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _legacy_key(texts: list[str]) -> str:
    """예전 스냅샷의 열쇠(전체 본문을 순서대로 이어 붙인 해시)."""
    h = hashlib.sha256()
    for t in texts:
        h.update(t.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()[:16]


def load_snapshot(path: Path, texts: list[str] | None = None) -> dict[str, np.ndarray]:
    """스냅샷을 {본문 해시: 벡터} 로 읽는다. 없으면 빈 dict.

    예전 형식(key 하나 + vectors)은 지금 본문 전체와 해시가 같을 때만 쓴다.
    """
    if not path.exists():
        return {}
    data = np.load(path, allow_pickle=False)
    if "keys" in data:
        return dict(zip(data["keys"].tolist(), data["vectors"]))
    if "key" in data and texts is not None and str(data["key"]) == _legacy_key(texts):
        return {text_key(t): v for t, v in zip(texts, data["vectors"])}
    return {}


def save_snapshot(path: Path, cache: dict[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = sorted(cache)
    np.savez_compressed(path, keys=np.array(keys),
                        vectors=np.stack([cache[k] for k in keys]).astype(np.float32))


def embed_texts(texts: list[str], *, batch_size: int = 16, show_progress: bool = False) -> np.ndarray:
    model = get_model()
    return np.asarray(model.encode(texts, batch_size=batch_size, normalize_embeddings=True,
                                   show_progress_bar=show_progress), dtype=np.float32)


def embed_chunks(chunks: list[dict], *, use_snapshot: bool = True,
                 show_progress: bool = True, tag: str = "") -> np.ndarray:
    """청크 벡터. 스냅샷에 있는 청크는 재사용하고 없는 것만 계산한다.

    3회차에서 학생이 CPU 로 3,700청크를 임베딩하려면 오래 걸린다. 강사가 만든
    스냅샷을 받아 두면(make embeddings) 본문이 같은 청크는 계산하지 않는다.
    새로 계산한 벡터는 스냅샷에 합쳐 저장하므로 두 번째부터는 전부 재사용된다.
    """
    texts = [c["text"] for c in chunks]
    keys = [text_key(t) for t in texts]
    path = snapshot_path(tag)
    cache = load_snapshot(path, texts) if use_snapshot else {}

    missing = [i for i, k in enumerate(keys) if k not in cache]
    if missing:
        print(f"임베딩: 스냅샷에서 {len(keys) - len(missing):,}개 재사용, {len(missing):,}개 계산")
        vecs = embed_texts([texts[i] for i in missing], show_progress=show_progress)
        for i, v in zip(missing, vecs):
            cache[keys[i]] = v
        save_snapshot(path, cache)
    elif keys:
        print(f"임베딩: 스냅샷에서 {len(keys):,}개 전부 재사용")

    return np.stack([cache[k] for k in keys]).astype(np.float32) if keys else np.zeros((0, 1024), np.float32)


def embed_query(q: str) -> np.ndarray:
    return embed_texts([q])[0]
