# -*- coding: utf-8 -*-
"""Dense 검색."""
from __future__ import annotations

from qdrant_client import models

from ..index import qdrant
from ..index.embed import embed_query


def search(query: str, k: int = 10, flt: models.Filter | None = None,
           collection: str | None = None) -> list[dict]:
    return qdrant.search(embed_query(query), k=k, flt=flt, collection=collection)
