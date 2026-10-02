# 3회차 과제

필수 둘, 선택 하나입니다. 다음 회차 전까지 냅니다. 끝났는지는 `make check-s03` 가 **6/6** 인지로 압니다.

## 필수 1. 전체 실행 — 수업에서 끝냈으면 0분, 아니면 10분

함수 두 개(`nodes.gate`, `graph.build_ingest_graph`)가 채워졌으면 이렇게 끝납니다.

```bash
make test        # 35개 전부 통과 (2회차 21개 + 3회차 14개)
make ingest      # 문서 51건 → data/chunks/chunks.jsonl + data/ingest_report.json. 약 6분
make index       # 청크 → Qdrant. 스냅샷이 있으면 10초
make baseline    # 40문항 → results/baseline.json. 30초
make check-s03   # 5/6. 마지막 항목은 필수 2 입니다
```

Windows 는 [install.md](../install.md) 의 PowerShell 명령을 씁니다. 수업에서 못 채운 함수가 있으면 강사가 수업 뒤 올리는 **solution 브랜치**를 봅니다.

https://github.com/hyeonsikseo/finance-agentic-rag-s03/tree/solution/src/finrag/ingestion

보고 베끼는 게 아니라 **읽고 닫은 다음 자기 손으로 다시 씁니다.** 4회차부터 이 그래프 위에 검색이 얹히므로, 지금 이해하고 넘어가야 합니다.

`results/baseline.json` 의 `overall.recall@5` 를 적어 두세요. 강사 값은 0.750(MRR 0.532)입니다. 문서가 한두 건 빠졌으면 조금 낮게 나오는데, 그건 틀린 게 아닙니다. `data/ingest_report.json` 의 `failed` 목록에 그 문서가 있는지 보면 됩니다.

## 필수 2. ADR-002 — 20분

오늘 만든 인제스천 그래프에 대해 **결정 기록(ADR)** 을 씁니다. 2회차에는 완성본(ADR-001)을 예시로 보기만 했고, 이번에는 직접 씁니다.

1. `docs/templates/adr.md` 를 `docs/adr/ADR-002-ingestion-graph.md` 로 복사합니다.
2. 빈칸(`______`)을 전부 채웁니다. `make check-s03` 가 빈칸이 남았는지 셉니다.

제목은 "인제스천에 LangGraph 를 쓰되, 문서당 LLM 루프는 두지 않는다" 로 잡으면 됩니다. 채울 때 볼 것:

- **맥락의 숫자**는 `data/ingest_report.json` 에서 가져옵니다. 게이트 판정별 문서 수, 사람 검토 큐에 간 3건이 무엇이고 왜 왔는지(`failed` 의 `reasons` 와 `warnings`).
- **대안**은 최소 둘. "문서마다 LLM 에게 읽혀서 정리시킨다"와 "if 문으로 직접 짠다"를 넣고, 왜 안 골랐는지를 비용·지연·재현성으로 적습니다. 수업 1부 슬라이드의 표가 그대로 근거입니다.
- **되돌릴 조건**을 비워 두지 않습니다. 어떤 일이 생기면 문서당 LLM 을 다시 검토할지 한 줄이면 됩니다.
- 길이는 한 쪽. 예시 형식은 [ADR-001](../session2/examples/01_ADR-001_청킹_전략.md) 을 봅니다.

## 선택. LLM 복구 노드 프롬프트 — 15분, OpenAI 키가 있는 분만

`src/finrag/ingestion/nodes.py` 의 `llm_repair` 는 다른 파서로 다시 추출해도 쓸 수 있는 쪽이 하나도 없는 문서를 LLM 에게 복원시키는 마지막 수단입니다. 지금 문서 중에는 손보협회 공시(`knia_4000`, 한 쪽짜리인데 띄어쓰기가 전부 사라진 문서) 한 건이 이 노드까지 갑니다. 키가 없으면 "LLM 키가 없어 복구를 건너뜀" 이라는 경고와 함께 사람 검토 큐로 갑니다. 지금은 프롬프트가 한 줄뿐입니다. 위의 "프롬프트를 채우세요" 안내를 보고 프롬프트를 고칩니다. 반드시 넣을 것: **내용을 추측해 채우지 말 것, 판독 불가한 부분은 `[판독불가]` 로 표시할 것.** 이걸 빼면 LLM 이 깨진 약관 조항을 그럴듯하게 지어내고, 그게 근거로 인용됩니다.

`.env.example` 을 `.env` 로 복사해 `OPENAI_API_KEY` 를 채운 뒤 그 문서 하나로 돌려 봅니다.

```bash
.venv/bin/python pipelines/ingest.py --only knia_4000 --no-checkpoint
```

`data/ingest_report_sample.json` 의 `llm_repaired` 에 `knia_4000` 이 찍히면 된 것입니다. 복구된 청크는 `data/chunks/chunks_sample.jsonl` 에 있고 `meta.llm_repaired` 가 `true` 라서 나중에 평가에서 따로 셀 수 있습니다. 결과는 `data/repair_cache/knia_4000.json` 에 캐시되어 두 번째 실행부터는 LLM 을 부르지 않습니다. 프롬프트를 고친 뒤 다시 보려면 그 파일을 지우고 돌립니다.

## 제출

1. `make check-s03` 가 6/6 인지 봅니다.
2. 커밋하고 자기 포크에 올립니다.

```bash
git add src/finrag/ingestion/ data/ingest_report.json results/baseline.json results/check_s03.json docs/adr/ADR-002-ingestion-graph.md
git commit -m "3회차 과제"
git push
```

3. 자기 포크 URL(`https://github.com/<계정>/finance-agentic-rag-s03`)를 디스코드에 올립니다. 포크 없이 받았으면 위 파일들을 zip 으로 묶어 올립니다.

## check-s03 가 보는 것

| 항목 | 통과 기준 |
|---|---|
| 인제스천 전체 처리 | 리포트의 문서 수가 카탈로그의 90% 이상이고, 경로별 문서 수의 합이 문서 수와 같다 (`--only` 로 몇 건만 돌린 것은 안 된다) |
| 게이트 3분기 동작 | 판정 종류가 세 가지 이상 (pass · reparse · ocr · fail 중) |
| Qdrant 포인트 | 컬렉션에 청크가 들어 있다 |
| baseline Recall@5 | `results/baseline.json` 에 숫자가 있다 |
| 유형별 분해 | 질문 유형별 성능이 5개 유형 이상 |
| ADR-002 | `docs/adr/ADR-002-ingestion-graph.md` 가 있고 빈칸(`______`)이 없다 |

## 5회차 전까지 준비할 것 — OpenAI 키

5회차(에이전트 루프)부터는 LLM 을 실제로 부릅니다. 키는 **메타코드에서 발급해 줍니다.** 직접 결제하거나 계정을 만들 것은 없습니다. 받으면 레포지토리 폴더에서 `.env.example` 을 `.env` 로 복사해 `OPENAI_API_KEY=` 뒤에 붙입니다. `.env` 는 커밋되지 않습니다. 키를 채팅이나 코드에 붙이지 마세요. 되는지 확인하는 명령은 4회차 과제 문서에 있습니다.

## 마감 뒤 강사가 올리는 것

`docs/session3/examples/` 에 ADR-002 완성본을 올립니다. 받는 법은 같습니다.

```bash
git pull upstream main
```
