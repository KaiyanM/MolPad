"""Initialize LLM instance for agent orchestrator."""

import os
from pathlib import Path
from dotenv import load_dotenv


# Load environment variables
# Get agent directory (two levels up from this file: agent_orchestrator/llm/ -> agent/)
agent_dir = Path(__file__).parent.parent.parent
env_path = agent_dir / ".env"
load_dotenv(env_path)
openai_api_key = (os.getenv('OPENAI_API_KEY') or '').strip()
qwen_api_key = (os.getenv('QWEN_API_KEY') or '').strip()
gemini_api_key = (os.getenv('GEMINI_API_KEY') or '').strip()
llm_source = os.getenv('LLM_SOURCE', 'OpenAI').strip()

# The model each provider runs. 
_MODELS = {
    "OpenAI": "gpt-4o-mini-2024-07-18",
    "Qwen": "Qwen-Flash",
    "Gemini": "gemini-3.5-flash-lite",
}

#-----------------
# basic llm
#-----------------

_LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "60"))
_LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "1"))
_LLM_SEED = int(os.getenv("LLM_SEED", "7"))

if llm_source == 'Qwen' and qwen_api_key:
    from .json_wrapper import QwenJsonWrapper

    llm = QwenJsonWrapper(
        model=_MODELS["Qwen"],
        openai_api_key=qwen_api_key,
        openai_api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
        temperature=0.1,
        seed=_LLM_SEED,
        timeout=_LLM_TIMEOUT,
        max_retries=_LLM_MAX_RETRIES,
    )

elif llm_source == "Gemini" and gemini_api_key:
    from langchain_google_genai import ChatGoogleGenerativeAI

    llm = ChatGoogleGenerativeAI(
        model=_MODELS["Gemini"],
        google_api_key=gemini_api_key,
        temperature=0.1,
        timeout=_LLM_TIMEOUT,
        max_retries=_LLM_MAX_RETRIES,
    )

elif llm_source == "OpenAI" and openai_api_key:
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model=_MODELS["OpenAI"],
        temperature=0.1,
        seed=_LLM_SEED,
        api_key=openai_api_key,
        timeout=_LLM_TIMEOUT,
        max_retries=_LLM_MAX_RETRIES,
    )
else:
    raise ValueError(f"Invalid LLM source: {llm_source}")

#-----------------
# reasoning llm
#-----------------
# A second, higher-tier client for work the cheap model is measurably bad at.
_REASONING_MODELS = {
    "OpenAI": "gpt-5.6-luna",
    "Qwen": "Qwen3.8-Flash",
    "Gemini": "gemini-3.5-flash",
}
_REASONING_MODEL = _REASONING_MODELS[llm_source]
_REASONING_TIMEOUT = 300.0

# Built here beside `llm`, eagerly and with no extra configuration: it uses the
# same API key as the tier above, so if `llm` could be built this can too.
if llm_source == 'Qwen':
    llm_reasoning = QwenJsonWrapper(
        model=_REASONING_MODEL,
        openai_api_key=qwen_api_key,
        openai_api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
        temperature=0.1,
        seed=_LLM_SEED,
        timeout=_REASONING_TIMEOUT,
        max_retries=_LLM_MAX_RETRIES,
    )

elif llm_source == "Gemini":
    llm_reasoning = ChatGoogleGenerativeAI(
        model=_REASONING_MODEL,
        google_api_key=gemini_api_key,
        temperature=0.1,
        timeout=_REASONING_TIMEOUT,
        max_retries=_LLM_MAX_RETRIES,
    )

else:
    llm_reasoning = ChatOpenAI(
        model=_REASONING_MODEL,
        api_key=openai_api_key,
        # gpt-5* and the o-series reject any temperature but 1 
        temperature=None,
        seed=None,
        timeout=_REASONING_TIMEOUT,
        max_retries=_LLM_MAX_RETRIES,
    )
