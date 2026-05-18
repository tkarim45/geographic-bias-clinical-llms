"""Unified generate(messages, **kwargs) abstraction across providers.

Supported providers (detected from model_id prefix or configured endpoint):
  - openai:*       -> OpenAI Chat Completions API
  - groq:*         -> Groq OpenAI-compatible endpoint
  - bedrock:*      -> AWS Bedrock Runtime (boto3; Anthropic + Meta Llama schemas)

Features:
  - Token-bucket rate limiting per (provider, model) — both RPM and TPM
  - Exponential-backoff retry on 5xx; 429 honours Retry-After / Groq body hint
  - Per-request client-side idempotency key derived from (model, prompt, seed)
  - File-based response cache keyed on the idempotency key so reruns are free

Transport is stdlib urllib for OpenAI/Groq; Bedrock uses boto3 (only
third-party dep). AWS creds are read from env by botocore (AWS_ACCESS_KEY_ID /
AWS_SECRET_ACCESS_KEY / AWS_SESSION_TOKEN / AWS_DEFAULT_REGION).
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
from dataclasses import dataclass, field
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
    provider: str          # "openai" | "groq" | "bedrock"
    model_id: str          # e.g. "gpt-4o-mini", "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    display_name: str      # pretty label for reports
    max_tokens: int = 512
    temperature: float = 0.2
    supports_json_format: bool = True
    bedrock_region: str | None = None  # required when provider=="bedrock"


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
# Bedrock entries use account-level per-model RPM quotas (Service Quotas →
# Amazon Bedrock → "On-demand InvokeModel requests per minute for model X").
# These defaults are conservative; request quota bumps on the console if a
# run plans to exceed them.
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
    # Bedrock (cross-region inference profiles; us-east-1 defaults)
    "bedrock/us.anthropic.claude-haiku-4-5-20251001-v1:0":   {"rpm": 200, "tpm": None},
    "bedrock/us.anthropic.claude-3-5-haiku-20241022-v1:0":   {"rpm": 200, "tpm": None},
    "bedrock/us.meta.llama3-3-70b-instruct-v1:0":            {"rpm": 100, "tpm": None},
    "bedrock/us.meta.llama3-1-70b-instruct-v1:0":            {"rpm": 100, "tpm": None},
    "bedrock/us.meta.llama3-1-8b-instruct-v1:0":             {"rpm": 200, "tpm": None},
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


# -----------------------------------------------------------------------------
# Bedrock
# -----------------------------------------------------------------------------

_BEDROCK_LOCAL = threading.local()


def _bedrock_client(region: str):
    """Return a bedrock-runtime client, one per (thread, region).

    botocore clients are not reliably safe to share across threads under the
    sandbox's SSL stack (a shared client segfaulted under the thread pool), so
    each worker thread builds and caches its own client.
    """
    clients = getattr(_BEDROCK_LOCAL, "clients", None)
    if clients is None:
        clients = {}
        _BEDROCK_LOCAL.clients = clients
    c = clients.get(region)
    if c is None:
        import boto3  # local import keeps stdlib-only for non-bedrock runs
        c = boto3.client("bedrock-runtime", region_name=region)
        clients[region] = c
    return c


_LLAMA_TEMPLATE = (
    "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
    "{system}<|eot_id|>{turns}<|start_header_id|>assistant<|end_header_id|>\n\n"
)
_LLAMA_TURN = (
    "<|start_header_id|>{role}<|end_header_id|>\n\n{content}<|eot_id|>"
)


def _render_llama_prompt(messages: list[dict]) -> str:
    """Render OpenAI-style chat messages into a Llama-3 instruct prompt.

    Bedrock's Meta Llama 3.x endpoint expects the raw prompt text with
    Llama's chat-template tokens, not a `messages` list.
    """
    system = ""
    turns: list[str] = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "") or ""
        if role == "system":
            system = content
            continue
        turns.append(_LLAMA_TURN.format(role=role, content=content))
    return _LLAMA_TEMPLATE.format(system=system, turns="".join(turns))


def _bedrock_body(spec: "ModelSpec", messages: list[dict]) -> tuple[dict, str]:
    """Return (request_body, family) for a Bedrock InvokeModel call.

    `family` is "anthropic" or "llama" — used for response decoding.
    """
    mid = spec.model_id
    # Inference-profile IDs carry a region prefix (e.g. "us.") before the vendor token.
    base = mid.split(".", 1)[1] if mid[:3] in ("us.", "eu.") or mid.startswith("global.") else mid
    if base.startswith("anthropic."):
        system_msgs = [m["content"] for m in messages if m.get("role") == "system"]
        user_turns = [m for m in messages if m.get("role") != "system"]
        body: dict = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": spec.max_tokens,
            "temperature": spec.temperature,
            "messages": user_turns,
        }
        if system_msgs:
            body["system"] = "\n\n".join(system_msgs)
        return body, "anthropic"
    if base.startswith("meta.llama"):
        return {
            "prompt": _render_llama_prompt(messages),
            "max_gen_len": spec.max_tokens,
            "temperature": spec.temperature,
        }, "llama"
    raise LLMError(f"Unsupported Bedrock modelId: {mid}")


def _bedrock_extract(family: str, payload: dict) -> tuple[str, dict]:
    """Return (text, usage_dict) from a Bedrock response payload."""
    if family == "anthropic":
        parts = payload.get("content") or []
        text = "".join(p.get("text", "") for p in parts if p.get("type") == "text")
        u = payload.get("usage", {}) or {}
        usage = {
            "prompt_tokens":     int(u.get("input_tokens", 0) or 0),
            "completion_tokens": int(u.get("output_tokens", 0) or 0),
            "total_tokens":      int(u.get("input_tokens", 0) or 0) + int(u.get("output_tokens", 0) or 0),
        }
        return text, usage
    if family == "llama":
        text = payload.get("generation", "") or ""
        usage = {
            "prompt_tokens":     int(payload.get("prompt_token_count", 0) or 0),
            "completion_tokens": int(payload.get("generation_token_count", 0) or 0),
            "total_tokens":      int(payload.get("prompt_token_count", 0) or 0) + int(payload.get("generation_token_count", 0) or 0),
        }
        return text, usage
    raise LLMError(f"Unknown Bedrock family: {family}")


def _invoke_bedrock(spec: "ModelSpec", messages: list[dict]) -> dict:
    """Single Bedrock invocation. Raises LLMError on failure with a .throttled flag."""
    region = spec.bedrock_region or os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
    client = _bedrock_client(region)
    body, family = _bedrock_body(spec, messages)
    resp = client.invoke_model(modelId=spec.model_id, body=json.dumps(body))
    payload = json.loads(resp["body"].read())
    text, usage = _bedrock_extract(family, payload)
    return {"text": text, "model_id": spec.model_id, "usage": usage}


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
    bedrock_result: dict | None = None
    for attempt in range(max_retries):
        try:
            if spec.provider == "bedrock":
                bedrock_result = _invoke_bedrock(spec, messages)
            else:
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
            # Bedrock ThrottlingException / ModelErrorException surface as
            # botocore ClientError; treat throttles like 429 and 5xx like
            # transient HTTP errors.
            name = type(e).__name__
            ecode = getattr(e, "response", {}).get("Error", {}).get("Code", "") if hasattr(e, "response") else ""
            if spec.provider == "bedrock" and (
                name == "ThrottlingException"
                or ecode in ("ThrottlingException", "TooManyRequestsException")
            ):
                wait = min((2 ** attempt) + random.random(), 30)
                bucket.drain_for(wait + 1.0)
                time.sleep(wait + 1.0)
                err = LLMError(f"{spec.provider}/{spec.model_id} throttled: {str(e)[:200]}")
                bucket.acquire(expected_tokens=expected_tokens)
                continue
            if spec.provider == "bedrock" and ecode in (
                "ModelErrorException", "ServiceUnavailableException",
                "InternalServerException", "ModelTimeoutException",
            ):
                time.sleep(min((2 ** attempt) + random.random(), 30))
                err = LLMError(f"{spec.provider}/{spec.model_id} {ecode}: {str(e)[:200]}")
                continue
            wait = (2 ** attempt) + random.random()
            time.sleep(min(wait, 20))
            err = e
            continue
    else:
        raise LLMError(f"Exhausted retries for {spec.provider}/{spec.model_id}: {err}")

    if spec.provider == "bedrock":
        assert bedrock_result is not None
        text = bedrock_result["text"]
        usage = bedrock_result["usage"]
        returned_model_id = bedrock_result["model_id"]
    else:
        text = ""
        try:
            text = resp["choices"][0]["message"]["content"] or ""
        except Exception:
            text = json.dumps(resp)[:500]
        usage = resp.get("usage", {}) or {}
        returned_model_id = resp.get("model", spec.model_id)

    actual_tokens = int(usage.get("total_tokens") or 0)
    if actual_tokens:
        bucket.record_actual_tokens(actual_tokens, expected=expected_tokens)

    out = {
        "text": text,
        "model_id": returned_model_id,
        "provider": spec.provider,
        "cached": False,
        "usage": usage,
    }
    if cache:
        cache.put(key, out)
    return out
