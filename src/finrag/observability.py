# -*- coding: utf-8 -*-
"""Langfuse 연결.

그래프가 어느 노드를 지나 얼마의 토큰과 시간을 썼는지 남긴다. 6회차 ROI 와
7회차 지연 분석이 이 기록 위에서 이뤄진다.

**키가 없으면 아무것도 만들지 않는다.** 키 없이 Langfuse 클라이언트를 만들면
"Authentication error ... Client will be disabled" 를 stderr 로 뱉는데, 수업에서
5회차 전까지는 키가 없는 것이 정상이라 그 줄이 매번 보이면 안 된다.

    from finrag.observability import callbacks
    graph.invoke(state, {"callbacks": callbacks(), ...})
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from .settings import get_settings

# 마지막으로 추적이 켜진 채 실행된 기록. check-s03 이 이 파일을 본다.
# Langfuse 서버에 다시 물어보지 않는 이유는, 확인 스크립트가 네트워크에 기대면
# 비행기 안에서 채점이 안 되기 때문이다.
MARKER = "langfuse_trace.json"


def enabled() -> bool:
    s = get_settings()
    return bool(s.langfuse_public_key and s.langfuse_secret_key)


@lru_cache
def _handler():
    """CallbackHandler 하나를 만들어 재사용한다. 실패하면 None."""
    s = get_settings()
    # langfuse SDK 는 os.environ 을 본다. .env 값을 그쪽으로 옮겨 준다.
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", s.langfuse_public_key)
    os.environ.setdefault("LANGFUSE_SECRET_KEY", s.langfuse_secret_key)
    os.environ.setdefault("LANGFUSE_HOST", s.langfuse_host)
    try:
        from langfuse.langchain import CallbackHandler
        return CallbackHandler()
    except ImportError:
        # 키는 넣었는데 패키지를 안 깔았다. 제일 흔한 경우라 따로 안내한다.
        print("[관측] langfuse 가 설치돼 있지 않습니다. 추적 없이 진행합니다.\n"
              "       설치: uv pip install --python .venv/bin/python -e \".[obs]\"")
        return None
    except Exception as e:
        # 관측이 안 된다고 파이프라인이 죽으면 안 된다. 관측은 곁다리다.
        print(f"[관측] Langfuse 연결 실패, 추적 없이 진행합니다: {type(e).__name__}: {e}")
        return None


def callbacks() -> list:
    """`config={"callbacks": callbacks()}` 로 넘긴다. 키가 없으면 빈 목록."""
    if not enabled():
        return []
    h = _handler()
    return [h] if h is not None else []


def flush(*, note: str = "") -> None:
    """버퍼를 비우고 기록을 남긴다. 스크립트가 끝나기 전에 한 번 부른다.

    Langfuse 는 배치로 보낸다. 짧은 스크립트는 다 보내기 전에 프로세스가 끝나서
    트레이스가 안 올라간 것처럼 보인다(실제로 겪는다). 끝에 flush 를 부른다.
    """
    if not enabled():
        return
    try:
        from langfuse import get_client
        get_client().flush()
    except Exception as e:
        print(f"[관측] flush 실패: {type(e).__name__}: {e}")
        return

    s = get_settings()
    out = s.results_dir / MARKER
    out.parent.mkdir(parents=True, exist_ok=True)
    prev = {}
    if out.exists():
        try:
            prev = json.loads(out.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            prev = {}
    runs = prev.get("runs", [])
    runs.append({"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "note": note})
    out.write_text(json.dumps({"host": s.langfuse_host, "runs": runs[-20:]},
                              ensure_ascii=False, indent=2), encoding="utf-8")


def marker_path() -> Path:
    return get_settings().results_dir / MARKER
