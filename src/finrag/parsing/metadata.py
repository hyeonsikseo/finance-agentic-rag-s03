# -*- coding: utf-8 -*-
"""메타데이터 정규형.

Self-Query 가 거는 필터의 값이 여기서 정해진다. 문서마다 표기가 다르면 필터가
안 걸리므로, 문서에서 읽은 원문 표기를 정규값으로 옮긴다.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field, asdict
from datetime import date
from functools import lru_cache

from ..settings import get_settings

DOC_TYPES = ["약관", "표준약관", "특약", "부속약관", "상품설명서", "개정대비표",
             "사업방법서", "사업비안내", "경영공시", "공시", "이용안내", "법령",
             "분쟁조정사례", "민원사례", "FAQ", "기타"]

# 사용자가 쓰는 말 → 문서에 있는 말. data/glossary.md 의 질의 확장 사전과 같은 표다.
ALIASES: dict[str, list[str]] = {
    "자기부담금": ["공제금액", "본인부담금", "면책금액"],
    "본인부담": ["공제금액", "자기부담률"],
    "리볼빙": ["일부결제금액이월약정", "회전결제"],
    "중도해지금리": ["중도해지이율", "중도해지이자율"],
    "중도상환수수료": ["중도상환해약금", "조기상환수수료"],
    "연체금리": ["연체이자율", "지연배상금률", "지연배상금"],
    "대출금리": ["약정이자율", "적용금리"],
    "해지환급금": ["해약환급금", "환급금"],
    "만기금리": ["만기후이율", "만기후금리"],
    "가입금액": ["보험가입금액", "계약금액"],
    "알릴의무": ["고지의무", "계약 전 알릴 의무"],
    "현금서비스": ["단기카드대출"],
    "카드론": ["장기카드대출"],
}

# 조항 표기가 제각각이다: "제31 조", "제 7 조", "제4조의2". 하나로 모은다.
ARTICLE_PAT = re.compile(r"제\s*(\d+)\s*조(?:\s*의\s*(\d+))?")
ARTICLE_HEAD = re.compile(r"^\s*제\s*(\d+)\s*조(?:\s*의\s*(\d+))?\s*[［\[(（]?\s*([^］\])）\n]{0,40})")


def normalize_article(raw: str) -> str | None:
    """'제 31 조' → '제31조', '제4조의2' → '제4조의2'."""
    m = ARTICLE_PAT.search(raw)
    if not m:
        return None
    return f"제{int(m.group(1))}조" + (f"의{int(m.group(2))}" if m.group(2) else "")


def expand_query_terms(q: str) -> list[str]:
    """질의에 별칭을 더한다. BM25 는 같은 뜻의 다른 말을 모른다."""
    extra: list[str] = []
    for user_word, doc_words in ALIASES.items():
        if user_word in q:
            extra += doc_words
        for w in doc_words:
            if w in q and user_word not in extra:
                extra.append(user_word)
    return extra


@dataclass
class DocMeta:
    doc_id: str
    doc_type: str = "기타"
    issuer: str = ""
    product: str = ""
    generation: str = ""
    effective_from: str = ""
    effective_to: str = ""
    review_expiry: str = ""
    category: str = ""
    license: str = ""
    synthetic_degraded: bool = False
    purpose: str = ""
    path: str = ""
    format: str = ""
    pages: int = 0
    quality: str = ""
    best_parser: str = ""
    traits: list[str] = field(default_factory=list)

    @property
    def expired(self) -> bool:
        """심의필 유효기간이 지났는가. 지났으면 답변에 경고를 붙여야 한다."""
        return bool(self.review_expiry) and self.review_expiry < date.today().isoformat()

    def payload(self) -> dict:
        d = asdict(self)
        d["expired"] = self.expired
        return d


@lru_cache
def load_documents() -> dict[str, DocMeta]:
    """data/documents.csv 를 읽는다. 이 파일이 메타데이터의 유일한 출처다."""
    s = get_settings()
    path = s.data / "documents.csv"
    out: dict[str, DocMeta] = {}
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[r["doc_id"]] = DocMeta(
                doc_id=r["doc_id"], doc_type=r["doc_type"] or "기타", issuer=r["issuer"],
                product=r["product"], generation=r["generation"],
                effective_from=r["effective_from"], effective_to=r["effective_to"],
                review_expiry=r["review_expiry"], category=r["category"],
                license=r["license"], purpose=r["purpose"], path=r["path"], format=r["format"],
                pages=int(r["pages"]) if r["pages"] else 0,
                quality=r["quality"], best_parser=r["best_parser"],
                synthetic_degraded=r["synthetic_degraded"] == "true",
                traits=[t for t in r["traits_measured"].split("|") if t],
            )
    return out
