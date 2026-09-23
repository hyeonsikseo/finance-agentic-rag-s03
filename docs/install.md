# 설치와 준비물 받기

2회차와 거의 같고, 4번(모델)과 5번(임베딩 스냅샷)이 새로 생겼습니다. **4번은 2.2GB 를 다운로드해서 10~20분 걸립니다.** 수업 전날까지 끝내 두고, 마지막 6번의 확인 줄을 디스코드에 남겨 주세요.

## 1. 준비물 두 가지, git 과 uv

1·2회차에 했으면 건너뜁니다.

**Mac**

```bash
xcode-select --install
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell)**

```powershell
winget install --id Git.Git -e
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

설치가 끝나면 터미널을 닫고 새로 엽니다. 확인은 `git --version`, `uv --version`.

## 2. 레포지토리 받기

2회차처럼 포크를 먼저 합니다.

1. 브라우저에서 https://github.com/hyeonsikseo/finance-agentic-rag-s03 를 열고 오른쪽 위 **Fork** 를 누릅니다.
2. 그 레포지토리를 받습니다. `<계정>` 자리에 자기 GitHub 계정을 넣습니다.

```bash
git clone https://github.com/<계정>/finance-agentic-rag-s03.git
cd finance-agentic-rag-s03
git remote add upstream https://github.com/hyeonsikseo/finance-agentic-rag-s03.git
```

포크가 막히면 원본을 그대로 받고 과제는 zip 으로 냅니다.

## 3. 2회차 폴더에서 문서와 OCR 캐시 가져오기

2회차 폴더(`finance-agentic-rag-s02`)가 옆에 있으면 다운로드한 문서와 OCR 캐시를 복사합니다. 폴더가 다른 곳에 있으면 경로만 바꿉니다.

**Mac**

```bash
cp -R ../finance-agentic-rag-s02/data/raw data/
cp -R ../finance-agentic-rag-s02/data/ocr_cache data/
```

**Windows (PowerShell)**

```powershell
Copy-Item -Recurse ..\finance-agentic-rag-s02\data\raw data\
Copy-Item -Recurse ..\finance-agentic-rag-s02\data\ocr_cache data\
```

2회차 폴더가 없으면 문서는 7번에서 새로 다운로드하고, OCR 캐시는 디스코드의 `ocr_cache.zip` 을 `data` 폴더 안에 풉니다(2회차 안내와 같습니다).

## 4. 파이썬과 패키지 설치

**Mac**

```bash
make setup
```

**Windows (PowerShell)**

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
```

2회차의 2~3분보다 오래 걸립니다. 임베딩 모델을 돌리는 torch 가 들어가서 Mac 은 5분, Windows 는 10분쯤 봅니다. 파이썬 3.12 가 없으면 uv 가 받아 옵니다.

## 5. 임베딩 모델 받기 — 2.2GB, 10~20분

문서와 질문을 숫자 벡터로 바꾸는 모델(BGE-M3)입니다. 청크를 벡터 DB 에 넣고 검색할 때 씁니다. 레포지토리 안의 `models` 폴더에 받고, 받은 뒤 실제로 한 번 돌려 봅니다.

**Mac**

```bash
make models
```

**Windows (PowerShell)**

```powershell
$env:HF_HOME = ".\models"
.venv\Scripts\python scripts\pull_models.py --only embed
```

마지막에 `검증: O 1024차원 · 코사인 0.716` 처럼 O 가 나오면 된 것입니다. 회사 네트워크에서 멈추면 휴대폰 핫스팟으로 바꿔 다시 돌립니다. 이미 받은 부분은 이어서 받습니다.

## 6. 임베딩 스냅샷 받기 — 13MB

강사가 청크 3,700개를 미리 임베딩해 둔 파일입니다. 이게 있으면 `make index` 가 10초에 끝나고, 없으면 각자 25분(M2 기준)을 씁니다. 본문이 아니라 숫자만 들어 있어서 GitHub Release 로 나눕니다.

**Mac**

```bash
make embeddings
```

**Windows (PowerShell)**

```powershell
New-Item -ItemType Directory -Force data\embeddings | Out-Null
Invoke-WebRequest -Uri https://github.com/hyeonsikseo/finance-agentic-rag-s03/releases/download/s03/BAAI_bge-m3.npz -OutFile data\embeddings\BAAI_bge-m3.npz
```

`data/embeddings/BAAI_bge-m3.npz` 가 13MB 로 있으면 됩니다.

## 7. 문서 다운로드

3번에서 복사했으면 이미 있는 파일은 건너뛰므로 몇 초면 끝납니다. 복사하지 않았으면 약 5분 걸립니다.

**Mac**: `make download`   **Windows**: `.venv\Scripts\python data\download_corpus.py`

## 8. 되는지 확인

**Mac**

```bash
make test
```

**Windows (PowerShell)**

```powershell
.venv\Scripts\python -m pytest -q
```

지금은 **실패가 정상**입니다. 채울 함수 두 개가 비어 있어서 3회차 테스트 12개가 `NotImplementedError` 로 실패합니다. 마지막 줄이 `12 failed, 19 passed, 4 skipped` (문서를 아직 안 받았으면 `11 failed, 17 passed, 7 skipped`) 이고 `error` 가 없으면 설치는 된 것입니다. **이 마지막 줄과 5번의 `검증:` 줄을 디스코드에 적어 주세요.**

## 막힐 때

| 증상 | 이유 | 이렇게 합니다 |
|---|---|---|
| `uv: command not found` | 설치 뒤 터미널을 새로 안 열었습니다 | 터미널을 닫고 새로 엽니다 |
| torch 설치가 실패한다 (Intel Mac, 오래된 Windows) | 그 기종용 최신 torch 가 없습니다 | `uv pip install --python .venv/bin/python "torch==2.2.2"` 를 먼저 하고 4번을 다시 합니다 |
| 리눅스에서 설치가 2GB 를 넘게 받는다 | 기본 torch 가 GPU 판입니다 | `uv pip install --python .venv/bin/python torch --index-url https://download.pytorch.org/whl/cpu` 를 먼저 하고 4번을 다시 합니다 |
| SSL 에러가 나거나 다운로드가 멈춘다 | 회사 네트워크의 보안 검사 | 휴대폰 핫스팟으로 바꿔 다시 돌립니다 |
| 모델을 받다가 끊겼다 | 네트워크 | 같은 명령을 다시 돌립니다. 받은 부분은 이어서 받습니다 |
| `임베딩 모델 BAAI/bge-m3 이 ./models 에 없습니다` | 5번을 안 했거나 다른 폴더에 받았습니다 | 레포지토리 폴더에서 5번을 다시 합니다 |
| `make index` 가 25분째 돌고 있다 | 6번 스냅샷이 없거나 이름이 다릅니다 | 멈추고(Ctrl+C) `data/embeddings/BAAI_bge-m3.npz` 가 있는지 봅니다 |
| Qdrant `already accessed` 에러 | 노트북이나 다른 터미널이 Qdrant 를 잡고 있습니다 | 그쪽을 닫고 다시 돌립니다 |
| Windows 에서 `make` 가 없다 | 원래 없습니다 | 위의 PowerShell 명령을 씁니다 |
| `make test` 에 `error` 가 있다 | 패키지가 덜 깔렸습니다 | 4번을 다시 합니다. 그래도 그러면 에러 줄을 채팅에 붙입니다 |

## 오늘 못 받았으면

노트북, 실습 1·2·3, `make ingest-sample` 은 모델 없이 됩니다. 모델이 필요한 것은 `make index` 와 `make baseline` 뿐이니, 그 둘은 강사 화면으로 따라오고 수업 뒤에 받아서 돌립니다.
