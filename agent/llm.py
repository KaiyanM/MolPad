"""LLM clients for the agent, adapted from initialize_llm.py.

Clients are built on first use, so the data tools and leaf templates can be
imported and tested without an API key.
"""

import contextvars
import os
import time
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


# Reasoning effort per call site; "" leaves the provider default. Override with AGENT_EFFORT_<SITE>.
_EFFORT_DEFAULTS = {"parse": "low", "plan": "low", "breakdown": "medium"}
_GEMINI_BUDGET = {"minimal": 0, "low": 1024, "medium": 4096, "high": 16384}

# One list per answer(): every LLM call appends {site, model, seconds, tokens...} to it.
_USAGE = contextvars.ContextVar("agent_llm_usage", default=None)


def effort_for(site: str) -> str:
    return os.getenv(f"AGENT_EFFORT_{site.upper()}", _EFFORT_DEFAULTS.get(site, "")).strip().lower()


def start_usage() -> list:
    """Start a fresh usage log for the current run and return it."""
    log = []
    _USAGE.set(log)
    return log


def usage_summary(log) -> dict:
    keys = ("input_tokens", "output_tokens", "reasoning_tokens", "seconds")
    total = {k: round(sum(c.get(k, 0) for c in log), 1) for k in keys}
    return {"calls": len(log), **total, "per_call": log}


def llm_source() -> str:
    return os.getenv("LLM_SOURCE", "OpenAI").strip()


@lru_cache(maxsize=None)
def get_llm(reasoning: bool = False, effort: str = ""):
    source = llm_source()
    key = (os.getenv({"OpenAI": "OPENAI_API_KEY", "Qwen": "QWEN_API_KEY",
                      "Gemini": "GEMINI_API_KEY"}.get(source, "")) or "").strip()
    if not key:
        raise ValueError(f"Invalid LLM source or missing API key: {source}")
    model = (_REASONING_MODELS if reasoning else _MODELS)[source]
    timeout = _REASONING_TIMEOUT if reasoning else _LLM_TIMEOUT

    if source == "Gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        extra = {"thinking_budget": _GEMINI_BUDGET[effort]} if reasoning and effort in _GEMINI_BUDGET else {}
        return ChatGoogleGenerativeAI(model=model, google_api_key=key, temperature=0.1,
                                      timeout=timeout, max_retries=_LLM_MAX_RETRIES, **extra)

    from langchain_openai import ChatOpenAI

    if source == "Qwen":
        extra = {"extra_body": {"enable_thinking": effort not in ("minimal", "none")}} if reasoning and effort else {}
        return ChatOpenAI(model=model, api_key=key, base_url=_QWEN_BASE, temperature=0.1,
                          seed=_LLM_SEED, timeout=timeout, max_retries=_LLM_MAX_RETRIES, **extra)
    if reasoning:
        # gpt-5* and the o-series reject any temperature but 1
        extra = {"reasoning_effort": effort} if effort else {}
        return ChatOpenAI(model=model, api_key=key, temperature=None, seed=None,
                          timeout=timeout, max_retries=_LLM_MAX_RETRIES, **extra)
    return ChatOpenAI(model=model, api_key=key, temperature=0.1, seed=_LLM_SEED,
                      timeout=timeout, max_retries=_LLM_MAX_RETRIES)


def _record(site, model, seconds, raw):
    log = _USAGE.get()
    if log is None:
        return {}
    meta = getattr(raw, "usage_metadata", None) or {}
    entry = {"site": site, "model": model, "seconds": round(seconds, 2),
             "input_tokens": meta.get("input_tokens", 0), "output_tokens": meta.get("output_tokens", 0),
             "reasoning_tokens": (meta.get("output_token_details") or {}).get("reasoning", 0)}
    log.append(entry)
    return entry


def ask(schema, system: str, user: str, reasoning: bool = False, site: str = "", effort: str | None = None):
    """One structured LLM call: returns an instance of the Pydantic `schema`.

    `site` names the caller in the usage log; `effort` defaults to effort_for(site).
    """
    effort = effort_for(site) if effort is None else effort
    client = get_llm(reasoning, effort if reasoning else "")
    source = llm_source()
    if source == "Gemini":
        runner = client.with_structured_output(schema, include_raw=True)
    elif source == "OpenAI" and reasoning:
        # gpt-5* reasoning models reject function tools on chat completions
        runner = client.with_structured_output(schema, method="json_schema", include_raw=True)
    else:
        runner = client.with_structured_output(schema, method="function_calling", include_raw=True)
    messages = [("system", system), ("human", user)]
    model = getattr(client, "model_name", None) or getattr(client, "model", "")
    error = None
    for _ in range(2):   # an answer that does not fit the schema is asked once more
        t0 = time.time()
        try:
            out = runner.invoke(messages)
        except Exception as exc:
            error = exc
            continue
        _record(site or schema.__name__, model, time.time() - t0, out.get("raw"))
        if out.get("parsed") is not None:
            return out["parsed"]
        error = out.get("parsing_error") or ValueError(f"no {schema.__name__} in the answer")
    raise error
