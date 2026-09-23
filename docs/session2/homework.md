# 2회차 과제

필수 둘, 선택 하나입니다. 다음 회차 전까지 냅니다. 끝났는지는 `make check-s02` 가 **6/6** 인지로 압니다.

## 필수 1. 청크 파일 만들기 — 수업에서 끝냈으면 0분, 아니면 15분

세 함수가 다 채워졌으면 이렇게 끝납니다.

```bash
make test        # 21개 전부 통과
make chunk       # 문서 51건 → data/chunks/chunks.jsonl. 4~5분
make check-s02   # 5/6. 마지막 항목은 필수 2 입니다
```

수업에서 못 채운 함수가 있으면 강사가 수업 뒤 올리는 **solution 브랜치**를 봅니다. 브라우저에서 이 URL 을 열면 세 파일이 있습니다.

https://github.com/hyeonsikseo/finance-agentic-rag-s02/tree/solution/src/finrag/parsing

보고 베끼는 게 아니라 **읽고 닫은 다음 자기 손으로 다시 씁니다.** 3회차부터 이 함수들 위에 쌓이므로, 지금 이해하고 넘어가야 합니다.

## 필수 2. 질문 3개와 근거 청크 — 15분

1회차에는 질문을 내지 않았으니 여기서 만듭니다. 상담사가 실제로 받을 법한 질문 3개를 만들고, 각 질문의 답이 있는 청크의 ID 를 붙입니다. 청크 ID 가 오늘 확정됐기 때문에 이제 할 수 있는 일이고, 자기 코드가 만든 `chunks.jsonl` 을 직접 열어 보게 됩니다.

파일은 `data/golden/student_q.jsonl` 입니다. 한 줄에 문항 하나, JSON 형식입니다(JSON Lines).

```json
{"id": "Q1", "type": "조항번호형", "question": "하나카드 표준약관 제31조의 리볼빙이란 무엇인가요?", "answer": "회원이 약정한 최소결제비율 이상을 결제하면 잔여금액을 다음 달로 이월하는 결제방식", "gold_chunk_ids": ["hanacard_std_2017#제31조#1"]}
```

- `type` 은 [1회차 질문 유형 정의서](../session1/examples/03_질문_유형_정의서.md) 의 8유형 중 하나입니다. 세 문항의 유형이 서로 다르면 좋습니다.
- `gold_chunk_ids` 는 `data/chunks/chunks.jsonl` 에 **실제로 있는** ID 여야 합니다. `make check-s02` 가 대조합니다. 답이 두 청크에 걸치면 둘 다 적습니다.
- 청크 ID 찾기. 문서와 조항을 알면 이렇게 봅니다.

```bash
.venv/bin/python -c "import json; [print(c['chunk_id'], '|', c['text'][:60]) for c in map(json.loads, open('data/chunks/chunks.jsonl', encoding='utf-8')) if c['doc_id']=='hanacard_std_2017' and c['article']=='제31조']"
```

조항을 모르면 `article` 조건을 빼고 `'리볼빙' in c['text']` 처럼 본문으로 찾습니다. `doc_id` 는 `data/documents.csv` 첫 열에 있습니다.

## 선택. 게이트 임계값 표 — 10분

`docs/templates/feedback_memo.md` 를 `docs/feedback_memo.md` 로 복사하고 **"4. 게이트 임계값과 근거" 표 하나만** 채웁니다. 노트북 4부에서 기준값을 움직여 본 셀(셀 15)에 숫자가 다 있으니 옮겨 적고, "왜 이 값인가"를 한 줄씩 씁니다. 한 번도 걸리지 않은 지표가 있으면 그 사실도 적습니다. 나머지 절은 비워 둬도 됩니다.

## 제출

1. `make check-s02` 가 6/6 인지 봅니다.
2. 커밋하고 자기 포크에 올립니다.

```bash
git add src/finrag/parsing/ data/golden/student_q.jsonl results/check_s02.json docs/feedback_memo.md
git commit -m "2회차 과제"
git push
```

(`docs/feedback_memo.md` 가 없으면 그 부분은 빼고 add 합니다.)

3. 자기 포크 URL(`https://github.com/<계정>/finance-agentic-rag-s02`)를 디스코드에 올립니다.

포크 없이 받았으면 위 파일들(`src/finrag/parsing/` 폴더 포함)을 zip 으로 묶어 디스코드에 올립니다.

## check-s02 가 보는 것

| 항목 | 통과 기준 |
|---|---|
| 청크 생성 | `data/chunks/chunks.jsonl` 에 1,000개 이상 |
| 청크 필수 필드 | `chunk_id`, `doc_id`, `text`, `article`, `page_start` |
| 메타데이터 부착 | `meta` 에 `doc_type`, `issuer`, `effective_from`, `parser`, `validation` |
| 게이트 판정 기록 | 모든 청크의 `validation` 이 `pass` / `reparse` / `ocr` 중 하나 |
| 청크 ID 유일 · 형식 | 중복 없음, `{doc_id}#{조항}#{seq}` |
| 질문에 근거 청크 | `student_q.jsonl` 에 `gold_chunk_ids` 가 있는 문항 3개 이상, 없는 ID 없음 |

## 마감 뒤 강사가 올리는 것

1회차 산출물 예시와 같은 방식입니다. `docs/session2/examples/` 에 청킹 전략 결정 기록(ADR-001)과 피드백 메모 완성본을 올립니다. 받는 법:

```bash
git pull upstream main
```

이런 문서를 왜 쓰는지, 어떻게 쓰는지는 예시를 보면 됩니다. 3회차부터는 직접 씁니다.
