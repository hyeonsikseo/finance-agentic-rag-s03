#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Baseline: Dense 검색만. 3회차에서 기록하는 첫 숫자."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from finrag.retrieval import dense   # noqa: E402


def build(k: int = 10):
    def run(question: str) -> dict:
        hits = dense.search(question, k=k)
        return {"chunk_ids": [h["chunk_id"] for h in hits], "hits": hits}
    return run


if __name__ == "__main__":
    from finrag.eval import harness
    res = harness.run(build(), "baseline")
    harness.print_summary(res)
    print("→", harness.save(res))
