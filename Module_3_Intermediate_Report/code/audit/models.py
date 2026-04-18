"""Unified generate(messages, **kwargs) abstraction across providers.

Supported providers (detected from model_id prefix or configured endpoint):
  - openai:*       -> OpenAI Chat Completions API
  - groq:*         -> Groq OpenAI-compatible endpoint

Features:
  - Token-bucket rate limiting per provider
  - Exponential-backoff retry on 429 / 5xx
  - Per-request client-side idempotency key derived from (model, prompt, seed)
  - File-based response cache keyed on the idempotency key so reruns are free

All transport is stdlib urllib, no third-party dependencies required.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path


BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

PROVIDER_ENDPOINTS = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "groq":   "https://api.groq.com/openai/v1/chat/completions",
}

PROVIDER_ENVVARS = {
    "openai": "OPENAI_API_KEY",
    "groq":   "GROQ_API_KEY",
}


@dataclass
class ModelSpec:
    provider: str          # "openai" | "groq"
    model_id: str          # e.g. "gpt-4o-mini", "llama-3.3-70b-versatile"
    display_name: str      # pretty label for reports
    max_tokens: int = 512
    temperature: float = 0.2
    supports_json_format: bool = True


# -----------------------------------------------------------------------------
# Rate limiting
# -----------------------------------------------------------------------------

class TokenBucket:
    def __init__(self, rate_per_sec: float, capacity: float | None = None):
        self.rate = rate_per_sec
        self.capacity = capacity or max(1.0, rate_per_sec)
        self._tokens = self.capacity
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def take(self, n: float = 1.0) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                self._tokens = min(self.capacity, self._tokens + (now - self._last) * self.rate)
                self._last = now
                if self._tokens >= n:
                    self._tokens -= n
                    return
                wait = (n - self._tokens) / self.rate
            time.sleep(min(wait, 1.0))


# Conservative defaults for free tiers
_BUCKETS: dict[str, TokenBucket] = {
    "openai": TokenBucket(rate_per_sec=5.0),   # ~300 RPM; gpt-4o-mini allows much more
    "groq":   TokenBucket(rate_per_sec=0.5),   # ~30 RPM free tier, per model
}


# -----------------------------------------------------------------------------
# Cache
# -----------------------------------------------------------------------------

class ResponseCache:
    def __init__(self, dir_: str | Path):
        self.dir = Path(dir_)
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.dir / f"{key}.json"

    def get(self, key: str) -> dict | None:
        p = self._path(key)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text())
        except Exception:
            return None

    def put(self, key: str, value: dict) -> None:
        p = self._path(key)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(value))
        tmp.rename(p)


def idempotency_key(model_id: str, messages: list[dict], seed: int, temperature: float) -> str:
    payload = json.dumps(
        {"m": model_id, "msgs": messages, "s": seed, "t": temperature},
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


# -----------------------------------------------------------------------------
# HTTP
# -----------------------------------------------------------------------------

def _api_key(provider: str) -> str:
    env = PROVIDER_ENVVARS[provider]
    key = os.environ.get(env)
    if not key:
        raise RuntimeError(f"{env} not set in environment")
    return key


class LLMError(RuntimeError):
    pass


def _post_json(provider: str, payload: dict, timeout: int = 120) -> dict:
    url = PROVIDER_ENDPOINTS[provider]
    hdrs = {
        "Authorization": f"Bearer {_api_key(provider)}",
        "Content-Type": "application/json",
        "User-Agent": BROWSER_UA,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=hdrs, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def generate(
    *,
    spec: ModelSpec,
    messages: list[dict],
    seed: int = 42,
    cache: ResponseCache | None = None,
    max_retries: int = 5,
    return_json: bool = False,
) -> dict:
    """Call a chat completion endpoint and return the raw provider response.

    The returned dict always has:
        - "text":          the assistant message string
        - "model_id":      provider-returned model id (may differ from requested)
        - "provider":      "openai" | "groq"
        - "cached":        True if served from cache
        - "usage":         provider usage dict (if present)
    """
    key = idempotency_key(spec.model_id, messages, seed, spec.temperature)
    if cache:
        hit = cache.get(key)
        if hit is not None:
            hit["cached"] = True
            return hit

    payload: dict = {
        "model": spec.model_id,
        "messages": messages,
        "max_tokens": spec.max_tokens,
        "temperature": spec.temperature,
    }
    if return_json and spec.supports_json_format:
        payload["response_format"] = {"type": "json_object"}

    _BUCKETS[spec.provider].take()

    err: Exception | None = None
    for attempt in range(max_retries):
        try:
            resp = _post_json(spec.provider, payload)
            break
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="ignore")
            except Exception:
                pass
            if e.code in (429, 500, 502, 503, 504):
                wait = (2 ** attempt) + random.random()
                time.sleep(min(wait, 30))
                err = LLMError(f"{spec.provider}/{spec.model_id} {e.code}: {body[:200]}")
                continue
            raise LLMError(f"{spec.provider}/{spec.model_id} {e.code}: {body[:300]}") from e
        except Exception as e:  # noqa: BLE001
            wait = (2 ** attempt) + random.random()
            time.sleep(min(wait, 20))
            err = e
            continue
    else:
        raise LLMError(f"Exhausted retries for {spec.provider}/{spec.model_id}: {err}")

    text = ""
    try:
        text = resp["choices"][0]["message"]["content"] or ""
    except Exception:
        text = json.dumps(resp)[:500]

    out = {
        "text": text,
        "model_id": resp.get("model", spec.model_id),
        "provider": spec.provider,
        "cached": False,
        "usage": resp.get("usage", {}),
    }
    if cache:
        cache.put(key, out)
    return out
