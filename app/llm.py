from langchain_openai import ChatOpenAI

from app.config import get_settings


def get_supervisor_llm(temperature: float = 0.0) -> ChatOpenAI:
    s = get_settings()
    return ChatOpenAI(
        model=s.supervisor_model,
        api_key=s.supervisor_api_key,
        base_url=s.llm_base_url,
        temperature=temperature,
        timeout=s.llm_timeout,
        max_retries=2,
    )


def get_worker_llm(temperature: float = 0.0) -> ChatOpenAI:
    s = get_settings()
    return ChatOpenAI(
        model=s.worker_model,
        api_key=s.worker_api_key,
        base_url=s.llm_base_url,
        temperature=temperature,
        timeout=s.llm_timeout,
        max_retries=2,
    )
