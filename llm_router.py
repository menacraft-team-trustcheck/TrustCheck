"""
══════════════════════════════════════════════════════════════════════════════
MENACRAFT TRUSTCHECK — LAYER 2: Smart Multi-Provider LLM Router
══════════════════════════════════════════════════════════════════════════════

This is the CORE ENGINE of the platform. It routes every LLM request to the
optimal provider based on task type, with automatic fallback chains and
rate-limit retry logic.

ROUTING TABLE:
  ✦ Fast Text    → Groq (llama-3.3-70b-versatile)
  ✦ Reasoning    → DeepSeek (deepseek-chat)          [fallback from Groq]
  ✦ Vision       → OpenRouter (llama-3.2-11b-vision)  [fallback: qwen2.5-vl-7b]

NO ANTHROPIC / CLAUDE DEPENDENCIES — strictly Groq + DeepSeek + OpenRouter.
══════════════════════════════════════════════════════════════════════════════
"""

import os
import time
import json
import base64
import logging
import requests
from typing import Optional, Dict, Any, List

logger = logging.getLogger("trustcheck.router")

# ─────────────────────────────────────────────────────────────
# PROVIDER CONFIGURATION
# ─────────────────────────────────────────────────────────────

PROVIDERS = {
    "groq": {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1/chat/completions",
        "env_key": "GROQ_API_KEY",
        "model": "llama-3.3-70b-versatile",
        "emoji": "⚡",
        "max_tokens": 4096,
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1/chat/completions",
        "env_key": "DEEPSEEK_API_KEY",
        "model": "deepseek-chat",
        "emoji": "🧠",
        "max_tokens": 4096,
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1/chat/completions",
        "env_key": "OPENROUTER_API_KEY",
        "model": "meta-llama/llama-3.2-11b-vision-instruct",
        "fallback_model": "qwen/qwq-32b-preview",
        "emoji": "👁️",
        "max_tokens": 4096,
    },
    "huggingface": {
        "name": "HuggingFace",
        "base_url": "https://api-inference.huggingface.co/models/",
        "env_key": "HF_API_KEY",
        "emoji": "🤗",
    },
}

# ─────────────────────────────────────────────────────────────
# API KEY HELPERS
# ─────────────────────────────────────────────────────────────

def get_api_key(provider_id: str) -> Optional[str]:
    """
    Retrieve an API key from environment variables (loaded via .env / dotenv).
    Returns None if the key is not set.
    """
    env_key = PROVIDERS[provider_id]["env_key"]
    return os.environ.get(env_key, None)


def check_provider_status() -> Dict[str, bool]:
    """
    Returns a dict mapping each provider_id → True/False depending on
    whether a valid API key is available.
    """
    return {pid: get_api_key(pid) is not None for pid in PROVIDERS}


# ─────────────────────────────────────────────────────────────
# CORE REQUEST FUNCTIONS
# ─────────────────────────────────────────────────────────────

def _call_openai_compatible(
    base_url: str,
    api_key: str,
    model: str,
    messages: List[Dict],
    max_tokens: int = 4096,
    temperature: float = 0.3,
    extra_headers: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Generic caller for any OpenAI-compatible chat completions endpoint.
    Used by Groq, DeepSeek, and OpenRouter since they all expose the
    same /chat/completions contract.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    response = requests.post(base_url, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    return response.json()


def _retry_with_backoff(fn, max_retries: int = 3, base_delay: float = 2.0):
    """
    Exponential-backoff wrapper.  Retries on 429 (rate-limit) and 5xx
    server errors.  Returns the first successful result or raises the
    last exception.
    """
    last_exc = None
    for attempt in range(max_retries):
        try:
            return fn()
        except requests.exceptions.HTTPError as e:
            last_exc = e
            status = e.response.status_code if e.response is not None else 0
            if status in (429, 500, 502, 503, 504):
                wait = base_delay * (2 ** attempt)
                time.sleep(wait)
                continue
            raise  # non-retryable HTTP error
        except requests.exceptions.ConnectionError as e:
            last_exc = e
            wait = base_delay * (2 ** attempt)
            time.sleep(wait)
            continue
    raise last_exc  # type: ignore


# ─────────────────────────────────────────────────────────────
# HIGH-LEVEL ROUTING FUNCTIONS
# ─────────────────────────────────────────────────────────────

def route_text(prompt: str, system_prompt: str = "", temperature: float = 0.3) -> str:
    """
    ✦ FAST TEXT ROUTE
    Primary   → Groq (llama-3.3-70b-versatile)
    Fallback  → DeepSeek (deepseek-chat)

    Used by: credibility.py, fact_check.py, context.py (text reasoning),
             heatmap.py (grid scoring)
    """
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    # ── Try Groq first (fastest inference) ──────────────────
    groq_key = get_api_key("groq")
    if groq_key:
        try:
            cfg = PROVIDERS["groq"]
            result = _retry_with_backoff(
                lambda: _call_openai_compatible(
                    cfg["base_url"], groq_key, cfg["model"],
                    messages, cfg["max_tokens"], temperature,
                )
            )
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            # Log failure; fall through to DeepSeek
            _log_fallback("groq", "deepseek", str(e))

    # ── Fallback: DeepSeek ──────────────────────────────────
    ds_key = get_api_key("deepseek")
    if ds_key:
        try:
            cfg = PROVIDERS["deepseek"]
            result = _retry_with_backoff(
                lambda: _call_openai_compatible(
                    cfg["base_url"], ds_key, cfg["model"],
                    messages, cfg["max_tokens"], temperature,
                )
            )
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            _log_fallback("deepseek", "none", str(e))

    return "[ERROR] No text LLM provider available. Please set GROQ_API_KEY or DEEPSEEK_API_KEY."


def route_vision(
    prompt: str,
    image_b64: str,
    system_prompt: str = "",
    temperature: float = 0.3,
) -> str:
    """
    ✦ VISION ROUTE
    Primary   → OpenRouter (llama-3.2-11b-vision-instruct:free)
    Fallback  → OpenRouter (qwen2.5-vl-7b-instruct:free)

    Used by: context.py, heatmap.py
    """
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image_b64}",
                },
            },
        ],
    })

    or_key = get_api_key("openrouter")
    if not or_key:
        return "[ERROR] No Vision LLM provider available. Please set OPENROUTER_API_KEY."

    cfg = PROVIDERS["openrouter"]
    extra_headers = {
        "HTTP-Referer": "https://menacraft-trustcheck.app",
        "X-Title": "MenaCraft TrustCheck",
    }

    # ── Try primary vision model ─────────────────────────────
    try:
        result = _retry_with_backoff(
            lambda: _call_openai_compatible(
                cfg["base_url"], or_key, cfg["model"],
                messages, cfg["max_tokens"], temperature, extra_headers,
            )
        )
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        _log_fallback("openrouter-primary", "openrouter-fallback", str(e))

    # ── Fallback vision model ────────────────────────────────
    try:
        result = _retry_with_backoff(
            lambda: _call_openai_compatible(
                cfg["base_url"], or_key, cfg["fallback_model"],
                messages, cfg["max_tokens"], temperature, extra_headers,
            )
        )
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        _log_fallback("openrouter-fallback", "none", str(e))

    return "[ERROR] All vision models failed. Please try again later."


def route_reasoning(prompt: str, system_prompt: str = "") -> str:
    """
    ✦ DEEP REASONING ROUTE
    Primary   → DeepSeek (deepseek-chat)  — optimised for chain-of-thought
    Fallback  → Groq (llama-3.3-70b)

    Used by: credibility.py (complex source analysis), fact_check.py (claim eval)
    """
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    # ── Try DeepSeek first (best for reasoning) ─────────────
    ds_key = get_api_key("deepseek")
    if ds_key:
        try:
            cfg = PROVIDERS["deepseek"]
            result = _retry_with_backoff(
                lambda: _call_openai_compatible(
                    cfg["base_url"], ds_key, cfg["model"],
                    messages, cfg["max_tokens"], 0.2,
                )
            )
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            _log_fallback("deepseek", "groq", str(e))

    # ── Fallback: Groq ──────────────────────────────────────
    groq_key = get_api_key("groq")
    if groq_key:
        try:
            cfg = PROVIDERS["groq"]
            result = _retry_with_backoff(
                lambda: _call_openai_compatible(
                    cfg["base_url"], groq_key, cfg["model"],
                    messages, cfg["max_tokens"], 0.2,
                )
            )
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            _log_fallback("groq", "none", str(e))

    return "[ERROR] No reasoning LLM provider available. Please set DEEPSEEK_API_KEY or GROQ_API_KEY."


# ─────────────────────────────────────────────────────────────
# HUGGING FACE INFERENCE HELPER
# ─────────────────────────────────────────────────────────────

def call_huggingface(
    model_id: str,
    image_bytes: bytes,
    task: str = "image-classification",
) -> Any:
    """
    Calls the Hugging Face Inference API for image-based tasks
    (e.g., AI-generated image detection).

    Handles 503 "model loading" responses by waiting and retrying.
    Returns the parsed JSON response or an error string.
    """
    hf_key = get_api_key("huggingface")
    if not hf_key:
        return "[ERROR] HuggingFace API key not set. Please set HF_API_KEY."

    url = f"{PROVIDERS['huggingface']['base_url']}{model_id}"
    headers = {"Authorization": f"Bearer {hf_key}"}

    # Custom retry loop for HF (handles 503 model-loading specially)
    max_retries = 4
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, data=image_bytes, timeout=90)

            # Model is loading — HF returns 503 with estimated_time
            if response.status_code == 503:
                try:
                    body = response.json()
                    wait_time = min(body.get("estimated_time", 20), 30)
                except Exception:
                    wait_time = 15
                logger.info(f"HF model {model_id} is loading, waiting {wait_time:.0f}s (attempt {attempt+1})")
                time.sleep(wait_time)
                continue

            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else 0
            if status in (429, 500, 502, 504):
                time.sleep(3 * (attempt + 1))
                continue
            return f"[ERROR] HuggingFace API error (HTTP {status}): {str(e)[:200]}"
        except requests.exceptions.ConnectionError:
            time.sleep(3)
            continue
        except Exception as e:
            return f"[ERROR] HuggingFace API call failed: {str(e)[:200]}"

    return f"[ERROR] HuggingFace model {model_id} did not respond after {max_retries} attempts."


# ─────────────────────────────────────────────────────────────
# IMAGE ENCODING UTILITY
# ─────────────────────────────────────────────────────────────

def encode_image_to_base64(image_bytes: bytes) -> str:
    """Encode raw image bytes to a base64 string for vision model APIs."""
    return base64.b64encode(image_bytes).decode("utf-8")


# ─────────────────────────────────────────────────────────────
# INTERNAL LOGGING
# ─────────────────────────────────────────────────────────────

# In-memory log buffer for the /status endpoint
_fallback_logs: List[str] = []

def _log_fallback(from_provider: str, to_provider: str, error: str):
    """Log provider fallback events to Python logger + in-memory buffer."""
    msg = f"[{from_provider}] failed -> falling back to [{to_provider}]: {error[:200]}"
    logger.warning(msg)
    _fallback_logs.append(msg)
    # Keep the buffer bounded
    if len(_fallback_logs) > 100:
        _fallback_logs.pop(0)


def get_fallback_logs() -> List[str]:
    """Return recent fallback log entries."""
    return list(_fallback_logs)
