# -*- coding: utf-8 -*-
"""LLM 팩토리.

프로바이더를 코드에 박지 않는다. `.env` 의 "provider:model" 문자열만 바꾸면
OpenAI → Anthropic → 로컬 Ollama 로 옮겨갈 수 있어야 한다(8회차 교체 시연의 근거).

키가 없으면 결정적 가짜 모델로 떨어진다. 채점 스크립트와 CI 가 키 없이도
그래프 전체를 돌려 볼 수 있어야 하기 때문이다.
"""
from __future__ import annotations

import json
from typing import Any

from langchain_core.language_models import BaseChatModel

from .settings import get_settings

# 키 없이 돌릴 때 노드별로 돌려줄 고정 응답. 실제 LLM 이 아니라 "그래프가 도는지"만 본다.
FAKE_RESPONSES: dict[str, str] = {
    "rewrite": "{}",
    "grade": '{"verdict": "sufficient", "reason": "가짜 모델 응답"}',
    "selfquery": '{"filters": {}, "rewritten_query": ""}',
    "answer": "[가짜 LLM] 키가 설정되지 않아 답변을 생성하지 않았습니다. 검색된 근거만 확인하세요.",
    "extract": "{}",
    "judge": '{"basis_match": 0, "numeric_ok": 0, "no_extra_claim": 0, "reason": "가짜 모델"}',
}


class DeterministicFakeChat(BaseChatModel):
    """키 없이 그래프를 돌리기 위한 결정적 모델.

    LangChain 의 FakeListChatModel 은 호출 순서대로 응답을 소비해서 그래프가
    분기하면 어긋난다. 여기서는 역할(role)로 응답을 고르므로 순서에 영향받지 않는다.
    """

    role: str = "answer"

    @property
    def _llm_type(self) -> str:
        return "deterministic-fake"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        from langchain_core.messages import AIMessage
        from langchain_core.outputs import ChatGeneration, ChatResult
        text = FAKE_RESPONSES.get(self.role, FAKE_RESPONSES["answer"])
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])

    def with_structured_output(self, schema, **kwargs):  # type: ignore[override]
        """구조화 출력도 흉내 낸다. 스키마 기본값으로 채운 인스턴스를 돌려준다."""
        from langchain_core.runnables import RunnableLambda

        def _fake(_: Any):
            raw = FAKE_RESPONSES.get(self.role, "{}")
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {}
            if hasattr(schema, "model_validate"):
                try:
                    return schema.model_validate(data)
                except Exception:
                    return schema.model_construct()
            return data

        return RunnableLambda(_fake)


def has_credentials(spec: str) -> bool:
    """그 모델 문자열을 실제로 호출할 수 있는지 본다.

    "키가 하나라도 있으면 된다"가 아니다. openai:* 를 쓰는데 anthropic 키만 있으면
    호출은 실패한다. 프로바이더별로 따로 본다.
    """
    s = get_settings()
    provider = spec.split(":", 1)[0]
    return {
        "openai": bool(s.openai_api_key),
        "anthropic": bool(s.anthropic_api_key),
        "ollama": True,          # 로컬 서버라 키가 없다. 연결 실패는 호출 시점에 드러난다.
    }.get(provider, False)


def get_llm(role: str = "answer", *, size: str = "main", temperature: float = 0.0,
            force_real: bool = False) -> BaseChatModel:
    """역할별 모델을 준다.

    role  : rewrite / grade / selfquery / answer / extract / judge (가짜 모델 응답 선택용)
    size  : main | small | local
    """
    s = get_settings()
    spec = {"main": s.llm_model_main, "small": s.llm_model_small, "local": s.llm_model_local}[size]

    if spec.startswith("fake") or not has_credentials(spec):
        if force_real:
            raise RuntimeError(
                f"'{spec}' 를 쓰려면 자격증명이 필요합니다. .env 의 API 키를 채우세요.")
        return DeterministicFakeChat(role=role)

    from langchain.chat_models import init_chat_model
    kwargs: dict[str, Any] = {"temperature": temperature}
    if spec.startswith("ollama:"):
        kwargs["base_url"] = s.ollama_base_url
    return init_chat_model(spec, **kwargs)


def is_fake(llm: BaseChatModel) -> bool:
    return isinstance(llm, DeterministicFakeChat)
