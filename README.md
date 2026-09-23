# 약관부터 답변까지 — 3회차

금융 문서 특화 Agentic RAG 수업의 3회차 레포지토리입니다. 2회차 레포지토리(finance-agentic-rag-s02)와는 별개이고 새로 받습니다. 1·2회차 내용은 그대로 들어 있고, 2회차에 채운 함수 세 개는 **강사 정답으로 채워져** 있습니다. 자기 코드로 바꿔 써도 되지만, 그러면 청크 수와 검색 성적이 강사 값과 조금 달라질 수 있습니다.

## 3회차에 할 일

1. 설치합니다. 이번에는 패키지가 무거워지고(torch) 임베딩 모델 2.2GB 를 받아야 해서 **수업 전에** 끝내 둡니다. → [docs/install.md](docs/install.md)
2. 수업 앞부분은 노트북으로 LangGraph 의 상태·노드·엣지를 봅니다. 실습 1 이 여기 있습니다. → `make notebook`
3. 수업 중반은 인제스천 그래프의 함수 두 개를 채우고, 문서 51건을 그래프에 통과시켜 리포트를 읽습니다. → [docs/session3/lab.md](docs/session3/lab.md)
4. 수업 뒷부분은 청크를 Qdrant 에 넣고, 골든셋 40문항으로 첫 검색 성능(Recall@5)을 측정합니다. **이 숫자가 이후 회차 비교의 기준선입니다.**
5. 과제는 필수 둘(전체 실행, ADR-002)에 선택 하나(LLM 복구)이고, `make check-s03` 가 6/6 이면 끝입니다. → [docs/session3/homework.md](docs/session3/homework.md)

## 폴더

| 폴더 | 무엇 |
|---|---|
| `docs/install.md` | 설치. 2회차와 같고, 모델·임베딩 스냅샷 받는 단계가 추가됐습니다 |
| `docs/session3/` | 실습 순서(lab.md)와 과제(homework.md) |
| `docs/templates/adr.md` | 과제 ADR-002 에 쓰는 템플릿. 완성 예시는 `docs/session2/examples/01_ADR-001_청킹_전략.md` |
| `notebooks/s03_langgraph.ipynb` | LangGraph 15분. 수업 1~2부, 실습 1 |
| `src/finrag/ingestion/` | 인제스천 그래프. 채울 함수 두 개(`nodes.gate`, `graph.build_ingest_graph`)가 여기 있습니다 |
| `src/finrag/index/`, `retrieval/`, `eval/` | 임베딩 · Qdrant · Dense 검색 · 평가. 읽기만 합니다 |
| `pipelines/ingest.py` | 문서 51건을 그래프에 통과시켜 `data/chunks/chunks.jsonl` 과 `data/ingest_report.json` 을 만듭니다 |
| `pipelines/baseline.py` | 골든셋 40문항을 Dense 검색으로 풀어 `results/baseline.json` 을 만듭니다 |
| `tests/test_ingest.py` | 채운 함수가 맞는지 보는 테스트. 2회차 테스트도 그대로 돕니다 |
| `scripts/check_session.py` | 3회차 확인. 결과 파일이 제출물입니다 |
| `data/golden/gold_chunk_ids.json` | 골든셋 문항마다 정답 청크 ID. baseline 이 이걸로 채점합니다 |

## 명령

```bash
make setup       # 파이썬 3.12 와 패키지 설치. 5~10분
make download    # 문서 내려받기. 2회차 폴더에서 복사했으면 몇 초
make models      # 임베딩 모델 BGE-M3 받기. 2.2GB, 10~20분. 수업 전에
make embeddings  # 강사가 만든 임베딩 스냅샷 받기. 13MB. 없으면 make index 가 25분 걸립니다
make notebook    # LangGraph 노트북 열기
make test        # 자동 채점. 2회차 21개 + 3회차 14개. 채우기 전에는 12개 실패가 정상입니다
make ingest-sample  # 문서 6건만 그래프에 통과시켜 본다. 10초. 수업 중 확인용
make ingest      # 문서 51건 전부 → data/chunks/chunks.jsonl + data/ingest_report.json. 약 6분
make index       # 청크를 임베딩(스냅샷 재사용)해서 Qdrant 에 넣는다. 10초
make baseline    # 골든셋 40문항 Dense 검색 성능 측정 → results/baseline.json. 30초
make check-s03   # 결과물이 조건 6개를 만족하는지 확인 → results/check_s03.json
```

Windows 에서는 `make` 가 없으니 [docs/install.md](docs/install.md) 의 PowerShell 명령을 씁니다.

## 원본 문서가 레포지토리에 없는 이유

약관과 상품설명서는 각 금융회사의 저작물이라 다시 나눠 줄 수 없습니다. 레포지토리에는 "무엇을 어디서 받는지"만 있고, 각자 원 출처에서 받습니다. 자세한 것은 [data/README.md](data/README.md) 에 있습니다. 같은 이유로 문서 본문이 들어 있는 `data/chunks/`, `data/ocr_cache/` 도 레포지토리에 올리지 않습니다. 임베딩 스냅샷(`data/embeddings/`)은 본문이 아니라 숫자 벡터라 나눌 수 있지만, 13MB 라 레포지토리 대신 GitHub Release 로 나눕니다.
