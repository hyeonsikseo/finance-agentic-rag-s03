.PHONY: help setup download models embeddings notebook test ingest-sample ingest index baseline chunk chunk-sample profile
PY := .venv/bin/python
export HF_HOME := ./models
EMB_URL := https://github.com/hyeonsikseo/finance-agentic-rag-s03/releases/download/s03/BAAI_bge-m3.npz
SAMPLE := --only hana_credit_terms_2009 --only fss_deposit_terms_2024_pdf --only knia_3500_scan --only kakao_deposit_terms_2024 --only hanacard_std_2017 --only law_silson_std_hwp

help:
	@echo "make setup       파이썬 3.12 와 패키지 설치 (5~10분. torch 가 들어갑니다)"
	@echo "make download    문서 다운로드 (2회차 폴더에서 복사했으면 몇 초)"
	@echo "make models      임베딩 모델 BGE-M3 다운로드 (2.2GB, 10~20분. 수업 전에)"
	@echo "make embeddings  강사가 만든 임베딩 스냅샷 다운로드 (13MB. 없으면 make index 가 25분)"
	@echo "make notebook    LangGraph 노트북 열기 (수업 1~2부, 실습 1)"
	@echo "make test        자동 채점. 2회차 21개 + 3회차 검사 (채우기 전에는 실패가 정상)"
	@echo "make ingest-sample  문서 6건만 그래프에 통과시켜 본다 (8초. 결과는 *_sample 파일에 따로)"
	@echo "make ingest      문서 51건 전부 → data/chunks/chunks.jsonl + data/ingest_report.json (약 6분)"
	@echo "make index       청크를 임베딩(스냅샷 재사용)해서 Qdrant 에 넣는다 (10초)"
	@echo "make baseline    골든셋 40문항으로 Dense 검색 성능 측정 → results/baseline.json (30초)"
	@echo "make check-s03   3회차 확인 → results/check_s03.json (이 파일을 제출)"

setup:
	uv venv --python 3.12 .venv
	uv pip install --python $(PY) -r requirements.txt

download:
	$(PY) data/download_corpus.py

models:
	$(PY) scripts/pull_models.py --only embed

embeddings:
	mkdir -p data/embeddings
	curl -L --fail -o data/embeddings/BAAI_bge-m3.npz $(EMB_URL)
	@ls -la data/embeddings/BAAI_bge-m3.npz

notebook:
	$(PY) -m jupyter lab notebooks/s03_langgraph.ipynb

test:
	$(PY) -m pytest -q

ingest-sample:
	$(PY) pipelines/ingest.py --no-checkpoint $(SAMPLE)

ingest:
	$(PY) pipelines/ingest.py

index:
	$(PY) scripts/build_index.py

baseline:
	$(PY) pipelines/baseline.py

check-s%:
	$(PY) scripts/check_session.py $*

# ── 2회차 명령. 그대로 남겨 둡니다 ──
chunk-sample:
	$(PY) pipelines/chunk_only.py --verbose $(SAMPLE)

chunk:
	$(PY) pipelines/chunk_only.py --verbose

profile:
	$(PY) scripts/profile_docs.py
