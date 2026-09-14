# -*- coding: utf-8 -*-
"""검증 게이트.

인제스천에서 유일하게 "판단"하는 자리다. 문서를 통과 / 재추출 / 실패 세 갈래로 보낸다.
LLM 을 쓰지 않는다. 휴리스틱 네 개로 충분하고, 결정적이라 재현된다.

임계값은 2회차에 실제 문서로 캘리브레이션한 값이다. 근거는 data/doc_profile.json.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict

from .extract import HANGUL, broken_ratio

# ── 임계값 (2026-09 코퍼스 51문서 실측 기준) ──────────────────────────
MIN_CHARS_PER_PAGE = 50        # 이보다 적으면 텍스트 레이어가 없다고 본다
MIN_HANGUL_RATIO = 0.10        # 한국어 문서인데 한글이 10% 미만이면 폰트가 깨진 것
MAX_BROKEN_RATIO = 0.05        # 허용 문자 밖 비율. 별표15 55쪽이 0.076, ABL 6쪽이 0.204
MIN_SPACE_RATIO = 0.02         # 공백 소실 감지. 정상 문서는 0.06~0.20
MAX_SINGLE_CHAR_TOKEN_RATIO = 0.55   # 자간 분리 감지("금 융 소 비 자")

TOKEN = re.compile(r"\S+")


@dataclass
class PageReport:
    page: int
    chars: int
    hangul_ratio: float
    broken_ratio: float
    space_ratio: float
    single_char_token_ratio: float
    verdict: str
    reasons: list[str]


@dataclass
class DocReport:
    doc_id: str
    parser: str
    verdict: str                  # pass | reparse | ocr | fail
    reasons: list[str]
    pages: list[PageReport]
    usable_pages: int = 0

    @property
    def bad_pages(self) -> list[int]:
        return [p.page for p in self.pages if p.verdict != "pass"]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["bad_pages"] = self.bad_pages
        return d


def score_page(text: str) -> dict:
    n = len(text)
    tokens = TOKEN.findall(text)
    return {
        "chars": n,
        "hangul_ratio": round(len(HANGUL.findall(text)) / n, 4) if n else 0.0,
        "broken_ratio": round(broken_ratio(text), 5),
        "space_ratio": round(text.count(" ") / n, 4) if n else 0.0,
        "single_char_token_ratio": round(sum(1 for t in tokens if len(t) == 1) / len(tokens), 4) if tokens else 0.0,
    }


def judge_page(m: dict, *, has_image: bool, skip_space: bool = False) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if m["chars"] < MIN_CHARS_PER_PAGE:
        # 이미지가 있으면 스캔본이라 OCR 로, 없으면 그냥 빈 페이지라 통과시킨다.
        return ("ocr", ["텍스트 없음, 이미지 있음"]) if has_image else ("pass", ["빈 페이지"])
    if m["hangul_ratio"] < MIN_HANGUL_RATIO:
        reasons.append(f"한글 비율 {m['hangul_ratio']:.3f} < {MIN_HANGUL_RATIO}")
    if m["broken_ratio"] > MAX_BROKEN_RATIO:
        reasons.append(f"깨진 문자 비율 {m['broken_ratio']:.3f} > {MAX_BROKEN_RATIO}")
    if not skip_space and m["space_ratio"] < MIN_SPACE_RATIO:
        reasons.append(f"공백 비율 {m['space_ratio']:.3f} < {MIN_SPACE_RATIO}")
    if m["single_char_token_ratio"] > MAX_SINGLE_CHAR_TOKEN_RATIO:
        reasons.append(f"단음절 토큰 비율 {m['single_char_token_ratio']:.3f} > {MAX_SINGLE_CHAR_TOKEN_RATIO}")
    return ("reparse" if reasons else "pass"), reasons


def validate(extraction, page_objs: list[dict] | None = None) -> DocReport:
    """페이지별로 재고 문서 판정을 낸다.

    한 페이지가 나쁘다고 문서 전체를 버리지 않는다. 별표15는 492쪽 중 1쪽만 깨졌다.
    문서 판정은 "나쁜 페이지가 얼마나 되는가"로 낸다.
    """
    page_objs = page_objs or []
    swapped = set(getattr(extraction, "table_swapped", []) or [])
    pages: list[PageReport] = []
    for i, text in enumerate(extraction.pages, start=1):
        m = score_page(text)
        obj = page_objs[i - 1] if i <= len(page_objs) else {"images": 0}
        verdict, reasons = judge_page(m, has_image=bool(obj.get("images")),
                                      skip_space=i in swapped)
        pages.append(PageReport(page=i, verdict=verdict, reasons=reasons, **m))

    n = len(pages) or 1
    n_reparse = sum(1 for p in pages if p.verdict == "reparse")
    n_ocr = sum(1 for p in pages if p.verdict == "ocr")
    usable = sum(1 for p in pages if p.verdict == "pass" and p.chars >= MIN_CHARS_PER_PAGE)

    reasons: list[str] = []
    if n_ocr:
        reasons.append(f"OCR 필요 {n_ocr}쪽")
    if n_reparse:
        reasons.append(f"재추출 필요 {n_reparse}쪽")

    # 문서 판정은 "이 문서를 통째로 어떻게 할 것인가"이지 "나쁜 페이지가 있는가"가 아니다.
    # 492쪽 중 2쪽이 나쁘다고 490쪽을 버리면 손해가 훨씬 크다. 그래서 쓸 수 있는
    # 페이지가 하나라도 있으면 버리지 않고, 나쁜 페이지만 고치거나 빼고 간다.
    if usable == 0 and n_ocr == 0:
        verdict = "fail"
        reasons.append("쓸 수 있는 페이지가 없음")
    elif usable == 0:
        verdict = "ocr"            # 전체가 스캔본. OCR 없이는 아무것도 못 한다.
    elif n_reparse:
        verdict = "reparse"        # 고쳐 보고, 안 되면 그 페이지만 빼고 간다.
    elif n_ocr:
        verdict = "ocr"
    else:
        verdict = "pass"
    return DocReport(extraction.doc_id, extraction.parser, verdict, reasons, pages,
                     usable_pages=usable)
