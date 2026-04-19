"""Unified generate(messages, **kwargs) abstraction across providers.

Supported providers (detected from model_id prefix or configured endpoint):
  - openai:*       -> OpenAI Chat Completions API
  - groq:*         -> Groq OpenAI-compatible endpoint

Features:
  - Token-bucket rate limiting per (provider, model) — both RPM and TPM
  - Exponential-backoff retry on 5xx; 429 honours Retry-After / Groq body hint
  - Per-request client-side idempotency key derived from (model, prompt, seed)
  - File-based response cache keyed on the idempotency key so reruns are free

All transport is stdlib urllib, no third-party dependencies required.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import re
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
    """Sliding 60s window bucket enforcing RPM and (optionally) TPM together.

    Replaces the previous provider-shared leaky bucket. Buckets are now keyed
    per (provider, model) so one model's TPM cannot starve another's; the
    annotator has its own bucket separate from main-model generation.
    """

    def __init__(self, rpm: int, tpm: int | None = None):
        self.rpm = rpm
        self.tpm = tpm
        self._req_times: list[float] = []
        self._tok_events: list[tuple[float, int]] = []  # (t, token_count)
        self._lock = threading.Lock()

    def acquire(self, expected_tokens: int = 800) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                self._req_times = [t for t in self._req_times if now - t < 60.0]
                self._tok_events = [(t, n) for (t, n) in self._tok_events if now - t < 60.0]
                tokens_used = sum(n for _, n in self._tok_events)
                under_rpm = len(self._req_times) < self.rpm
                under_tpm = self.tpm is None or (tokens_used + expected_tokens) <= self.tpm
                if under_rpm and under_tpm:
                    self._req_times.append(now)
                    self._tok_events.append((now, expected_tokens))
                    return
            time.sleep(0.25)

    # Backwards-compatible shim so any residual take() callers still work.
    def take(self, n: float = 1.0) -> None:
        self.acquire(expected_tokens=int(max(1, n) * 800))

    def record_actual_tokens(self, actual: int, expected: int = 800) -> None:
        """Replace the most-recent token estimate with the observed count.

        Called after a successful response so the 60s window reflects reality
        (Groq's TPM is enforced on real usage, not our guess).
        """
        if actual <= 0 or abs(actual - expected) < 100:
            return
        with self._lock:
            if self._tok_events:
                t, _ = self._tok_events.pop()
                self._tok_events.append((t, int(actual)))

    def drain_for(self, seconds: float) -> None:
        """Mark the bucket fully saturated for ``seconds``.

        Used after a 429 so no further requests fire until the server-provided
        retry window elapses, even if another thread would otherwise slip in.
        """
        if seconds <= 0:
            return
        with self._lock:
            now = time.monotonic()
            # Insert synthetic events in the past so they expire exactly when
            # the server says we're allowed to try again.
            future_offset = max(0.0, seconds - 60.0)
            anchor = now - 60.0 + seconds + future_offset
            # Saturate RPM.
            self._req_times = [anchor] * self.rpm
            # Saturate TPM if configured.
            if self.tpm is not None:
                self._tok_events = [(anchor, self.tpm)]


# Free-tier limits per (provider, model). Verified against Groq's
# rate-limit page as of April 2026; conservative where the tier wobbles.
_RATE_LIMITS: dict[str, dict[str, int | None]] = {
    # OpenAI direct
    "openai/gpt-4o-mini":                 {"rpm": 60,  "tpm": None},
    "openai/gpt-4.1-mini":                {"rpm": 60,  "tpm": None},  # forward-compat
    # Groq main models (pilot cohort)
    "groq/llama-3.3-70b-versatile":       {"rpm": 10,  "tpm": 6000},
    "groq/openai/gpt-oss-20b":            {"rpm": 5,   "tpm": 3000},  # 19 losses in pilot
    "groq/qwen/qwen3-32b":                {"rpm": 5,   "tpm": 3000},  # 33 losses in pilot
    # Groq annotator — reserved bucket so re-annotation cannot starve generation
    "groq/llama-3.1-8b-instant":          {"rpm": 15,  "tpm": 6000},
}

# Safe fallback for any model not in the table above.
_DEFAULT_LIMIT: dict[str, int | None] = {"rpm": 10, "tpm": 6000}

_BUCKETS: dict[str, TokenBucket] = {}
_BUCKETS_LOCK = threading.Lock()


def _bucket_key(provider: str, model_id: str) -> str:
    return f"{provider}/{model_id}"


def _bucket_for(provider: str, model_id: str) -> TokenBucket:
    key = _bucket_key(provider, model_id)
    with _BUCKETS_LOCK:
        b = _BUCKETS.get(key)
        if b is None:
            spec = _RATE_LIMITS.get(key, _DEFAULT_LIMIT)
            b = TokenBucket(rpm=int(spec["rpm"]), tpm=spec["tpm"])  # type: ignore[arg-type]
            _BUCKETS[key] = b
        return b


_RETRY_AFTER_RE = re.compile(r"try again in\s*([\d.]+)\s*s", re.IGNORECASE)


def _parse_retry_after(body: str, headers: dict) -> float | None:
    """Return the server-requested cooldown in seconds, or None.

    Honours the standard ``Retry-After`` header first (seconds form), then
    falls back to parsing Groq's free-form body hint ("Please try again in
    42.1s"). Returns None if neither is present/parseable.
    """
    # Header names may arrive in mixed case depending on transport.
    for k, v in (headers or {}).items():
        if k.lower() == "retry-after":
            try:
                return float(v)
            except (TypeError, ValueError):
                break
    if body:
        m = _RETRY_AFTER_RE.search(body)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                return None
    return None


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


def _http_error_parts(e: urllib.error.HTTPError) -> tuple[str, dict]:
    body = ""
    try:
        body = e.read().decode("utf-8", errors="ignore")
    except Exception:
        pass
    headers: dict = {}
    try:
        headers = {k: v for k, v in e.headers.items()} if e.headers else {}
    except Exception:
        headers = {}
    return body, headers


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

    bucket = _bucket_for(spec.provider, spec.model_id)
    expected_tokens = 800
    bucket.acquire(expected_tokens=expected_tokens)

    err: Exception | None = None
    for attempt in range(max_retries):
        try:
            resp = _post_json(spec.provider, payload)
            break
        except urllib.error.HTTPError as e:
            body, headers = _http_error_parts(e)
            if e.code == 429:
                retry = _parse_retry_after(body, headers)
                if retry is not None:
                    bucket.drain_for(retry + 1.0)
                    time.sleep(retry + 1.0)
                else:
                    time.sleep(min((2 ** attempt) + random.random(), 30))
                err = LLMError(f"{spec.provider}/{spec.model_id} 429: {body[:200]}")
                # Re-acquire before the next attempt so we respect the drained bucket.
                bucket.acquire(expected_tokens=expected_tokens)
                continue
            if e.code in (500, 502, 503, 504):
                retry = _parse_retry_after(body, headers)
                wait = retry if retry is not None else (2 ** attempt) + random.random()
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

    usage = resp.get("usage", {}) or {}
    actual_tokens = int(usage.get("total_tokens") or 0)
    if actual_tokens:
        bucket.record_actual_tokens(actual_tokens, expected=expected_tokens)

    out = {
        "text": text,
        "model_id": resp.get("model", spec.model_id),
        "provider": spec.provider,
        "cached": False,
        "usage": usage,
    }
    if cache:
        cache.put(key, out)
    return out
