#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""0회차 모델 캐시 내려받기.

    python scripts/pull_models.py            # 받고 실제로 한 번 돌려 본다
    python scripts/pull_models.py --verify   # 이미 받은 캐시만 검증
    python scripts/pull_models.py --list     # 무엇을 얼마나 받는지만 본다
    python scripts/pull_models.py --only embed   # 임베딩 모델만 (3회차. 리랭커는 4회차에)

받는 곳은 `.env` 의 HF_HOME(기본 ./models)이다. 수업 중에는 이 캐시만 보고 돌기 때문에
여기서 한 번 받아 두면 이후 회차에서 네트워크가 필요 없다.

받은 뒤 반드시 한 번 돌려 본다. 파일이 있는 것과 모델이 로드되는 것은 다르다.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

# snapshot_download 는 저장소 전체를 받는다. BGE-M3 에는 onnx/model.onnx_data 가 2.11GB
# 들어 있는데 우리는 sentence-transformers(PyTorch)로만 돌리므로 한 번도 열지 않는다.
# 빼면 받는 양이 절반 가까이 준다.
#
# 주의: *.bin 은 빼면 안 된다. BGE-M3 본 리비전에는 safetensors 가 없고 가중치가
# pytorch_model.bin 하나뿐이다(리랭커는 반대로 safetensors 뿐이다).
IGNORE = ["onnx/*", "openvino/*", "*.h5", "*.msgpack", "*.ot", "assets/*", "imgs/*", "*.png", "*.jpg"]

MODELS = [
    # (설명, HuggingFace repo, 대략 크기, 쓰는 회차)
    ("임베딩", "BAAI/bge-m3", 2.2, "3회차~"),
    ("리랭커", "BAAI/bge-reranker-v2-m3", 2.2, "4회차~"),
]


def hf_home() -> Path:
    """settings 를 쓸 수 있으면 쓰고, 아니면 .env 를 직접 읽는다."""
    raw = os.environ.get("HF_HOME")
    if not raw:
        try:
            from finrag.settings import get_settings
            raw = get_settings().hf_home
        except Exception:
            raw = "./models"
            env = ROOT / ".env"
            if env.exists():
                for line in env.read_text(encoding="utf-8", errors="replace").splitlines():
                    if line.strip().startswith("HF_HOME="):
                        raw = line.split("=", 1)[1].strip() or raw
    p = Path(raw)
    return p if p.is_absolute() else (ROOT / raw).resolve()


def size_gb(path: Path, *, follow_links: bool) -> float:
    """HF 캐시는 snapshots/ 의 심볼릭 링크가 blobs/ 의 실파일을 가리킨다.

    스냅샷 한 개의 크기를 재려면 링크를 따라가야 하고(follow_links=True),
    캐시 전체를 재려면 따라가면 안 된다. 따라가면 같은 파일을 두 번 센다
    (실제로 6.4GB 캐시가 12.8GB 로 나왔다).
    """
    total = 0
    for f in path.rglob("*"):
        try:
            if f.is_symlink():
                if follow_links and f.is_file():
                    total += f.stat().st_size
            elif f.is_file():
                total += f.stat().st_size
        except OSError:
            continue
    return total / 1024**3


def pull(repo: str) -> Path:
    from huggingface_hub import snapshot_download
    local = Path(snapshot_download(repo, ignore_patterns=IGNORE))
    # 제외 규칙이 가중치까지 걸러 버리면 로드가 실패한다. 받은 뒤에 확인한다.
    if not (list(local.glob("*.safetensors")) or list(local.glob("*.bin"))):
        print("   가중치 파일이 없습니다. 제외 없이 다시 받습니다")
        local = Path(snapshot_download(repo))
    return local


def verify(repo: str) -> str:
    """로드해서 실제로 한 번 돌린다. 값이 이상하면 캐시가 깨진 것이다."""
    if "rerank" in repo:
        from sentence_transformers import CrossEncoder
        m = CrossEncoder(repo, max_length=512)
        pairs = [("적금을 중도해지하면 이율이 어떻게 되나요?",
                  "제10조(중도해지이율) 만기일 이전에 해지할 경우 가입일 당시 중도해지이율을 적용합니다."),
                 ("적금을 중도해지하면 이율이 어떻게 되나요?",
                  "제3조(가입대상) 실명의 개인으로 하며 1인 1계좌에 한합니다.")]
        s = m.predict(pairs)
        if not s[0] > s[1]:
            return f"X 관련 조항의 점수가 더 낮습니다 {s[0]:.3f} vs {s[1]:.3f}"
        return f"O 관련 조항 {s[0]:.3f} > 무관 조항 {s[1]:.3f}"

    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer(repo)
    v = m.encode(["중도해지이율", "중도상환수수료"], normalize_embeddings=True)
    if v.shape[1] != 1024:
        return f"X 차원이 {v.shape[1]} 입니다(1024 이어야 합니다)"
    return f"O {v.shape[1]}차원 · 코사인 {float(v[0] @ v[1]):.3f}"


def main() -> int:
    ap = argparse.ArgumentParser(description="모델 캐시 내려받기")
    ap.add_argument("--verify", action="store_true", help="받지 않고 검증만 한다")
    ap.add_argument("--list", action="store_true", help="목록만 보여준다")
    ap.add_argument("--offline", action="store_true",
                    help="네트워크를 끊고 캐시만으로 뜨는지 본다(수업 당일 상태 재현)")
    ap.add_argument("--only", choices=["embed", "rerank"], default=None,
                    help="하나만 받는다. embed=임베딩(3회차), rerank=리랭커(4회차)")
    args = ap.parse_args()
    models = [m for m in MODELS if not args.only or
              (args.only == "embed" and "rerank" not in m[1]) or
              (args.only == "rerank" and "rerank" in m[1])]

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

    home = hf_home()
    os.environ["HF_HOME"] = str(home)
    home.mkdir(parents=True, exist_ok=True)

    print(f"\n캐시 위치: {home}")
    if args.list:
        for label, repo, gb, when in models:
            print(f"  {label:<6} {repo:<28} 약 {gb} GB   {when}")
        print(f"  합계 약 {sum(m[2] for m in models):.1f} GB (Wi-Fi 로 {'10~20' if len(models) == 1 else '20~40'}분)")
        print("\n  로컬 LLM(8회차 시연, 선택): ollama pull qwen3:4b   약 2.5GB")
        return 0

    # HF_HUB_OFFLINE 은 huggingface_hub 임포트 시점에 읽힌다. 임포트 전에 정해야 한다.
    if args.offline:
        os.environ["HF_HUB_OFFLINE"] = "1"
        print("오프라인 모드: 캐시에 없는 것은 받지 않습니다")

    try:
        import sentence_transformers  # noqa: F401
    except ImportError:
        print("X sentence-transformers 가 없습니다 →  uv pip install -e '.[embed]'")
        return 1

    t0 = time.perf_counter()
    for label, repo, gb, when in models:
        print(f"\n[{label}] {repo}  ({when})")
        if not args.verify:
            try:
                local = pull(repo)
            except Exception as e:
                print(f"  X 내려받기 실패: {type(e).__name__}: {e}")
                print("    사내망이라면 프록시·인증서 설정이 필요합니다. 설치 가이드 FAQ 를 보세요.")
                return 1
            print(f"  받음: {size_gb(local, follow_links=True):.2f} GB")
        try:
            print(f"  검증: {verify(repo)}")
        except Exception as e:
            print(f"  X 로드 실패: {type(e).__name__}: {e}")
            print("    캐시가 깨졌을 수 있습니다. 해당 폴더를 지우고 다시 받으세요.")
            return 1

    print(f"\n완료. {home.name}/ {size_gb(home, follow_links=False):.1f} GB · {time.perf_counter() - t0:.0f}초")
    print("다음: python scripts/check_env.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
