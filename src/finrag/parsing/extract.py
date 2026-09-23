# -*- coding: utf-8 -*-
"""텍스트 추출과 파서 고르기.

같은 PDF 인데 파서에 따라 결과가 다르다. 하나은행 2009 약관은 pypdf 로 한글이 0자
나오지만 PyMuPDF 로는 6,874자가 나오고, 금감원 예금거래기본약관 PDF 는 PyMuPDF 로
띄어쓰기가 사라지지만 pdfplumber 로는 남는다. 그래서 "하나만 고르는" 대신
기본 파서로 뽑고 품질을 숫자로 재서 필요하면 다른 파서로 다시 뽑는다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import logging

import pymupdf

# 일부 PDF 는 색상 프로파일이 깨져 있어 MuPDF 가 "cmsOpenProfileFromMem failed" 를
# stderr 에 찍는다. 글자 추출 결과와는 무관한 경고라 꺼 둔다. 진짜 오류는 예외로 올라온다.
pymupdf.TOOLS.mupdf_display_errors(False)

# pypdf 는 한글 CID 폰트를 만나면 "Advanced encoding /UniKS-UTF16-H not implemented yet" 을
# 문서마다 찍는다. 글자를 못 읽는다는 뜻이 아니라 그 인코딩 표를 안 쓴다는 뜻이고, 결과는
# 검사기가 어차피 잰다. 51건을 돌리면 화면이 이 줄로 덮이므로 꺼 둔다.
logging.getLogger("pypdf").setLevel(logging.CRITICAL)

# 한국어 금융문서에 나올 수 있는 문자 범위. 이 밖은 폰트 매핑이 깨졌다는 신호다.
# scripts/profile_docs.py 와 같은 기준을 쓴다(둘이 어긋나면 게이트가 거짓말을 한다).
ALLOWED_RANGES = [
    (0x09, 0x0A), (0x0D, 0x0D), (0x20, 0x7E), (0xA0, 0xFF),
    (0x2000, 0x206F), (0x20A0, 0x20CF), (0x2100, 0x21FF), (0x2200, 0x22FF),
    (0x2460, 0x24FF), (0x2500, 0x257F), (0x25A0, 0x26FF),
    (0x3000, 0x303F), (0x3130, 0x318F), (0x4E00, 0x9FFF), (0xAC00, 0xD7A3),
    (0xF900, 0xFAFF), (0xFF00, 0xFFEF),
]
CID = re.compile(r"\(cid:\d+\)")
HANGUL = re.compile(r"[가-힣]")

PARSERS = ("pdfplumber", "pymupdf", "pypdf")


def is_allowed(ch: str) -> bool:
    o = ord(ch)
    return any(lo <= o <= hi for lo, hi in ALLOWED_RANGES)


def broken_ratio(text: str) -> float:
    if not text:
        return 0.0
    body = CID.sub("", text)
    return (sum(1 for c in body if not is_allowed(c)) + len(CID.findall(text))) / max(len(text), 1)


@dataclass
class Extraction:
    doc_id: str
    parser: str
    pages: list[str]
    attempts: list[dict] = field(default_factory=list)
    # 표 때문에 일부러 PyMuPDF 로 바꾼 페이지. 이 페이지는 공백이 적은 게 정상이므로
    # 게이트가 "공백 소실"로 벌주면 안 된다.
    table_swapped: list[int] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(self.pages)

    @property
    def n_pages(self) -> int:
        return len(self.pages)


def _pdfplumber(path: Path) -> list[str]:
    import pdfplumber
    with pdfplumber.open(str(path)) as pdf:
        return [(p.extract_text() or "") for p in pdf.pages]


def _pymupdf(path: Path) -> list[str]:
    import pymupdf
    with pymupdf.open(str(path)) as doc:
        return [pg.get_text() for pg in doc]


def _pypdf(path: Path) -> list[str]:
    from pypdf import PdfReader
    return [(p.extract_text() or "") for p in PdfReader(str(path)).pages]


_FN = {"pdfplumber": _pdfplumber, "pymupdf": _pymupdf, "pypdf": _pypdf}


def extract_with(path: Path, parser: str) -> list[str]:
    try:
        return _FN[parser](path)
    except Exception:
        return []


def page_objects(path: Path) -> list[dict]:
    """페이지마다 이미지·벡터 객체가 있는지 본다.

    글자가 0자인 페이지가 다 같지 않다. 이미지가 있으면 스캔본이라 OCR 로 보내야 하고,
    아무 객체도 없으면 그냥 빈 페이지라 건너뛰어야 한다. 이 구분을 못 하면 빈 페이지가
    OCR 큐에 계속 쌓인다.
    """
    try:
        import pymupdf
        with pymupdf.open(str(path)) as doc:
            return [{"images": len(p.get_images(full=True)), "drawings": len(p.get_drawings())}
                    for p in doc]
    except Exception:
        return []


def table_pages(path: Path, max_pages: int = 400) -> set[int]:
    """표가 있는 페이지 번호.

    pdfplumber 는 흐르는 본문에서 띄어쓰기를 잘 살리지만, 표 페이지에서는 셀을
    좌표 순서로 읽어 문장을 흩뜨린다. 실손 표준약관 259쪽에서 "3만원과 보장대상
    의료비의 30% 중 큰 금액"이 조각나 검색으로 찾을 수 없게 되는 식이다.
    PyMuPDF 는 블록 단위로 읽어 이런 문구를 붙여 둔다. 그래서 표 페이지만 갈아 끼운다.
    """
    found: set[int] = set()
    try:
        import pdfplumber
        with pdfplumber.open(str(path)) as pdf:
            for i, page in enumerate(pdf.pages[:max_pages], start=1):
                try:
                    if page.find_tables():
                        found.add(i)
                except Exception:
                    continue
    except Exception:
        pass
    return found


def score(pages: list[str]) -> dict:
    text = "".join(pages)
    n = len(text)
    return {
        "chars": n,
        "hangul": len(HANGUL.findall(text)),
        "broken_ratio": round(broken_ratio(text), 5),
        "space_ratio": round(text.count(" ") / n, 4) if n else 0.0,
        "chars_per_page": round(n / len(pages), 1) if pages else 0.0,
    }


def extract(path: Path, doc_id: str, *, prefer: str = "pdfplumber") -> Extraction:
    """기본 파서로 뽑고, 품질이 나쁘면 다른 파서로 다시 뽑는다.

    판단 기준은 두 가지뿐이다.
      - 한글이 거의 안 나온다(폰트 매핑이 깨졌다)
      - 띄어쓰기가 거의 없다(한컴 계열 PDF 에서 공백이 흘렀다)
    둘 다 "본문 자체가 달라지는" 문제라서 재시도할 값어치가 있다. 표가 깨지는 것은
    여기서 다루지 않고 tables.py 가 따로 처리한다.
    """
    order = [prefer] + [p for p in PARSERS if p != prefer]
    attempts: list[dict] = []
    best: tuple[list[str], str, dict] | None = None

    for parser in order:
        pages = extract_with(path, parser)
        st = score(pages)
        attempts.append({"parser": parser, **st})
        if best is None or st["hangul"] > best[2]["hangul"]:
            best = (pages, parser, st)

        # 첫 파서 결과가 쓸 만하면 더 시도하지 않는다(모든 문서를 3번 열 이유가 없다).
        if parser == prefer:
            enough_hangul = st["hangul"] >= 50
            enough_space = st["space_ratio"] >= 0.03 or st["chars"] < 200
            if enough_hangul and enough_space and st["broken_ratio"] < 0.05:
                pages, swapped = _fix_table_pages(path, pages, parser)
                if swapped:
                    attempts.append({"parser": f"{parser}+pymupdf(표 {len(swapped)}쪽)",
                                     **score(pages)})
                return Extraction(doc_id, parser, pages, attempts, swapped)

    pages, parser, _ = best  # type: ignore[misc]
    pages, swapped = _fix_table_pages(path, pages, parser)
    if swapped:
        attempts.append({"parser": f"{parser}+pymupdf(표 {len(swapped)}쪽)", **score(pages)})
    return Extraction(doc_id, parser, pages, attempts, swapped)


def _fix_table_pages(path: Path, pages: list[str], parser: str) -> tuple[list[str], list[int]]:
    """표가 있는 페이지만 PyMuPDF 결과로 바꾼다. 파서 선택을 문서가 아니라 페이지 단위로 한다."""
    if parser != "pdfplumber" or not pages:
        return pages, []
    tp = table_pages(path)
    if not tp:
        return pages, []
    alt = extract_with(path, "pymupdf")
    if not alt:
        return pages, []
    out, swapped = list(pages), []
    for pno in sorted(tp):
        if pno <= len(alt) and alt[pno - 1].strip():
            out[pno - 1] = alt[pno - 1]
            swapped.append(pno)
    return out, swapped
