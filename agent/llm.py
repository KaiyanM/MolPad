"""LLM clients for the agent, adapted from initialize_llm.py.

Clients are built on first use, so the data tools and leaf templates can be
imported and tested without an API key.
"""

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

# The model each provider runs.
_MODELS = {
    "OpenAI": "gpt-4o-mini-2024-07-18",
    "Qwen": "Qwen-Flash",
    "Gemini": "gemini-3.5-flash-lite",
}
# A second, higher-tier client for work the cheap model is measurably bad at.
_REASONING_MODELS = {
    "OpenAI": "gpt-5.6-luna",
    "Qwen": "Qwen3.8-Flash",
    "Gemini": "gemini-3.5-flash",
}
_QWEN_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"

_LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "60"))
_REASONING_TIMEOUT = 300.0
_LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "1"))
_LLM_SEED = int(os.getenv("LLM_SEED", "7"))

# Which client makes the tree judgements (N0-N6): "basic" or "reasoning".
# On the 43 cheese questions the basic model reached the expected leaf for 19 and
# the reasoning model for 28 (agent/tests/eval_trace.py), so reasoning is the default.
JUDGE_TIER = os.getenv("AGENT_JUDGE_TIER", "reasoning").strip().lower()


def llm_source() -> str:
    return os.getenv("LLM_SOURCE", "OpenAI").strip()


@lru_cache(maxsize=None)
def get_llm(reasoning: bool = False):
    source = llm_source()
    key = (os.getenv({"OpenAI": "OPENAI_API_KEY", "Qwen": "QWEN_API_KEY",
                      "Gemini": "GEMINI_API_KEY"}.get(source, "")) or "").strip()
    if not key:
        raise ValueError(f"Invalid LLM source or missing API key: {source}")
    model = (_REASONING_MODELS if reasoning else _MODELS)[source]
    timeout = _REASONING_TIMEOUT if reasoning else _LLM_TIMEOUT

    if source == "Gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model=model, google_api_key=key, temperature=0.1,
                                      timeout=timeout, max_retries=_LLM_MAX_RETRIES)

    from langchain_openai import ChatOpenAI

    if source == "Qwen":
        return ChatOpenAI(model=model, api_key=key, base_url=_QWEN_BASE, temperature=0.1,
                          seed=_LLM_SEED, timeout=timeout, max_retries=_LLM_MAX_RETRIES)
    if reasoning:
        # gpt-5* and the o-series reject any temperature but 1
        return ChatOpenAI(model=model, api_key=key, temperature=None, seed=None,
                          timeout=timeout, max_retries=_LLM_MAX_RETRIES)
    return ChatOpenAI(model=model, api_key=key, temperature=0.1, seed=_LLM_SEED,
                      timeout=timeout, max_retries=_LLM_MAX_RETRIES)


def ask(schema, system: str, user: str, reasoning: bool = False):
    """One structured LLM call: returns an instance of the Pydantic `schema`."""
    client = get_llm(reasoning)
    source = llm_source()
    if source == "Gemini":
        runner = client.with_structured_output(schema)
    elif source == "OpenAI" and reasoning:
        # gpt-5* reasoning models reject function tools on chat completions
        runner = client.with_structured_output(schema, method="json_schema")
    else:
        runner = client.with_structured_output(schema, method="function_calling")
    messages = [("system", system), ("human", user)]
    try:
        return runner.invoke(messages)
    except Exception:  # most often an answer that does not fit the schema; try once more
        return runner.invoke(messages)
